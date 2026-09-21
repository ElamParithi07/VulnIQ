# Implementation 11: Coding Execution Plan

## Purpose

This document defines how VulnIQ should be implemented module by module, how parallel coding agents should be used, how testing gates should work, and in what order modules should be integrated.

It does not change product behavior. It defines execution strategy.

---

## Delivery Principle

Implementation should follow this rule:

1. define shared foundations first
2. build independent modules in parallel where dependencies are stable
3. require tests for each module before it is considered complete
4. integrate modules in dependency order
5. run end-to-end validation before release

Parallelism should be used aggressively, but only after contracts are fixed enough that agents are not inventing incompatible code.

---

## High-Level Build Phases

### Phase 0: Foundation

Build the project skeleton and shared infrastructure first:

- Django project bootstrap
- app creation and settings split
- PostgreSQL connection and environment config
- base model mixins and timestamp conventions
- pytest setup
- factory/test-data setup
- local development commands

This phase is owned centrally and should not be parallelized heavily because every later module depends on it.

### Phase 1: Data and Core Domain

After the foundation is ready, build the domain models and migrations:

- `accounts`
- `taxonomy`
- `intel`
- `digests`
- `ingestion`

Model contracts, constraints, indexes, and admin registration should be implemented here.

### Phase 2: Independent Feature Modules

Once the DB schema is stable, multiple agents can work in parallel on:

- authentication and account flows
- taxonomy management and user tag selection
- ingestion connectors and normalization pipeline
- scoring and candidate selection
- AI enrichment
- email rendering and delivery
- dashboard views
- admin actions

### Phase 3: Integration

After module-level completion:

- connect ingestion to persistence
- connect matching to digest generation
- connect AI enrichment to digest items
- connect digest snapshots to email and dashboard rendering
- connect admin actions to pipeline entrypoints

### Phase 4: System Validation

Final validation should include:

- end-to-end pipeline run
- email generation assertions
- dashboard rendering assertions
- degraded-source behavior
- retry behavior
- auth and permission checks

---

## Module Breakdown

### Module A: Project Foundation

Scope:

- Django project bootstrap
- settings organization
- env loading
- PostgreSQL configuration
- installed apps
- base utilities
- pytest and test settings

Outputs:

- working Django project
- local boot instructions
- test runner working

Must finish before parallel agent work begins.

### Module B: Accounts

Scope:

- organization model
- user model wiring
- signup
- login/logout
- session behavior
- email verification
- password reset
- digest enablement guard for verified users only

Tests:

- signup success/failure
- password hashing/authentication
- verification token behavior
- unverified user blocked from enabling digests
- password reset token flow

### Module C: Taxonomy

Scope:

- `tech_tags`
- `tech_tag_aliases`
- `user_tech_tags`
- taxonomy admin
- seed command
- dashboard tag selection

Tests:

- unique normalized alias enforcement
- category required behavior
- tag assignment rules
- seed idempotency

### Module D: Vulnerability Intel Domain

Scope:

- `vulnerabilities`
- `vulnerability_products`
- `vulnerability_ai_enrichments`
- raw payload storage
- scoring fields
- normalization status fields

Tests:

- CVE uniqueness
- product row uniqueness
- status handling
- score persistence
- latest-only enrichment ownership

### Module E: Ingestion Connectors

Scope:

- NVD fetch client
- KEV fetch client
- EPSS fetch client
- ingestion run tracking
- degraded run behavior
- source parsing into normalized internal payloads

Tests:

- source response parsing
- pagination or batching logic if used
- degraded run marking when one source fails
- upsert behavior contract

### Module F: Normalization and Matching

Scope:

- vendor/product extraction from CPE
- normalization pipeline
- alias resolution
- canonical tag matching
- unmatched and ignored handling

Tests:

- exact alias match
- canonical name fallback
- vendor repetition cleanup
- unmatched status assignment
- duplicate prevention

### Module G: Scoring and Candidate Selection

Scope:

- fixed priority score calculation
- direct match selection
- ranking
- backfill logic
- no-match digest-note condition

Tests:

- score formula correctness
- matched items ranked first
- backfill only when needed
- zero-direct-match behavior
- duplicate CVE suppression across tags

### Module H: AI Enrichment

Scope:

- Gemini client wrapper
- prompt versioning
- summary generation
- remediation generation
- deterministic fallback text
- caching/reuse of latest enrichment

Tests:

- prompt contract formatting
- fallback on provider failure
- latest-only persistence behavior
- no regeneration when not needed

### Module I: Digest Snapshot Generation

Scope:

- `daily_digests`
- `daily_digest_items`
- immutable snapshot creation
- per-org digest assembly
- latest digest retrieval

Tests:

- one digest per org per day
- immutable item snapshot behavior
- stored note for no-stack-match case
- latest digest query behavior

### Module J: Email Delivery

Scope:

- email HTML/text rendering
- Resend client wrapper
- send attempt recording
- retry behavior against same snapshot
- provider-accepted-as-sent interpretation

Tests:

- template renders required fields
- text fallback output
- send-attempt persistence
- retry uses same digest snapshot

### Module K: Dashboard

Scope:

- authenticated pages
- verification state display
- digest enable/disable
- tag selection UI
- latest digest view
- send-time visibility

Tests:

