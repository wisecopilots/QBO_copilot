-- CPA Client Onboarding System - Initial Schema
-- File: qbo_copilot/data/migrations/001_initial.sql

-- Client records
CREATE TABLE IF NOT EXISTS clients (
    id TEXT PRIMARY KEY,
    legal_name TEXT NOT NULL,
    display_name TEXT,
    entity_type TEXT,  -- LLC, S-Corp, C-Corp, Sole Prop, Partnership
    year_end TEXT,     -- MM-DD (fiscal year end)
    qbo_realm_id TEXT,
    slack_channel_id TEXT,
    drive_folder_id TEXT,
    primary_contact_email TEXT,
    primary_contact_name TEXT,
    onboarding_phase INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Onboarding phase tracking
CREATE TABLE IF NOT EXISTS onboarding_phases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL REFERENCES clients(id),
    phase INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending, in_progress, completed, blocked
    started_at TEXT,
    completed_at TEXT,
    notes TEXT,
    UNIQUE(client_id, phase)
);

-- Contacts and roles
CREATE TABLE IF NOT EXISTS client_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL REFERENCES clients(id),
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    role TEXT,  -- owner, operator, approver, payroll_contact, bookkeeper
    is_primary BOOLEAN DEFAULT 0,
    approval_threshold REAL,  -- max $ they can approve
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Bank/CC accounts inventory
CREATE TABLE IF NOT EXISTS bank_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL REFERENCES clients(id),
    institution TEXT NOT NULL,
    account_type TEXT,  -- checking, savings, credit_card, loc
    last_four TEXT,
    nickname TEXT,
    feed_connected BOOLEAN DEFAULT 0,
    feed_verified_at TEXT,
    volume_estimate TEXT,  -- low, medium, high
    notes TEXT
);

-- Document requests and tracking
CREATE TABLE IF NOT EXISTS doc_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL REFERENCES clients(id),
    doc_type TEXT NOT NULL,
    period TEXT,  -- e.g., "2024", "Q4 2024", "Jan 2025"
    description TEXT,
    status TEXT DEFAULT 'requested',  -- requested, received, reviewed, filed
    requested_at TEXT DEFAULT CURRENT_TIMESTAMP,
    requested_by TEXT,
    due_date TEXT,
    received_at TEXT,
    drive_file_id TEXT,
    drive_folder_id TEXT,
    slack_thread_ts TEXT,
    notes TEXT
);

-- Cases (from message conversion)
CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT REFERENCES clients(id),
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'open',  -- open, in_progress, waiting_client, waiting_cpa, resolved
    priority TEXT DEFAULT 'normal',  -- low, normal, high, urgent
    assigned_to TEXT,
    slack_channel_id TEXT,
    slack_thread_ts TEXT,
    slack_permalink TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT
);

-- Audit trail
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT REFERENCES clients(id),
    case_id INTEGER REFERENCES cases(id),
    action TEXT NOT NULL,
    actor_slack_id TEXT,
    actor_name TEXT,
    details TEXT,  -- JSON
    slack_permalink TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Operating rules per client
CREATE TABLE IF NOT EXISTS operating_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL REFERENCES clients(id) UNIQUE,
    approval_threshold REAL DEFAULT 500,
    response_sla_hours INTEGER DEFAULT 48,
    close_schedule TEXT,  -- e.g., "monthly by 15th"
    communication_channel TEXT DEFAULT 'slack',
    escalation_contact TEXT,
    notes TEXT
);

-- Systems inventory
CREATE TABLE IF NOT EXISTS client_systems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL REFERENCES clients(id),
    system_type TEXT NOT NULL,  -- stripe, shopify, gusto, square, paypal, etc.
    system_name TEXT,
    status TEXT DEFAULT 'identified',  -- identified, connecting, connected, verified
    credentials_location TEXT,
    notes TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_clients_qbo_realm ON clients(qbo_realm_id);
CREATE INDEX IF NOT EXISTS idx_clients_slack_channel ON clients(slack_channel_id);
CREATE INDEX IF NOT EXISTS idx_onboarding_phases_client ON onboarding_phases(client_id);
CREATE INDEX IF NOT EXISTS idx_client_contacts_client ON client_contacts(client_id);
CREATE INDEX IF NOT EXISTS idx_bank_accounts_client ON bank_accounts(client_id);
CREATE INDEX IF NOT EXISTS idx_doc_requests_client ON doc_requests(client_id);
CREATE INDEX IF NOT EXISTS idx_doc_requests_status ON doc_requests(status);
CREATE INDEX IF NOT EXISTS idx_cases_client ON cases(client_id);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_audit_log_client ON audit_log(client_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_client_systems_client ON client_systems(client_id);
