"""Transition row for the base state ``analysis_task_2``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.

Spec #16 C1-6 (ADR-0006): the level axis is a parameter — this one
module replaces the three triplet modules and the seam generates the
axis: :func:`axis_pairs` keys the rows by ``(base, level)`` pair at assembly,
:func:`with_fixture_level` injects the level into the one fixture
dict. `back` spells the intro base state, converted in an earlier
ticket (spec #16 C1-3), so the seam resolves it with the session's
level. `next` spells the feedback-2 base state, converted in the
following ticket (spec #16 C1-7), so the seam resolves it with the
session's level - the exception that named the feedback-2 axis by
level inside this row retires there. Ticket #27: the row body is
declared once and :func:`axis_rows` builds the level-keyed map; the
fixture delta is the finished task 1 with task 2 in progress.
"""

from ._registry import axis_fixture, axis_rows

#: The base state name; :func:`axis_pairs` generates the pair keys.
BASE = "analysis_task_2"

#: The one per-base fixture dict (ADR-0006 decision 6), as a delta on
#: the shared analysis-arc shape (:func:`axis_fixture`, ticket #27):
#: task 1 is done and task 2 is in progress — the feedback-1 row's
#: effects land the learner here.
_FIXTURE = axis_fixture(
    mode_analysis="completed",
    analysis_task_1="completed",
    analysis_task_2="in_progress",
)

#: The level-keyed row map, built by the shared builder (ticket #27):
#: the row body carries no level, and the assembly generates the pair
#: keys with :func:`axis_pairs` — a state name never carries the level.
ROWS: dict[str, dict] = axis_rows(
    _FIXTURE,
    next="analysis_feedback_2",
    back="analysis_intro",
    nav={},
    retryable=False,
    item="analysis_task_2",
    phase="analysis",
    accept=None,
    effects=[("set-item", "analysis_task_2", "completed")],
    rejected=None,
)