- auth protection
- unverified restrictions
- settings persistence
- digest snapshot rendering

### Module L: Admin Operations

Scope:

- Django admin registration
- admin list/detail usability
- admin actions:
  - resend digest
  - disable org digests
  - reissue verification email
  - create alias/canonical tag support actions
  - ignore unmatched product
  - trigger full ingestion
  - trigger AI regeneration

Tests:

- action availability
- permission restrictions
- state transitions caused by actions

### Module M: Scheduler and Command Entry

Scope:

- canonical management command
- DB-backed run lock
- admin-triggered entrypoint reuse
- CLI historical backfill path

Tests:

- lock prevents overlap
- command invokes same pipeline path
- backfill command validation

---

## Parallel Agent Strategy

Use a lead integrator agent plus several module agents.

### Lead Integrator Agent

Responsibilities:

- create project foundation
- define coding conventions and shared contracts
- review output from module agents
- merge incompatible assumptions
- integrate completed modules
- run integration and end-to-end tests

The lead agent should own cross-module interfaces so individual agents do not drift.

### Parallel Module Agents

Recommended first parallel batch after foundation:

1. Agent 1: `accounts`
2. Agent 2: `taxonomy`
3. Agent 3: `intel` domain models
4. Agent 4: ingestion connectors

Recommended second batch:

1. Agent 5: normalization and matching
2. Agent 6: scoring and candidate selection
3. Agent 7: dashboard
4. Agent 8: admin operations

Recommended third batch:

1. Agent 9: AI enrichment
2. Agent 10: digest snapshot generation
3. Agent 11: email delivery
4. Agent 12: scheduler/management commands

Not all agents need to run at the same time if context quality drops. Parallelism should be limited by dependency maturity, not by ambition.

---

## Handoff Contract For Each Agent

Every agent working on a module should return:

1. code changes for the assigned module only
2. migrations if the module owns schema changes
3. tests for that module
4. a short note describing assumptions
5. a list of integration touchpoints with other modules

Each agent must avoid editing unrelated modules unless explicitly assigned shared integration work.

---

## Completion Criteria Per Module

A module is complete only when all of these are true:

1. code is implemented
2. tests for the module are written
3. module tests pass
4. lint/type checks pass for touched code
5. admin or API wiring for that module is connected where applicable
6. no unresolved contract ambiguity remains

A module is not considered done merely because the main code path exists.

---

## Testing Strategy

### Test Layers

Use three layers of tests:

1. unit tests
2. module/service integration tests
3. end-to-end workflow tests

### Unit Tests

Best for:

- normalization functions
- score calculation
- prompt builders
- token validation
- selection logic

### Module Integration Tests

Best for:

- model constraints
- ORM queries
- ingestion upserts
- digest assembly
- email send attempt persistence

### End-to-End Tests

Best for:

- signup to verified enablement
- ingestion to digest generation
- digest snapshot to email rendering
- no-match backfill scenario
- degraded source scenario

### External Service Testing

- mock Gemini
- mock Resend
- mock NVD, KEV, EPSS clients

No test should depend on live third-party APIs.

---

## Integration Order

Modules should be connected in this order:

1. Foundation
2. Core schema and migrations
3. Accounts
4. Taxonomy
5. Intel domain
6. Ingestion connectors
7. Normalization and matching
8. Scoring and candidate selection
9. Digest snapshot generation
10. AI enrichment
11. Email delivery
12. Dashboard
13. Admin actions
14. Scheduler/command entry
15. End-to-end hardening

Reason:

- schema-dependent work must stabilize early
- digest generation depends on matching and scoring
- email and dashboard both depend on snapshot contract
- admin and scheduler should trigger already-stable workflows

---

## Practical Build Sequence

### Step 1

Lead agent creates:

- Django project
- apps
- settings
- pytest
- base dependencies

### Step 2

Lead agent defines shared contracts:

- model naming
- service/module layout
- management command pattern
- testing conventions
- client wrapper boundaries for Gemini and Resend

### Step 3

Run first parallel batch:

- accounts
- taxonomy
- intel models
- ingestion clients

Require tests before merge.

### Step 4

Run second parallel batch:

- normalization/matching
- scoring/selection
- dashboard
- admin wiring

Require tests before merge.

### Step 5

Run third parallel batch:

- digest generation
- AI enrichment
- email delivery
- scheduler/commands

Require tests before merge.

### Step 6

Lead agent performs integration passes:

- connect pipeline services
- connect email rendering to snapshot
- connect dashboard to snapshot
- connect admin actions to service layer

### Step 7

Run final validation suite:

- module tests
- integration tests
- end-to-end tests

---

## Risks To Control During Parallel Coding

Main risks:

- different agents inventing conflicting model fields
- duplicate business logic across modules
- digest snapshot contract drift between email and dashboard
- ingestion and selection logic diverging from scoring contract
- missing test coverage on retry/degraded flows

Mitigations:

- foundation and schema first
- shared contracts written before agent fan-out
- strict module boundaries
- mandatory tests with each module
- lead integrator merges and verifies every batch

---

## Final Execution Rule

Coding should start only after the lead integrator defines the project skeleton and shared interfaces.

After that, module agents can run in parallel, but no module should be merged without tests. Integration happens in controlled batches, not as one large final merge.
