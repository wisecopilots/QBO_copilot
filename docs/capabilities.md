# QBO Copilot — Capabilities

## Overview

QBO Copilot is an AI-powered QuickBooks Online assistant built for CPA firms. It connects your QBO data to Slack, letting you manage invoices, expenses, customers, vendors, and client onboarding through natural language and interactive UI -- no browser tabs, no clicking through menus.

The system has **21 registered agent tools** across 7 categories, plus a full suite of Slack interactive components (buttons, modals, dropdowns, shortcuts) and a 7-phase client onboarding workflow. Below is an exhaustive list of everything QBO Copilot can do today.

---

## 1. Natural Language Reporting & Analytics

The most powerful feature: ask any question about your books in plain English. The AI agent translates your question into the right API calls and returns a formatted answer.

### What You Can Ask

- "Show me all unpaid invoices"
- "What's my total accounts receivable?"
- "List vendors I paid last month"
- "What's the balance for customer Acme Corp?"
- "Show me expense accounts with current balances"
- "How much did we spend on office supplies this quarter?"
- "Show purchases between Jan 1 and Jan 31"
- "Who are my top 5 customers by revenue?"

### Built-In Query Tools

| Tool | What It Does | Example |
|------|-------------|---------|
| **Query QBO Data** | Execute any QBO Query Language query | `SELECT * FROM Invoice WHERE Balance > 0` |
| **Get Accounts** | List chart of accounts, filter by type | All expense accounts, all bank accounts |
| **Get Customers** | List all customers with balances | Active customers with outstanding balances |
| **Get Vendors** | List all vendors with balances | All vendors, filter active/inactive |
| **Get Invoices** | List invoices, filter unpaid | Unpaid invoices, all invoices |
| **Get Purchases** | List expenses by date range | Purchases from last week, last month |
| **Get Entity** | Look up any single record by ID | Invoice #1045, Customer #123, Vendor #456 |
| **Get Tax Codes** | List available tax codes | HST, GST, Exempt, Zero-rated |

### Power User: QBO Query Language

For advanced users, the agent supports raw QBO Query Language. You can type these directly or let the AI generate them from your natural language question:

```sql
SELECT * FROM Invoice WHERE DueDate < '2026-02-01' AND Balance > 0
SELECT * FROM Purchase WHERE TxnDate >= '2026-01-01' ORDER BY TotalAmt DESC
SELECT * FROM Customer WHERE Active = true AND Balance > 1000
SELECT * FROM Account WHERE AccountType = 'Expense'
SELECT * FROM Vendor WHERE Active = true
```

---

## 2. Invoice Management

Full lifecycle management of invoices without opening QBO.

### Agent Tools

| Action | How to Ask | What Happens |
|--------|-----------|--------------|
| **Create Invoice** | "Create invoice for Acme Corp, web design $2,500" | Creates invoice with line items, returns confirmation with doc number |
| **Create with Details** | "Invoice customer 123, consulting $1,500, due March 15" | Supports custom due dates, multiple line items, tax codes, memos |
| **Send Invoice** | "Send invoice 1045 to client" | Emails invoice to customer's email address on file |
| **Send to Custom Email** | "Send invoice 1045 to john@acme.com" | Sends to a specified email address |
| **View Invoice** | "Show me invoice 1045" | Returns all invoice details: customer, dates, line items, balance |
| **Update Invoice** | "Update invoice 1045, change amount to $3,000" | Modifies existing invoice (line items, due date, memo) |
| **Void Invoice** | "Void invoice 1032" | Voids the invoice (requires confirmation, cannot be undone) |
| **Delete Invoice** | "Delete invoice 1099" | Permanently removes the invoice (requires confirmation, cannot be undone) |
| **List Unpaid** | "Show me unpaid invoices" | All invoices with balance > 0 |
| **List Overdue** | "Show overdue invoices" | Invoices past due date |

### Interactive UI (Slack)

