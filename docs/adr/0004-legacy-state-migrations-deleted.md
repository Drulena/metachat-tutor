# 0004. Legacy session-state migrations are deleted

- **Status:** accepted
- **Date:** 2026-10-23
- **Supersedes:** the maintenance decision of commit `42c0f6b` (keep the retired idea-feedback key routable, 2026-10-22).

## Context

Sessions saved before 2026-10-20 store shapes the current module no longer writes: progress kept as parallel lists instead of the per-item ledger, the pre-rename `roleplay_feedback_idea` state key, and analysis task keys in the positional slug form (`analysis_task_{n}_{level}`). The module carried the translation in code — `_migrate_items`, `LEGACY_STATE_KEYS` + `_migrate_state_key`, and `_task_slug`, the slug rule the progress rows used to match saved keys — plus two tests pinning the migrations. That was ~90 lines living in the same module area as the new `Summary` shape, and the slug rule was the last reason any consumer still formatted task keys.

## Decision

Delete the migrations outright: `_migrate_items`, `LEGACY_STATE_KEYS`, `_migrate_state_key`, `_task_slug`, and the two legacy tests. `_load()` is a plain storage read. The roundtrip test for the current items shape (`test_saved_state_preserves_items_model`) stays — it guards save/load, not migration.

The attestation behind the cut, given by the project owner during the design grilling: the research cohort that used the pre-2026-10-20 app is closed, and no sessions created before that date hold live data outside tests.

## Consequences

- A stray legacy row strands **by design**: its migrated-in state has no transition row, so every input is rejected and the session cannot advance. The recovery is reset — accepted, because the attestation says there is no such row to strand.
- Task keys have exactly one spelling: the ledger keys (`analysis_task_1`, `role_mediator`, …). No formatting rule survives in module or templates.
- The retirement of the positional slug completes the `Summary` reshaping of [0003](0003-summary-answers-the-status-question.md).

## Alternatives considered

- **Keep the migrations as permanent insurance** — rejected: ~90 dead lines in the area the new shape touches, guarding data the attestation says does not exist; insurance against an attested-empty set is dead code.
- **Write a one-off data migration for stored sessions** — rejected: nothing to migrate under the attestation, and a migration script would need the same slug rules being deleted.
