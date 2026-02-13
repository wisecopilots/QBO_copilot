#!/usr/bin/env python3
"""
Slack Bot for QBO Copilot

Connects the QBO Copilot agent to Slack using Socket Mode.
Uses Claude (Anthropic API) as the brain with QBO tools.

Supports:
- Direct messages and @mentions for natural language queries
- Slash commands (/qbo)
- Block Kit interactive UI (buttons, modals, dropdowns)
- Home tab dashboard

Usage:
    python integrations/slack/bot.py
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Import onboarding modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from qbo_copilot.data.onboarding_db import OnboardingDB
from qbo_copilot.onboarding.state_machine import OnboardingStateMachine, PHASE_NAMES
from qbo_copilot.onboarding.doc_templates import ONBOARDING_DOC_PACK, create_doc_request_pack

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CPACopilotSlackBot:
    """Slack bot with Claude brain and Block Kit interactive UI"""

    def __init__(self):
        self.bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.app_token = os.getenv("SLACK_APP_TOKEN")

        if not self.bot_token or not self.app_token:
            raise ValueError("SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set")

        self.app = App(token=self.bot_token)

        # Initialize onboarding database and state machine
        self.db = OnboardingDB()
        self.state_machine = OnboardingStateMachine(self.db)

        # Track selected client per user (in-memory)
        self.user_selected_client = {}
        # Track selected QBO company per user (realm_id from clients.yaml)
        self.user_qbo_client = {}

        self._init_agent()
        self._register_message_handlers()
        self._register_interactive_handlers()
        self._register_modal_handlers()
        self._register_home_tab()
        self._register_onboarding_handlers()
        self._register_shortcuts()
        self._register_receipt_handlers()

    def _init_agent(self):
        """Initialize the QBO agent with Claude callback"""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))

        from agent.main import create_agent, SYSTEM_PROMPT
        from agent.tools.qbo_tools import qbo_tools

        self.system_prompt = SYSTEM_PROMPT
        self.qbo_tools = qbo_tools

        # Build tool schemas for Claude
        self.tool_schemas = []
        self.tool_functions = {}
        for tool in qbo_tools:
            self.tool_schemas.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool.get("parameters", {"type": "object", "properties": {}})
            })
            self.tool_functions[tool["name"]] = tool["function"]

        # Create agent with Claude callback
        self.agent = create_agent(llm_callback=self._claude_callback)
        logger.info(f"Agent initialized with {len(self.tool_schemas)} tools")

    def _claude_callback(self, message: str, system_prompt: str, tools: dict, context: dict) -> str:
        """Send message to Claude with tool use"""
        import anthropic

        client = anthropic.Anthropic()
        messages = [{"role": "user", "content": message}]

        # Agentic loop - let Claude call tools and continue
        for _ in range(10):  # max iterations
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                system=system_prompt,
                tools=self.tool_schemas,
                messages=messages
            )

            # If no tool use, extract text and return
            if response.stop_reason != "tool_use":
                text_parts = [b.text for b in response.content if b.type == "text"]
                return "\n".join(text_parts) if text_parts else "I processed your request."

            # Handle tool calls
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    logger.info(f"Tool call: {tool_name}({json.dumps(tool_input)[:200]})")

                    try:
                        func = self.tool_functions.get(tool_name)
                        if func:
                            result = func(**tool_input)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(result, default=str)[:10000]
                            })
                        else:
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": f"Unknown tool: {tool_name}",
                                "is_error": True
                            })
                    except Exception as e:
                        logger.error(f"Tool error {tool_name}: {e}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {str(e)}",
                            "is_error": True
                        })

            messages.append({"role": "user", "content": tool_results})

        return "I hit the maximum number of steps. Please try a simpler query."

    # -----------------------------------------------------------------------
    # QBO client selection
    # -----------------------------------------------------------------------

    def _ensure_qbo_client(self, user_id: str, reply_fn) -> bool:
        """
        Ensure a QBO client is selected for this user before processing.

        If only one client exists, auto-selects it.
        If multiple clients exist and none selected, shows a selector dropdown.

        Args:
            user_id: Slack user ID
            reply_fn: Function to send messages (say or respond)

        Returns:
            True if a client is selected and ready, False if selector was shown.
        """
        from agent.tools.qbo_tools import set_current_client, _get_tenant_manager
        from integrations.slack.blocks import build_qbo_client_selector_message

        manager = _get_tenant_manager()
        clients = manager.list_clients()

        if not clients:
            reply_fn("No QBO companies configured. Add one in `config/clients.yaml`.")
            return False

        selected_realm = self.user_qbo_client.get(user_id)

        # Auto-select if only one client
        if not selected_realm and len(clients) == 1:
            selected_realm = clients[0].realm_id
            self.user_qbo_client[user_id] = selected_realm

        if not selected_realm:
            # Multiple clients, none selected — show selector
            client_list = [{"name": c.name, "realm_id": c.realm_id} for c in clients]
            blocks = build_qbo_client_selector_message(client_list)
            reply_fn(
                text="Please select a QBO company first, then re-send your message.",
                blocks=blocks
            )
            return False

        # Set the active client for this request
        set_current_client(selected_realm)
        return True

    def _get_active_client_name(self, user_id: str) -> Optional[str]:
        """Get the display name of the user's active QBO client."""
        from agent.tools.qbo_tools import _get_tenant_manager

        realm_id = self.user_qbo_client.get(user_id)
        if not realm_id:
            return None
        manager = _get_tenant_manager()
        config = manager.get_client_config(realm_id)
        return config.name if config else None

    # -----------------------------------------------------------------------
    # Message handlers
    # -----------------------------------------------------------------------

    def _register_message_handlers(self):
        """Register Slack event handlers for messages"""

        # Handle file_share subtype separately (slack-bolt requires explicit subtype registration)
        @self.app.event({"type": "message", "subtype": "file_share"})
        def handle_file_share(event, say, client):
            logger.info(f"File share event received: {event.get('channel_type')}")
            if event.get("bot_id") or event.get("channel_type") != "im":
                return

            files = event.get("files", [])
            image_files = [
                f for f in files
                if f.get("mimetype", "").startswith("image/")
            ]
            if image_files:
                from integrations.slack.blocks import build_receipt_classify_blocks

                for img_file in image_files:
                    file_id = img_file.get("id", "")
                    filename = img_file.get("name", "image")
                    blocks = build_receipt_classify_blocks(file_id, filename)
                    say(
                        text=f"Image received: {filename}. Please classify it.",
                        blocks=blocks,
                    )

        @self.app.event("message")
        def handle_message(event, say, client):
            if event.get("bot_id") or event.get("channel_type") != "im":
                return

            user_id = event.get("user")
            channel = event.get("channel")

            # Check for file uploads (image scanning flow) - fallback for events without subtype
            files = event.get("files", [])
            if files:
                image_files = [
                    f for f in files
                    if f.get("mimetype", "").startswith("image/")
                ]
                if image_files:
                    from integrations.slack.blocks import build_receipt_classify_blocks

                    for img_file in image_files:
                        file_id = img_file.get("id", "")
                        filename = img_file.get("name", "image")
                        blocks = build_receipt_classify_blocks(file_id, filename)
                        say(
                            text=f"Image received: {filename}. Please classify it.",
                            blocks=blocks,
                        )
                    return

            message = event.get("text", "")
            logger.info(f"DM from {user_id}: {message}")

            # Ensure QBO client is selected
            if not self._ensure_qbo_client(user_id, say):
                return

            try:
                user_info = client.users_info(user=user_id)
                user_name = user_info["user"]["real_name"]
            except Exception:
                user_name = user_id

            context = {
                "user_id": user_id,
                "user_name": user_name,
                "channel": channel,
                "channel_type": "dm"
            }

            response = self.agent.process_message(message, context)
            say(response)

        @self.app.event("app_mention")
        def handle_mention(event, say, client):
            message = re.sub(r"<@[A-Z0-9]+>\s*", "", event.get("text", "")).strip()
            user_id = event.get("user")
            channel = event.get("channel")

            logger.info(f"Mention from {user_id} in {channel}: {message}")

            # Ensure QBO client is selected
            if not self._ensure_qbo_client(user_id, say):
                return

            try:
                user_info = client.users_info(user=user_id)
                user_name = user_info["user"]["real_name"]
            except Exception:
                user_name = user_id

            context = {
                "user_id": user_id,
                "user_name": user_name,
                "channel": channel,
                "channel_type": "channel"
            }

            response = self.agent.process_message(message, context)
            say(response)

        @self.app.command("/qbo")
        def handle_qbo_command(ack, respond, command):
            ack()
            query = command.get("text", "").strip()
            user_id = command.get("user_id")

            if not query or query.lower() in ("help", "?"):
                from integrations.slack.blocks import _build_help_blocks
                respond(
                    text="QBO Copilot — Help",
                    blocks=_build_help_blocks(),
                )
                return

            # Handle receipts subcommand
            if query.lower() in ("receipts", "receipt queue", "receipt"):
                from integrations.slack.blocks import build_receipt_queue_blocks
                receipts = self.db.get_receipts_by_status()
                blocks = build_receipt_queue_blocks(receipts)
                respond(text=f"Receipt queue: {len(receipts)} items", blocks=blocks)
                return

            # Ensure QBO client is selected
            if not self._ensure_qbo_client(user_id, respond):
                return

            logger.info(f"/qbo from {user_id}: {query}")
            context = {"user_id": user_id, "channel_type": "slash_command"}
            response = self.agent.process_message(query, context)
            respond(response)

    # -----------------------------------------------------------------------
    # Interactive handlers (buttons, dropdowns, overflow menus)
    # -----------------------------------------------------------------------

    def _register_interactive_handlers(self):
        """Register handlers for Block Kit interactive elements"""
        from integrations.slack.blocks import (
            build_invoice_blocks,
            build_expense_blocks,
            build_customer_blocks,
            build_confirm_modal,
            build_create_invoice_modal,
            build_create_customer_modal,
        )
        from agent.tools.qbo_tools import (
            qbo_get_invoices,
            qbo_get_purchases,
            qbo_get_customers,
            qbo_get_entity,
            qbo_send_invoice,
            qbo_void_invoice,
        )

        # Invoice overflow menu actions
        @self.app.action(re.compile(r"^invoice_actions_"))
        def handle_invoice_action(ack, body, client):
            ack()
            action = body["actions"][0]
            selected = action["selected_option"]["value"]
            parts = selected.split("|")
            action_type, inv_id = parts[0], parts[1]
            sync_token = parts[2] if len(parts) > 2 else "0"

            if action_type == "view":
                try:
                    invoice = qbo_get_entity("Invoice", inv_id)
                    customer = invoice.get("CustomerRef", {}).get("name", "Unknown")
                    total = invoice.get("TotalAmt", 0)
                    balance = invoice.get("Balance", 0)
                    date = invoice.get("TxnDate", "N/A")
                    due = invoice.get("DueDate", "N/A")
                    lines = invoice.get("Line", [])

                    detail = f"*Invoice #{invoice.get('DocNumber', 'N/A')}*\n"
                    detail += f"Customer: {customer}\n"
                    detail += f"Date: {date} \u2022 Due: {due}\n"
                    detail += f"Total: ${total:,.2f} \u2022 Balance: ${balance:,.2f}\n\n"
                    detail += "*Line Items:*\n"
                    for line in lines:
                        if line.get("DetailType") == "SalesItemLineDetail":
                            desc = line.get("Description", "Item")
                            amt = line.get("Amount", 0)
                            detail += f"\u2022 {desc}: ${amt:,.2f}\n"

                    client.chat_postEphemeral(
                        channel=body["channel"]["id"],
                        user=body["user"]["id"],
                        text=detail
                    )
                except Exception as e:
                    client.chat_postEphemeral(
                        channel=body["channel"]["id"],
                        user=body["user"]["id"],
                        text=f"Error fetching invoice: {e}"
                    )

            elif action_type == "send":
                modal = build_confirm_modal(
                    "send", f"Invoice #{inv_id}",
                    json.dumps({"invoice_id": inv_id})
                )
                client.views_open(trigger_id=body["trigger_id"], view=modal)

            elif action_type == "void":
                modal = build_confirm_modal(
                    "void", f"Invoice #{inv_id}",
                    json.dumps({"invoice_id": inv_id, "sync_token": sync_token})
                )
                client.views_open(trigger_id=body["trigger_id"], view=modal)

        # Quick action buttons (from dashboard or messages)
        @self.app.action("view_unpaid_btn")
        def handle_view_unpaid(ack, body, client):
            ack()
            invoices = qbo_get_invoices(unpaid_only=True)
            blocks = build_invoice_blocks(invoices, "Unpaid Invoices")
            client.chat_postMessage(
                channel=body["channel"]["id"] if "channel" in body else body["user"]["id"],
                blocks=blocks,
                text=f"Found {len(invoices)} unpaid invoices"
            )

        @self.app.action("view_expenses_btn")
        def handle_view_expenses(ack, body, client):
            ack()
            expenses = qbo_get_purchases()
            blocks = build_expense_blocks(expenses, title="Recent Expenses")
            client.chat_postMessage(
                channel=body["channel"]["id"] if "channel" in body else body["user"]["id"],
                blocks=blocks,
                text=f"Found {len(expenses)} expenses"
            )

        @self.app.action("create_invoice_btn")
        def handle_create_invoice_btn(ack, body, client):
            ack()
            customers = qbo_get_customers()
            modal = build_create_invoice_modal(customers)
            client.views_open(trigger_id=body["trigger_id"], view=modal)

        @self.app.action("create_expense_btn")
        def handle_create_expense_btn(ack, body, client):
            ack()
            client.chat_postEphemeral(
                channel=body["channel"]["id"] if "channel" in body else body["user"]["id"],
                user=body["user"]["id"],
                text="To add an expense, try: `/qbo create expense $50 to Office Supplies from Staples`"
            )

        # Expense categorization dropdown
        @self.app.action(re.compile(r"^categorize_expense_"))
        def handle_categorize(ack, body, client):
            ack()
            action = body["actions"][0]
            action_id = action["action_id"]
            expense_id = action_id.replace("categorize_expense_", "")
            account_id = action["selected_option"]["value"]
            account_name = action["selected_option"]["text"]["text"]

            client.chat_update(
                channel=body["channel"]["id"],
                ts=body["message"]["ts"],
                text=f"Expense {expense_id} categorized as {account_name}",
                blocks=[{
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"\u2705 Categorized as *{account_name}*"
                    }
                }]
            )

    # -----------------------------------------------------------------------
    # Modal submission handlers
    # -----------------------------------------------------------------------

    def _register_modal_handlers(self):
        """Register handlers for modal submissions"""
        from agent.tools.qbo_tools import (
            qbo_create_invoice,
            qbo_create_customer,
            qbo_send_invoice,
            qbo_void_invoice,
        )

        @self.app.view("create_invoice_modal")
        def handle_create_invoice(ack, body, view, client):
            values = view["state"]["values"]
            customer_id = values["customer_block"]["customer_select"]["selected_option"]["value"]
            description = values["description_block"]["description_input"]["value"]
            amount_str = values["amount_block"]["amount_input"]["value"]
            due_date = values["due_date_block"]["due_date_input"].get("selected_date")

            # Validate amount
            try:
                amount = float(amount_str.replace(",", "").replace("$", ""))
            except ValueError:
                ack(response_action="errors", errors={"amount_block": "Please enter a valid amount"})
                return

            ack()

            try:
                result = qbo_create_invoice(
                    customer_id=customer_id,
                    line_items=[{"description": description, "amount": amount}],
                    due_date=due_date
                )
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"\u2705 {result.get('message', 'Invoice created!')}"
                )
            except Exception as e:
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"\u274c Error creating invoice: {e}"
                )

        @self.app.view("create_customer_modal")
        def handle_create_customer(ack, body, view, client):
            values = view["state"]["values"]
            name = values["name_block"]["name_input"]["value"]
            email = values["email_block"]["email_input"].get("value")
            phone = values["phone_block"]["phone_input"].get("value")
            company = values["company_block"]["company_input"].get("value")

            ack()

            try:
                from agent.tools.qbo_tools import qbo_create_customer
                result = qbo_create_customer(
                    display_name=name,
                    email=email,
                    phone=phone,
                    company_name=company
                )
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"\u2705 {result.get('message', 'Customer created!')}"
                )
            except Exception as e:
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"\u274c Error creating customer: {e}"
                )

        @self.app.view("confirm_send_modal")
        def handle_confirm_send(ack, body, view, client):
            ack()
            metadata = json.loads(view.get("private_metadata", "{}"))
            invoice_id = metadata.get("invoice_id")

            try:
                result = qbo_send_invoice(invoice_id)
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"\u2705 Invoice #{invoice_id} sent to customer!"
                )
            except Exception as e:
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"\u274c Error sending invoice: {e}"
                )

        @self.app.view("confirm_void_modal")
        def handle_confirm_void(ack, body, view, client):
            ack()
            metadata = json.loads(view.get("private_metadata", "{}"))
            invoice_id = metadata.get("invoice_id")
            sync_token = metadata.get("sync_token", "0")

            try:
                result = qbo_void_invoice(invoice_id, sync_token)
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"\u2705 Invoice #{invoice_id} voided."
                )
            except Exception as e:
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"\u274c Error voiding invoice: {e}"
                )

    # -----------------------------------------------------------------------
    # Home tab
    # -----------------------------------------------------------------------

    def _register_home_tab(self):
        """Register Home tab handler"""
        from integrations.slack.blocks import (
            build_dashboard_blocks,
            build_client_selector_blocks,
            build_onboarding_dashboard_blocks,
            build_waiting_queues_blocks,
            build_receipt_queue_summary_blocks,
            build_home_capabilities_blocks,
        )
        from agent.tools.qbo_tools import (
            qbo_get_accounts,
            qbo_get_invoices,
            qbo_get_purchases,
        )

        @self.app.event("app_home_opened")
        def update_home_tab(event, client):
            user_id = event["user"]

            try:
                # Get clients for selector
                clients = self.db.list_clients()
                selected_client_id = self.user_selected_client.get(user_id)

                # Build home tab blocks
                blocks = []

                # Client selector
                blocks.extend(build_client_selector_blocks(clients, selected_client_id))
                blocks.append({"type": "divider"})

                # If a client is selected, show onboarding dashboard
                if selected_client_id:
                    selected_client = self.db.get_client(selected_client_id)
                    if selected_client:
                        progress = self.state_machine.get_overall_progress(selected_client_id)
                        waiting_on_client = self.db.get_waiting_on_client()
                        waiting_on_cpa = self.db.get_waiting_on_cpa()

                        blocks.extend(build_onboarding_dashboard_blocks(
                            client=selected_client,
                            progress=progress,
                            waiting_on_client=waiting_on_client,
                            waiting_on_cpa=waiting_on_cpa
                        ))
                        blocks.append({"type": "divider"})

                # Also show QBO dashboard if connected
                try:
                    accounts = qbo_get_accounts()
                    receivable = sum(
                        a.get("CurrentBalance", 0) for a in accounts
                        if a.get("AccountType") == "Accounts Receivable"
                    )
                    payable = sum(
                        a.get("CurrentBalance", 0) for a in accounts
                        if a.get("AccountType") == "Accounts Payable"
                    )
                    cash = sum(
                        a.get("CurrentBalance", 0) for a in accounts
                        if a.get("AccountType") == "Bank"
                    )

                    unpaid = qbo_get_invoices(unpaid_only=True)
                    expenses = qbo_get_purchases()

                    blocks.extend(build_dashboard_blocks(
                        total_receivable=receivable,
                        total_payable=payable,
                        cash_balance=cash,
                        overdue_count=len(unpaid),
                        recent_expenses=expenses[:5]
                    ))
                except Exception as qbo_err:
                    logger.debug(f"QBO data not available: {qbo_err}")
                    # QBO not connected, that's fine

                # Show work queues summary
                if not selected_client_id:
                    waiting_on_client = self.db.get_waiting_on_client()
                    waiting_on_cpa = self.db.get_waiting_on_cpa()
                    blocks.extend(build_waiting_queues_blocks(waiting_on_client, waiting_on_cpa))

                # Receipt queue summary
                try:
                    receipt_summary = self.db.get_receipt_queue_summary()
                    blocks.extend(build_receipt_queue_summary_blocks(receipt_summary))
                except Exception as rq_err:
                    logger.debug(f"Receipt queue not available: {rq_err}")

                # Capabilities / help section
                blocks.extend(build_home_capabilities_blocks())

                client.views_publish(
                    user_id=user_id,
                    view={"type": "home", "blocks": blocks[:100]}  # Slack limit
                )
            except Exception as e:
                logger.error(f"Home tab error: {e}")
                client.views_publish(
                    user_id=user_id,
                    view={
                        "type": "home",
                        "blocks": [{
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*QBO Copilot*\n\nError loading dashboard: {e}\n\nTry sending a message instead."
                            }
                        }]
                    }
                )

    # -----------------------------------------------------------------------
    # Onboarding Handlers
    # -----------------------------------------------------------------------

    def _register_onboarding_handlers(self):
        """Register handlers for onboarding workflows"""
        from integrations.slack.blocks import (
            build_new_client_modal,
            build_add_contact_modal,
            build_add_bank_modal,
            build_operating_rules_modal,
            build_add_system_modal,
            build_request_docs_modal,
            build_qbo_connect_card,
            build_qbo_verify_result_blocks,
            build_bank_feeds_status_blocks,
        )

        # Client selector action (onboarding Home tab)
        @self.app.action("select_client")
        def handle_select_client(ack, body, client):
            ack()
            user_id = body["user"]["id"]
            selected = body["actions"][0]["selected_option"]["value"]
            self.user_selected_client[user_id] = selected
            # Refresh home tab
            client.views_publish(
                user_id=user_id,
                view={"type": "home", "blocks": self._build_home_blocks(user_id)}
            )

        # QBO company selector action (inline in DMs)
        @self.app.action("select_qbo_client")
        def handle_select_qbo_client(ack, body, client):
            ack()
            user_id = body["user"]["id"]
            selected_realm = body["actions"][0]["selected_option"]["value"]
            selected_name = body["actions"][0]["selected_option"]["text"]["text"]
            self.user_qbo_client[user_id] = selected_realm
            logger.info(f"User {user_id} selected QBO company: {selected_name} ({selected_realm})")
            client.chat_postMessage(
                channel=body["channel"]["id"] if "channel" in body else user_id,
                text=f"Active QBO company set to *{selected_name}*. Go ahead and send your query."
            )

        # New client button
        @self.app.action("new_client_btn")
        def handle_new_client_btn(ack, body, client):
            ack()
            modal = build_new_client_modal()
            client.views_open(trigger_id=body["trigger_id"], view=modal)

        # New client modal submission
        @self.app.view("new_client_modal")
        def handle_new_client_modal(ack, body, view, client):
            values = view["state"]["values"]
            legal_name = values["legal_name_block"]["legal_name_input"]["value"]
            display_name = values["display_name_block"]["display_name_input"].get("value")
            entity_type = values["entity_type_block"]["entity_type_select"]["selected_option"]["value"]
            year_end = values["year_end_block"]["year_end_input"].get("value")
            contact_name = values["contact_name_block"]["contact_name_input"].get("value")
            contact_email = values["contact_email_block"]["contact_email_input"].get("value")

            ack()

            try:
                # Create client
                new_client = self.db.create_client(
                    legal_name=legal_name,
                    display_name=display_name,
                    entity_type=entity_type,
                    year_end=year_end,
                    primary_contact_name=contact_name,
                    primary_contact_email=contact_email
                )

                # Start onboarding
                self.state_machine.start_onboarding(new_client["id"])

                # Log action
                self.db.log_action(
                    action="client_created",
                    client_id=new_client["id"],
                    actor_slack_id=body["user"]["id"],
                    details={"legal_name": legal_name}
                )

                # Set as selected client
                user_id = body["user"]["id"]
                self.user_selected_client[user_id] = new_client["id"]

                client.chat_postMessage(
                    channel=user_id,
                    text=f"✅ Client '{display_name or legal_name}' created! Onboarding started."
                )
            except Exception as e:
                logger.error(f"Error creating client: {e}")
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"❌ Error creating client: {e}"
                )

        # Add contact button
        @self.app.action("add_contact_btn")
        def handle_add_contact_btn(ack, body, client):
            ack()
            client_id = body["actions"][0]["value"]
            modal = build_add_contact_modal(client_id)
            client.views_open(trigger_id=body["trigger_id"], view=modal)

        # Add contact modal submission
        @self.app.view("add_contact_modal")
        def handle_add_contact_modal(ack, body, view, client):
            values = view["state"]["values"]
            metadata = json.loads(view.get("private_metadata", "{}"))
            client_id = metadata.get("client_id")

            name = values["name_block"]["name_input"]["value"]
            email = values["email_block"]["email_input"].get("value")
            phone = values["phone_block"]["phone_input"].get("value")
            role = values["role_block"]["role_select"]["selected_option"]["value"]
            threshold_str = values["threshold_block"]["threshold_input"].get("value")
            primary_selected = values["primary_block"]["primary_check"].get("selected_options", [])

            ack()

            try:
                threshold = float(threshold_str) if threshold_str else None
                is_primary = len(primary_selected) > 0

                self.db.add_contact(
                    client_id=client_id,
                    name=name,
                    email=email,
                    phone=phone,
                    role=role,
                    is_primary=is_primary,
                    approval_threshold=threshold
                )

                self.db.log_action(
                    action="contact_added",
                    client_id=client_id,
                    actor_slack_id=body["user"]["id"],
                    details={"name": name, "role": role}
                )

                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"✅ Contact '{name}' added as {role}."
                )
            except Exception as e:
                logger.error(f"Error adding contact: {e}")
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"❌ Error adding contact: {e}"
                )

        # Add bank account button
        @self.app.action("add_bank_btn")
        def handle_add_bank_btn(ack, body, client):
            ack()
            client_id = body["actions"][0]["value"]
            modal = build_add_bank_modal(client_id)
            client.views_open(trigger_id=body["trigger_id"], view=modal)

        # Add bank modal submission
        @self.app.view("add_bank_modal")
        def handle_add_bank_modal(ack, body, view, client):
            values = view["state"]["values"]
            metadata = json.loads(view.get("private_metadata", "{}"))
            client_id = metadata.get("client_id")

            institution = values["institution_block"]["institution_input"]["value"]
            account_type = values["type_block"]["type_select"]["selected_option"]["value"]
            last_four = values["last_four_block"]["last_four_input"].get("value")
            nickname = values["nickname_block"]["nickname_input"].get("value")
            volume = values["volume_block"]["volume_select"].get("selected_option", {}).get("value")

            ack()

            try:
                self.db.add_bank_account(
                    client_id=client_id,
                    institution=institution,
                    account_type=account_type,
                    last_four=last_four,
                    nickname=nickname,
                    volume_estimate=volume
                )

                self.db.log_action(
                    action="bank_account_added",
                    client_id=client_id,
                    actor_slack_id=body["user"]["id"],
                    details={"institution": institution, "type": account_type}
                )

                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"✅ Bank account added: {institution} ({account_type})"
                )
            except Exception as e:
                logger.error(f"Error adding bank account: {e}")
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"❌ Error adding bank account: {e}"
                )

        # Mark feed connected
        @self.app.action(re.compile(r"^mark_feed_connected_"))
        def handle_mark_feed_connected(ack, body, client):
            ack()
            action_id = body["actions"][0]["action_id"]
            account_id = int(action_id.replace("mark_feed_connected_", ""))

            try:
                self.db.mark_feed_connected(account_id)
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text="✅ Bank feed marked as connected."
                )
            except Exception as e:
                logger.error(f"Error marking feed connected: {e}")

        # Verify QBO button
        @self.app.action("verify_qbo_btn")
        def handle_verify_qbo(ack, body, client):
            ack()
            client_id = body["actions"][0]["value"]
            user_id = body["user"]["id"]

            try:
                from agent.tools.qbo_tools import qbo_get_company_info, qbo_get_accounts

                company_info = qbo_get_company_info()
                accounts = qbo_get_accounts()

                company_name = company_info.get("CompanyName", "Unknown")
                realm_id = company_info.get("Id", "")

                # Update client with realm_id
                self.db.update_client(client_id, qbo_realm_id=realm_id)

                self.db.log_action(
                    action="qbo_verified",
                    client_id=client_id,
                    actor_slack_id=user_id,
                    details={"realm_id": realm_id, "company_name": company_name}
                )

                blocks = build_qbo_verify_result_blocks(
                    success=True,
                    company_name=company_name,
                    realm_id=realm_id,
                    account_count=len(accounts)
                )

                client.chat_postMessage(
                    channel=user_id,
                    blocks=blocks,
                    text="QBO verification successful"
                )
            except Exception as e:
                logger.error(f"QBO verification failed: {e}")
                blocks = build_qbo_verify_result_blocks(
                    success=False,
                    error=str(e)
                )
                client.chat_postMessage(
                    channel=user_id,
                    blocks=blocks,
                    text="QBO verification failed"
                )

        # Request documents button
        @self.app.action("request_docs_btn")
        def handle_request_docs_btn(ack, body, client):
            ack()
            client_id = body["actions"][0]["value"]
            modal = build_request_docs_modal(client_id, ONBOARDING_DOC_PACK)
            client.views_open(trigger_id=body["trigger_id"], view=modal)

        # Request docs modal submission
        @self.app.view("request_docs_modal")
        def handle_request_docs_modal(ack, body, view, client):
            values = view["state"]["values"]
            metadata = json.loads(view.get("private_metadata", "{}"))
            client_id = metadata.get("client_id")

            selected_docs = values["docs_block"]["docs_select"]["selected_options"]
            period = values["period_block"]["period_input"].get("value")
            due_date = values["due_block"]["due_date_picker"].get("selected_date")
            custom_message = values["message_block"]["message_input"].get("value")

            ack()

            try:
                user_id = body["user"]["id"]

                for doc_option in selected_docs:
                    doc_type = doc_option["value"]
                    doc_desc = next(
                        (d["description"] for d in ONBOARDING_DOC_PACK if d["type"] == doc_type),
                        doc_type
                    )

                    self.db.create_doc_request(
                        client_id=client_id,
                        doc_type=doc_type,
                        period=period,
                        description=doc_desc,
                        requested_by=user_id,
                        due_date=due_date
                    )

                self.db.log_action(
                    action="docs_requested",
                    client_id=client_id,
                    actor_slack_id=user_id,
                    details={"count": len(selected_docs), "period": period}
                )

                client.chat_postMessage(
                    channel=user_id,
                    text=f"✅ {len(selected_docs)} document(s) requested."
                )
            except Exception as e:
                logger.error(f"Error creating doc requests: {e}")
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"❌ Error: {e}"
                )

        # Add system button
        @self.app.action("add_system_btn")
        def handle_add_system_btn(ack, body, client):
            ack()
            client_id = body["actions"][0]["value"]
            modal = build_add_system_modal(client_id)
            client.views_open(trigger_id=body["trigger_id"], view=modal)

        # Add system modal submission
        @self.app.view("add_system_modal")
        def handle_add_system_modal(ack, body, view, client):
            values = view["state"]["values"]
            metadata = json.loads(view.get("private_metadata", "{}"))
            client_id = metadata.get("client_id")

            system_type = values["type_block"]["type_select"]["selected_option"]["value"]
            system_name = values["name_block"]["name_input"].get("value")
            status = values["status_block"]["status_select"]["selected_option"]["value"]
            notes = values["notes_block"]["notes_input"].get("value")

            ack()

            try:
                self.db.add_system(
                    client_id=client_id,
                    system_type=system_type,
                    system_name=system_name,
                    status=status,
                    notes=notes
                )

                self.db.log_action(
                    action="system_added",
                    client_id=client_id,
                    actor_slack_id=body["user"]["id"],
                    details={"system_type": system_type}
                )

                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"✅ System '{system_type}' added."
                )
            except Exception as e:
                logger.error(f"Error adding system: {e}")
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"❌ Error: {e}"
                )

        # Set operating rules button
        @self.app.action("set_rules_btn")
        def handle_set_rules_btn(ack, body, client):
            ack()
            client_id = body["actions"][0]["value"]
            existing_rules = self.db.get_operating_rules(client_id)
            modal = build_operating_rules_modal(client_id, existing_rules)
            client.views_open(trigger_id=body["trigger_id"], view=modal)

        # Operating rules modal submission
        @self.app.view("operating_rules_modal")
        def handle_operating_rules_modal(ack, body, view, client):
            values = view["state"]["values"]
            metadata = json.loads(view.get("private_metadata", "{}"))
            client_id = metadata.get("client_id")

            threshold_str = values["threshold_block"]["threshold_input"]["value"]
            sla_hours = int(values["sla_block"]["sla_select"]["selected_option"]["value"])
            schedule = values["schedule_block"]["schedule_select"]["selected_option"]["value"]
            escalation = values["escalation_block"]["escalation_input"].get("value")
            notes = values["notes_block"]["notes_input"].get("value")

            ack()

            try:
                threshold = float(threshold_str.replace(",", "").replace("$", ""))

                self.db.set_operating_rules(
                    client_id=client_id,
                    approval_threshold=threshold,
                    response_sla_hours=sla_hours,
                    close_schedule=schedule,
                    escalation_contact=escalation,
                    notes=notes
                )

                self.db.log_action(
                    action="rules_set",
                    client_id=client_id,
                    actor_slack_id=body["user"]["id"],
                    details={"threshold": threshold, "sla": sla_hours}
                )

                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text="✅ Operating rules saved."
                )
            except Exception as e:
                logger.error(f"Error saving rules: {e}")
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"❌ Error: {e}"
                )

        # Advance phase button
        @self.app.action("advance_phase_btn")
        def handle_advance_phase(ack, body, client):
            ack()
            client_id = body["actions"][0]["value"]
            user_id = body["user"]["id"]

            result = self.state_machine.advance_phase(client_id)

            if result["success"]:
                self.db.log_action(
                    action="phase_advanced",
                    client_id=client_id,
                    actor_slack_id=user_id,
                    details=result
                )

                client.chat_postMessage(
                    channel=user_id,
                    text=f"✅ Advanced to Phase {result['phase']}: {result['phase_name']}\n_{result.get('description', '')}_"
                )
            else:
                blockers = result.get("blockers", [])
                blocker_text = "\n".join(f"• {b}" for b in blockers) if blockers else "Unknown"
                client.chat_postMessage(
                    channel=user_id,
                    text=f"⚠️ Cannot advance phase: {result.get('error', 'Unknown')}\n\n*Blockers:*\n{blocker_text}"
                )

        # Edit client button
        @self.app.action("edit_client_btn")
        def handle_edit_client_btn(ack, body, client):
            ack()
            client_id = body["actions"][0]["value"]
            # For now, just show the new client modal (could make a separate edit modal)
            from integrations.slack.blocks import build_new_client_modal
            modal = build_new_client_modal()
            modal["callback_id"] = "edit_client_modal"
            modal["private_metadata"] = json.dumps({"client_id": client_id})
            modal["title"]["text"] = "Edit Client"
            modal["submit"]["text"] = "Save"
            client.views_open(trigger_id=body["trigger_id"], view=modal)

    # -----------------------------------------------------------------------
    # Shortcuts (Message Actions)
    # -----------------------------------------------------------------------

    # -----------------------------------------------------------------------
    # Receipt Scanning Handlers
    # -----------------------------------------------------------------------

    def _register_receipt_handlers(self):
        """Register handlers for receipt scanning workflow"""
        from integrations.slack.blocks import (
            build_receipt_scanning_blocks,
            build_receipt_review_blocks,
            build_receipt_edit_modal,
        )

        # Doc-type classification dropdown
        @self.app.action(re.compile(r"^classify_doc_type_"))
        def handle_classify_doc_type(ack, body, client):
            ack()
            action = body["actions"][0]
            action_id = action["action_id"]
            slack_file_id = action_id.replace("classify_doc_type_", "")
            doc_type = action["selected_option"]["value"]
            user_id = body["user"]["id"]
            channel_id = body["channel"]["id"]
            message_ts = body["message"]["ts"]

            # Look up the original filename from the action context
            # Parse from the message blocks
            filename = "image"
            msg_blocks = body.get("message", {}).get("blocks", [])
            for blk in msg_blocks:
                txt = blk.get("text", {}).get("text", "")
                if "`" in txt:
                    # Extract filename from backtick-wrapped text
                    parts = txt.split("`")
                    if len(parts) >= 2:
                        filename = parts[1]
                        break

            # Create receipt DB entry
            receipt = self.db.create_receipt(
                doc_type=doc_type,
                original_filename=filename,
                slack_file_id=slack_file_id,
                slack_user_id=user_id,
                slack_channel_id=channel_id,
                slack_message_ts=message_ts,
            )
            receipt_id = receipt["id"]

            # Update message to show scanning status
            scanning_blocks = build_receipt_scanning_blocks(receipt_id, filename)
            client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text=f"Scanning {filename}...",
                blocks=scanning_blocks,
            )

            # Kick off background scan
            import threading
            thread = threading.Thread(
                target=self._process_receipt_scan,
                args=(receipt_id, slack_file_id, filename, doc_type, channel_id, message_ts),
                daemon=True,
            )
            thread.start()

        # Approve button
        @self.app.action(re.compile(r"^receipt_approve_"))
        def handle_receipt_approve(ack, body, client):
            ack()
            action = body["actions"][0]
            receipt_id = int(action["value"])
            user_id = body["user"]["id"]

            self.db.update_receipt(
                receipt_id,
                status="approved",
                reviewed_at=datetime.utcnow().isoformat(),
                reviewed_by=user_id,
            )

            # Update message
            client.chat_update(
                channel=body["channel"]["id"],
                ts=body["message"]["ts"],
                text=f"Receipt #{receipt_id} approved.",
                blocks=[{
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Receipt #{receipt_id} — Approved* by <@{user_id}>",
                    },
                }],
            )

        # Reject button
        @self.app.action(re.compile(r"^receipt_reject_"))
        def handle_receipt_reject(ack, body, client):
            ack()
            action = body["actions"][0]
            receipt_id = int(action["value"])
            user_id = body["user"]["id"]

            self.db.update_receipt(
                receipt_id,
                status="rejected",
                reviewed_at=datetime.utcnow().isoformat(),
                reviewed_by=user_id,
            )

            client.chat_update(
                channel=body["channel"]["id"],
                ts=body["message"]["ts"],
                text=f"Receipt #{receipt_id} rejected.",
                blocks=[{
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Receipt #{receipt_id} — Rejected* by <@{user_id}>",
                    },
                }],
            )

        # Edit button — open modal
        @self.app.action(re.compile(r"^receipt_edit_"))
        def handle_receipt_edit(ack, body, client):
            ack()
            action = body["actions"][0]
            receipt_id = int(action["value"])

            receipt = self.db.get_receipt(receipt_id)
            if not receipt:
                return

            extracted_data = {}
            if receipt.get("extracted_data"):
                try:
                    extracted_data = json.loads(receipt["extracted_data"])
                except (json.JSONDecodeError, TypeError):
                    pass

            modal = build_receipt_edit_modal(
                receipt_id=receipt_id,
                extracted_data=extracted_data,
                doc_type=receipt.get("doc_type", "other"),
            )
            client.views_open(trigger_id=body["trigger_id"], view=modal)

        # Edit modal submission
        @self.app.view("receipt_edit_modal")
        def handle_receipt_edit_modal(ack, body, view, client):
            values = view["state"]["values"]
            metadata = json.loads(view.get("private_metadata", "{}"))
            receipt_id = metadata.get("receipt_id")

            vendor = values["vendor_block"]["vendor_input"]["value"]
            date = values["date_block"]["date_input"]["value"]
            total_str = values["total_block"]["total_input"]["value"]
            tax_str = (values["tax_block"]["tax_input"].get("value") or "")
            category = (values["category_block"]["category_input"].get("value") or "")
            notes = (values["notes_block"]["notes_input"].get("value") or "")

            # Validate total
            try:
                total = float(total_str.replace(",", "").replace("$", ""))
            except ValueError:
                ack(response_action="errors", errors={"total_block": "Please enter a valid amount"})
                return

            tax = None
            if tax_str:
                try:
                    tax = float(tax_str.replace(",", "").replace("$", ""))
                except ValueError:
                    pass

            ack()

            # Build updated extracted data
            receipt = self.db.get_receipt(receipt_id)
            extracted_data = {}
            if receipt and receipt.get("extracted_data"):
                try:
                    extracted_data = json.loads(receipt["extracted_data"])
                except (json.JSONDecodeError, TypeError):
                    pass

            extracted_data.update({
                "vendor_name": vendor,
                "date": date,
                "total": total,
                "tax": tax,
                "category_suggestion": category,
                "notes": notes,
            })

            user_id = body["user"]["id"]
            self.db.update_receipt(
                receipt_id,
                status="approved",
                extracted_data=json.dumps(extracted_data),
                reviewed_at=datetime.utcnow().isoformat(),
                reviewed_by=user_id,
            )

            client.chat_postMessage(
                channel=user_id,
                text=f"Receipt #{receipt_id} updated and approved.",
            )

    def _process_receipt_scan(
        self,
        receipt_id: int,
        slack_file_id: str,
        filename: str,
        doc_type: str,
        channel_id: str,
        message_ts: str,
    ):
        """Background task: download from Slack, upload to Drive, scan with Vision, post review card."""
        from slack_sdk import WebClient
        from integrations.slack.blocks import build_receipt_review_blocks

        slack_client = WebClient(token=self.bot_token)

        try:
            # Update status to scanning
            self.db.update_receipt(receipt_id, status="scanning")

            # Download file from Slack
            file_info = slack_client.files_info(file=slack_file_id)
            file_url = file_info["file"]["url_private"]
            mime_type = file_info["file"].get("mimetype", "image/jpeg")

            import urllib.request
            req = urllib.request.Request(
                file_url,
                headers={"Authorization": f"Bearer {self.bot_token}"},
            )
            with urllib.request.urlopen(req) as resp:
                image_bytes = resp.read()

            logger.info(f"Downloaded {len(image_bytes)} bytes from Slack for receipt #{receipt_id} ({mime_type})")

            # Upload to Google Drive (best-effort)
            drive_file_id = None
            drive_folder_id = None
            try:
                from integrations.google_drive.client import get_drive_client

                drive = get_drive_client()
                if drive:
                    # Map doc_type to Drive folder name
                    folder_map = {
                        "expense_receipt": "Receipts",
                        "invoice": "Invoices",
                        "bill": "Bills",
                        "bank_statement": "Bank Statements",
                        "other": "Correspondence",
                    }
                    folder_name = folder_map.get(doc_type, "Receipts")

                    # Use first client or generic folder
                    clients = self.db.list_clients()
                    client_name = clients[0]["display_name"] if clients else "General"

                    drive_folder_id = drive.ensure_folder_structure(client_name, folder_name)
                    drive_file_id = drive.upload_bytes(
                        drive_folder_id, image_bytes, filename, mime_type
                    )
                    self.db.update_receipt(
                        receipt_id,
                        drive_file_id=drive_file_id,
                        drive_folder_id=drive_folder_id,
                    )
            except Exception as drive_err:
                logger.warning(f"Drive upload failed for receipt {receipt_id}: {drive_err}")

            # Scan with Claude Vision
            from qbo_copilot.receipt_scanner import scan_receipt, validate_extracted_data

            extracted_data, confidence = scan_receipt(image_bytes, mime_type, doc_type)
            validation = validate_extracted_data(extracted_data)

            # Save results
            self.db.update_receipt(
                receipt_id,
                status="scanned",
                extracted_data=json.dumps(extracted_data),
                confidence_score=confidence,
                scanned_at=datetime.utcnow().isoformat(),
            )

            # Post review card
            warnings = validation.get("warnings", []) + validation.get("errors", [])
            review_blocks = build_receipt_review_blocks(
                receipt_id=receipt_id,
                extracted_data=extracted_data,
                doc_type=doc_type,
                filename=filename,
                confidence=confidence,
                warnings=warnings if warnings else None,
            )

            slack_client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text=f"Receipt #{receipt_id} scanned — review below.",
                blocks=review_blocks,
            )

        except Exception as e:
            logger.error(f"Receipt scan failed for #{receipt_id}: {e}", exc_info=True)
            self.db.update_receipt(receipt_id, status="error", notes=str(e))

            try:
                slack_client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text=f"Receipt #{receipt_id} scan failed: {e}",
                    blocks=[{
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Receipt #{receipt_id} — Scan Failed*\n{e}",
                        },
                    }],
                )
            except Exception:
                pass

    def _register_shortcuts(self):
        """Register message shortcut handlers"""
        from integrations.slack.blocks import build_convert_to_case_modal, build_request_docs_modal

        # Convert to Case shortcut
        @self.app.shortcut("convert_to_case")
        def handle_convert_to_case(ack, shortcut, client):
            ack()

            message = shortcut.get("message", {})
            message_text = message.get("text", "")
            channel_id = shortcut.get("channel", {}).get("id", "")
            thread_ts = message.get("ts", "")

            # Get permalink
            try:
                permalink_resp = client.chat_getPermalink(
                    channel=channel_id,
                    message_ts=thread_ts
                )
                permalink = permalink_resp.get("permalink", "")
            except Exception:
                permalink = ""

            # Get clients for selector
            clients = self.db.list_clients()

            modal = build_convert_to_case_modal(
                message_text=message_text,
                channel_id=channel_id,
                thread_ts=thread_ts,
                permalink=permalink,
                clients=clients
            )

            client.views_open(trigger_id=shortcut["trigger_id"], view=modal)

        # Convert to case modal submission
        @self.app.view("convert_to_case_modal")
        def handle_convert_to_case_modal(ack, body, view, client):
            values = view["state"]["values"]
            metadata = json.loads(view.get("private_metadata", "{}"))

            title = values["title_block"]["title_input"]["value"]
            client_id = values["client_block"]["client_select"]["selected_option"]["value"]
            priority = values["priority_block"]["priority_select"]["selected_option"]["value"]
            description = values["description_block"]["description_input"].get("value")

            channel_id = metadata.get("channel_id")
            thread_ts = metadata.get("thread_ts")
            permalink = metadata.get("permalink")

            ack()

            try:
                case = self.db.create_case(
                    title=title,
                    client_id=client_id,
                    description=description,
                    priority=priority,
                    slack_channel_id=channel_id,
                    slack_thread_ts=thread_ts,
                    slack_permalink=permalink
                )

                self.db.log_action(
                    action="case_created",
                    client_id=client_id,
                    case_id=case["id"],
                    actor_slack_id=body["user"]["id"],
                    details={"title": title, "priority": priority},
                    slack_permalink=permalink
                )

                # Reply in thread
                if channel_id and thread_ts:
                    client.chat_postMessage(
                        channel=channel_id,
                        thread_ts=thread_ts,
                        text=f"📋 *Case #{case['id']} Created*\n_{title}_\nPriority: {priority}"
                    )

                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"✅ Case #{case['id']} created: {title}"
                )
            except Exception as e:
                logger.error(f"Error creating case: {e}")
                client.chat_postMessage(
                    channel=body["user"]["id"],
                    text=f"❌ Error creating case: {e}"
                )

        # Request docs shortcut
        @self.app.shortcut("request_docs")
        def handle_request_docs_shortcut(ack, shortcut, client):
            ack()

            # Try to detect client from channel
            channel_id = shortcut.get("channel", {}).get("id", "")
            detected_client = self.db.get_client_by_slack_channel(channel_id)

            clients = self.db.list_clients()

            if detected_client:
                # Pre-select the detected client
                modal = build_request_docs_modal(detected_client["id"], ONBOARDING_DOC_PACK)
            elif clients:
                # Use first client as default
                modal = build_request_docs_modal(clients[0]["id"], ONBOARDING_DOC_PACK)
            else:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=shortcut["user"]["id"],
                    text="No clients found. Create a client first."
                )
                return

            client.views_open(trigger_id=shortcut["trigger_id"], view=modal)

    def _build_home_blocks(self, user_id: str) -> list:
        """Build home tab blocks for a user"""
        from integrations.slack.blocks import (
            build_client_selector_blocks,
            build_onboarding_dashboard_blocks,
            build_waiting_queues_blocks,
            build_receipt_queue_summary_blocks,
            build_home_capabilities_blocks,
        )

        clients = self.db.list_clients()
        selected_client_id = self.user_selected_client.get(user_id)

        blocks = []
        blocks.extend(build_client_selector_blocks(clients, selected_client_id))
        blocks.append({"type": "divider"})

        if selected_client_id:
            selected_client = self.db.get_client(selected_client_id)
            if selected_client:
                progress = self.state_machine.get_overall_progress(selected_client_id)
                waiting_on_client = self.db.get_waiting_on_client()
                waiting_on_cpa = self.db.get_waiting_on_cpa()

                blocks.extend(build_onboarding_dashboard_blocks(
                    client=selected_client,
                    progress=progress,
                    waiting_on_client=waiting_on_client,
                    waiting_on_cpa=waiting_on_cpa
                ))
        else:
            waiting_on_client = self.db.get_waiting_on_client()
            waiting_on_cpa = self.db.get_waiting_on_cpa()
            blocks.extend(build_waiting_queues_blocks(waiting_on_client, waiting_on_cpa))

        # Receipt queue summary
        try:
            receipt_summary = self.db.get_receipt_queue_summary()
            blocks.extend(build_receipt_queue_summary_blocks(receipt_summary))
        except Exception:
            pass

        # Capabilities / help section
        blocks.extend(build_home_capabilities_blocks())

        return blocks[:100]  # Slack limit

    def start(self):
        """Start the Slack bot"""
        logger.info("Starting QBO Copilot Slack Bot (Claude + Block Kit)...")
        handler = SocketModeHandler(self.app, self.app_token)
        handler.start()


if __name__ == "__main__":
    from dotenv import load_dotenv

    # Load environment
    env_path = Path(__file__).parent.parent.parent / "config" / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()

    bot = CPACopilotSlackBot()
    bot.start()
