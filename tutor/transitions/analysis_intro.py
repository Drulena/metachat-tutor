"""Transition row for the base state ``analysis_intro``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.

Spec #16 C1-3 (ADR-0006): the level axis is a parameter — this one
module replaces the three triplet modules and the seam generates the
axis: :func:`axis_pairs` keys the rows by ``(base, level)`` pair at assembly,
:func:`with_fixture_level` injects the level into the one fixture dict.
Targets spell base names, resolved by the row registry: ``back`` spells
the registration base state, converted in the preceding ticket (spec #16
C1-2), and ``next`` spells the analysis task base state, converted in
the following ticket (spec #16 C1-4) — the seam resolves both with the
session's level. Ticket #27: the row body is declared once and
:func:`axis_rows` builds the level-keyed map; the fixture delta is the
mode pick the learner made at registration.
"""

from ._registry import axis_fixture, axis_rows

#: The base state name; :func:`axis_pairs` generates the pair keys.
BASE = "analysis_intro"

#: The one per-base fixture dict (ADR-0006 decision 6), as a delta on
#: the shared analysis-arc shape (:func:`axis_fixture`, ticket #27):
#: past registration, the analysis mode is picked — the arc's tasks
#: have not started.
_FIXTURE = axis_fixture(mode_analysis="completed")

#: The level-keyed row map, built by the shared builder (ticket #27):
#: the row body carries no level, and the assembly generates the pair
#: keys with :func:`axis_pairs` — a state name never carries the level.
ROWS: dict[str, dict] = axis_rows(
    _FIXTURE,
    next="analysis_task_1",
    back="after_registration",
    nav={"yes": "Yes"},
    retryable=False,
    item="analysis_task_1",
    phase="analysis",
    accept=["yes"],
    effects=[("set-item", "analysis_task_1", "in_progress")],
    rejected="Please confirm you want to proceed with the analysis.",
)
