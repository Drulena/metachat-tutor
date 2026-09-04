"""State machine for the MetaChat Tutor chatbot.

Handles all state transitions, input validation, LLM feedback injection,
and chat history management for the Django session-based tutor.
"""

import logging
import re
import uuid
from datetime import datetime
from typing import Any, Optional

from .llm import get_llm_feedback

logger = logging.getLogger(__name__)

_MAX_INPUT_LENGTH = 5000
_MAX_NAME_LENGTH = 50

# Шаги tutorials (steps of the tutorial)
TOTAL_STEPS = 15
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


def _mark_step_completed(request: Any, step_key: str) -> None:
    """Отметить шаг как завершённый."""
    user_data = request.session["user_data"]
    completed_steps = user_data.setdefault("completed_steps", [])
    if step_key not in completed_steps:
        completed_steps.append(step_key)
        request.session.modified = True


def calculate_progress(request: Any) -> dict:
    """Рассчитать прогресс выполнения.

    Возвращает словарь с данными прогресса для шаблона:
    - status_badge: 'completed', 'in_progress' или 'not_started'
    - percentage: 0-100
    - current_step: номер текущего шага (1-based) или 0
    - total_steps: общее количество шагов
    - completed_steps_count: количество завершённых шагов
    - analysis_progress: прогресс по заданиям анализа
    - roleplay_progress: прогресс по ролям
    """
    user_data = request.session["user_data"]
    completed_steps = user_data.get("completed_steps", [])
    completed_count = len(completed_steps)
    percentage = int((completed_count / TOTAL_STEPS) * 100) if TOTAL_STEPS > 0 else 0

    # Определить текущий шаг (находится в процессе)
    current_state = request.session.get("current_state", "start")

    # Расширенный маппинг состояний к шагам (включает промежуточные состояния)
    state_to_step = {
        "start": None,
        "pretest": "pretest",
        "level_assessment": "level_assessment",
        "after_registration_beginner": None,
        "after_registration_intermediate": None,
        "after_registration_advanced": None,
        "analysis_intro_beginner": "analysis_task_1",
        "analysis_intro_intermediate": "analysis_task_1",
        "analysis_intro_advanced": "analysis_task_1",
        "analysis_task_1_beginner": "analysis_task_1",
        "analysis_task_1_intermediate": "analysis_task_1",
        "analysis_task_1_advanced": "analysis_task_1",
        "analysis_feedback_1_beginner": "analysis_task_1",
        "analysis_feedback_1_intermediate": "analysis_task_1",
        "analysis_feedback_1_advanced": "analysis_task_1",
        "analysis_task_2_beginner": "analysis_task_2",
        "analysis_task_2_intermediate": "analysis_task_2",
        "analysis_task_2_advanced": "analysis_task_2",
        "analysis_feedback_2_beginner": "analysis_task_2",
        "analysis_feedback_2_intermediate": "analysis_task_2",
        "analysis_feedback_2_advanced": "analysis_task_2",
        "roleplay_intro": None,
        "role_menu": None,
        "role_mediator": "role_mediator",
        "role_logical": "role_logical",
        "role_idea_generator": "role_idea_generator",
        "role_researcher": "role_researcher",
        "role_interpreter": "role_interpreter",
        "role_advocate": "role_advocate",
        "role_judge": "role_judge",
        "role_peacemaker": "role_peacemaker",
        "role_empath": "role_empath",
        "roleplay_feedback_mediator": "role_mediator",
        "roleplay_feedback_logical": "role_logical",
        "roleplay_feedback_idea_generator": "role_idea_generator",
        "roleplay_feedback_researcher": "role_researcher",
        "roleplay_feedback_interpreter": "role_interpreter",
        "roleplay_feedback_advocate": "role_advocate",
        "roleplay_feedback_judge": "role_judge",
        "roleplay_feedback_peacemaker": "role_peacemaker",
        "roleplay_feedback_empath": "role_empath",
        "reflection": "reflection",
        "posttest": "posttest",
        "data_collection": None,
        "end": None,
    }

    current_step_key = state_to_step.get(current_state)

    # Найти номер текущего шага (1-based индекс в STEP_KEYS)
    current_step_number = 0
    if current_step_key and current_step_key in STEP_KEYS:
        current_step_number = STEP_KEYS.index(current_step_key) + 1

    # Статус-значок
    if percentage == 0:
        status_badge = "not_started"
    elif percentage == 100:
        status_badge = "completed"
    else:
        status_badge = "in_progress"

    # Прогресс по заданиям анализа (2 задания)
    analysis_total = 2
    analysis_completed = 0
    if "analysis_task_1" in completed_steps:
        analysis_completed += 1
    if "analysis_task_2" in completed_steps:
        analysis_completed += 1
    analysis_progress = {
        "completed": analysis_completed,
        "total": analysis_total,
        "percentage": int((analysis_completed / analysis_total) * 100)
        if analysis_total > 0
        else 0,
    }

    # Прогресс по ролям (9 ролей)
    roleplay_total = 9
    completed_roles = user_data.get("completed_roles", [])
    roleplay_completed = len([r for r in completed_roles if r.startswith("role_")])
    roleplay_progress = {
        "completed": roleplay_completed,
        "total": roleplay_total,
        "percentage": int((roleplay_completed / roleplay_total) * 100)
        if roleplay_total > 0
        else 0,
    }

    return {
        "status_badge": status_badge,
        "percentage": percentage,
        "current_step": current_step_number,
        "total_steps": TOTAL_STEPS,
        "completed_steps_count": completed_count,
        "analysis_progress": analysis_progress,
        "roleplay_progress": roleplay_progress,
    }


