# Implementation Decision 02: Postgres Schema

## Purpose

This file captures the finalized Postgres schema direction for the VulnIQ MVP.

Decision date: 2026-08-08

---

## Summary

The VulnIQ MVP uses a relational schema centered around:

- customer ownership through `organizations`
- global vulnerability intelligence records
- controlled product taxonomy and alias mapping
- immutable daily digest snapshots
- explicit ingestion and delivery run tracking

The schema is intentionally designed to support the MVP cleanly while avoiding early rework in ownership, normalization, and digest history.

---

## Core Tables

### Accounts

- `organizations`
- `users`
- `email_verification_tokens`

### Taxonomy

- `tech_tags`
- `tech_tag_aliases`
- `user_tech_tags`

### Intel

- `vulnerabilities`
- `vulnerability_products`
- `vulnerability_ai_enrichments`

### Digests

- `daily_digests`
- `daily_digest_items`
- `email_send_attempts`

### Ingestion

- `ingestion_runs`

---

## Table-Level Decisions

### `organizations`

Purpose:

- represents one customer/company
- owns customer-level settings and digest behavior

Planned fields:

- `id`
- `name`
- `slug`
- `digest_enabled`
- `created_at`
- `updated_at`

Notes:

- MVP supports one organization per customer and one login per organization
- digest enablement belongs here, not on the user row

### `users`

Purpose:

- represents the single login for an organization in MVP

Planned fields:

- `id`
- `organization_id`
- `email`
- `password_hash`
- `is_email_verified`
- `last_login_at`
- `created_at`
- `updated_at`

Final decision:

- do not include `full_name` in MVP

### `email_verification_tokens`

Purpose:

- tracks email verification links securely

Planned fields:

- `id`
- `user_id`
- `token_hash`
- `expires_at`
- `used_at`
- `created_at`

Final decisions:

- store token hash, not raw token
- if a new verification token is issued, older unused tokens should be invalidated
- expired or used tokens must not work

### `tech_tags`

Purpose:

- canonical product taxonomy used for user selection and CVE matching

Planned fields:

- `id`
- `name`
- `slug`
- `category`
- `is_active`
- `created_at`
- `updated_at`

Final decision:

- `category` is required in MVP

### `tech_tag_aliases`

Purpose:

- alias and normalization support for mapping raw source names to canonical tags

Planned fields:

- `id`
- `tech_tag_id`
- `alias`
- `normalized_alias`
- `created_at`

Final decision:

- `normalized_alias` should be globally unique

### `user_tech_tags`

Purpose:

- organization-to-tag selection mapping

Planned fields:

- `id`
- `organization_id`
- `tech_tag_id`
- `created_at`

Constraint:

- unique on `(organization_id, tech_tag_id)`

### `vulnerabilities`

Purpose:

- global vulnerability intelligence records reused across all customers

Planned fields:

- `id`
- `cve_id`
- `title`
- `description`
- `status`
- `cvss_score`
- `epss_score`
- `is_cisa_kev`
- `priority_score`
- `published_at`
- `last_modified_at`
- `last_seen_in_feed_at`
- `nvd_raw_json`
- `kev_raw_json`
- `epss_raw_json`
- `created_at`
- `updated_at`

Final decisions:

- use one primary `cvss_score` field in MVP
- keep an explicit `status` field
- raw source JSON should still be preserved for traceability

### `vulnerability_products`

Purpose:

- stores product mappings extracted from source CPE data

Planned fields:

- `id`
- `vulnerability_id`
- `raw_vendor`
- `raw_product`
- `normalized_vendor`
- `normalized_product`
- `tech_tag_id`
- `source_cpe`
- `created_at`

Final decisions:

- store both raw and normalized vendor/product values
- keep source CPE for debugging and traceability
- allow one CVE to map to multiple products

### `vulnerability_ai_enrichments`

Purpose:

- stores generated summary and remediation content for a vulnerability

Planned fields:

- `id`
- `vulnerability_id`
- `provider`
- `model_name`
- `prompt_version`
- `input_hash`
- `summary_text`
- `remediation_text`
- `status`
- `error_message`
- `generated_at`
- `created_at`
- `updated_at`

Final decision:

- keep only the latest enrichment row per vulnerability in MVP

### `daily_digests`

Purpose:

- represents one immutable digest snapshot for one organization and one business date

Planned fields:

- `id`
- `organization_id`
- `digest_date`
- `status`
- `sent_at`
- `generation_started_at`
- `generation_completed_at`
- `created_at`
- `updated_at`

Final decisions:

- `digest_date` represents the business date in IST
- unique on `(organization_id, digest_date)`

### `daily_digest_items`

Purpose:

- stores the exact vulnerability items included in a digest snapshot

Planned fields:

- `id`
- `daily_digest_id`
- `vulnerability_id`
- `rank`
- `is_backfill`
- `match_reason`
- `matched_tech_tag_id`
- `matched_product_name_snapshot`
- `snapshot_title`
- `snapshot_summary`
- `snapshot_remediation`
- `snapshot_cvss_score`
- `snapshot_epss_score`
- `snapshot_is_cisa_kev`
- `snapshot_priority_score`
- `created_at`

Final decisions:

- include `matched_product_name_snapshot`
- store snapshot fields so historical digests do not change when source vulnerability records later change

### `email_send_attempts`

Purpose:

- tracks each send/retry attempt separately

Planned fields:

- `id`
- `daily_digest_id`
- `attempt_number`
- `provider`
- `provider_message_id`
- `status`
- `error_message`
- `attempted_at`

Constraint:

- unique on `(daily_digest_id, attempt_number)`

### `ingestion_runs`

Purpose:

- tracks operational execution of the daily pipeline

Planned fields:

- `id`
- `run_type`
- `status`
- `started_at`
- `completed_at`
- `is_degraded`
- `degraded_reason`
- `nvd_count`
- `kev_count`
- `epss_count`
- `candidate_count`
- `digest_count`
- `error_message`
- `created_at`

---

## Cross-Cutting Rules

- vulnerability data is global, not tenant-scoped
- organizations own tag selections and digest settings
- digests are immutable snapshots
- digest retry attempts reuse the same digest snapshot
- source raw payloads are retained alongside normalized fields
- normalization traceability is required for debugging and support

---

## Practical Interpretation

When implementation begins:

- create schema ownership according to the five Django apps already defined
- keep customer-level state on `organizations`
- keep digest history durable and auditable
- keep vulnerability normalization inspectable through raw and normalized fields

This schema is the implementation baseline for the MVP unless later product decisions explicitly change it.
