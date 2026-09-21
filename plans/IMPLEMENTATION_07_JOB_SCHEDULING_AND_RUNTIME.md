# Implementation Decision 07: Job Scheduling and Runtime

## Purpose

This file captures the finalized scheduling and runtime strategy for the VulnIQ MVP pipeline.

Decision date: 2026-08-09

---

## Summary

The VulnIQ MVP should use:

- a Django management command as the canonical daily pipeline entrypoint
- an external system scheduler to trigger it at `12:00 AM IST`
- no Celery, Redis, or in-process scheduler for MVP

This keeps runtime operations simple while preserving a clean upgrade path if background infrastructure is needed later.

---

## Canonical Entry Point

The daily pipeline should run through one top-level Django management command.

Example direction:

- `run_daily_digest_pipeline`

This command should be the single canonical execution path for:

- scheduled daily runs
- manual CLI runs
- admin-triggered "run now" behavior

The admin trigger must call the same core pipeline path, not a separate implementation.

---

## Scheduler Strategy

Final decision:

- use an external scheduler such as the server's native scheduler
- do not use APScheduler inside the Django process
- do not introduce Celery beat + worker for MVP

Reasoning:

- lowest operational complexity
- no queue infrastructure required
- easier debugging and deployment
- sufficient for one daily pipeline in MVP

---

## Internal Runtime Design

The pipeline should be implemented as:

- one orchestration command
- internally composed of callable service functions/modules

This allows:

- clean code structure
- easier testing
- later extraction into queued/background execution if needed

Optional smaller commands may be added later, such as:

- source sync commands
- historical backfill commands
- targeted maintenance commands

They are not required to be part of MVP from day one.

---

## Locking Strategy

Final decision:

- use a database-backed application lock

Goal:

- prevent overlapping daily runs
- ensure only one pipeline execution operates at a time for the main scheduled workflow

Do not rely on:

- no locking
- filesystem-only locking as the primary coordination method

---

## Error and Exit Behavior

The command should:

- create or update an `ingestion_run` record
- continue per organization even if one organization's digest generation fails
- record degraded and failed states clearly
- exit non-zero only when the global run itself fails materially

This preserves maximum daily output while maintaining operational visibility.

---

## Admin Trigger Scope

Final decision:

- admin may trigger the full daily pipeline only

Do not allow from admin in MVP:

- arbitrary partial pipeline step execution
- source-specific run orchestration controls

This keeps internal tooling safer and simpler.

---

## Historical Backfill Scope

Final decision:

- historical or special backfill runs should be CLI-only

Do not expose historical backfill controls in admin for MVP.

Reasoning:

- lower risk
- clearer operator intent
- easier to keep support tooling simple

---

## Practical Interpretation

When implementation begins:

- build one Django management command as the production entrypoint
- trigger it from the server scheduler at `12:00 AM IST`
- protect it with a DB-backed lock
- use the same pipeline path for scheduler, CLI, and admin-triggered runs

This is the finalized runtime and scheduling strategy for the MVP.
