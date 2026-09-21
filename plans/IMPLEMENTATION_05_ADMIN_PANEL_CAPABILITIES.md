# Implementation Decision 05: Admin Panel Capabilities

## Purpose

This file captures the finalized internal admin scope for the VulnIQ MVP.

Decision date: 2026-08-09

---

## Summary

The MVP should use a single internal admin access level with Django admin as the operational interface.

This is not a multi-role admin permission system.

It is:

- one internal admin capability level
- one Django admin interface
- organized sections for the major operational data domains

The admin surface should be operationally useful, but intentionally constrained.

---

## Access Model

- use one internal admin access level for MVP
- no separate admin role hierarchy is needed
- no custom RBAC system is needed
- Django admin should be the internal admin surface

This keeps implementation simple while still giving the team the tools needed to operate the product.

---

## Admin Areas

The admin interface should be organized around these operational areas:

### Accounts

Admins should be able to inspect:

- organizations
- users
- email verification state
- digest enabled state
- last login
- latest digest status

### Taxonomy

Admins should be able to inspect and manage:

- canonical tech tags
- aliases
- internal categories
- active/inactive tag state
- unmatched product review entry points

### Intel

Admins should be able to inspect:

- vulnerabilities
- raw source payloads
- CVSS / EPSS / KEV / priority score
- extracted products
- normalization status
- linked `tech_tag`
- latest AI enrichment state and content

### Digests

Admins should be able to inspect:

- daily digests
- digest items
- send status
- send attempts
- latest sent timestamp
- whether a digest contains global backfill behavior

### Ingestion

Admins should be able to inspect:

- ingestion runs
- run status
- degraded flags
- source counts
- candidate counts
- digest counts
- error summaries

---

## Allowed Admin Actions

Admins should be able to:

- resend a digest email for an existing digest snapshot
- disable digest sending for an organization
- reissue a verification email
- add an alias from unmatched product review
- create a canonical tag from unmatched product review
- mark a product row as ignored when it is irrelevant or noisy
- edit customer-selected tags on behalf of a customer for support use
- manually trigger the daily ingestion pipeline with proper run logging
- manually trigger AI regeneration for a specific vulnerability

---

## Restricted Admin Actions

Admins should not use admin as a normal workflow for:

- manually rewriting vulnerability narrative content
- manually overriding priority scores
- manually rebuilding historical digest snapshots
- manually editing raw source payloads

This keeps operational control focused on safe support actions and input correction, not ad hoc modification of historical outputs or source truth.

---

## Additional Decisions

### Ingestion trigger

- admin may manually trigger the daily ingestion pipeline
- this must be logged like any other run

### AI regeneration

- admin may manually regenerate AI output for a specific vulnerability
- this should update the current enrichment record only
- it must not mutate historical digest snapshots

### Test digest sending

- no dedicated test-digest-to-internal-email workflow is needed in MVP

### Unmatched products queue

- admin should have a dedicated unmatched-products review view or equivalent filtered workflow

This is important because taxonomy quality is expected to improve iteratively after real source data is observed.

---

## Practical Interpretation

When implementation begins:

- use Django admin as the internal operational console
- do not build a custom internal admin app for MVP
- support one internal admin capability level
- focus admin actions on support, delivery, ingestion operations, and taxonomy correction

This is the finalized admin scope for the MVP.
