"""
Document Request Templates

Standard document packs and templates for client onboarding.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Standard onboarding document pack
ONBOARDING_DOC_PACK = [
    {
        "type": "prior_year_return",
        "description": "Prior year tax return (complete, all pages)",
        "category": "tax",
        "required": True
    },
    {
        "type": "trial_balance",
        "description": "Trial balance as of year-end",
        "category": "accounting",
        "required": True
    },
    {
        "type": "bank_statements",
        "description": "Last 3 months bank statements (all accounts)",
        "category": "banking",
        "required": True
    },
    {
        "type": "payroll_reports",
        "description": "YTD payroll summary and 941s",
        "category": "payroll",
        "required": False
    },
    {
        "type": "incorporation_docs",
        "description": "Articles of incorporation / Operating agreement",
        "category": "legal",
        "required": True
    },
    {
        "type": "sales_tax",
        "description": "Last sales tax filing",
        "category": "tax",
        "required": False
    },
    {
        "type": "ein_letter",
        "description": "IRS EIN confirmation letter",
        "category": "legal",
        "required": True
    },
    {
        "type": "prior_financials",
        "description": "Prior year financial statements (P&L, Balance Sheet)",
        "category": "accounting",
        "required": False
    }
]

# Periodic document packs
MONTHLY_DOC_PACK = [
    {
        "type": "bank_statements",
        "description": "Bank statements for the month",
        "category": "banking"
    },
    {
        "type": "credit_card_statements",
        "description": "Credit card statements for the month",
        "category": "banking"
    },
    {
        "type": "payroll_reports",
        "description": "Payroll reports for the month",
        "category": "payroll"
    }
]

QUARTERLY_DOC_PACK = [
    {
        "type": "941",
        "description": "Form 941 - Quarterly payroll tax return",
        "category": "payroll"
    },
    {
        "type": "sales_tax",
        "description": "Quarterly sales tax filing",
        "category": "tax"
    },
    {
        "type": "estimated_tax",
        "description": "Quarterly estimated tax payment confirmation",
        "category": "tax"
    }
]

ANNUAL_DOC_PACK = [
    {
        "type": "w2_w3",
        "description": "W-2s and W-3 transmittal",
        "category": "payroll"
    },
    {
        "type": "1099s",
        "description": "1099-NEC/MISC forms issued",
        "category": "tax"
    },
    {
        "type": "year_end_statements",
        "description": "Year-end bank statements (all accounts)",
        "category": "banking"
    },
    {
        "type": "depreciation_schedule",
        "description": "Fixed asset and depreciation schedule",
        "category": "accounting"
    },
    {
        "type": "insurance_policies",
        "description": "Current insurance policies (GL, WC, etc.)",
        "category": "legal"
    }
]

# Document type metadata
DOC_TYPE_INFO = {
    "prior_year_return": {
        "name": "Prior Year Tax Return",
        "icon": "📄",
        "typical_format": "PDF"
    },
    "trial_balance": {
        "name": "Trial Balance",
        "icon": "📊",
        "typical_format": "Excel/PDF"
    },
    "bank_statements": {
        "name": "Bank Statements",
        "icon": "🏦",
        "typical_format": "PDF"
    },
    "credit_card_statements": {
        "name": "Credit Card Statements",
        "icon": "💳",
        "typical_format": "PDF"
    },
    "payroll_reports": {
        "name": "Payroll Reports",
        "icon": "👥",
        "typical_format": "PDF/Excel"
    },
    "incorporation_docs": {
        "name": "Incorporation Documents",
        "icon": "📜",
        "typical_format": "PDF"
    },
    "sales_tax": {
        "name": "Sales Tax Filing",
        "icon": "🧾",
        "typical_format": "PDF"
    },
    "ein_letter": {
        "name": "EIN Letter",
        "icon": "📋",
        "typical_format": "PDF"
    },
    "prior_financials": {
        "name": "Prior Financials",
        "icon": "📈",
        "typical_format": "PDF/Excel"
    },
    "941": {
        "name": "Form 941",
        "icon": "📝",
        "typical_format": "PDF"
    },
    "estimated_tax": {
        "name": "Estimated Tax Payment",
        "icon": "💰",
        "typical_format": "PDF"
    },
    "w2_w3": {
        "name": "W-2s and W-3",
        "icon": "📋",
        "typical_format": "PDF"
    },
    "1099s": {
        "name": "1099 Forms",
        "icon": "📋",
        "typical_format": "PDF"
    },
    "year_end_statements": {
        "name": "Year-End Statements",
        "icon": "📊",
        "typical_format": "PDF"
    },
    "depreciation_schedule": {
        "name": "Depreciation Schedule",
        "icon": "🏢",
        "typical_format": "Excel"
    },
    "insurance_policies": {
        "name": "Insurance Policies",
        "icon": "🛡️",
        "typical_format": "PDF"
    }
}


def get_doc_type_name(doc_type: str) -> str:
    """Get human-readable name for a document type"""
    info = DOC_TYPE_INFO.get(doc_type, {})
    return info.get("name", doc_type.replace("_", " ").title())


def get_doc_type_icon(doc_type: str) -> str:
    """Get icon for a document type"""
    info = DOC_TYPE_INFO.get(doc_type, {})
    return info.get("icon", "📄")


def create_doc_request_pack(
    db,
    client_id: str,
    pack_type: str = "onboarding",
    period: Optional[str] = None,
    requested_by: Optional[str] = None,
    due_days: int = 14
) -> List[Dict[str, Any]]:
    """
    Create a pack of document requests for a client

    Args:
        db: OnboardingDB instance
        client_id: Client ID
        pack_type: Type of pack (onboarding, monthly, quarterly, annual)
        period: Period for the documents (e.g., "2024", "Q1 2025", "Jan 2025")
        requested_by: Slack user ID who requested
        due_days: Days until due

    Returns:
        List of created doc request records
    """
    packs = {
        "onboarding": ONBOARDING_DOC_PACK,
        "monthly": MONTHLY_DOC_PACK,
        "quarterly": QUARTERLY_DOC_PACK,
        "annual": ANNUAL_DOC_PACK
    }

    pack = packs.get(pack_type, ONBOARDING_DOC_PACK)
    due_date = (datetime.utcnow() + timedelta(days=due_days)).strftime("%Y-%m-%d")

    created = []
    for doc in pack:
        request = db.create_doc_request(
            client_id=client_id,
            doc_type=doc["type"],
            period=period,
            description=doc["description"],
            requested_by=requested_by,
            due_date=due_date
        )
        created.append(request)

    return created


def get_required_docs(pack_type: str = "onboarding") -> List[Dict[str, Any]]:
    """Get list of required documents for a pack type"""
    packs = {
        "onboarding": ONBOARDING_DOC_PACK,
        "monthly": MONTHLY_DOC_PACK,
        "quarterly": QUARTERLY_DOC_PACK,
        "annual": ANNUAL_DOC_PACK
    }

    pack = packs.get(pack_type, ONBOARDING_DOC_PACK)
    return [doc for doc in pack if doc.get("required", True)]


def format_doc_request_message(doc_requests: List[Dict[str, Any]]) -> str:
    """Format document requests into a readable message"""
    if not doc_requests:
        return "No documents requested."

    lines = ["*Documents Requested:*\n"]

    by_category = {}
    for req in doc_requests:
        doc_type = req.get("doc_type", "unknown")
        info = DOC_TYPE_INFO.get(doc_type, {})
        category = info.get("category", "other") if info else "other"

        if category not in by_category:
            by_category[category] = []
        by_category[category].append(req)

    category_names = {
        "tax": "Tax Documents",
        "accounting": "Accounting",
        "banking": "Banking",
        "payroll": "Payroll",
        "legal": "Legal",
        "other": "Other"
    }

    for category, docs in by_category.items():
        lines.append(f"\n*{category_names.get(category, category.title())}*")
        for doc in docs:
            icon = get_doc_type_icon(doc.get("doc_type", ""))
            desc = doc.get("description", doc.get("doc_type", "Document"))
            status = doc.get("status", "requested")
            status_emoji = "⏳" if status == "requested" else "✅" if status in ("received", "filed") else "📋"
            lines.append(f"{icon} {desc} {status_emoji}")

    due_date = doc_requests[0].get("due_date") if doc_requests else None
    if due_date:
        lines.append(f"\n_Due by: {due_date}_")

    return "\n".join(lines)
