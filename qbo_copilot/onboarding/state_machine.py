"""
Onboarding State Machine

Manages the multi-phase client onboarding workflow with phase transitions,
completion tracking, and blocker detection.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

# Phase definitions
PHASES = {
    0: "start",           # Client record creation
    1: "contacts_roles",  # Capture contacts and routing rules
    2: "qbo_connect",     # QBO connection + verification
    3: "bank_feeds",      # Bank/CC inventory + feed status
    4: "documents",       # Doc vault + historical intake
    5: "systems",         # External systems inventory
    6: "operating_rules"  # Confirm cadence and rules
}

PHASE_NAMES = {
    0: "Client Setup",
    1: "Contacts & Roles",
    2: "QBO Connection",
    3: "Bank Feeds",
    4: "Document Vault",
    5: "Systems Inventory",
    6: "Operating Rules"
}

PHASE_DESCRIPTIONS = {
    0: "Create client record with basic information",
    1: "Add contacts with roles and approval thresholds",
    2: "Connect and verify QuickBooks Online access",
    3: "Inventory bank accounts and connect feeds",
    4: "Set up document vault and request historical docs",
    5: "Identify external systems (Stripe, Gusto, etc.)",
    6: "Confirm communication cadence and operating rules"
}


class OnboardingStateMachine:
    """Manages onboarding phase transitions and completion tracking"""

    def __init__(self, db):
        """
        Initialize with database instance

        Args:
            db: OnboardingDB instance
        """
        self.db = db

    def get_phase(self, client_id: str) -> int:
        """Get the current onboarding phase for a client"""
        client = self.db.get_client(client_id)
        if not client:
            return -1
        return client.get('onboarding_phase', 0)

    def get_phase_name(self, phase: int) -> str:
        """Get human-readable phase name"""
        return PHASE_NAMES.get(phase, f"Phase {phase}")

    def get_phase_description(self, phase: int) -> str:
        """Get phase description"""
        return PHASE_DESCRIPTIONS.get(phase, "")

    def get_phase_status(self, client_id: str, phase: int) -> Dict[str, Any]:
        """Get detailed status for a specific phase"""
        phase_record = self.db.get_phase_status(client_id, phase)
        if not phase_record:
            return {
                'phase': phase,
                'name': self.get_phase_name(phase),
                'status': 'pending',
                'completion_pct': 0,
                'items': [],
                'blockers': []
            }

        # Get completion details for this phase
        completion = self._calculate_phase_completion(client_id, phase)

        return {
            'phase': phase,
            'name': self.get_phase_name(phase),
            'status': phase_record.get('status', 'pending'),
            'started_at': phase_record.get('started_at'),
            'completed_at': phase_record.get('completed_at'),
            'notes': phase_record.get('notes'),
            'completion_pct': completion['percentage'],
            'items': completion['items'],
            'blockers': completion['blockers']
        }

    def get_all_phases_status(self, client_id: str) -> List[Dict[str, Any]]:
        """Get status for all phases"""
        return [
            self.get_phase_status(client_id, phase)
            for phase in range(7)
        ]

    def _calculate_phase_completion(self, client_id: str, phase: int) -> Dict[str, Any]:
        """Calculate completion percentage and items for a phase"""
        items = []
        blockers = []

        if phase == 0:
            # Phase 0: Client record creation
            client = self.db.get_client(client_id)
            if client:
                items.append({'name': 'Legal name', 'complete': bool(client.get('legal_name'))})
                items.append({'name': 'Entity type', 'complete': bool(client.get('entity_type'))})
                items.append({'name': 'Year end', 'complete': bool(client.get('year_end'))})
                items.append({'name': 'Primary contact', 'complete': bool(client.get('primary_contact_name'))})

        elif phase == 1:
            # Phase 1: Contacts and roles
            contacts = self.db.get_contacts(client_id)
            has_primary = any(c.get('is_primary') for c in contacts)
            has_approver = any(c.get('role') == 'approver' for c in contacts)

            items.append({'name': 'At least one contact', 'complete': len(contacts) > 0})
            items.append({'name': 'Primary contact designated', 'complete': has_primary})
            items.append({'name': 'Approver designated', 'complete': has_approver})

            if len(contacts) == 0:
                blockers.append("Add at least one contact")

        elif phase == 2:
            # Phase 2: QBO connection
            client = self.db.get_client(client_id)
            has_realm = bool(client.get('qbo_realm_id')) if client else False

            items.append({'name': 'QBO connected', 'complete': has_realm})
            items.append({'name': 'Realm ID verified', 'complete': has_realm})

            if not has_realm:
                blockers.append("Connect QuickBooks Online")

        elif phase == 3:
            # Phase 3: Bank feeds
            accounts = self.db.get_bank_accounts(client_id)
            connected = [a for a in accounts if a.get('feed_connected')]

            items.append({'name': 'Bank accounts listed', 'complete': len(accounts) > 0})
            items.append({'name': 'At least one feed connected', 'complete': len(connected) > 0})

            if len(accounts) == 0:
                blockers.append("Add at least one bank account")
            elif len(connected) == 0:
                blockers.append("Connect at least one bank feed")

        elif phase == 4:
            # Phase 4: Documents
            client = self.db.get_client(client_id)
            has_drive = bool(client.get('drive_folder_id')) if client else False
            doc_requests = self.db.get_doc_requests(client_id)
            received_count = len([d for d in doc_requests if d.get('status') in ('received', 'reviewed', 'filed')])

            items.append({'name': 'Drive folder created', 'complete': has_drive})
            items.append({'name': 'Doc requests created', 'complete': len(doc_requests) > 0})
            items.append({'name': 'Some docs received', 'complete': received_count > 0})

            if not has_drive:
                blockers.append("Create Google Drive folder")

        elif phase == 5:
            # Phase 5: Systems inventory
            systems = self.db.get_systems(client_id)
            connected = [s for s in systems if s.get('status') == 'connected']

            items.append({'name': 'Systems identified', 'complete': len(systems) > 0})
            items.append({'name': 'Systems connected', 'complete': len(connected) > 0 or len(systems) == 0})

        elif phase == 6:
            # Phase 6: Operating rules
            rules = self.db.get_operating_rules(client_id)
            client = self.db.get_client(client_id)
            has_channel = bool(client.get('slack_channel_id')) if client else False

            items.append({'name': 'Operating rules set', 'complete': rules is not None})
            items.append({'name': 'Slack channel created', 'complete': has_channel})

            if rules is None:
                blockers.append("Set operating rules")

        # Calculate percentage
        if items:
            completed = sum(1 for item in items if item['complete'])
            percentage = int((completed / len(items)) * 100)
        else:
            percentage = 0

        return {
            'percentage': percentage,
            'items': items,
            'blockers': blockers
        }

    def can_advance(self, client_id: str) -> bool:
        """Check if the current phase can be advanced"""
        current_phase = self.get_phase(client_id)
        if current_phase >= 6:
            return False

        completion = self._calculate_phase_completion(client_id, current_phase)
        return completion['percentage'] == 100 and len(completion['blockers']) == 0

    def advance_phase(self, client_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Advance to the next phase if conditions are met

        Args:
            client_id: Client ID
            force: If True, advance even if phase is not complete

        Returns:
            Dict with success status and new phase info
        """
        current_phase = self.get_phase(client_id)

        if current_phase >= 6:
            return {
                'success': False,
                'error': 'Onboarding already complete',
                'phase': current_phase
            }

        if not force and not self.can_advance(client_id):
            blockers = self.get_blockers(client_id)
            return {
                'success': False,
                'error': 'Phase requirements not met',
                'phase': current_phase,
                'blockers': blockers
            }

        # Mark current phase as completed
        self.db.update_phase(client_id, current_phase, 'completed')

        # Advance to next phase
        new_phase = current_phase + 1
        self.db.update_client(client_id, onboarding_phase=new_phase)
        self.db.update_phase(client_id, new_phase, 'in_progress')

        # Log the advancement
        self.db.log_action(
            action='phase_advanced',
            client_id=client_id,
            details={
                'from_phase': current_phase,
                'to_phase': new_phase,
                'forced': force
            }
        )

        return {
            'success': True,
            'phase': new_phase,
            'phase_name': self.get_phase_name(new_phase),
            'description': self.get_phase_description(new_phase)
        }

    def get_blockers(self, client_id: str) -> List[str]:
        """Get list of blockers for the current phase"""
        current_phase = self.get_phase(client_id)
        completion = self._calculate_phase_completion(client_id, current_phase)
        return completion['blockers']

    def get_overall_progress(self, client_id: str) -> Dict[str, Any]:
        """Get overall onboarding progress"""
        current_phase = self.get_phase(client_id)
        phases = self.get_all_phases_status(client_id)

        completed_phases = sum(1 for p in phases if p['status'] == 'completed')
        overall_pct = int((completed_phases / 7) * 100)

        # Add partial credit for current phase
        if current_phase < 7:
            current_completion = self._calculate_phase_completion(client_id, current_phase)
            phase_contribution = current_completion['percentage'] / 7
            overall_pct = int(overall_pct + phase_contribution)

        return {
            'current_phase': current_phase,
            'current_phase_name': self.get_phase_name(current_phase),
            'completed_phases': completed_phases,
            'total_phases': 7,
            'overall_percentage': min(overall_pct, 100),
            'phases': phases,
            'blockers': self.get_blockers(client_id) if current_phase < 7 else [],
            'is_complete': current_phase >= 6 and phases[6]['status'] == 'completed'
        }

    def start_onboarding(self, client_id: str) -> Dict[str, Any]:
        """Start the onboarding process for a client"""
        # Mark phase 0 as in_progress
        self.db.update_phase(client_id, 0, 'in_progress')

        self.db.log_action(
            action='onboarding_started',
            client_id=client_id,
            details={'phase': 0}
        )

        return {
            'success': True,
            'phase': 0,
            'phase_name': self.get_phase_name(0),
            'description': self.get_phase_description(0)
        }

    def complete_onboarding(self, client_id: str) -> Dict[str, Any]:
        """Mark onboarding as complete"""
        # Ensure we're at phase 6
        current_phase = self.get_phase(client_id)
        if current_phase < 6:
            return {
                'success': False,
                'error': 'Not at final phase',
                'phase': current_phase
            }

        # Mark final phase as completed
        self.db.update_phase(client_id, 6, 'completed')

        self.db.log_action(
            action='onboarding_completed',
            client_id=client_id,
            details={'final_phase': 6}
        )

        return {
            'success': True,
            'message': 'Onboarding complete!'
        }

    def reset_phase(self, client_id: str, phase: int) -> bool:
        """Reset a phase to pending status"""
        if phase < 0 or phase > 6:
            return False

        self.db.update_phase(client_id, phase, 'pending')

        # If resetting to earlier than current phase, update current phase
        current = self.get_phase(client_id)
        if phase < current:
            self.db.update_client(client_id, onboarding_phase=phase)

        self.db.log_action(
            action='phase_reset',
            client_id=client_id,
            details={'phase': phase}
        )

        return True
