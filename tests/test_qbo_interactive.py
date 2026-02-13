#!/usr/bin/env python3
"""
QBO Interactive Test Script

Simple test script that runs through all QBO operations and reports results.
Run with: python tests/test_qbo_interactive.py

No pytest required - just runs tests and prints results.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add parent to path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Change to project root for consistent path resolution
os.chdir(PROJECT_ROOT)

from dotenv import load_dotenv

# Load environment
env_path = PROJECT_ROOT / "config" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")


def error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")


def warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")


def header(msg):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*50}")
    print(f"  {msg}")
    print(f"{'='*50}{Colors.END}\n")


def run_test(name, func):
    """Run a test function and report results"""
    try:
        result = func()
        success(f"{name}")
        return True, result
    except Exception as e:
        error(f"{name}: {e}")
        return False, None


def main():
    print(f"\n{Colors.BOLD}QBO Tools Interactive Test Suite{Colors.END}")
    print(f"Running at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Import tools
    from agent.tools.qbo_tools import (
        qbo_query,
        qbo_get_accounts,
        qbo_get_customers,
        qbo_get_vendors,
        qbo_get_invoices,
        qbo_get_purchases,
        qbo_get_entity,
        qbo_list_clients,
        qbo_create_customer,
        qbo_create_vendor,
        qbo_create_invoice,
        qbo_void_invoice,
    )

    passed = 0
    failed = 0
    results = {}

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================
    header("READ OPERATIONS")

    ok, data = run_test("Get Accounts", qbo_get_accounts)
    if ok:
        print(f"    Found {len(data)} accounts")
        results['accounts'] = data
        passed += 1
    else:
        failed += 1

    ok, data = run_test("Get Accounts (Expense type)", lambda: qbo_get_accounts(account_type="Expense"))
    if ok:
        print(f"    Found {len(data)} expense accounts")
        passed += 1
    else:
        failed += 1

    ok, data = run_test("Get Customers", qbo_get_customers)
    if ok:
        print(f"    Found {len(data)} customers")
        results['customers'] = data
        passed += 1
    else:
        failed += 1

    ok, data = run_test("Get Vendors", qbo_get_vendors)
    if ok:
        print(f"    Found {len(data)} vendors")
        results['vendors'] = data
        passed += 1
    else:
        failed += 1

    ok, data = run_test("Get Invoices", qbo_get_invoices)
    if ok:
        print(f"    Found {len(data)} invoices")
        results['invoices'] = data
        passed += 1
    else:
        failed += 1

    ok, data = run_test("Get Unpaid Invoices", lambda: qbo_get_invoices(unpaid_only=True))
    if ok:
        print(f"    Found {len(data)} unpaid invoices")
        passed += 1
    else:
        failed += 1

    ok, data = run_test("Get Purchases", qbo_get_purchases)
    if ok:
        print(f"    Found {len(data)} purchases")
        results['purchases'] = data
        passed += 1
    else:
        failed += 1

    ok, data = run_test("Custom Query", lambda: qbo_query("SELECT * FROM Account MAXRESULTS 3"))
    if ok:
        count = len(data.get('QueryResponse', {}).get('Account', []))
        print(f"    Query returned {count} results")
        passed += 1
    else:
        failed += 1

    # Get single entity
    if results.get('accounts'):
        account_id = results['accounts'][0]['Id']
        ok, data = run_test(f"Get Single Entity (Account {account_id})", lambda: qbo_get_entity('Account', account_id))
        if ok:
            print(f"    Retrieved: {data.get('Name', 'N/A')}")
            passed += 1
        else:
            failed += 1

    # =========================================================================
    # MULTI-TENANT OPERATIONS
    # =========================================================================
    header("MULTI-TENANT OPERATIONS")

    ok, data = run_test("List Clients", qbo_list_clients)
    if ok:
        print(f"    Found {len(data)} configured clients:")
        for client in data:
            current = " (CURRENT)" if client.get('is_current') else ""
            print(f"      - {client.get('name', 'Unknown')}{current}")
        passed += 1
    else:
        failed += 1

    # =========================================================================
    # WRITE OPERATIONS
    # =========================================================================
    header("WRITE OPERATIONS")

    timestamp = datetime.now().strftime('%H%M%S')

    # Create customer
    customer_name = f"Test Customer {timestamp}"
    ok, data = run_test(f"Create Customer '{customer_name}'",
                        lambda: qbo_create_customer(
                            display_name=customer_name,
                            email=f"test{timestamp}@example.com"
                        ))
    if ok:
        customer_id = data['customer']['Id']
        print(f"    Created with ID: {customer_id}")
        results['created_customer'] = data['customer']
        passed += 1
    else:
        failed += 1

    # Create vendor
    vendor_name = f"Test Vendor {timestamp}"
    ok, data = run_test(f"Create Vendor '{vendor_name}'",
                        lambda: qbo_create_vendor(
                            display_name=vendor_name,
                            email=f"vendor{timestamp}@example.com"
                        ))
    if ok:
        vendor_id = data['vendor']['Id']
        print(f"    Created with ID: {vendor_id}")
        results['created_vendor'] = data['vendor']
        passed += 1
    else:
        failed += 1

    # Create invoice
    if results.get('customers'):
        customer_id = results['customers'][0]['Id']
        customer_name = results['customers'][0].get('DisplayName', 'Customer')

        ok, data = run_test(f"Create Invoice for {customer_name}",
                            lambda: qbo_create_invoice(
                                customer_id=customer_id,
                                line_items=[
                                    {"description": "Test Service A", "amount": 100.00},
                                    {"description": "Test Service B", "amount": 50.00}
                                ],
                                due_date=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                                customer_memo="Test invoice from interactive test"
                                # tax_code_id defaults to "2" (Exempt)
                            ))
        if ok:
            invoice = data['invoice']
            print(f"    Created Invoice #{invoice.get('DocNumber')} for ${invoice.get('TotalAmt')}")
            results['created_invoice'] = invoice
            passed += 1
        else:
            failed += 1

    # =========================================================================
    # VOID OPERATION (creates and voids an invoice)
    # =========================================================================
    header("VOID OPERATION")

    if results.get('customers'):
        customer_id = results['customers'][0]['Id']

        # Create invoice to void
        ok, create_data = run_test("Create Invoice (to void)",
                                   lambda: qbo_create_invoice(
                                       customer_id=customer_id,
                                       line_items=[{"description": "To be voided", "amount": 1.00}]
                                       # tax_code_id defaults to "2" (Exempt)
                                   ))
        if ok:
            invoice = create_data['invoice']
            invoice_id = invoice['Id']
            sync_token = invoice['SyncToken']
            print(f"    Created Invoice #{invoice.get('DocNumber')}")

            ok, void_data = run_test(f"Void Invoice #{invoice.get('DocNumber')}",
                                     lambda: qbo_void_invoice(invoice_id, sync_token))
            if ok:
                print(f"    Invoice voided successfully")
                if void_data.get('warning'):
                    warning(f"    {void_data['warning']}")
                passed += 1
            else:
                failed += 1
            passed += 1
        else:
            failed += 1

    # =========================================================================
    # SUMMARY
    # =========================================================================
    header("TEST SUMMARY")

    total = passed + failed
    print(f"  Total Tests: {total}")
    print(f"  {Colors.GREEN}Passed: {passed}{Colors.END}")
    print(f"  {Colors.RED}Failed: {failed}{Colors.END}")
    print()

    if failed == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}All tests passed!{Colors.END}")
    else:
        print(f"{Colors.YELLOW}Some tests failed. Check output above for details.{Colors.END}")

    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
