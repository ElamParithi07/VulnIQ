# Implementation 12: Coding Backlog and Agent Prompts

## Purpose

This document turns the execution strategy into a coding-ready backlog.

It defines:

- milestone order
- exact module ownership
- expected files per module
- test expectations per module
- sub-agent prompts to use during implementation

This is an execution document, not a product decision document.

---

## Delivery Model

Implementation should run in milestone batches.

Rules:

1. no parallel agent fan-out before foundation is complete
2. no module merge without tests
3. no integration of unstable contracts
4. lead integrator owns final structure and cross-module consistency

---

## Milestone 0: Foundation

### Goal

Create the base Django project and shared development/testing infrastructure.

### Owned By

Lead integrator only.

### Scope

- create Django project
- create Django apps
- configure Postgres-ready settings
- configure env loading
- configure installed apps and middleware
- configure custom user model if needed from day one
- configure pytest
- configure test settings
- configure base templates/static structure
- create shared model mixins/utilities
- create common service/client layout

### Expected Files

- `manage.py`
- project package:
  - `config/__init__.py`
  - `config/settings.py` or settings package
  - `config/urls.py`
  - `config/wsgi.py`
  - `config/asgi.py`
- app packages:
  - `accounts/`
  - `taxonomy/`
  - `intel/`
  - `digests/`
  - `ingestion/`
- shared package if needed:
  - `common/`
- test config:
  - `pytest.ini`
  - `conftest.py`
  - test factories package if used
- dependency files:
  - `requirements.txt` or equivalent
  - `.env.example`

### Tests Required

- Django boots
- DB connection config loads
- test runner executes
- a smoke test passes

### Completion Gate

Foundation is complete only when later agents can code against stable app names, stable settings, and stable test conventions.

---

## Milestone 1: Core Schema Batch

This batch stabilizes models and migrations before deeper feature work.

### Module 1A: Accounts Schema and Auth Flows

#### Scope

- `Organization`
- `User`
- `EmailVerificationToken`
- signup/login/logout
- email verification
- password reset
- digest enablement restriction for unverified users

#### Expected Files

- `accounts/models.py`
- `accounts/admin.py`
- `accounts/forms.py` if used
- `accounts/views.py`
- `accounts/urls.py`
- `accounts/services/verification.py`
- `accounts/services/auth.py`
- `accounts/tests/`
- `accounts/migrations/`

#### Tests

- model constraints
- email uniqueness behavior
- token lifecycle
- verification gating
- password reset flow
- session auth behavior

### Module 1B: Taxonomy Schema and Management

#### Scope

- `TechTag`
- `TechTagAlias`
- `UserTechTag`
- tag admin
- seed command
- user tag selection persistence

#### Expected Files

- `taxonomy/models.py`
- `taxonomy/admin.py`
- `taxonomy/services/tags.py`
- `taxonomy/management/commands/seed_taxonomy.py`
- `taxonomy/tests/`
- `taxonomy/migrations/`

#### Tests

- alias uniqueness
- category required
- tag assignment
- seed idempotency

### Module 1C: Intel Domain Schema

#### Scope

- `Vulnerability`
- `VulnerabilityProduct`
- `VulnerabilityAIEnrichment`
- raw payload fields
- scoring fields
- normalization status fields

#### Expected Files

- `intel/models.py`
- `intel/admin.py`
- `intel/tests/`
- `intel/migrations/`

#### Tests

- CVE uniqueness
- product uniqueness rule
- latest-only enrichment rule
- score/status field behavior

### Module 1D: Digest and Run Tracking Schema

#### Scope

- `DailyDigest`
- `DailyDigestItem`
- `EmailSendAttempt`
- `IngestionRun`

#### Expected Files

- `digests/models.py`
- `digests/admin.py`
- `digests/tests/`
- `digests/migrations/`
- `ingestion/models.py`
- `ingestion/admin.py`
- `ingestion/tests/`
- `ingestion/migrations/`

#### Tests

- one digest per org per date
- rank uniqueness inside digest
- send attempt numbering
- degraded run/state persistence

### Batch Gate

Milestone 1 completes only when all schema migrations apply cleanly and the model test suite passes.

---

