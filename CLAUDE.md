# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QBO Copilot is an AI-powered QuickBooks Online assistant for CPAs. It provides natural language access to QBO operations through Slack (primary), with a multi-tenant architecture supporting multiple client companies.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Slack bot
python integrations/slack/bot.py

# Run the interactive CLI agent
python agent/main.py

# Run QBO client CLI commands directly
python qbo/client.py accounts
python qbo/client.py customers
python qbo/client.py invoices

# Run all tests
python -m pytest tests/ -v

# Run a single test class
python -m pytest tests/test_qbo_tools.py::TestReadOperations -v

# Run a single test
python -m pytest tests/test_qbo_tools.py::TestReadOperations::test_get_accounts -v

# Format code
black .

```

## Architecture

```
Slack (Bot/Shortcuts/Modals) → Agent (Claude LLM) → Tool Functions → QBO REST API
                                                                   → SQLite (onboarding)
```

**Five layers, bottom to top:**

1. **`qbo/client.py`** — QBO REST API wrapper with OAuth token management (auto-refresh on 401). Handles all CRUD operations against QBO endpoints. Supports sandbox and production environments.

2. **`qbo/multi_tenant.py`** — Multi-tenant client management. Loads client configs from `config/clients.yaml`, maps Slack channels to QBO companies, and manages per-client token storage in `config/tokens/{realm_id}.json`.

3. **`agent/tools/qbo_tools.py`** — Tool registry (25+ tools) with standardized schemas for LLM integration. Uses global state (`_tenant_manager`, `_current_client`) to track the active QBO client. Each tool is a dict with `name`, `description`, `parameters`, and `function`.

4. **`agent/main.py`** — `CPACopilotAgent` class that orchestrates Claude as the LLM with the tool registry. Contains the system prompt and handles tool call routing.

5. **`integrations/slack/bot.py`** — Slack bot using Socket Mode (slack-bolt). Handles DMs, @mentions, `/qbo` slash command, interactive components (buttons, modals, dropdowns), shortcuts, and Home tab dashboard. This is the largest file (~70KB) and the primary user-facing interface.

**Supporting modules:**

- **`integrations/slack/blocks.py`** — Slack Block Kit builders for rich UI (invoices, expenses, accounts, dashboards, modals)
- **`qbo_copilot/onboarding/`** — Client onboarding state machine with phases 0-6, blocker detection, and progress tracking
- **`qbo_copilot/data/onboarding_db.py`** — SQLite persistence for onboarding state (auto-creates DB, uses SQL migrations in `data/migrations/`)

## Configuration

- **`config/.env`** — All secrets (QBO OAuth, Anthropic API key, Slack tokens, SMTP). Copy from `.env.example`.
- **`config/clients.yaml`** — Multi-tenant client definitions mapping company names to QBO realm IDs and Slack channels.
- **`config/tokens/`** — Per-client OAuth token JSON files, auto-managed by `QBOClient`.
- **`config/slack-app-manifest.json`** — Slack app definition (scopes, shortcuts, slash commands).

## Key Patterns

- **Tool registry pattern**: Tools in `qbo_tools.py` are dicts with a `function` key pointing to the handler. The agent calls tools by name and the registry dispatches.
- **Global mutable state**: `qbo_tools.py` uses module-level globals (`_tenant_manager`, `_current_client`) set via `initialize()` and `switch_client()`. Be careful with concurrent access.
- **OAuth token lifecycle**: Tokens stored as JSON in `config/tokens/`. `QBOClient._make_request()` auto-retries with token refresh on 401 responses.
- **Slack interaction flow**: User action → Slack event/command → bot handler → Claude agent → tool execution → Block Kit response back to Slack.

## Testing

Tests in `tests/test_qbo_tools.py` use module-scoped fixtures (`qbo_client`, `test_customer_name`, `test_vendor_name`) that create real QBO sandbox entities. Tests run against the actual QBO sandbox API — they are integration tests, not mocked.

`tests/test_qbo_interactive.py` contains interactive tests. `tests/test_qbo_quick.sh` is a shell-based quick validation script.