- **Create Invoice button** opens a modal with customer dropdown, description, amount, and due date fields
- **Invoice list** shows an overflow menu per invoice with View Details, Send, and Void actions
- **Void and Send** require a confirmation modal before executing
- **Tax code support**: Invoices can include per-line or invoice-level tax codes (e.g., HST ON at 13%, Exempt, Zero-rated)

---

## 3. Expense & Receipt Management

### Manual Expense Creation

| Action | How to Ask |
|--------|-----------|
| **Create Expense** | "Add expense $50 to Office Supplies from Staples" |
| **Create with Details** | "Create expense, checking account, $1,200, vendor FedEx, category Shipping" |
| **Delete Expense** | "Delete expense [ID]" (requires confirmation) |
| **List Expenses** | "Show me expenses from last month" or "Show purchases between Jan 1 and Jan 31" |

Expense creation supports:
- Bank or credit card account selection
- Vendor assignment
- Multiple line items with per-line account categorization
- Transaction date
- Payment type: Cash, Check, or CreditCard
- Private memo

### Receipt Scanning (AI Vision OCR)

Upload a photo of any document in the Slack DM and QBO Copilot will extract structured data using Claude Vision.

**Step 1: Upload** -- Drop an image file (JPEG, PNG, etc.) in the bot's DM channel.

**Step 2: Classify** -- The bot shows a dropdown asking you to categorize the document:
- Expense Receipt
- Invoice
- Bill
- Bank Statement
- Other

**Step 3: AI Scan** -- Claude Vision OCR runs in the background (daemon thread) and extracts:
- Vendor name
- Transaction date
- Subtotal, tax, tip, total amount
- Currency
- Payment method (cash, credit, debit, check)
- Line items (description, quantity, unit price, amount)
- Invoice/reference number (for invoices and bills)
- Due date (for invoices and bills)
- Category suggestion (mapped to QBO expense categories)
- ALL visible text on the document (verbatim transcription)
- Notes (addresses, partial account numbers, memo fields)
- Confidence score (0-100%, calculated from key field extraction quality)

**Step 4: Review** -- A review card appears in Slack with all extracted data and a confidence indicator.

**Step 5: Action** -- Three buttons:
- **Approve** -- Accept data as-is, mark as approved in the queue
- **Edit** -- Open a modal to correct any field (vendor, date, total, tax, category, notes)
- **Reject** -- Discard the scan results

### Receipt Queue

- `/qbo receipts` -- View all receipts in queue with status
- Statuses: Uploaded, Scanning, Scanned, Approved, Rejected, Error
- Home tab shows receipt queue summary counts by status

---

## 4. Customer & Vendor Management

### Agent Tools

| Action | How to Ask | Details |
|--------|-----------|---------|
| **Create Customer** | "Create customer John Smith, john@example.com" | Name (required), email, phone, company name |
| **Update Customer** | "Update customer John Smith, new email john@newco.com" | Any field: name, email, phone, active status |
| **Deactivate Customer** | "Deactivate customer John Smith" | Soft delete (sets Active = false, can be reactivated) |
| **Create Vendor** | "Create vendor FedEx" | Name (required), email, phone, company name |
| **Update Vendor** | "Update vendor FedEx, phone 416-555-1234" | Any field: name, email, phone, active status |
| **List Customers** | "Show me all customers" | With balances and contact info |
| **List Vendors** | "Who are my vendors?" | With balances and contact info |

### Interactive UI (Slack)

- **Create Customer button** opens a modal with name, email, phone, and company fields
- Entity lookups by ID return full detail including SyncToken for subsequent updates

---

## 5. Multi-Company Management

For CPA firms managing multiple client QBO companies simultaneously.

### Agent Tools

| Action | How to Ask |
|--------|-----------|
| **List Companies** | "Show me all companies" or `/qbo clients` |
| **Switch Company** | "Switch to Acme Corp" |

### How It Works

