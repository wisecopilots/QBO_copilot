"""
Onboarding Database Layer

SQLite-backed persistence for client onboarding, cases, and audit trails.
Keeps data separate from OpenClaw's memory database.
"""

import os
import json
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


def get_db_path() -> Path:
    """Get the database path, using env var or default"""
    env_path = os.getenv("ONBOARDING_DB_PATH")
    if env_path:
        return Path(env_path)

    # Default: qbo_copilot/data/onboarding.sqlite
    return Path(__file__).parent / "onboarding.sqlite"


class OnboardingDB:
    """Database operations for client onboarding system"""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            self.db_path = get_db_path()
        elif isinstance(db_path, str):
            self.db_path = Path(db_path)
        else:
            self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema if not exists"""
        migrations_dir = Path(__file__).parent / "migrations"

        with self._get_conn() as conn:
            if migrations_dir.exists():
                for migration_path in sorted(migrations_dir.glob("*.sql")):
                    conn.executescript(migration_path.read_text())
            conn.commit()

    @contextmanager
    def _get_conn(self):
        """Get a database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a sqlite Row to a dict"""
        return dict(row) if row else None

    def _rows_to_dicts(self, rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
        """Convert multiple rows to dicts"""
        return [dict(row) for row in rows]

    # -----------------------------------------------------------------------
    # Client CRUD
    # -----------------------------------------------------------------------

    def create_client(
        self,
        legal_name: str,
        display_name: Optional[str] = None,
        entity_type: Optional[str] = None,
        year_end: Optional[str] = None,
        primary_contact_name: Optional[str] = None,
        primary_contact_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new client record"""
        client_id = str(uuid.uuid4())[:8]

        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO clients (
                    id, legal_name, display_name, entity_type, year_end,
                    primary_contact_name, primary_contact_email
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                client_id, legal_name, display_name or legal_name, entity_type,
                year_end, primary_contact_name, primary_contact_email
            ))

            # Initialize onboarding phases (0-6)
            for phase in range(7):
                conn.execute("""
                    INSERT INTO onboarding_phases (client_id, phase, status)
                    VALUES (?, ?, ?)
                """, (client_id, phase, 'pending'))

            conn.commit()

        return self.get_client(client_id)

    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get a client by ID"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM clients WHERE id = ?", (client_id,)
            ).fetchone()
            return self._row_to_dict(row)

    def get_client_by_slack_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get a client by Slack channel ID"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM clients WHERE slack_channel_id = ?", (channel_id,)
            ).fetchone()
            return self._row_to_dict(row)

    def get_client_by_qbo_realm(self, realm_id: str) -> Optional[Dict[str, Any]]:
        """Get a client by QBO realm ID"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM clients WHERE qbo_realm_id = ?", (realm_id,)
            ).fetchone()
            return self._row_to_dict(row)

    def list_clients(self, include_completed: bool = True) -> List[Dict[str, Any]]:
        """List all clients"""
        with self._get_conn() as conn:
            if include_completed:
                rows = conn.execute(
                    "SELECT * FROM clients ORDER BY created_at DESC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM clients WHERE onboarding_phase < 6 ORDER BY created_at DESC"
                ).fetchall()
            return self._rows_to_dicts(rows)

    def update_client(self, client_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Update a client record"""
        allowed_fields = {
            'legal_name', 'display_name', 'entity_type', 'year_end',
            'qbo_realm_id', 'slack_channel_id', 'drive_folder_id',
            'primary_contact_email', 'primary_contact_name', 'onboarding_phase'
        }

        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return self.get_client(client_id)

        updates['updated_at'] = datetime.utcnow().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [client_id]

        with self._get_conn() as conn:
            conn.execute(
                f"UPDATE clients SET {set_clause} WHERE id = ?", values
            )
            conn.commit()

        return self.get_client(client_id)

    def delete_client(self, client_id: str) -> bool:
        """Delete a client and all related records"""
        with self._get_conn() as conn:
            # Delete related records first
            for table in ['onboarding_phases', 'client_contacts', 'bank_accounts',
                         'doc_requests', 'cases', 'audit_log', 'operating_rules',
                         'client_systems']:
                conn.execute(f"DELETE FROM {table} WHERE client_id = ?", (client_id,))

            result = conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
            conn.commit()
            return result.rowcount > 0

    # -----------------------------------------------------------------------
    # Onboarding Phases
    # -----------------------------------------------------------------------

    def get_phase_status(self, client_id: str, phase: int) -> Optional[Dict[str, Any]]:
        """Get the status of a specific phase"""
        with self._get_conn() as conn:
            row = conn.execute("""
                SELECT * FROM onboarding_phases
                WHERE client_id = ? AND phase = ?
            """, (client_id, phase)).fetchone()
            return self._row_to_dict(row)

    def get_all_phases(self, client_id: str) -> List[Dict[str, Any]]:
        """Get all phases for a client"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM onboarding_phases
                WHERE client_id = ? ORDER BY phase
            """, (client_id,)).fetchall()
            return self._rows_to_dicts(rows)

    def update_phase(
        self,
        client_id: str,
        phase: int,
        status: str,
        notes: Optional[str] = None
    ) -> bool:
        """Update a phase status"""
        with self._get_conn() as conn:
            now = datetime.utcnow().isoformat()

            update_fields = ["status = ?"]
            values = [status]

            if status == 'in_progress':
                update_fields.append("started_at = ?")
                values.append(now)
            elif status == 'completed':
                update_fields.append("completed_at = ?")
                values.append(now)

            if notes is not None:
                update_fields.append("notes = ?")
                values.append(notes)

            values.extend([client_id, phase])

            result = conn.execute(f"""
                UPDATE onboarding_phases
                SET {", ".join(update_fields)}
                WHERE client_id = ? AND phase = ?
            """, values)
            conn.commit()
            return result.rowcount > 0

    # -----------------------------------------------------------------------
    # Contacts
    # -----------------------------------------------------------------------

    def add_contact(
        self,
        client_id: str,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        role: Optional[str] = None,
        is_primary: bool = False,
        approval_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """Add a contact for a client"""
        with self._get_conn() as conn:
            if is_primary:
                # Clear existing primary flag
                conn.execute("""
                    UPDATE client_contacts SET is_primary = 0
                    WHERE client_id = ?
                """, (client_id,))

            cursor = conn.execute("""
                INSERT INTO client_contacts (
                    client_id, name, email, phone, role, is_primary, approval_threshold
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (client_id, name, email, phone, role, is_primary, approval_threshold))
            conn.commit()

            row = conn.execute(
                "SELECT * FROM client_contacts WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return self._row_to_dict(row)

    def get_contacts(self, client_id: str) -> List[Dict[str, Any]]:
        """Get all contacts for a client"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM client_contacts
                WHERE client_id = ? ORDER BY is_primary DESC, name
            """, (client_id,)).fetchall()
            return self._rows_to_dicts(rows)

    def update_contact(self, contact_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Update a contact"""
        allowed_fields = {'name', 'email', 'phone', 'role', 'is_primary', 'approval_threshold'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return None

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [contact_id]

        with self._get_conn() as conn:
            conn.execute(
                f"UPDATE client_contacts SET {set_clause} WHERE id = ?", values
            )
            conn.commit()

            row = conn.execute(
                "SELECT * FROM client_contacts WHERE id = ?", (contact_id,)
            ).fetchone()
            return self._row_to_dict(row)

    def delete_contact(self, contact_id: int) -> bool:
        """Delete a contact"""
        with self._get_conn() as conn:
            result = conn.execute(
                "DELETE FROM client_contacts WHERE id = ?", (contact_id,)
            )
            conn.commit()
            return result.rowcount > 0

    # -----------------------------------------------------------------------
    # Bank Accounts
    # -----------------------------------------------------------------------

    def add_bank_account(
        self,
        client_id: str,
        institution: str,
        account_type: Optional[str] = None,
        last_four: Optional[str] = None,
        nickname: Optional[str] = None,
        volume_estimate: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a bank account"""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO bank_accounts (
                    client_id, institution, account_type, last_four,
                    nickname, volume_estimate, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (client_id, institution, account_type, last_four, nickname, volume_estimate, notes))
            conn.commit()

            row = conn.execute(
                "SELECT * FROM bank_accounts WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return self._row_to_dict(row)

    def get_bank_accounts(self, client_id: str) -> List[Dict[str, Any]]:
        """Get all bank accounts for a client"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM bank_accounts WHERE client_id = ?
                ORDER BY institution, account_type
            """, (client_id,)).fetchall()
            return self._rows_to_dicts(rows)

    def update_bank_account(self, account_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Update a bank account"""
        allowed_fields = {
            'institution', 'account_type', 'last_four', 'nickname',
            'feed_connected', 'feed_verified_at', 'volume_estimate', 'notes'
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return None

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [account_id]

        with self._get_conn() as conn:
            conn.execute(
                f"UPDATE bank_accounts SET {set_clause} WHERE id = ?", values
            )
            conn.commit()

            row = conn.execute(
                "SELECT * FROM bank_accounts WHERE id = ?", (account_id,)
            ).fetchone()
            return self._row_to_dict(row)

    def mark_feed_connected(self, account_id: int) -> bool:
        """Mark a bank feed as connected"""
        with self._get_conn() as conn:
            result = conn.execute("""
                UPDATE bank_accounts
                SET feed_connected = 1, feed_verified_at = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), account_id))
            conn.commit()
            return result.rowcount > 0

    def delete_bank_account(self, account_id: int) -> bool:
        """Delete a bank account"""
        with self._get_conn() as conn:
            result = conn.execute(
                "DELETE FROM bank_accounts WHERE id = ?", (account_id,)
            )
            conn.commit()
            return result.rowcount > 0

    # -----------------------------------------------------------------------
    # Document Requests
    # -----------------------------------------------------------------------

    def create_doc_request(
        self,
        client_id: str,
        doc_type: str,
        period: Optional[str] = None,
        description: Optional[str] = None,
        requested_by: Optional[str] = None,
        due_date: Optional[str] = None,
        slack_thread_ts: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a document request"""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO doc_requests (
                    client_id, doc_type, period, description,
                    requested_by, due_date, slack_thread_ts
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (client_id, doc_type, period, description, requested_by, due_date, slack_thread_ts))
            conn.commit()

            row = conn.execute(
                "SELECT * FROM doc_requests WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return self._row_to_dict(row)

    def get_doc_requests(
        self,
        client_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get document requests for a client"""
        with self._get_conn() as conn:
            if status:
                rows = conn.execute("""
                    SELECT * FROM doc_requests
                    WHERE client_id = ? AND status = ?
                    ORDER BY requested_at DESC
                """, (client_id, status)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM doc_requests
                    WHERE client_id = ?
                    ORDER BY requested_at DESC
                """, (client_id,)).fetchall()
            return self._rows_to_dicts(rows)

    def get_pending_doc_requests(self) -> List[Dict[str, Any]]:
        """Get all pending document requests across all clients"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT dr.*, c.display_name as client_name
                FROM doc_requests dr
                JOIN clients c ON dr.client_id = c.id
                WHERE dr.status IN ('requested', 'received')
                ORDER BY dr.due_date ASC, dr.requested_at ASC
            """).fetchall()
            return self._rows_to_dicts(rows)

    def update_doc_request(self, request_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Update a document request"""
        allowed_fields = {
            'status', 'received_at', 'drive_file_id', 'drive_folder_id',
            'slack_thread_ts', 'notes'
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return None

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [request_id]

        with self._get_conn() as conn:
            conn.execute(
                f"UPDATE doc_requests SET {set_clause} WHERE id = ?", values
            )
            conn.commit()

            row = conn.execute(
                "SELECT * FROM doc_requests WHERE id = ?", (request_id,)
            ).fetchone()
            return self._row_to_dict(row)

    def mark_doc_received(
        self,
        request_id: int,
        drive_file_id: Optional[str] = None,
        drive_folder_id: Optional[str] = None
    ) -> bool:
        """Mark a document as received"""
        with self._get_conn() as conn:
            result = conn.execute("""
                UPDATE doc_requests
                SET status = 'received', received_at = ?,
                    drive_file_id = COALESCE(?, drive_file_id),
                    drive_folder_id = COALESCE(?, drive_folder_id)
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), drive_file_id, drive_folder_id, request_id))
            conn.commit()
            return result.rowcount > 0

    # -----------------------------------------------------------------------
    # Cases
    # -----------------------------------------------------------------------

    def create_case(
        self,
        title: str,
        client_id: Optional[str] = None,
        description: Optional[str] = None,
        priority: str = 'normal',
        assigned_to: Optional[str] = None,
        slack_channel_id: Optional[str] = None,
        slack_thread_ts: Optional[str] = None,
        slack_permalink: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a case"""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO cases (
                    client_id, title, description, priority, assigned_to,
                    slack_channel_id, slack_thread_ts, slack_permalink
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (client_id, title, description, priority, assigned_to,
                  slack_channel_id, slack_thread_ts, slack_permalink))
            conn.commit()

            row = conn.execute(
                "SELECT * FROM cases WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return self._row_to_dict(row)

    def get_case(self, case_id: int) -> Optional[Dict[str, Any]]:
        """Get a case by ID"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM cases WHERE id = ?", (case_id,)
            ).fetchone()
            return self._row_to_dict(row)

    def get_cases(
        self,
        client_id: Optional[str] = None,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get cases with optional filters"""
        conditions = []
        params = []

        if client_id:
            conditions.append("client_id = ?")
            params.append(client_id)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if assigned_to:
            conditions.append("assigned_to = ?")
            params.append(assigned_to)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with self._get_conn() as conn:
            rows = conn.execute(f"""
                SELECT * FROM cases
                WHERE {where_clause}
                ORDER BY
                    CASE priority
                        WHEN 'urgent' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'normal' THEN 3
                        WHEN 'low' THEN 4
                    END,
                    created_at DESC
            """, params).fetchall()
            return self._rows_to_dicts(rows)

    def get_open_cases(self) -> List[Dict[str, Any]]:
        """Get all open cases across all clients"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT cs.*, c.display_name as client_name
                FROM cases cs
                LEFT JOIN clients c ON cs.client_id = c.id
                WHERE cs.status NOT IN ('resolved')
                ORDER BY
                    CASE cs.priority
                        WHEN 'urgent' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'normal' THEN 3
                        WHEN 'low' THEN 4
                    END,
                    cs.created_at DESC
            """).fetchall()
            return self._rows_to_dicts(rows)

    def update_case(self, case_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Update a case"""
        allowed_fields = {
            'title', 'description', 'status', 'priority', 'assigned_to',
            'slack_channel_id', 'slack_thread_ts', 'slack_permalink'
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return None

        updates['updated_at'] = datetime.utcnow().isoformat()

        if updates.get('status') == 'resolved':
            updates['resolved_at'] = datetime.utcnow().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [case_id]

        with self._get_conn() as conn:
            conn.execute(
                f"UPDATE cases SET {set_clause} WHERE id = ?", values
            )
            conn.commit()

            row = conn.execute(
                "SELECT * FROM cases WHERE id = ?", (case_id,)
            ).fetchone()
            return self._row_to_dict(row)

    # -----------------------------------------------------------------------
    # Audit Log
    # -----------------------------------------------------------------------

    def log_action(
        self,
        action: str,
        client_id: Optional[str] = None,
        case_id: Optional[int] = None,
        actor_slack_id: Optional[str] = None,
        actor_name: Optional[str] = None,
        details: Optional[Dict] = None,
        slack_permalink: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log an action to the audit trail"""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO audit_log (
                    client_id, case_id, action, actor_slack_id,
                    actor_name, details, slack_permalink
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                client_id, case_id, action, actor_slack_id, actor_name,
                json.dumps(details) if details else None, slack_permalink
            ))
            conn.commit()

            row = conn.execute(
                "SELECT * FROM audit_log WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return self._row_to_dict(row)

    def get_audit_log(
        self,
        client_id: Optional[str] = None,
        case_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit log entries"""
        conditions = []
        params = []

        if client_id:
            conditions.append("client_id = ?")
            params.append(client_id)
        if case_id:
            conditions.append("case_id = ?")
            params.append(case_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        with self._get_conn() as conn:
            rows = conn.execute(f"""
                SELECT * FROM audit_log
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ?
            """, params).fetchall()
            return self._rows_to_dicts(rows)

    # -----------------------------------------------------------------------
    # Operating Rules
    # -----------------------------------------------------------------------

    def set_operating_rules(
        self,
        client_id: str,
        approval_threshold: float = 500,
        response_sla_hours: int = 48,
        close_schedule: Optional[str] = None,
        communication_channel: str = 'slack',
        escalation_contact: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Set or update operating rules for a client"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO operating_rules (
                    client_id, approval_threshold, response_sla_hours,
                    close_schedule, communication_channel, escalation_contact, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(client_id) DO UPDATE SET
                    approval_threshold = excluded.approval_threshold,
                    response_sla_hours = excluded.response_sla_hours,
                    close_schedule = excluded.close_schedule,
                    communication_channel = excluded.communication_channel,
                    escalation_contact = excluded.escalation_contact,
                    notes = excluded.notes
            """, (client_id, approval_threshold, response_sla_hours,
                  close_schedule, communication_channel, escalation_contact, notes))
            conn.commit()

            row = conn.execute(
                "SELECT * FROM operating_rules WHERE client_id = ?", (client_id,)
            ).fetchone()
            return self._row_to_dict(row)

    def get_operating_rules(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get operating rules for a client"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM operating_rules WHERE client_id = ?", (client_id,)
            ).fetchone()
            return self._row_to_dict(row)

    # -----------------------------------------------------------------------
    # Client Systems
    # -----------------------------------------------------------------------

    def add_system(
        self,
        client_id: str,
        system_type: str,
        system_name: Optional[str] = None,
        status: str = 'identified',
        credentials_location: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a system to client inventory"""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO client_systems (
                    client_id, system_type, system_name, status,
                    credentials_location, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (client_id, system_type, system_name, status, credentials_location, notes))
            conn.commit()

            row = conn.execute(
                "SELECT * FROM client_systems WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return self._row_to_dict(row)

    def get_systems(self, client_id: str) -> List[Dict[str, Any]]:
        """Get all systems for a client"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM client_systems
                WHERE client_id = ?
                ORDER BY system_type
            """, (client_id,)).fetchall()
            return self._rows_to_dicts(rows)

    def update_system(self, system_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Update a system"""
        allowed_fields = {'system_type', 'system_name', 'status', 'credentials_location', 'notes'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return None

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [system_id]

        with self._get_conn() as conn:
            conn.execute(
                f"UPDATE client_systems SET {set_clause} WHERE id = ?", values
            )
            conn.commit()

            row = conn.execute(
                "SELECT * FROM client_systems WHERE id = ?", (system_id,)
            ).fetchone()
            return self._row_to_dict(row)

    def delete_system(self, system_id: int) -> bool:
        """Delete a system"""
        with self._get_conn() as conn:
            result = conn.execute(
                "DELETE FROM client_systems WHERE id = ?", (system_id,)
            )
            conn.commit()
            return result.rowcount > 0

    # -----------------------------------------------------------------------
    # Waiting Queues
    # -----------------------------------------------------------------------

    def get_waiting_on_client(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get items waiting on client response"""
        result = {
            'doc_requests': [],
            'cases': []
        }

        with self._get_conn() as conn:
            # Pending doc requests
            rows = conn.execute("""
                SELECT dr.*, c.display_name as client_name
                FROM doc_requests dr
                JOIN clients c ON dr.client_id = c.id
                WHERE dr.status = 'requested'
                ORDER BY dr.due_date ASC, dr.requested_at ASC
            """).fetchall()
            result['doc_requests'] = self._rows_to_dicts(rows)

            # Cases waiting on client
            rows = conn.execute("""
                SELECT cs.*, c.display_name as client_name
                FROM cases cs
                LEFT JOIN clients c ON cs.client_id = c.id
                WHERE cs.status = 'waiting_client'
                ORDER BY cs.created_at DESC
            """).fetchall()
            result['cases'] = self._rows_to_dicts(rows)

        return result

    def get_waiting_on_cpa(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get items waiting on CPA action"""
        result = {
            'doc_requests': [],
            'cases': []
        }

        with self._get_conn() as conn:
            # Docs received but not reviewed
            rows = conn.execute("""
                SELECT dr.*, c.display_name as client_name
                FROM doc_requests dr
                JOIN clients c ON dr.client_id = c.id
                WHERE dr.status = 'received'
                ORDER BY dr.received_at ASC
            """).fetchall()
            result['doc_requests'] = self._rows_to_dicts(rows)

            # Cases waiting on CPA
            rows = conn.execute("""
                SELECT cs.*, c.display_name as client_name
                FROM cases cs
                LEFT JOIN clients c ON cs.client_id = c.id
                WHERE cs.status IN ('open', 'in_progress', 'waiting_cpa')
                ORDER BY
                    CASE cs.priority
                        WHEN 'urgent' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'normal' THEN 3
                        WHEN 'low' THEN 4
                    END,
                    cs.created_at ASC
            """).fetchall()
            result['cases'] = self._rows_to_dicts(rows)

        return result

    # -----------------------------------------------------------------------
    # Receipt Queue
    # -----------------------------------------------------------------------

    def create_receipt(
        self,
        doc_type: str,
        original_filename: str,
        slack_file_id: str,
        slack_user_id: str,
        slack_channel_id: str,
        slack_message_ts: Optional[str] = None,
        client_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a receipt queue entry"""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO receipt_queue (
                    client_id, doc_type, status, original_filename,
                    slack_file_id, slack_user_id, slack_channel_id, slack_message_ts
                ) VALUES (?, ?, 'uploaded', ?, ?, ?, ?, ?)
            """, (
                client_id, doc_type, original_filename,
                slack_file_id, slack_user_id, slack_channel_id, slack_message_ts
            ))
            conn.commit()

            row = conn.execute(
                "SELECT * FROM receipt_queue WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return self._row_to_dict(row)

    def get_receipt(self, receipt_id: int) -> Optional[Dict[str, Any]]:
        """Get a receipt by ID"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM receipt_queue WHERE id = ?", (receipt_id,)
            ).fetchone()
            return self._row_to_dict(row)

    def update_receipt(self, receipt_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Update a receipt queue entry"""
        allowed_fields = {
            'status', 'doc_type', 'drive_file_id', 'drive_folder_id',
            'extracted_data', 'confidence_score', 'scanned_at',
            'reviewed_at', 'reviewed_by', 'posted_at', 'notes', 'client_id'
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return self.get_receipt(receipt_id)

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [receipt_id]

        with self._get_conn() as conn:
            conn.execute(
                f"UPDATE receipt_queue SET {set_clause} WHERE id = ?", values
            )
            conn.commit()

        return self.get_receipt(receipt_id)

    def get_receipts_by_status(
        self,
        status: Optional[str] = None,
        client_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get receipts filtered by status and/or client"""
        conditions = []
        params = []

        if status:
            conditions.append("status = ?")
            params.append(status)
        if client_id:
            conditions.append("client_id = ?")
            params.append(client_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        with self._get_conn() as conn:
            rows = conn.execute(f"""
                SELECT * FROM receipt_queue
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ?
            """, params).fetchall()
            return self._rows_to_dicts(rows)

    def get_receipt_queue_summary(self, client_id: Optional[str] = None) -> Dict[str, int]:
        """Get receipt queue counts by status"""
        with self._get_conn() as conn:
            if client_id:
                rows = conn.execute("""
                    SELECT status, COUNT(*) as count
                    FROM receipt_queue
                    WHERE client_id = ?
                    GROUP BY status
                """, (client_id,)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT status, COUNT(*) as count
                    FROM receipt_queue
                    GROUP BY status
                """).fetchall()

            return {row['status']: row['count'] for row in rows}
