"""The ``(base state, level)`` row registry — the row-resolution seam.

Spec #16 C1-1 (ticket #17), per ADR-0006: the level axis is a
parameter of row lookup. The flat :data:`~tutor.transitions.TRANSITIONS`
table keys its 44 rows by scenario state name, which bakes the axis
into the suffix of 18 analysis/registration names. This module expands
that table 1:1 into a registry keyed ``(base state, level)``: suffixed
names split into base + axis level, single-form names key as
``(base, None)``.

This is the EXPAND step of expand-contract: the suffix-name keys
remain the storage of record, the pair keys are built alongside them,
and nothing migrates. The base-name cutover of the scenario names is
C1-9. The prefix-match back repair retired in C1-8 (ticket #24):
back targets are true predecessors; a bare base name resolves with
the session's level at this seam.

Spec #16 C1-2 (ticket #18) adds the generation half of the same seam
algebra: :func:`join_state` joins a pair into a suffixed name,
:func:`axis_rows` generates one base's three suffixed rows from a
single level-keyed map, and :func:`with_fixture_level` injects the
level into one per-base fixture dict (ADR-0006 decisions 5-6).

:func:`make_row_resolver` builds the ``row_for(state, level)`` seam,
preserving today's resolution behavior exactly:

1. a level suffix embedded in the state name wins — history entries
   are self-describing and resolve to the row they were created in,
   whatever the session's registered level is now (the mid-session
   level change is not reachable; spec #16 C1-3 pins this);
2. a bare base name plus the session's level resolves as
   ``(base, level)``;
3. single-form states resolve as ``(base, None)``;
4. an unknown pair resolves to ``None``, like :meth:`dict.get`.
"""

import copy
from collections.abc import Callable, Mapping
from typing import Any

from ..data import LEVELS

#: The level-axis values, in scenario order: the suffixes that carry it.
LEVEL_SUFFIXES: tuple[str, ...] = tuple(LEVELS)

#: One row of the transition table (schema: :mod:`._validate`).
Row = dict[str, Any]


def split_state(name: str) -> tuple[str, str | None]:
    """Split a state name into its registry pair key.

    ``"analysis_task_1_beginner"`` → ``("analysis_task_1", "beginner")``;
    a single-form name like ``"pretest"`` → ``("pretest", None)``.
    """
    for suffix in LEVEL_SUFFIXES:
        if name.endswith(f"_{suffix}"):
            return name[: -len(suffix) - 1], suffix
    return name, None


def join_state(base: str, level: str) -> str:
    """Join a registry pair into its suffixed state name.

    Inverse of :func:`split_state` for axis levels:
    ``("analysis_intro", "beginner")`` → ``"analysis_intro_beginner"``.
    """
    return f"{base}_{level}"


def expand_rows(table: Mapping[str, Row]) -> dict[tuple[str, str | None], Row]:
    """Expand a suffix-named row table to ``(base, level)`` pair keys.

    Raises ``ValueError`` when two state names collapse onto one pair:
    the registry must stay a faithful 1:1 view of the table.
    """
    pairs: dict[tuple[str, str | None], Row] = {}
    source: dict[tuple[str, str | None], str] = {}
    for name, row in table.items():
        pair = split_state(name)
        if pair in pairs:
            raise ValueError(
                f"pair key {pair!r} claimed by both {source[pair]!r} and {name!r}"
            )
        pairs[pair] = row
        source[pair] = name
    return pairs


def axis_rows(base: str, rows_by_level: Mapping[str, Row]) -> dict[str, Row]:
    """Generate one base state's suffixed-key rows from a level-keyed map.

    The seam generating the level axis (ADR-0006, spec #16 C1-2): one
    module spells a row per level once, and the assembly keys them
    ``f"{base}_{level}"`` in axis order — the suffixed names appear in
    no row module. Raises ``ValueError`` when the map is not keyed by
    exactly the axis levels: a partial axis is a bug, not a row set.
    """
    if set(rows_by_level) != set(LEVEL_SUFFIXES):
        raise ValueError(
            f"axis map for {base!r} must cover exactly {LEVEL_SUFFIXES}, "
            f"got {tuple(sorted(rows_by_level))}"
        )
    return {join_state(base, level): rows_by_level[level] for level in LEVEL_SUFFIXES}


def with_fixture_level(fixture: Mapping[str, Any], level: str) -> Row:
    """Copy a per-base fixture dict, injecting the axis level.

    Spec #16 C1-2 (ADR-0006 decision 6): a base state carries one
    fixture dict; the seam generates the axis by setting
    ``user_data["level"]`` per level. The assembly keys the generated
    fixture under the suffixed state name, keeping every fixture
    self-coherent (fixture level == state-name suffix).
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
    self-describing suffixes and single-form states resolve.
    """

    def row_for(state: str, level: str | None = None) -> Row | None:
        base, embedded = split_state(state)
        if embedded is not None:
            return registry.get((base, embedded))
        row = registry.get((base, level))
        if row is None and level is not None:
            row = registry.get((base, None))
        return row

    return row_for
