# Implementation Decision 06: Email and Dashboard Data Shape

## Purpose

This file captures the finalized user-facing digest rendering shape for the VulnIQ MVP.

Decision date: 2026-08-09

---

## Summary

The email digest and the dashboard latest-digest page should render from the same stored digest snapshot.

The MVP should use:

- one snapshot source of truth
- one shared digest data contract
- two render surfaces:
  - email
  - latest digest page in the dashboard

This avoids drift between what users received by email and what they later see in the app.

---

## Core Rendering Principle

The dashboard should not recalculate or reassemble digest content from live vulnerability data.

Both email and dashboard should render from the immutable stored snapshot for that organization and business date.

This ensures:

- consistency
- historical accuracy
- simpler rendering behavior

---

## Digest-Level Display Shape

Each digest render should include:

- digest date
- organization name
- whether backfill items are present
- whether the digest is fully matched or includes global backfill content
- short intro text
- optional no-match message if global threats were used because no stack matches existed

---

## Digest Item Display Shape

Each digest item should include:

- rank
- title
- CVE ID
- one clean vendor/product display line
- label chips such as:
  - `Actively Exploited` when KEV is true
  - `High EPSS` when above threshold
  - `Critical` when severity is high
- `cvss_score`
- `epss_score`
- short AI risk summary
- short AI remediation block
- one contextual date label:
  - `Updated` when modified in the relevant window
  - otherwise `Published`
- indicator if the item is global backfill

Final display rule:

- do not show the internal composite `priority_score` to end users

---

## User-Facing Simplicity Rule

Users do not need to see an explicit explanation of why a vulnerability was selected.

Do not expose per-item rationale such as:

- `Matched: PostgreSQL`
- `Chosen because of your stack`
- `Global Threat Backfill`

The digest should remain simple and operationally useful rather than explanatory about internal selection logic.

The only exception is the digest-level no-match message:

- when there were no stack-matched vulnerabilities and the digest contains top global threats instead, the digest may say that at the overall digest level

That is acceptable because it explains the overall content shape without cluttering each item.

---

## Email Shape

The email should contain:

1. Header
   - VulnIQ branding
   - digest date
2. Intro text
   - normal case: tailored to the user's selected products
   - no-match case: no stack matches were found, so top global threats are included instead
3. List of up to 10 digest items
4. Footer
   - link to dashboard
   - note about why the user receives these emails in general
   - manage digest settings link or direction

### Email content style

- keep remediation concise inline
- keep summaries concise
- do not overload the email with extra metadata

---

## Dashboard Latest Digest Page

The dashboard latest-digest page should:

- show the same digest snapshot content that was emailed
- keep a slightly easier-to-scan layout than email
- avoid live recalculation
- allow source links where useful

### Source links

Including source links such as NVD links is acceptable and useful in MVP.

---

## Date Display Rule

Show one contextual date label per item rather than multiple raw timestamps.

Rule:

- if the item was modified in the relevant digest window, show `Updated`
- otherwise show `Published`

This keeps presentation simpler while still reflecting why an older CVE may reappear in a later digest.

---

## Practical Interpretation

When implementation begins:

- treat the digest snapshot as the only user-facing rendering source
- keep end-user display simple and compact
- show identifiers and operational signals
- hide internal scoring and selection reasoning
- allow digest-level explanation in no-match/global-threat days

This is the finalized user-facing digest data shape for the MVP.
