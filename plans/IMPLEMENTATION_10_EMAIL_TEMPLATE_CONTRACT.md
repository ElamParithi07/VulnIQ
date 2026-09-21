# Implementation Decision 10: Email Template Contract

## Purpose

This file captures the finalized email-template behavior and content contract for the VulnIQ MVP.

Decision date: 2026-08-09

---

## Summary

The daily digest email should be a professional, compact operational briefing rather than a marketing email.

It should present the stored digest snapshot clearly, link users back to the dashboard, and expose enough context for trust without overwhelming them.

---

## Visual and Branding Direction

Final decision:

- use light branding
- use a professional plain layout
- do not make the digest marketing-heavy

The email should feel like a security operations briefing, not a promotional newsletter.

---

## Item-Level Display Contract

Each digest item should show:

- title
- CVE ID
- one clean vendor/product line
- severity chips when applicable:
  - `Actively Exploited`
  - `High EPSS`
  - `Critical`
- `cvss_score`
- `epss_score`
- concise AI risk summary
- concise AI remediation block
- source link such as the NVD link

---

## Footer Contract

The footer should include:

- a short explanation of why the user receives the digest
- a link or direction to the dashboard
- a settings-management line

### Unsubscribe behavior

Final decision:

- include unsubscribe-style wording
- in MVP this should map to disabling digests in settings
- no separate marketing unsubscribe system is needed

---

## Short-Content Rule

If fewer than 10 total items exist even after backfill:

- send fewer items
- do not fabricate or pad the digest with synthetic content

---

## Delivery Interpretation Rule

If Resend accepts the send request but deeper delivery confirmation is unavailable:

- treat provider acceptance as sent for MVP

Final related decision:

- do not integrate provider webhooks in MVP

---

## Audit Simplicity Rule

For MVP:

- rely on database timestamps, digest status fields, and send attempts
- do not build a separate audit-log subsystem

---

## Practical Interpretation

When implementation begins:

- render a compact HTML email with text fallback
- keep the tone operational and clear
- expose source links and identifiers
- keep settings and unsubscribe behavior simple and product-linked

This is the finalized email-template contract for the MVP.
