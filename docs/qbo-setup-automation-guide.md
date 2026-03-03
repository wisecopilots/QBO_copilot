# QBO Setup Automation Guide

> Agent-driven QuickBooks Online setup and configuration for the QBO Copilot.
> Research completed February 2026.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [QBO Setup Process by Complexity Tier](#qbo-setup-process-by-complexity-tier)
3. [What the Agent Can Automate](#what-the-agent-can-automate)
4. [Minimum Required Human Intervention](#minimum-required-human-intervention)
5. [API Capabilities and Limitations](#api-capabilities-and-limitations)
6. [Browser Automation Opportunities](#browser-automation-opportunities)
7. [Irreversible Settings (Critical)](#irreversible-settings-critical)
8. [Agent-Driven Setup Flow (Proposed)](#agent-driven-setup-flow-proposed)
9. [Industry Templates](#industry-templates)
10. [Implementation Architecture](#implementation-architecture)
11. [Database Schema](#database-schema)
12. [New Tools Required](#new-tools-required)
13. [Security and Guardrails](#security-and-guardrails)
14. [Implementation Roadmap](#implementation-roadmap)

---

## Executive Summary

This guide documents the research and design for adding a conversational QBO setup skill to the QBO Copilot. The key findings:

- **No existing product** provides end-to-end programmatic QBO setup through a conversational interface. This is a genuine market gap.
- A **hybrid API + browser automation** approach can automate ~90% of QBO setup tasks. Only 2 of 20 setup tasks truly require unaided human action.
- The **minimum viable human setup** is ~15 minutes of owner action + ~30 minutes of CPA decisions before the agent takes over everything else.
- Under Intuit's 2025 App Partner Program, **setup write operations are free and unlimited** (Core API calls).
- The setup skill integrates into the existing onboarding state machine as sub-phases within Phase 2.

---

## QBO Setup Process by Complexity Tier

### Tier 1: Simple (Freelancer / Sole Proprietor)

**Profile**: Service-only, <$250K revenue, no employees, 1-2 bank accounts.

| Step | Information Required | Where in QBO |
|------|---------------------|--------------|
| Company Info | Legal name, DBA, address, phone, email | Settings > Company |
| Tax Form | Schedule C (Form 1040) | Settings > Advanced |
| EIN or SSN | Federal tax ID | Settings > Company |
| Industry | Select from list | Wizard or Settings |
| Fiscal Year | Starting month (usually January) | Settings > Advanced |
| Accounting Method | Cash (typical for this tier) | Settings > Advanced |
| Bank Connection | 1-2 accounts via Plaid | Banking > Connect |
| Invoice Setup | Logo, terms, template | Custom Form Styles |
| Products/Services | Service items with rates | Products & Services |

**Agent handles**: CoA population (15-20 accounts), invoice template, products/services, preferences.
**Human handles**: Intuit account, EIN, bank connection.
**Estimated setup time**: 15 min human + 5 min agent execution.

### Tier 2: Moderate (Small Business, 1-10 Employees)

Everything in Tier 1, plus:

| Additional Step | Details |
|----------------|---------|
| Payroll | Federal EIN, state tax IDs, employee SSNs, W-4s, pay schedule |
| Inventory | FIFO only; items with qty on hand, cost, reorder points |
| Sales Tax | State registration numbers, nexus determination, product taxability |
| Classes/Locations | Department or project tracking (QBO Plus/Advanced) |
| Users & Permissions | Team access with role assignments |
| 1099 Tracking | Flag contractor vendors |

**Agent handles**: Expanded CoA (30-50 accounts), customer/vendor bulk import, inventory items, classes/locations, bank rules (20-30), recurring transactions.
**Human handles**: Payroll sensitive data (SSNs, bank details), bank connections, user role decisions.
**Estimated setup time**: 30 min human + 10 min agent execution.

### Tier 3: Complex (Multi-Entity, CPA-Managed)

Everything in Tiers 1-2, plus:

| Additional Step | Details |
|----------------|---------|
| Multi-Currency | IRREVERSIBLE once enabled; home currency locked |
| Custom Fields | Up to 30 per customer profile (all tiers); 12 per transaction (Advanced) |
| Custom Roles | Up to 25 users with granular permissions (Advanced) |
| Workflow Automation | 60+ templates for approvals, reminders, routing (Advanced) |
| Multi-Entity | Separate QBO subscription per entity; QBOA for unified management |
| Advanced Reporting | Custom Report Builder, Fathom dashboards, Spreadsheet Sync |
| Third-Party Integrations | E-commerce, POS, CRM, payroll, document management |

**Agent handles**: Full CoA with hierarchy (50-80 accounts), all entity imports, custom fields, workflow setup, report configurations, tag structure.
**Human handles**: Multi-currency decision (irreversible), opening balances verification, entity structure decisions, third-party OAuth flows.
**Estimated setup time**: 60 min human decisions + 15 min agent execution.

---

## What the Agent Can Automate

### Via QBO REST API (Existing Infrastructure)

| Operation | Endpoint | Batch-able | Notes |
|-----------|----------|-----------|-------|
| Chart of Accounts | `POST /v3/company/{id}/account` | Yes (30/batch) | Create, deactivate; cannot delete or change type |
| Customers | `POST /v3/company/{id}/customer` | Yes | Full CRUD |
| Vendors | `POST /v3/company/{id}/vendor` | Yes | Full CRUD, 1099 tracking |
| Products/Services | `POST /v3/company/{id}/item` | Yes | Service, Inventory, NonInventory |
| Payment Terms | `POST /v3/company/{id}/term` | Yes | Net 30, Due on Receipt, etc. |
| Classes | `POST /v3/company/{id}/class` | Yes | Department/segment tracking |
| Departments/Locations | `POST /v3/company/{id}/department` | Yes | Geographic/location tracking |
| Preferences | `POST /v3/company/{id}/preferences` | N/A | Accounting method, fiscal year, features |
| Company Info | `POST /v3/company/{id}/companyinfo` | N/A | Name, address, contact info |
| Recurring Transactions | `POST /v3/company/{id}/recurringtransaction` | Yes | Scheduled invoices, bills |
| Opening Balances | `POST /v3/company/{id}/journalentry` | Yes | Via journal entries |

**Rate limits**: 500 requests/min per realm, 30 operations per batch, 40 batches/min.
**Typical setup**: ~120 entities = 4 batch requests. Well under limits.

### Via Browser Automation (New Capability)

| Operation | Automation Level | Value | Priority |
|-----------|-----------------|-------|----------|
| Bank Rules | Fully automatable | Very High | P1 |
| Tags | Fully automatable | Very High | P1 |
| CSV Data Import | Fully automatable | Very High | P1 |
| Closing Date/Password | Fully automatable | High | P1 |
| CoA Template Application | Fully automatable | High | P1 |
| Custom Fields | Fully automatable | Medium | P2 |
| Projects | Fully automatable | Medium | P2 |
| Company Logo Upload | Fully automatable | Low | P3 |
| Bank Reconciliation | Browser-assisted | Very High | P1 |
| Invoice Templates | Browser-assisted | Medium | P2 |
| Sales Tax Config | Browser-assisted | Medium | P2 |
| Workflow Automation | Browser-assisted | Medium | P2 |
| Report Customization | Browser-assisted | Medium | P2 |
| Email Templates | Browser-assisted | Low | P3 |
| User/Role Management | Browser-assisted | Medium | P2 |

### Things With No API and No Safe Browser Path

| Operation | Why | Agent's Role |
|-----------|-----|-------------|
| Bank Connections (Plaid) | Cross-origin iframe, bank credentials, MFA | Guide human; verify afterward |
| Payroll Setup (sensitive fields) | SSNs, employee bank details | Fill non-sensitive fields; guide human for PII |
| Third-Party App OAuth | Credentials on third-party sites | Navigate to OAuth URL; guide consent flow |
| QB Payments KYC | Identity verification, government ID | Explain process; fill non-sensitive fields |
| Subscription Changes | Financial transaction | Advise on plan selection; human executes |

---

## Minimum Required Human Intervention

### Business Owner (~15 minutes)

| Action | Why It Cannot Be Delegated |
|--------|---------------------------|
| Create Intuit account | Legal contract, identity, payment |
| Enter EIN | Primary Admin only, IRS compliance |
| Connect bank account(s) via Plaid | Bank credentials + MFA |
| Invite CPA as accountant user | Must be done by Primary Admin |

### CPA / Accountant (~30-60 minutes of decisions)

| Action | Why It Needs Professional Judgment |
|--------|-----------------------------------|
| Confirm accounting method (cash/accrual) | Tax election; IRS Form 3115 to change |
| Confirm fiscal year | IRS Form 1128 to change |
| Review/approve CoA template | Foundation of all financial reporting |
| Provide opening balances (mid-year conversion) | Must tie to prior-year financials |
| Determine sales tax nexus states | Legal/tax obligation |
| Specify depreciation methods | Tax implications |

### Everything Else: Agent Takes Over

After the above ~45-75 minutes of human involvement, the agent can execute all remaining setup autonomously via API + browser automation.

---

## API Capabilities and Limitations

### Entities with Full CRUD

Account, Customer, Vendor, Item, Class, Department, Term, Employee, Invoice, Bill, JournalEntry, Payment, Transfer, RecurringTransaction.

### Preferences (Read + Partial Write)

| Preference | Read | Write |
|-----------|------|-------|
| AccountingInfoPrefs (fiscal year, close date) | Yes | Partial |
| SalesFormsPrefs (invoice defaults) | Yes | Partial |
| VendorAndPurchasesPrefs | Yes | Partial |
| TaxPrefs | Yes | Limited (AST overrides in US) |
| TimeTrackingPrefs | Yes | Yes |
| CurrencyPrefs | Yes | Yes |
| EmailMessagesPrefs | Yes | Yes |
| ProductAndServicesPrefs | Yes | Yes |
| ReportPrefs | Yes | Yes |

### No API Support

Tags (create/update/delete), Bank Connections, Bank Rules, Projects (dedicated), Payroll, User Management, Reconciliation, Subscription Management, Bank Feed "For Review" items.

### API Economics (2025 Intuit App Partner Program)

| Tier | Monthly Cost | Notes |
|------|-------------|-------|
| Builder | Free | 500K CorePlus reads/month; unlimited Core writes |
| Silver | $300 | 1M CorePlus reads |
| Gold | $1,700 | 10M CorePlus reads |

**Setup operations are mostly writes (Core) = free and unlimited on all tiers.**

### App Type Recommendation

Use a **Private App** with scope `com.intuit.quickbooks.accounting`. No app review process needed. Same API access as listed apps. Ideal for CPA firms building tools for their own clients.

---

## Browser Automation Opportunities

### Full Assessment (20 Tasks)

| # | Task | Category | Security Risk | Value |
|---|------|----------|--------------|-------|
| 1 | Bank Connections (Plaid) | Browser-guided | HIGH | Medium |
| 2 | Bank Rules Creation | **Fully automatable** | LOW | Very High |
| 3 | User/Role Management | Browser-assisted | MEDIUM | Medium |
| 4 | Payroll Setup | Browser-guided | HIGH | Medium |
| 5 | Tags Creation | **Fully automatable** | LOW | Very High |
| 6 | Projects Setup | **Fully automatable** | LOW | Medium |
| 7 | Company Logo Upload | **Fully automatable** | LOW | Low |
| 8 | Invoice Template Customization | Browser-assisted | LOW | Medium |
| 9 | Sales Tax Setup | Browser-assisted | LOW | Medium |
| 10 | Bank Reconciliation | Browser-assisted | LOW | Very High |
| 11 | Subscription/Plan Changes | **Still requires human** | HIGH | N/A |
| 12 | Third-Party App OAuth | Browser-guided | HIGH | Medium |
| 13 | QB Payments KYC | **Still requires human** | HIGH | N/A |
| 14 | Closing Date/Password | **Fully automatable** | LOW | High |
| 15 | CSV Data Import | **Fully automatable** | LOW | Very High |
| 16 | CoA Template Application | **Fully automatable** | LOW | High |
| 17 | Custom Fields Setup | **Fully automatable** | LOW | Medium |
| 18 | Workflow Automation | Browser-assisted | LOW | Medium |
| 19 | Report Customization | Browser-assisted | LOW | Medium |
| 20 | Email Templates | Browser-assisted | LOW | Low |

### Security Boundaries for Browser Automation

**NEVER automate (agent must not touch):**
- Bank login credentials (Plaid or direct)
- Social Security Numbers / Tax IDs
- Bank account numbers for payroll/payments
- Credit card or payment information
- Government-issued ID uploads
- Account creation on behalf of users
- Subscription purchases or plan changes

**Automate only with explicit CPA approval:**
- Sending user invitations
- Applying CoA templates
- Running CSV imports
- Saving/sharing reports
- Clicking "Finish Now" on reconciliation

**Safe to fully automate:**
- Bank rules creation from specifications
- Tag and tag group creation
- Project creation
- Logo upload
- Closing date updates
- Custom field creation
- Template customization from specifications

---

## Irreversible Settings (Critical)

### Truly Irreversible

| Setting | Impact |
|---------|--------|
| **Multi-Currency** | Once enabled, cannot be disabled. Permanently loses: Insights dashboard, Income Tracker, Bill Tracker, batch invoicing. Only fix: create new QBO file. |
| **Customer/Vendor currency** | Locked after first transaction in that currency |
| **Inventory method** | QBO Online is FIFO only. No switching. |
| **Home currency** | Cannot change once multi-currency is enabled |

### Difficult to Change

| Setting | Notes |
|---------|-------|
| Company Type / Tax Form | Switching nonprofit <-> for-profit breaks CoA |
| Fiscal Year | Affects all historical reporting; confusing after data exists |
| Accounting Method | Toggling after transactions changes all historical reports |
| Account Types | Cannot change type after creation; must create new + reclassify |
| Opening Balances | Incorrect entries compound over time |

### Agent Guardrails for Irreversible Settings

- NEVER enable multi-currency without explicit per-item confirmation + CPA sign-off
- ALWAYS warn before any irreversible operation
- ALWAYS snapshot current config before making changes
- Require separate confirmation for tax code creation (cannot delete via API)

---

## Agent-Driven Setup Flow (Proposed)

```
Phase 0: Pre-requisites (HUMAN)
  - Create Intuit account + subscribe
  - Complete OAuth connection to QBO Copilot
  - Enter EIN

Phase 1: Business Profile Gathering (AGENT via Slack conversation)
  - 5-20 questions based on complexity tier
  - Industry classification
  - Feature needs assessment
  - External systems inventory

Phase 2: Intelligent Defaults (AGENT computation)
  - Select industry template
  - Customize CoA based on profile
  - Assemble preferences configuration
  - Generate complete setup plan

Phase 3: Plan Review (HUMAN reviews, AGENT presents)
  - Block Kit card with full plan summary
  - [Approve] [Show Details] [Revise] buttons
  - CPA confirms accounting method + fiscal year here

Phase 4: API-Driven Configuration (AGENT executes)
  - Batch create accounts (CoA)
  - Create customers/vendors/items
  - Update preferences
  - Create payment terms, classes, departments
  - Progress bar in Slack

Phase 5: Browser-Driven Configuration (AGENT executes)
  - Create bank rules from specifications
  - Create tags and tag groups
  - Import CSV data (if applicable)
  - Set closing date
  - Apply CoA template (if using QBO Accountant)
  - Upload company logo
  - Configure custom fields

Phase 6: Guided Human Steps (AGENT guides, HUMAN acts)
  - Connect bank accounts (step-by-step instructions with URLs)
  - Invite team members
  - Set up payroll (if applicable)
  - Connect third-party apps
  - Agent detects completion and advances automatically

Phase 7: Verification (AGENT executes)
  - CoA completeness check
  - Preferences verification
  - Test transaction (create + void)
  - Bank feed connection check
  - Report generation test

Phase 8: Data Migration (AGENT executes, CPA reviews)
  - Source identification (Desktop, spreadsheet, other cloud, fresh start)
  - Export guidance for source system
  - CSV import via browser automation
  - Balance reconciliation
```

### Complexity-Based Question Flow

**Simple tier** (5-8 questions):
1. What's your business name?
2. What do you do? (free text -> agent classifies industry)
3. Are you a sole proprietor, LLC, or corporation?
4. Do you sell products, services, or both?
5. Do you collect sales tax?
6. How many bank accounts do you have?
7. Are you migrating from another system?

**Moderate tier** adds:
8. How many employees do you have?
9. Do you need to track inventory?
10. Which states do you operate in?
11. Do you need to track by department/project/location?
12. What's your approximate annual revenue?
13. What payroll provider do you use (if any)?
14. What payment processor do you use?

**Complex tier** adds:
15. Do you have international transactions (multi-currency)?
16. How many entities/companies?
17. Do you need job costing?
18. What e-commerce platforms do you use?
19. Do you need custom approval workflows?
20. What are your reporting requirements?

---

## Industry Templates

Templates are data structures containing CoA accounts, items, features, and preferences specific to an industry. The agent selects and customizes templates based on the profile gathered in Phase 1.

### Supported Industries (Initial Set)

| Industry | Key CoA Features | Special Needs |
|----------|-----------------|---------------|
| Construction | WIP, Retainage, Job Costing accounts | Classes for projects, subcontractor tracking |
| Professional Services | Consulting revenue, retainers | Project tracking, time billing |
| Restaurant/Food Service | Food/Beverage COGS split | Inventory, POS integration, tip tracking |
| E-Commerce/Retail | Product sales, shipping, marketplace fees | Inventory, multi-channel classes |
| Real Estate | Commission, rental income, property maintenance | Classes for properties |
| Healthcare | Patient revenue, medical supplies | HIPAA considerations, insurance billing |
| SaaS/Technology | Subscription revenue, hosting costs | MRR/ARR tracking, deferred revenue |
| Nonprofit | Grants, program expenses, fund classes | Form 990 settings, donor tracking |
| General Business | Standard income/expense categories | Fallback template |

### Template Structure

Each template defines:
- **Accounts to create**: Name, AccountType, AccountSubType, Description
- **Default accounts to deactivate**: QBO auto-creates accounts not needed for the industry
- **Items to create**: Products/services typical for the industry
- **Features to enable**: Classes, locations, projects, inventory
- **Accounting method recommendation**: Cash or accrual with reasoning
- **Bank rule patterns**: Common categorization rules for the industry

Templates can be extended via configuration files without code changes.

---

## Implementation Architecture

### System Architecture

```
Slack (Bot/Shortcuts/Modals)
  |
  v
Agent (Claude LLM + Setup Skill Context)
  |
  +---> Tool Functions ---> QBO REST API (CRUD, bulk, preferences)
  |
  +---> Browser Agent  ---> QBO Web UI (rules, tags, import, closing date)
  |
  +---> SQLite         ---> Setup State, Operations Log, Conversation History
```

### Integration with Existing Codebase

The setup skill extends the existing architecture:

- **`qbo/client.py`** -- Add 8 new methods: `get_company_info`, `get_preferences`, `update_preferences`, `create_account`, `deactivate_account`, `create_item`, `create_term`, `update_company_info`
- **`agent/tools/qbo_tools.py`** -- Add 12 new tools for setup operations
- **`agent/skills/setup_skill.py`** (NEW) -- SetupSkill orchestrator with dynamic system prompt injection per phase
- **`agent/skills/setup_templates.py`** (NEW) -- Industry template data structures
- **`agent/skills/setup_models.py`** (NEW) -- SetupProfile, SetupPlan dataclasses
- **`qbo_copilot/data/migrations/003_setup_state.sql`** (NEW) -- Schema for setup state tracking
- **`qbo_copilot/data/setup_db.py`** (NEW) -- Setup-specific DB operations
- **`qbo_copilot/onboarding/state_machine.py`** -- Extend Phase 2 completion checks
- **`integrations/slack/bot.py`** -- Add `_register_setup_handlers()`
- **`integrations/slack/blocks.py`** -- Add setup plan Block Kit builders

### Key Design Decisions

1. **Sub-state-machine within Phase 2** rather than new top-level phases. Preserves existing 7-phase onboarding flow.
2. **Dynamic system prompt injection** rather than separate agent instances. Keeps architecture simple.
3. **Plan-then-execute with explicit approval**. No QBO write operations without human review.
4. **Industry templates as data, not code**. Extensible without changing execution engine.
5. **SQLite state persistence** using existing OnboardingDB pattern. Survives across sessions/restarts.
6. **Background execution with progress reporting** using existing `threading.Thread(daemon=True)` pattern.
7. **Snapshot-before-change rollback**. QBO's API has no transactions; we capture before-state.
8. **Hybrid API + browser** approach. API for supported CRUD; browser for everything else.

---

## Database Schema

New migration: `qbo_copilot/data/migrations/003_setup_state.sql`

```sql
-- Main setup state per client
CREATE TABLE IF NOT EXISTS setup_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL REFERENCES clients(id),
    setup_phase TEXT DEFAULT 'not_started',
    profile_json TEXT,
    plan_json TEXT,
    plan_approved BOOLEAN DEFAULT 0,
    plan_approved_at TEXT,
    plan_approved_by TEXT,
    config_snapshot_json TEXT,
    execution_log_json TEXT,
    human_steps_json TEXT,
    verification_json TEXT,
    migration_source TEXT,
    migration_status TEXT DEFAULT 'not_started',
    started_at TEXT,
    completed_at TEXT,
    started_by TEXT,
    last_interaction TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(client_id)
);

-- Individual setup operations (granular tracking + rollback)
CREATE TABLE IF NOT EXISTS setup_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL REFERENCES clients(id),
    operation_type TEXT NOT NULL,
    operation_payload TEXT,
    status TEXT DEFAULT 'pending',
    qbo_entity_id TEXT,
    qbo_entity_type TEXT,
    error_message TEXT,
    rollback_possible BOOLEAN DEFAULT 1,
    executed_at TEXT,
    rolled_back_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Conversation history (context preservation across sessions)
CREATE TABLE IF NOT EXISTS setup_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL REFERENCES clients(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    setup_phase TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

---

## New Tools Required

### Setup Lifecycle Tools

| Tool | Purpose |
|------|---------|
| `setup_save_profile` | Persist gathered profile data during conversation |
| `setup_get_profile` | Retrieve current profile for context |
| `setup_generate_plan` | Compute configuration plan from profile |
| `setup_get_plan` | Retrieve plan for review |
| `setup_execute_plan` | Execute approved plan (confirmation required) |
| `setup_run_verification` | Post-setup verification checks |
| `setup_get_human_steps` | List pending manual steps |

### New QBO API Tools

| Tool | Purpose |
|------|---------|
| `qbo_create_account` | Create Chart of Accounts entries |
| `qbo_update_preferences` | Set accounting method, fiscal year, features |
| `qbo_get_company_info` | Read company settings |
| `qbo_get_preferences` | Read current preferences |
| `qbo_create_item` | Create products/services |

### New Browser Automation Tools

| Tool | Purpose |
|------|---------|
| `qbo_browser_create_bank_rule` | Create bank categorization rule |
| `qbo_browser_create_tags` | Create tag groups and tags |
| `qbo_browser_import_csv` | Import data via QBO import wizard |
| `qbo_browser_set_closing_date` | Set/update closing date and password |
| `qbo_browser_apply_coa_template` | Apply CoA template from QBO Accountant |
| `qbo_browser_upload_logo` | Upload company logo |
| `qbo_browser_create_custom_fields` | Create custom fields (Advanced) |
| `qbo_browser_create_project` | Create projects |

---

## Security and Guardrails

### Agent-Level Rules

1. **NEVER execute write operations without showing the plan first and receiving explicit approval**
2. **ALWAYS snapshot current config before making changes**
3. **NEVER assume defaults for**: accounting method, fiscal year, sales tax settings
4. **NEVER handle via browser**: bank credentials, SSNs, payment info, government IDs
5. **For irreversible operations** (multi-currency, tax codes): require per-item confirmation separate from plan approval
6. **If any API call fails**: continue independent operations, report all failures at end
7. **Recommend CPA consultation** for: entity type selection, accounting method (large businesses), multi-state sales tax

### Rollback Strategy

- **Account creation**: Deactivate (soft delete)
- **Preference changes**: Restore from pre-change snapshot
- **Items**: Deactivate
- **Tax codes**: Cannot delete via API (design around this; warn before creation)
- **Bank rules (browser)**: Delete via browser automation
- **Tags (browser)**: Delete via browser automation

### Error Handling

- Each operation tracked individually in `setup_operations` table
- Partial completion is expected (not all operations depend on each other)
- Failed operations reported with specific remediation steps
- Agent can retry failed operations after root cause is addressed

---

## Implementation Roadmap

### Sprint 1: Foundation (1-2 weeks)
- [ ] Migration `003_setup_state.sql`
- [ ] `SetupDB` class
- [ ] New `QBOClient` methods (get/update preferences, create account, etc.)
- [ ] Basic `SetupSkill` class with state management
- [ ] `qbo_check_connection_status` tool

### Sprint 2: Profile Gathering (1-2 weeks)
- [ ] `setup_save_profile` and `setup_get_profile` tools
- [ ] Dynamic system prompt context for gathering phase
- [ ] `SetupProfile` data model
- [ ] Slack handlers for starting setup flow
- [ ] End-to-end conversation flow testing

### Sprint 3: Templates and Plan Generation (1-2 weeks)
- [ ] Industry templates for top 8 industries
- [ ] Template selection and customization logic
- [ ] `setup_generate_plan` tool
- [ ] Block Kit cards for plan presentation
- [ ] Approval/rejection Slack handlers

### Sprint 4: API Execution Engine (1-2 weeks)
- [ ] Remaining `QBOClient` methods
- [ ] `setup_execute_plan` with operation tracking
- [ ] Snapshot/rollback capability
- [ ] Progress reporting in Slack
- [ ] QBO sandbox testing

### Sprint 5: Browser Automation (2-3 weeks)
- [ ] Browser agent infrastructure (Playwright or Claude-in-Chrome integration)
- [ ] Bank rules creation tool
- [ ] Tags creation tool
- [ ] CSV import tool
- [ ] Closing date tool
- [ ] CoA template application tool

### Sprint 6: Human Steps and Verification (1 week)
- [ ] Guided human steps with completion detection
- [ ] Verification check suite
- [ ] Completion reporting and onboarding hand-off

### Sprint 7: Polish and Migration (1-2 weeks)
- [ ] Data migration flows (CSV import, Desktop export guidance)
- [ ] Additional industry templates (12-15 more)
- [ ] Error handling hardening
- [ ] Full integration testing
- [ ] Reconciliation assist via browser

---

## Common Setup Mistakes to Prevent

The agent should actively prevent these common errors:

1. **Wrong account types** -- Validate AccountType against AccountSubType before creation
2. **Incorrect opening balances** -- Verify Opening Balance Equity nets to zero
3. **Premature multi-currency** -- Always warn; never auto-enable
4. **Missing closing date** -- Set after initial setup is complete
5. **No bank rules** -- Create rules during setup, not as afterthought
6. **Unflagged 1099 vendors** -- Prompt for contractor classification during vendor setup
7. **Default CoA without customization** -- Always apply industry template, not generic defaults
8. **Missing bank reconciliation** -- Guide first reconciliation as part of setup verification

---

## References

- [Intuit Developer API Documentation](https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities)
- [QBO API Batch Operations](https://developer.intuit.com/app/developer/qbo/docs/learn/explore-the-quickbooks-online-api/batch)
- [Intuit App Partner Program (2025)](https://blogs.intuit.com/2025/05/15/introducing-the-intuit-app-partner-program/)
- [QBO Advanced Setup Checklist](https://quickbooks.intuit.com/online/advanced/customers/checklist/)
- [Industry-Specific Charts of Accounts](https://www.firmofthefuture.com/accounting/create-31-industry-specific-charts-of-accounts-in-quickbooks/)
- [QBO API Rate Limits](https://help.developer.intuit.com/s/article/API-call-limits-and-throttling)
- [QBO Custom Fields API (Dec 2025)](https://blogs.intuit.com/2025/12/01/custom-fields-api-extending-quickbooks-online-with-flexible-metadata/)
- [QBO Refresh Token Policy](https://blogs.intuit.com/2025/11/12/important-changes-to-refresh-token-policy/)
