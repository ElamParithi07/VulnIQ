# Implementation Decision 08: Indexes, Constraints, and Migration Order

## Purpose

This file captures the finalized index, constraint, and migration-order decisions for the VulnIQ MVP.

Decision date: 2026-08-09

---

## Summary

The MVP schema should enforce strong uniqueness where business identity matters, use targeted performance indexes for the core query paths, and apply schema/data setup in a controlled order that avoids bootstrap confusion.

---

## Core Uniqueness and Constraint Rules

### `users`

- `email` should be unique with case-insensitive logical uniqueness

### `organizations`

- `slug` should be unique

### `tech_tags`

- canonical tag names should be unique at the normalized business-name level

### `vulnerabilities`

- `cve_id` should be unique

### `vulnerability_products`

- unique constraint on:
  - `(vulnerability_id, normalized_vendor, normalized_product, source_cpe)`

### `vulnerability_ai_enrichments`

- `vulnerability_id` should be unique because MVP keeps latest-only enrichment

### `daily_digest_items`

- unique constraint on:
  - `(daily_digest_id, rank)`

### `daily_digests`

- unique constraint on:
  - `(organization_id, digest_date)`

### `email_send_attempts`

- unique constraint on:
  - `(daily_digest_id, attempt_number)`

---

## Indexes

### `email_verification_tokens`

- index on `user_id`
- index on `expires_at`

### `email_send_attempts`

- index on `status`
- index on `attempted_at`

### `vulnerabilities`

- index on `priority_score`
- index on `is_cisa_kev`
- index on `last_modified_at`
- index on `published_at`
- index on `status`

### `vulnerability_products`

- index on `tech_tag_id`
- index on `normalized_product`
- index on `normalization_status`

### `daily_digests`

- index on `status`
- index on `sent_at`

### `ingestion_runs`

- index on `started_at`
- index on `status`
- index on `is_degraded`

---

## Migration Order

Apply schema in this order:

1. `accounts`
   - organizations
   - users
   - email verification tokens
2. `taxonomy`
   - tech tags
   - aliases
   - user tech tags
3. `intel`
   - vulnerabilities
   - vulnerability products
   - vulnerability AI enrichments
4. `digests`
   - daily digests
   - daily digest items
   - email send attempts
5. `ingestion`
   - ingestion runs

---

## Seed and Bootstrap Order

Recommended initial setup order:

1. create base schema
2. seed taxonomy categories and tags
3. add initial aliases
4. ingest vulnerability data
5. enable real users and digests

Final decision:

- taxonomy seed data should be loaded through a separate seed command, not embedded in migrations

---

## Practical Interpretation

When implementation begins:

- enforce uniqueness early to protect data quality
- add indexes for the known query paths now instead of waiting for production pain
- keep bootstrap data loading separate from schema migrations

This is the finalized schema-performance and migration-order baseline for the MVP.
