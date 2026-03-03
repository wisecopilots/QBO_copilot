# Changelog

All notable changes to QBO Copilot are documented here.

## [0.1.0] - 2026-02-13

Initial public release.

### Added
- Natural language queries for QBO data via Slack (accounts, customers, vendors, invoices, expenses)
- Full CRUD operations: create, send, void, and delete invoices; create expenses; manage customers and vendors
- Receipt and invoice scanning with Claude Vision OCR (upload image, classify, AI extraction, review card)
- Multi-tenant architecture: multiple QBO companies per Slack workspace with channel-based routing
- 7-phase client onboarding state machine with progress tracking, blocker detection, and SQLite persistence
- 25+ tool registry for LLM-driven QBO operations with structured schemas
- Slack integration: Socket Mode bot, `/qbo` slash command, Home tab dashboard, message shortcuts, interactive modals
- Google Drive document vault with auto-created folder structures per client
- OAuth token management with automatic refresh on 401 responses
- Interactive setup script (`setup.sh`) with connection validation
- Integration test suite running against QBO sandbox API
