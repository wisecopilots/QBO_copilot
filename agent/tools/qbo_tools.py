#!/usr/bin/env python3
"""
QBO Tools for CPA Copilot Agent

These tools allow the AI agent to interact with QuickBooks Online.
Designed for use with OpenClaw or similar agent frameworks.

Tool Functions:
- qbo_query: Execute any QBO query
- qbo_get_accounts: Get chart of accounts
- qbo_get_customers: Get customer list
- qbo_get_vendors: Get vendor list
- qbo_get_invoices: Get invoices
- qbo_get_purchases: Get expenses/purchases
- qbo_list_clients: List all configured QBO clients
- qbo_switch_client: Switch to a different client company

Usage with OpenClaw:
    from agent.tools.qbo_tools import qbo_tools

    # Register tools with agent
    agent.register_tools(qbo_tools)
"""

import json
from typing import Dict, Any, List, Optional
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from qbo.client import QBOClient
from qbo.multi_tenant import TenantManager


# Global state
_tenant_manager: Optional[TenantManager] = None
_current_client: Optional[str] = None


def _get_tenant_manager() -> TenantManager:
    """Get or create TenantManager singleton"""
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantManager()
    return _tenant_manager


def _get_qbo_client() -> QBOClient:
    """Get QBO client for current tenant"""
    manager = _get_tenant_manager()
    if _current_client:
        return manager.get_client(_current_client)
    # Use first available client
    clients = manager.list_clients()
    if clients:
        return manager.get_client(clients[0].realm_id)
    raise ValueError("No QBO clients configured")


# =============================================================================
# Tool Definitions
# =============================================================================

def qbo_query(query: str) -> Dict[str, Any]:
    """
    Execute a QBO Query Language query.

    Args:
        query: SQL-like query string (e.g., "SELECT * FROM Account WHERE Active = true")

    Returns:
        Query results with entities and metadata

    Examples:
        qbo_query("SELECT * FROM Account WHERE AccountType = 'Expense'")
        qbo_query("SELECT * FROM Invoice WHERE Balance > 0")
        qbo_query("SELECT * FROM Purchase WHERE TxnDate >= '2026-01-01' MAXRESULTS 10")
    """
    client = _get_qbo_client()
    result = client.query(query)
    return result


