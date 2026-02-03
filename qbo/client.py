#!/usr/bin/env python3
"""
QBO API Client for CPA Copilot

Provides direct access to QuickBooks Online API with:
- SQL-like query language support
- Automatic OAuth token refresh
- Multi-tenant support (multiple client companies)

Usage:
    from qbo.client import QBOClient

    client = QBOClient()
    accounts = client.query("SELECT * FROM Account WHERE Active = true")

    # Multi-tenant: query specific company
    client = QBOClient(realm_id="1234567890")
    customers = client.query("SELECT * FROM Customer")
"""

import json
import os
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List


class QBOClient:
    """QuickBooks Online API Client"""

    SANDBOX_BASE_URL = "https://sandbox-quickbooks.api.intuit.com"
    PRODUCTION_BASE_URL = "https://quickbooks.api.intuit.com"
    TOKEN_ENDPOINT = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

    def __init__(
        self,
        realm_id: Optional[str] = None,
        tokens_file: Optional[Path] = None,
        environment: str = "sandbox"
    ):
        """
        Initialize QBO Client

        Args:
            realm_id: QBO company ID (uses default from tokens if not provided)
            tokens_file: Path to tokens.json (default: config/tokens/{realm_id}.json)
            environment: "sandbox" or "production"
        """
        self.environment = environment or os.getenv("QBO_ENVIRONMENT", "sandbox")
        self.base_url = (
            self.SANDBOX_BASE_URL if self.environment == "sandbox"
            else self.PRODUCTION_BASE_URL
        )

        # Load credentials
        self.client_id = os.getenv("QBO_CLIENT_ID")
        self.client_secret = os.getenv("QBO_CLIENT_SECRET")

        if not self.client_id or not self.client_secret:
            raise ValueError("QBO_CLIENT_ID and QBO_CLIENT_SECRET must be set")

        # Set up token storage
        self.config_dir = Path(__file__).parent.parent / "config"
        self.tokens_dir = self.config_dir / "tokens"
        self.tokens_dir.mkdir(parents=True, exist_ok=True)

        # Load tokens
        self.realm_id = realm_id
        self.tokens_file = tokens_file
        self._tokens = None
        self._load_tokens()

    def _load_tokens(self) -> None:
        """Load OAuth tokens from file"""
        if self.tokens_file and self.tokens_file.exists():
            with open(self.tokens_file) as f:
                self._tokens = json.load(f)
        elif self.realm_id:
            token_path = self.tokens_dir / f"{self.realm_id}.json"
            if token_path.exists():
                with open(token_path) as f:
                    self._tokens = json.load(f)
                self.tokens_file = token_path
        else:
            # Try default tokens file
            default_path = self.tokens_dir / "default.json"
            if default_path.exists():
                with open(default_path) as f:
                    self._tokens = json.load(f)
                self.realm_id = self._tokens.get("realmId")
                self.tokens_file = default_path

        if self._tokens and not self.realm_id:
            self.realm_id = self._tokens.get("realmId")

    def _save_tokens(self) -> None:
        """Save OAuth tokens to file"""
        if not self.tokens_file:
            self.tokens_file = self.tokens_dir / f"{self.realm_id}.json"

        with open(self.tokens_file, 'w') as f:
            json.dump(self._tokens, f, indent=2)

    def refresh_access_token(self) -> bool:
        """
        Refresh the access token using the refresh token

        Returns:
            bool: True if refresh successful
        """
        if not self._tokens or 'refresh_token' not in self._tokens:
            raise ValueError("No refresh token available")

        response = requests.post(
            self.TOKEN_ENDPOINT,
            data={
                'grant_type': 'refresh_token',
                'refresh_token': self._tokens['refresh_token']
            },
            auth=(self.client_id, self.client_secret),
            headers={'Accept': 'application/json'}
        )

        if response.status_code == 200:
            new_tokens = response.json()
            new_tokens['realmId'] = self.realm_id
            self._tokens = new_tokens
            self._save_tokens()
            return True
        else:
            raise Exception(f"Token refresh failed: {response.status_code} - {response.text}")

    def query(self, query_string: str, auto_refresh: bool = True) -> Dict[str, Any]:
        """
        Execute a query against the QBO API

        Args:
            query_string: SQL-like query (e.g., "SELECT * FROM Account")
            auto_refresh: Automatically refresh token if expired

        Returns:
            dict: API response

        Raises:
            ValueError: If not authenticated
            Exception: On API error
        """
        if not self._tokens or not self.realm_id:
            raise ValueError("Not authenticated. Call authenticate() first.")

        url = f"{self.base_url}/v3/company/{self.realm_id}/query"
        headers = {
            'Authorization': f"Bearer {self._tokens['access_token']}",
            'Accept': 'application/json',
            'Content-Type': 'application/text'
        }

        response = requests.get(url, headers=headers, params={'query': query_string})

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401 and auto_refresh:
            # Token expired, try refresh
            self.refresh_access_token()
            headers['Authorization'] = f"Bearer {self._tokens['access_token']}"
            response = requests.get(url, headers=headers, params={'query': query_string})
            if response.status_code == 200:
                return response.json()

        raise Exception(f"Query failed: {response.status_code} - {response.text}")

    def get_accounts(self, active_only: bool = True) -> List[Dict]:
        """Get all accounts (Chart of Accounts)"""
        query = "SELECT * FROM Account"
        if active_only:
            query += " WHERE Active = true"
        result = self.query(query)
        return result.get('QueryResponse', {}).get('Account', [])

    def get_customers(self, active_only: bool = True) -> List[Dict]:
        """Get all customers"""
        query = "SELECT * FROM Customer"
        if active_only:
            query += " WHERE Active = true"
        result = self.query(query)
        return result.get('QueryResponse', {}).get('Customer', [])

    def get_vendors(self, active_only: bool = True) -> List[Dict]:
        """Get all vendors"""
        query = "SELECT * FROM Vendor"
        if active_only:
            query += " WHERE Active = true"
        result = self.query(query)
        return result.get('QueryResponse', {}).get('Vendor', [])

    def get_invoices(self, unpaid_only: bool = False) -> List[Dict]:
        """Get invoices"""
        query = "SELECT * FROM Invoice"
        result = self.query(query)
        invoices = result.get('QueryResponse', {}).get('Invoice', [])

        # Filter unpaid in Python (QBO doesn't support > operator for Balance)
        if unpaid_only:
            invoices = [inv for inv in invoices if inv.get('Balance', 0) > 0]

        return invoices

    def get_purchases(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """Get purchases (expenses)"""
        query = "SELECT * FROM Purchase"
        conditions = []
        if start_date:
            conditions.append(f"TxnDate >= '{start_date}'")
        if end_date:
            conditions.append(f"TxnDate <= '{end_date}'")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        result = self.query(query)
        return result.get('QueryResponse', {}).get('Purchase', [])


# CLI interface for testing
if __name__ == '__main__':
    import sys
    from dotenv import load_dotenv

    # Load environment
    env_path = Path(__file__).parent.parent / "config" / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python client.py <query|accounts|customers|vendors>")
        sys.exit(1)

    client = QBOClient()
    command = sys.argv[1].lower()

    if command == 'query' and len(sys.argv) > 2:
        result = client.query(sys.argv[2])
        print(json.dumps(result, indent=2))
    elif command == 'accounts':
        accounts = client.get_accounts()
        print(f"Found {len(accounts)} accounts")
        for acc in accounts[:10]:
            print(f"  [{acc['Id']}] {acc['Name']} - {acc['AccountType']}")
    elif command == 'customers':
        customers = client.get_customers()
        print(f"Found {len(customers)} customers")
        for cust in customers[:10]:
            print(f"  [{cust['Id']}] {cust.get('DisplayName', 'N/A')}")
    elif command == 'vendors':
        vendors = client.get_vendors()
        print(f"Found {len(vendors)} vendors")
        for vendor in vendors[:10]:
            print(f"  [{vendor['Id']}] {vendor.get('DisplayName', 'N/A')}")
    else:
        print(f"Unknown command: {command}")
