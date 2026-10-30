"""State transition table — one data row per graph node (ticket #8, #25).

This module is the single source of state-transition mechanics and the
schema over the ``(base state, level)`` row registry (spec #16 C1-9,
ticket #25): 44 pairs — 18 axis pairs on the level axis plus 26
single-form ``(state, None)`` entries. The registry IS the storage:
suffix-name keys are retired (ADR-0006).

Each row is a plain mapping with the fields in :data:`ROW_FIELDS`:

- ``next`` — the next-state target: a scenario state base name,
  resolved by the row registry with a level through the seam (spec
  #16 C1-9: every axis target spells the base, never a suffix) — a
  dict keyed by accepted input value (when the target depends on the
  answer), or ``None`` (no transition).
- ``back`` — the back target, or ``None`` at ``start`` and at the
  registration axis (the point of no return, spec #16 C1-8).
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

No per-state handler functions live here; the registry is greppable
end-to-end. :func:`validate_transitions` checks the registry against
the scenario and the closed sets above; :func:`axis_copy_violations`
pins that the scenario carries every axis copy, byte-identical to the
scenario modules (spec #16 C1-9 AC2: the copy survives the cutover).
"""

from collections.abc import Iterator

from ..data import SCENARIO
from ._registry import LEVEL_SUFFIXES

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

#: The base states on the level axis (spec #16 C1-2..C1-7, ADR-0006).
AXIS_BASES = (
    "after_registration",
    "analysis_intro",
    "analysis_task_1",
    "analysis_task_2",
    "analysis_feedback_1",
    "analysis_feedback_2",
)


def _ends_with_level(name: str) -> tuple[str, str | None]:
    """Split a name spelling the level as a suffix (the retired shape).

    The cutover retires suffixed spellings; this only exists so the
    validator can report a target that (mis)spells one (spec #16 C1-9:
    a suffixed literal must never enter the graph).
    """
    for suffix in LEVEL_SUFFIXES:
        if name.endswith(f"_{suffix}"):
            return name[: -len(suffix) - 1], suffix
    return name, None


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


def _resolve_target(
    target: str,
    row_level: str | None,
    pairs: set[tuple[str, str | None]],
    axis_bases: set[str],
) -> list[tuple[str, str | None]]:
    """Resolve one row target to graph nodes, seen from a row at ``row_level``.

    A target spells a base name (spec #16 C1-9): it resolves as
    ``(base, None)`` when that row exists, and otherwise at the row's
    own level when the base is on the axis. A single-form row
    targeting a bare axis base stands for *every* level of it — at
    runtime the session's level builds the concrete target (the
    construction point, ADR-0006). A target that (mis)spells a level
    suffix is self-describing so the caller reports the pair with no
    row; anything else unresolvable keys to ``(base, None)``.
    """
    base, embedded = _ends_with_level(target)
    if embedded is not None:
        return [(base, embedded)]
    if (base, None) in pairs:
        return [(base, None)]
    if base in axis_bases:
        if row_level is not None:
            return [(base, row_level)]
        return [(base, level) for level in LEVEL_SUFFIXES]
    return [(base, None)]


def _pair_sort(pair: tuple[str, str | None]) -> tuple[str, str]:
    """Total order over pair keys (the level slot may be ``None``)."""
    return (pair[0], pair[1] or "")


def validate_transitions(
    table: dict[tuple[str, str | None], dict] | None = None,
) -> list[str]:
    """Check ``table`` (default :data:`ROW_REGISTRY`) against the scenario.

    Returns a list of human-readable violations; an empty list means the
    registry is valid. The checks mirror the ticket's acceptance
    criteria: one row per non-terminal scenario state (as a pair — the
    axis covers every level of its base), every next/back target a
    known base state spelled by base name, every effect referencing a
    valid item or user-data key, and effects aligned with the ``next``
    map. The graph checks (closure, reachability from
    ``("start", None)``, level coverage) run over the same pairs and
    their violations — prefixed ``expanded:`` — join the same list.
    """
    from ..tutor_session import ITEM_KEYS  # deferred: avoids a circular import

    if table is None:
        from . import ROW_REGISTRY  # deferred: avoids a circular import

        table = ROW_REGISTRY
    violations: list[str] = []
    states = set(SCENARIO["states"])
    non_terminal = states - {"end"}
    pairs = set(table)
    axis_bases = {base for base, level in pairs if level is not None}

    bases_with_rows = {base for base, _ in pairs}
    for base in sorted(non_terminal - bases_with_rows):
        violations.append(f"missing row for state {base!r}")
    for base in sorted(bases_with_rows - states):
        violations.append(f"row for unknown state {base!r}")

    for pair in sorted(pairs, key=_pair_sort):
        base, level = pair
        if pair not in table:
            continue
        if base not in non_terminal:
            continue
        row = table[pair]
        for field in ROW_FIELDS:
            if field not in row:
                violations.append(f"{pair}: missing field {field!r}")
        for field in sorted(set(row) - set(ROW_FIELDS)):
            violations.append(f"{pair}: unknown field {field!r}")

        next_ = row.get("next")
        targets = next_.items() if isinstance(next_, dict) else [(None, next_)]
        for value, target in targets:
            if target is not None and target not in states:
                violations.append(
                    f"{pair}: next target {target!r} is not a scenario state"
                )

        back = row.get("back")
        if base == "start":
            if back is not None:
                violations.append(f"{pair}: back must be None")
        elif back is None:
            # The registration axis declares ``back: None`` — the point of
            # no return (spec #16 C1-8, ADR-0006 decision 2); every other
            # row must name a back target.
            if base != "after_registration":
                violations.append(
                    f"{pair}: back target None is allowed only at start "
                    "and the registration axis"
                )
        elif back not in states:
            violations.append(
                f"{pair}: back target {back!r} is not a scenario state"
            )

        rejected = row.get("rejected")
        if not (rejected is None or isinstance(rejected, str)):
            violations.append(
                f"{pair}: rejected copy {rejected!r} is not str or None"
            )

        effects = row.get("effects")
        lists = effects.values() if isinstance(effects, dict) else [effects]
        for eff_list in lists:
            for effect in eff_list:
                if not (isinstance(effect, tuple) and len(effect) == 3):
                    violations.append(f"{pair}: effect {effect!r} is not a 3-tuple")
                    continue
                op, key, third = effect
                if op == "set-item":
                    if key not in ITEM_KEYS:
                        violations.append(
                            f"{pair}: set-item key {key!r} is not a completion-model item"
                        )
                    if third not in ITEM_STATUSES:
                        violations.append(
                            f"{pair}: set-item status {third!r} is not a known status"
                        )
                elif op == "set-user-data":
                    if key not in USER_DATA_KEYS:
                        violations.append(
                            f"{pair}: set-user-data key {key!r} is not a user-data key"
                        )
                    if not (third in USER_DATA_SOURCES or third.startswith("literal:")):
                        violations.append(
                            f"{pair}: set-user-data source {third!r} is not in the "
                            "closed primitive set"
                        )
                else:
                    violations.append(f"{pair}: unknown effect op {op!r}")

        if isinstance(next_, dict):
            if not isinstance(effects, dict) or set(effects) != set(next_):
                violations.append(
                    f"{pair}: effects map must match the next map keys"
                )
        else:
            if not isinstance(effects, list):
                violations.append(
                    f"{pair}: effects must be a list when next is a plain state"
                )

    violations.extend(_graph_checks(table, pairs, axis_bases))
    violations.extend(axis_copy_violations())
    return violations


