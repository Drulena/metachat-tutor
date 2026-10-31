"""Transition row for the base state ``analysis_feedback_2``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.

Spec #16 C1-7 (ADR-0006): the level axis is a parameter — this one
module replaces the three triplet modules and the seam generates the
axis: :func:`axis_pairs` keys the rows by ``(base, level)`` pair at assembly,
:func:`with_fixture_level` injects the level into the one fixture
dict. This is the retryable LLM-feedback row that closes the analysis
arc: the copy it renders, the :func:`with_fixture_level` fixture it
seeds and the ``retry`` offer all follow from the level the seam
resolved, so the row body itself carries no level. `back` spells the
intro base state, converted in an earlier ticket (spec #16 C1-3), so
the seam resolves it with the session's level. `next` leaves the
analysis arc for the role-play intro: a single-form state, the same
node for every level, so it needs no join. Ticket #27: the row body
is declared once and :func:`axis_rows` builds the level-keyed map; the
fixture delta is the arc fully done — this row's effects close it.
"""

from ._registry import axis_fixture, axis_rows

#: The base state name; :func:`axis_pairs` generates the pair keys.
BASE = "analysis_feedback_2"

#: The one per-base fixture dict (ADR-0006 decision 6), as a delta on
#: the shared analysis-arc shape (:func:`axis_fixture`, ticket #27):
#: both tasks are done — the state the arc's last answer lands in,
#: before this row's effect closes task 2 for good.
_FIXTURE = axis_fixture(
    mode_analysis="completed",
    analysis_task_1="completed",
    analysis_task_2="completed",
)

#: The level-keyed row map, built by the shared builder (ticket #27):
#: the row body carries no level, and the assembly generates the pair
#: keys with :func:`axis_pairs` — a state name never carries the level.
ROWS: dict[str, dict] = axis_rows(
    _FIXTURE,
    next="roleplay_intro",
    back="analysis_intro",
    nav={"next": "Next"},
    retryable=True,
    item="analysis_task_2",
    phase="analysis",
    accept=["next"],
    effects=[("set-item", "analysis_task_2", "completed")],
    rejected=None,
)
