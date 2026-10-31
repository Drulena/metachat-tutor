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
per-base fixture dict.

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
