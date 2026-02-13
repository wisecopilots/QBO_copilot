"""
QBO Copilot Data Layer

SQLite-backed persistence for client onboarding, cases, and audit trails.
"""

from .onboarding_db import OnboardingDB

__all__ = ["OnboardingDB"]
