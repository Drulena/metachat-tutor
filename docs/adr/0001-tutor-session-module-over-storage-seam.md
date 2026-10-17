# 0001. The Tutor Session is a deep module over a storage seam

- **Status:** accepted
- **Date:** 2026-10-17

## Context

The current tutor logic is split across three places, and every one of them reaches through a live Django `request`:

- `tutor/state_machine.py` — reads/writes stringly-typed `request.session` keys (`user_data`, `current_state`, `chat_history`, `scenario`, `session_id`, `retry_count`).
- `tutor/views.py` — `chat_view` re-derives navigation (`show_back` / `advance_*` / `show_finish`) and `completed_option_values` by branching on `current_state`, and duplicates the `back` button (stored on every turn *and* rendered via `show_back`).
- `tutor/data.py` — a second completion scheme (`completed_tasks` / `opened_tasks` / `get_completion_percentage`) that sits alongside `state_machine`'s `completed_steps` and `views`' `completed_roles` / `completed_modes`.

As a result: callers must know the session's stringly-typed keys; completion is tracked in three parallel schemes; and the negative-navigation tests read rendered HTML with a regex that structurally can never see the option buttons it claims to check (the `system-options` div comes after the first `</div>` that truncates the capture).

## Decision

The tutor becomes a single deep module, `TutorSession`, that owns the state machine, the completion model, and the navigation rules, and hides all storage behind a seam.

- **Interface — five methods:** `start() -> Turn`, `submit(text) -> Turn`, `turns() -> list[Turn]`, `progress() -> Summary`, `reset() -> None`. Export is composed by the view from `turns()` + `progress()` + `session_id`; it is not a sixth method.
- **`Turn = {role, message, state, options, timestamp}`.** An assistant turn carries the *full* option set — scenario choices plus system navigation (back / advance / finish), navigation on the current turn only. A user turn carries message + `state`, no options. The template renders one option list per turn.
- **`Summary`** (from `progress()`) is the single derived, presentation-ready view: progress metrics, `completed_option_values`, `completed_roles` / `completed_modes`, task lists, `level`, and the menu `phase`.
- **A single canonical completion model** — a per-item status (`not_started` / `in_progress` / `completed`) over the scenario's tasks and assessment points. Every progress figure, task list, and completed-value set is *derived* from it; the three parallel completion lists are deleted.
- **A storage seam with two adapters:** `SessionStorage` (the Django session, in production) and `MemoryStorage` (an in-memory dict, in tests). The module never touches `request.session`.
- **Views never branch on `current_state`.** `chat_view` uses `start` / `submit` / `turns` / `progress`; `main_menu_view` uses `progress()` (the `phase` + task lists drive its layout); `export_view` / `reset_view` use `turns` / `progress` / `session_id` / `reset`.
- **The LLM is an injected dependency** (`llm.feedback(...) -> (text, failed)`), defaulting to the existing demo/echo when no API key is set; tests inject a deterministic fake.
- **Cutover is strangler-style, green at each cut:** build the module + seam + adapters → flip `chat_view` + `chat.html` and move the nav tests to structured `Turn.options` assertions → flip the other three views → delete the absorbed old code. Pure constants (`SCENARIO`, `LEVELS`, `STEP_KEYS`, `ANALYSIS_STEP_KEYS`, `ROLE_STEP_KEYS`) stay in `data.py`.

## Consequences

- Invariants (state transitions, navigation availability, completion tracking) relocate into the module — locality.
- The negative-navigation tests become structured assertions on `Turn.options`; the Django `request` mock and the `os.getenv` / `requests.post` mocks disappear.
- `state_machine.py` and `data.py`'s completion functions dissolve into the module.
- The module is fully exercisable in memory, so the flow is testable without Django's test client.

## Alternatives considered

- **A key/value storage seam** (load/save individual session keys) — rejected: it leaks the stringly-typed keys across the seam, which is exactly the coupling being removed.
- **Keep the thin view + `state_machine` split and only fix the tests** — rejected: it leaves the stringly-typed session coupling, the duplicated `back` button, and the three parallel completion schemes in place.
