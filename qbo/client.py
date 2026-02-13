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

    # Default tax code for invoices (can be overridden via environment or parameter)
    # Common codes: "2" = Exempt, "5" = HST ON (13%), "3" = Zero-rated
    DEFAULT_TAX_CODE = "2"  # Exempt by default

    def __init__(
        self,
        realm_id: Optional[str] = None,
        tokens_file: Optional[Path] = None,
        environment: Optional[str] = None,
        default_tax_code: Optional[str] = None
    ):
        """
        Initialize QBO Client

        Args:
            realm_id: QBO company ID (uses default from tokens if not provided)
            tokens_file: Path to tokens.json (default: config/tokens/{realm_id}.json)
            environment: "sandbox" or "production"
            default_tax_code: Default tax code ID for invoices (default: "2" = Exempt)
        """
        self.environment = environment or os.getenv("QBO_ENVIRONMENT", "sandbox")
        self.default_tax_code = default_tax_code or os.getenv("QBO_DEFAULT_TAX_CODE", self.DEFAULT_TAX_CODE)
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

    # =========================================================================
    # CRUD Operations - Create, Update, Delete
    # =========================================================================

    def _api_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        auto_refresh: bool = True
    ) -> Dict[str, Any]:
        """
        Make an API request to QBO

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint path (e.g., "invoice", "customer/123")
            data: Request body for POST requests
            auto_refresh: Automatically refresh token if expired

        Returns:
            dict: API response
        """
        if not self._tokens or not self.realm_id:
            raise ValueError("Not authenticated. Call authenticate() first.")

        url = f"{self.base_url}/v3/company/{self.realm_id}/{endpoint}"
        headers = {
            'Authorization': f"Bearer {self._tokens['access_token']}",
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        if method.upper() == 'GET':
            response = requests.get(url, headers=headers)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        if response.status_code in (200, 201):
            return response.json()
        elif response.status_code == 401 and auto_refresh:
            # Token expired, try refresh
            self.refresh_access_token()
            headers['Authorization'] = f"Bearer {self._tokens['access_token']}"
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers)
            if response.status_code in (200, 201):
                return response.json()

        raise Exception(f"API request failed: {response.status_code} - {response.text}")

    def get_entity(self, entity_type: str, entity_id: str) -> Dict[str, Any]:
        """
        Get a single entity by ID

        Args:
            entity_type: Entity type (Invoice, Customer, Vendor, etc.)
            entity_id: Entity ID

        Returns:
            dict: Entity data
        """
        result = self._api_request('GET', f"{entity_type.lower()}/{entity_id}")
        return result.get(entity_type, result)

    # -------------------------------------------------------------------------
    # Customer Operations
    # -------------------------------------------------------------------------

    def create_customer(
        self,
        display_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        company_name: Optional[str] = None,
        billing_address: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a new customer

        Args:
            display_name: Customer display name (required, must be unique)
            email: Primary email address
            phone: Primary phone number
            company_name: Company name
            billing_address: Billing address dict with keys:
                Line1, City, CountrySubDivisionCode (state), PostalCode

        Returns:
            dict: Created customer data with Id
        """
        customer_data = {
            "DisplayName": display_name
        }

        if email:
            customer_data["PrimaryEmailAddr"] = {"Address": email}
        if phone:
            customer_data["PrimaryPhone"] = {"FreeFormNumber": phone}
        if company_name:
            customer_data["CompanyName"] = company_name
        if billing_address:
            customer_data["BillAddr"] = billing_address

        result = self._api_request('POST', 'customer', customer_data)
        return result.get('Customer', result)

    def update_customer(
        self,
        customer_id: str,
        sync_token: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        company_name: Optional[str] = None,
        active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Update an existing customer

        Args:
            customer_id: Customer ID to update
            sync_token: Current SyncToken (for optimistic locking)
            display_name: New display name
            email: New email address
            phone: New phone number
            company_name: New company name
            active: Set active status

        Returns:
            dict: Updated customer data
        """
        # Start with required fields
        customer_data = {
            "Id": customer_id,
            "SyncToken": sync_token,
            "sparse": True  # Sparse update - only update provided fields
        }

        if display_name is not None:
            customer_data["DisplayName"] = display_name
        if email is not None:
            customer_data["PrimaryEmailAddr"] = {"Address": email}
        if phone is not None:
            customer_data["PrimaryPhone"] = {"FreeFormNumber": phone}
        if company_name is not None:
            customer_data["CompanyName"] = company_name
        if active is not None:
            customer_data["Active"] = active

        result = self._api_request('POST', 'customer', customer_data)
        return result.get('Customer', result)

    # -------------------------------------------------------------------------
    # Vendor Operations
    # -------------------------------------------------------------------------

    def create_vendor(
        self,
        display_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new vendor

        Args:
            display_name: Vendor display name (required, must be unique)
            email: Primary email address
            phone: Primary phone number
            company_name: Company name

        Returns:
            dict: Created vendor data with Id
        """
        vendor_data = {
            "DisplayName": display_name
        }

        if email:
            vendor_data["PrimaryEmailAddr"] = {"Address": email}
        if phone:
            vendor_data["PrimaryPhone"] = {"FreeFormNumber": phone}
        if company_name:
            vendor_data["CompanyName"] = company_name

        result = self._api_request('POST', 'vendor', vendor_data)
        return result.get('Vendor', result)

    def update_vendor(
        self,
        vendor_id: str,
        sync_token: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Update an existing vendor

        Args:
            vendor_id: Vendor ID to update
            sync_token: Current SyncToken
            display_name: New display name
            email: New email address
            phone: New phone number
            active: Set active status

        Returns:
            dict: Updated vendor data
        """
        vendor_data = {
            "Id": vendor_id,
            "SyncToken": sync_token,
            "sparse": True
        }

        if display_name is not None:
            vendor_data["DisplayName"] = display_name
        if email is not None:
            vendor_data["PrimaryEmailAddr"] = {"Address": email}
        if phone is not None:
            vendor_data["PrimaryPhone"] = {"FreeFormNumber": phone}
        if active is not None:
            vendor_data["Active"] = active

        result = self._api_request('POST', 'vendor', vendor_data)
        return result.get('Vendor', result)

    # -------------------------------------------------------------------------
    # Invoice Operations
    # -------------------------------------------------------------------------

    def create_invoice(
        self,
        customer_id: str,
        line_items: List[Dict[str, Any]],
        due_date: Optional[str] = None,
        doc_number: Optional[str] = None,
        customer_memo: Optional[str] = None,
        tax_code_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new invoice

        Args:
            customer_id: Customer ID to bill
            line_items: List of line items, each with:
                - description: Line description
                - amount: Line amount
                - detail_type: "SalesItemLineDetail" (default) or "DescriptionOnly"
                - item_id: Optional item/service ID
                - quantity: Optional quantity (default 1)
                - unit_price: Optional unit price
                - tax_code_id: Optional tax code ID for this line
            due_date: Due date in YYYY-MM-DD format
            doc_number: Invoice number (auto-generated if not provided)
            customer_memo: Memo to customer
            tax_code_id: Default tax code ID for all lines (e.g., "5" for HST ON, "2" for Exempt).
                         If not provided, uses client's default_tax_code setting.

        Returns:
            dict: Created invoice data with Id and DocNumber
        """
        # Use client default if no tax code specified
        effective_tax_code = tax_code_id or self.default_tax_code

        # Build line items
        lines = []
        for idx, item in enumerate(line_items):
            line = {
                "Id": str(idx + 1),
                "DetailType": item.get("detail_type", "SalesItemLineDetail"),
                "Amount": item.get("amount", 0),
                "Description": item.get("description", "")
            }

            if line["DetailType"] == "SalesItemLineDetail":
                line["SalesItemLineDetail"] = {
                    "Qty": item.get("quantity", 1),
                    "UnitPrice": item.get("unit_price", item.get("amount", 0))
                }
                if item.get("item_id"):
                    line["SalesItemLineDetail"]["ItemRef"] = {"value": str(item["item_id"])}

                # Apply tax code (line-level overrides invoice-level, which overrides client default)
                line_tax_code = item.get("tax_code_id") or effective_tax_code
                if line_tax_code:
                    line["SalesItemLineDetail"]["TaxCodeRef"] = {"value": str(line_tax_code)}

            lines.append(line)

        invoice_data = {
            "CustomerRef": {"value": str(customer_id)},
            "Line": lines
        }

        if due_date:
            invoice_data["DueDate"] = due_date
        if doc_number:
            invoice_data["DocNumber"] = doc_number
        if customer_memo:
            invoice_data["CustomerMemo"] = {"value": customer_memo}

        result = self._api_request('POST', 'invoice', invoice_data)
        return result.get('Invoice', result)

    def update_invoice(
        self,
        invoice_id: str,
        sync_token: str,
        line_items: Optional[List[Dict[str, Any]]] = None,
        due_date: Optional[str] = None,
        customer_memo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing invoice

        Args:
            invoice_id: Invoice ID to update
            sync_token: Current SyncToken
            line_items: New line items (replaces all existing lines)
            due_date: New due date
            customer_memo: New customer memo

        Returns:
            dict: Updated invoice data
        """
        # For invoice updates, we need the full invoice data
        # Get current invoice first
        current = self.get_entity('Invoice', invoice_id)

        invoice_data = {
            "Id": invoice_id,
            "SyncToken": sync_token,
            "sparse": True
        }

        if line_items is not None:
            lines = []
            for idx, item in enumerate(line_items):
                line = {
                    "Id": str(idx + 1),
                    "DetailType": item.get("detail_type", "SalesItemLineDetail"),
                    "Amount": item.get("amount", 0),
                    "Description": item.get("description", "")
                }
                if line["DetailType"] == "SalesItemLineDetail":
                    line["SalesItemLineDetail"] = {
                        "Qty": item.get("quantity", 1),
                        "UnitPrice": item.get("unit_price", item.get("amount", 0))
                    }
                    if item.get("item_id"):
                        line["SalesItemLineDetail"]["ItemRef"] = {"value": str(item["item_id"])}
                lines.append(line)
            invoice_data["Line"] = lines

        if due_date is not None:
            invoice_data["DueDate"] = due_date
        if customer_memo is not None:
            invoice_data["CustomerMemo"] = {"value": customer_memo}

        result = self._api_request('POST', 'invoice', invoice_data)
        return result.get('Invoice', result)

    def void_invoice(self, invoice_id: str, sync_token: str) -> Dict[str, Any]:
        """
        Void an invoice (cannot be undone)

        Args:
            invoice_id: Invoice ID to void
            sync_token: Current SyncToken

        Returns:
            dict: Voided invoice data
        """
        # QBO uses a special endpoint for voiding
        invoice_data = {
            "Id": invoice_id,
            "SyncToken": sync_token
        }

        result = self._api_request('POST', 'invoice?operation=void', invoice_data)
        return result.get('Invoice', result)

    def delete_invoice(self, invoice_id: str, sync_token: str) -> Dict[str, Any]:
        """
        Delete an invoice (permanently removes it)

        Args:
            invoice_id: Invoice ID to delete
            sync_token: Current SyncToken

        Returns:
            dict: Deletion confirmation
        """
        invoice_data = {
            "Id": invoice_id,
            "SyncToken": sync_token
        }

        result = self._api_request('POST', 'invoice?operation=delete', invoice_data)
        return result

    def send_invoice(self, invoice_id: str, email: Optional[str] = None) -> Dict[str, Any]:
        """
        Email an invoice to the customer

        Args:
            invoice_id: Invoice ID to send
            email: Override email address (uses customer email if not provided)

        Returns:
            dict: Send confirmation with delivery info
        """
        endpoint = f"invoice/{invoice_id}/send"
        if email:
            endpoint += f"?sendTo={email}"

        result = self._api_request('POST', endpoint)
        return result.get('Invoice', result)

    # -------------------------------------------------------------------------
    # Purchase/Expense Operations
    # -------------------------------------------------------------------------

    def create_expense(
        self,
        account_id: str,
        vendor_id: Optional[str] = None,
        line_items: Optional[List[Dict[str, Any]]] = None,
        txn_date: Optional[str] = None,
        payment_type: str = "Cash",
        total_amount: Optional[float] = None,
        memo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new expense/purchase

        Args:
            account_id: Bank/Credit Card account ID
            vendor_id: Vendor ID (optional)
            line_items: List of expense line items with:
                - amount: Line amount
                - account_id: Expense account ID
                - description: Line description
            txn_date: Transaction date (YYYY-MM-DD)
            payment_type: "Cash", "Check", or "CreditCard"
            total_amount: Total amount (if not using line items)
            memo: Private memo

        Returns:
            dict: Created purchase data
        """
        purchase_data = {
            "PaymentType": payment_type,
            "AccountRef": {"value": str(account_id)}
        }

        if vendor_id:
            purchase_data["EntityRef"] = {"value": str(vendor_id), "type": "Vendor"}

        if txn_date:
            purchase_data["TxnDate"] = txn_date

        if memo:
            purchase_data["PrivateNote"] = memo

        # Build line items
        if line_items:
            lines = []
            for idx, item in enumerate(line_items):
                line = {
                    "Id": str(idx + 1),
                    "DetailType": "AccountBasedExpenseLineDetail",
                    "Amount": item.get("amount", 0),
                    "Description": item.get("description", ""),
                    "AccountBasedExpenseLineDetail": {
                        "AccountRef": {"value": str(item.get("account_id", account_id))}
                    }
                }
                lines.append(line)
            purchase_data["Line"] = lines
        elif total_amount:
            # Single line item
            purchase_data["Line"] = [{
                "Id": "1",
                "DetailType": "AccountBasedExpenseLineDetail",
                "Amount": total_amount,
                "AccountBasedExpenseLineDetail": {
                    "AccountRef": {"value": str(account_id)}
                }
            }]

        result = self._api_request('POST', 'purchase', purchase_data)
        return result.get('Purchase', result)

    def delete_purchase(self, purchase_id: str, sync_token: str) -> Dict[str, Any]:
        """
        Delete a purchase/expense

        Args:
            purchase_id: Purchase ID to delete
            sync_token: Current SyncToken

        Returns:
            dict: Deletion confirmation
        """
        purchase_data = {
            "Id": purchase_id,
            "SyncToken": sync_token
        }

        result = self._api_request('POST', 'purchase?operation=delete', purchase_data)
        return result


# CLI interface for testing and OpenClaw integration
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
        print("Usage: python client.py <command> [args...]")
        print("\nRead commands:")
        print("  query <sql>           - Execute QBO Query Language")
        print("  accounts              - List accounts")
        print("  customers             - List customers")
        print("  vendors               - List vendors")
        print("  invoices [--unpaid]   - List invoices")
        print("  purchases [--start YYYY-MM-DD] [--end YYYY-MM-DD]")
        print("  get <entity> <id>     - Get entity by ID")
        print("\nWrite commands:")
        print("  create-customer --name <name> [--email <email>] [--phone <phone>]")
        print("  create-vendor --name <name> [--email <email>] [--phone <phone>]")
        print("  create-invoice --customer <id> --amount <amt> [--description <desc>]")
        print("  void-invoice --id <id> --sync-token <token>")
        print("  send-invoice --id <id> [--email <email>]")
        sys.exit(1)

    client = QBOClient()
    command = sys.argv[1].lower()

    try:
        # Read commands
        if command == 'query' and len(sys.argv) > 2:
            result = client.query(sys.argv[2])
            print(json.dumps(result, indent=2))

        elif command == 'accounts':
            accounts = client.get_accounts()
            print(json.dumps({"accounts": accounts, "count": len(accounts)}, indent=2))

        elif command == 'customers':
            customers = client.get_customers()
            print(json.dumps({"customers": customers, "count": len(customers)}, indent=2))

        elif command == 'vendors':
            vendors = client.get_vendors()
            print(json.dumps({"vendors": vendors, "count": len(vendors)}, indent=2))

        elif command == 'invoices':
            unpaid_only = '--unpaid' in sys.argv
            invoices = client.get_invoices(unpaid_only=unpaid_only)
            print(json.dumps({"invoices": invoices, "count": len(invoices), "unpaid_only": unpaid_only}, indent=2))

        elif command == 'purchases':
            start_date = None
            end_date = None
            args = sys.argv[2:]
            for i, arg in enumerate(args):
                if arg == '--start' and i + 1 < len(args):
                    start_date = args[i + 1]
                elif arg == '--end' and i + 1 < len(args):
                    end_date = args[i + 1]
            purchases = client.get_purchases(start_date=start_date, end_date=end_date)
            print(json.dumps({"purchases": purchases, "count": len(purchases)}, indent=2))

        elif command == 'get' and len(sys.argv) >= 4:
            entity_type = sys.argv[2]
            entity_id = sys.argv[3]
            result = client.get_entity(entity_type, entity_id)
            print(json.dumps(result, indent=2))

        # Write commands
        elif command == 'create-customer':
            args = sys.argv[2:]
            name = email = phone = None
            for i, arg in enumerate(args):
                if arg == '--name' and i + 1 < len(args):
                    name = args[i + 1]
                elif arg == '--email' and i + 1 < len(args):
                    email = args[i + 1]
                elif arg == '--phone' and i + 1 < len(args):
                    phone = args[i + 1]
            if not name:
                print("Error: --name is required")
                sys.exit(1)
            result = client.create_customer(display_name=name, email=email, phone=phone)
            print(json.dumps({"success": True, "customer": result}, indent=2))

        elif command == 'create-vendor':
            args = sys.argv[2:]
            name = email = phone = None
            for i, arg in enumerate(args):
                if arg == '--name' and i + 1 < len(args):
                    name = args[i + 1]
                elif arg == '--email' and i + 1 < len(args):
                    email = args[i + 1]
                elif arg == '--phone' and i + 1 < len(args):
                    phone = args[i + 1]
            if not name:
                print("Error: --name is required")
                sys.exit(1)
            result = client.create_vendor(display_name=name, email=email, phone=phone)
            print(json.dumps({"success": True, "vendor": result}, indent=2))

        elif command == 'create-invoice':
            args = sys.argv[2:]
            customer_id = amount = description = due_date = None
            for i, arg in enumerate(args):
                if arg == '--customer' and i + 1 < len(args):
                    customer_id = args[i + 1]
                elif arg == '--amount' and i + 1 < len(args):
                    amount = float(args[i + 1])
                elif arg == '--description' and i + 1 < len(args):
                    description = args[i + 1]
                elif arg == '--due-date' and i + 1 < len(args):
                    due_date = args[i + 1]
            if not customer_id or not amount:
                print("Error: --customer and --amount are required")
                sys.exit(1)
            line_items = [{"amount": amount, "description": description or "Services"}]
            result = client.create_invoice(customer_id=customer_id, line_items=line_items, due_date=due_date)
            print(json.dumps({"success": True, "invoice": result}, indent=2))

        elif command == 'void-invoice':
            args = sys.argv[2:]
            invoice_id = sync_token = None
            for i, arg in enumerate(args):
                if arg == '--id' and i + 1 < len(args):
                    invoice_id = args[i + 1]
                elif arg == '--sync-token' and i + 1 < len(args):
                    sync_token = args[i + 1]
            if not invoice_id or not sync_token:
                print("Error: --id and --sync-token are required")
                sys.exit(1)
            result = client.void_invoice(invoice_id=invoice_id, sync_token=sync_token)
            print(json.dumps({"success": True, "invoice": result}, indent=2))

        elif command == 'send-invoice':
            args = sys.argv[2:]
            invoice_id = email = None
            for i, arg in enumerate(args):
                if arg == '--id' and i + 1 < len(args):
                    invoice_id = args[i + 1]
                elif arg == '--email' and i + 1 < len(args):
                    email = args[i + 1]
            if not invoice_id:
                print("Error: --id is required")
                sys.exit(1)
            result = client.send_invoice(invoice_id=invoice_id, email=email)
            print(json.dumps({"success": True, "invoice": result}, indent=2))

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        sys.exit(1)
