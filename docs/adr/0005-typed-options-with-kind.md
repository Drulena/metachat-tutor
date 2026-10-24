# ADR-0005 — Typed options with kind; row-owned rejection copy

- Status: Accepted
- Date: 2026-10-24
- Issue: #15 (supersedes the options clause of ADR-0001; builds on ADR-0003)

## Context

ADR-0001 set `Turn.options: Optional[dict[str, str]]` — one flat label map for the current assistant turn. Three sources merge into it: scenario options (from the scenario's state entry), the transition row's `nav` map, and the `back`/`retry` edges synthesised by `_navigation_options`. The merge rule ("scenario-defined options win on clashes") silently drops the row's nav label on a clash — in `analysis_intro_*` the row offers `yes: "Yes"` and the scenario maps `yes: "Yes, proceed"`, so the learner sees the scenario label while the value still routes through the row's nav. Nothing in the flat map tells a template which of the three kinds an offer is; the GLOSSARY's "option" entry names two origins and the third (retry) lives only in code.

Rejection was the same shape problem in the view: the module silently drops an input the routing does not accept, and `chat_view` inferred that a rejection had happened (POST, last turn unanswered, not finished) to raise a generic `messages.warning` with hardcoded copy — the view guessing at module behavior, the template carrying a `messages` block for it.

## Decision

1. `Turn.options: Optional[list[TurnOption]]`. `TurnOption` is a frozen dataclass `{value, label, kind}` in `tutor/session.py`. The kind vocabulary is `OPTION_KINDS = ("choice", "nav", "retry")`.
2. Kind is the routing origin, tested at rendering time against the row's `nav` map (plus the synthesised `back`/`retry` edges): an offered nav edge is `nav`, the LLM-failure retry is `retry`, everything else — the scenario's learner values (numbers, free text, yes, and scenario-declared loop values like `revise`, `continue`) — is `choice`. The scenario map is presentation; the nav map is routing, so it is the origin test.
3. Labels keep the existing presentation precedence, unchanged: on a clash the scenario-defined label wins and the kind stays `nav`. Rendered labels are byte-identical to before; the list keeps today's merge order (nav offers first).
4. Transition rows gain `rejected: Optional[str]` in the closed field set: the row's copy shown when its input is rejected; `None` takes the module's generic fallback (`_GENERIC_REJECTION`). The validator checks the type.
5. `Turn.rejection: Optional[str]`: the module pairs the row's copy with the unanswered user turn (the chat entry is flagged at `submit()` time when routing drops it). `chat_view`'s rejection inference, its hardcoded copy, and the `messages` block in `chat.html` are retired.
6. The export payload inherits the shape shift (`turn.options` dict → list of `{value, label, kind}`) — no external consumer, per the ADR-0003 precedent.

## Options considered

- Parallel kind map (`options: dict[str,str]` + `kinds: dict[str,str]`) — two shapes to keep in sync, primitive obsession.
- Separate lists per kind — the template must reassemble the single set; the glossary defines options as one set.
- Infer kind from the label (emojis, "Back") — fragile, no source of truth.
- Keep rejection inference in the view — the status quo: the view guesses, the copy is one-size, and the template needs a `messages` block for a module question.

## Consequences

- Templates render what they are told: `opt.kind` is a styling/behaviour hook, `turn.rejection` is one line under the user bubble; no page infers option origins or rejections.
- Rejection copy becomes per-state where useful (`role_menu`: "Choose one of the numbered roles, finish, or back.") while nav-only and prose rows take the generic fallback.
- The export payload shifts shape (schema-shift precedent of ADR-0003).
- All 45 transition rows carry the `rejected` key (closed schema, validator-enforced).
- `TurnOption` is the repo's first frozen dataclass — session value types are now immutable by default.