def _graph_checks(
    table: dict[tuple[str, str | None], dict],
    pairs: set[tuple[str, str | None]],
    axis_bases: set[str],
) -> list[str]:
    """Closure, reachability and level coverage over the pair registry.

    Spec #16 C1-1 raised these checks over the expand; C1-9 folds them
    into the single registry walk, keeping the ``expanded:`` message
    prefix. Three checks run over the whole pair set:

    - graph closure: every next/back target resolves to a pair that
      has a row (``("end", None)`` is the terminal exception);
    - reachability: every pair is reachable from ``("start", None)``
      along next/back edges;
    - level coverage: a base carrying any axis row must carry every
      :data:`~tutor.transitions._registry.LEVEL_SUFFIXES` level, so a
      row module missing an axis level is rejected.
    """
    violations: list[str] = []
    terminal = ("end", None)

    for pair in sorted(pairs, key=_pair_sort):
        for target in _row_targets(table[pair]):
            for node in _resolve_target(target, pair[1], pairs, axis_bases):
                if node not in pairs and node != terminal:
                    violations.append(
                        f"expanded: {pair!r}: target {target!r} resolves to "
                        f"pair {node!r} with no row"
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
            for target in _row_targets(table[node]):
                for pair in _resolve_target(target, node[1], pairs, axis_bases):
                    if pair in pairs and pair not in seen:
                        seen.add(pair)
                        queue.append(pair)
        for pair in sorted(set(pairs) - seen, key=_pair_sort):
            violations.append(
                f"expanded: pair {pair!r} is unreachable from {start!r}"
            )

    return violations


def axis_copy_violations(
    states: dict[str, dict] | None = None,
    axis_entries: dict[str, object] | None = None,
) -> list[str]:
    """Check the scenario's axis copy against the scenario modules (C1-9).

    The scenario keys its states by base name; an axis entry is the
    scenario module's level-keyed copy map spelled under the base
    name, and the construction point flattens one ``(base, level)``
    entry into the learner-facing shape. This check pins that every
    axis entry carries every level's copy — byte-identical to the
    module (spec #16 C1-9 AC2: the copy survives the cutover) — and
    that single-form entries stay flat. Violations are prefixed
    ``scenario:``; an empty list means the copy is carried exactly.
    """
    from .. import scenarios as scenario_modules  # deferred: import cycle

    if states is None:
        states = SCENARIO["states"]
    if axis_entries is None:
        axis_entries = {base: getattr(scenario_modules, base) for base in AXIS_BASES}

    violations: list[str] = []
    for base in sorted(axis_entries):
        state_module = axis_entries[base]
        entry = states.get(base)
        if entry is None:
            violations.append(f"scenario: axis base {base!r} missing from the states")
            continue
        if "message" in entry:
            violations.append(
                f"scenario: axis base {base!r} carries a flattened single-form entry"
            )
            continue
        for level in LEVEL_SUFFIXES:
            want = getattr(state_module, "STATE").get(level)
            got = entry.get(level)
            if want is None:
                violations.append(
                    f"scenario: axis module {base!r} misses level {level!r}"
                )
                continue
            if got is None:
                violations.append(f"scenario: axis base {base!r} misses level {level!r}")
                continue
            for field, text in want.items():
                if got.get(field) != text:
                    violations.append(
                        f"scenario: axis entry {base!r} level {level!r} field "
                        f"{field!r} differs from the scenario module's copy"
                    )
    return violations
