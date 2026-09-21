# VulnIQ Knowledge

## Purpose

This file captures the finalized shared understanding of the VulnIQ MVP so implementation can proceed without re-deciding product fundamentals.

Last updated: 2026-08-08
Last updated: 2026-08-09

---

## Product Summary

VulnIQ is a Cyber Threat Intelligence SaaS product focused on personalized vulnerability intelligence.

The MVP goal is to:

- ingest public vulnerability intelligence on a daily schedule
- identify the most relevant vulnerabilities for each customer based on selected product tags
- prioritize those vulnerabilities using severity and exploitation signals
- generate AI-assisted summaries and remediation guidance
- send a daily personalized vulnerability digest by email

The MVP also includes a simple dashboard where users can:

- sign up and log in
- verify their email
- enable or disable daily digests
- select product tags from a controlled taxonomy
- view the latest sent digest

---

## Stack Direction

The finalized MVP stack is:

- Backend: Python Django
- Database: PostgreSQL
- Deployment model: small server-based application
- Email provider: Resend
- AI provider: Gemini API

Previous directions such as `Node.js`, `MongoDB Atlas`, `Cloudflare Workers`, and a fully serverless deployment are no longer the preferred MVP path.

Detailed implementation decision references:

- Django app breakdown: `plans/IMPLEMENTATION_01_DJANGO_APP_BREAKDOWN.md`
- Postgres schema: `plans/IMPLEMENTATION_02_POSTGRES_SCHEMA.md`
- Normalization and alias strategy: `plans/IMPLEMENTATION_03_NORMALIZATION_AND_ALIAS_STRATEGY.md`
- Digest generation flow: `plans/IMPLEMENTATION_04_DIGEST_GENERATION_FLOW.md`
- Admin panel capabilities: `plans/IMPLEMENTATION_05_ADMIN_PANEL_CAPABILITIES.md`
- Email and dashboard data shape: `plans/IMPLEMENTATION_06_EMAIL_AND_DASHBOARD_DATA_SHAPE.md`
- Job scheduling and runtime: `plans/IMPLEMENTATION_07_JOB_SCHEDULING_AND_RUNTIME.md`
- Indexes, constraints, and migration order: `plans/IMPLEMENTATION_08_INDEXES_CONSTRAINTS_AND_MIGRATION_ORDER.md`
- Gemini prompt design: `plans/IMPLEMENTATION_09_GEMINI_PROMPT_DESIGN.md`
- Email template contract: `plans/IMPLEMENTATION_10_EMAIL_TEMPLATE_CONTRACT.md`
- Coding execution plan: `plans/IMPLEMENTATION_11_EXECUTION_PLAN.md`
- Coding backlog and agent prompts: `plans/IMPLEMENTATION_12_CODING_BACKLOG_AND_AGENT_PROMPTS.md`

---

## Account Model

- One account equals one customer/company.
- MVP supports exactly one login per customer.
- There is no multi-user organization support in MVP.
- There is no billing or role system in MVP.
- A separate organization/customer model should still exist internally from the beginning.

---

## MVP Functional Flow

1. User signs up with email and password.
2. User verifies their email.
3. User logs in and selects product tags from a controlled flat list.
4. User explicitly enables daily vulnerability emails.
5. A daily ingestion and digest pipeline runs at `12:00 AM IST`.
6. VulnIQ pulls vulnerability data from public sources.
7. CVEs are normalized, enriched with external signals, and scored.
8. Relevant vulnerabilities are matched to users based on normalized product names.
9. AI enrichment runs only for vulnerabilities that are actual digest candidates.
10. A digest snapshot is generated and stored.
11. The user receives the daily ranked digest by email.
12. The latest digest is available in the dashboard.

---

## Data Sources

The MVP uses these public sources:

- NVD
- CISA KEV
- FIRST EPSS

### NVD

Used for:

- newly published CVEs
- modified CVEs
- CVE metadata
- CVSS data
- CPE-derived vendor and product data

### CISA KEV

Used for:

- whether a vulnerability is known to be actively exploited

### EPSS

Used for:

- probability of exploitation

---

## Digest Window Logic

The daily digest considers vulnerabilities from the last 24 hours based on:

- newly published CVEs
- modified CVEs

If a CVE appeared earlier and is modified later, it can appear again in a later digest.

Example:

- a CVE published yesterday can reappear today if its KEV status changes or if another relevant field changes

For MVP:

- all modified CVEs in the 24-hour window should be processed, even if the change is minor

---

## Matching Logic

### User Tag Model

- Users select from a broad controlled flat list.
- Tags are product-level tags only.
- The taxonomy is defined internally by the team.
- Taxonomy entries should still have internal categories for organization and future use.

