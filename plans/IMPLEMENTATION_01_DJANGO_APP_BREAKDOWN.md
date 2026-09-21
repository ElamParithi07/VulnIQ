# Implementation Decision 01: Django App Breakdown

## Purpose

This file captures the finalized Django app structure for the VulnIQ MVP.

Decision date: 2026-08-08

---

## Final Decision

Use these Django apps:

- `accounts`
- `taxonomy`
- `intel`
- `digests`
- `ingestion`

Do not create a separate `ops` app for MVP.

Operational/admin behavior should be handled through Django admin and app-local admin registrations inside the existing apps.

---

## Responsibilities

### `accounts`

Owns:

- organization/customer model
- user model or user-related account model behavior
- login-related account settings
- email verification state
- password reset flow integration
- digest enabled setting

Notes:

- One organization equals one customer/company.
- MVP supports exactly one login per customer.

### `taxonomy`

Owns:

- canonical tech/product tags
- tag aliases
- internal categories for tags
- user tag selections

Notes:

- User-facing selection is product-tag based.
- Categories are mainly internal for organization and future use.

### `intel`

Owns:

- vulnerability records
- raw source payload storage
- CVSS / KEV / EPSS fields on vulnerability intelligence
- normalized vulnerability fields
- extracted vulnerability-to-product mappings
- AI enrichment records

Notes:

- Vulnerability intelligence is global, not tenant-scoped.

### `digests`

Owns:

- daily digest snapshots
- digest items
- digest delivery status
- resend/retry tracking tied to the same snapshot
- latest digest retrieval behavior

Notes:

- Digests are immutable snapshots once created for a send date.

### `ingestion`

Owns:

- scheduled pipeline orchestration
- source fetchers/adapters for NVD, KEV, and EPSS
- ingestion run tracking
- degraded-run handling
- retry/orchestration logic for pipeline execution

Notes:

- `ingestion` is intentionally separate from `intel`.
- `intel` owns the data model.
- `ingestion` owns how data is fetched and processed.

---

## Why `ingestion` Is Separate

### Benefits

- clean separation between vulnerability data and pipeline execution
- easier future growth for backfills, reruns, retries, and source-specific jobs
- clearer ownership of scheduled jobs and run logging
- better maintainability once the ingestion pipeline becomes more complex

### Cost

- slightly more project structure up front
- a few more app boundaries and imports

This tradeoff is acceptable because ingestion is a core subsystem in VulnIQ, not a minor background task.

---

## Why There Is No Separate `ops` App

MVP does not need a dedicated `ops` Django app.

Reasoning:

- current admin/support needs can be handled through Django admin
- operational tooling can live in app-local admin registrations
- this avoids adding an extra app whose only purpose is grouping support behavior

If VulnIQ later needs custom internal dashboards, support workflows, or operator-only screens beyond Django admin, an `ops` app can be introduced later.

---

## Boundary Rules

- `accounts` owns customer/account state
- `taxonomy` owns tag definitions and selection
- `intel` owns global threat intelligence records
- `digests` owns customer-facing digest output records
- `ingestion` owns scheduled execution and source synchronization

Important rule:

- admin tooling must not become the real owner of core business data
- each model should be owned by one of the domain apps above

---

## Practical Interpretation

When coding starts:

- create these five Django apps first
- keep ingestion code out of `intel` except for calling into `intel` model/services APIs
- use Django admin registrations inside the owning apps rather than creating an `ops` app

This is the baseline project structure for the MVP.
