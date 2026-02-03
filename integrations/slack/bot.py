#!/usr/bin/env python3
"""
Slack Bot for QBO Copilot

Connects the QBO Copilot agent to Slack using Socket Mode.
Users can interact with the agent through:
- Direct messages
- Channel mentions (@QBO Copilot)
- Slash commands (/qbo)

Setup:
1. Create Slack App at https://api.slack.com/apps
2. Enable Socket Mode
3. Add Bot Token Scopes: chat:write, app_mentions:read, im:history, im:read
4. Install to workspace
5. Set SLACK_BOT_TOKEN and SLACK_APP_TOKEN in .env

Usage:
    python integrations/slack/bot.py
"""

import os
import re
import logging
from typing import Optional
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CPACopilotSlackBot:
    """Slack bot that interfaces with QBO Copilot agent"""

    def __init__(self, agent_callback=None):
        """
        Initialize Slack bot

        Args:
            agent_callback: Function to call for agent responses
                           Signature: callback(message: str, context: dict) -> str
        """
        self.bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.app_token = os.getenv("SLACK_APP_TOKEN")

        if not self.bot_token or not self.app_token:
            raise ValueError("SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set")

        self.app = App(token=self.bot_token)
        self.agent_callback = agent_callback or self._default_callback
        self._register_handlers()

    def _default_callback(self, message: str, context: dict) -> str:
        """Default callback when no agent is configured"""
        return f"Received: {message}\n\n(Agent not configured - this is a test response)"

    def _register_handlers(self):
        """Register Slack event handlers"""

        # Handle direct messages
        @self.app.event("message")
        def handle_message(event, say, client):
            # Ignore bot messages
            if event.get("bot_id"):
                return

            # Only respond to DMs (channel type "im")
            if event.get("channel_type") != "im":
                return

            message = event.get("text", "")
            user_id = event.get("user")
            channel = event.get("channel")

            logger.info(f"DM from {user_id}: {message}")

            # Get user info for context
            user_info = client.users_info(user=user_id)
            user_name = user_info["user"]["real_name"]

            context = {
                "user_id": user_id,
                "user_name": user_name,
                "channel": channel,
                "channel_type": "dm"
            }

            # Get agent response
            response = self.agent_callback(message, context)
            say(response)

        # Handle @mentions
        @self.app.event("app_mention")
        def handle_mention(event, say, client):
            message = event.get("text", "")
            user_id = event.get("user")
            channel = event.get("channel")

            # Remove bot mention from message
            message = re.sub(r"<@[A-Z0-9]+>\s*", "", message).strip()

            logger.info(f"Mention from {user_id} in {channel}: {message}")

            # Get user info
            user_info = client.users_info(user=user_id)
            user_name = user_info["user"]["real_name"]

            context = {
                "user_id": user_id,
                "user_name": user_name,
                "channel": channel,
                "channel_type": "channel"
            }

            response = self.agent_callback(message, context)
            say(response)

        # Slash command: /qbo
        @self.app.command("/qbo")
        def handle_qbo_command(ack, respond, command):
            ack()

            query = command.get("text", "").strip()
            user_id = command.get("user_id")
            channel = command.get("channel_id")

            if not query:
                respond("Usage: `/qbo <query or question>`\n\nExamples:\n"
                       "• `/qbo show me expense accounts`\n"
                       "• `/qbo list unpaid invoices`\n"
                       "• `/qbo what's the balance of checking account?`")
                return

            logger.info(f"/qbo command from {user_id}: {query}")

            context = {
                "user_id": user_id,
                "channel": channel,
                "channel_type": "slash_command"
            }

            response = self.agent_callback(query, context)
            respond(response)

        # Slash command: /qbo-client
        @self.app.command("/qbo-client")
        def handle_client_command(ack, respond, command):
            ack()

            args = command.get("text", "").strip()

            if not args:
                # List clients
                respond("Use `/qbo-client <client name>` to switch companies.\n\n"
                       "Available clients will be shown by the agent.")
                return

            context = {
                "user_id": command.get("user_id"),
                "channel": command.get("channel_id"),
                "channel_type": "slash_command"
            }

            response = self.agent_callback(f"switch to client: {args}", context)
            respond(response)

    def start(self):
        """Start the Slack bot"""
        logger.info("Starting QBO Copilot Slack Bot...")
        handler = SocketModeHandler(self.app, self.app_token)
        handler.start()


# Example agent callback (replace with actual agent)
def example_agent_callback(message: str, context: dict) -> str:
    """
    Example callback - replace with actual agent integration

    In production, this would:
    1. Send message to OpenClaw/Claude agent
    2. Agent uses QBO tools to query data
    3. Return formatted response
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from agent.tools.qbo_tools import qbo_get_accounts, qbo_list_clients

    # Simple keyword matching for demo
    message_lower = message.lower()

    if "account" in message_lower:
        accounts = qbo_get_accounts()
        response = f"Found {len(accounts)} accounts:\n\n"
        for acc in accounts[:10]:
            balance = acc.get('CurrentBalance', 0)
            response += f"• {acc['Name']} ({acc['AccountType']}): ${balance:,.2f}\n"
        if len(accounts) > 10:
            response += f"\n... and {len(accounts) - 10} more"
        return response

    elif "client" in message_lower:
        clients = qbo_list_clients()
        response = "Configured QBO clients:\n\n"
        for client in clients:
            current = " *(current)*" if client.get('is_current') else ""
            response += f"• {client['name']}{current}\n"
        return response

    else:
        return (f"I received your message: \"{message}\"\n\n"
                f"I can help with QuickBooks Online queries. Try:\n"
                f"• `show me accounts`\n"
                f"• `list clients`\n"
                f"• `get unpaid invoices`")


if __name__ == "__main__":
    from dotenv import load_dotenv

    # Load environment
    env_path = Path(__file__).parent.parent.parent / "config" / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()

    # Start bot with example callback
    bot = CPACopilotSlackBot(agent_callback=example_agent_callback)
    bot.start()
