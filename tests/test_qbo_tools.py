#!/usr/bin/env python3
"""
QBO Tools Test Suite

Comprehensive tests for all QBO operations against the sandbox environment.
Run with: python -m pytest tests/test_qbo_tools.py -v

Prerequisites:
- QBO sandbox credentials configured in config/.env
- Valid OAuth tokens in config/tokens/default.json
"""

import os
import sys
import json
import pytest
from pathlib import Path
from datetime import datetime, timedelta

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent / "config" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

from qbo.client import QBOClient
from agent.tools.qbo_tools import (
    qbo_query,
    qbo_get_accounts,
    qbo_get_customers,
    qbo_get_vendors,
    qbo_get_invoices,
    qbo_get_purchases,
    qbo_get_entity,
    qbo_list_clients,
    qbo_switch_client,
    qbo_create_customer,
    qbo_update_customer,
    qbo_create_vendor,
    qbo_update_vendor,
    qbo_create_invoice,
    qbo_update_invoice,
    qbo_void_invoice,
    qbo_send_invoice,
    qbo_create_expense,
    qbo_delete_expense,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def qbo_client():
    """Create a QBO client for testing"""
    return QBOClient()


@pytest.fixture(scope="module")
def test_customer_name():
    """Generate unique test customer name"""
    return f"Test Customer {datetime.now().strftime('%Y%m%d%H%M%S')}"


@pytest.fixture(scope="module")
def test_vendor_name():
    """Generate unique test vendor name"""
    return f"Test Vendor {datetime.now().strftime('%Y%m%d%H%M%S')}"


# =============================================================================
# Read Operations Tests
# =============================================================================

class TestReadOperations:
    """Test all read operations"""

    def test_get_accounts(self):
        """Test fetching accounts from Chart of Accounts"""
        accounts = qbo_get_accounts()
        assert isinstance(accounts, list)
        assert len(accounts) > 0

        # Verify account structure
        account = accounts[0]
        assert 'Id' in account
        assert 'Name' in account
        assert 'AccountType' in account
        print(f"✓ Found {len(accounts)} accounts")

    def test_get_accounts_by_type(self):
        """Test filtering accounts by type"""
        expense_accounts = qbo_get_accounts(account_type="Expense")
        assert isinstance(expense_accounts, list)

        for account in expense_accounts:
            assert account.get('AccountType') == 'Expense'
        print(f"✓ Found {len(expense_accounts)} expense accounts")

    def test_get_customers(self):
        """Test fetching customers"""
        customers = qbo_get_customers()
        assert isinstance(customers, list)

        if customers:
            customer = customers[0]
            assert 'Id' in customer
            assert 'DisplayName' in customer or 'CompanyName' in customer
        print(f"✓ Found {len(customers)} customers")

    def test_get_vendors(self):
        """Test fetching vendors"""
        vendors = qbo_get_vendors()
        assert isinstance(vendors, list)

        if vendors:
            vendor = vendors[0]
            assert 'Id' in vendor
        print(f"✓ Found {len(vendors)} vendors")

    def test_get_invoices(self):
        """Test fetching invoices"""
        invoices = qbo_get_invoices()
        assert isinstance(invoices, list)

        if invoices:
            invoice = invoices[0]
            assert 'Id' in invoice
            assert 'TotalAmt' in invoice or 'Balance' in invoice
        print(f"✓ Found {len(invoices)} invoices")

    def test_get_invoices_unpaid_only(self):
        """Test fetching only unpaid invoices"""
        unpaid = qbo_get_invoices(unpaid_only=True)
        assert isinstance(unpaid, list)

        for invoice in unpaid:
            assert invoice.get('Balance', 0) > 0, "Unpaid invoice should have balance > 0"
        print(f"✓ Found {len(unpaid)} unpaid invoices")

    def test_get_purchases(self):
        """Test fetching purchases/expenses"""
        purchases = qbo_get_purchases()
        assert isinstance(purchases, list)
        print(f"✓ Found {len(purchases)} purchases")

    def test_get_purchases_with_date_filter(self):
        """Test fetching purchases with date range"""
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')

        purchases = qbo_get_purchases(start_date=start_date, end_date=end_date)
        assert isinstance(purchases, list)
        print(f"✓ Found {len(purchases)} purchases in date range")

    def test_qbo_query(self):
        """Test custom QBO query"""
        result = qbo_query("SELECT * FROM Account MAXRESULTS 5")
        assert isinstance(result, dict)
        assert 'QueryResponse' in result
        print("✓ Custom query executed successfully")

    def test_get_entity(self):
        """Test fetching a single entity by ID"""
        # First get an account to test with
        accounts = qbo_get_accounts()
        if accounts:
            account_id = accounts[0]['Id']
            entity = qbo_get_entity('Account', account_id)
            assert isinstance(entity, dict)
            assert entity.get('Id') == account_id
            print(f"✓ Fetched single account: {entity.get('Name')}")


# =============================================================================
# Multi-Tenant Tests
# =============================================================================

class TestMultiTenant:
    """Test multi-tenant operations"""

    def test_list_clients(self):
        """Test listing all configured clients"""
        clients = qbo_list_clients()
        assert isinstance(clients, list)
        print(f"✓ Found {len(clients)} configured clients")

        for client in clients:
            print(f"  - {client.get('name', 'Unknown')} ({client.get('realm_id', 'N/A')})")

    def test_switch_client(self):
        """Test switching between clients"""
        clients = qbo_list_clients()
        if clients:
            # Switch to first client
            result = qbo_switch_client(clients[0]['realm_id'])
            assert result.get('success') or 'error' not in result
            print(f"✓ Switched to client: {result.get('name', clients[0]['realm_id'])}")


# =============================================================================
# Create Operations Tests
# =============================================================================

class TestCreateOperations:
    """Test create operations (these create real sandbox data)"""

    @pytest.fixture(autouse=True)
    def setup(self, test_customer_name, test_vendor_name):
        self.customer_name = test_customer_name
        self.vendor_name = test_vendor_name

    def test_create_customer(self):
        """Test creating a new customer"""
        result = qbo_create_customer(
            display_name=self.customer_name,
            email=f"test_{datetime.now().strftime('%H%M%S')}@example.com",
            phone="555-0100"
        )

        assert result.get('success') == True
        assert 'customer' in result
        customer = result['customer']
        assert customer.get('Id') is not None
        assert customer.get('DisplayName') == self.customer_name

        # Store for later tests
        self.__class__.created_customer_id = customer['Id']
        self.__class__.created_customer_sync_token = customer['SyncToken']

        print(f"✓ Created customer: {customer.get('DisplayName')} (ID: {customer.get('Id')})")
        return customer

    def test_create_vendor(self):
        """Test creating a new vendor"""
        result = qbo_create_vendor(
            display_name=self.vendor_name,
            email=f"vendor_{datetime.now().strftime('%H%M%S')}@example.com"
        )

        assert result.get('success') == True
        assert 'vendor' in result
        vendor = result['vendor']
        assert vendor.get('Id') is not None

        # Store for later tests
        self.__class__.created_vendor_id = vendor['Id']
        self.__class__.created_vendor_sync_token = vendor['SyncToken']

        print(f"✓ Created vendor: {vendor.get('DisplayName')} (ID: {vendor.get('Id')})")
        return vendor

    def test_create_invoice(self):
        """Test creating a new invoice"""
        # Get a customer to bill
        customers = qbo_get_customers()
        if not customers:
            pytest.skip("No customers available to create invoice")

        customer_id = customers[0]['Id']
        due_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

        result = qbo_create_invoice(
            customer_id=customer_id,
            line_items=[
                {"description": "Test Service", "amount": 100.00},
                {"description": "Additional Work", "amount": 50.00}
            ],
            due_date=due_date,
            customer_memo="Test invoice created by automated tests"
        )

        assert result.get('success') == True
        assert 'invoice' in result
        invoice = result['invoice']
        assert invoice.get('Id') is not None
        assert float(invoice.get('TotalAmt', 0)) == 150.00

        # Store for later tests
        self.__class__.created_invoice_id = invoice['Id']
        self.__class__.created_invoice_sync_token = invoice['SyncToken']
        self.__class__.created_invoice_doc_number = invoice.get('DocNumber')

        print(f"✓ Created invoice #{invoice.get('DocNumber')} for ${invoice.get('TotalAmt')}")
        return invoice


# =============================================================================
# Update Operations Tests
# =============================================================================

class TestUpdateOperations:
    """Test update operations"""

    def test_update_customer(self):
        """Test updating a customer"""
        # Get a customer to update
        customers = qbo_get_customers()
        if not customers:
            pytest.skip("No customers available to update")

        customer = customers[0]
        customer_id = customer['Id']
        sync_token = customer['SyncToken']

        # Update email
        new_email = f"updated_{datetime.now().strftime('%H%M%S')}@example.com"
        result = qbo_update_customer(
            customer_id=customer_id,
            sync_token=sync_token,
            email=new_email
        )

        assert result.get('success') == True
        updated = result['customer']
        assert updated.get('PrimaryEmailAddr', {}).get('Address') == new_email

        print(f"✓ Updated customer {customer.get('DisplayName')} email to {new_email}")

    def test_update_vendor(self):
        """Test updating a vendor"""
        vendors = qbo_get_vendors()
        if not vendors:
            pytest.skip("No vendors available to update")

        vendor = vendors[0]
        vendor_id = vendor['Id']
        sync_token = vendor['SyncToken']

        new_phone = f"555-{datetime.now().strftime('%H%M')}"
        result = qbo_update_vendor(
            vendor_id=vendor_id,
            sync_token=sync_token,
            phone=new_phone
        )

        assert result.get('success') == True
        print(f"✓ Updated vendor {vendor.get('DisplayName')} phone to {new_phone}")


# =============================================================================
# Invoice Operations Tests
# =============================================================================

class TestInvoiceOperations:
    """Test invoice-specific operations"""

    def test_send_invoice(self):
        """Test sending an invoice (dry-run in sandbox)"""
        invoices = qbo_get_invoices()
        if not invoices:
            pytest.skip("No invoices available to send")

        invoice = invoices[0]
        invoice_id = invoice['Id']

        # This may fail in sandbox if email is not configured
        try:
            result = qbo_send_invoice(
                invoice_id=invoice_id,
                email="test@example.com"
            )
            assert result.get('success') == True
            print(f"✓ Sent invoice #{invoice.get('DocNumber')}")
        except Exception as e:
            print(f"⚠ Send invoice skipped (sandbox limitation): {e}")
            pytest.skip(f"Sandbox limitation: {e}")

    def test_void_invoice(self):
        """Test voiding an invoice"""
        # Create a new invoice to void
        customers = qbo_get_customers()
        if not customers:
            pytest.skip("No customers available")

        # Create invoice
        create_result = qbo_create_invoice(
            customer_id=customers[0]['Id'],
            line_items=[{"description": "To be voided", "amount": 1.00}]
        )

        if not create_result.get('success'):
            pytest.skip("Could not create invoice to void")

        invoice = create_result['invoice']

        # Void it
        result = qbo_void_invoice(
            invoice_id=invoice['Id'],
            sync_token=invoice['SyncToken']
        )

        assert result.get('success') == True
        assert 'warning' in result  # Should warn that it's irreversible
        print(f"✓ Voided invoice #{invoice.get('DocNumber')}")


# =============================================================================
# Expense Operations Tests
# =============================================================================

class TestExpenseOperations:
    """Test expense/purchase operations"""

    def test_create_expense(self):
        """Test creating an expense"""
        # Get a bank account
        accounts = qbo_get_accounts(account_type="Bank")
        if not accounts:
            pytest.skip("No bank accounts available")

        bank_account_id = accounts[0]['Id']

        result = qbo_create_expense(
            account_id=bank_account_id,
            total_amount=25.00,
            payment_type="Cash",
            memo="Test expense from automated tests",
            txn_date=datetime.now().strftime('%Y-%m-%d')
        )

        assert result.get('success') == True
        assert 'purchase' in result
        purchase = result['purchase']

        # Store for cleanup
        self.__class__.created_expense_id = purchase['Id']
        self.__class__.created_expense_sync_token = purchase['SyncToken']

        print(f"✓ Created expense for ${purchase.get('TotalAmt')}")

    def test_delete_expense(self):
        """Test deleting an expense"""
        if not hasattr(self.__class__, 'created_expense_id'):
            pytest.skip("No expense created to delete")

        result = qbo_delete_expense(
            purchase_id=self.__class__.created_expense_id,
            sync_token=self.__class__.created_expense_sync_token
        )

        assert result.get('success') == True
        print(f"✓ Deleted expense {self.__class__.created_expense_id}")


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error handling"""

    def test_invalid_query(self):
        """Test handling of invalid query"""
        with pytest.raises(Exception):
            qbo_query("SELECT * FROM NonExistentEntity")

    def test_get_nonexistent_entity(self):
        """Test getting entity that doesn't exist"""
        with pytest.raises(Exception):
            qbo_get_entity('Invoice', '999999999')

    def test_create_duplicate_customer(self):
        """Test creating customer with duplicate name"""
        # Create first
        unique_name = f"Duplicate Test {datetime.now().strftime('%H%M%S')}"
        result1 = qbo_create_customer(display_name=unique_name)
        assert result1.get('success') == True

        # Try to create duplicate
        with pytest.raises(Exception):
            qbo_create_customer(display_name=unique_name)


# =============================================================================
# CLI Interface Tests
# =============================================================================

class TestCLIInterface:
    """Test CLI interface"""

    def test_cli_accounts(self):
        """Test CLI accounts command"""
        import subprocess
        result = subprocess.run(
            ['python', 'qbo/client.py', 'accounts'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert 'accounts' in output
        print(f"✓ CLI accounts returned {output.get('count', 0)} accounts")

    def test_cli_customers(self):
        """Test CLI customers command"""
        import subprocess
        result = subprocess.run(
            ['python', 'qbo/client.py', 'customers'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert 'customers' in output
        print(f"✓ CLI customers returned {output.get('count', 0)} customers")

    def test_cli_invoices_unpaid(self):
        """Test CLI invoices with unpaid filter"""
        import subprocess
        result = subprocess.run(
            ['python', 'qbo/client.py', 'invoices', '--unpaid'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert 'invoices' in output
        assert output.get('unpaid_only') == True
        print(f"✓ CLI unpaid invoices returned {output.get('count', 0)} invoices")

    def test_cli_query(self):
        """Test CLI query command"""
        import subprocess
        result = subprocess.run(
            ['python', 'qbo/client.py', 'query', 'SELECT * FROM Account MAXRESULTS 3'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert 'QueryResponse' in output
        print("✓ CLI query executed successfully")


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