Examples:

- PostgreSQL
- Apache HTTP Server
- Kubernetes
- Cisco IOS XE

### Taxonomy Management

- Taxonomy is DB-managed.
- Tags and aliases should be managed through admin or internal tooling.
- Initial seed data is allowed, but taxonomy should not be code-only.

### CVE Matching Rule

- Vendor and product are extracted from CPE data.
- Product names are normalized.
- Aliases should exist for normalization and matching quality.
- One CVE can map to multiple normalized products.
- Matching is based on normalized product names against user-selected product tags.

### Internal Storage

- Even though users only select product tags, vendor information should still be stored internally for normalization, debugging, and support use.

### Version Handling

The MVP is not version-strict for matching.

Example:

- if a CVE affects `PostgreSQL 13`
- and the user selected `PostgreSQL`
- the user should still receive that vulnerability

This is intentionally broad for MVP coverage.

---

## Prioritization Logic

The fixed scoring formula for MVP is:

`Priority Score = (CVSS Base * 0.4) + (EPSS Probability * 10 * 0.3) + (CISA KEV Status * 3.0)`

This formula should remain fixed for MVP and not be made admin-tunable yet.

### Broad Threat Backfill

If a user has fewer than 10 relevant vulnerabilities for the day:

- fill the remaining slots using broadly important global threats
- do not use arbitrary unrelated noise

Broad threat criteria for MVP:

- `KEV = true`
- or `EPSS >= 0.7`
- or `CVSS >= 9.0`

Digest selection behavior:

- relevant matched vulnerabilities come first
- ranked by priority score
- up to 10 total items
- backfill only when needed
- backfill items should be clearly labeled as global/high-priority rather than directly matched

If enough eligible backfill exists, the digest should still reach 10 items.

If no vulnerabilities match the selected customer stack for a given day:

- still send a digest if eligible broad global threats exist
- use global top threats as the digest content
- include explanatory messaging that no stack-matched vulnerabilities were found

---

## AI Enrichment Rules

AI enrichment does not run for every ingested CVE.

It runs only after filtering, for vulnerabilities that are actual digest candidates.

### AI Output Types

1. Risk summary
2. Remediation guidance

### Provider

- Gemini API is the initial enrichment provider

### Prompt Rules

- risk summary should be at most two sentences
- remediation should be short technical guidance plus commands/config examples when appropriate
- summary prose does not need to mention CVE ID because CVE ID is shown separately in user-facing metadata
- if remediation confidence is low, use conservative generic guidance rather than inventing specific commands
- store explicit prompt version information with enrichment records

### Risk Summary Style

- concise
- operationally clear
- business-friendly

### Remediation Style

The preferred output format is:

- a short technical guidance line
- followed by commands or configuration examples when applicable

It should not be command-only with no context.

### Failure Behavior

- If AI enrichment fails for a candidate CVE, deterministic fallback text should be used.
- AI failure should not block a digest from being sent.
- AI enrichment should not be blindly rerun for every score-only change unless the enrichment input materially changed.

---

## Email Delivery Behavior

### Schedule

- Daily at `12:00 AM IST`

### Provider

- Resend

### Recipient Model

- One login email per customer for MVP

### Default State

- Email delivery is not enabled automatically after signup or verification
- User must enable it explicitly in the dashboard

### Email Format

- HTML email with text fallback

### Email Contract

- use light branding and a professional plain layout
- show CVE ID explicitly
- show source links such as NVD links
- include unsubscribe-style wording that maps to disabling digests in settings
- if fewer than 10 total items exist even after backfill, send fewer items rather than padding content

### Retry Behavior

- If a send fails, retry automatically the same day
- retry against the same immutable digest snapshot
- do not rebuild a fresh digest during resend attempts

---

## Authentication Model

The MVP uses Django-based application auth.

In-scope auth features:

- email + password signup
- secure password hashing
- session cookies
- email verification
- password reset

Authentication behavior:

- users can log in before email verification
- unverified users cannot enable daily digests
- session lifetime should be fixed at 30 days
- password policy should be a strong minimum, without enterprise-complex composition requirements

### Verification Token Behavior

- expired verification links remain invalid
- user must request a fresh verification email

Important note:

Although earlier discussion used the phrase "custom auth", the current stack is Django. In practice, Django's built-in auth, password hashing, and session primitives should be used instead of inventing security logic from scratch.

---

## Dashboard Scope

The dashboard is intentionally minimal for MVP.

It should allow users to:

