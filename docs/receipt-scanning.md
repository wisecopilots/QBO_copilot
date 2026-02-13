# Receipt Scanning Deep Dive

QBO Copilot uses Claude Vision to extract structured financial data from receipts, invoices, bills, and bank statements uploaded through Slack.

## Overview

The receipt scanning pipeline:

```
Slack File Upload --> Classification Dropdown --> Claude Vision OCR --> Review Card --> QBO Posting
       |                     |                         |                    |              |
   User uploads         User selects            Background thread      Extracted      (Optional)
   image to DM          doc type               sends to Claude API    data shown     Post to QBO
```

---

## Supported Document Types

| Type | Key (`doc_type`) | What It Extracts |
|------|-------------------|-----------------|
| Expense Receipt | `expense_receipt` | Vendor, date, total, tax, tip, line items, payment method |
| Invoice | `invoice` | Vendor/customer, date, due date, invoice number, line items, total |
| Bill | `bill` | Vendor, date, due date, invoice number, line items, total |
| Bank Statement | `bank_statement` | Institution, period, transactions, balances |

## Step-by-Step Flow

### 1. Upload an Image

Send an image file to the bot's DM. Supported formats:
- JPEG / JPG
- PNG

The bot detects the file upload and responds with a classification dropdown.

### 2. Select the Document Type

A Slack dropdown appears asking you to classify the document:

- Expense Receipt
- Invoice
- Bill
- Bank Statement

Select the appropriate type and the scan begins.

### 3. Background Scanning

Once classified, the bot:

1. Creates an entry in the `receipt_queue` table with status `uploaded`
2. Downloads the file from Slack
3. Updates status to `scanning`
4. Sends the image to Claude Vision via the Anthropic API
5. Claude analyzes the image and returns structured JSON

The scan runs in a background thread (`threading.Thread`, daemon mode) so it does not block other bot operations. You will see a "Scanning..." message while it processes.

### 4. Data Extraction

Claude Vision reads the document and extracts:

```json
{
  "vendor_name": "Office Depot",
  "date": "2026-02-10",
  "subtotal": 45.99,
  "tax": 3.68,
  "total": 49.67,
  "currency": "USD",
  "payment_method": "credit",
  "category_suggestion": "Office Supplies",
  "line_items": [
    {
      "description": "Copy Paper (case)",
      "quantity": 2,
      "unit_price": 15.99,
      "amount": 31.98
    },
    {
      "description": "Ink Cartridge - Black",
      "quantity": 1,
      "unit_price": 14.01,
      "amount": 14.01
    }
  ],
  "all_text": "OFFICE DEPOT #1234\n...(full text transcription)",
  "notes": "Store #1234, Transaction #98765"
}
```

The extraction prompt instructs Claude to:
- Read all visible text on the document, including headers, footers, and fine print
- Return amounts as numbers (not strings)
- Format dates as YYYY-MM-DD
- Suggest a QBO expense category
- Mark unclear text with `[unclear]`
- Never include full account numbers (only last 4 digits)

### 5. Review Card

After extraction completes, the bot posts a formatted review card in Slack:

The card shows:
- **Vendor:** Detected vendor name
- **Date:** Transaction date
- **Total:** Extracted total amount
- **Tax:** Tax amount (if detected)
- **Line Items:** Individual items with quantities and prices
- **Category:** Suggested QBO expense category
- **Confidence:** A score from 0.0 to 1.0

Action buttons on the card:
- **Approve** -- Accept the extraction and optionally post to QBO
- **Edit** -- Opens a modal to correct any fields
- **Reject** -- Discard the scan result

---

## Confidence Scores

The confidence score estimates how complete the extraction is, based on which key fields were successfully extracted:

| Score Range | Meaning |
|-------------|---------|
| 0.9 - 1.0 | All key fields extracted, line items present |
| 0.7 - 0.9 | Most key fields extracted |
| 0.5 - 0.7 | Some fields missing |
| Below 0.5 | Poor extraction, manual review recommended |

Key fields checked:
- `vendor_name`
- `date`
- `total`
- `invoice_number` (for invoices and bills only)

A 0.1 bonus is added when line items are successfully extracted.

### Validation Checks

The system also validates extracted data:
- Verifies the total is a positive number
- Checks that subtotal + tax equals the total (warns if mismatch exceeds $0.02)
- Warns if vendor name or date was not detected

---

## Google Drive Filing (Optional)

When Google Drive integration is configured (see [setup-google-drive.md](setup-google-drive.md)):

- Approved receipts are uploaded to the client's `Receipts/` folder
- Approved invoices go to the `Invoices/` folder
- Approved bills go to the `Bills/` folder
- The Drive file link is included in the approval confirmation message

Without Google Drive, the scan and review workflow still works -- documents just are not filed.

---

## Receipt Queue

### View the Queue

Use the slash command:

```
/qbo receipts
```

This shows a summary of the receipt queue with counts by status:
- **Uploaded** -- Waiting to be scanned
- **Scanning** -- Currently being processed
- **Scanned** -- Extraction complete, awaiting review
- **Approved** -- Reviewed and accepted
- **Rejected** -- Reviewed and discarded
- **Error** -- Scan failed (check logs)

### Home Tab Summary

The bot's Home tab includes receipt queue summary counts, giving you a quick overview without running a command.

---

## Database Schema

Receipt queue entries are stored in the `receipt_queue` table:

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-increment primary key |
| `client_id` | TEXT | References the onboarding client (optional) |
| `doc_type` | TEXT | `expense_receipt`, `invoice`, `bill`, `bank_statement`, `other` |
| `status` | TEXT | `uploaded`, `scanning`, `scanned`, `approved`, `rejected`, `error` |
| `original_filename` | TEXT | Name of the uploaded file |
| `slack_file_id` | TEXT | Slack file identifier |
| `slack_user_id` | TEXT | Who uploaded the file |
| `slack_channel_id` | TEXT | Channel where it was uploaded |
| `extracted_data` | TEXT | JSON blob with all extracted fields |
| `confidence_score` | REAL | 0.0 to 1.0 confidence score |
| `created_at` | TEXT | Upload timestamp |
| `scanned_at` | TEXT | Scan completion timestamp |
| `reviewed_at` | TEXT | Review timestamp |
| `reviewed_by` | TEXT | Slack user who reviewed |

---

## Configuration

### Model Selection

By default, receipt scanning uses `claude-sonnet-4-5-20250929`. You can override this with an environment variable:

```bash
CLAUDE_MODEL=claude-sonnet-4-5-20250929
```

### API Key

Receipt scanning requires the Anthropic API key:

```bash
ANTHROPIC_API_KEY=your_key_here
```

This is the same key used by the main agent. No additional setup is needed if the bot is already working.

---

## Troubleshooting

### Scan returns low confidence or wrong data

- Ensure the image is clear and well-lit
- Crop the image to show only the document (remove background clutter)
- Higher resolution images produce better results
- Try re-uploading with a different angle or lighting

### "Parse error" in extracted data

Claude's response could not be parsed as JSON. This can happen with:
- Very blurry or unreadable images
- Images that are not financial documents
- Unusual document layouts

Check the bot logs for the raw response text.

### Scanning takes too long

The scan typically completes in 5-15 seconds. If it takes longer:
- Check your network connection
- Verify the Anthropic API is not experiencing issues
- Large images take longer -- consider resizing before upload

### File too large

Slack has a file size limit. If the image is very large:
- Resize or compress the image before uploading
- Take a photo at a lower resolution
- Screenshots are typically smaller than camera photos
