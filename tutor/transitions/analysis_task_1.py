"""Transition row for the base state ``analysis_task_1``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.

Spec #16 C1-4 (ADR-0006): the level axis is a parameter — this one
module replaces the three triplet modules and the seam generates the
axis: :func:`axis_pairs` keys the rows by ``(base, level)`` pair at assembly,
:func:`with_fixture_level` injects the level into the one fixture dict.
Targets resolve through the row registry: `back` spells the intro base
state, converted in the preceding ticket (spec #16 C1-3), and `next`
spells the feedback base state, converted in the following ticket
(spec #16 C1-5), so the seam resolves both with the session's level.
Ticket #27: the row body is declared once and :func:`axis_rows` builds
the level-keyed map; the fixture delta is the mode pick plus the task
in progress.
"""

from ._registry import axis_fixture, axis_rows

#: The base state name; :func:`axis_pairs` generates the pair keys.
BASE = "analysis_task_1"

#: The one per-base fixture dict (ADR-0006 decision 6), as a delta on
#: the shared analysis-arc shape (:func:`axis_fixture`, ticket #27):
#: the mode is picked and task 1 is in progress — coherent answers
#: land in this state.
_FIXTURE = axis_fixture(mode_analysis="completed", analysis_task_1="in_progress")

#: The level-keyed row map, built by the shared builder (ticket #27):
#: the row body carries no level, and the assembly generates the pair
#: keys with :func:`axis_pairs` — a state name never carries the level.
ROWS: dict[str, dict] = axis_rows(
    _FIXTURE,
    next="analysis_feedback_1",
    back="analysis_intro",
    nav={},
    retryable=False,
    item="analysis_task_1",
    phase="analysis",
    accept=None,
    effects=[("set-item", "analysis_task_1", "completed")],
    rejected=None,
)
