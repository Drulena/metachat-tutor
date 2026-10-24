"""State transition table — one data row per concrete scenario state (ticket #8).

This module is the single source of state-transition mechanics for the
scenario: 44 rows, every scenario state except the terminal ``end``.
It is the EXPAND step of an expand–contract refactor: the legacy
routing if-chains in :mod:`tutor.tutor_session` keep running until the
migrate step, and this table must describe exactly what they do — no
behavior change.

Each row is a plain mapping with the fields in :data:`ROW_FIELDS`:

- ``next`` — the next-state target: a plain state name, a dict keyed by
  accepted input value (when the target depends on the answer), or
  ``None`` (no transition).
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

from ..data import SCENARIO

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
    and effects aligned with the ``next`` map.
    """
    from ..tutor_session import ITEM_KEYS  # deferred: avoids a circular import

    if table is None:
        from . import TRANSITIONS  # deferred: avoids a circular import

        table = TRANSITIONS
    violations: list[str] = []
    states = set(SCENARIO["states"])
    non_terminal = states - {"end"}

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
            if target is not None and target not in states:
                violations.append(f"{state}: next target {target!r} is not a scenario state")

        back = row.get("back")
        if state == "start":
            if back is not None:
                violations.append(f"{state}: back must be None")
        elif back not in states:
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

    return violations
