#!/usr/bin/env python3
"""
Multi-Tenant QBO Support for CPA Copilot

Manages multiple QBO client companies under a single CPA's OAuth connection.

Configuration file (config/clients.yaml):
    clients:
      - name: "Acme Corp"
        realm_id: "1234567890"
        primary_contact: "john@acme.com"
        slack_channel: "#acme-accounting"

      - name: "Beta Industries"
        realm_id: "0987654321"
        primary_contact: "jane@beta.com"
        slack_channel: "#beta-accounting"

Usage:
    from qbo.multi_tenant import TenantManager

    manager = TenantManager()
    clients = manager.list_clients()

    # Get QBO client for specific company
    qbo = manager.get_client("Acme Corp")
    accounts = qbo.get_accounts()
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional
from .client import QBOClient


class ClientConfig:
    """Configuration for a single QBO client company"""

    def __init__(self, config: Dict):
        self.name = config['name']
        self.realm_id = config['realm_id']
        self.primary_contact = config.get('primary_contact')
        self.slack_channel = config.get('slack_channel')
        self.teams_channel = config.get('teams_channel')
        self.metadata = config.get('metadata', {})

    def __repr__(self):
        return f"ClientConfig(name={self.name}, realm_id={self.realm_id})"


class TenantManager:
    """Manages multiple QBO client companies"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize TenantManager

        Args:
            config_path: Path to clients.yaml (default: config/clients.yaml)
        """
        self.config_dir = Path(__file__).parent.parent / "config"
        self.config_path = config_path or self.config_dir / "clients.yaml"
        self._clients: Dict[str, ClientConfig] = {}
        self._qbo_clients: Dict[str, QBOClient] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load client configuration from YAML"""
        if not self.config_path.exists():
            # Create default config
            default_config = {
                'clients': [
                    {
                        'name': 'Sandbox Company',
                        'realm_id': '9341456144523072',
                        'primary_contact': 'sandbox@example.com',
                        'slack_channel': '#qbo-sandbox'
                    }
                ]
            }
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                yaml.dump(default_config, f, default_flow_style=False)

        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        for client_config in config.get('clients', []):
            client = ClientConfig(client_config)
            self._clients[client.name.lower()] = client
            self._clients[client.realm_id] = client

    def list_clients(self) -> List[ClientConfig]:
        """List all configured client companies"""
        # Return unique clients (avoid duplicates from name/realm_id mapping)
        seen = set()
        clients = []
        for client in self._clients.values():
            if client.realm_id not in seen:
                seen.add(client.realm_id)
                clients.append(client)
        return clients

    def get_client_config(self, identifier: str) -> Optional[ClientConfig]:
        """
        Get client configuration by name or realm_id

        Args:
            identifier: Client name or realm_id

        Returns:
            ClientConfig or None if not found
        """
        return self._clients.get(identifier.lower()) or self._clients.get(identifier)

    def get_client(self, identifier: str) -> QBOClient:
        """
        Get QBO client for a specific company

        Args:
            identifier: Client name or realm_id

        Returns:
            QBOClient configured for the specified company

        Raises:
            ValueError: If client not found
        """
        config = self.get_client_config(identifier)
        if not config:
            raise ValueError(f"Client not found: {identifier}")

        # Cache QBO clients
        if config.realm_id not in self._qbo_clients:
            self._qbo_clients[config.realm_id] = QBOClient(realm_id=config.realm_id)

        return self._qbo_clients[config.realm_id]

    def find_client_by_channel(self, channel: str) -> Optional[ClientConfig]:
        """
        Find client by Slack/Teams channel

        Args:
            channel: Channel name (e.g., "#acme-accounting")

        Returns:
            ClientConfig or None
        """
        for client in self.list_clients():
            if client.slack_channel == channel or client.teams_channel == channel:
                return client
        return None

    def add_client(
        self,
        name: str,
        realm_id: str,
        primary_contact: Optional[str] = None,
        slack_channel: Optional[str] = None
    ) -> ClientConfig:
        """
        Add a new client company

        Args:
            name: Company display name
            realm_id: QBO realm ID
            primary_contact: Primary contact email
            slack_channel: Associated Slack channel

        Returns:
            ClientConfig for the new client
        """
        client_data = {
            'name': name,
            'realm_id': realm_id,
            'primary_contact': primary_contact,
            'slack_channel': slack_channel
        }

        client = ClientConfig(client_data)
        self._clients[name.lower()] = client
        self._clients[realm_id] = client

        # Save to config file
        self._save_config()

        return client

    def _save_config(self) -> None:
        """Save current configuration to YAML"""
        clients_list = []
        seen = set()

        for client in self._clients.values():
            if client.realm_id not in seen:
                seen.add(client.realm_id)
                clients_list.append({
                    'name': client.name,
                    'realm_id': client.realm_id,
                    'primary_contact': client.primary_contact,
                    'slack_channel': client.slack_channel,
                    'teams_channel': client.teams_channel,
                    'metadata': client.metadata
                })

        config = {'clients': clients_list}
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)


# CLI interface
if __name__ == '__main__':
    manager = TenantManager()

    print("Configured QBO Clients:")
    print("=" * 50)
    for client in manager.list_clients():
        print(f"\n  {client.name}")
        print(f"    Realm ID: {client.realm_id}")
        print(f"    Contact: {client.primary_contact}")
        print(f"    Slack: {client.slack_channel}")
