# Glossary

Canonical domain vocabulary for MetaChat Tutor. Use these terms in issues, code, and tests, and avoid the listed synonyms.

## Session terms

- **Turn** — A single step of the tutor conversation: either a learner message or a tutor (assistant) message. A tutor turn carries the message, the machine `state` it was produced under, and the `options` available at that point. Submitting input yields the new tutor turn.

- **option** — A labelled choice a learner can make from a turn: a value plus a label (a button). Options have two origins — a scenario *choice*, or *system navigation* (back / advance / finish) — but on a turn they form a single set. System navigation appears only on the current turn. _Avoid: "button"._

- **state** — The machine's current position in a scenario, named by a string (e.g. `analysis_task_1_intermediate`, `role_menu`). Transitions are data-driven from the scenario's state map. `state` is internal to the session module; views and tests receive a `Turn` and a `Summary` rather than branching on the state name. _Avoid: "stage" — the README's "eight stages" is a coarser presentation grouping, not the machine's `state`._

- **Summary** — The derived, presentation-ready view of a session's progress: overall and per-section completion, status, completed option values, completed roles/modes, task lists, participant level, and the current menu phase. Produced by the session module; views render it without inspecting raw `state`.

- **completion model** — The module's single source of truth for progress: a per-item status (`not_started` / `in_progress` / `completed`) across the scenario's tasks and assessment points. Every progress figure, task list, and completed-value set is derived from it; there is no parallel completion list.

## Research-domain terms

- **polylogue** — A computer-mediated, written, multi-party, asynchronous online exchange characterised by a complex structure of participants' connections rather than linear interactions, a high potential for conflict, often anonymous participants, and messages without addressing. The conversation the tutor simulates.

- **role** — One of the constructive-communication roles a learner practises during a role-play task (the nine `role_*` tasks); it relies on rational argumentation.

- **tactic** — A communicative move used within a constructive strategy by a role while conducting a polylogue.

- **metagrapheme** — A metalinguistic/graphemic device used in a polylogue (e.g. emojis, text formatting).
