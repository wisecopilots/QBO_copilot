# Feature Guide

QBO Copilot provides natural language access to QuickBooks Online through Slack. This guide covers all available features with usage examples.

---

## Natural Language Queries

The bot's primary interface is conversational. Send a DM or @mention the bot in a channel.

### Accounts

```
show me all accounts
```

```
list expense accounts
```

```
what's the balance of accounts receivable?
```

```
show bank accounts
```

### Customers

```
show customers
```

```
how many customers do I have?
```

```
list customer balances
```

### Vendors

```
show vendors
```

```
list all vendors
```

### Invoices

```
show unpaid invoices
```

```
list all invoices
```

```
how much is outstanding?
```

### Expenses / Purchases

```
show recent expenses
```

```
list purchases from January 2026
```

```
what did we spend last month?
```

### Custom Queries

For advanced users, you can use QBO Query Language directly:

```
run query: SELECT * FROM Account WHERE AccountType = 'Expense'
```

```
query: SELECT * FROM Invoice WHERE Balance > 0
```

```
query: SELECT * FROM Purchase WHERE TxnDate >= '2026-01-01' MAXRESULTS 10
```

---

## Creating Records

QBO Copilot can create invoices, customers, vendors, and expenses through natural language.

### Create a Customer

```
create a customer called Acme Corp with email billing@acme.com
```

```
add a new customer: Jane Smith, phone 555-0100
```

### Create a Vendor

```
create a vendor called Office Supplies Inc
```

```
add vendor Tech Services LLC with email invoices@techservices.com
```

### Create an Invoice

```
create an invoice for Acme Corp for $5000 for consulting services
```

```
create an invoice for customer 123, amount $2500, due 2026-03-15, memo "Q1 Retainer"
```

The bot will confirm the details before creating the invoice.

### Create an Expense

```
record a $150 expense to Office Supplies
```

```
create an expense: $2000 to vendor Tech Services for server maintenance
```

### Send an Invoice

```
send invoice #1042 to the customer
```

```
email invoice 1042 to billing@acme.com
```

### Void an Invoice

```
void invoice #1042
```

The bot will ask for confirmation before voiding.

---

## Slash Command: /qbo

The `/qbo` slash command provides quick access to common operations without @mentioning the bot.

### Subcommands

| Command | Description |
|---------|-------------|
| `/qbo help` | Show available commands |
| `/qbo accounts` | List accounts from Chart of Accounts |
| `/qbo customers` | List customers |
| `/qbo invoices` | List invoices |
| `/qbo expenses` | List recent expenses |
| `/qbo receipts` | Show the receipt scanning queue |
| `/qbo clients` | Show available QBO companies with switcher dropdown |

### Examples

```
/qbo invoices
```

Returns a formatted Block Kit card with invoice summaries, totals, and action buttons.

```
/qbo accounts
```

Shows accounts grouped by type (Bank, Expense, Income, etc.) with current balances.

---

## Receipt Scanning

Upload a receipt, invoice, or bill image directly to the bot's DM. QBO Copilot uses Claude Vision to extract structured data.

### How It Works

1. **Upload** an image (JPEG, PNG) to the bot's DM
2. A **classification dropdown** appears -- select the document type (Receipt, Invoice, Bill, Bank Statement)
3. The bot runs a **background scan** using Claude Vision OCR
4. A **review card** appears with extracted data: vendor, amount, date, line items, tax, confidence score
5. You can **approve** (post to QBO), **edit**, or **reject** the extraction

### Supported Document Types

- **Expense Receipt** -- Store receipts, restaurant bills, gas receipts
- **Invoice** -- Invoices received from vendors or sent to customers
- **Bill** -- Bills to be paid
- **Bank Statement** -- Monthly bank or credit card statements

See [receipt-scanning.md](receipt-scanning.md) for a deep dive.

---

## Home Tab Dashboard

Click on the bot's name in Slack, then go to the **Home** tab to see:

- **Account Summaries** -- Key balances at a glance
- **Recent Activity** -- Latest invoices, expenses, and transactions
- **Receipt Queue** -- Summary counts of scanned/pending/approved receipts
- **Client Onboarding Status** -- Progress for active onboarding clients

The Home tab refreshes each time you open it.

---

## Message Shortcuts

Right-click (or long-press on mobile) any message in Slack to access these shortcuts:

### Convert to Case

Converts a Slack message into a trackable case in the QBO Copilot system.

1. Right-click a message
2. Select **Convert to Case**
3. A modal appears to add a title, priority, and description
4. The case is created and linked to the original message

Cases can be tracked, assigned, and resolved through the bot.

### Request Documents

Request documents from a client directly from a conversation.

1. Right-click a message
2. Select **Request Documents**
3. A modal appears to specify document type, period, and due date
4. The request is tracked in the system and the client is notified

---

## Client Onboarding

QBO Copilot includes a structured onboarding workflow for new CPA clients, organized into 7 phases:

| Phase | Name | Description |
|-------|------|-------------|
| 0 | Intake | Initial client information gathering |
| 1 | Entity Setup | Business structure, year-end, contacts |
| 2 | Systems Inventory | Identify connected systems (Stripe, Shopify, Gusto, etc.) |
| 3 | Bank Accounts | Inventory bank and credit card accounts, connect feeds |
| 4 | Document Collection | Request and collect required documents |
| 5 | QBO Setup | Configure the QBO company (Chart of Accounts, settings) |
| 6 | Go Live | Final verification and handoff |

### Managing Onboarding

The onboarding system is accessible through the Slack bot:
- View onboarding progress for all clients
- Advance phases when milestones are complete
- Track blockers that prevent a phase from completing
- Request specific documents needed for each phase

---

## Multi-Company Switching

If you manage multiple QBO companies (see [setup-multi-tenant.md](setup-multi-tenant.md)):

### Switch via Natural Language

```
switch to Acme Corp
```

```
switch to Sandbox Company
```

### Switch via Slash Command

```
/qbo clients
```

This shows a dropdown menu with all configured companies. Select one to switch.

### Channel-Based Auto-Switching

When a Slack channel is mapped to a company in `config/clients.yaml`, all queries in that channel automatically target the correct company. No manual switching needed.

---

## Interactive Block Kit UI

Many responses include interactive elements:

- **Buttons** -- Approve/reject receipts, create invoices, advance onboarding phases
- **Dropdowns** -- Select companies, document types, expense categories
- **Modals** -- Multi-field forms for creating invoices, cases, and document requests
- **Overflow Menus** -- Additional actions on items (view details, edit, delete)

These interactive elements work in both DMs and channels.
