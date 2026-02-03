# CPA Copilot

AI-powered assistant for CPAs to manage QuickBooks Online clients through conversational interfaces.

## Overview

CPA Copilot is an AI agent that acts as a member of your Slack/Teams/WhatsApp community, helping CPAs:
- Query QuickBooks Online data across multiple client companies
- Execute accounting workflows through natural language
- Follow up with company employees via email/messaging
- Track and manage accounting tasks

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Messaging Channels                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │  Slack  │ │WhatsApp │ │  Teams  │ │ Discord │           │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘           │
│       └──────────┼──────────┼──────────┘                   │
│                  ▼                                          │
│         ┌───────────────┐                                   │
│         │  CPA Copilot  │ ◄── OpenClaw + Claude            │
│         │    (Agent)    │                                   │
│         └───────┬───────┘                                   │
│                 │                                           │
│    ┌────────────┼────────────┐                             │
│    ▼            ▼            ▼                             │
│ ┌──────┐  ┌──────────┐  ┌────────┐                        │
│ │ QBO  │  │   n8n    │  │ Email  │                        │
│ │ API  │  │Workflows │  │  SMTP  │                        │
│ └──────┘  └──────────┘  └────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
cpa-copilot/
├── agent/                    # OpenClaw/Claude brain
│   ├── main.py              # Agent entry point
│   ├── tools/               # Agent tools
│   │   ├── qbo_tools.py     # QBO query/action tools
│   │   ├── slack_tools.py   # Slack messaging
│   │   ├── email_tools.py   # Email sending
│   │   └── n8n_tools.py     # Complex workflow triggers
│   ├── prompts/             # System prompts
│   └── memory/              # Conversation state
├── integrations/            # Messaging channel adapters
│   ├── slack/               # Slack bot
│   ├── whatsapp/            # WhatsApp Business API
│   ├── teams/               # Microsoft Teams
│   └── discord/             # Discord bot
├── qbo/                     # QuickBooks Online client
│   ├── client.py            # API client
│   ├── oauth.py             # OAuth token management
│   └── multi_tenant.py      # Multi-company support
├── n8n/                     # Workflow engine
│   ├── docker-compose.yml   # n8n deployment
│   └── workflows/           # Exported workflows
├── config/                  # Configuration
│   ├── .env.example         # Environment template
│   └── clients.yaml         # Client company configs
└── docker-compose.yml       # Full stack deployment
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- Claude Pro/Max subscription (for OpenClaw)
- QuickBooks Online Developer account

### Setup

1. Clone the repository:
```bash
git clone https://github.com/YOUR_ORG/cpa-copilot.git
cd cpa-copilot
```

2. Copy and configure environment:
```bash
cp config/.env.example .env
# Edit .env with your credentials
```

3. Start services:
```bash
docker-compose up -d
```

4. Configure QBO OAuth:
```bash
python qbo/oauth.py setup
```

5. Add Slack bot to your workspace (see integrations/slack/README.md)

## Features

### QBO Integration
- Query any QBO entity (Accounts, Customers, Vendors, Invoices, etc.)
- Full QBO Query Language support
- Multi-tenant: Access multiple client companies with one setup
- Automatic OAuth token refresh

### Messaging
- **Slack**: Full bot integration with slash commands
- **WhatsApp**: Business API integration (application required)
- **Teams**: Coming soon
- **Discord**: Coming soon

### Workflows
- 42 pre-built QBO actions via n8n
- Custom workflow creation
- Scheduled tasks and reminders

## Development

### Running locally
```bash
# Install dependencies
pip install -r requirements.txt

# Run agent
python agent/main.py

# Run Slack bot
python integrations/slack/bot.py
```

### Testing with QBO Sandbox
The project is configured to use QBO Sandbox by default. Set `QBO_ENVIRONMENT=production` in `.env` for live data.

## License

MIT
