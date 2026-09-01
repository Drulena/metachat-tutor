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


def chat_view(request: HttpRequest):
    try:
        init_session(request)

        if request.method == "POST":
            user_input = request.POST.get("user_input", "").strip()
            if user_input:
                process_input(request, _limit_length(user_input))

        history = request.session.get("chat_history", [])
        user_data: Dict[str, Any] = request.session.get("user_data", {})
        current_state: str = request.session.get("current_state", "start")

        # Raw messages are rendered through the `markdown` template filter,
        # which escapes first and thus neutralizes any embedded HTML/JS.
        display_history: List[Dict[str, str]] = [
            {"role": msg["role"], "content": msg["content"]} for msg in history
        ]

        context = {
            "chat_history": display_history,
            "welcome_message": SCENARIO["welcome_message"],
            "is_end": current_state == "end",
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
