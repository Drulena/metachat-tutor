# Coding Standards

The rules this repo holds itself to, each with its why. Standards reviews check
them; new code joins them at the same bar.

## Docstrings

Public callables carry PEP 257 docstrings: a one-line summary in third person
("Project a chat-history entry into a Turn."), `Parameters:` only when a
parameter is non-obvious. Private helpers (`_rejection_copy`, `_used_value`,
`_navigation_options`, …) carry one too — they encode the routing rules, and a
reader at the seam needs the rule, not just the name. A docstring that merely
restates the name is noise.

## Every template class has a style rule

A class rendered into `tutor/templates/tutor/*.html` must have a matching rule
in `tutor/static/tutor/style.css`. A class shipped without one is an
unstyled element the learner sees plain (`.rejection-note` rode the template
for a commit before its rule landed). When a template gains a class, the CSS
rule lands in the same change.

## Design follows Material Design 3

All UI styling respects MD3 (owner standing rule, 2026-10-25). Colors, corner
radii, control shapes and state treatments come from the tonal token set in
`:root` of `tutor/static/tutor/style.css` (baseline purple scheme:
`--md-primary`, `--md-primary-container`, `--md-surface*`, `--md-outline*`,
`--md-error*`, …) — not from ad-hoc hex. Component roles: learner choices use
filled tonal buttons (primary-container); system/utility offers use the
secondary-container pill; destructive notes use error-container; state marks
(used, completed) are muted tonal states, never `pointer-events` removal —
visual disability is a color decision, functional disability is a routing
decision, and the two stay separate. A new component picks its colors from
the tokens; a new token joins `:root`, never a literal in a rule.


Module strings pinned by tests — the generic rejection copy
(`GENERIC_REJECTION`), the role-menu copy (`ROLE_MENU_COPY`), the drive
sequence (`ROLE_MENU_INPUTS`) — are defined once, in
`tutor/test_tutor_session.py`, and imported by the other test modules
(`test_options.py`, `test_views.py`). A string copy pinned twice drifts the
first time the string changes; the shared pin catches every consumer at once.

## Django template comments

`{# … #}` is single-line (Django ≥1.9). A multi-line block header written as
`{#` … `#}` renders as literal text on the page — the progress-panel header
shipped on both pages that way. Block comments use `{% comment %}…{% endcomment %}`.
A rendered-page test (assert the words absent from the response) catches what
unit tests of the module never see.

## LLM output contract

The learner-facing answer is the parsed `content` field only. Chain-of-thought
fields (`reasoning`, `reasoning_content`) are model thinking and never reach a
page — a `content`-missing answer is treated as a miss and falls through to the
demo-failure path, not to the thinking text (owner: "I want only result of llm,
not what it thought").

## Commands

Tests run in the uv environment, from the repo root, Django's runner:

```
uv run manage.py test tutor              # full suite, browser paints included
uv run manage.py test tutor.test_tutor_session.TutorSessionTests.test_<name>
```

`uv sync` first: it builds `.venv` from `uv.lock`. `uv run` spawns the
interpreter, so an agent sandbox that denies child processes needs the
escalation for every test command (the browser tests spawn a browser too).
The paint tests drive an installed browser channel (Edge by default,
`BROWSER_CHANNEL` to override) and skip the module when the machine has
neither Edge nor Chrome, so a bare container still reports one green run.

The method label keeps its `test_` prefix in the dotted form — the runner
treats the last segment as a file import without it.
