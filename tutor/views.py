import logging
from datetime import datetime
from typing import Any, Dict, List

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render

from .data import SCENARIO
from .state_machine import init_session, process_input

logger = logging.getLogger(__name__)

#: Same cap the state machine enforces; trimmed here as a defense in depth
#: layer before input ever reaches session handling.
_MAX_INPUT_LENGTH = 5000


def _limit_length(value: str) -> str:
    """Defensively truncate input sent by the client."""
    return value[:_MAX_INPUT_LENGTH]


def _add_completion_markers(request: HttpRequest) -> None:
    """Добавить маркеры завершения (✅) к пунктам меню выбора."""
    user_data: Dict[str, Any] = request.session.get("user_data", {})
    current_state: str = request.session.get("current_state", "start")
    chat_history: List[Dict[str, str]] = request.session.get("chat_history", [])

    # Найти последнее сообщение ассистента
    last_assistant_msg = None
    for msg in reversed(chat_history):
        if msg.get("role") == "assistant":
            last_assistant_msg = msg
            break

    if not last_assistant_msg:
        return

    content = last_assistant_msg["content"]
    modified = False

    # Маппинг ключей ролей к именам для отображения в меню
    _ROLE_KEY_TO_NAME: Dict[str, str] = {
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

    if current_state == "role_menu":
        completed_roles = user_data.get("completed_roles", [])
        for role_key in completed_roles:
            role_name = _ROLE_KEY_TO_NAME.get(role_key)
            if not role_name:
                continue
            old_pattern = f" - {role_name} ("
            new_pattern = f" - {role_name} ✅ ("
            if old_pattern in content and new_pattern not in content:
                content = content.replace(old_pattern, new_pattern, 1)
                modified = True

    elif current_state.startswith("after_registration_"):
        completed_modes = user_data.get("completed_modes", [])
        if "analysis" in completed_modes:
            old = "🔹 **Step1️⃣** - ANALYSIS"
            new = "🔹 **Step1️⃣** - ANALYSIS ✅"
            if old in content and new not in content:
                content = content.replace(old, new, 1)
                modified = True
        if "roleplay" in completed_modes:
            old = "🔹 **Step2️⃣** - ROLE-PLAY"
            new = "🔹 **Step2️⃣** - ROLE-PLAY ✅"
            if old in content and new not in content:
                content = content.replace(old, new, 1)
                modified = True

    elif current_state == "level_assessment":
        level = user_data.get("level")
        if level:
            _LEVEL_TO_NUM = {"beginner": "1", "intermediate": "2", "advanced": "3"}
            level_num = _LEVEL_TO_NUM.get(level)
            if level_num:
                level_label = level.capitalize()
                old = f"▫️{level_num}▫️ {level_label} ("
                new = f"▫️{level_num}▫️ {level_label} ✅ ("
                if old in content and new not in content:
                    content = content.replace(old, new, 1)
                    modified = True

    if modified:
        last_assistant_msg["content"] = content
        request.session.modified = True


def chat_view(request: HttpRequest):
    try:
        init_session(request)

        if request.method == "POST":
            user_input = request.POST.get("user_input", "").strip()
            if user_input:
                process_input(request, _limit_length(user_input))
                _add_completion_markers(request)

        history = request.session.get("chat_history", [])
        user_data: Dict[str, Any] = request.session.get("user_data", {})
        current_state: str = request.session.get("current_state", "start")

        # Raw messages are rendered through the `markdown` template filter,
        # which escapes first and thus neutralizes any embedded HTML/JS.
        display_history: List[Dict[str, Any]] = [
            {
                "role": msg["role"],
                "content": msg["content"],
                "options": msg.get("options"),
            }
            for msg in history
        ]

        # Маппинг значений кнопок → ключей завершённых элементов
        _ROLE_VAL_TO_KEY = {
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
        completed_option_values: set = set()
        completed_roles = user_data.get("completed_roles", [])
        completed_modes = user_data.get("completed_modes", [])
        level = user_data.get("level")
        if current_state == "role_menu":
            for val, key in _ROLE_VAL_TO_KEY.items():
                if key in completed_roles:
                    completed_option_values.add(val)
        elif current_state.startswith("after_registration_"):
            if "analysis" in completed_modes:
                completed_option_values.add("1")
            if "roleplay" in completed_modes:
                completed_option_values.add("2")
        elif current_state == "level_assessment" and level:
            _LEVEL_MAP = {"beginner": "1", "intermediate": "2", "advanced": "3"}
            if level in _LEVEL_MAP:
                completed_option_values.add(_LEVEL_MAP[level])

        context = {
            "chat_history": display_history,
            "welcome_message": SCENARIO["welcome_message"],
            "is_end": current_state == "end",
            "completed_option_values": completed_option_values,
            "system_option_keys": {"back", "finish", "exit"},
            "user_data": user_data,
            "session_id": request.session.get("session_id", ""),
            "debug": settings.DEBUG,
        }

        return render(request, "tutor/chat.html", context)
    except Exception:
        logger.exception("Unhandled error in chat_view")
        raise


def reset_confirm_view(request: HttpRequest):
    """Confirm page shown before wiping the session (GET only)."""
    return render(request, "tutor/reset_confirm.html", {})


def reset_view(request: HttpRequest):
    """Reset the session. POST-only to protect against CSRF-triggered wipes."""
    if request.method != "POST":
        return redirect("reset_confirm")

    try:
        request.session.flush()
        logger.info("Session reset for client %s", request.META.get("REMOTE_ADDR"))
    except Exception:
        logger.exception("Failed to reset session")
        raise
    return redirect("chat")


def export_view(request: HttpRequest):
    data = {
        "session_id": request.session.get("session_id"),
        "user_data": request.session.get("user_data"),
        "chat_history": request.session.get("chat_history"),
        "export_time": datetime.now().isoformat(),
    }
    response = JsonResponse(
        data, json_dumps_params={"indent": 2, "ensure_ascii": False}
    )
    response["Content-Disposition"] = (
        f'attachment; filename="metachat_session_{request.session.get("session_id")}.json"'
    )
    return response