## Milestone 2: Source Ingestion and Matching Batch

### Module 2A: Source Clients

#### Scope

- NVD client
- KEV client
- EPSS client
- payload normalization per source

#### Expected Files

- `ingestion/clients/nvd.py`
- `ingestion/clients/kev.py`
- `ingestion/clients/epss.py`
- `ingestion/services/source_parsing.py`
- `ingestion/tests/test_clients_*.py`

#### Tests

- source parsing
- error handling
- degraded-source reporting behavior

### Module 2B: Ingestion Persistence Pipeline

#### Scope

- source fetch orchestration
- vulnerability upsert logic
- product extraction persistence
- run logging

#### Expected Files

- `ingestion/services/pipeline.py`
- `ingestion/services/upserts.py`
- `ingestion/services/runs.py`
- `ingestion/tests/test_pipeline.py`
- `ingestion/tests/test_upserts.py`

#### Tests

- CVE upsert behavior
- partial-source degraded run
- raw payload storage

### Module 2C: Normalization and Alias Matching

#### Scope

- CPE vendor/product extraction
- product normalization
- alias resolution
- canonical matching
- unmatched/ignored/ambiguous status handling

#### Expected Files

- `intel/services/cpe.py`
- `intel/services/normalization.py`
- `intel/services/matching.py`
- `intel/tests/test_normalization.py`
- `intel/tests/test_matching.py`

#### Tests

- alias match
- canonical fallback
- vendor repetition cleanup
- unmatched handling
- duplicate prevention

### Batch Gate

Milestone 2 completes only when an ingestion test can produce persisted vulnerabilities and matched product rows in the database using mocked source responses.

---

## Milestone 3: Selection and Snapshot Batch

### Module 3A: Scoring

#### Scope

- fixed priority formula
- supporting score helpers

#### Expected Files

- `intel/services/scoring.py`
- `intel/tests/test_scoring.py`

#### Tests

- formula correctness
- missing-data behavior

### Module 3B: Candidate Selection

#### Scope

- direct match lookup
- ranking
- backfill logic
- duplicate CVE suppression
- no-match note rule

#### Expected Files

- `digests/services/selection.py`
- `digests/tests/test_selection.py`

#### Tests

- matched-first ordering
- backfill fill-up behavior
- no-match scenario
- dedupe across multiple selected tags

### Module 3C: Digest Snapshot Builder

#### Scope

- build immutable daily digest snapshots
- persist items in ranked order
- latest digest retrieval

#### Expected Files

- `digests/services/snapshots.py`
- `digests/services/query.py`
- `digests/tests/test_snapshots.py`

#### Tests

- one snapshot per org/day
- item snapshot immutability
- latest digest retrieval

### Batch Gate

Milestone 3 completes only when a mocked daily run can select vulnerabilities and persist a full digest snapshot without email or AI dependencies.

---

## Milestone 4: AI and Delivery Batch

### Module 4A: AI Enrichment

#### Scope

- Gemini client wrapper
- prompt builder
- enrichment persistence/reuse
- deterministic fallback text

#### Expected Files

- `intel/clients/gemini.py`
- `intel/services/ai_prompts.py`
- `intel/services/enrichment.py`
- `intel/tests/test_ai_prompts.py`
- `intel/tests/test_enrichment.py`

#### Tests

- prompt output contract
- fallback behavior
- latest-only reuse behavior

### Module 4B: Email Rendering

#### Scope

- HTML template
- text template
- digest context builder

#### Expected Files

- `digests/services/email_context.py`
- `digests/templates/digests/email_digest.html`
- `digests/templates/digests/email_digest.txt`
- `digests/tests/test_email_rendering.py`

#### Tests

- required fields rendered
- no-match note rendered
- text fallback rendered

### Module 4C: Email Delivery and Retry

#### Scope

- Resend client wrapper
- send attempt persistence
- retry against same snapshot
- provider acceptance handling

#### Expected Files

- `digests/clients/resend.py`
- `digests/services/delivery.py`
- `digests/tests/test_delivery.py`

#### Tests

- send attempt creation
- retry numbering
- same-snapshot resend
- sent-state mapping

### Batch Gate

