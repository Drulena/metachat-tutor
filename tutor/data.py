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

# Общее количество заданий для каждого уровня (2 анализа + 9 ролей)
TOTAL_TASKS_PER_LEVEL = 11

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


def get_task_status(session: dict, task_type: str, slug: str) -> str:
    """Вернуть статус задания: 'not_started', 'in_progress', 'completed'.

    Args:
        session: Django request.session (словарь с user_data).
        task_type: 'analysis' или 'roleplay'.
        slug: Идентификатор задания.
            Для анализа: 'analysis_task_1_beginner', 'analysis_task_2_intermediate' и т.д.
            Для ролей: 'role_mediator', 'role_logical' и т.д.

    Returns:
        Статус задания.
    """
    user_data = session.get("user_data", {})
    opened_tasks = user_data.get("opened_tasks", [])
    completed_tasks = user_data.get("completed_tasks", [])

    # Проверяем, завершено ли задание
    if slug in completed_tasks:
        return "completed"

    # Проверяем, открыто ли задание (начато, но не завершено)
    if slug in opened_tasks:
        return "in_progress"

    # Дополнительно проверяем, находится ли текущее состояние в этом задании
    current_state = session.get("current_state", "")
    if task_type == "analysis":
        # Для анализа проверяем, что текущее состояние содержит slug без уровня
        # Например, slug = "analysis_task_1_beginner" -> base = "analysis_task_1"
        base = "_".join(slug.split("_")[:3])  # analysis_task_1
        if base in current_state:
            return "in_progress"
    elif task_type == "roleplay":
        # Для ролей slug уже является базовым именем (role_mediator)
        if slug in current_state:
            return "in_progress"

    return "not_started"


def get_completion_percentage(session: dict, participant_level: str) -> int:
    """Рассчитать процент завершения заданий дляданного уровня.

    Args:
        session: Django request.session.
        participant_level: Уровень участника ('beginner', 'intermediate', 'advanced').

    Returns:
        Процент от 0 до 100.
    """
    user_data = session.get("user_data", {})
    completed_tasks = user_data.get("completed_tasks", [])

    # Считаем завершённые задания для данного уровня
    completed_count = 0

    # Анализ: 2 задания (analysis_task_1, analysis_task_2) с суффиксом уровня
    for step_key in ANALYSIS_STEP_KEYS:
        task_slug = f"{step_key}_{participant_level}"
        if task_slug in completed_tasks:
            completed_count += 1

    # Роли: 9 ролей (role_*) — они не зависят от уровня
    for role_slug in ROLE_STEP_KEYS:
        if role_slug in completed_tasks:
            completed_count += 1

    percentage = int((completed_count / TOTAL_TASKS_PER_LEVEL) * 100)
    return min(percentage, 100)  # На случай ошибок округления
