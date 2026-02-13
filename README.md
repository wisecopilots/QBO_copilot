# QBO Copilot

**AI-powered QuickBooks Online assistant for CPAs -- manage your clients' books from Slack.**

QBO Copilot connects your Slack workspace to QuickBooks Online through Claude AI. Ask questions in plain English, create invoices, scan receipts, and manage multiple client companies without leaving Slack. It is built for accounting firms that want to move faster.

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)

---

## Key Features

- **Natural language queries** -- ask things like "show me all unpaid invoices over $5,000" and get formatted results in Slack
- **Full CRUD operations** -- create and manage invoices, expenses, customers, vendors, journal entries, and more
- **Receipt and invoice scanning** -- upload images in Slack and Claude Vision OCR extracts line items, totals, and vendor details
- **Multi-company support** -- switch between QBO client companies within Slack, each mapped to its own channel
- **Client onboarding workflow** -- a 6-phase state machine that tracks new client setup from intake to go-live
- **Home tab dashboard** -- see account summaries, receipt queue status, and onboarding progress at a glance
- **Slash command with interactive UI** -- `/qbo` opens dropdowns, modals, and buttons for common operations
- **Message shortcuts** -- right-click any Slack message to convert it into a case or document request
- **Google Drive document vault** -- (optional) auto-organize client documents into per-client folder structures
- **25+ tool functions** -- a full registry of QBO operations exposed to the AI agent with structured schemas

## How It Works

```
You (Slack)  -->  QBO Copilot (Claude AI)  -->  QuickBooks Online
```

You send a message or use a slash command in Slack. The bot routes your request to the Claude-powered agent, which selects the right tool, calls the QBO REST API, and returns a rich Block Kit response back to your channel.

## Quick Start

```bash
git clone https://github.com/qbo-copilot/qbo-copilot.git
cd qbo-copilot
bash setup.sh
```

Then open Slack, DM the bot, and start asking questions.

## What You'll Need