def _sanitize_name(raw: str) -> str:
    """Strip HTML tags and limit length for user_name."""
    clean = re.sub(r"<[^>]*>", "", raw).strip()
    return clean[:_MAX_NAME_LENGTH] if clean else raw[:_MAX_NAME_LENGTH]


def _sanitize_input(raw: str) -> str:
    """Truncate overly long input."""
    return raw[:_MAX_INPUT_LENGTH]


def _append_assistant_message(request: Any) -> None:
    """Append the current state's message to chat_history as an assistant turn."""
    state_data = request.session["scenario"]["states"].get(
        request.session["current_state"]
    )
    if state_data is None:
        logger.warning(
            "State %s not found in scenario", request.session["current_state"]
        )
        return
    content = get_current_message(request)
    request.session["chat_history"].append(
        {
            "role": "assistant",
            "content": content,
            "state": request.session["current_state"],
            "timestamp": datetime.now().isoformat(),
            "options": state_data.get("options") if state_data else None,
        }
    )
    request.session.modified = True


def _append_user_message(request: Any, user_input: str) -> None:
    """Append the user's input to chat_history as a user turn."""
    request.session["chat_history"].append(
        {
            "role": "user",
            "content": user_input,
            "state": request.session["current_state"],
            "timestamp": datetime.now().isoformat(),
        }
    )


def init_session(request: Any) -> None:
    """Initialize session state for a new tutor session.

    Sets up chat_history, current_state, user_data, scenario, and session_id
    in ``request.session`` if not already present.
    """
    from .data import SCENARIO as _SCENARIO
    from .data import randomize_scenario

    if "current_state" not in request.session:
        request.session["chat_history"] = []
        request.session["current_state"] = "start"
        request.session["user_data"] = {
            "user_name": None,
            "level": None,
            "pretest_scores": None,
            "posttest_scores": None,
            "current_role": None,
            "current_role_variant": None,
            "completed_roles": [],
            "completed_modes": [],
            "completed_steps": [],
            "opened_tasks": [],  # Задания, которые были открыты (начаты)
            "completed_tasks": [],  # Задания, которые были завершены (обработан фидбек)
        }
        request.session["scenario"] = randomize_scenario(_SCENARIO)
        request.session["session_id"] = uuid.uuid4().hex
        request.session.modified = True


