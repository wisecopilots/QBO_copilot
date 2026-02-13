# Multi-Company Setup

QBO Copilot supports managing multiple QuickBooks Online companies from a single Slack workspace. This is the core use case for CPAs who manage accounting for several clients.

## How It Works

The multi-tenant system has three components:

1. **`config/clients.yaml`** -- Defines which QBO companies are available and maps them to Slack channels
2. **`config/tokens/{realm_id}.json`** -- Stores OAuth tokens for each company (one file per company)
3. **`qbo/multi_tenant.py`** -- The `TenantManager` class that loads configs, routes requests, and caches QBO client instances

When a Slack message arrives, the bot determines which QBO company to query based on:
- The Slack channel the message was sent in (channel-based routing)
- The user's explicitly selected company (via dropdown or command)
- The default company (first entry in `clients.yaml`)

---

## Configuration File Format

The file `config/clients.yaml` defines all connected companies. Here is an annotated example:

```yaml
clients:
  # Production client
  - name: "Acme Corp"                    # Display name (used in UI and logs)
    realm_id: "4620816365178805"          # QBO Company ID (from OAuth)
    primary_contact: "john@acmecorp.com"  # Client's primary contact email
    slack_channel: "#qbo-acme"            # Slack channel mapped to this company
    metadata:
      environment: production             # "sandbox" or "production"
      notes: "Monthly close by 15th"      # Free-form notes

  # Another production client
  - name: "Beta Industries"
    realm_id: "4620816365246813"
    primary_contact: "jane@beta.com"
    slack_channel: "#qbo-beta"
    metadata:
      environment: production
      notes: "Quarterly reporting"

  # QBO Sandbox (for development and testing)
  - name: "Sandbox Company"
    realm_id: "4620816365213579"
    primary_contact: "sandbox@example.com"
    slack_channel: "#qbo-sandbox"
    metadata:
      environment: sandbox
      notes: "Intuit developer sandbox for testing"
```

### Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Display name for the company. Used in Slack messages and dropdowns. |
| `realm_id` | Yes | QBO Company ID. Found in token files or printed during OAuth. |
| `primary_contact` | No | Email of the client's main contact person. |
| `slack_channel` | No | Slack channel name (with `#`). Messages in this channel auto-route to this company. |
| `metadata.environment` | No | `sandbox` or `production`. Controls which QBO API endpoint is used. |
| `metadata.notes` | No | Free-form notes about the client. |

---

## Adding a New Company

### 1. Run OAuth for the New Company

```bash
python3 qbo/oauth.py
```

When the browser opens, sign in and select the new QBO company. This saves tokens to:
- `config/tokens/default.json` (overwritten each time)
- `config/tokens/{realm_id}.json` (unique per company)

Note the `realm_id` printed in the success message.

### 2. Add an Entry to clients.yaml

```yaml
clients:
  # ... existing entries ...

  - name: "New Client LLC"
    realm_id: "1234567890123456"    # from OAuth output
    primary_contact: "owner@newclient.com"
    slack_channel: "#qbo-newclient"
    metadata:
      environment: production
```

### 3. Create the Slack Channel

In Slack, create the channel specified in `slack_channel` (e.g., `#qbo-newclient`) and invite the bot:

```
/invite @QBO Copilot
```

### 4. Restart the Bot

```bash
# Stop the bot (Ctrl+C) and restart
python3 integrations/slack/bot.py
```

The new company is now available.

---

## Channel-Based Routing

When a message is sent in a Slack channel that matches a `slack_channel` in `clients.yaml`, the bot automatically routes QBO queries to that company.

For example:
- A message in `#qbo-acme` queries Acme Corp's QBO data
- A message in `#qbo-beta` queries Beta Industries' QBO data
- A message in `#qbo-sandbox` queries the sandbox company

This means each client can have their own dedicated channel where all queries automatically target the right company.

## Switching Companies Manually

Users can also switch companies explicitly, which is useful in DMs or shared channels:

### In Natural Language

```
Switch to Acme Corp
```

```
Switch to client 4620816365178805
```

The agent understands both company names and realm IDs.

### Via the /qbo Command

```
/qbo clients
```

This shows a dropdown with all available companies. Selecting one switches the active company for your session.

### How State is Tracked

- Each Slack user has an independently tracked "current company"
- The selection is stored in memory (resets when the bot restarts)
- Channel-based routing takes priority when a channel is mapped to a specific company

---

## Per-Client Token Storage

Each company's OAuth tokens are stored separately:

```
config/tokens/
  default.json              # Last company authorized (convenience)
  4620816365178805.json     # Acme Corp tokens
  4620816365246813.json     # Beta Industries tokens
  4620816365213579.json     # Sandbox Company tokens
```

Token files are auto-managed:
- Created during the OAuth flow
- Updated automatically when tokens are refreshed (on 401 response)
- Each file contains `access_token`, `refresh_token`, and `realmId`

---

## Listing Connected Companies

### From the CLI

```bash
python3 qbo/multi_tenant.py
```

Output:

```
Configured QBO Clients:
==================================================

  Acme Corp
    Realm ID: 4620816365178805
    Contact: john@acmecorp.com
    Slack: #qbo-acme

  Beta Industries
    Realm ID: 4620816365246813
    Contact: jane@beta.com
    Slack: #qbo-beta
```

### From Slack

```
/qbo clients
```

Or in natural language:

```
list all clients
```

---

## Programmatic Usage

```python
from qbo.multi_tenant import TenantManager

manager = TenantManager()

# List all companies
for client in manager.list_clients():
    print(f"{client.name} ({client.realm_id})")

# Get a QBO client for a specific company
qbo = manager.get_client("Acme Corp")
accounts = qbo.get_accounts()

# Find company by Slack channel
client = manager.find_client_by_channel("#qbo-acme")

# Add a new company programmatically
manager.add_client(
    name="New Corp",
    realm_id="1234567890",
    primary_contact="info@newcorp.com",
    slack_channel="#qbo-newcorp"
)
```

---

## Troubleshooting

### "Client not found" when switching

- Check that the company name matches exactly (case-insensitive) or use the realm_id
- Verify the entry exists in `config/clients.yaml`

### Wrong company being queried

- In a mapped channel, the channel mapping always takes priority
- In DMs, the bot uses the last company you switched to, or the first in the config
- Use `/qbo clients` to verify which company is active

### Token errors for one company but not others

- Each company has its own token file
- Re-run `python3 qbo/oauth.py` and select the affected company to refresh its tokens