def qbo_get_accounts(
    active_only: bool = True,
    account_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get accounts from Chart of Accounts.

    Args:
        active_only: Only return active accounts (default: True)
        account_type: Filter by type (e.g., "Expense", "Income", "Bank", "Asset")

    Returns:
        List of account objects with Id, Name, AccountType, CurrentBalance, etc.
    """
    query = "SELECT * FROM Account"
    conditions = []

    if active_only:
        conditions.append("Active = true")
    if account_type:
        conditions.append(f"AccountType = '{account_type}'")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    client = _get_qbo_client()
    result = client.query(query)
    return result.get('QueryResponse', {}).get('Account', [])


def qbo_get_customers(active_only: bool = True) -> List[Dict[str, Any]]:
    """
    Get customer list.

    Args:
        active_only: Only return active customers (default: True)

    Returns:
        List of customer objects with Id, DisplayName, Balance, etc.
    """
    client = _get_qbo_client()
    return client.get_customers(active_only)


def qbo_get_vendors(active_only: bool = True) -> List[Dict[str, Any]]:
    """
    Get vendor list.

    Args:
        active_only: Only return active vendors (default: True)

    Returns:
        List of vendor objects with Id, DisplayName, Balance, etc.
    """
    client = _get_qbo_client()
    return client.get_vendors(active_only)


def qbo_get_invoices(unpaid_only: bool = False) -> List[Dict[str, Any]]:
    """
    Get invoices.

    Args:
        unpaid_only: Only return invoices with balance > 0 (default: False)

    Returns:
        List of invoice objects with DocNumber, CustomerRef, TotalAmt, Balance, etc.
    """
    client = _get_qbo_client()
    return client.get_invoices(unpaid_only)


def qbo_get_purchases(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get purchases/expenses.

    Args:
        start_date: Filter by date >= this (YYYY-MM-DD format)
        end_date: Filter by date <= this (YYYY-MM-DD format)

    Returns:
        List of purchase objects with TxnDate, TotalAmt, VendorRef, etc.
    """
    client = _get_qbo_client()
    return client.get_purchases(start_date, end_date)


def qbo_list_clients() -> List[Dict[str, str]]:
    """
    List all configured QBO client companies.

    Returns:
        List of client info with name, realm_id, contact, channel
    """
    global _current_client
    manager = _get_tenant_manager()
    clients = []

    for client in manager.list_clients():
        clients.append({
            'name': client.name,
            'realm_id': client.realm_id,
            'primary_contact': client.primary_contact,
            'slack_channel': client.slack_channel,
            'is_current': client.realm_id == _current_client or client.name.lower() == _current_client
        })

    return clients


def qbo_switch_client(client_name_or_id: str) -> Dict[str, str]:
    """
    Switch to a different QBO client company.

    Args:
        client_name_or_id: Client name or realm ID

    Returns:
        Confirmation with client details
    """
    global _current_client
    manager = _get_tenant_manager()
    config = manager.get_client_config(client_name_or_id)

    if not config:
        return {'error': f"Client not found: {client_name_or_id}"}

    _current_client = config.realm_id

    return {
        'success': True,
        'message': f"Switched to {config.name}",
        'realm_id': config.realm_id,
        'name': config.name
    }


# =============================================================================
# CRUD Operations (Create, Update, Delete)
# =============================================================================

def qbo_get_entity(entity_type: str, entity_id: str) -> Dict[str, Any]:
    """
    Get a single entity by ID.

    Args:
        entity_type: Type of entity (Invoice, Customer, Vendor, Purchase, Account)
        entity_id: The entity ID

    Returns:
        Entity data with all fields
    """
    client = _get_qbo_client()
    return client.get_entity(entity_type, entity_id)


def qbo_get_tax_codes() -> List[Dict[str, Any]]:
    """
    Get available tax codes for invoices.

    Returns:
        List of tax codes with Id, Name, and Active status.
        Use the Id when creating invoices with tax_code_id parameter.
    """
    client = _get_qbo_client()
    result = client.query("SELECT * FROM TaxCode WHERE Active = true")
    return result.get('QueryResponse', {}).get('TaxCode', [])


def qbo_create_customer(
    display_name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new customer in QuickBooks Online.

    Args:
        display_name: Customer display name (required, must be unique)
        email: Primary email address
        phone: Primary phone number
        company_name: Company/business name

    Returns:
        Created customer data including Id and SyncToken
    """
    client = _get_qbo_client()
    result = client.create_customer(
        display_name=display_name,
        email=email,
        phone=phone,
        company_name=company_name
    )
    return {
        'success': True,
        'customer': result,
        'message': f"Created customer: {result.get('DisplayName')} (ID: {result.get('Id')})"
    }


def qbo_update_customer(
    customer_id: str,
    sync_token: str,
    display_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    active: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Update an existing customer.

    Args:
        customer_id: Customer ID to update
        sync_token: Current SyncToken (get from qbo_get_entity first)
        display_name: New display name
        email: New email address
        phone: New phone number
        active: Set active status (False to deactivate)

    Returns:
        Updated customer data
    """
    client = _get_qbo_client()
    result = client.update_customer(
        customer_id=customer_id,
        sync_token=sync_token,
        display_name=display_name,
        email=email,
        phone=phone,
        active=active
    )
    return {
        'success': True,
        'customer': result,
        'message': f"Updated customer: {result.get('DisplayName')}"
    }


def qbo_create_vendor(
    display_name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new vendor in QuickBooks Online.

    Args:
        display_name: Vendor display name (required, must be unique)
        email: Primary email address
        phone: Primary phone number
        company_name: Company/business name

    Returns:
        Created vendor data including Id and SyncToken
    """
    client = _get_qbo_client()
    result = client.create_vendor(
        display_name=display_name,
        email=email,
        phone=phone,
        company_name=company_name
    )
    return {
        'success': True,
        'vendor': result,
        'message': f"Created vendor: {result.get('DisplayName')} (ID: {result.get('Id')})"
    }


def qbo_update_vendor(
    vendor_id: str,
    sync_token: str,
    display_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    active: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Update an existing vendor.

    Args:
        vendor_id: Vendor ID to update
        sync_token: Current SyncToken (get from qbo_get_entity first)
        display_name: New display name
        email: New email address
        phone: New phone number
        active: Set active status (False to deactivate)

    Returns:
        Updated vendor data
    """
    client = _get_qbo_client()
    result = client.update_vendor(
        vendor_id=vendor_id,
        sync_token=sync_token,
        display_name=display_name,
        email=email,
        phone=phone,
        active=active
    )
    return {
        'success': True,
        'vendor': result,
        'message': f"Updated vendor: {result.get('DisplayName')}"
    }


def qbo_create_invoice(
    customer_id: str,
    line_items: List[Dict[str, Any]],
    due_date: Optional[str] = None,
    doc_number: Optional[str] = None,
    customer_memo: Optional[str] = None,
    tax_code_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new invoice in QuickBooks Online.

    IMPORTANT: This creates a real invoice. Use with confirmation flow.

    Args:
        customer_id: Customer ID to bill
        line_items: List of line items, each with:
            - description: Line description (required)
            - amount: Line amount in dollars (required)
            - quantity: Optional quantity (default 1)
            - unit_price: Optional unit price
            - tax_code_id: Optional tax code for this line
        due_date: Due date in YYYY-MM-DD format
        doc_number: Invoice number (auto-generated if not provided)
        customer_memo: Memo visible to customer
        tax_code_id: Default tax code ID for all lines (e.g., "5" for HST ON, "2" for Exempt)

    Returns:
        Created invoice data including DocNumber and Id
    """
    client = _get_qbo_client()
    result = client.create_invoice(
        customer_id=customer_id,
        line_items=line_items,
        due_date=due_date,
        doc_number=doc_number,
        customer_memo=customer_memo,
        tax_code_id=tax_code_id
    )
    return {
        'success': True,
        'invoice': result,
        'message': f"Created invoice #{result.get('DocNumber')} for ${result.get('TotalAmt', 0):.2f}",
        'confirmation_required': False  # Already created
    }


def qbo_update_invoice(
    invoice_id: str,
    sync_token: str,
    line_items: Optional[List[Dict[str, Any]]] = None,
    due_date: Optional[str] = None,
    customer_memo: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update an existing invoice.

    Args:
        invoice_id: Invoice ID to update
        sync_token: Current SyncToken (get from qbo_get_entity first)
        line_items: New line items (replaces all existing)
        due_date: New due date
        customer_memo: New customer memo

    Returns:
        Updated invoice data
    """
    client = _get_qbo_client()
    result = client.update_invoice(
        invoice_id=invoice_id,
        sync_token=sync_token,
        line_items=line_items,
        due_date=due_date,
        customer_memo=customer_memo
    )
    return {
        'success': True,
        'invoice': result,
        'message': f"Updated invoice #{result.get('DocNumber')}"
    }


def qbo_void_invoice(invoice_id: str, sync_token: str) -> Dict[str, Any]:
    """
    Void an invoice. This cannot be undone.

    IMPORTANT: This is a destructive operation. Use with confirmation flow.

    Args:
        invoice_id: Invoice ID to void
        sync_token: Current SyncToken (get from qbo_get_entity first)

    Returns:
        Voided invoice data
    """
    client = _get_qbo_client()
    result = client.void_invoice(invoice_id=invoice_id, sync_token=sync_token)
    return {
        'success': True,
        'invoice': result,
        'message': f"Voided invoice #{result.get('DocNumber')}",
        'warning': 'This action cannot be undone'
    }


def qbo_delete_invoice(invoice_id: str, sync_token: str) -> Dict[str, Any]:
    """
    Permanently delete an invoice. This cannot be undone.

    IMPORTANT: This is a destructive operation. Use with confirmation flow.
    Consider using qbo_void_invoice instead to preserve records.

    Args:
        invoice_id: Invoice ID to delete
        sync_token: Current SyncToken (get from qbo_get_entity first)

    Returns:
        Deletion confirmation
    """
    client = _get_qbo_client()
    result = client.delete_invoice(invoice_id=invoice_id, sync_token=sync_token)
    return {
        'success': True,
        'result': result,
        'message': f"Deleted invoice {invoice_id}",
        'warning': 'This action cannot be undone'
    }


def qbo_send_invoice(invoice_id: str, email: Optional[str] = None) -> Dict[str, Any]:
    """
    Email an invoice to the customer.

    Args:
        invoice_id: Invoice ID to send
        email: Override recipient email (uses customer's email if not provided)

    Returns:
        Send confirmation with delivery info
    """
    client = _get_qbo_client()
    result = client.send_invoice(invoice_id=invoice_id, email=email)
    return {
        'success': True,
        'invoice': result,
        'message': f"Sent invoice #{result.get('DocNumber')} to {email or 'customer email'}"
    }


def qbo_create_expense(
    account_id: str,
    vendor_id: Optional[str] = None,
    line_items: Optional[List[Dict[str, Any]]] = None,
    txn_date: Optional[str] = None,
    payment_type: str = "Cash",
    total_amount: Optional[float] = None,
    memo: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new expense/purchase in QuickBooks Online.

    Args:
        account_id: Bank or Credit Card account ID
        vendor_id: Vendor ID (optional)
        line_items: List of expense lines with:
            - amount: Line amount
            - account_id: Expense account ID
            - description: Line description
        txn_date: Transaction date (YYYY-MM-DD)
        payment_type: "Cash", "Check", or "CreditCard"
        total_amount: Total amount (if not using line_items)
        memo: Private memo

    Returns:
        Created purchase data
    """
    client = _get_qbo_client()
    result = client.create_expense(
        account_id=account_id,
        vendor_id=vendor_id,
        line_items=line_items,
        txn_date=txn_date,
        payment_type=payment_type,
        total_amount=total_amount,
        memo=memo
    )
    return {
        'success': True,
        'purchase': result,
        'message': f"Created expense for ${result.get('TotalAmt', 0):.2f}"
    }


def qbo_delete_expense(purchase_id: str, sync_token: str) -> Dict[str, Any]:
    """
    Delete an expense/purchase. This cannot be undone.

    IMPORTANT: This is a destructive operation. Use with confirmation flow.

    Args:
        purchase_id: Purchase ID to delete
        sync_token: Current SyncToken (get from qbo_get_entity first)

    Returns:
        Deletion confirmation
    """
    client = _get_qbo_client()
    result = client.delete_purchase(purchase_id=purchase_id, sync_token=sync_token)
    return {
        'success': True,
        'result': result,
        'message': f"Deleted expense {purchase_id}",
        'warning': 'This action cannot be undone'
    }


# =============================================================================
# Tool Registry for Agent Frameworks
# =============================================================================

qbo_tools = [
    # -------------------------------------------------------------------------
    # Read Operations
    # -------------------------------------------------------------------------
    {
        'name': 'qbo_query',
        'description': 'Execute a QBO Query Language query against QuickBooks Online',
        'function': qbo_query,
        'parameters': {
            'type': 'object',
            'properties': {
                'query': {
                    'type': 'string',
                    'description': 'SQL-like query (e.g., "SELECT * FROM Account WHERE Active = true")'
                }
            },
            'required': ['query']
        }
    },
    {
        'name': 'qbo_get_entity',
        'description': 'Get a single entity by type and ID',
        'function': qbo_get_entity,
        'parameters': {
            'type': 'object',
            'properties': {
                'entity_type': {
                    'type': 'string',
                    'description': 'Entity type: Invoice, Customer, Vendor, Purchase, Account'
                },
                'entity_id': {'type': 'string', 'description': 'Entity ID'}
            },
            'required': ['entity_type', 'entity_id']
        }
    },
    {
        'name': 'qbo_get_accounts',
        'description': 'Get accounts from the Chart of Accounts',
        'function': qbo_get_accounts,
        'parameters': {
            'type': 'object',
            'properties': {
                'active_only': {'type': 'boolean', 'default': True},
                'account_type': {'type': 'string', 'description': 'Filter by type: Expense, Income, Bank, Asset, etc.'}
            }
        }
    },
    {
        'name': 'qbo_get_customers',
        'description': 'Get customer list from QuickBooks Online',
        'function': qbo_get_customers,
        'parameters': {
            'type': 'object',
            'properties': {
                'active_only': {'type': 'boolean', 'default': True}
            }
        }
    },
    {
        'name': 'qbo_get_vendors',
        'description': 'Get vendor list from QuickBooks Online',
        'function': qbo_get_vendors,
        'parameters': {
            'type': 'object',
            'properties': {
                'active_only': {'type': 'boolean', 'default': True}
            }
        }
    },
    {
        'name': 'qbo_get_invoices',
        'description': 'Get invoices from QuickBooks Online',
        'function': qbo_get_invoices,
        'parameters': {
            'type': 'object',
            'properties': {
                'unpaid_only': {'type': 'boolean', 'default': False}
            }
        }
    },
    {
        'name': 'qbo_get_purchases',
        'description': 'Get purchases/expenses from QuickBooks Online',
        'function': qbo_get_purchases,
        'parameters': {
            'type': 'object',
            'properties': {
                'start_date': {'type': 'string', 'description': 'YYYY-MM-DD format'},
                'end_date': {'type': 'string', 'description': 'YYYY-MM-DD format'}
            }
        }
    },
    # -------------------------------------------------------------------------
    # Multi-Tenant Operations
    # -------------------------------------------------------------------------
    {
        'name': 'qbo_list_clients',
        'description': 'List all configured QBO client companies',
        'function': qbo_list_clients,
        'parameters': {'type': 'object', 'properties': {}}
    },
    {
        'name': 'qbo_switch_client',
        'description': 'Switch to a different QBO client company',
        'function': qbo_switch_client,
        'parameters': {
            'type': 'object',
            'properties': {
                'client_name_or_id': {
                    'type': 'string',
                    'description': 'Client name or realm ID'
                }
            },
            'required': ['client_name_or_id']
        }
    },
    # -------------------------------------------------------------------------
    # Customer CRUD Operations
    # -------------------------------------------------------------------------
    {
        'name': 'qbo_create_customer',
        'description': 'Create a new customer in QuickBooks Online',
        'function': qbo_create_customer,
        'parameters': {
            'type': 'object',
            'properties': {
                'display_name': {'type': 'string', 'description': 'Customer display name (required, must be unique)'},
                'email': {'type': 'string', 'description': 'Primary email address'},
                'phone': {'type': 'string', 'description': 'Primary phone number'},
                'company_name': {'type': 'string', 'description': 'Company/business name'}
            },
            'required': ['display_name']
        }
    },
    {
        'name': 'qbo_update_customer',
        'description': 'Update an existing customer. Get SyncToken first with qbo_get_entity.',
        'function': qbo_update_customer,
        'parameters': {
            'type': 'object',
            'properties': {
                'customer_id': {'type': 'string', 'description': 'Customer ID to update'},
                'sync_token': {'type': 'string', 'description': 'Current SyncToken from qbo_get_entity'},
                'display_name': {'type': 'string', 'description': 'New display name'},
                'email': {'type': 'string', 'description': 'New email address'},
                'phone': {'type': 'string', 'description': 'New phone number'},
                'active': {'type': 'boolean', 'description': 'Set active status (False to deactivate)'}
            },
            'required': ['customer_id', 'sync_token']
        }
    },
    # -------------------------------------------------------------------------
    # Vendor CRUD Operations
    # -------------------------------------------------------------------------
    {
        'name': 'qbo_create_vendor',
        'description': 'Create a new vendor in QuickBooks Online',
        'function': qbo_create_vendor,
        'parameters': {
            'type': 'object',
            'properties': {
                'display_name': {'type': 'string', 'description': 'Vendor display name (required, must be unique)'},
                'email': {'type': 'string', 'description': 'Primary email address'},
                'phone': {'type': 'string', 'description': 'Primary phone number'},
                'company_name': {'type': 'string', 'description': 'Company/business name'}
            },
            'required': ['display_name']
        }
    },
    {
        'name': 'qbo_update_vendor',
        'description': 'Update an existing vendor. Get SyncToken first with qbo_get_entity.',
        'function': qbo_update_vendor,
        'parameters': {
            'type': 'object',
            'properties': {
                'vendor_id': {'type': 'string', 'description': 'Vendor ID to update'},
                'sync_token': {'type': 'string', 'description': 'Current SyncToken from qbo_get_entity'},
                'display_name': {'type': 'string', 'description': 'New display name'},
                'email': {'type': 'string', 'description': 'New email address'},
                'phone': {'type': 'string', 'description': 'New phone number'},
                'active': {'type': 'boolean', 'description': 'Set active status (False to deactivate)'}
            },
            'required': ['vendor_id', 'sync_token']
        }
    },
    # -------------------------------------------------------------------------
    # Invoice CRUD Operations
    # -------------------------------------------------------------------------
    {
        'name': 'qbo_get_tax_codes',
        'description': 'Get available tax codes for invoices (use before creating invoices)',
        'function': qbo_get_tax_codes,
        'parameters': {'type': 'object', 'properties': {}}
    },
    {
        'name': 'qbo_create_invoice',
        'description': 'Create a new invoice. IMPORTANT: Creates a real invoice - use with confirmation.',
        'function': qbo_create_invoice,
        'parameters': {
            'type': 'object',
            'properties': {
                'customer_id': {'type': 'string', 'description': 'Customer ID to bill'},
                'line_items': {
                    'type': 'array',
                    'description': 'Line items with description, amount, optional quantity/unit_price/tax_code_id',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'description': {'type': 'string'},
                            'amount': {'type': 'number'},
                            'quantity': {'type': 'number'},
                            'unit_price': {'type': 'number'},
                            'tax_code_id': {'type': 'string'}
                        },
                        'required': ['description', 'amount']
                    }
                },
                'due_date': {'type': 'string', 'description': 'YYYY-MM-DD format'},
                'doc_number': {'type': 'string', 'description': 'Invoice number (auto-generated if not provided)'},
                'customer_memo': {'type': 'string', 'description': 'Memo visible to customer'},
                'tax_code_id': {'type': 'string', 'description': 'Default tax code ID (e.g., "5" for HST ON, "2" for Exempt). Use qbo_get_tax_codes to list options.'}
            },
            'required': ['customer_id', 'line_items']
        }
    },
    {
        'name': 'qbo_update_invoice',
        'description': 'Update an existing invoice. Get SyncToken first with qbo_get_entity.',
        'function': qbo_update_invoice,
        'parameters': {
            'type': 'object',
            'properties': {
                'invoice_id': {'type': 'string', 'description': 'Invoice ID to update'},
                'sync_token': {'type': 'string', 'description': 'Current SyncToken from qbo_get_entity'},
                'line_items': {
                    'type': 'array',
                    'description': 'New line items (replaces all existing)',
                    'items': {'type': 'object'}
                },
                'due_date': {'type': 'string', 'description': 'New due date YYYY-MM-DD'},
                'customer_memo': {'type': 'string', 'description': 'New customer memo'}
            },
            'required': ['invoice_id', 'sync_token']
        }
    },
    {
        'name': 'qbo_void_invoice',
        'description': 'Void an invoice. DESTRUCTIVE - cannot be undone. Use with confirmation.',
        'function': qbo_void_invoice,
        'parameters': {
            'type': 'object',
            'properties': {
                'invoice_id': {'type': 'string', 'description': 'Invoice ID to void'},
                'sync_token': {'type': 'string', 'description': 'Current SyncToken from qbo_get_entity'}
            },
            'required': ['invoice_id', 'sync_token']
        },
        'confirmation_required': True
    },
    {
        'name': 'qbo_delete_invoice',
        'description': 'Permanently delete an invoice. DESTRUCTIVE - cannot be undone. Consider void instead.',
        'function': qbo_delete_invoice,
        'parameters': {
            'type': 'object',
            'properties': {
                'invoice_id': {'type': 'string', 'description': 'Invoice ID to delete'},
                'sync_token': {'type': 'string', 'description': 'Current SyncToken from qbo_get_entity'}
            },
            'required': ['invoice_id', 'sync_token']
        },
        'confirmation_required': True
    },
    {
        'name': 'qbo_send_invoice',
        'description': 'Email an invoice to the customer',
        'function': qbo_send_invoice,
        'parameters': {
            'type': 'object',
            'properties': {
                'invoice_id': {'type': 'string', 'description': 'Invoice ID to send'},
                'email': {'type': 'string', 'description': 'Override recipient email (optional)'}
            },
            'required': ['invoice_id']
        }
    },
    # -------------------------------------------------------------------------
    # Expense/Purchase Operations
    # -------------------------------------------------------------------------
    {
        'name': 'qbo_create_expense',
        'description': 'Create a new expense/purchase in QuickBooks Online',
        'function': qbo_create_expense,
        'parameters': {
            'type': 'object',
            'properties': {
                'account_id': {'type': 'string', 'description': 'Bank or Credit Card account ID'},
                'vendor_id': {'type': 'string', 'description': 'Vendor ID (optional)'},
                'line_items': {
                    'type': 'array',
                    'description': 'Expense lines with amount, account_id, description',
                    'items': {'type': 'object'}
                },
                'txn_date': {'type': 'string', 'description': 'Transaction date YYYY-MM-DD'},
                'payment_type': {'type': 'string', 'enum': ['Cash', 'Check', 'CreditCard'], 'default': 'Cash'},
                'total_amount': {'type': 'number', 'description': 'Total amount (if not using line_items)'},
                'memo': {'type': 'string', 'description': 'Private memo'}
            },
            'required': ['account_id']
        }
    },
    {
        'name': 'qbo_delete_expense',
        'description': 'Delete an expense/purchase. DESTRUCTIVE - cannot be undone. Use with confirmation.',
        'function': qbo_delete_expense,
        'parameters': {
            'type': 'object',
            'properties': {
                'purchase_id': {'type': 'string', 'description': 'Purchase ID to delete'},
                'sync_token': {'type': 'string', 'description': 'Current SyncToken from qbo_get_entity'}
            },
            'required': ['purchase_id', 'sync_token']
        },
        'confirmation_required': True
    }
]


# For CLI testing
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()

    print("QBO Tools Test")
    print("=" * 50)

    # List clients
    print("\nConfigured Clients:")
    for client in qbo_list_clients():
        print(f"  - {client['name']} ({client['realm_id']})")

    # Get accounts
    print("\nAccounts (first 5):")
    accounts = qbo_get_accounts()
    for acc in accounts[:5]:
        print(f"  [{acc['Id']}] {acc['Name']} - {acc['AccountType']}")

    print("\nTools registered:", len(qbo_tools))
