# Technical Architecture

This document describes the architecture of QBO Copilot, covering all layers from the Slack interface down to the QBO REST API.

## High-Level Architecture

```
                        Slack Workspace
                             |
                    [Socket Mode Connection]
                             |
                   +-------------------+
                   | Slack Bot (bot.py)|  Layer 5: User Interface
                   +-------------------+
                             |
                   +-------------------+
                   | Agent (main.py)   |  Layer 4: LLM Orchestration
                   +-------------------+
                             |
                   +-------------------+
                   | Tools (qbo_tools) |  Layer 3: Tool Registry
                   +-------------------+
                             |
                   +-------------------+
                   | Multi-Tenant      |  Layer 2: Client Management
                   | (multi_tenant.py) |
                   +-------------------+
                             |
                   +-------------------+
                   | QBO Client        |  Layer 1: API Wrapper
                   | (client.py)       |
                   +-------------------+
                             |
                   [HTTPS / OAuth 2.0]
                             |
                   +-------------------+
                   | QBO REST API      |
                   | (Intuit servers)  |
                   +-------------------+
```

---

## Layer 1: QBO REST API Client

**File:** `qbo/client.py`

The foundation layer. `QBOClient` is a Python wrapper around the QuickBooks Online REST API.

### Responsibilities
- Execute QBO Query Language queries (`SELECT * FROM Account ...`)
- Perform CRUD operations on entities (Customer, Vendor, Invoice, Purchase)
- Manage OAuth token lifecycle (load, save, auto-refresh on 401)
- Support both sandbox and production environments

### Key Methods

| Method | Description |
|--------|-------------|
| `query(query_string)` | Execute a QBO Query Language query |
| `get_accounts()` | Get Chart of Accounts |
| `get_customers()` | Get customer list |
| `get_invoices()` | Get invoices (optionally unpaid only) |
| `create_invoice()` | Create a new invoice with line items |
| `create_expense()` | Create a new expense/purchase |
| `void_invoice()` | Void an invoice (irreversible) |
| `send_invoice()` | Email an invoice to the customer |

### Token Auto-Refresh

```
API Request
    |
    v
Response 200? --yes--> Return data
    |
   (401)
    |
    v
Refresh token via POST to Intuit token endpoint
    |
    v
Save new tokens to config/tokens/{realm_id}.json
    |
    v
Retry original request with new access_token
    |
    v
Response 200? --yes--> Return data
    |
   (fail)
    |
    v
Raise exception
```

---

## Layer 2: Multi-Tenant Client Management

**File:** `qbo/multi_tenant.py`

Manages multiple QBO companies under a single CPA's installation.

### Responsibilities
- Load client configurations from `config/clients.yaml`
- Map Slack channels to QBO companies
- Manage per-client `QBOClient` instances (cached)
- Provide lookup by company name, realm ID, or Slack channel

### Key Classes

**`ClientConfig`** -- Configuration for a single company:
- `name`, `realm_id`, `primary_contact`, `slack_channel`, `metadata`

**`TenantManager`** -- Manages all companies:
- `list_clients()` -- List all configured companies
- `get_client(identifier)` -- Get a `QBOClient` instance by name or realm_id
- `find_client_by_channel(channel)` -- Look up company by Slack channel name
- `add_client(...)` -- Add a new company and save to YAML

### Client Resolution Order

```
1. Slack channel matches a slack_channel in clients.yaml?
   --> Use that company

2. User has explicitly selected a company?
   --> Use their selection

3. Neither?
   --> Use the first company in clients.yaml
```

---

## Layer 3: Tool Registry

**File:** `agent/tools/qbo_tools.py`

Defines 25+ tools that the LLM agent can call. Each tool is a dictionary with a standardized schema.

### Tool Structure

```python
{
    'name': 'qbo_get_invoices',
    'description': 'Get invoices from QuickBooks Online',
    'function': qbo_get_invoices,      # Python callable
    'parameters': {
        'type': 'object',
        'properties': {
            'unpaid_only': {'type': 'boolean', 'default': False}
        }
    }
}
```

### Tool Categories

**Read Operations (7 tools):**
- `qbo_query` -- Execute raw QBO Query Language
- `qbo_get_entity` -- Get a single entity by type and ID
- `qbo_get_accounts` -- Chart of Accounts (filterable by type)
- `qbo_get_customers` -- Customer list
- `qbo_get_vendors` -- Vendor list
- `qbo_get_invoices` -- Invoices (optionally unpaid only)
- `qbo_get_purchases` -- Expenses with date filters

