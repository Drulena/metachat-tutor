# 0002. State transitions are a flat data table with declarative effects

- **Status:** accepted
- **Date:** 2026-10-22

## Context

Before the refactor, the transition mechanics were procedural code: a single
`_route` if-chain in `tutor_session.py` branched on `current_state` to compute,
per state, the accepted input, the target state, the completion/user-data
effects, the navigation options, and the retry behaviour. The scenario's state
entries also carried `next_state` and `input_type`, so the *same* transition
fact was stated twice — once as data in the scenario, once as code in the
router. Consequences:

- The whole transition graph was visible only by reading the if-chain end to end.
- Adding a state meant editing the routing function, not just adding data.
- Individual transitions could not be tested in isolation; the router and the
  scenario data could drift apart silently.
- Presentation (`message` / `options` / `validation`) and mechanism
  (`next_state` / `input_type`) were interleaved in the same dict.

## Decision

State transitions are a flat data table — `tutor/transitions` — with **one row
per non-terminal scenario state** (44 rows; the terminal `end` has none). Each
row records:

- **`accept`** — the input the state accepts: a regex for free-text states, or
  the set of option commands for button states.
- **`next`** — the target state: a string for a single target, or a
  `command → target` dict when the target depends on the input.
- **`effects`** — a list of declarative `(op, key, source)` triples that update
  the completion `items` and `user_data` (`set-item`, `set-user-data`).
- **`nav`** — the navigation options offered at the state.
- **`item` / `phase`** — the progress item key and the menu phase.
- **`back`** — the target of the back navigation.
- **`retryable`** — whether the state offers a retry after an LLM failure.

The session module routes purely by table lookup (`TRANSITIONS[current_state]`);
there is no per-state handler function and no routing if-chain. A scenario's
state entries carry **only** presentation data (`message`, `options`,
`validation`) — the dead `next_state` / `input_type` fields are deleted. A
`validate_transitions()` function checks the table's invariants at import/test
time: every non-terminal state has a row, every target names a known state, and
every effect references a known key and source.

Dynamic targets that cannot be a plain string are expressed by a small named
mechanism, not arbitrary code: a `next` value of `after_registration_{level}`
resolves the level suffix against the session's stored level (`_resolve_source`
/ `_go_back`), and role targets resolve through `ROLE_BY_VALUE`.

## Consequences

- The entire transition graph is visible in one place (44 flat rows).
- Adding a state is a data change — a row plus a scenario presentation module —
  with no edit to the routing function.
- Each transition is testable in isolation; `test_transitions.py` is
  table-driven and asserts rows directly.
- Presentation and mechanism are separated: scenario data no longer duplicates
  the transition facts.
- Effects are declarative data, not code — no per-state handler functions.
- Trade-off: a transition that needs genuinely imperative logic is harder to
  express than a function; the table (or its named-source resolver) must be
  extended for a new kind of dynamic target rather than inlining a lambda.

## Alternatives considered

- **Per-state handler functions** (each state a function computing its own
  transition) — rejected: it scatters the transition graph across many
  functions, hides the whole graph, and re-couples presentation to mechanism.
- **Keep the routing if-chain in `tutor_session`** — rejected: it is the original
  problem; the graph is invisible as a whole, untestable per state, and the
  scenario data duplicates the same facts.
