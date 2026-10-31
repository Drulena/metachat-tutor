"""Transition row for the base state ``after_registration``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.

Spec #16 C1-2 (ADR-0006): the level axis is a parameter — this one
module replaces the three triplet modules and the seam generates the
axis: :func:`axis_pairs` keys the rows by ``(base, level)`` pair at assembly,
:func:`with_fixture_level` injects the level into the one fixture dict.
Targets spell base names, resolved by the row registry at the
row's own level (ADR-0002's mechanism built at the construction
point): ``next`` names the base states the learner goes to from here
— the analysis intro since spec #16 C1-3, the role-play intro being a
single-form state — and ``back`` is ``None``: registration is the point
of no return (spec #16 C1-8, ADR-0006 decision 2); the escape from a
mis-pick is reset, not back. Ticket #27: the row body is declared once
and :func:`axis_rows` builds the level-keyed map; the fixture is the
empty delta, because registration sits before the analysis arc.
"""

from ._registry import axis_fixture, axis_rows

#: The base state name; :func:`axis_pairs` generates the pair keys.
BASE = "after_registration"

#: The one per-base fixture dict (ADR-0006 decision 6), as a delta on
#: the shared analysis-arc shape (:func:`axis_fixture`, ticket #27):
#: the arc has not started, which is exactly the shared shape — so
#: the delta is empty.
_FIXTURE = axis_fixture()

#: The level-keyed row map, built by the shared builder (ticket #27):
#: the row body carries no level, and the assembly generates the pair
#: keys with :func:`axis_pairs` — a state name never carries the level.
ROWS: dict[str, dict] = axis_rows(
    _FIXTURE,
    next={
        "1": "analysis_intro",
        "2": "roleplay_intro",
    },
    back=None,
    nav={},
    retryable=False,
    item=None,
    phase="registration",
    accept=["1", "2"],
    effects={
        "1": [("set-item", "mode_analysis", "completed")],
        "2": [("set-item", "mode_roleplay", "completed")],
    },
    rejected="Choose the level to continue with.",
)