Milestone 4 completes only when a stored snapshot can be rendered into email content and a mocked provider send can update delivery state correctly.

---

## Milestone 5: User Surface and Operations Batch

### Module 5A: Dashboard

#### Scope

- signup/login pages if server-rendered here
- verification status
- digest enable/disable
- tag selection UI
- latest digest view

#### Expected Files

- `accounts/templates/...`
- `taxonomy/templates/...`
- `digests/templates/...`
- `accounts/views.py` additions
- `taxonomy/views.py`
- `digests/views.py`
- `accounts/urls.py`
- `taxonomy/urls.py`
- `digests/urls.py`
- app tests for views/forms

#### Tests

- auth protection
- verified-user restrictions
- settings persistence
- latest digest rendering

### Module 5B: Admin Operations

#### Scope

- admin registrations
- list filters/search
- support actions
- unmatched review flow

#### Expected Files

- `accounts/admin.py`
- `taxonomy/admin.py`
- `intel/admin.py`
- `digests/admin.py`
- `ingestion/admin.py`
- admin action helper services if needed
- admin tests

#### Tests

- action availability
- action result behavior
- permission protection

### Module 5C: Scheduler and Command Entry

#### Scope

- canonical management command
- DB-backed lock
- admin trigger reuse
- CLI-only backfill entry if included now

#### Expected Files

- `ingestion/management/commands/run_daily_pipeline.py`
- `ingestion/services/locking.py`
- `ingestion/tests/test_commands.py`
- `ingestion/tests/test_locking.py`

#### Tests

- overlap prevention
- command invokes canonical pipeline
- degraded run state persists

### Batch Gate

Milestone 5 completes only when an operator can run the full pipeline from command line and an authenticated user can manage tags/digest settings and view the latest digest.

---

## Milestone 6: End-to-End Hardening

### Scope

- integration cleanup
- fixture quality improvements
- end-to-end test coverage
- docs cleanup
- final manual smoke verification

### Expected Tests

- signup -> verify -> select tags -> enable digest
- ingestion -> matching -> scoring -> snapshot -> email send
- zero-direct-match -> global backfill note
- degraded KEV/EPSS source -> run marked degraded
- retry send path uses same digest snapshot

### Completion Gate

This milestone is complete only when the full system works through the intended MVP flow under test.

---

## Sub-Agent Prompt Templates

These prompts should be used when implementation begins.

### Lead Integrator Prompt

You are the lead integration agent for the VulnIQ Django MVP.

Your responsibilities:

- maintain architectural consistency
- own shared contracts and service boundaries
- review module outputs from other agents
- merge only tested modules
- resolve cross-module conflicts
- protect the snapshot, scoring, and auth contracts

Rules:

- do not change product decisions
- do not invent new behavior outside documented plans
- prefer clean service boundaries over tightly coupled views
- require tests before accepting module completion

Reference documents:

- `plans/VULNIQ_KNOWLEDGE.md`
- `plans/IMPLEMENTATION_11_EXECUTION_PLAN.md`
- `plans/IMPLEMENTATION_12_CODING_BACKLOG_AND_AGENT_PROMPTS.md`

### Module Agent Prompt

You are responsible for one VulnIQ module in the Django MVP.

Your task:

- implement only the assigned module
- follow existing project structure and contracts
- add or update tests for all added behavior
- avoid unrelated refactors
- return a short note of assumptions and integration touchpoints

Rules:

- do not change product behavior
- do not rename shared models or fields unless required by the current codebase and clearly justified
- do not depend on live external services in tests
- keep module boundaries clean

Before coding:

- read `plans/VULNIQ_KNOWLEDGE.md`
- read `plans/IMPLEMENTATION_11_EXECUTION_PLAN.md`
- read this backlog document
- read only the app files relevant to your assigned module

Output expectation:

- implementation
- tests
- short assumptions note
- short integration note

### Accounts Agent Prompt

Implement the `accounts` module for VulnIQ in Django.

Scope:

- `Organization`, `User`, `EmailVerificationToken`
- signup/login/logout
- email verification flow
- password reset flow
- verified-user requirement for enabling digests

Required:

- migrations
- model tests
- auth/flow tests
- no live email provider dependency in tests

