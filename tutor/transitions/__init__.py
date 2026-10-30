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

Spec #16 C1-2 (ticket #18) folds the registration triplet into one
axis module: the assembly generates its suffixed keys with
:func:`axis_rows` from a level-keyed row map, landing targets spell
base names, and fixtures are generated from one per-base dict
(:func:`with_fixture_level`).

Spec #16 C1-3 (ticket #19) folds the analysis-intro triplet into the
same shape: the intro rows generate from the axis, and the intro
back-target spells the registration base state through the seam.

Spec #16 C1-4 (ticket #20) folds the analysis-task-1 triplet into the
same shape: the task rows generate from the axis, and the task
back-target spells the intro base state through the seam.

Spec #16 C1-5 (ticket #21) folds the analysis-feedback-1 triplet into
the same shape: the retryable LLM-feedback rows generate from the axis,
its back-target spells the intro base state, and the landing target
that spells this row's own level moves to the task-2 axis (C1-6).

Spec #16 C1-6 (ticket #22) folds the analysis-task-2 triplet into the
same shape: the task rows generate from the axis, its back-target
spells the intro base state, feedback-1's landing retires its level-
named exception for the task-2 base, and the session's task-context
read names the task-2 sibling by base through the seam.

Spec #16 C1-7 (ticket #23) folds the analysis-feedback-2 triplet into
the same shape: the retryable LLM-feedback rows generate from the
axis, its back-target spells the intro base state, task-2's landing
retires its level-named exception for the feedback-2 base, and the
row's own ``next`` leaves the analysis arc for the single-form
role-play intro — one node for every level, so it needs no join.
"""

from . import (
    start,
    pretest,
    level_assessment,
    after_registration,
    analysis_intro,
    analysis_task_1,
    analysis_task_2,
    analysis_feedback_1,
    analysis_feedback_2,
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
    split_state,
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
    "split_state",
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
    # The registration axis (spec #16 C1-2, ADR-0006): rows and
    # fixtures generated from the level-keyed map by the seam —
    # suffixed keys appear in no row module.
    **axis_rows(after_registration.BASE, after_registration.ROWS),
    # The analysis-intro axis (spec #16 C1-3, ADR-0006): the suffixed
    # keys and the fixture levels come from the seam; both targets spell
    # base names — the registration state (C1-2) and the task-1 state
    # (C1-4) — resolved by the seam with the session's level.
    **axis_rows(analysis_intro.BASE, analysis_intro.ROWS),
    # The analysis-task-1 axis (spec #16 C1-4, ADR-0006): rows and fixtures
    # generated from the level-keyed map by the seam; the back target spells
    # the intro base state, the next target embeds the row level until the
    # feedback axis lands (spec #16 C1-5).
    **axis_rows(analysis_task_1.BASE, analysis_task_1.ROWS),
    # The analysis-task-2 axis (spec #16 C1-6, ADR-0006): rows and
    # fixtures generated from the level-keyed map by the seam; the back
    # target spells the intro base state, and the next target spells the
    # feedback-2 base state (spec #16 C1-7).
    **axis_rows(analysis_task_2.BASE, analysis_task_2.ROWS),
    # The analysis-feedback-1 axis (spec #16 C1-5, ADR-0006): the retryable
    # LLM-feedback rows and their fixtures generate from the level-keyed map
    # by the seam; the back target spells the intro base state, and the next
    # target spells the task-2 base state (spec #16 C1-6).
    **axis_rows(analysis_feedback_1.BASE, analysis_feedback_1.ROWS),
    # The analysis-feedback-2 axis (spec #16 C1-7, ADR-0006): the
    # retryable LLM-feedback rows and their fixtures generate from the
    # level-keyed map by the seam; the back target spells the intro base
    # state, and the next target leaves the analysis arc for the
    # single-form role-play intro.
    **axis_rows(analysis_feedback_2.BASE, analysis_feedback_2.ROWS),
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
