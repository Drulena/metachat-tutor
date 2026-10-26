"""State transition table — one data row per concrete scenario state (ticket #8).

This module is the single source of state-transition mechanics for the
scenario: 44 rows, every scenario state except the terminal ``end``.
It is the EXPAND step of an expand–contract refactor: the legacy
routing if-chains in :mod:`tutor.tutor_session` keep running until the
migrate step, and this table must describe exactly what they do — no
behavior change.

Each row is a plain mapping with the fields in :data:`ROW_FIELDS`:

- ``next`` — the next-state target: a plain state name — a bare axis
  base for level-axis targets, resolved by the row registry with a
  level (spec #16 C1-2) — a dict keyed by accepted input value (when
  the target depends on the answer), or ``None`` (no transition).
- ``back`` — the back target, or ``None`` at ``start``.
- ``nav`` — the system-navigation option to offer (value → label);
  the universal ``back`` option is handled separately and not listed.
- ``retryable`` — whether ``retry`` is a valid command in this state
  (the LLM-feedback states).
- ``item`` — the completion-model item this state stands for, or ``None``.
- ``phase`` — the learning phase label for progress display.
- ``accept`` — the accept gate: ``None`` (no gate — the legacy if-chain
  validates nothing in this state), a validation regex string, or the
  list of accepted literal values (option-driven states).
- ``effects`` — declarative triples (or, when ``next`` is a map, a dict
  keyed by the accepted value) drawn from the CLOSED primitive set
  :data:`EFFECT_OPS`: ``("set-item", key, status)`` and
  ``("set-user-data", key, source)`` where source is one of
  :data:`USER_DATA_SOURCES` or ``"literal:<value>"``.
- ``rejected`` — the copy this state shows when the learner's input is
  rejected, or ``None`` to fall back to the module's generic copy (ADR-0005:
  views and templates never infer or author rejection copy).
- ``fixture`` — test-only: the user data and completion-model statuses
  required to be coherently in this state
  (``{"user_data": {...}, "items": {...}}``).

No per-state handler functions live here; the table is greppable
end-to-end. :func:`validate_transitions` checks the table against the
scenario and the closed sets above.
"""

from collections.abc import Iterator

from ..data import SCENARIO
from ._registry import LEVEL_SUFFIXES, expand_rows, split_state

#: The fields every row carries, in canonical order.
ROW_FIELDS = (
    "next",
    "back",
    "nav",
    "retryable",
    "item",
    "phase",
    "accept",
    "effects",
    "rejected",
    "fixture",
)

#: The closed set of effect primitives.
EFFECT_OPS = ("set-item", "set-user-data")

#: The completion-model item statuses.
ITEM_STATUSES = ("not_started", "in_progress", "completed")

#: The user-data keys the effects may write.
USER_DATA_KEYS = (
    "user_name",
    "level",
    "pretest_scores",
    "posttest_scores",
    "current_role",
    "current_role_variant",
)

#: The non-literal effect sources (see module docstring).
USER_DATA_SOURCES = (
    "sanitized-name",
    "parsed-scores",
    "parsed-level",
    "mapped-role",
)


def validate_transitions(table: dict[str, dict] | None = None) -> list[str]:
    """Check ``table`` (default :data:`TRANSITIONS`) against the scenario.

    Returns a list of human-readable violations; an empty list means the
    table is valid. The checks mirror the ticket's acceptance criteria:
    one row per non-terminal scenario state, every next/back target a
    known state, every effect referencing a valid item or user-data key,
    and effects aligned with the ``next`` map. The expanded-table checks
    of :func:`validate_expanded` (spec #16 C1-1) run over the same
    table and their violations join the same list.
    """
    from ..tutor_session import ITEM_KEYS  # deferred: avoids a circular import

    if table is None:
        from . import TRANSITIONS  # deferred: avoids a circular import

        table = TRANSITIONS
    violations: list[str] = []
    states = set(SCENARIO["states"])
    non_terminal = states - {"end"}
    # Bare base names of the level axis: seam-resolvable targets — a
    # row spells the base and the row registry resolves it with a
    # level, so they name no scenario state (spec #16 C1-2).
    axis_names = {split_state(name)[0] for name in table if split_state(name)[1] is not None}

    for state in sorted(non_terminal - set(table)):
        violations.append(f"missing row for state {state!r}")
    for state in sorted(set(table) - non_terminal):
        violations.append(f"row for unknown state {state!r}")

    for state in sorted(set(table) & non_terminal):
        row = table[state]
        for field in ROW_FIELDS:
            if field not in row:
                violations.append(f"{state}: missing field {field!r}")
        for field in sorted(set(row) - set(ROW_FIELDS)):
            violations.append(f"{state}: unknown field {field!r}")

        next_ = row.get("next")
        targets = next_.items() if isinstance(next_, dict) else [(None, next_)]
        for value, target in targets:
            if target is not None and target not in states and target not in axis_names:
                violations.append(f"{state}: next target {target!r} is not a scenario state")

        back = row.get("back")
        if state == "start":
            if back is not None:
                violations.append(f"{state}: back must be None")
        elif back not in states and back not in axis_names:
            violations.append(f"{state}: back target {back!r} is not a scenario state")

        rejected = row.get("rejected")
        if not (rejected is None or isinstance(rejected, str)):
            violations.append(f"{state}: rejected copy {rejected!r} is not str or None")

        effects = row.get("effects")
        lists = effects.values() if isinstance(effects, dict) else [effects]
        for eff_list in lists:
            for effect in eff_list:
                if not (isinstance(effect, tuple) and len(effect) == 3):
                    violations.append(f"{state}: effect {effect!r} is not a 3-tuple")
                    continue
                op, key, third = effect
                if op == "set-item":
                    if key not in ITEM_KEYS:
                        violations.append(f"{state}: set-item key {key!r} is not a completion-model item")
                    if third not in ITEM_STATUSES:
                        violations.append(f"{state}: set-item status {third!r} is not a known status")
                elif op == "set-user-data":
                    if key not in USER_DATA_KEYS:
                        violations.append(f"{state}: set-user-data key {key!r} is not a user-data key")
                    if not (third in USER_DATA_SOURCES or third.startswith("literal:")):
                        violations.append(f"{state}: set-user-data source {third!r} is not in the closed primitive set")
                else:
                    violations.append(f"{state}: unknown effect op {op!r}")

        if isinstance(next_, dict):
            if not isinstance(effects, dict) or set(effects) != set(next_):
                violations.append(f"{state}: effects map must match the next map keys")
        else:
            if not isinstance(effects, list):
                violations.append(f"{state}: effects must be a list when next is a plain state")

    violations.extend(validate_expanded(table))
    return violations


