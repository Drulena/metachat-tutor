"""State transition table — one data row per concrete scenario state (ticket #8).

This package is the single source of state-transition mechanics for the
scenario: 44 rows, one per scenario state except the terminal ``end``.
It is the EXPAND step of an expand–contract refactor: the legacy
routing if-chains in :mod:`tutor.tutor_session` keep running until the
migrate step, so the table must describe exactly what they do — no
behavior change.

Each row lives in its own module, one per scenario state. The row schema,
the closed sets and :func:`validate_transitions` live in
:mod:`tutor.transitions._validate` and are re-exported here.

Spec #16 C1-1 (ticket #17) adds :data:`ROW_REGISTRY` and the
:func:`row_for` seam: the table expanded 1:1 to ``(base state, level)``
pair keys per ADR-0006. The suffix-name keys above stay the storage of
record — expand only; the base-name cutover is C1-9.
"""

from . import (
    start,
    pretest,
    level_assessment,
    after_registration_beginner,
    after_registration_intermediate,
    after_registration_advanced,
    analysis_intro_beginner,
    analysis_task_1_beginner,
    analysis_task_2_beginner,
    analysis_intro_intermediate,
    analysis_task_1_intermediate,
    analysis_task_2_intermediate,
    analysis_intro_advanced,
    analysis_task_1_advanced,
    analysis_task_2_advanced,
    analysis_feedback_1_beginner,
    analysis_feedback_2_beginner,
    analysis_feedback_1_intermediate,
    analysis_feedback_2_intermediate,
    analysis_feedback_1_advanced,
    analysis_feedback_2_advanced,
    roleplay_intro,
    role_menu,
    role_mediator,
    role_logical,
    role_idea_generator,
    role_researcher,
    role_interpreter,
    role_advocate,
    role_judge,
    role_peacemaker,
    role_empath,
    roleplay_feedback_mediator,
    roleplay_feedback_logical,
    roleplay_feedback_idea_generator,
    roleplay_feedback_researcher,
    roleplay_feedback_interpreter,
    roleplay_feedback_advocate,
    roleplay_feedback_judge,
    roleplay_feedback_peacemaker,
    roleplay_feedback_empath,
    reflection,
    posttest,
    data_collection
)
from ._registry import (
    axis_rows,
    expand_rows,
    join_state,
    make_row_resolver,
    with_fixture_level,
)
from ._validate import (
    EFFECT_OPS,
    ITEM_STATUSES,
    ROW_FIELDS,
    USER_DATA_KEYS,
    USER_DATA_SOURCES,
    validate_expanded,
    validate_transitions,
)

__all__ = [
    "TRANSITIONS",
    "ROW_REGISTRY",
    "row_for",
    "axis_rows",
    "join_state",
    "with_fixture_level",
    "EFFECT_OPS",
    "ITEM_STATUSES",
    "ROW_FIELDS",
    "USER_DATA_KEYS",
    "USER_DATA_SOURCES",
    "validate_expanded",
    "validate_transitions",
]

TRANSITIONS = {
    "start": start.ROW,
    "pretest": pretest.ROW,
    "level_assessment": level_assessment.ROW,
    "after_registration_beginner": after_registration_beginner.ROW,
    "after_registration_intermediate": after_registration_intermediate.ROW,
    "after_registration_advanced": after_registration_advanced.ROW,
    "analysis_intro_beginner": analysis_intro_beginner.ROW,
    "analysis_task_1_beginner": analysis_task_1_beginner.ROW,
    "analysis_task_2_beginner": analysis_task_2_beginner.ROW,
    "analysis_intro_intermediate": analysis_intro_intermediate.ROW,
    "analysis_task_1_intermediate": analysis_task_1_intermediate.ROW,
    "analysis_task_2_intermediate": analysis_task_2_intermediate.ROW,
    "analysis_intro_advanced": analysis_intro_advanced.ROW,
    "analysis_task_1_advanced": analysis_task_1_advanced.ROW,
    "analysis_task_2_advanced": analysis_task_2_advanced.ROW,
    "analysis_feedback_1_beginner": analysis_feedback_1_beginner.ROW,
    "analysis_feedback_2_beginner": analysis_feedback_2_beginner.ROW,
    "analysis_feedback_1_intermediate": analysis_feedback_1_intermediate.ROW,
    "analysis_feedback_2_intermediate": analysis_feedback_2_intermediate.ROW,
    "analysis_feedback_1_advanced": analysis_feedback_1_advanced.ROW,
    "analysis_feedback_2_advanced": analysis_feedback_2_advanced.ROW,
    "roleplay_intro": roleplay_intro.ROW,
    "role_menu": role_menu.ROW,
    "role_mediator": role_mediator.ROW,
    "role_logical": role_logical.ROW,
    "role_idea_generator": role_idea_generator.ROW,
    "role_researcher": role_researcher.ROW,
    "role_interpreter": role_interpreter.ROW,
    "role_advocate": role_advocate.ROW,
    "role_judge": role_judge.ROW,
    "role_peacemaker": role_peacemaker.ROW,
    "role_empath": role_empath.ROW,
    "roleplay_feedback_mediator": roleplay_feedback_mediator.ROW,
    "roleplay_feedback_logical": roleplay_feedback_logical.ROW,
    "roleplay_feedback_idea_generator": roleplay_feedback_idea_generator.ROW,
    "roleplay_feedback_researcher": roleplay_feedback_researcher.ROW,
    "roleplay_feedback_interpreter": roleplay_feedback_interpreter.ROW,
    "roleplay_feedback_advocate": roleplay_feedback_advocate.ROW,
    "roleplay_feedback_judge": roleplay_feedback_judge.ROW,
    "roleplay_feedback_peacemaker": roleplay_feedback_peacemaker.ROW,
    "roleplay_feedback_empath": roleplay_feedback_empath.ROW,
    "reflection": reflection.ROW,
    "posttest": posttest.ROW,
    "data_collection": data_collection.ROW,
}

#: The table expanded 1:1 to ``(base state, level)`` pair keys
#: (ADR-0006, spec #16 C1-1): 18 analysis/registration rows on the
#: level axis plus 26 single-form ``(state, None)`` entries. Built
#: from :data:`TRANSITIONS`, which remains the storage of record.
ROW_REGISTRY = expand_rows(TRANSITIONS)

#: The row-resolution seam (spec #16 C1-1): the session module resolves
#: every row through this, never through the flat table. A suffix
#: embedded in the name wins; then ``(base, level)``; then the
#: single-form ``(base, None)``; unknown pairs resolve to ``None``.
row_for = make_row_resolver(ROW_REGISTRY)
