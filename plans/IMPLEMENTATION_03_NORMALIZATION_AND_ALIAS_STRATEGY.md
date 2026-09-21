# Implementation Decision 03: Normalization and Alias Strategy

## Purpose

This file captures the finalized normalization and alias strategy for the VulnIQ MVP.

Decision date: 2026-08-09

---

## Summary

The MVP should use deterministic, alias-driven matching from CPE-derived product data to canonical product tags.

The primary goal is:

- high-confidence matching
- controlled false positives
- admin-correctable taxonomy evolution

The MVP should not use fuzzy matching for automatic resolution.

---

## Core Principle

Normalization exists to map raw vulnerability source product names to canonical `tech_tags` safely.

The system should prefer:

- predictable matching
- explainable matching
- easy admin correction

over:

- aggressive auto-resolution
- similarity-based guessing

---

## Normalization Pipeline

For each CPE-derived vendor/product pair:

1. Extract `raw_vendor` and `raw_product`.
2. Lowercase values.
3. Trim whitespace.
4. Replace separators such as `_`, `-`, and `/` with spaces where appropriate.
5. Collapse repeated spaces.
6. Remove obvious vendor repetition from the product string when safe and deterministic.
7. Compare the normalized value against:
   - `tech_tag_aliases.normalized_alias`
   - canonical normalized tag name
8. If exactly one canonical match exists, link the product row to that `tech_tag`.
9. If no match exists, keep the normalized values and leave `tech_tag_id` unresolved.
10. If a match would be ambiguous, do not guess automatically.

---

## Matching Rules

### Matching precedence

1. Exact match on normalized alias
2. Exact match on normalized canonical tag name
3. Otherwise unresolved

### Fuzzy matching

Do not use fuzzy matching for automatic resolution in MVP.

Reasoning:

- fuzzy matching increases false positives
- silent bad matches reduce trust in the digest
- alias-driven correction is safer and easier to debug

Fuzzy suggestions may be added later as an admin aid, but should not drive automatic matching in MVP.

---

## Vendor Removal Rule

When the raw product string includes vendor words, normalization should attempt to remove vendor repetition before alias matching.

Example:

- raw vendor: `cisco`
- raw product: `cisco_ios_xe`
- normalized product may become `ios xe`

Rule:

- this should be done only with simple deterministic normalization
- do not apply aggressive heuristics that may distort legitimate product names

---

## Alias Rules

- aliases are stored in `tech_tag_aliases`
- `normalized_alias` is globally unique
- ambiguous alias ownership must be prevented at the database level

This ensures one normalized alias resolves to only one canonical product tag.

---

## Unmatched and Ambiguous Products

If a normalized product cannot be mapped safely:

- keep the `vulnerability_products` row
- store normalized values for inspection
- leave `tech_tag_id` unresolved
- mark the normalization result explicitly

If a product is unresolved, that CVE can still participate in global backfill logic.

Reason:

- backfill is based on global risk, not only taxonomy matching

---

## Admin Workflow

Admin must be able to:

- inspect unmatched normalized products
- create new aliases
- create entirely new canonical tags when needed

This allows taxonomy coverage to improve over time without code changes.

---

## Normalization Result Status

`vulnerability_products` should include a normalization result status.

Recommended statuses:

- `matched`
- `unmatched`
- `ambiguous`
- `ignored`

Purpose:

- easier debugging
- better admin review workflow
- clearer operational visibility into matching quality

---

## Practical Interpretation

When implementation begins:

- build deterministic normalization first
- resolve through exact alias/canonical matching only
- store unresolved products instead of guessing
- use admin-managed taxonomy and aliases to improve coverage iteratively

This strategy is the MVP baseline for product matching quality.
