import logging
from datetime import datetime
from typing import Any, Dict

from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render

from .data import ANALYSIS_STEP_KEYS, ROLE_STEP_KEYS
from .session import SessionStorage
from .state_machine import init_session, calculate_progress
from .tutor_session import TutorSession

logger = logging.getLogger(__name__)


def chat_view(request: HttpRequest):
    """Chat interface, driven entirely by the TutorSession module.

    The view never branches on the current state: the module decides which
    navigation options are available and attaches them to the current
    assistant turn; the template renders exactly one option list per turn.
    """
    session: TutorSession = TutorSession(SessionStorage(request.session))

    # A fresh browser session has nothing stored yet — start one.
    try:
        session.turns()
    except RuntimeError:
        session.start()

    if request.method == "POST":
        text = request.POST.get("user_input", "").strip()
        if text:
            session.submit(text)

    summary = session.progress()
    turns = session.turns()

    # The module silently drops a rejected input (the user turn stays
    # unanswered) — surface it as a warning so the message does not hang.
    if (
        request.method == "POST"
        and turns
        and turns[-1].role == "user"
        and summary.phase != "finished"
    ):
        messages.warning(
            request, "⚠️ Your input was not recognized — please choose one of the options below."
        )

    return render(
        request,
        "tutor/chat.html",
        {
            "turns": turns,
            "summary": summary,
            "is_end": summary.phase == "finished",
            "debug": settings.DEBUG,
        },
    )


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


def main_menu_view(request: HttpRequest):
    """Standalone progress overview page."""
    init_session(request)

    user_data: Dict[str, Any] = request.session.get("user_data", {})
    current_state: str = request.session.get("current_state", "start")

    completed_option_values: set = set()
    completed_roles = user_data.get("completed_roles", [])
    completed_modes = user_data.get("completed_modes", [])
    level = user_data.get("level")

    if current_state == "role_menu":
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
        for val, key in _ROLE_VAL_TO_KEY.items():
            if key in completed_roles:
                completed_option_values.add(val)
    elif current_state.startswith("after_registration_"):
        if "analysis" in completed_modes:
            completed_option_values.add("1")
        if "roleplay" in completed_modes:
            completed_option_values.add("2")

    _ANALYSIS_LABELS = {
        "analysis_task_1": "Task 1: Softening Criticism",
        "analysis_task_2": "Task 2: Aggressive Formatting",
    }
    _ROLE_LABELS = {
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

    analysis_tasks = [(k, _ANALYSIS_LABELS[k]) for k in ANALYSIS_STEP_KEYS]
    role_tasks = [(k, _ROLE_LABELS[k]) for k in ROLE_STEP_KEYS]

    context = {
        "user_data": user_data,
        "session_id": request.session.get("session_id", ""),
        "debug": settings.DEBUG,
        "progress": calculate_progress(request),
        "analysis_tasks": analysis_tasks,
        "role_tasks": role_tasks,
        "completed_option_values": completed_option_values,
        "completed_roles": completed_roles,
        "opened_tasks": user_data.get("opened_tasks", []),
    }
    return render(request, "tutor/main_menu.html", context)


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
