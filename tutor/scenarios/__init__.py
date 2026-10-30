"""Scenario data and randomization logic for MetaChat Tutor.

This module contains the core scenario definitions (SCENARIO, TASK_VARIANTS,
LEVELS, THEORETICAL_BASE) and the ``randomize_scenario`` function that
substitutes random variant data into a deep copy of the scenario template.
"""

from __future__ import annotations

from typing import Any

from . import (
    start,
    pretest,
    level_assessment,
    after_registration,
    analysis_intro,
    analysis_task_1,
    analysis_task_2_beginner,
    analysis_task_2_intermediate,
    analysis_feedback_1,
    analysis_task_2_advanced,
    analysis_feedback_2_advanced,
    analysis_feedback_2_beginner,
    analysis_feedback_2_intermediate,
    roleplay_intro,
    role_menu,
    role_mediator,
    roleplay_feedback_mediator,
    role_logical,
    roleplay_feedback_logical,
    role_idea_generator,
    roleplay_feedback_idea_generator,
    role_researcher,
    roleplay_feedback_researcher,
    role_interpreter,
    roleplay_feedback_interpreter,
    role_advocate,
    roleplay_feedback_advocate,
    role_judge,
    roleplay_feedback_judge,
    role_peacemaker,
    roleplay_feedback_peacemaker,
    role_empath,
    roleplay_feedback_empath,
    reflection,
    posttest,
    data_collection,
    end
)
from .common import (
    BOT_NAME,
    LEVELS,
    ROLEPLAY_ERROR_DEFAULT,
    ROLEPLAY_ERROR_TEMPLATES,
    ROLE_STATE_KEYS,
    THEORETICAL_BASE,
    WELCOME_MESSAGE,
)
from .randomize import randomize_scenario
from .tasks import TASK_VARIANTS

__all__ = [
    "SCENARIO",
    "LEVELS",
    "TASK_VARIANTS",
    "THEORETICAL_BASE",
    "ROLE_STATE_KEYS",
    "ROLEPLAY_ERROR_TEMPLATES",
    "ROLEPLAY_ERROR_DEFAULT",
    "randomize_scenario",
]

SCENARIO: dict[str, Any] = {
    "bot_name": BOT_NAME,
    "welcome_message": WELCOME_MESSAGE,
    "states": {
        "start": start.STATE,
        "pretest": pretest.STATE,
        "level_assessment": level_assessment.STATE,
        # The registration axis (spec #16 C1-2, ADR-0006): the suffixed
        # keys are generated from the level-keyed map — the axis is
        # spelled once, in this comprehension, not in three module lines.
        **{
            f"after_registration_{level}": after_registration.STATE[level]
            for level in LEVELS
        },
        # The intro axis (spec #16 C1-3, ADR-0006): the suffixed scenario
        # keys are generated from the level-keyed map, spelled once here.
        **{
            f"analysis_intro_{level}": analysis_intro.STATE[level]
            for level in LEVELS
        },
        # The task-1 axis (spec #16 C1-4, ADR-0006): the suffixed scenario
        # keys are generated from the level-keyed map, spelled once here.
        **{
            f"analysis_task_1_{level}": analysis_task_1.STATE[level]
            for level in LEVELS
        },
        # The feedback-1 axis (spec #16 C1-5, ADR-0006): the suffixed
        # scenario keys are generated from the level-keyed map, spelled
        # once here.
        **{
            f"analysis_feedback_1_{level}": analysis_feedback_1.STATE[level]
            for level in LEVELS
        },
        "analysis_task_2_beginner": analysis_task_2_beginner.STATE,
        "analysis_task_2_intermediate": analysis_task_2_intermediate.STATE,
        "analysis_task_2_advanced": analysis_task_2_advanced.STATE,
        "analysis_feedback_2_advanced": analysis_feedback_2_advanced.STATE,
        "analysis_feedback_2_beginner": analysis_feedback_2_beginner.STATE,
        "analysis_feedback_2_intermediate": analysis_feedback_2_intermediate.STATE,
        "roleplay_intro": roleplay_intro.STATE,
        "role_menu": role_menu.STATE,
        "role_mediator": role_mediator.STATE,
        "roleplay_feedback_mediator": roleplay_feedback_mediator.STATE,
        "role_logical": role_logical.STATE,
        "roleplay_feedback_logical": roleplay_feedback_logical.STATE,
        "role_idea_generator": role_idea_generator.STATE,
        "roleplay_feedback_idea_generator": roleplay_feedback_idea_generator.STATE,
        "role_researcher": role_researcher.STATE,
        "roleplay_feedback_researcher": roleplay_feedback_researcher.STATE,
        "role_interpreter": role_interpreter.STATE,
        "roleplay_feedback_interpreter": roleplay_feedback_interpreter.STATE,
        "role_advocate": role_advocate.STATE,
        "roleplay_feedback_advocate": roleplay_feedback_advocate.STATE,
        "role_judge": role_judge.STATE,
        "roleplay_feedback_judge": roleplay_feedback_judge.STATE,
        "role_peacemaker": role_peacemaker.STATE,
        "roleplay_feedback_peacemaker": roleplay_feedback_peacemaker.STATE,
        "role_empath": role_empath.STATE,
        "roleplay_feedback_empath": roleplay_feedback_empath.STATE,
        "reflection": reflection.STATE,
        "posttest": posttest.STATE,
        "data_collection": data_collection.STATE,
        "end": end.STATE,
    },
}
