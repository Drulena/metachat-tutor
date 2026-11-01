# 0007. SessionRecord is the write-through ledger

- **Status:** accepted
- **Date:** 2026-11-01

## Context

Research admin (#35) needs to inspect, filter and export sessions; the intake form (#28) and selector assessments (#29) need a place for group and score data. `SessionRecord` (`tutor/models.py`) is dead code: the app has **no migrations at all**, the table has never existed, no code imports the model, and `pretest_scores` is read nowhere — scores live only in the browser-bound Django session and reach neither the Summary nor the export payload. Greenfield: there is no stored session data to protect (the standing owner attestation from ADR-0004/0006: the database holds test sessions only, recovery is reset).

## Decision

1. **One ledger row per session, created at the intake form's submission, written through on every submission.** Participant, group, level, the appended Turn log, reflection (on acceptance) and lifecycle timestamps all land on the row. Pages never read the ledger; the **Summary** (ADR-0003) stays the sole presentation source, the ledger is the research artefact.
2. **chat_history entries are appended verbatim, append-only** — the existing entry dicts (`role`, `content`, `state`, `timestamp` ISO; assistant entries also `options`, `llm_failed`; dropped inputs carry `rejected`). The future per-Turn table is a one-pass read-transform of this log; nothing today mutates past entries.
3. **Identity: `session_id` becomes a UUID v7** (canonical 36 chars, `unique=True`, index), generated at state creation (`tutor_session.py:298`) and copied onto the row at intake. Python 3.11 has no `uuid.uuid7()`, so a small helper (unix-ms 48 bits + version/variant + random bits) owns generation. The same value is the canonical identifier everywhere: chat UI info-button (#32), admin, export payload, export filename. Time-ordered ids sort by creation and index well.
4. **Lifecycle: `created_at` = session start (the row's birth at intake), `updated_at` = auto last activity, `finished_at` = nullable and derived.** It is stamped when the machine enters `data_collection` and — because `data_collection` is now **terminal** (`back: None`, no exit nav, the completed banner renders on it, the `end` state retired with its goodbye) — is never cleared. The ledger mirrors the Summary's `finished` (ADR-0003 lifecycle pair unchanged; `finished` = terminal = data_collection).
5. **Group is a canonical entity** (`Group`): intake does case-insensitive lookup, creates on a miss, keeps the first-entered spelling; the ledger row references it by FK. The intake field is a plain text input with a native `datalist` (revisit at >500 groups; the FK model never blocks a later searchable combobox).
6. **Assessments are child rows** (`Assessment`: session FK, `kind` ∈ {pretest, posttest} — extendable, `raw_answer`, `scores`, `created_at`), written at gate acceptance. The legacy `pretest_scores`/`posttest_scores` column pair and the never-set `session_key` field are dropped from the model **before the first migration exists** — no data migration, no shim. The selector UI (three 1–5 selects + submit, rendered inline on pretest/posttest states) posts the same `"a b c"` string to the existing chat endpoint: the gate regex (`^[1-5] [1-5] [1-5]$`) and `_parse_scores` stay byte-identical. The abstraction lives in the data model, not in transition plumbing (refactoring the chat gates into the abstract test kind stays a considered future step).
7. **Reset chains.** `reset_view` swaps in a fresh state (new `session_id`) and a fresh ledger row; the abandoned row gains a `previous_session` self-FK to its successor's predecessor — chains are reconstructible, chain heads filter trivially. "Abandoned session" is defined operationally: `finished_at` is null. Cleanup is admin-side: filter (finished empty, `updated_at` range) + a Delete-selected action with the standard confirmation — **no abandonment policy is coded**.
8. **Migration is greenfield:** the app's first `0001_initial` creates `Group`, `SessionRecord` (as decided) and `Assessment`. No backfill, no compatibility shim (owner attestation).
9. **Admin is stock Django admin:** `list_display` (short id, participant, group, level, created, last activity, finished, score summary, reflection size), `list_filter` (group, level, finished/not, created and finished date ranges), search on id + participant, read-only dialogue detail. Researchers: view-only; maintainer: full + the delete action. Extensibility is kept the Django way (custom `FieldListFilter` subclasses, registered actions, template overrides) — a rich custom page stays a considered increment, not today's design.
10. **Consent disclosure:** the intake page carries one line — proceeding with the session counts as explicit consent — linking a static `/terms/` page. No checkbox, no consent plumbing; retention/deletion obligations remain an open research-ethics question, not an architectural one.

## Consequences

- Scores finally reach the research corpus: the export payload gains an `assessments` dict (the uploaded artefact is self-contained), and admin shows them per session.
- Walk-aways and the 24 h cookie expiry (`SESSION_COOKIE_AGE=86400`) produce abandoned rows **by design** — visible, chainable, deletable; no completion state can silently vanish.
- Transition/scenario fixtures and traversals are rewritten mechanically for the retired states (`start` registration, `level_assessment`, `end`); no test pins the prose counts (32 bases / 44 pairs / 33 states).
- `data_collection` loses its Exit option; its export instructions are the session's last screen.
- Abandonment cleanup is a maintainer judgement applied through filters, not a cron.

## Alternatives considered

- **Write the row at completion only** — rejected: abandoned sessions (the admin's #1 inspection question) would be invisible.
- **Per-Turn table now** — deferred: the append-only JSON log gives the same query depth for admin viewing at a fraction of the cost; the 1:1 transform keeps the door open.
- **`finished_at` stamped at the Exit tap (the `end` state kept)** — rejected: leaves a "finished the flow, never tapped Exit" gap; retiring `end` makes the terminal screen itself the completion event.
- **Status enum (in_progress/finished/abandoned)** — rejected: invents an abandonment policy nobody set; `finished_at` + `updated_at` answer every filter with two columns.
- **Durable client participant key (localStorage) chaining all sessions of a browser** — deferred: needs client identity infra; the self-FK covers the reset chain, which is the flow that exists.
- **`session_id` as plain uuid4 hex (as today)** — rejected against v7: v7 orders ids by creation time, giving free chronology in indexes, admin ordering and filenames at zero query cost.
- **Score selectors feeding a refactored abstract-test state machine** — split: the data model abstracts now (child rows, extendable kind); the transition-side refactor is a separate, future ticket.