def _row_targets(row: dict) -> Iterator[str]:
    """Every next/back target name declared by a row (map values included)."""
    next_ = row.get("next")
    if isinstance(next_, dict):
        yield from next_.values()
    elif next_ is not None:
        yield next_
    back = row.get("back")
    if back is not None:
        yield back


def _resolve_pairs(
    target: str,
    row_level: str | None,
    pairs: set[tuple[str, str | None]],
    axis_bases: set[str],
) -> list[tuple[str, str | None]]:
    """Resolve one row target to graph nodes, seen from a row at ``row_level``.

    The pair seam of the validator (spec #16 C1-2): a target with an
    embedded suffix is self-describing; a bare name resolves as
    ``(base, None)`` when that row exists, and otherwise at the row's
    own level when the base is on the axis. A single-form row
    targeting a bare axis base stands for *every* level of it — at
    runtime the session's level builds the concrete target (the
    construction point, ADR-0006). Anything unresolvable keys to
    ``(base, None)`` so the caller reports the pair with no row.
    """
    base, embedded = split_state(target)
    if embedded is not None:
        return [(base, embedded)]
    if (base, None) in pairs:
        return [(base, None)]
    if base in axis_bases:
        if row_level is not None:
            return [(base, row_level)]
        return [(base, level) for level in LEVEL_SUFFIXES]
    return [(base, None)]


def validate_expanded(table: dict[str, dict] | None = None) -> list[str]:
    """Check the ``(base state, level)`` expansion of ``table`` (#17).

    Spec #16 C1-1 expands the suffix-named table 1:1 to pair keys
    (ADR-0006): 44 graph nodes — 18 axis pairs plus 26 single-form
    ``(state, None)`` entries. Three checks run over the whole
    expansion:

    - graph closure: every next/back target resolves to a pair that
      has a row (``("end", None)`` is the terminal exception). Bare
      axis-base targets resolve at the row's own level; from a
      single-form row they stand for every level of the axis
      (:func:`_resolve_pairs`, spec #16 C1-2);
    - reachability: every pair is reachable from ``("start", None)``
      along next/back edges;
    - level coverage: a base carrying any axis row must carry every
      :data:`~tutor.transitions._registry.LEVEL_SUFFIXES` level, so a
      row module missing an axis level is rejected.

    Returns human-readable violations prefixed ``expanded:``; an empty
    list means the expansion is sound.
    """
    if table is None:
        from . import TRANSITIONS  # deferred: avoids a circular import

        table = TRANSITIONS
    try:
        pairs = expand_rows(table)
    except ValueError as exc:
        return [f"expanded: {exc}"]

    violations: list[str] = []
    terminal = ("end", None)
    axis_bases = {base for base, level in pairs if level is not None}

    for state in sorted(table):
        row_level = split_state(state)[1]
        for target in _row_targets(table[state]):
            for pair in _resolve_pairs(target, row_level, pairs, axis_bases):
                if pair not in pairs and pair != terminal:
                    violations.append(
                        f"expanded: {state!r}: target {target!r} resolves to "
                        f"pair {pair!r} with no row"
                    )

    axis_levels: dict[str, set[str]] = {}
    for base, level in pairs:
        if level is not None:
            axis_levels.setdefault(base, set()).add(level)
    for base in sorted(axis_levels):
        for level in LEVEL_SUFFIXES:
            if level not in axis_levels[base]:
                violations.append(
                    f"expanded: row module {base!r} misses axis level {level!r}"
                )

    start = ("start", None)
    if start in pairs:
        seen = {start}
        queue = [start]
        while queue:
            node = queue.pop()
            for target in _row_targets(pairs[node]):
                for pair in _resolve_pairs(target, node[1], pairs, axis_bases):
                    if pair in pairs and pair not in seen:
                        seen.add(pair)
                        queue.append(pair)
        for pair in sorted(set(pairs) - seen):
            violations.append(f"expanded: pair {pair!r} is unreachable from {start!r}")

    return violations