- Each QBO company is defined in `config/clients.yaml` with a company name, realm ID, primary contact, and Slack channel mapping
- OAuth tokens are stored separately per company in `config/tokens/{realm_id}.json` with automatic refresh on 401 responses
- **Channel auto-routing**: Messages sent in a client's designated Slack channel automatically target that client's QBO instance
- **DM with multiple companies**: If you DM the bot and have multiple companies configured, it shows a dropdown selector before processing your request. Once selected, the choice persists for the session.
- **Single company auto-select**: If only one company is configured, it is selected automatically with no prompt

---

## 6. Client Onboarding Workflow

A structured 7-phase onboarding process for new CPA clients, with progress tracking, blocker detection, and persistent state in SQLite.

### Phase 0: Client Setup
- Legal name, display name, entity type
- Entity types: LLC, S-Corp, C-Corp, Sole Proprietorship, Partnership
- Fiscal year end
- Primary contact name

### Phase 1: Contacts & Roles
- Add team contacts with roles: Owner, Operator, Approver, Payroll Contact, Bookkeeper
- Designate a primary contact
- Designate an approver (required to advance)
- Set approval thresholds per contact

### Phase 2: QBO Connection
- Connect to QuickBooks Online via OAuth
- Store realm ID and tokens
- Verify connection by fetching company data

### Phase 3: Bank Feeds
- Inventory bank accounts: institution name, account type, last 4 digits
- Account types: Checking, Savings, Credit Card, Line of Credit
- Track feed connection status per account
- Requires at least one bank account and one connected feed to advance

### Phase 4: Document Vault
- Create Google Drive folder structure with standard subfolders:
  - Tax Returns, Financial Statements, Bank Statements, Payroll, Legal, Correspondence, Receipts, Invoices, Bills
- Request historical documents using pre-built document packs
- **Onboarding pack** (8 document types): prior year tax return, trial balance, bank statements, payroll reports, incorporation docs, sales tax filing, EIN letter, prior financials
- **Monthly pack**: bank statements, credit card statements, payroll reports
- **Quarterly pack**: Form 941, sales tax filing, estimated tax payments
- **Annual pack**: W-2s/W-3, 1099s, year-end statements, depreciation schedule, insurance policies
- Track document receipt status: Requested, Received, Reviewed, Filed
- Documents organized by category: Tax, Accounting, Banking, Payroll, Legal

### Phase 5: Systems Inventory
- Catalog external systems the client uses: Stripe, Square, PayPal, Shopify, Gusto, ADP, Bill.com, Expensify, and others
- Track integration status: Identified, Connecting, Connected, Verified

### Phase 6: Operating Rules
- Set approval threshold (dollar amount)
- Define response SLA (24h, 48h, 72h, 1 week)
- Set close schedule (Monthly by 15th, Monthly by 10th, Quarterly, Annual)
- Designate escalation contact
- Verify Slack channel exists for the client

### Onboarding Features
- **Progress tracking**: Per-phase completion percentage and overall progress across all 7 phases
- **Blocker detection**: Each phase calculates whether its requirements are met. Advancement is blocked until all required items are complete (can be force-advanced if needed).
- **Phase advancement**: Automatic transition from one phase to the next when all requirements are met
- **Phase reset**: Any phase can be reset to pending status, which also resets the current phase pointer if needed
- **Persistent state**: All onboarding data stored in SQLite with migration-based schema management
- **Visible from Home tab**: Onboarding dashboard with progress bars, work queues (waiting on client vs. waiting on CPA), and blocker summaries

---

## 7. Slack Integration Features

### Interaction Methods

| Method | When to Use | Visibility |
|--------|------------|-----------|
| **DM the bot** | Multi-step conversations, receipt uploads, private queries | Private (only you see it) |
| **`/qbo <query>`** | Quick one-off queries from any channel | Ephemeral (only you see the response) |
| **`/qbo help`** | Show the full capabilities help card | Ephemeral |
| **`/qbo receipts`** | View the receipt scanning queue | Ephemeral |
| **@QBO Copilot** | Team-visible answers in channels | Public to the entire channel |

