# Glossary

Canonical domain vocabulary for MetaChat Tutor. Use these terms in issues, code, and tests, and avoid the listed synonyms.

## Session terms

- **Turn** — A single step of the tutor conversation: either a learner message or a tutor (assistant) message. A tutor turn carries the message, the machine `state` it was produced under, the `options` available at that point, and once answered, the **used option** — the choice the learner made to answer that turn (nothing for a free-text answer). A **user** turn whose input the routing dropped carries its **rejection** — the copy shown beneath it, from the transition row (the module pairs them; pages never infer rejection). Submitting input yields the new tutor turn.

- **option** — A labelled choice a learner can make from a turn: a value, a label (a button) and an **option kind**. Options have two origins — a scenario *choice*, or *system navigation* (back / advance / finish) — but on a turn they form a single set. System navigation appears only on the current turn. _Avoid: "button"._

- **option kind** — An option's routing origin, carried beside its label: `choice` (scenario-defined), `nav` (system navigation — the transition row's `nav` map and the synthesised `back` edge), `retry` (the LLM-failure re-offer). The kind is fixed by origin, independent of the label: labels are presentation, and on a clash the scenario-defined label wins while the kind stays `nav`. _Avoid: "button type", "option type"._

- **state** — The machine's current position in a scenario, named by a string (e.g. `analysis_task_1_intermediate`, `role_menu`). Transitions out of a state are driven by the **transition table** (`tutor/transitions`), not by the scenario's state entries. `state` is internal to the session module; views and tests receive a `Turn` and a `Summary` rather than branching on the state name. _Avoid: "stage" — the README's "eight stages" is a coarser presentation grouping, not the machine's `state`._

- **transition table** — The flat data table (`tutor/transitions`) and single source of state-transition mechanics: one row per non-terminal scenario state recording the accepted input, the target state, the declarative effects (item / user-data updates), the navigation options, the progress item and phase, the rejection copy for dropped inputs, and whether the state is retryable after an LLM failure. The session module routes purely by table lookup; a scenario's state entries carry only presentation data (`message`, `options`, `validation`).

- **Summary** — The derived, presentation-ready answer to the status question of a session. One question per field: the **section rows** with their statuses (in the module's own section order, under the module's own headings), step counts and percentage, the **lifecycle pair** (`started` / `finished`), participant name and level, and the session id. Produced by the session module for an untouched session as well — the **zero-state Summary** — so asking about progress never fails. Consumers render what they are told and compute nothing; they never inspect raw `state`. _Avoid: "phase" (gone — lifecycle is the `started`/`finished` pair), "progress dict"._

- **section row** — The progress line for one **task**: its key, label and **completion status**. Rows are grouped into sections (Analysis Tasks, Communication Roles); a section states how many of its rows are completed. Pages render rows as given — the status is decided once, in the module. _Avoid: "task cell", "progress bar item"._

- **step** — One of the fifteen ledger items the **completion model** tracks, including the scaffolding points (pre/post-test, level, modes, reflection) that never appear as task lines. The percentage denominator counts steps. _Avoid: "task" (a task is what a row shows)._

- **task** — A unit of learner work a **section row** shows: the two analysis tasks and the nine roles — eleven rows, a deliberate subset of the fifteen **steps**. _Avoid: "step" for a row, "task" for the pre/post-test._

- **lifecycle pair (started / finished)** — `started`: the conversation exists — the session has begun (the chat auto-starts it, before the learner registers). `finished`: the conversation has reached its terminal state. They answer lifecycle questions only — completion is the job of counts and rows, never of `finished`. Registration is carried by the **Summary**'s participant name: set once the learner has given it. Pages gate on `started` (the progress panel shows from the **zero-state Summary**) and on `finished` (the conversation is over).

- **completion model** — The module's single source of truth for progress: a per-item status (`not_started` / `in_progress` / `completed`) across the scenario's tasks and assessment points. Every progress figure, **section row**, and used-option mark is derived from it; there is no parallel completion list.

## Research-domain terms

- **polylogue** — A computer-mediated, written, multi-party, asynchronous online exchange characterised by a complex structure of participants' connections rather than linear interactions, a high potential for conflict, often anonymous participants, and messages without addressing. The conversation the tutor simulates.

- **role** — One of the constructive-communication roles a learner practises during a role-play task (the nine `role_*` tasks); it relies on rational argumentation.

- **tactic** — A communicative move used within a constructive strategy by a role while conducting a polylogue.

- **metagrapheme** — A metalinguistic/graphemic device used in a polylogue (e.g. emojis, text formatting).
