"""
QBO Copilot Onboarding Module

Manages the multi-phase client onboarding workflow.
"""

from .state_machine import OnboardingStateMachine, PHASES, PHASE_NAMES
from .doc_templates import ONBOARDING_DOC_PACK, create_doc_request_pack

__all__ = [
    "OnboardingStateMachine",
    "PHASES",
    "PHASE_NAMES",
    "ONBOARDING_DOC_PACK",
    "create_doc_request_pack",
]
