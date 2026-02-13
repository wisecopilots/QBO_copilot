# QBO Copilot Quickstart Guide

Get QBO Copilot running from scratch in about 30-45 minutes. By the end, you will have a Slack bot that can query your QuickBooks Online data using natural language.

## Prerequisites Checklist

Before you begin, make sure you have:

- [ ] **Python 3.11+** installed (`python3 --version` to check)
- [ ] **pip** package manager (`pip3 --version`)
- [ ] **git** installed (`git --version`)
- [ ] A **Slack workspace** where you have admin permissions
- [ ] An **Intuit Developer account** (free at [developer.intuit.com](https://developer.intuit.com))
- [ ] An **Anthropic API key** (from [console.anthropic.com](https://console.anthropic.com))

Optional:
- [ ] A **Google Cloud Platform** account (for Google Drive document vault)

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/qbo_copilot.git
cd qbo_copilot
```

## Step 2: Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `slack-bolt` and `slack-sdk` for the Slack integration
- `anthropic` for the Claude LLM agent
- `requests` for QBO API calls
- `python-dotenv` for environment variable management
- `pyyaml` for multi-tenant configuration
- `google-api-python-client` and `google-auth` for optional Google Drive support

## Step 4: Create Your Environment File

```bash
cp config/.env.example config/.env
```

Open `config/.env` in your editor and fill in the required values. You will populate these across the next few steps:

```bash
# QuickBooks Online (see docs/setup-qbo-oauth.md)
QBO_CLIENT_ID=your_client_id_here
QBO_CLIENT_SECRET=your_client_secret_here
QBO_ENVIRONMENT=sandbox

# Claude / Anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key

# Slack Bot (see docs/setup-slack-app.md)
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_SIGNING_SECRET=your_signing_secret
```

## Step 5: Set Up QuickBooks Online OAuth

Follow the detailed guide in [setup-qbo-oauth.md](setup-qbo-oauth.md). The short version:

1. Create an app at [developer.intuit.com](https://developer.intuit.com)
2. Copy Client ID and Client Secret into `config/.env`
3. Run the OAuth flow:

```bash
python3 qbo/oauth.py
```

This opens your browser, you authorize the QBO connection, and tokens are saved to `config/tokens/`.

4. Verify it worked:

```bash
python3 qbo/client.py accounts
```

You should see a JSON list of your Chart of Accounts.

## Step 6: Set Up the Slack App

Follow the detailed guide in [setup-slack-app.md](setup-slack-app.md). The short version:

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app from the manifest in `config/slack-app-manifest.json`
2. Copy the three tokens into `config/.env`:
   - **Bot Token** (`xoxb-...`) from OAuth & Permissions
   - **App-Level Token** (`xapp-...`) from Basic Information (generate with `connections:write` scope)
   - **Signing Secret** from Basic Information
3. Install the app to your workspace

## Step 7: Configure Your First Client Company

Edit `config/clients.yaml` to match your QBO company:

```yaml
clients:
  - name: "My Company"
    realm_id: "YOUR_REALM_ID"
    primary_contact: "you@example.com"
    slack_channel: "#qbo-general"
    metadata:
      environment: sandbox
```

The `realm_id` is printed when you complete the OAuth flow, and also stored in `config/tokens/default.json` as `realmId`.

## Step 8: Start the Bot

```bash
python3 integrations/slack/bot.py
```

You should see output like:

```
INFO:__main__:Agent initialized with 25 tools
INFO:slack_bolt.App:A]new session has been established
```

## Step 9: Your First Interaction

1. In Slack, invite the bot to a channel or open a DM with **QBO Copilot**
2. Type: `show me all accounts`
3. The bot will query your QBO company and return a formatted list

Try a few more:
- `list unpaid invoices`
- `show customers`
- `how many vendors do I have?`

## Step 10: Explore the CLI Agent (Optional)

You can also interact with QBO Copilot from the command line, without Slack:

```bash
python3 agent/main.py
```

This starts an interactive session where you can type natural language queries.

Or use the QBO client directly for specific operations:

```bash
python3 qbo/client.py customers
python3 qbo/client.py invoices --unpaid
python3 qbo/client.py query "SELECT * FROM Account WHERE AccountType = 'Expense'"
```

---

## Next Steps

Now that the bot is running, explore these guides:

- **[features.md](features.md)** -- Full feature guide with example commands
- **[setup-multi-tenant.md](setup-multi-tenant.md)** -- Add multiple QBO companies
- **[receipt-scanning.md](receipt-scanning.md)** -- Set up receipt/invoice scanning with Claude Vision
- **[setup-google-drive.md](setup-google-drive.md)** -- Optional Google Drive document vault
- **[architecture.md](architecture.md)** -- Understand the codebase structure
- **[troubleshooting.md](troubleshooting.md)** -- Common issues and fixes

## Running Tests

The test suite runs against the QBO sandbox API (integration tests, not mocked):

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run a specific test class
python3 -m pytest tests/test_qbo_tools.py::TestReadOperations -v

# Run a single test
python3 -m pytest tests/test_qbo_tools.py::TestReadOperations::test_get_accounts -v
```

## Docker Deployment

For production deployment with Docker:

```bash
docker-compose up -d
```

This starts all services (Slack bot, etc.) in the background.
