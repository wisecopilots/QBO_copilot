# Messaging Your QBO Copilot

## What It Is

QBO Copilot is an AI assistant that lives inside Slack and connects to your QuickBooks Online account. You talk to it in plain English — no commands to memorize, no menus to navigate. An AI agent interprets what you need, calls the right QuickBooks API, and replies with the answer.

## How to Talk to the Bot

There are three ways to interact with QBO Copilot:

### 1. Direct Message (DM)

Open the bot's DM in Slack (find **QBO Copilot** in your sidebar under Apps). Type your question in the **main message box at the bottom** of the conversation — just like texting a coworker.

> "show me unpaid invoices"
> "create a customer called John Smith, john@example.com"
> "what's my total revenue this month?"

The DM is the best place for back-and-forth conversations, uploading receipt images, and longer queries.

### 2. Slash Command: `/qbo <your question>`

Type `/qbo` followed by your question in **any channel or DM**. This is the fastest way to fire off a quick query without switching to the bot's DM.

> `/qbo list expense accounts`
> `/qbo show purchases from last week`
> `/qbo create invoice for customer 123, web design $2500`

The response is only visible to you (ephemeral) unless the bot posts a follow-up.

### 3. @Mention in a Channel

Tag **@QBO Copilot** in any channel the bot has been added to:

> @QBO Copilot who are my top 5 vendors?

This is useful when you want the answer visible to your whole team.

## What You Can Ask

### Look Up Data
Ask for any data in your QuickBooks — accounts, customers, vendors, invoices, purchases, balances. Be as specific or general as you want.

- "show me expense accounts"
- "list unpaid invoices"
- "who are my vendors?"
- "what's the balance for customer Acme Corp?"
- "show purchases from last month"

### Create & Update Records
Create customers, vendors, invoices, and expenses by describing what you need.

- "create customer John Smith, john@example.com"
- "create invoice for customer 123, web design $2500"
- "add expense $50 to Office Supplies from Staples"
- "create vendor FedEx"
- "update customer John Smith, new email john.s@newco.com"

### Invoice Actions
Send, void, or manage invoices directly from Slack.

- "send invoice 1045 to client"
- "void invoice 1032"
- "show me overdue invoices"
- "delete invoice 1099"

### Receipt & Document Scanning
Upload a photo of a receipt, invoice, bill, or check directly in the DM. The bot will:

1. Show a dropdown asking you to classify the document type
2. You select the type (Expense Receipt, Invoice, Bill, Bank Statement, Other)
3. The bot scans the image with AI vision and extracts vendor, date, amount, line items, and all visible text
4. A review card appears with the extracted data and **Approve / Edit / Reject** buttons
5. You review and approve — approved items are queued for posting to QBO

Use `/qbo receipts` to view your scanning queue at any time.

### Multi-Company Support
If you manage multiple QBO companies, the bot asks which one to use when you first message it. Switch anytime with:

- "switch to Acme Corp"
- `/qbo switch to Acme Corp`

## When to Use Each Method

| Scenario | Best Method |
|---|---|
| Quick one-off lookup | `/qbo <question>` |
| Uploading receipts/images | DM the bot |
| Multi-step conversation | DM the bot |
| Team-visible answer | @QBO Copilot in a channel |
| Creating records | `/qbo` or DM |
| Checking receipt queue | `/qbo receipts` |
| Getting help | `/qbo help` |

## Tips

- **Be natural.** You don't need special syntax. "What invoices are overdue?" works just as well as "list unpaid invoices."
- **Be specific when creating.** Include the details upfront: "create invoice for customer 123, web design $2500, due in 30 days" saves a round trip.
- **Upload one image at a time** for receipt scanning — the bot processes each file individually.
- **Use the main message box**, not a thread reply, when uploading images. The scanning flow updates the original message in place.
- **Check `/qbo help`** anytime for a quick reference of example queries.
