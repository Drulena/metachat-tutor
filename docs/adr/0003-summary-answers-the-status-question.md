# 0003. The Summary answers the status question

- **Status:** accepted
- **Date:** 2026-10-23
- **Supersedes:** parts of [0001](0001-tutor-session-module-over-storage-seam.md) — its `Summary` bullet and the `main_menu_view` phase sentence (quoted below). The five-method interface, the storage seam, the completion model, `Turn`, and LLM injection stand.

## Context

ADR-0001 made `TutorSession` the deep module and `Summary` its progress view. The shipped `Summary` was shallow: 17 flat fields — progress figures, a status badge, the current step, opened tasks, completed roles/modes, task lists, the menu `phase`, `completed_option_values`. The status vocabulary (`not_started` / `in_progress` / `completed`) lived in the module's completion model, but the returned shape handed out label lists plus completed-key sets, so every consumer derived each task's status itself. That vocabulary ended up spread across 11 templates.

The divergence was measured on one learner state — one analysis task in progress: `menu.html` asked the question positionally (`forloop.counter <= analysis_progress.completed`) and stamped ✅ **Completed** on task 2, a task the learner never opened, while `main_menu.html` asked it by key membership and said ⬜ **Not Started**. Same session, two pages, two answers.

`completed_option_values` was the same shallowness in the chat: it is the value `views.py` used to re-derive by branching on `current_state` (the leak ADR-0001's Context names), surviving into the interface — `chat.html` compared raw option values, and `progress()` rebuilt the set by branching on the current state (`role_menu` → role values, `after_registration_*` → mode values, `level_assessment` → the level). It is also coarse where option values collide: `'1'` is the Mediator choice at the role menu *and* the analysis-mode choice after registration.

## Decision

`progress()` returns a `Summary` of nine fields, one question per field: `sections`, `started`, `percentage`, `total_steps`, `completed_steps_count`, `finished`, `level`, `user_name`, `session_id`.

- **`sections: list[ProgressSection]`** — the module owns the section order (analysis, roles), the heading wording (`📝 Analysis Tasks`, `🎭 Communication Roles`) and every row's status: `ProgressSection = {title, rows: [{key, label, status}], completed, total}`. Templates render rows as given; one shared include (`task_group.html`) is used by both pages, so the status question is asked once, in the module.
- **The lifecycle pair is in the interface.** `progress()` never raises: an untouched session answers with the **zero-state Summary** (all rows `not_started`, counts 0, `started` False). `turns()` / `submit()` keep their start-precondition. Views probe `progress().started`; the `_summary_or_none` exception translation is deleted.
- **`finished` answers lifecycle only** — the conversation is at its terminal state. Completion is the domain of counts and rows; pages gate the end banner and the composer on `finished`.
- **The used-option mark belongs to the turn.** `Turn` gains `used_value`: the option value the learner used to answer that turn, paired from the user entry that follows it; `None` for free-text answers, off-list answers, and the newest unanswered turn. `chat.html` marks the used option from `turn.used_value`. `completed_option_values` leaves the `Summary`, the branch-on-state block leaves `progress()` — it is pure ledger arithmetic — and the chat template receives no raw option values at all.
- **Field guards pin the shape.** The guard tests assert the exact field-name lists: the `Summary` shape is a contract, and adding a field is a deliberate act.

## Consequences

- The pages cannot disagree: they render the same include, fed by statuses decided once. The measured contradiction is structurally impossible, not fixed line by line.
- The export payload schema shifts: `progress` gains `started` / `finished`, turns gain `used_value`, eleven fields leave. Accepted — the export is a research artifact and nothing in the repo parses it.
- The leak ADR-0001 named is closed in the interface, not just in `views.py`.
- Retiring the `phase` field retires the positional task slug with it (see [0004](0004-legacy-state-migrations-deleted.md)).

## Alternatives considered

- **Fix each template in place** (patch the sidebar's positional fallback) — rejected: the status vocabulary stays distributed across 11 templates, and every new consumer re-asks the question and can diverge again.
- **Return the raw items ledger and let pages group it** — rejected: consumers would re-derive section grouping, titles and counts — the same shallowness one level down.
- **Keep `completed_option_values` alongside the per-turn mark** — rejected: a global set is coarse at colliding values, and it is the leak being closed.
- **Per-section percentage fields** — rejected: no consumer counts it; `completed` / `total` are kept because templates cannot count rows without re-deriving status.