- manage login/account basics
- view email verification status
- enable or disable daily emails
- choose product tags from the taxonomy
- view the latest sent digest
- see the latest digest send time if available

The dashboard should show only the latest digest in MVP.

Digest history should still be stored in the database for internal use, but does not need to be shown to users initially.

The core user-facing product remains the daily email digest.

User-facing digest rendering rules:

- email and dashboard should render from the same stored digest snapshot
- show CVE ID explicitly
- do not show internal composite priority score to users
- use one contextual date label per item such as `Published` or `Updated`
- do not show per-item internal selection reasons
- allow a digest-level note when no stack-matched vulnerabilities were found and global threats are shown instead

---

## Admin Scope

An internal admin panel is in scope for MVP.

Admin capabilities should be operational, not full editorial control.

Use one internal admin access level for MVP.

There is no need for a multi-role admin permission system or a separate custom internal admin application.

Django admin should be the internal operational interface.

Admins should be able to:

- inspect users and organizations
- inspect verification state
- inspect tag selections and taxonomy data
- inspect vulnerabilities, scores, products, enrichments, and raw source payloads
- inspect ingestion runs and degraded runs
- inspect digest records and send status
- trigger support-oriented actions such as resend or disabling digest workflows when needed
- manually trigger ingestion runs with logging
- manually trigger AI regeneration for a specific vulnerability

Admins should not manually edit vulnerability intelligence content as a normal MVP workflow.

---

## Data Model Direction

The planned core tables/models are:

- organizations
- users
- email_verification_tokens
- tech_tags
- tech_tag_aliases
- user_tech_tags
- vulnerabilities
- vulnerability_products
- vulnerability_ai_enrichments
- daily_digests
- daily_digest_items
- ingestion_runs

Potential supporting delivery records may also exist if needed for send attempt tracking.

Model rules:

- vulnerabilities are global, not tenant-scoped
- store both normalized fields and raw source JSON
- digest snapshots should be immutable once created for a send date
- send/retry history should be retained

Important index and constraint direction:

- enforce uniqueness on business identifiers such as organization slug, user email, CVE ID, digest date per organization, and latest-only enrichment ownership
- add indexes for vulnerability scoring, product normalization lookups, digest status, and ingestion-run tracking

---

## Ingestion and Delivery Pipeline

The intended daily pipeline is:

1. Pull NVD CVEs published or modified in the prior 24 hours.
2. Upsert CVEs by CVE ID.
3. Pull CISA KEV data and attach active exploitation signals.
4. Pull EPSS data and attach exploitation probability.
5. Extract vendor and product data from CPEs.
6. Normalize products and map them to canonical product tags.
7. Compute the fixed priority score.
8. Select digest candidates for each user.
9. Run AI enrichment only for candidate CVEs.
10. Persist digest snapshots.
11. Send emails through Resend.
12. Persist run and send outcomes.

### Source Failure Behavior

- If one external source such as KEV or EPSS is unavailable, proceed with partial data
- mark the run as degraded
- surface that degraded state in admin

### Runtime Strategy

- use one Django management command as the canonical daily pipeline entrypoint
- trigger it from an external scheduler at `12:00 AM IST`
- use a DB-backed lock to prevent overlapping runs
- use the same pipeline path for scheduler, CLI, and admin-triggered runs
- historical backfills should be CLI-only

### Delivery Tracking Interpretation

- treat provider acceptance from Resend as sent for MVP
- do not integrate provider webhooks in MVP

---

## Current Repository Status

As of 2026-08-08:

- the project is only just started
- only the ingestion part has been started

Existing code observations from the current repo state:

- there is an early Node-based ingestion script under `server/services/ingest.js`
- it currently fetches NVD CVEs from the last 24 hours
- KEV, EPSS, normalization, scoring, AI enrichment, persistence, auth, dashboard, and email delivery are not implemented yet
- the old Node code should be treated as exploratory or transitional now that the preferred stack is Django + Postgres

---

## Remaining Implementation Decisions

The major product and implementation-shaping decisions are finalized.

What remains is execution during coding, not unresolved product direction.

The agreed execution strategy is documented in:

- `plans/IMPLEMENTATION_11_EXECUTION_PLAN.md`

---

## Practical Interpretation

VulnIQ MVP should be built as:

- a Django application
- backed by PostgreSQL
- with Django-native auth/session primitives
- with a scheduled ingestion and digest pipeline
- focused on one daily email digest as the core product output
- with a minimal settings-oriented dashboard
- with an operational admin panel
- using normalized product-tag matching, fixed scoring, selective AI enrichment, and immutable digest snapshots

This document must be updated whenever a final product decision changes or when a new final decision deviates from prior assumptions.
