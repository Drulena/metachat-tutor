"""Re-export scenario data from :mod:`tutor.scenarios`.

All data originally lived here. It has been moved to ``tutor.scenarios``
for better organization.  This module re-exports every name so that
existing ``from .data import ...`` statements keep working.
"""

from .scenarios import (  # noqa: F401
    LEVELS,
    SCENARIO,
    THEORETICAL_BASE,
    TASK_VARIANTS,
    randomize_scenario,
)

# Шаги tutorials (assessment steps of the session lifecycle)
STEP_KEYS = [
    "pretest",
    "level_assessment",
    "analysis_task_1",
    "analysis_task_2",
    "role_mediator",
    "role_logical",
    "role_idea_generator",
    "role_researcher",
    "role_interpreter",
    "role_advocate",
    "role_judge",
    "role_peacemaker",
    "role_empath",
    "reflection",
    "posttest",
]
TOTAL_STEPS = len(STEP_KEYS)

# Значение кнопки в role_menu -> ключ роли (каноническое соответствие,
# используется живым приложением)
ROLE_BY_VALUE = {
    "1": "role_mediator",
    "2": "role_logical",
    "3": "role_idea_generator",
    "4": "role_researcher",
    "5": "role_interpreter",
    "6": "role_advocate",
    "7": "role_judge",
    "8": "role_peacemaker",
    "9": "role_empath",
}

# Подписи заданий для списков задач (presentation view)
ANALYSIS_LABELS = {
    "analysis_task_1": "Task 1: Softening Criticism",
    "analysis_task_2": "Task 2: Aggressive Formatting",
}
ROLE_LABELS = {
    "role_mediator": "Mediator",
    "role_logical": "Logical Expert",
    "role_idea_generator": "Idea Generator",
    "role_researcher": "Researcher",
    "role_interpreter": "Interpreter",
    "role_advocate": "Advocate",
    "role_judge": "Judge",
    "role_peacemaker": "Peacemaker",
    "role_empath": "Empath",
}

# Ключи шагов для заданий анализа и ролей
ANALYSIS_STEP_KEYS = ["analysis_task_1", "analysis_task_2"]
ROLE_STEP_KEYS = [
    "role_mediator",
    "role_logical",
    "role_idea_generator",
    "role_researcher",
    "role_interpreter",
    "role_advocate",
    "role_judge",
    "role_peacemaker",
    "role_empath",
]