def get_current_message(request: Any) -> str:
    """Return the formatted message for the current state.

    Performs variable substitution ({user_name}, {level}) and injects
    LLM feedback for analysis/roleplay feedback states.
    """
    scenario = request.session["scenario"]
    current_state = request.session["current_state"]
    user_data = request.session["user_data"]

    state_data = scenario["states"][current_state]
    message = state_data["message"]

    # --- Determine task context for LLM feedback injection ---
    task_context: Optional[str] = None
    role_name: Optional[str] = None
    if "analysis_feedback_1" in current_state:
        task_state = current_state.replace("feedback_1", "task_1")
        if task_state in scenario["states"]:
            task_context = scenario["states"][task_state]["message"]
    elif "analysis_feedback_2" in current_state:
        task_state = current_state.replace("feedback_2", "task_2")
        if task_state in scenario["states"]:
            task_context = scenario["states"][task_state]["message"]
    elif "roleplay_feedback" in current_state:
        role_name = current_state.replace("roleplay_feedback_", "")
        task_state = f"role_{role_name}"
        if task_state in scenario["states"]:
            task_context = scenario["states"][task_state]["message"]

    # --- Guard for empty chat_history ---
    chat_history = request.session.get("chat_history", [])
    user_answer = chat_history[-1]["content"] if chat_history else ""

    # --- LLM feedback injection ---
    if task_context and user_data.get("user_name") and user_data.get("level"):
        llm_out = get_llm_feedback(
            user_name=user_data["user_name"],
            level=user_data["level"],
            role_name=role_name,
            user_answer=user_answer,
            task_question=task_context,
        )
        if llm_out:
            skip_model_answer = "roleplay_feedback" in current_state
            markers = (
                ["\n\n\u25b6\ufe0f"]
                if skip_model_answer
                else ["\n\n**\U0001f4cb Model answer:**", "\n\n\u25b6\ufe0f"]
            )
            for marker in markers:
                parts = message.split(marker, 1)
                if len(parts) == 2:
                    header = parts[0].split("\n\n", 1)[0]
                    message = header + "\n\n" + llm_out + marker + parts[1]
                    break
            else:
                message = message.split("\n\n", 1)[0] + "\n\n" + llm_out

    # --- Variable substitution ---
    if user_data.get("user_name"):
        message = message.replace("{user_name}", user_data["user_name"])
    if "{level}" in message and user_data.get("level"):
        message = message.replace("{level}", user_data["level"])

    return message


# ---------------------------------------------------------------------------
# Handler functions
# ---------------------------------------------------------------------------


def handle_back(request: Any) -> None:
    """Handle the 'back' command — navigate to the appropriate previous state."""
    user_data = request.session["user_data"]
    level = user_data.get("level", "beginner")
    current_state = request.session["current_state"]

    if "analysis_task_" in current_state:
        request.session["current_state"] = f"analysis_intro_{level}"
    elif "analysis_feedback_" in current_state:
        request.session["current_state"] = f"analysis_intro_{level}"
    elif "analysis_intro_" in current_state:
        request.session["current_state"] = f"after_registration_{level}"
    elif current_state == "role_menu":
        request.session["current_state"] = "roleplay_intro"
    elif current_state == "roleplay_intro":
        request.session["current_state"] = f"after_registration_{level}"
    elif "roleplay_feedback" in current_state:
        request.session["current_state"] = "role_menu"
    else:
        request.session["current_state"] = f"after_registration_{level}"

    _append_assistant_message(request)


