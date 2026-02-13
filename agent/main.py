#!/usr/bin/env python3
"""
QBO Copilot Agent

Main entry point for the AI agent that processes user requests
and interacts with QuickBooks Online.

This module is designed to work with OpenClaw or similar agent frameworks,
but can also be used standalone for testing.

Usage:
    # Standalone testing
    python agent/main.py

    # With OpenClaw (when available)
    # from openclaw import Agent
    # from agent.main import create_agent
    # agent = create_agent()
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Callable

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment
config_env = Path(__file__).parent.parent / "config" / ".env"
if config_env.exists():
    load_dotenv(config_env)
else:
    load_dotenv()

from agent.tools.qbo_tools import (
    qbo_query,
    qbo_get_accounts,
    qbo_get_customers,
    qbo_get_vendors,
    qbo_get_invoices,
    qbo_get_purchases,
    qbo_list_clients,
    qbo_switch_client,
    qbo_tools
)


# System prompt for the QBO Copilot agent
SYSTEM_PROMPT = """You are QBO Copilot, an AI assistant for Certified Public Accountants.

You help CPAs manage their clients' QuickBooks Online data through natural conversation.
You have access to the following tools:

**QBO Query Tools:**
- qbo_query: Execute any QBO Query Language query
- qbo_get_accounts: Get chart of accounts
- qbo_get_customers: Get customer list
- qbo_get_vendors: Get vendor list
- qbo_get_invoices: Get invoices (optionally unpaid only)
- qbo_get_purchases: Get expenses/purchases

**Client Management:**
- qbo_list_clients: List all configured QBO client companies
- qbo_switch_client: Switch to a different client company

**Guidelines:**
1. Always confirm which client company you're working with before queries
2. Format financial data clearly with proper currency formatting
3. When showing lists, limit to 10-15 items unless asked for more
4. Proactively suggest follow-up actions when appropriate
5. Keep responses concise but informative

