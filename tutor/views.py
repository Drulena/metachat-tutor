import logging
from dataclasses import asdict
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render

from .session import SessionStorage, Summary
from .tutor_session import TutorSession

logger = logging.getLogger(__name__)


def _session_for(request: HttpRequest) -> TutorSession:
    """Build a TutorSession over the browser's Django session."""
    return TutorSession(SessionStorage(request.session))


def _summary_or_none(session: TutorSession) -> Summary | None:
    """Return the session's ``Summary``, or ``None`` if the session is unstarted.

    ``TutorSession.progress()`` raises ``RuntimeError`` on an unstarted
    session; this is the single place that translates that into ``None`` so
    the views never spell the "is it started?" probe themselves.
    """
    try:
        return session.progress()
    except RuntimeError:
        return None


def _started_session(request: HttpRequest) -> TutorSession:
    """Build a TutorSession, starting one if the browser has none yet.

    Used by views that must render a live session (chat, menu). Views that
    only inspect or wipe state use :func:`_session_for` directly so a fresh
    browser session is left unstarted (no side effect).
    """
    session = _session_for(request)
    if _summary_or_none(session) is None:
        session.start()
    return session


def chat_view(request: HttpRequest):
    """Chat interface, driven entirely by the TutorSession module.

    The view never branches on the current state: the module decides which
    navigation options are available and attaches them to the current
    assistant turn; the template renders exactly one option list per turn.
    """
    session = _started_session(request)

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
    """Confirm page shown before wiping the session (GET only).

    Shows what a reset would wipe via the module's Summary; a session that
    was never started renders the plain confirmation card.
    """
    session = _session_for(request)
    summary = _summary_or_none(session)
    return render(request, "tutor/reset_confirm.html", {"summary": summary})


def reset_view(request: HttpRequest):
    """Reset the session. POST-only to protect against CSRF-triggered wipes."""
    if request.method != "POST":
        return redirect("reset_confirm")

    session = _session_for(request)
    try:
        session.reset()
    except Exception:
        logger.exception("Session reset failed for client %s", request.META.get("REMOTE_ADDR"))
        raise
    logger.info("Session reset for client %s", request.META.get("REMOTE_ADDR"))
    return redirect("chat")


def main_menu_view(request: HttpRequest):
    """Standalone progress overview page, driven entirely by the module's Summary.

    The view never branches on the current state: every figure (percentage,
    step counts, task lists, completed sets, level, participant name) comes
    from ``TutorSession.progress()``.
    """
    session = _started_session(request)
    summary = session.progress()
    return render(
        request,
        "tutor/main_menu.html",
        {"summary": summary, "debug": settings.DEBUG},
    )


def export_view(request: HttpRequest):
    """Session export, composed from the module's turns, progress, and identity.

    No raw session keys are read: the payload is built from
    ``TutorSession.turns()``, ``TutorSession.progress()``, and the Summary's
    session id. A session that was never started exports an empty, fresh
    representation without being started (no side effect).
    """
    session = _session_for(request)
    summary = _summary_or_none(session)
    if summary is None:
        # Unstarted session: export a fresh, empty representation (no side effect).
        summary = Summary()
        turns = []
    else:
        turns = session.turns()
    data = {
        "session_id": summary.session_id,
        "turns": [asdict(turn) for turn in turns],
        "progress": asdict(summary),
        "export_time": datetime.now().isoformat(),
    }
    response = JsonResponse(
        data, json_dumps_params={"indent": 2, "ensure_ascii": False}
    )
    response["Content-Disposition"] = (
        f'attachment; filename="metachat_session_{summary.session_id}.json"'
    )
    return response
