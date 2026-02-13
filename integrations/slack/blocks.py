"""
Slack Block Kit message builders for QBO Copilot

Builds rich interactive messages with buttons, dropdowns, and modals
for QuickBooks Online accounting workflows and client onboarding.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime


def format_currency(amount) -> str:
    """Format a number as currency"""
    try:
        return f"${float(amount):,.2f}"
    except (ValueError, TypeError):
        return "$0.00"


# ---------------------------------------------------------------------------
# Help / Capabilities
# ---------------------------------------------------------------------------

def _build_help_blocks() -> List[Dict]:
    """Build help message showing all QBO Copilot capabilities"""
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "QBO Copilot — Help"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*How it works:* Just talk to the bot in plain English — either DM it "
                    "or use `/qbo <your question>`. An AI agent reads your request, picks the "
                    "right QuickBooks API calls, and replies with the answer.\n\n"
                    "_You don't need to memorize commands. Just ask for what you need._"
                ),
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*:mag: Look Up Data*\n"
                    "`/qbo show me expense accounts`\n"
                    "`/qbo list unpaid invoices`\n"
                    "`/qbo who are my vendors?`\n"
                    "`/qbo what's the balance for customer Acme Corp?`\n"
                    "`/qbo show purchases from last month`"
                ),
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*:pencil2: Create & Update*\n"
                    "`/qbo create customer John Smith, john@example.com`\n"
                    "`/qbo create invoice for customer 123, web design $2500`\n"
                    "`/qbo add expense $50 to Office Supplies from Staples`\n"
                    "`/qbo create vendor FedEx`"
                ),
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*:email: Invoice Actions*\n"
                    "`/qbo send invoice 1045 to client`\n"
                    "`/qbo void invoice 1032`\n"
                    "`/qbo show me overdue invoices`"
                ),
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*:receipt: Receipt Scanning*\n"
                    "Upload an image in this DM — the bot will ask you to classify it "
                    "(receipt, invoice, bill, etc.), then scan it with AI vision to extract "
                    "vendor, amount, date, and line items. Review and approve the results.\n"
                    "`/qbo receipts` — view the receipt queue"
                ),
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*:office: Multi-Company*\n"
                    "If you manage multiple QBO companies, the bot will ask you to pick one "
                    "when you first message it. You can switch anytime:\n"
                    "`/qbo switch to Acme Corp`"
                ),
            },
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": (
                    "*Slash command:* `/qbo <question>` | "
                    "*DM:* message this bot directly | "
                    "*Mention:* @QBO Copilot in a channel | "
                    "`/qbo help` for this message"
                ),
            }],
        },
    ]


def build_home_capabilities_blocks() -> List[Dict]:
    """Build capabilities summary section for the Home tab"""
    return [
        {"type": "divider"},
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "What Can I Do?"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "Talk to me in plain English — DM me or use `/qbo <question>`."
                ),
            },
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": (
                        "*:mag: Query QBO*\n"
                        "Accounts, customers, vendors,\n"
                        "invoices, expenses, balances"
                    ),
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        "*:pencil2: Create & Edit*\n"
                        "Customers, vendors, invoices,\n"
                        "expenses — just ask"
                    ),
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        "*:receipt: Scan Receipts*\n"
                        "Upload an image in this DM.\n"
                        "AI extracts vendor, amount, date"
                    ),
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        "*:email: Invoice Actions*\n"
                        "Send, void, or delete invoices.\n"
                        "Track unpaid & overdue"
                    ),
                },
            ],
        },
        {
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": "Type `/qbo help` for examples and detailed usage.",
            }],
        },
    ]


# ---------------------------------------------------------------------------
# Account blocks
# ---------------------------------------------------------------------------

def build_account_blocks(accounts: List[Dict], title: str = "Accounts") -> List[Dict]:
    """Build Block Kit blocks for an account list"""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{title} ({len(accounts)})"}
        }
    ]

    for acc in accounts[:15]:
        name = acc.get("Name", "Unknown")
        acct_type = acc.get("AccountType", "")
        balance = format_currency(acc.get("CurrentBalance", 0))

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{name}*\n{acct_type} \u2022 Balance: {balance}"
            }
        })

    if len(accounts) > 15:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"_...and {len(accounts) - 15} more_"}]
        })

    return blocks


# ---------------------------------------------------------------------------
# Invoice blocks
# ---------------------------------------------------------------------------

def build_invoice_blocks(invoices: List[Dict], title: str = "Invoices") -> List[Dict]:
    """Build Block Kit blocks for invoices with action buttons"""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{title} ({len(invoices)})"}
        }
    ]

    for inv in invoices[:10]:
        inv_id = inv.get("Id", "")
        doc_num = inv.get("DocNumber", "N/A")
        customer = inv.get("CustomerRef", {}).get("name", "Unknown")
        total = format_currency(inv.get("TotalAmt", 0))
        balance = format_currency(inv.get("Balance", 0))
        date = inv.get("TxnDate", "N/A")
        sync_token = inv.get("SyncToken", "0")

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Invoice #{doc_num}* \u2014 {customer}\nDate: {date} \u2022 Total: {total} \u2022 Balance: {balance}"
            },
            "accessory": {
                "type": "overflow",
                "action_id": f"invoice_actions_{inv_id}",
                "options": [
                    {
                        "text": {"type": "plain_text", "text": "View Details"},
                        "value": f"view|{inv_id}|{sync_token}"
                    },
                    {
                        "text": {"type": "plain_text", "text": "Send to Customer"},
                        "value": f"send|{inv_id}|{sync_token}"
                    },
                    {
                        "text": {"type": "plain_text", "text": "Void Invoice"},
                        "value": f"void|{inv_id}|{sync_token}"
                    }
                ]
            }
        })
        blocks.append({"type": "divider"})

    if len(invoices) > 10:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"_...and {len(invoices) - 10} more_"}]
        })

    return blocks


# ---------------------------------------------------------------------------
# Customer blocks
# ---------------------------------------------------------------------------

def build_customer_blocks(customers: List[Dict], title: str = "Customers") -> List[Dict]:
    """Build Block Kit blocks for customer list"""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{title} ({len(customers)})"}
        }
    ]

    for cust in customers[:15]:
        name = cust.get("DisplayName", "Unknown")
        balance = format_currency(cust.get("Balance", 0))
        email = cust.get("PrimaryEmailAddr", {}).get("Address", "")
        phone = cust.get("PrimaryPhone", {}).get("FreeFormNumber", "")

        detail_parts = []
        if email:
            detail_parts.append(email)
        if phone:
            detail_parts.append(phone)
        detail = " \u2022 ".join(detail_parts) if detail_parts else "No contact info"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{name}* \u2014 Balance: {balance}\n{detail}"
            }
        })

    if len(customers) > 15:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"_...and {len(customers) - 15} more_"}]
        })

    return blocks


# ---------------------------------------------------------------------------
# Expense blocks with categorization
# ---------------------------------------------------------------------------

def build_expense_blocks(
    expenses: List[Dict],
    account_options: Optional[List[Dict]] = None,
    title: str = "Expenses"
) -> List[Dict]:
    """Build Block Kit blocks for expenses, optionally with category dropdowns"""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{title} ({len(expenses)})"}
        }
    ]

    for exp in expenses[:10]:
        exp_id = exp.get("Id", "")
        vendor = exp.get("EntityRef", {}).get("name", "Unknown")
        total = format_currency(exp.get("TotalAmt", 0))
        date = exp.get("TxnDate", "N/A")
        account_name = ""
        lines = exp.get("Line", [])
        if lines:
            account_ref = lines[0].get("AccountBasedExpenseLineDetail", {}).get("AccountRef", {})
            account_name = account_ref.get("name", "Uncategorized")

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{vendor}* \u2014 {total}\n{date} \u2022 {account_name}"
            }
        })

        if account_options and account_name == "Uncategorized":
            blocks.append({
                "type": "actions",
                "elements": [{
                    "type": "static_select",
                    "placeholder": {"type": "plain_text", "text": "Categorize..."},
                    "action_id": f"categorize_expense_{exp_id}",
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": opt["Name"][:75]},
                            "value": opt["Id"]
                        }
                        for opt in account_options[:20]
                    ]
                }]
            })

        blocks.append({"type": "divider"})

    if len(expenses) > 10:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"_...and {len(expenses) - 10} more_"}]
        })

    return blocks


# ---------------------------------------------------------------------------
# Dashboard blocks (Home tab)
# ---------------------------------------------------------------------------

def build_dashboard_blocks(
    total_receivable: float = 0,
    total_payable: float = 0,
    cash_balance: float = 0,
    overdue_count: int = 0,
    recent_expenses: Optional[List[Dict]] = None
) -> List[Dict]:
    """Build Block Kit blocks for the Home tab dashboard"""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "QBO Copilot Dashboard"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Accounts Receivable*\n{format_currency(total_receivable)}"},
                {"type": "mrkdwn", "text": f"*Accounts Payable*\n{format_currency(total_payable)}"},
                {"type": "mrkdwn", "text": f"*Cash Balance*\n{format_currency(cash_balance)}"},
                {"type": "mrkdwn", "text": f"*Overdue Invoices*\n{overdue_count}"}
            ]
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Quick Actions*"}
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Create Invoice"},
                    "action_id": "create_invoice_btn",
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Add Expense"},
                    "action_id": "create_expense_btn"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Unpaid Invoices"},
                    "action_id": "view_unpaid_btn"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Recent Expenses"},
                    "action_id": "view_expenses_btn"
                }
            ]
        }
    ]

    if recent_expenses:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Recent Expenses*"}
        })
        for exp in recent_expenses[:5]:
            vendor = exp.get("EntityRef", {}).get("name", "Unknown")
            total = format_currency(exp.get("TotalAmt", 0))
            date = exp.get("TxnDate", "N/A")
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"{date} \u2022 *{vendor}* \u2022 {total}"}]
            })

    return blocks


# ---------------------------------------------------------------------------
# Modal builders
# ---------------------------------------------------------------------------

def build_create_invoice_modal(customers: List[Dict]) -> Dict:
    """Build modal for creating an invoice"""
    customer_options = [
        {
            "text": {"type": "plain_text", "text": c.get("DisplayName", "Unknown")[:75]},
            "value": c.get("Id", "")
        }
        for c in customers[:100]
    ]

    return {
        "type": "modal",
        "callback_id": "create_invoice_modal",
        "title": {"type": "plain_text", "text": "Create Invoice"},
        "submit": {"type": "plain_text", "text": "Create"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "customer_block",
                "label": {"type": "plain_text", "text": "Customer"},
                "element": {
                    "type": "static_select",
                    "action_id": "customer_select",
                    "placeholder": {"type": "plain_text", "text": "Select a customer"},
                    "options": customer_options
                }
            },
            {
                "type": "input",
                "block_id": "description_block",
                "label": {"type": "plain_text", "text": "Description"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "description_input",
                    "placeholder": {"type": "plain_text", "text": "Service or product description"}
                }
            },
            {
                "type": "input",
                "block_id": "amount_block",
                "label": {"type": "plain_text", "text": "Amount"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "amount_input",
                    "placeholder": {"type": "plain_text", "text": "0.00"}
                }
            },
            {
                "type": "input",
                "block_id": "due_date_block",
                "label": {"type": "plain_text", "text": "Due Date"},
                "element": {
                    "type": "datepicker",
                    "action_id": "due_date_input"
                },
                "optional": True
            }
        ]
    }


def build_create_customer_modal() -> Dict:
    """Build modal for creating a customer"""
    return {
        "type": "modal",
        "callback_id": "create_customer_modal",
        "title": {"type": "plain_text", "text": "Create Customer"},
        "submit": {"type": "plain_text", "text": "Create"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "name_block",
                "label": {"type": "plain_text", "text": "Display Name"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "name_input",
                    "placeholder": {"type": "plain_text", "text": "Customer name"}
                }
            },
            {
                "type": "input",
                "block_id": "email_block",
                "label": {"type": "plain_text", "text": "Email"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "email_input",
                    "placeholder": {"type": "plain_text", "text": "email@example.com"}
                },
                "optional": True
            },
            {
                "type": "input",
                "block_id": "phone_block",
                "label": {"type": "plain_text", "text": "Phone"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "phone_input",
                    "placeholder": {"type": "plain_text", "text": "(555) 555-5555"}
                },
                "optional": True
            },
            {
                "type": "input",
                "block_id": "company_block",
                "label": {"type": "plain_text", "text": "Company Name"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "company_input",
                    "placeholder": {"type": "plain_text", "text": "Company name"}
                },
                "optional": True
            }
        ]
    }


def build_confirm_modal(action: str, entity: str, detail: str) -> Dict:
    """Build a generic confirmation modal"""
    return {
        "type": "modal",
        "callback_id": f"confirm_{action}_modal",
        "title": {"type": "plain_text", "text": f"Confirm {action.title()}"},
        "submit": {"type": "plain_text", "text": f"Yes, {action.title()}"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "private_metadata": detail,
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Are you sure you want to *{action}* {entity}?"
                }
            }
        ]
    }


# ---------------------------------------------------------------------------
# Onboarding Dashboard Blocks
# ---------------------------------------------------------------------------

def build_progress_bar(percentage: int, width: int = 10) -> str:
    """Build a text-based progress bar"""
    filled = int((percentage / 100) * width)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    return f"[{bar}] {percentage}%"


def build_onboarding_dashboard_blocks(
    client: Dict[str, Any],
    progress: Dict[str, Any],
    waiting_on_client: Dict[str, List],
    waiting_on_cpa: Dict[str, List]
) -> List[Dict]:
    """
    Build onboarding dashboard blocks for the Home tab.

    Args:
        client: Client record dict
        progress: Progress dict from OnboardingStateMachine.get_overall_progress()
        waiting_on_client: Items waiting on client response
        waiting_on_cpa: Items waiting on CPA action
    """
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Onboarding: {client.get('display_name', 'Client')}"}
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Overall Progress:* {build_progress_bar(progress.get('overall_percentage', 0))}"
            }
        }
    ]

    # Phase checklist
    phases = progress.get('phases', [])
    phase_lines = []
    for p in phases:
        status = p.get('status', 'pending')
        if status == 'completed':
            emoji = "✅"
        elif status == 'in_progress':
            emoji = "🔄"
        elif status == 'blocked':
            emoji = "🚫"
        else:
            emoji = "⬜"

        phase_lines.append(f"{emoji} *Phase {p['phase']}:* {p.get('name', '')} ({p.get('completion_pct', 0)}%)")

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "\n".join(phase_lines)
        }
    })

    # Current phase details
    current_phase = progress.get('current_phase', 0)
    if current_phase < 7:
        current_phase_info = next((p for p in phases if p['phase'] == current_phase), None)
        if current_phase_info:
            items = current_phase_info.get('items', [])
            if items:
                item_lines = []
                for item in items:
                    check = "✓" if item.get('complete') else "○"
                    item_lines.append(f"  {check} {item.get('name', '')}")

                blocks.append({
                    "type": "context",
                    "elements": [{
                        "type": "mrkdwn",
                        "text": "*Current phase items:*\n" + "\n".join(item_lines)
                    }]
                })

            blockers = current_phase_info.get('blockers', [])
            if blockers:
                blocks.append({
                    "type": "context",
                    "elements": [{
                        "type": "mrkdwn",
                        "text": "⚠️ *Blockers:* " + ", ".join(blockers)
                    }]
                })

    blocks.append({"type": "divider"})

    # Onboarding action buttons
    blocks.append({
        "type": "actions",
        "elements": _get_phase_action_buttons(client.get('id'), current_phase)
    })

    # Waiting queues
    client_items = (
        len(waiting_on_client.get('doc_requests', [])) +
        len(waiting_on_client.get('cases', []))
    )
    cpa_items = (
        len(waiting_on_cpa.get('doc_requests', [])) +
        len(waiting_on_cpa.get('cases', []))
    )

    if client_items > 0 or cpa_items > 0:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Waiting Queues*"}
        })
        blocks.append({
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Waiting on Client:* {client_items}"},
                {"type": "mrkdwn", "text": f"*Waiting on CPA:* {cpa_items}"}
            ]
        })

    return blocks


def _get_phase_action_buttons(client_id: str, current_phase: int) -> List[Dict]:
    """Get action buttons appropriate for the current phase"""
    import json

    buttons = []

    if current_phase == 0:
        buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "Complete Client Info"},
            "action_id": "edit_client_btn",
            "value": client_id
        })
    elif current_phase == 1:
        buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "Add Contact"},
            "action_id": "add_contact_btn",
            "value": client_id,
            "style": "primary"
        })
    elif current_phase == 2:
        buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "Verify QBO Connection"},
            "action_id": "verify_qbo_btn",
            "value": client_id,
            "style": "primary"
        })
    elif current_phase == 3:
        buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "Add Bank Account"},
            "action_id": "add_bank_btn",
            "value": client_id,
            "style": "primary"
        })
    elif current_phase == 4:
        buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "Request Documents"},
            "action_id": "request_docs_btn",
            "value": client_id,
            "style": "primary"
        })
    elif current_phase == 5:
        buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "Add System"},
            "action_id": "add_system_btn",
            "value": client_id,
            "style": "primary"
        })
    elif current_phase == 6:
        buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "Set Operating Rules"},
            "action_id": "set_rules_btn",
            "value": client_id,
            "style": "primary"
        })

    # Always show advance button if not at the end
    if current_phase < 6:
        buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "Advance Phase →"},
            "action_id": "advance_phase_btn",
            "value": client_id
        })

    return buttons[:4]  # Slack limits to 5 elements per actions block


def build_qbo_client_selector_message(clients: List[Dict], selected_realm: Optional[str] = None) -> List[Dict]:
    """Build an inline QBO client selector for DM conversations.

    Args:
        clients: List of dicts with 'name' and 'realm_id' keys (from TenantManager)
        selected_realm: Currently selected realm_id, if any
    """
    if not clients:
        return [{
            "type": "section",
            "text": {"type": "mrkdwn", "text": "No QBO companies configured."}
        }]

    options = [
        {
            "text": {"type": "plain_text", "text": c["name"][:75]},
            "value": c["realm_id"]
        }
        for c in clients
    ]

    selector = {
        "type": "section",
        "block_id": "qbo_client_selector_block",
        "text": {"type": "mrkdwn", "text": "*Select a QBO company to query:*"},
        "accessory": {
            "type": "static_select",
            "placeholder": {"type": "plain_text", "text": "Choose company..."},
            "action_id": "select_qbo_client",
            "options": options[:100]
        }
    }

    if selected_realm:
        initial = next((o for o in options if o["value"] == selected_realm), None)
        if initial:
            selector["accessory"]["initial_option"] = initial

    return [selector]


def build_client_selector_blocks(clients: List[Dict], selected_id: Optional[str] = None) -> List[Dict]:
    """Build client selector dropdown"""
    if not clients:
        return [{
            "type": "section",
            "text": {"type": "mrkdwn", "text": "No clients found. Create a new client to get started."},
            "accessory": {
                "type": "button",
                "text": {"type": "plain_text", "text": "New Client"},
                "action_id": "new_client_btn",
                "style": "primary"
            }
        }]

    options = [
        {
            "text": {"type": "plain_text", "text": c.get('display_name', c.get('legal_name', 'Unknown'))[:75]},
            "value": c.get('id', '')
        }
        for c in clients
    ]

    initial_option = None
    if selected_id:
        initial_option = next((o for o in options if o['value'] == selected_id), None)

    selector = {
        "type": "section",
        "text": {"type": "mrkdwn", "text": "*Select Client:*"},
        "accessory": {
            "type": "static_select",
            "placeholder": {"type": "plain_text", "text": "Choose a client"},
            "action_id": "select_client",
            "options": options[:100]
        }
    }

    if initial_option:
        selector["accessory"]["initial_option"] = initial_option

    return [
        selector,
        {
            "type": "actions",
            "elements": [{
                "type": "button",
                "text": {"type": "plain_text", "text": "+ New Client"},
                "action_id": "new_client_btn"
            }]
        }
    ]


def build_waiting_queues_blocks(
    waiting_on_client: Dict[str, List],
    waiting_on_cpa: Dict[str, List]
) -> List[Dict]:
    """Build waiting queue summary blocks"""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Work Queues"}
        }
    ]

    # Waiting on client
    client_docs = waiting_on_client.get('doc_requests', [])
    client_cases = waiting_on_client.get('cases', [])

    if client_docs or client_cases:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Waiting on Client*"}
        })

        for doc in client_docs[:5]:
            client_name = doc.get('client_name', 'Unknown')
            doc_type = doc.get('doc_type', 'Document')
            due = doc.get('due_date', 'No due date')
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"📄 *{client_name}:* {doc_type} (due: {due})"}]
            })

        for case in client_cases[:5]:
            client_name = case.get('client_name', 'Unknown')
            title = case.get('title', 'Case')
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"📋 *{client_name}:* {title}"}]
            })

    # Waiting on CPA
    cpa_docs = waiting_on_cpa.get('doc_requests', [])
    cpa_cases = waiting_on_cpa.get('cases', [])

    if cpa_docs or cpa_cases:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Waiting on CPA*"}
        })

        for doc in cpa_docs[:5]:
            client_name = doc.get('client_name', 'Unknown')
            doc_type = doc.get('doc_type', 'Document')
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"📄 *{client_name}:* {doc_type} - needs review"}]
            })

        for case in cpa_cases[:5]:
            client_name = case.get('client_name', 'Unknown')
            title = case.get('title', 'Case')
            priority = case.get('priority', 'normal')
            priority_emoji = "🔴" if priority == 'urgent' else "🟡" if priority == 'high' else ""
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"📋 {priority_emoji} *{client_name}:* {title}"}]
            })

    if not (client_docs or client_cases or cpa_docs or cpa_cases):
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_All caught up! No pending items._"}
        })

    return blocks


def build_doc_requests_blocks(requests: List[Dict], title: str = "Document Requests") -> List[Dict]:
    """Build document requests list"""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{title} ({len(requests)})"}
        }
    ]

    status_emoji = {
        'requested': '⏳',
        'received': '📥',
        'reviewed': '👁️',
        'filed': '✅'
    }

    for req in requests[:15]:
        doc_type = req.get('doc_type', 'Document')
        period = req.get('period', '')
        status = req.get('status', 'requested')
        emoji = status_emoji.get(status, '📄')
        due = req.get('due_date', '')

        text = f"{emoji} *{doc_type}*"
        if period:
            text += f" ({period})"
        text += f"\nStatus: {status}"
        if due and status == 'requested':
            text += f" | Due: {due}"

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": text}
        })

    if len(requests) > 15:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"_...and {len(requests) - 15} more_"}]
        })

    return blocks


# ---------------------------------------------------------------------------
# Onboarding Modals
# ---------------------------------------------------------------------------

def build_new_client_modal() -> Dict:
    """Build modal for creating a new client"""
    entity_types = [
        {"text": {"type": "plain_text", "text": "LLC"}, "value": "LLC"},
        {"text": {"type": "plain_text", "text": "S-Corp"}, "value": "S-Corp"},
        {"text": {"type": "plain_text", "text": "C-Corp"}, "value": "C-Corp"},
        {"text": {"type": "plain_text", "text": "Sole Proprietorship"}, "value": "Sole Prop"},
        {"text": {"type": "plain_text", "text": "Partnership"}, "value": "Partnership"},
    ]

    return {
        "type": "modal",
        "callback_id": "new_client_modal",
        "title": {"type": "plain_text", "text": "New Client"},
        "submit": {"type": "plain_text", "text": "Create"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "legal_name_block",
                "label": {"type": "plain_text", "text": "Legal Name"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "legal_name_input",
                    "placeholder": {"type": "plain_text", "text": "Full legal business name"}
                }
            },
            {
                "type": "input",
                "block_id": "display_name_block",
                "label": {"type": "plain_text", "text": "Display Name"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "display_name_input",
                    "placeholder": {"type": "plain_text", "text": "Short name for display"}
                },
                "optional": True
            },
            {
                "type": "input",
                "block_id": "entity_type_block",
                "label": {"type": "plain_text", "text": "Entity Type"},
                "element": {
                    "type": "static_select",
                    "action_id": "entity_type_select",
                    "placeholder": {"type": "plain_text", "text": "Select entity type"},
                    "options": entity_types
                }
            },
            {
                "type": "input",
                "block_id": "year_end_block",
                "label": {"type": "plain_text", "text": "Fiscal Year End"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "year_end_input",
                    "placeholder": {"type": "plain_text", "text": "MM-DD (e.g., 12-31)"}
                },
                "optional": True
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Primary Contact*"}
            },
            {
                "type": "input",
                "block_id": "contact_name_block",
                "label": {"type": "plain_text", "text": "Contact Name"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "contact_name_input",
                    "placeholder": {"type": "plain_text", "text": "Primary contact name"}
                },
                "optional": True
            },
            {
                "type": "input",
                "block_id": "contact_email_block",
                "label": {"type": "plain_text", "text": "Contact Email"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "contact_email_input",
                    "placeholder": {"type": "plain_text", "text": "email@company.com"}
                },
                "optional": True
            }
        ]
    }


def build_add_contact_modal(client_id: str) -> Dict:
    """Build modal for adding a contact"""
    import json

    role_options = [
        {"text": {"type": "plain_text", "text": "Owner"}, "value": "owner"},
        {"text": {"type": "plain_text", "text": "Operator"}, "value": "operator"},
        {"text": {"type": "plain_text", "text": "Approver"}, "value": "approver"},
        {"text": {"type": "plain_text", "text": "Payroll Contact"}, "value": "payroll_contact"},
        {"text": {"type": "plain_text", "text": "Bookkeeper"}, "value": "bookkeeper"},
    ]

    return {
        "type": "modal",
        "callback_id": "add_contact_modal",
        "private_metadata": json.dumps({"client_id": client_id}),
        "title": {"type": "plain_text", "text": "Add Contact"},
        "submit": {"type": "plain_text", "text": "Add"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "name_block",
                "label": {"type": "plain_text", "text": "Name"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "name_input",
                    "placeholder": {"type": "plain_text", "text": "Contact name"}
                }
            },
            {
                "type": "input",
                "block_id": "email_block",
                "label": {"type": "plain_text", "text": "Email"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "email_input",
                    "placeholder": {"type": "plain_text", "text": "email@company.com"}
                },
                "optional": True
            },
            {
                "type": "input",
                "block_id": "phone_block",
                "label": {"type": "plain_text", "text": "Phone"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "phone_input",
                    "placeholder": {"type": "plain_text", "text": "(555) 555-5555"}
                },
                "optional": True
            },
            {
                "type": "input",
                "block_id": "role_block",
                "label": {"type": "plain_text", "text": "Role"},
                "element": {
                    "type": "static_select",
                    "action_id": "role_select",
                    "placeholder": {"type": "plain_text", "text": "Select role"},
                    "options": role_options
                }
            },
            {
                "type": "input",
                "block_id": "threshold_block",
                "label": {"type": "plain_text", "text": "Approval Threshold ($)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "threshold_input",
                    "placeholder": {"type": "plain_text", "text": "Max amount they can approve"}
                },
                "optional": True
            },
            {
                "type": "input",
                "block_id": "primary_block",
                "label": {"type": "plain_text", "text": "Primary Contact?"},
                "element": {
                    "type": "checkboxes",
                    "action_id": "primary_check",
                    "options": [{
                        "text": {"type": "plain_text", "text": "This is the primary contact"},
                        "value": "is_primary"
                    }]
                },
                "optional": True
            }
        ]
    }


def build_add_bank_modal(client_id: str) -> Dict:
    """Build modal for adding a bank account"""
    import json

    account_types = [
        {"text": {"type": "plain_text", "text": "Checking"}, "value": "checking"},
        {"text": {"type": "plain_text", "text": "Savings"}, "value": "savings"},
        {"text": {"type": "plain_text", "text": "Credit Card"}, "value": "credit_card"},
        {"text": {"type": "plain_text", "text": "Line of Credit"}, "value": "loc"},
    ]

    volume_options = [
        {"text": {"type": "plain_text", "text": "Low (<50 txns/month)"}, "value": "low"},
        {"text": {"type": "plain_text", "text": "Medium (50-200 txns/month)"}, "value": "medium"},
        {"text": {"type": "plain_text", "text": "High (200+ txns/month)"}, "value": "high"},
    ]

    return {
        "type": "modal",
        "callback_id": "add_bank_modal",
        "private_metadata": json.dumps({"client_id": client_id}),
        "title": {"type": "plain_text", "text": "Add Bank Account"},
        "submit": {"type": "plain_text", "text": "Add"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "institution_block",
                "label": {"type": "plain_text", "text": "Institution"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "institution_input",
                    "placeholder": {"type": "plain_text", "text": "Bank name"}
                }
            },
            {
                "type": "input",
                "block_id": "type_block",
                "label": {"type": "plain_text", "text": "Account Type"},
                "element": {
                    "type": "static_select",
                    "action_id": "type_select",
                    "placeholder": {"type": "plain_text", "text": "Select type"},
                    "options": account_types
                }
            },
            {
                "type": "input",
                "block_id": "last_four_block",
                "label": {"type": "plain_text", "text": "Last 4 Digits"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "last_four_input",
                    "placeholder": {"type": "plain_text", "text": "1234"},
                    "max_length": 4
                },
                "optional": True
            },
            {
                "type": "input",
                "block_id": "nickname_block",
                "label": {"type": "plain_text", "text": "Nickname"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "nickname_input",
                    "placeholder": {"type": "plain_text", "text": "Operating account, Payroll, etc."}
                },
                "optional": True
            },
            {
                "type": "input",
                "block_id": "volume_block",
                "label": {"type": "plain_text", "text": "Transaction Volume"},
                "element": {
                    "type": "static_select",
                    "action_id": "volume_select",
                    "placeholder": {"type": "plain_text", "text": "Estimate monthly volume"},
                    "options": volume_options
                },
                "optional": True
            }
        ]
    }


def build_bank_feeds_status_blocks(accounts: List[Dict], client_id: str) -> List[Dict]:
    """Build bank feeds status display"""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Bank Accounts ({len(accounts)})"}
        }
    ]

    if not accounts:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_No bank accounts added yet._"}
        })
        return blocks

    for acc in accounts:
        acc_id = acc.get('id')
        institution = acc.get('institution', 'Unknown')
        acc_type = acc.get('account_type', '').replace('_', ' ').title()
        last_four = acc.get('last_four', '')
        nickname = acc.get('nickname', '')
        connected = acc.get('feed_connected', False)

        status = "✅ Feed Connected" if connected else "⚠️ Feed Not Connected"
        title = f"*{institution}* - {acc_type}"
        if last_four:
            title += f" (x{last_four})"
        if nickname:
            title += f"\n_{nickname}_"

        block = {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"{title}\n{status}"}
        }

        if not connected:
            block["accessory"] = {
                "type": "button",
                "text": {"type": "plain_text", "text": "Mark Connected"},
                "action_id": f"mark_feed_connected_{acc_id}",
                "value": str(acc_id)
            }

        blocks.append(block)
        blocks.append({"type": "divider"})

    return blocks


def build_operating_rules_modal(client_id: str, existing_rules: Optional[Dict] = None) -> Dict:
    """Build modal for setting operating rules"""
    import json

    schedule_options = [
        {"text": {"type": "plain_text", "text": "Monthly by 15th"}, "value": "monthly by 15th"},
        {"text": {"type": "plain_text", "text": "Monthly by 10th"}, "value": "monthly by 10th"},
        {"text": {"type": "plain_text", "text": "Quarterly"}, "value": "quarterly"},
        {"text": {"type": "plain_text", "text": "Annual"}, "value": "annual"},
    ]

    sla_options = [
        {"text": {"type": "plain_text", "text": "24 hours"}, "value": "24"},
        {"text": {"type": "plain_text", "text": "48 hours"}, "value": "48"},
        {"text": {"type": "plain_text", "text": "72 hours"}, "value": "72"},
        {"text": {"type": "plain_text", "text": "1 week"}, "value": "168"},
    ]

    blocks = [
        {
            "type": "input",
            "block_id": "threshold_block",
            "label": {"type": "plain_text", "text": "Approval Threshold ($)"},
            "element": {
                "type": "plain_text_input",
                "action_id": "threshold_input",
                "placeholder": {"type": "plain_text", "text": "500"},
                "initial_value": str(existing_rules.get('approval_threshold', 500)) if existing_rules else "500"
            }
        },
        {
            "type": "input",
            "block_id": "sla_block",
            "label": {"type": "plain_text", "text": "Response SLA"},
            "element": {
                "type": "static_select",
                "action_id": "sla_select",
                "placeholder": {"type": "plain_text", "text": "Select SLA"},
                "options": sla_options
            }
        },
        {
            "type": "input",
            "block_id": "schedule_block",
            "label": {"type": "plain_text", "text": "Close Schedule"},
            "element": {
                "type": "static_select",
                "action_id": "schedule_select",
                "placeholder": {"type": "plain_text", "text": "Select schedule"},
                "options": schedule_options
            }
        },
        {
            "type": "input",
            "block_id": "escalation_block",
            "label": {"type": "plain_text", "text": "Escalation Contact"},
            "element": {
                "type": "plain_text_input",
                "action_id": "escalation_input",
                "placeholder": {"type": "plain_text", "text": "Name or email for escalations"}
            },
            "optional": True
        },
        {
            "type": "input",
            "block_id": "notes_block",
            "label": {"type": "plain_text", "text": "Notes"},
            "element": {
                "type": "plain_text_input",
                "action_id": "notes_input",
                "multiline": True,
                "placeholder": {"type": "plain_text", "text": "Any special instructions or notes"}
            },
            "optional": True
        }
    ]

    return {
        "type": "modal",
        "callback_id": "operating_rules_modal",
        "private_metadata": json.dumps({"client_id": client_id}),
        "title": {"type": "plain_text", "text": "Operating Rules"},
        "submit": {"type": "plain_text", "text": "Save"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": blocks
    }


def build_operating_rules_card(rules: Dict, client_name: str) -> List[Dict]:
    """Build operating rules summary card for pinning"""
    threshold = rules.get('approval_threshold', 500)
    sla = rules.get('response_sla_hours', 48)
    schedule = rules.get('close_schedule', 'Not set')
    escalation = rules.get('escalation_contact', 'Not set')

    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Operating Rules: {client_name}"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Approval Threshold:*\n${threshold:,.2f}"},
                {"type": "mrkdwn", "text": f"*Response SLA:*\n{sla} hours"},
                {"type": "mrkdwn", "text": f"*Close Schedule:*\n{schedule}"},
                {"type": "mrkdwn", "text": f"*Escalation:*\n{escalation}"}
            ]
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "_Pin this message for easy reference_"}]
        }
    ]


def build_add_system_modal(client_id: str) -> Dict:
    """Build modal for adding a system to inventory"""
    import json

    system_types = [
        {"text": {"type": "plain_text", "text": "Stripe"}, "value": "stripe"},
        {"text": {"type": "plain_text", "text": "Square"}, "value": "square"},
        {"text": {"type": "plain_text", "text": "PayPal"}, "value": "paypal"},
        {"text": {"type": "plain_text", "text": "Shopify"}, "value": "shopify"},
        {"text": {"type": "plain_text", "text": "Gusto (Payroll)"}, "value": "gusto"},
        {"text": {"type": "plain_text", "text": "ADP (Payroll)"}, "value": "adp"},
        {"text": {"type": "plain_text", "text": "Bill.com"}, "value": "billcom"},
        {"text": {"type": "plain_text", "text": "Expensify"}, "value": "expensify"},
        {"text": {"type": "plain_text", "text": "Other"}, "value": "other"},
    ]

    status_options = [
        {"text": {"type": "plain_text", "text": "Identified"}, "value": "identified"},
        {"text": {"type": "plain_text", "text": "Connecting"}, "value": "connecting"},
        {"text": {"type": "plain_text", "text": "Connected"}, "value": "connected"},
        {"text": {"type": "plain_text", "text": "Verified"}, "value": "verified"},
    ]

    return {
        "type": "modal",
        "callback_id": "add_system_modal",
        "private_metadata": json.dumps({"client_id": client_id}),
        "title": {"type": "plain_text", "text": "Add System"},
        "submit": {"type": "plain_text", "text": "Add"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "type_block",
                "label": {"type": "plain_text", "text": "System Type"},
                "element": {
                    "type": "static_select",
                    "action_id": "type_select",
                    "placeholder": {"type": "plain_text", "text": "Select system"},
                    "options": system_types
                }
            },
            {
                "type": "input",
                "block_id": "name_block",
                "label": {"type": "plain_text", "text": "System Name"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "name_input",
                    "placeholder": {"type": "plain_text", "text": "Custom name (if 'Other')"}
                },
                "optional": True
            },
            {
                "type": "input",
                "block_id": "status_block",
                "label": {"type": "plain_text", "text": "Status"},
                "element": {
                    "type": "static_select",
                    "action_id": "status_select",
                    "placeholder": {"type": "plain_text", "text": "Select status"},
                    "options": status_options,
                    "initial_option": status_options[0]
                }
            },
            {
                "type": "input",
                "block_id": "notes_block",
                "label": {"type": "plain_text", "text": "Notes"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "notes_input",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Integration notes, credentials location, etc."}
                },
                "optional": True
            }
        ]
    }


def build_request_docs_modal(client_id: str, doc_types: List[Dict]) -> Dict:
    """Build modal for requesting documents"""
    import json

    doc_options = [
        {
            "text": {"type": "plain_text", "text": d.get('description', d.get('type', ''))[:75]},
            "value": d.get('type', '')
        }
        for d in doc_types
    ]

    return {
        "type": "modal",
        "callback_id": "request_docs_modal",
        "private_metadata": json.dumps({"client_id": client_id}),
        "title": {"type": "plain_text", "text": "Request Documents"},
        "submit": {"type": "plain_text", "text": "Send Request"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "docs_block",
                "label": {"type": "plain_text", "text": "Documents to Request"},
                "element": {
                    "type": "multi_static_select",
                    "action_id": "docs_select",
                    "placeholder": {"type": "plain_text", "text": "Select documents"},
                    "options": doc_options[:100]
                }
            },
            {
                "type": "input",
                "block_id": "period_block",
                "label": {"type": "plain_text", "text": "Period"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "period_input",
                    "placeholder": {"type": "plain_text", "text": "e.g., 2024, Q4 2024, Jan 2025"}
                },
                "optional": True
            },
            {
                "type": "input",
                "block_id": "due_block",
                "label": {"type": "plain_text", "text": "Due Date"},
                "element": {
                    "type": "datepicker",
                    "action_id": "due_date_picker"
                },
                "optional": True
            },
            {
                "type": "input",
                "block_id": "message_block",
                "label": {"type": "plain_text", "text": "Custom Message"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "message_input",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Additional instructions for the client"}
                },
                "optional": True
            }
        ]
    }


# ---------------------------------------------------------------------------
# Case/Message Action Modals
# ---------------------------------------------------------------------------

def build_convert_to_case_modal(
    message_text: str,
    channel_id: str,
    thread_ts: str,
    permalink: str,
    clients: List[Dict]
) -> Dict:
    """Build modal for converting a message to a case"""
    import json

    client_options = [
        {
            "text": {"type": "plain_text", "text": c.get('display_name', c.get('legal_name', 'Unknown'))[:75]},
            "value": c.get('id', '')
        }
        for c in clients
    ]

    priority_options = [
        {"text": {"type": "plain_text", "text": "Low"}, "value": "low"},
        {"text": {"type": "plain_text", "text": "Normal"}, "value": "normal"},
        {"text": {"type": "plain_text", "text": "High"}, "value": "high"},
        {"text": {"type": "plain_text", "text": "Urgent"}, "value": "urgent"},
    ]

    # Truncate message for title suggestion
    suggested_title = message_text[:50] + "..." if len(message_text) > 50 else message_text

    return {
        "type": "modal",
        "callback_id": "convert_to_case_modal",
        "private_metadata": json.dumps({
            "channel_id": channel_id,
            "thread_ts": thread_ts,
            "permalink": permalink
        }),
        "title": {"type": "plain_text", "text": "Convert to Case"},
        "submit": {"type": "plain_text", "text": "Create Case"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Original Message:*\n>{message_text[:500]}"}
            },
            {"type": "divider"},
            {
                "type": "input",
                "block_id": "title_block",
                "label": {"type": "plain_text", "text": "Case Title"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "title_input",
                    "initial_value": suggested_title,
                    "placeholder": {"type": "plain_text", "text": "Brief description of the issue"}
                }
            },
            {
                "type": "input",
                "block_id": "client_block",
                "label": {"type": "plain_text", "text": "Client"},
                "element": {
                    "type": "static_select",
                    "action_id": "client_select",
                    "placeholder": {"type": "plain_text", "text": "Select client"},
                    "options": client_options[:100]
                }
            },
            {
                "type": "input",
                "block_id": "priority_block",
                "label": {"type": "plain_text", "text": "Priority"},
                "element": {
                    "type": "static_select",
                    "action_id": "priority_select",
                    "placeholder": {"type": "plain_text", "text": "Select priority"},
                    "options": priority_options,
                    "initial_option": priority_options[1]  # Normal
                }
            },
            {
                "type": "input",
                "block_id": "description_block",
                "label": {"type": "plain_text", "text": "Additional Details"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "description_input",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Any additional context or notes"}
                },
                "optional": True
            }
        ]
    }


def build_qbo_connect_card(client_id: str, is_connected: bool = False, realm_id: Optional[str] = None) -> List[Dict]:
    """Build QBO connection status card"""
    import json

    if is_connected and realm_id:
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*QuickBooks Online*\n✅ Connected (Realm: {realm_id})"
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Verify"},
                    "action_id": "verify_qbo_btn",
                    "value": client_id
                }
            }
        ]

    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*QuickBooks Online*\n⚠️ Not connected\n\n1. Complete OAuth connection in QBO\n2. Click 'I've Connected' when done"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "I've Connected QBO"},
                    "action_id": "verify_qbo_btn",
                    "value": client_id,
                    "style": "primary"
                }
            ]
        }
    ]


# ---------------------------------------------------------------------------
# Receipt Scanning Blocks
# ---------------------------------------------------------------------------

DOC_TYPE_OPTIONS = [
    {"label": "Expense Receipt", "value": "expense_receipt"},
    {"label": "Invoice", "value": "invoice"},
    {"label": "Bill", "value": "bill"},
    {"label": "Bank Statement", "value": "bank_statement"},
    {"label": "Other", "value": "other"},
]


def build_receipt_classify_blocks(slack_file_id: str, filename: str) -> List[Dict]:
    """Build doc-type classification dropdown after a file upload"""
    options = [
        {
            "text": {"type": "plain_text", "text": opt["label"]},
            "value": opt["value"],
        }
        for opt in DOC_TYPE_OPTIONS
    ]

    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Image received:* `{filename}`\nWhat type of document is this?",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "static_select",
                    "placeholder": {"type": "plain_text", "text": "Select document type..."},
                    "action_id": f"classify_doc_type_{slack_file_id}",
                    "options": options,
                }
            ],
        },
    ]


def build_receipt_scanning_blocks(receipt_id: int, filename: str) -> List[Dict]:
    """Build 'scanning in progress' status message"""
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Scanning:* `{filename}`\n"
                    f"Receipt #{receipt_id} — extracting data with AI vision..."
                ),
            },
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "This usually takes a few seconds."}],
        },
    ]


def build_receipt_review_blocks(
    receipt_id: int,
    extracted_data: Dict[str, Any],
    doc_type: str,
    filename: str,
    confidence: float = 0.0,
    warnings: Optional[List[str]] = None,
) -> List[Dict]:
    """Build review card with extracted data and Approve/Edit/Reject buttons"""
    doc_label = {
        "expense_receipt": "Expense Receipt",
        "invoice": "Invoice",
        "bill": "Bill",
        "bank_statement": "Bank Statement",
        "other": "Document",
    }.get(doc_type, "Document")

    vendor = extracted_data.get("vendor_name", "Unknown")
    date = extracted_data.get("date", "N/A")
    total = extracted_data.get("total")
    total_str = format_currency(total) if total is not None else "N/A"
    tax = extracted_data.get("tax")
    tax_str = format_currency(tax) if tax is not None else "—"
    category = extracted_data.get("category_suggestion", "—")
    inv_num = extracted_data.get("invoice_number", "")
    conf_pct = f"{int(confidence * 100)}%"

    header_text = f"{doc_label} — {vendor}"
    if inv_num:
        header_text += f" (#{inv_num})"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": header_text[:150]},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Vendor:*\n{vendor}"},
                {"type": "mrkdwn", "text": f"*Date:*\n{date}"},
                {"type": "mrkdwn", "text": f"*Total:*\n{total_str}"},
                {"type": "mrkdwn", "text": f"*Tax:*\n{tax_str}"},
            ],
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Category:*\n{category}"},
                {"type": "mrkdwn", "text": f"*Confidence:*\n{conf_pct}"},
            ],
        },
    ]

    # Line items
    line_items = extracted_data.get("line_items") or []
    if line_items:
        items_text = "*Line Items:*\n"
        for item in line_items[:10]:
            desc = item.get("description", "Item")
            amt = item.get("amount")
            amt_str = format_currency(amt) if amt is not None else "—"
            qty = item.get("quantity", 1)
            items_text += f"  {desc} (x{qty}) — {amt_str}\n"
        if len(line_items) > 10:
            items_text += f"  _...and {len(line_items) - 10} more_\n"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": items_text},
        })

    # All text (OCR transcription)
    all_text = extracted_data.get("all_text")
    if all_text:
        # Slack section text limit is 3000 chars
        truncated = all_text[:2900]
        if len(all_text) > 2900:
            truncated += "\n_...truncated_"
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*All Text on Document:*\n```{truncated}```"},
        })

    # Notes
    notes = extracted_data.get("notes")
    if notes:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Notes:*\n{notes[:2000]}"},
        })

    # Warnings
    if warnings:
        warn_text = "\n".join(f"  - {w}" for w in warnings)
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"*Warnings:*\n{warn_text}"}],
        })

    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"File: `{filename}` | Receipt #{receipt_id}"}],
    })

    # Action buttons
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Approve"},
                "action_id": f"receipt_approve_{receipt_id}",
                "value": str(receipt_id),
                "style": "primary",
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Edit"},
                "action_id": f"receipt_edit_{receipt_id}",
                "value": str(receipt_id),
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Reject"},
                "action_id": f"receipt_reject_{receipt_id}",
                "value": str(receipt_id),
                "style": "danger",
            },
        ],
    })

    return blocks


def build_receipt_edit_modal(
    receipt_id: int,
    extracted_data: Dict[str, Any],
    doc_type: str,
) -> Dict:
    """Build modal for editing extracted receipt data before approval"""
    import json

    vendor = extracted_data.get("vendor_name", "")
    date = extracted_data.get("date", "")
    total = extracted_data.get("total", "")
    tax = extracted_data.get("tax", "")
    category = extracted_data.get("category_suggestion", "")
    notes = extracted_data.get("notes", "")

    return {
        "type": "modal",
        "callback_id": "receipt_edit_modal",
        "private_metadata": json.dumps({"receipt_id": receipt_id, "doc_type": doc_type}),
        "title": {"type": "plain_text", "text": "Edit Scanned Data"},
        "submit": {"type": "plain_text", "text": "Save & Approve"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "vendor_block",
                "label": {"type": "plain_text", "text": "Vendor Name"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "vendor_input",
                    "initial_value": str(vendor) if vendor else "",
                    "placeholder": {"type": "plain_text", "text": "Business name"},
                },
            },
            {
                "type": "input",
                "block_id": "date_block",
                "label": {"type": "plain_text", "text": "Date (YYYY-MM-DD)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "date_input",
                    "initial_value": str(date) if date else "",
                    "placeholder": {"type": "plain_text", "text": "2025-01-15"},
                },
            },
            {
                "type": "input",
                "block_id": "total_block",
                "label": {"type": "plain_text", "text": "Total Amount"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "total_input",
                    "initial_value": str(total) if total else "",
                    "placeholder": {"type": "plain_text", "text": "0.00"},
                },
            },
            {
                "type": "input",
                "block_id": "tax_block",
                "label": {"type": "plain_text", "text": "Tax"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "tax_input",
                    "initial_value": str(tax) if tax else "",
                    "placeholder": {"type": "plain_text", "text": "0.00"},
                },
                "optional": True,
            },
            {
                "type": "input",
                "block_id": "category_block",
                "label": {"type": "plain_text", "text": "Category"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "category_input",
                    "initial_value": str(category) if category else "",
                    "placeholder": {"type": "plain_text", "text": "e.g., Office Supplies"},
                },
                "optional": True,
            },
            {
                "type": "input",
                "block_id": "notes_block",
                "label": {"type": "plain_text", "text": "Notes"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "notes_input",
                    "multiline": True,
                    "initial_value": str(notes) if notes else "",
                    "placeholder": {"type": "plain_text", "text": "Additional notes"},
                },
                "optional": True,
            },
        ],
    }


def build_receipt_queue_blocks(receipts: List[Dict]) -> List[Dict]:
    """Build receipt queue list display"""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Receipt Queue ({len(receipts)})"},
        }
    ]

    if not receipts:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_No receipts in queue._"},
        })
        return blocks

    status_emoji = {
        "uploaded": "📤",
        "scanning": "🔍",
        "scanned": "📋",
        "approved": "✅",
        "rejected": "❌",
        "error": "⚠️",
    }

    for r in receipts[:20]:
        rid = r.get("id", "")
        filename = r.get("original_filename", "unknown")
        status = r.get("status", "uploaded")
        doc_type = r.get("doc_type", "other")
        emoji = status_emoji.get(status, "📄")
        created = r.get("created_at", "")[:10]

        extracted = {}
        if r.get("extracted_data"):
            try:
                extracted = json.loads(r["extracted_data"]) if isinstance(r["extracted_data"], str) else r["extracted_data"]
            except (json.JSONDecodeError, TypeError):
                pass

        vendor = extracted.get("vendor_name", "")
        total = extracted.get("total")
        total_str = format_currency(total) if total is not None else ""

        text = f"{emoji} *#{rid}* — `{filename}`"
        if vendor:
            text += f"\n{vendor}"
        if total_str:
            text += f" — {total_str}"
        text += f"\n_{doc_type.replace('_', ' ').title()}_ | {status} | {created}"

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": text},
        })

    if len(receipts) > 20:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"_...and {len(receipts) - 20} more_"}],
        })

    return blocks


def build_receipt_queue_summary_blocks(summary: Dict[str, int]) -> List[Dict]:
    """Build compact receipt queue summary for Home tab"""
    total = sum(summary.values())
    if total == 0:
        return []

    parts = []
    for status, count in sorted(summary.items()):
        if count > 0:
            parts.append(f"{status}: {count}")

    return [
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Receipt Queue* ({total} total)\n" + " | ".join(parts),
            },
        },
    ]


def build_qbo_verify_result_blocks(
    success: bool,
    company_name: Optional[str] = None,
    realm_id: Optional[str] = None,
    account_count: int = 0,
    error: Optional[str] = None
) -> List[Dict]:
    """Build QBO verification result blocks"""
    if success:
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✅ *QBO Verification Successful*\n\n"
                           f"*Company:* {company_name}\n"
                           f"*Realm ID:* {realm_id}\n"
                           f"*Accounts:* {account_count} accounts found"
                }
            }
        ]

    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"❌ *QBO Verification Failed*\n\n"
                       f"Error: {error or 'Unknown error'}\n\n"
                       f"Please check the OAuth connection and try again."
            }
        }
    ]
