# LexAd Reliability and Demo Experience Implementation Plan

Source design: `docs/superpowers/specs/2026-07-11-lexad-reliability-demo-experience-design.md`

## 1. Establish regression coverage and shared limits

- Add reusable material-field limits and apply them to create and update schemas.
- Add service/API tests for invalid updates, conditional decisions, failure semantics, and version reporting.
- Add a frontend test command and focused tests for status/feedback utilities if the existing dependency lock can be updated safely.

## 2. Preserve submitted inputs and correct state semantics

- Add a migration and model for immutable material submission snapshots.
- Create/reuse a snapshot when a material version is reviewed and associate reviews with it.
- Add `conditional_approved` to the material status enum and migration; validate that conditional decisions include conditions.
- Add legal-review claim and conditional decision updates that cannot overwrite an already decided review.
- Return snapshot-aware version history to the UI.

## 3. Make in-app review execution recoverable

- Add queue/lease/retry fields to reviews and a migration.
- Replace request-only execution with a small lifespan runner that claims queued/stale jobs using an independent session.
- Make duplicate AI-review requests return the active job, and make retries preserve prior attempts.
- Ensure legal failure marks the review failed; deterministic-only output is explicitly degraded and never shown as a normal full AI conclusion.

## 4. Bound extraction work

- Validate upload signatures and extraction limits before parsing.
- Move blocking extraction into a thread from async endpoints.
- Bound PDF pages, image pixels, archive expansion, worksheet traversal, and output text; preserve friendly API errors.

## 5. Improve demonstration feedback and consistency

- Add shared toast and confirmation controls and replace existing native dialogs.
- Update result, dashboard, and legal pages for queued/recovered/degraded/conditional states and retry actions.
- Tighten touched API DTOs and synchronize the runtime application version and Python dependency metadata.

## 6. Verification and handoff

- Run Alembic migration checks and backend tests against SQLite.
- Run frontend type check, tests, and production build.
- Re-audit version references and validate the health/OpenAPI version.
- Document known demonstration-grade task-runner limits.