**QBO Query Language Examples:**
- SELECT * FROM Account WHERE AccountType = 'Expense'
- SELECT * FROM Invoice WHERE Balance > 0
- SELECT * FROM Purchase WHERE TxnDate >= '2026-01-01'
- SELECT * FROM Customer WHERE DisplayName LIKE '%smith%'
"""


class CPACopilotAgent:
    """
    QBO Copilot Agent

    Handles natural language requests and executes QBO operations.
    Can be integrated with OpenClaw or used standalone.
    """

    def __init__(self, llm_callback: Optional[Callable] = None):
        """
        Initialize agent

        Args:
            llm_callback: Function to call for LLM responses
                         Signature: callback(prompt: str, tools: list) -> str
        """
        self.llm_callback = llm_callback
        self.tools = {
            'qbo_query': qbo_query,
            'qbo_get_accounts': qbo_get_accounts,
            'qbo_get_customers': qbo_get_customers,
            'qbo_get_vendors': qbo_get_vendors,
            'qbo_get_invoices': qbo_get_invoices,
            'qbo_get_purchases': qbo_get_purchases,
            'qbo_list_clients': qbo_list_clients,
            'qbo_switch_client': qbo_switch_client,
        }
        self.system_prompt = SYSTEM_PROMPT

    def process_message(self, message: str, context: Optional[Dict] = None) -> str:
        """
        Process a user message and return a response

        Args:
            message: User's natural language message
            context: Optional context (user_id, channel, etc.)

        Returns:
            Agent's response string
        """
        context = context or {}

        # If we have an LLM callback, use it
        if self.llm_callback:
            return self.llm_callback(
                message,
                self.system_prompt,
                self.tools,
                context
            )

        # Otherwise, use simple keyword matching for testing
        return self._simple_process(message, context)

    def _simple_process(self, message: str, context: Dict) -> str:
        """Simple keyword-based processing for testing without LLM"""
        message_lower = message.lower()

        try:
            # Client management
            if "switch" in message_lower and "client" in message_lower:
                # Extract client name (simple approach)
                words = message.split()
                if "to" in words:
                    idx = words.index("to")
                    if idx + 1 < len(words):
                        client_name = " ".join(words[idx + 1:])
                        result = qbo_switch_client(client_name)
                        if result.get('success'):
                            return f"✓ Switched to {result['name']}"
                        return f"Could not find client: {client_name}"

            if "list" in message_lower and "client" in message_lower:
                clients = qbo_list_clients()
                response = "**Configured QBO Clients:**\n\n"
                for client in clients:
                    current = " ← current" if client.get('is_current') else ""
                    response += f"• {client['name']}{current}\n"
                    response += f"  Realm: {client['realm_id']}\n"
                return response

            # Account queries
            if "account" in message_lower:
                account_type = None
                if "expense" in message_lower:
                    account_type = "Expense"
                elif "income" in message_lower:
                    account_type = "Income"
                elif "bank" in message_lower:
                    account_type = "Bank"

                accounts = qbo_get_accounts(account_type=account_type)
                response = f"**Found {len(accounts)} accounts"
                if account_type:
                    response += f" (type: {account_type})"
                response += ":**\n\n"

                for acc in accounts[:15]:
                    balance = acc.get('CurrentBalance', 0)
                    response += f"• {acc['Name']} ({acc['AccountType']}): ${balance:,.2f}\n"

                if len(accounts) > 15:
                    response += f"\n... and {len(accounts) - 15} more"
                return response

            # Customer queries
            if "customer" in message_lower:
                customers = qbo_get_customers()
                response = f"**Found {len(customers)} customers:**\n\n"
                for cust in customers[:15]:
                    balance = cust.get('Balance', 0)
                    response += f"• {cust.get('DisplayName', 'N/A')}: ${balance:,.2f}\n"
                if len(customers) > 15:
                    response += f"\n... and {len(customers) - 15} more"
                return response

            # Vendor queries
            if "vendor" in message_lower:
                vendors = qbo_get_vendors()
                response = f"**Found {len(vendors)} vendors:**\n\n"
                for vendor in vendors[:15]:
                    balance = vendor.get('Balance', 0)
                    response += f"• {vendor.get('DisplayName', 'N/A')}: ${balance:,.2f}\n"
                if len(vendors) > 15:
                    response += f"\n... and {len(vendors) - 15} more"
                return response

            # Invoice queries
            if "invoice" in message_lower:
                unpaid_only = "unpaid" in message_lower or "outstanding" in message_lower
                invoices = qbo_get_invoices(unpaid_only=unpaid_only)
                label = "unpaid invoices" if unpaid_only else "invoices"
                response = f"**Found {len(invoices)} {label}:**\n\n"
                for inv in invoices[:15]:
                    customer = inv.get('CustomerRef', {}).get('name', 'N/A')
                    total = inv.get('TotalAmt', 0)
                    balance = inv.get('Balance', 0)
                    response += f"• #{inv.get('DocNumber', 'N/A')} - {customer}: ${total:,.2f}"
                    if unpaid_only:
                        response += f" (balance: ${balance:,.2f})"
                    response += "\n"
                if len(invoices) > 15:
                    response += f"\n... and {len(invoices) - 15} more"
                return response

            # Purchase/expense queries
            if "purchase" in message_lower or "expense" in message_lower:
                purchases = qbo_get_purchases()
                response = f"**Found {len(purchases)} purchases/expenses:**\n\n"
                for purch in purchases[:15]:
                    vendor = purch.get('EntityRef', {}).get('name', 'N/A')
                    total = purch.get('TotalAmt', 0)
                    date = purch.get('TxnDate', 'N/A')
                    response += f"• {date} - {vendor}: ${total:,.2f}\n"
                if len(purchases) > 15:
                    response += f"\n... and {len(purchases) - 15} more"
                return response

            # Help
            if "help" in message_lower:
                return """**QBO Copilot Help**

I can help you with QuickBooks Online queries:

• **Accounts**: "show me expense accounts", "list all accounts"
• **Customers**: "show customers", "list customer balances"
• **Vendors**: "show vendors"
• **Invoices**: "show unpaid invoices", "list all invoices"
• **Purchases**: "show recent expenses"
• **Clients**: "list clients", "switch to Acme Corp"

Just ask in natural language!"""

            # Default response
            return """I'm QBO Copilot. I can help you query QuickBooks Online data.

Try asking:
• "Show me expense accounts"
• "List unpaid invoices"
• "Show customers"
• "List clients"

Type "help" for more options."""

        except Exception as e:
            return f"Error processing request: {str(e)}"


def create_agent(llm_callback: Optional[Callable] = None) -> CPACopilotAgent:
    """
    Factory function to create a QBO Copilot agent

    Args:
        llm_callback: Optional LLM callback for OpenClaw integration

    Returns:
        Configured CPACopilotAgent instance
    """
    return CPACopilotAgent(llm_callback=llm_callback)


# Interactive CLI for testing
if __name__ == "__main__":
    print("=" * 60)
    print("QBO Copilot - Interactive Mode")
    print("=" * 60)
    print("\nType 'quit' to exit, 'help' for commands\n")

    agent = create_agent()

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ('quit', 'exit', 'q'):
                print("Goodbye!")
                break

            response = agent.process_message(user_input)
            print(f"\nQBO Copilot:\n{response}\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
