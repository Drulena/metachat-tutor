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

## Shared test constants live once

Module strings pinned by tests — the generic rejection copy
(`GENERIC_REJECTION`), the role-menu copy (`ROLE_MENU_COPY`), the drive
sequence (`ROLE_MENU_INPUTS`) — are defined once, in
`tutor/test_tutor_session.py`, and imported by the other test modules
(`test_options.py`, `test_views.py`). A string copy pinned twice drifts the
first time the string changes; the shared pin catches every consumer at once.

## Commands

Tests run on the project venv, from the repo root, Django's runner:

```
.\venv\Scripts\python.exe manage.py test tutor          # full suite
.\venv\Scripts\python.exe manage.py test tutor.test_tutor_session.TutorSessionTests.test_<name>
```

The method label keeps its `test_` prefix in the dotted form — the runner
treats the last segment as a file import without it.