### Home Tab Dashboard

Open the QBO Copilot app in Slack to see a live dashboard:

- **Client selector**: Dropdown to pick which onboarding client to view
- **Financial summary** (when QBO is connected): AR balance, AP balance, Cash balance, Overdue invoice count
- **Recent expenses**: Last 5 expenses
- **Quick action buttons**: Create Invoice, Add Expense, View Unpaid, View Expenses
- **Receipt queue summary**: Counts by status (scanning, scanned, approved, rejected)
- **Onboarding dashboard**: Current phase, progress bar, phase completion items
- **Work queues**: Items waiting on client vs. items waiting on CPA
- **Capabilities / help section**: Quick reference for what the bot can do

### Message Shortcuts (Right-Click Actions)

- **Convert to Case** -- Right-click any Slack message and turn it into a tracked case with:
  - Title
  - Client selection
  - Priority level
  - Description
  - Automatic link back to the original message (permalink)
  - Thread reply confirming case creation

- **Request Documents** -- Right-click to open a document request modal:
  - Auto-detects the client from the channel context
  - Pre-populates with the onboarding document pack
  - Creates tracked document requests in the database

### Interactive Components

- **Buttons**: Create Invoice, Add Expense, View Unpaid, View Expenses, Approve Receipt, Reject Receipt, Edit Receipt
- **Dropdown menus**: Company selector, document type classifier, expense categorization
- **Modals**: Invoice creation, customer creation, receipt editing, case creation, document request, void/send confirmation
- **Confirmation dialogs**: Required before destructive actions (void invoice, delete invoice, delete expense)
- **Overflow menus**: Per-invoice actions (View Details, Send, Void) on invoice list items
- **Home tab**: Full dashboard with live data, auto-refreshed on open

### Google Drive Integration

- **Automatic folder creation**: Standard folder structure per client with 9 subfolders
- **Period subfolders**: Create year/quarter/month subfolders within category folders
- **File operations**: Upload, download, move, delete, search, share
- **Ensure folder structure**: Idempotent operation that creates missing folders without duplicating existing ones
- **Sharing**: Share client folders with team members by email with configurable permissions (reader, writer, commenter)

---

## Quick Reference

### Most Common Commands

```
show me unpaid invoices
what's my accounts receivable?
create invoice for [customer], [description] $[amount]
send invoice [number]
show me expenses from last month
create customer [name], [email]
switch to [company name]
/qbo help
/qbo receipts
```

### CLI Access

QBO Copilot also supports direct CLI usage for scripting and testing:

```bash
# Interactive AI agent
python agent/main.py

# Direct QBO client commands
python qbo/client.py accounts
python qbo/client.py customers
python qbo/client.py invoices --unpaid
python qbo/client.py purchases --start 2026-01-01 --end 2026-01-31
python qbo/client.py query "SELECT * FROM Vendor WHERE Active = true"
python qbo/client.py get Invoice 1045
python qbo/client.py create-customer --name "Acme Corp" --email "billing@acme.com"
python qbo/client.py create-invoice --customer 123 --amount 2500 --description "Web Design"
python qbo/client.py send-invoice --id 1045
python qbo/client.py void-invoice --id 1032 --sync-token 0
```

---

## What QBO Copilot Cannot Do (Yet)

The following are not yet supported with dedicated tools. The AI agent may attempt some of these through raw QBO queries, but purpose-built tools and UI are not yet implemented.

- Bank reconciliation
- Payroll processing
- Journal entries
- Bill payments
- Inventory management
- Profit & Loss / Balance Sheet report generation
- Bank feed auto-categorization
- Recurring invoices and scheduled sends
- Payment recording against invoices
- Multi-currency transactions
- Time tracking and billable hours
- Estimates and sales orders
- Credit memos and refunds

These represent future development priorities.