**Multi-Tenant Operations (2 tools):**
- `qbo_list_clients` -- List all configured companies
- `qbo_switch_client` -- Switch active company

**Customer CRUD (2 tools):**
- `qbo_create_customer` -- Create a customer
- `qbo_update_customer` -- Update a customer (requires SyncToken)

**Vendor CRUD (2 tools):**
- `qbo_create_vendor` -- Create a vendor
- `qbo_update_vendor` -- Update a vendor (requires SyncToken)

**Invoice Operations (6 tools):**
- `qbo_get_tax_codes` -- List available tax codes
- `qbo_create_invoice` -- Create an invoice with line items
- `qbo_update_invoice` -- Update an existing invoice
- `qbo_void_invoice` -- Void an invoice (destructive)
- `qbo_delete_invoice` -- Delete an invoice (destructive)
- `qbo_send_invoice` -- Email an invoice to the customer

**Expense Operations (2 tools):**
- `qbo_create_expense` -- Create an expense/purchase
- `qbo_delete_expense` -- Delete an expense (destructive)

### Global State

The tool registry uses module-level globals to track state:

```python
_tenant_manager: Optional[TenantManager] = None  # Singleton
_current_client: Optional[str] = None             # Active realm_id
```

- `_tenant_manager` is lazily initialized on first use
- `_current_client` is set per-user by the Slack bot via `set_current_client(realm_id)`

---

## Layer 4: LLM Orchestration

**File:** `agent/main.py`

The `CPACopilotAgent` class connects the user's natural language input to the tool registry via Claude.

### Responsibilities
- Maintain the system prompt with tool descriptions and guidelines
- Route user messages to Claude with tool schemas
- Handle Claude's tool call requests by dispatching to the tool registry
- Format results for the user

### Request Flow

```
User message
    |
    v
CPACopilotAgent.process_message()
    |
    v
Claude API call (with system prompt + tool schemas)
    |
    v
Claude returns tool_use response?
    |
   yes
    |
    v
Dispatch to tool function from registry
    |
    v
Return tool result to Claude
    |
    v
Claude generates human-readable response
    |
    v
Return to user
```

### System Prompt

The system prompt defines the agent's persona and guidelines:
- Identity: "QBO Copilot, an AI assistant for CPAs"
- Available tools and their descriptions
- Formatting guidelines (currency formatting, list limits)
- QBO Query Language examples
- Instructions to confirm which company before querying

---

## Layer 5: Slack Bot Interface

**File:** `integrations/slack/bot.py`

The largest module (~1700 lines). Handles all Slack interactions.

### Responsibilities
- Socket Mode connection to Slack (no public URL needed)
- Message handling (DMs, @mentions, channel messages)
- Slash command processing (`/qbo`)
- Interactive components (buttons, dropdowns, modals)
- Home tab dashboard rendering
- Receipt scanning workflow (file uploads, classification, review)
- Client onboarding phase management
- Message shortcuts (Convert to Case, Request Documents)

### Handler Registration Pattern

The bot organizes handlers into groups using `_register_*_handlers()` methods:

```python
class CPACopilotSlackBot:
    def __init__(self):
        ...
        self._register_message_handlers()
        self._register_interactive_handlers()
        self._register_modal_handlers()
        self._register_home_tab()
        self._register_onboarding_handlers()
        self._register_shortcuts()
        self._register_receipt_handlers()
```

### Message Processing Pipeline

```
Slack Event (message, app_mention, command, action)
    |
    v
Bot handler receives event
    |
    v
Determine active QBO company (channel mapping or user selection)
    |
    v
Send to Claude agent (with tool schemas)
    |
    v
Agent executes tools, returns response
    |
    v
Format as Block Kit message (via blocks.py)
    |
    v
Post response back to Slack
```

---

## Supporting Modules

### Block Kit Builders

**File:** `integrations/slack/blocks.py` (~1800 lines)

Builds Slack Block Kit JSON structures for rich UI. Functions for:
- Invoice cards, expense summaries, account lists
- Dashboard sections for the Home tab
- Modals for creating invoices, cases, document requests
- Receipt review cards with action buttons

### Onboarding State Machine

**File:** `qbo_copilot/onboarding/state_machine.py`

