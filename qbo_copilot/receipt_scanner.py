"""
Receipt Scanner - Claude Vision OCR for document extraction

Uses Claude's vision capabilities to extract structured data from
receipts, invoices, bills, and bank statements.
"""

import base64
import json
import logging
from typing import Dict, Any, Optional, Tuple

import anthropic

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Analyze this {doc_type} image and extract all relevant financial data into structured JSON.

Return ONLY valid JSON with the following structure (omit fields that are not present):

{{
  "vendor_name": "Business name on the document",
  "date": "YYYY-MM-DD format",
  "due_date": "YYYY-MM-DD format (invoices/bills only)",
  "invoice_number": "Document/invoice number if present",
  "subtotal": 0.00,
  "tax": 0.00,
  "tip": 0.00,
  "total": 0.00,
  "currency": "USD",
  "payment_method": "cash/credit/debit/check if visible",
  "category_suggestion": "Best QBO expense category (e.g., Office Supplies, Meals, Travel)",
  "line_items": [
    {{
      "description": "Item description",
      "quantity": 1,
      "unit_price": 0.00,
      "amount": 0.00
    }}
  ],
  "notes": "Any additional relevant info (addresses, account numbers with last 4 only, memo fields)"
}}

Important:
- Use null for fields you cannot read or that don't exist
- Amounts should be numbers, not strings
- Dates must be YYYY-MM-DD
- For unclear text, provide your best reading with a note
- Do NOT include full account numbers or sensitive data"""

DOC_TYPE_LABELS = {
    "expense_receipt": "expense receipt",
    "invoice": "invoice",
    "bill": "bill",
    "bank_statement": "bank statement",
    "other": "financial document",
}


def scan_receipt(
    image_bytes: bytes,
    mime_type: str,
    doc_type: str = "expense_receipt",
) -> Tuple[Dict[str, Any], float]:
    """
    Send an image to Claude Vision for structured data extraction.

    Args:
        image_bytes: Raw image bytes
        mime_type: Image MIME type (e.g., image/jpeg, image/png)
        doc_type: Document type key from DOC_TYPE_LABELS

    Returns:
        Tuple of (extracted_data dict, confidence_score 0-1)
    """
    client = anthropic.Anthropic()
    doc_label = DOC_TYPE_LABELS.get(doc_type, "financial document")

    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": EXTRACTION_PROMPT.format(doc_type=doc_label),
                    },
                ],
            }
        ],
    )

    raw_text = response.content[0].text.strip()

    # Strip markdown code fences if present
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw_text = "\n".join(lines).strip()

    try:
        extracted = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse extraction response: {raw_text[:200]}")
        return {"raw_text": raw_text, "parse_error": True}, 0.0

    # Calculate confidence based on key fields present
    confidence = _calculate_confidence(extracted, doc_type)

    return extracted, confidence


def _calculate_confidence(data: Dict[str, Any], doc_type: str) -> float:
    """Estimate confidence based on which key fields were extracted."""
    key_fields = ["vendor_name", "date", "total"]
    if doc_type in ("invoice", "bill"):
        key_fields.append("invoice_number")

    present = sum(1 for f in key_fields if data.get(f) is not None)
    base = present / len(key_fields)

    # Bonus for line items
    if data.get("line_items"):
        base = min(1.0, base + 0.1)

    return round(base, 2)


def validate_extracted_data(data: Dict[str, Any]) -> Dict[str, list]:
    """
    Validate extracted receipt data and return errors/warnings.

    Returns:
        Dict with 'errors' and 'warnings' lists
    """
    errors = []
    warnings = []

    if data.get("parse_error"):
        errors.append("Could not parse structured data from image")
        return {"errors": errors, "warnings": warnings}

    if not data.get("vendor_name"):
        warnings.append("Vendor name not detected")

    if not data.get("date"):
        warnings.append("Date not detected")

    total = data.get("total")
    if total is None:
        errors.append("Total amount not detected")
    elif not isinstance(total, (int, float)):
        errors.append(f"Total is not a number: {total}")
    elif total <= 0:
        warnings.append("Total is zero or negative")

    subtotal = data.get("subtotal")
    tax = data.get("tax")
    if all(v is not None for v in [subtotal, tax, total]):
        try:
            expected = float(subtotal) + float(tax)
            if abs(expected - float(total)) > 0.02:
                warnings.append(
                    f"Subtotal ({subtotal}) + tax ({tax}) = {expected:.2f}, "
                    f"but total is {total}"
                )
        except (ValueError, TypeError):
            pass

    return {"errors": errors, "warnings": warnings}
