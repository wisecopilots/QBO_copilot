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
# Tool Registry for Agent Frameworks
# =============================================================================

qbo_tools = [
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
