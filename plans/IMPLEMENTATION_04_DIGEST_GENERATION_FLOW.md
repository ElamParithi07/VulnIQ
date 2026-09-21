# Implementation Decision 04: Digest Generation Flow

## Purpose

This file captures the finalized daily digest generation flow for the VulnIQ MVP.

Decision date: 2026-08-09

---

## Summary

The daily digest should be generated through a deterministic nightly pipeline that:

- operates on the prior 24-hour vulnerability window
- builds one immutable digest snapshot per eligible organization per business date
- uses direct product matches first
- uses broad global backfill when needed
- sends from the stored snapshot, not live vulnerability records

---

## Eligibility Rules

A digest should be generated only for organizations where:

- `digest_enabled = true`
- a user exists for the organization
- the user email is verified

If an organization is not eligible, it should be skipped and reflected in run-level metrics.

---

## Daily Pipeline Flow

The intended daily process is:

1. Start the daily run at `12:00 AM IST`.
2. Pull NVD, KEV, and EPSS data for the prior 24-hour window.
3. Upsert and refresh vulnerability intelligence records.
4. Normalize products and recompute priority scores.
5. Determine the candidate vulnerability set for the day.
6. For each eligible organization:
   - find vulnerabilities matching selected `tech_tags`
   - rank matched CVEs by `priority_score` descending
   - take up to 10
   - if fewer than 10, backfill with broad global threats from the same window
   - if zero direct matches exist, still send a digest using backfill items if enough eligible backfill exists
7. Ensure AI enrichment exists for included CVEs.
8. Create immutable `daily_digests` and `daily_digest_items` snapshots.
9. Send the email through Resend.
10. Record send attempts and final delivery state.
11. Mark final digest and run status.

---

## No-Match Behavior

If an organization has no vulnerabilities matching its selected stack:

- still send a digest if broad global backfill items exist
- use up to 10 global items
- include explanatory copy indicating that no vulnerabilities were found for the selected stack and that the digest contains top global threats instead

This preserves daily product value even when the customer has no direct matches that day.

---

## Matching and Ranking Rules

### Direct matches

- direct product matches come first
- ranked by `priority_score` descending

### Backfill

- backfill is used only when direct matches are fewer than 10
- backfill comes from the same 24-hour window
- backfill must satisfy the agreed broad-threat criteria
- backfill is ordered by `priority_score` descending
- backfill items should be clearly labeled as global/high-priority

### Duplicate handling

If one CVE matches multiple selected tags for the same organization:

- include the CVE only once
- keep one resolved matched tag for storage/display
- preserve a sensible match reason for the snapshot

---

## AI Enrichment Timing

AI enrichment should happen during digest generation for included CVEs only.

Rules:

- do not run AI for every ingested CVE
- only generate enrichment for included digest candidates lacking usable current enrichment
- if AI generation fails, use deterministic fallback text

---

## Snapshot Rules

The digest snapshot is the source of truth for:

- outbound email content
- latest digest display in the dashboard

Rules:

- do not render user-facing digest content directly from live vulnerability rows
- freeze display fields into `daily_digest_items`
- keep snapshots immutable once created for that business date

This ensures historical digests do not change when vulnerability intelligence changes later.

---

## Failure and Retry Rules

### Organization-level failure

If one organization's digest generation fails after global ingestion succeeds:

- continue processing other organizations
- mark the failed organization's digest state accordingly

### Retry boundary

- automatic retries apply only to email sending
- retries must reuse the same immutable digest snapshot
- do not rebuild digest contents during resend attempts

---

## Practical Interpretation

When implementation begins:

- treat digest generation as a business-date pipeline, not ad hoc live rendering
- persist one digest snapshot per eligible organization per day
- send from stored snapshot content
- preserve customer value even on zero-match days by sending labeled global backfill content

This is the finalized digest generation baseline for the MVP.