### Taxonomy Agent Prompt

Implement the `taxonomy` module for VulnIQ in Django.

Scope:

- `TechTag`, `TechTagAlias`, `UserTechTag`
- taxonomy admin
- taxonomy seed command
- persistence for customer tag selections

Required:

- migrations
- model tests
- seed command tests
- alias matching assumptions must align with documented normalization strategy

### Intel Schema Agent Prompt

Implement the core `intel` models for VulnIQ in Django.

Scope:

- `Vulnerability`
- `VulnerabilityProduct`
- `VulnerabilityAIEnrichment`
- constraints, indexes, raw payload storage, score/status fields

Required:

- migrations
- model tests
- admin registration if assigned in current batch

### Ingestion Agent Prompt

Implement the ingestion source clients and persistence pipeline for VulnIQ.

Scope:

- NVD client
- KEV client
- EPSS client
- ingestion orchestration
- ingestion run logging
- vulnerability upserts

Required:

- mocked tests only
- degraded-run behavior
- no digest generation logic in this module

### Matching Agent Prompt

Implement normalization and product matching for VulnIQ.

Scope:

- CPE vendor/product extraction
- normalization
- alias resolution
- canonical tag fallback
- unmatched/ignored/ambiguous status handling

Required:

- unit tests for normalization
- integration tests for DB-backed matching behavior
- no fuzzy matching

### Selection Agent Prompt

Implement vulnerability scoring and digest candidate selection for VulnIQ.

Scope:

- fixed priority score formula
- matched vulnerability ranking
- global backfill logic
- duplicate suppression
- no-match digest note rule

Required:

- unit tests for formula
- integration tests for candidate selection
- keep output compatible with digest snapshot builder

### Digest Agent Prompt

Implement digest snapshot generation for VulnIQ.

Scope:

- `DailyDigest` creation
- `DailyDigestItem` creation
- immutable snapshot persistence
- latest digest retrieval behavior

Required:

- model/service tests
- no email sending logic here
- snapshot contract must support both email and dashboard

### AI Agent Prompt

Implement AI enrichment for VulnIQ using Gemini.

Scope:

- prompt builder
- Gemini wrapper
- enrichment generation
- latest-only persistence/reuse
- deterministic fallback

Required:

- mocked tests only
- prompt output must align with documented AI contract

### Email Agent Prompt

Implement email rendering and delivery for VulnIQ.

Scope:

- digest email HTML and text templates
- context builder
- Resend wrapper
- delivery service
- retry behavior against same snapshot

Required:

- rendering tests
- mocked provider tests
- no rebuilding digest content during retries

### Dashboard Agent Prompt

Implement the user dashboard for VulnIQ.

Scope:

- verification state display
- digest enable/disable
- product tag selection
- latest digest page

Required:

- auth-protected view tests
- persistence tests
- render stored snapshot, not live vulnerability queries

### Admin Agent Prompt

Implement Django admin operations for VulnIQ.

Scope:

- admin registration across apps
- operational list/detail configuration
- support/admin actions
- unmatched product review support

Required:

- admin behavior tests where practical
- do not build a custom internal admin app

### Scheduler Agent Prompt

Implement pipeline command execution for VulnIQ.

Scope:

- canonical management command
- DB-backed overlap lock
- admin-triggerable same-path execution
- CLI backfill support if included in current batch

Required:

- command tests
- locking tests
- reuse canonical pipeline path

---

## Integrator Review Checklist

Before merging a module from a sub-agent, confirm:

1. scope matches assignment
2. no undocumented product behavior was added
3. migrations are sane
4. tests exist and are meaningful
5. module boundaries are respected
6. integration touchpoints are identified
7. naming matches established contracts

---

## Recommended Implementation Start Order

When coding begins, the practical order should be:

1. Milestone 0 by lead integrator
2. Milestone 1 parallel schema batch
3. Milestone 2 parallel ingestion/matching batch
4. Milestone 3 selection/snapshot batch
5. Milestone 4 AI/delivery batch
6. Milestone 5 dashboard/admin/scheduler batch
7. Milestone 6 hardening

This is the backlog that should drive implementation unless a new constraint emerges during coding.