def handle_numeric_test(request: Any, user_input: str, key: str) -> bool:
    """Handle pretest or posttest numeric input (3 numbers 1-5).

    Args:
        request: Django request with session.
        user_input: Raw user input string.
        key: Either 'pretest_scores' or 'posttest_scores'.

    Returns:
        True if input was valid and processed, False otherwise.
    """
    from django.contrib import messages as dj_messages

    try:
        scores = list(map(int, user_input.split()))
        if len(scores) == 3 and all(1 <= s <= 5 for s in scores):
            request.session["user_data"][key] = scores
            next_state = (
                "level_assessment" if key == "pretest_scores" else "data_collection"
            )
            request.session["current_state"] = next_state
            if key == "pretest_scores":
                _mark_step_completed(request, "pretest")
            elif key == "posttest_scores":
                _mark_step_completed(request, "posttest")
            _append_assistant_message(request)
            return True
        else:
            dj_messages.warning(
                request,
                "\u26a0\ufe0f Please enter three numbers between 1 and 5, separated by spaces.",
            )
            request.session.modified = True
            return False
    except (ValueError, IndexError):
        dj_messages.warning(
            request,
            "\u26a0\ufe0f Please enter three numbers between 1 and 5, separated by spaces.",
        )
        request.session.modified = True
        return False


def handle_analysis_feedback(request: Any, user_input: str) -> None:
    """Handle commands at analysis_feedback states ('next' / 'back')."""
    from django.contrib import messages as dj_messages

    cmd = user_input.lower()
    current_state = request.session["current_state"]
    user_data = request.session["user_data"]

    # Определяем текущее задание анализа для пометки как завершённого
    task_slug = None
    if "feedback_1" in current_state:
        # Аналогичный уровень из текущего состояния
        level = current_state.replace("analysis_feedback_1_", "")
        task_slug = f"analysis_task_1_{level}"
    elif "feedback_2" in current_state:
        level = current_state.replace("analysis_feedback_2_", "")
        task_slug = f"analysis_task_2_{level}"

    if cmd == "next":
        if "feedback_1" in current_state:
            new_state = current_state.replace("feedback_1", "task_2")
            request.session["current_state"] = new_state
            # Отмечаем новое задание как открытое
            opened_tasks = user_data.setdefault("opened_tasks", [])
            if new_state not in opened_tasks:
                opened_tasks.append(new_state)
        elif "feedback_2" in current_state:
            request.session["current_state"] = "roleplay_intro"
        # Отмечаем задание как завершённое
        if task_slug:
            completed_tasks = user_data.setdefault("completed_tasks", [])
            if task_slug not in completed_tasks:
                completed_tasks.append(task_slug)
                request.session.modified = True
        _append_assistant_message(request)
    elif cmd == "back":
        level = user_data.get("level", "beginner")
        request.session["current_state"] = f"analysis_intro_{level}"
        # Отмечаем задание как завершённое
        if task_slug:
            completed_tasks = user_data.setdefault("completed_tasks", [])
            if task_slug not in completed_tasks:
                completed_tasks.append(task_slug)
                request.session.modified = True
        _append_assistant_message(request)
    else:
        dj_messages.warning(
            request, "\u26a0\ufe0f Please type 'next' to continue or 'back' to return."
        )
        request.session.modified = True


def handle_roleplay_feedback(request: Any, user_input: str) -> None:
    """Handle commands at roleplay_feedback states ('revise' / 'next' / 'back')."""
    from django.contrib import messages as dj_messages

    cmd = user_input.lower()
    user_data = request.session["user_data"]
    current_role = user_data.get("current_role", "role_mediator")

    if cmd == "revise":
        request.session["current_state"] = current_role
    elif cmd in ("next", "back"):
        # Отмечаем текущую роль как завершённую
        completed_roles = request.session["user_data"].setdefault("completed_roles", [])
        if current_role not in completed_roles:
            completed_roles.append(current_role)
        _mark_step_completed(request, current_role)
        # Добавляем роль в список завершённых заданий
        completed_tasks = user_data.setdefault("completed_tasks", [])
        if current_role not in completed_tasks:
            completed_tasks.append(current_role)
        request.session.modified = True
        request.session["current_state"] = "role_menu"
    else:
        dj_messages.warning(
            request, "\u26a0\ufe0f Please type 'revise', 'next', or 'back'."
        )
        request.session.modified = True
        return

    _append_assistant_message(request)