Manages the 7-phase onboarding workflow:
- Phase transitions with validation
- Blocker detection (prevents advancing until resolved)
- Progress tracking and reporting

### Onboarding Database

**File:** `qbo_copilot/data/onboarding_db.py`

SQLite persistence layer for all onboarding data. Uses the `OnboardingDB` class with methods for:
- Client CRUD
- Phase status tracking
- Contact and bank account management
- Document request tracking
- Case management
- Receipt queue
- Audit logging

### Receipt Scanner

**File:** `qbo_copilot/receipt_scanner.py`

Claude Vision integration for document OCR:
- `scan_receipt(image_bytes, mime_type, doc_type)` -- Sends image to Claude, returns extracted data and confidence score
- `validate_extracted_data(data)` -- Validates extracted fields, returns errors and warnings
- `_calculate_confidence(data, doc_type)` -- Computes confidence score based on key field presence

---

## Data Flow Diagrams

### Natural Language Query

```
User: "show unpaid invoices"
  |
  v
Slack --> bot.py (message handler)
  |
  v
bot.py --> Claude API (with qbo_tools schemas)
  |
  v
Claude --> tool_use: qbo_get_invoices(unpaid_only=True)
  |
  v
qbo_tools.py --> QBOClient.get_invoices(unpaid_only=True)
  |
  v
QBOClient --> QBO API: GET /v3/company/{realmId}/query?query=SELECT * FROM Invoice
  |
  v
QBO API --> JSON response with invoice data
  |
  v
qbo_tools.py --> filters invoices with Balance > 0
  |
  v
Claude --> formats human-readable response
  |
  v
bot.py --> blocks.py (builds Block Kit invoice cards)
  |
  v
Slack --> displays formatted invoice list to user
```

### Receipt Scanning

```
User: uploads receipt.jpg to DM
  |
  v
Slack file_share event --> bot.py (receipt handler)
  |
  v
bot.py --> posts classification dropdown
  |
  v
User selects "Expense Receipt"
  |
  v
bot.py --> creates receipt_queue entry (status: uploaded)
  |
  v
bot.py --> starts background thread (_process_receipt_scan)
  |
  v
Thread: downloads file from Slack API
  |
  v
Thread: receipt_scanner.scan_receipt(image_bytes, mime_type, "expense_receipt")
  |
  v
Thread: Claude Vision API --> returns extracted JSON
  |
  v
Thread: updates receipt_queue (status: scanned, extracted_data, confidence_score)
  |
  v
Thread: posts review card to Slack with Approve/Edit/Reject buttons
```

---

## SQLite Schema Overview

Three migrations define the database schema:

### 001_initial.sql -- Core Tables

| Table | Purpose |
|-------|---------|
| `clients` | Client company records with onboarding status |
| `onboarding_phases` | Per-client phase tracking (0-6) |
| `client_contacts` | Contact people with roles and approval thresholds |
| `bank_accounts` | Bank/CC account inventory with feed status |
| `doc_requests` | Document request tracking with lifecycle |
| `cases` | Trackable cases from message conversion |
| `audit_log` | Full audit trail of all actions |
| `operating_rules` | Per-client SLA and approval settings |
| `client_systems` | Third-party systems inventory (Stripe, Shopify, etc.) |

### 002_receipt_queue.sql -- Receipt Scanning

| Table | Purpose |
|-------|---------|
| `receipt_queue` | Document scanning pipeline with status tracking |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `config/.env` | All secrets: QBO OAuth, Anthropic API key, Slack tokens, SMTP, Google Drive |
| `config/.env.example` | Template for `.env` with all available settings |
| `config/clients.yaml` | Multi-tenant client definitions |
| `config/tokens/` | Per-client OAuth token JSON files (auto-managed) |
| `config/slack-app-manifest.json` | Slack app configuration (scopes, commands, events) |
| `config/google-service-account.json` | Google Drive service account credentials (optional) |

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Slack SDK | slack-bolt (Socket Mode), slack-sdk |
| LLM | Anthropic Claude (via anthropic SDK) |
| QBO API | REST over HTTPS, OAuth 2.0 |
| Database | SQLite (via stdlib sqlite3) |
| Config | YAML (pyyaml), .env (python-dotenv) |
| Google Drive | google-api-python-client, google-auth (optional) |
| HTTP Client | requests |
| Testing | pytest (integration tests against QBO sandbox) |
| Formatting | black |
