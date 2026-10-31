"""The ``(base state, level)`` row registry — the row-resolution seam.

Spec #16 C1-1 (ticket #17), per ADR-0006: the level axis is a
parameter of row lookup. Spec #16 C1-9 (ticket #25) completes the
expand–contract: the registry IS the row storage, keyed by pair —
suffixed state names no longer exist anywhere. The expand step of
C1-1 built the pair view alongside the suffix-name keys; this ticket
deletes the suffix-name storage, the expand step (:func:`expand_rows`),
the join (:func:`join_state`), the flat-table row generator
(:func:`axis_rows`) and the suffix-preferring resolution rule.

The algebra of the seam (ADR-0006 decisions 5-6): one module spells a
base state once — an axis module keys its rows by bare level, single-
form modules carry one row — and the assembly keys them by pair
directly. :func:`axis_pairs` validates the axis covers exactly the
level axis; :func:`with_fixture_level` injects the level into one
per-base fixture dict. Ticket #27 adds the shared builder behind that
algebra: :func:`axis_rows` turns one declaration of the level-
independent row fields plus a fixture into the level-keyed row map,
and :func:`axis_fixture` spells a base's fixture as a delta on the
shared analysis-arc shape.

:func:`make_row_resolver` builds the ``row_for(state, level)`` seam:

1. a bare base name plus the session's level resolves as
   ``(base, level)``;
2. single-form states resolve as ``(base, None)`` — the fallback
   carries an unregistered level (a learner mid-registration) onto
   the single-form rows;
3. an unknown pair resolves to ``None``, like :meth:`dict.get`.

Every state a session, a turn or a row map spells is a base name;
the level travels in its own field, never in the name.
"""

import copy
from collections.abc import Callable, Mapping
from typing import Any

from ..data import LEVELS

#: The level-axis values, in scenario order: the levels the axis keys carry.
LEVEL_KEYS: tuple[str, ...] = tuple(LEVELS)

#: One row of the transition table (schema: :mod:`._validate`).
Row = dict[str, Any]


def axis_pairs(base: str, rows_by_level: Mapping[str, Row]) -> dict[tuple[str, str], Row]:
    """Generate one base state's ``(base, level)`` rows from a level-keyed map.

    The seam generating the level axis (ADR-0006, spec #16 C1-2, keyed
    by pair per C1-9): one module spells a row per level once, and the
    assembly keys them by pair in axis order — the level is a value in
    the pair, never a suffix inside a state name. Raises ``ValueError``
    when the map is not keyed by exactly the axis levels: a partial
    axis is a bug, not a row set.
    """
    if set(rows_by_level) != set(LEVEL_KEYS):
        raise ValueError(
            f"axis map for {base!r} must cover exactly {LEVEL_KEYS}, "
            f"got {tuple(sorted(rows_by_level))}"
        )
    return {(base, level): rows_by_level[level] for level in LEVEL_KEYS}


def with_fixture_level(fixture: Mapping[str, Any], level: str) -> Row:
    """Copy a per-base fixture dict, injecting the axis level.

    Spec #16 C1-2 (ADR-0006 decision 6): a base state carries one
    fixture dict; the seam generates the axis by setting
    ``user_data["level"]`` per level. The assembly keys the generated
    fixture under the ``(base, level)`` pair, keeping every fixture
    self-coherent (fixture level == pair level).
    """
    generated = copy.deepcopy(dict(fixture))
    generated["user_data"]["level"] = level
    return generated


#: The shared shape of the axis fixtures (ticket #27), spelled once:
#: a learner at the start of the analysis arc — the assessment pair
#: done, every task, role and mode item ``not_started``, the probe
#: scores fixed. This is the registration shape: registration sits
#: before the arc, so its fixture is the empty delta (:func:`axis_fixture`
#: with no statuses); every arc base spells its progress as the delta.
#: :func:`axis_fixture` expresses each axis base against this shape.
_AXIS_FIXTURE_BASE: Row = {
    "user_data": {
        "user_name": "Test Learner",
        "level": None,
        "pretest_scores": [3, 4, 5],
        "posttest_scores": None,
        "current_role": None,
        "current_role_variant": None,
    },
    "items": {
        "pretest": "completed",
        "level_assessment": "completed",
        "analysis_task_1": "not_started",
        "analysis_task_2": "not_started",
        "role_mediator": "not_started",
        "role_logical": "not_started",
        "role_idea_generator": "not_started",
        "role_researcher": "not_started",
        "role_interpreter": "not_started",
        "role_advocate": "not_started",
        "role_judge": "not_started",
        "role_peacemaker": "not_started",
        "role_empath": "not_started",
        "reflection": "not_started",
        "posttest": "not_started",
        "mode_analysis": "not_started",
        "mode_roleplay": "not_started",
    },
}


def axis_fixture(**item_statuses: str) -> Row:
    """Fresh per-base axis fixture: the shared shape, delta-applied.

    ADR-0006 decision 6 keeps one fixture dict per base state; ticket
    #27 expresses the between-base delta as parameters: the shape of
    the whole analysis arc lives in :data:`_AXIS_FIXTURE_BASE`, and a
    base state names the item statuses that place it coherently *in*
    that state (past registration: ``mode_analysis="completed"``;
    mid-task: that task ``"in_progress"``). The seam injects the axis
    level per row (:func:`with_fixture_level`).
    """
    fixture = copy.deepcopy(_AXIS_FIXTURE_BASE)
    fixture["items"].update(item_statuses)
    return fixture


def axis_rows(fixture: Mapping[str, Any], **fields: Any) -> dict[str, Row]:
    """Build a base state's level-keyed rows from its level-independent fields.

    Ticket #27: the comprehension every axis module repeated lives
    here — a module declares its targets, effects and the rest of the
    row body once, and the builder clones the per-base fixture across
    the axis (:func:`with_fixture_level`), so a state name never
    carries the level. Field order follows the declaration order,
    canonical per :data:`~tutor.transitions._validate.ROW_FIELDS`,
    fixture slot last; the assembly keys the map by pair with
    :func:`axis_pairs`.
    """
    return {
        level: dict(fields, fixture=with_fixture_level(fixture, level))
        for level in LEVEL_KEYS
    }


def make_row_resolver(
    registry: Mapping[tuple[str, str | None], Row],
) -> Callable[[str, str | None], Row | None]:
    """Build the ``row_for(state, level)`` seam over ``registry``.

    Resolution order is documented in the module docstring; ``level``
    may be ``None`` (no registered level), in which case only
    single-form states resolve.
    """

    def row_for(state: str, level: str | None = None) -> Row | None:
        row = registry.get((state, level))
        if row is None and level is not None:
            row = registry.get((state, None))
        return row

    return row_for