def handle_after_registration(request: Any, user_input: str) -> None:
    """Handle input at after_registration states (step selection: 1 or 2)."""
    from django.contrib import messages as dj_messages

    user_data = request.session["user_data"]

    if user_input in ("1", "2"):
        if user_input == "1":
            level = user_data.get("level", "beginner")
            request.session["current_state"] = f"analysis_intro_{level}"
            # Отмечаем режим анализа как завершённый
            completed_modes = user_data.setdefault("completed_modes", [])
            if "analysis" not in completed_modes:
                completed_modes.append("analysis")
        else:
            request.session["current_state"] = "roleplay_intro"
            # Отмечаем режим ролевой игры как завершённый
            completed_modes = user_data.setdefault("completed_modes", [])
            if "roleplay" not in completed_modes:
                completed_modes.append("roleplay")
        request.session.modified = True
        _append_assistant_message(request)
    elif user_input.lower() == "back":
        request.session["current_state"] = "level_assessment"
        _append_assistant_message(request)
    else:
        dj_messages.warning(
            request, "\u26a0\ufe0f Please type 1 (ANALYSIS) or 2 (ROLE-PLAY)."
        )
        request.session.modified = True


def handle_role_menu(request: Any, user_input: str) -> None:
    """Handle input at the role_menu state."""
    from django.contrib import messages as dj_messages

    user_data = request.session["user_data"]
    cmd = user_input.lower()

    _ROLE_MAP = {
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

    if cmd == "finish":
        request.session["current_state"] = "reflection"
    elif cmd == "back":
        request.session["current_state"] = "roleplay_intro"
    elif user_input in _ROLE_MAP:
        role = _ROLE_MAP[user_input]
        user_data["current_role"] = role
        request.session["current_state"] = role
        # Отмечаем роль как открытую (начатую)
        opened_tasks = user_data.setdefault("opened_tasks", [])
        if role not in opened_tasks:
            opened_tasks.append(role)
    else:
        dj_messages.warning(
            request, "\u26a0\ufe0f Please type a number from 1 to 9, or 'finish'."
        )
        request.session.modified = True
        return

    _append_assistant_message(request)


def handle_roleplay_intro(request: Any, user_input: str) -> None:
    """Handle input at roleplay_intro ('continue' / 'back')."""
    from django.contrib import messages as dj_messages

    user_data = request.session["user_data"]
    cmd = user_input.lower()

    if cmd == "continue":
        request.session["current_state"] = "role_menu"
    elif cmd == "back":
        level = user_data.get("level", "beginner")
        request.session["current_state"] = f"after_registration_{level}"
    else:
        dj_messages.warning(
            request,
            "\u26a0\ufe0f Please type 'continue' to proceed or 'back' to return.",
        )
        request.session.modified = True
        return

    _append_assistant_message(request)


def handle_analysis_intro(request: Any, user_input: str) -> None:
    """Handle input at analysis_intro states ('yes' to start)."""
    if user_input.lower() == "yes":
        current = request.session["current_state"]
        new_state = current.replace("intro", "task_1")
        request.session["current_state"] = new_state
        # Отмечаем задание анализа как открытое (начатое)
        user_data = request.session["user_data"]
        opened_tasks = user_data.setdefault("opened_tasks", [])
        if new_state not in opened_tasks:
            opened_tasks.append(new_state)
            request.session.modified = True
        _append_assistant_message(request)


def handle_analysis_task(request: Any) -> None:
    """Handle analysis_task states — accept any text, transition to feedback."""
    current_state = request.session["current_state"]
    # Определяем номер задачи
    if "analysis_task_1" in current_state:
        step_key = "analysis_task_1"
    elif "analysis_task_2" in current_state:
        step_key = "analysis_task_2"
    else:
        step_key = None
    if step_key:
        _mark_step_completed(request, step_key)
    request.session["current_state"] = current_state.replace("task", "feedback")
    _append_assistant_message(request)


def handle_data_collection(request: Any, user_input: str) -> None:
    """Handle data_collection state ('exit' to finish)."""
    from django.contrib import messages as dj_messages

    if user_input.lower() == "exit":
        request.session["current_state"] = "end"
        _mark_step_completed(request, "data_collection")
        _append_assistant_message(request)
    else:
        dj_messages.warning(
            request, "\u26a0\ufe0f Please type 'exit' to close the session."
        )
        request.session.modified = True


def process_input(request: Any, user_input: str) -> None:
    """Main entry point: process user input and update session state.

    Routes to the appropriate handler based on the current state,
    then performs validation and state transitions.
    """
    from django.contrib import messages as dj_messages

    user_input = _sanitize_input(user_input)
    current_state = request.session["current_state"]

    logger.debug("process_input: state=%s, input=%s", current_state, user_input[:80])

    # --- Handle 'back' command globally ---
    if user_input.lower() == "back":
        handle_back(request)
        return

    # --- Append user message to history ---
    _append_user_message(request, user_input)

    # --- Validate against state regex ---
    current_state_obj = request.session["scenario"]["states"][current_state]
    if "validation" in current_state_obj:
        if not re.match(current_state_obj["validation"], user_input):
            dj_messages.warning(
                request,
                "\u26a0\ufe0f Please enter the data in the correct format. Try again.",
            )
            request.session.modified = True
            return

    # --- State-specific handlers ---
    if current_state == "start":
        raw = user_input.split()[0] if user_input.split() else user_input
        request.session["user_data"]["user_name"] = _sanitize_name(raw)
        request.session["current_state"] = "pretest"
        _append_assistant_message(request)
        return

    if current_state == "pretest":
        handle_numeric_test(request, user_input, "pretest_scores")
        return

    if current_state == "level_assessment":
        if user_input in ("1", "2", "3"):
            level_map = {"1": "beginner", "2": "intermediate", "3": "advanced"}
            request.session["user_data"]["level"] = level_map[user_input]
            request.session["current_state"] = (
                f"after_registration_{level_map[user_input]}"
            )
            _mark_step_completed(request, "level_assessment")
            _append_assistant_message(request)
        else:
            dj_messages.warning(request, "\u26a0\ufe0f Please enter 1, 2, or 3.")
            request.session.modified = True
        return

    if current_state == "posttest":
        handle_numeric_test(request, user_input, "posttest_scores")
        return

    if "roleplay_feedback" in current_state:
        handle_roleplay_feedback(request, user_input)
        return

    if "analysis_feedback_" in current_state:
        handle_analysis_feedback(request, user_input)
        return

    if "after_registration_" in current_state:
        handle_after_registration(request, user_input)
        return

    if current_state == "role_menu":
        handle_role_menu(request, user_input)
        return

    if current_state == "roleplay_intro":
        handle_roleplay_intro(request, user_input)
        return

    if "analysis_intro_" in current_state:
        handle_analysis_intro(request, user_input)
        return

    if "analysis_task_" in current_state:
        handle_analysis_task(request)
        return

    if current_state == "data_collection":
        handle_data_collection(request, user_input)
        return

    # --- Generic next_state / options fallback ---
    if "next_state" in current_state_obj:
        next_state = current_state_obj["next_state"]
        if isinstance(next_state, dict):
            if user_input in next_state:
                request.session["current_state"] = next_state[user_input]
            elif "default" in next_state:
                request.session["current_state"] = next_state["default"]
            else:
                request.session["current_state"] = "end"
        else:
            request.session["current_state"] = next_state
    elif "options" in current_state_obj and user_input in current_state_obj["options"]:
        request.session["current_state"] = current_state_obj["next_state"][user_input]

    # Отметить reflection как завершённый, если перешли к posttest
    if request.session["current_state"] == "posttest":
        _mark_step_completed(request, "reflection")

    if request.session["current_state"] != "end":
        _append_assistant_message(request)
    else:
        request.session.modified = True