| Requirement | Details |
|---|---|
| Operating system | macOS 12+ (Apple Silicon or Intel) |
| Python | 3.11 or newer |
| QuickBooks Online | Any account (sandbox works for testing) |
| Slack workspace | Admin access to install apps |
| Anthropic API key | For Claude ([console.anthropic.com](https://console.anthropic.com)) |
| Disk space | ~500 MB |

## Features Showcase

### Natural Language Queries

Ask questions the way you would ask a colleague:

```
> Show me all invoices over $5,000 that are past due
> What's the total accounts receivable for Acme Corp?
> List all vendors we paid last month
```

The agent translates your question into the appropriate QBO API calls and returns formatted results.

<!-- screenshot placeholder -->

### Receipt Scanning

Upload a receipt or invoice image directly in Slack. The bot detects the file, asks you to classify it (receipt, invoice, or bill), then runs Claude Vision OCR in the background. When processing finishes, you get a review card with extracted fields -- vendor, date, line items, totals -- and one-click actions to approve or edit before posting to QBO.

<!-- screenshot placeholder -->

### Multi-Company

CPA firms manage many clients. QBO Copilot maps each Slack channel to a QBO company through `config/clients.yaml`. Switch context with a command:

```
> /qbo switch Acme Corp
```

The bot confirms the switch and all subsequent queries in that channel target the new company.

<!-- screenshot placeholder -->

### Home Tab Dashboard

Open the QBO Copilot app home tab in Slack to see a summary dashboard: account balances, recent transactions, receipt queue counts, and onboarding progress for each client.

<!-- screenshot placeholder -->

### Client Onboarding

New client setup is tracked through a 6-phase state machine (phases 0 through 6). Each phase has required steps, blocker detection, and progress tracking. The onboarding status is persisted in SQLite and visible from the Home tab and via slash commands.

<!-- screenshot placeholder -->

## Project Structure

```
qbo-copilot/
├── agent/
│   ├── main.py                    # CPACopilotAgent -- orchestrates Claude + tools
│   └── tools/
│       └── qbo_tools.py           # 25+ tool definitions for QBO operations
├── integrations/
│   ├── slack/
│   │   ├── bot.py                 # Slack bot (Socket Mode, slash commands, shortcuts)
│   │   └── blocks.py              # Block Kit builders for rich Slack UI
│   └── google_drive/
│       └── client.py              # Google Drive document vault (optional)
├── qbo/
│   ├── client.py                  # QBO REST API wrapper with OAuth token management
│   ├── multi_tenant.py            # Multi-company client manager
│   └── oauth.py                   # OAuth setup and token refresh
├── qbo_copilot/
│   ├── receipt_scanner.py         # Claude Vision OCR for receipts/invoices
│   ├── onboarding/
│   │   ├── state_machine.py       # 6-phase onboarding workflow
│   │   └── doc_templates.py       # Document request templates
│   └── data/
│       ├── onboarding_db.py       # SQLite persistence layer
│       └── migrations/            # SQL migration scripts
├── config/
│   ├── .env.example               # Environment variable template
│   ├── clients.yaml               # Client-to-QBO-company mappings
│   ├── slack-app-manifest.json    # Slack app definition
│   └── tokens/                    # Per-client OAuth token files (auto-managed)
├── tests/
│   ├── test_qbo_tools.py          # Integration tests (runs against QBO sandbox)
│   ├── test_qbo_interactive.py    # Interactive test suite
│   └── test_qbo_quick.sh          # Quick validation script
├── docker-compose.yml             # Full stack deployment
├── Dockerfile.agent               # Agent container
├── Dockerfile.slack               # Slack bot container
└── requirements.txt               # Python dependencies
```

## Configuration

**`config/.env`** -- All secrets and API keys. Copy from `.env.example` and fill in your values:

- `ANTHROPIC_API_KEY` -- your Claude API key
- `QBO_CLIENT_ID` / `QBO_CLIENT_SECRET` -- from the Intuit Developer portal
- `SLACK_BOT_TOKEN` / `SLACK_APP_TOKEN` -- from your Slack app settings
- `QBO_ENVIRONMENT` -- `sandbox` (default) or `production`

**`config/clients.yaml`** -- Maps company names to QBO realm IDs and Slack channels. Add a new block for each client company you manage.

**`config/slack-app-manifest.json`** -- Import this into Slack to create the app with all required scopes, slash commands, and shortcuts pre-configured.

See the `config/` directory for full examples.

## Docker (Optional)

Run the full stack (agent, Slack bot, n8n workflow engine) with Docker Compose:

```bash
docker-compose up -d
```

This starts three services: the QBO Copilot agent, the Slack bot in Socket Mode, and an n8n instance for workflow automation. Configuration is read from `config/.env`.

## FAQ

<details>
<summary>How much does it cost to run?</summary>

The main cost is the Anthropic API. A typical CPA firm making 50-100 queries per day will spend roughly $5-15/month on Claude API calls. QBO API access is free with your QuickBooks subscription. Slack is free for small workspaces or included in paid plans.
</details>

<details>
<summary>Is my data secure?</summary>

QBO Copilot runs on your own infrastructure. OAuth tokens are stored locally in `config/tokens/` and never leave your machine. All communication with QBO uses HTTPS. No data is sent to third parties beyond the Anthropic API (for LLM processing) and Intuit (for QBO operations). You control the deployment.
</details>

<details>
<summary>Which QBO editions are supported?</summary>

Any QuickBooks Online edition works: Simple Start, Essentials, Plus, and Advanced. The QBO sandbox (free through the Intuit Developer portal) is fully supported for testing.
</details>

<details>
<summary>Does it work on Windows or Linux?</summary>

The project is developed and tested on macOS but should run on any platform with Python 3.11+. Docker deployment works on Linux and Windows with WSL2. Some setup scripts may need minor adjustments for non-macOS environments.
</details>

<details>
<summary>Can I use a different LLM?</summary>

The agent layer in `agent/main.py` is built around the Anthropic SDK and Claude's tool-use capabilities. Swapping in a different LLM would require modifying the agent to use that provider's SDK and ensuring the model supports structured tool calling. The tool definitions in `qbo_tools.py` are provider-agnostic.
</details>

<details>
<summary>How do I add another QBO company?</summary>

Add a new entry to `config/clients.yaml` with the company name, QBO realm ID, and Slack channel. Then run the OAuth flow (`python qbo/oauth.py`) to authorize the new company. The token is saved automatically and the bot picks it up on the next request.
</details>

<details>
<summary>What Slack permissions are needed?</summary>

The app requires Socket Mode (for real-time events without a public URL) and the scopes defined in `config/slack-app-manifest.json`. Key scopes include `chat:write`, `commands`, `files:read`, `im:history`, `im:read`, `im:write`, and `app_mentions:read`. You need Slack workspace admin access to install the app.
</details>

<details>
<summary>How do I run the tests?</summary>

Tests run against the real QBO sandbox API (not mocked). Make sure your sandbox credentials are configured in `config/.env`, then run:

```bash
python -m pytest tests/ -v
```

You can also run a single test class or test method. See the `CLAUDE.md` file for detailed test commands.
</details>

## Contributing

Contributions are welcome. Please see [CONTRIBUTING.md](.github/CONTRIBUTING.md) for guidelines on submitting pull requests, reporting issues, and coding standards.

## License

[MIT](LICENSE)

## Built With

- [Claude by Anthropic](https://www.anthropic.com/claude) -- AI model powering the agent
- [slack-bolt](https://github.com/slackapi/bolt-python) -- Slack app framework for Python
- [QuickBooks Online API](https://developer.intuit.com/app/developer/qbo/docs/get-started) -- Intuit's REST API for accounting data
