# LexAd Reliability and Demo Experience Design

Date: 2026-07-11

## Goal

Improve the demonstration project in two ordered stages: first remove defects that can create misleading review conclusions or lose review work, then make the repaired flows clear and pleasant to demonstrate. Deployment-account hardening is explicitly out of scope for this iteration.

## Constraints

- Keep the existing FastAPI, SQLAlchemy, Vue, and SQLite/PostgreSQL-compatible stack.
- Do not add Redis, Celery, RQ, or a separately deployed worker.
- A conditional legal decision is a distinct terminal state, not a returned material.
- Preserve existing review records and remain usable with SQLite for local verification.

## Stage 1: Review Integrity and Reliability

### Immutable submission snapshots

Create an immutable submission snapshot when a material version is first submitted for AI review. The snapshot stores the submitted material fields that affect a review: name, raw text, industry, platforms, material type, priority, deadline, and submission version. Retries for the same submitted version reuse that snapshot; a changed and resubmitted material creates a new one. Each review points to its snapshot, while `Material` remains the editable working copy.

Returned materials may be edited, but editing must never alter the input associated with an earlier review. Historical version views will read the review and its snapshot together, including stored legal and public-opinion results and referenced rule/library versions.

### Material and legal-decision state machine

The material workflow becomes:

`draft` or `returned` -> `ai_reviewing` -> `pending_legal` -> `in_legal_review` -> `approved`, `conditional_approved`, or `returned`.

Only returned materials are editable and may be resubmitted. `conditional_approved` is a terminal business state. It must include a non-empty condition/notes field and be shown to marketing users as a final result with its conditions.

Legal users explicitly claim a pending review. Final decision writes include an optimistic state/version condition so a second legal user cannot silently overwrite the first decision.

### Durable in-app execution

The review record is the durable job record. It gains a queued state, retry count, a lease/claim marker, and timestamps needed for recovery. A request creates or returns a single active job for the material submission version; a database uniqueness rule plus conditional update prevents concurrent duplicate jobs.

An application-lifespan runner periodically claims queued jobs and reclaims expired leases. It uses a separate database session per execution. A process restart leaves the job in the database; the next application start recovers it. A retry produces a new attempt or requeues a failed job while preserving the failure history.

This is at-least-once, demonstration-grade execution. It prevents duplicate final writes with a lease token but cannot provide strict exactly-once external model calls across a process failure; the limitation is documented rather than hidden.

### Legal result semantics

A task cannot be presented as a completed legal conclusion when the legal branch failed. If only the semantic-model layer is unavailable, the deterministic legal layers (L1/L3/L4) may produce a `degraded` legal result with an explicit warning and an available legal-review action. A hard legal failure produces a failed task with a retry action and no misleading score of zero.

## Stage 1: Resource Boundaries

- Apply the same Pydantic limits to material creation and update: bounded name/text lengths, platform count and platform-item lengths, priority enum, and valid deadlines.
- Validate upload signatures as well as extensions. Bound image pixels, PDF pages, archive entry count and expanded size, worksheet rows/cells, and extracted-text length.
- Run blocking OCR and document parsing off the async request event loop. Return short business-facing errors for unsupported, oversize, or unreadable files.

## Stage 2: Demonstration Experience

- Add a small app-level toast and confirmation-dialog facility; replace the existing browser `alert` and `confirm` calls.
- Make result status visible and actionable: queued, processing, recovered, degraded completion, failed/retryable, approved, conditional approval, and returned.
- Keep the current visual theme. Extract only reusable feedback/state logic and low-risk sections of large pages; do not perform a wholesale UI rewrite.
- Tighten API DTOs and remove `any` from the touched review/material/feedback paths.
- Make the application version single-source and align Python packaging metadata with runtime dependencies.

## Verification

Backend tests cover snapshot immutability, duplicate trigger handling, restart/lease recovery, legal failure and degraded completion, legal-decision concurrency, conditional approval validation, and material/file limits. Frontend tests cover status mapping, feedback controls, and theme preference. CI runs backend tests, frontend tests, type checking, and production build.

Acceptance criteria:

- Restarted review work is recovered from the database.
- A review history shows the exact submitted material version and stored result.
- Legal failure never appears as a completed zero-risk conclusion.
- Conditional approval completes its own user-visible terminal flow.
- Oversize or malformed inputs fail safely with useful messages.
- Existing regression tests and new focused checks pass under SQLite; the frontend type check and build pass.

## v0.5.1 Audit Note

The current source is mostly labelled `0.5.1`: README, frontend package/lockfile, frontend UI constant, backend package metadata, development documentation, technical reference, and release notes agree. One runtime discrepancy remains: `backend/app/core/config.py` still sets `APP_VERSION` to `0.5.0`, so the health endpoint and OpenAPI metadata report the wrong version. The v0.5.1 release is therefore not completely consistent and this iteration will correct it.
