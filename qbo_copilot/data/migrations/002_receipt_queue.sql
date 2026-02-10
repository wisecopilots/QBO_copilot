-- Receipt/Invoice Queue - Document scanning and approval workflow
-- File: qbo_copilot/data/migrations/002_receipt_queue.sql

CREATE TABLE IF NOT EXISTS receipt_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT REFERENCES clients(id),
    doc_type TEXT NOT NULL,  -- expense_receipt, invoice, bill, bank_statement, other
    status TEXT DEFAULT 'uploaded',  -- uploaded, scanning, scanned, approved, rejected, error
    original_filename TEXT,
    slack_file_id TEXT,
    slack_user_id TEXT,
    slack_channel_id TEXT,
    slack_message_ts TEXT,
    drive_file_id TEXT,
    drive_folder_id TEXT,
    extracted_data TEXT,  -- JSON: vendor, amount, date, tax, line_items, etc.
    confidence_score REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    scanned_at TEXT,
    reviewed_at TEXT,
    reviewed_by TEXT,
    posted_at TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_receipt_queue_client ON receipt_queue(client_id);
CREATE INDEX IF NOT EXISTS idx_receipt_queue_status ON receipt_queue(status);
CREATE INDEX IF NOT EXISTS idx_receipt_queue_slack_file ON receipt_queue(slack_file_id);
