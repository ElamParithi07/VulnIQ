# Implementation Decision 09: Gemini Prompt Design

## Purpose

This file captures the finalized Gemini prompt behavior and enrichment-output rules for the VulnIQ MVP.

Decision date: 2026-08-09

---

## Summary

The MVP should use Gemini to generate two outputs for selected digest candidate CVEs:

- a concise risk summary
- concise remediation guidance

Prompts should be versioned, outputs should stay operationally useful, and the system should avoid inventing overly specific remediation when confidence is low.

---

## Output Rules

### Risk summary

- maximum two sentences
- concise
- operationally clear
- business-friendly

### Remediation

- short technical guidance
- followed by commands or configuration examples when applicable
- no long prose explanations

---

## CVE Identifier Rule

Prompted summary prose does not need to mention the CVE ID explicitly.

Reason:

- CVE ID will already be shown in the UI and email metadata
- summary text should focus on risk and impact clarity

---

## Confidence Rule

If product-specific remediation is unclear or cannot be inferred confidently:

- return conservative generic remediation guidance
- do not invent highly specific commands that are not well supported by the available input

This protects trust and reduces unsafe automation-style output.

---

## Prompt Versioning

Final decision:

- store an explicit prompt version string on the enrichment record

This supports:

- prompt iteration
- debugging
- selective regeneration later

---

## Model Strategy

Final decision:

- use one Gemini model for both summary and remediation in MVP

If quality later demands separate model choice or separate prompt paths, that can be introduced after the MVP.

---

## Practical Interpretation

When implementation begins:

- build prompts for concise structured operational output
- keep prompt versions explicit and stored
- bias the model toward safe, compact guidance instead of speculative specificity

This is the finalized Gemini prompt behavior baseline for the MVP.
