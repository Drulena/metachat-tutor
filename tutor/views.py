import logging
from dataclasses import asdict
from datetime import datetime

from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render

from .forms import IntakeForm
from .ledger import open_session
from .models import Group
from .session import Intake, SessionStorage
from .tutor_session import TutorSession

logger = logging.getLogger(__name__)


def _session_for(request: HttpRequest) -> TutorSession:
    """Build a TutorSession over the browser's Django session."""
    return TutorSession(SessionStorage(request.session))


def _intake_pending(request: HttpRequest) -> bool:
    """True while the browser has submitted no intake form.

    The intake replaced the chat states that used to collect name, group
    and level (ticket #37), so a browser with no session has nothing to
    show on the chat pages: ``progress()`` answers the zero-state and
    never raises, which is what the gate reads. The gate adds no flag of
    its own — an unstarted session IS an intake pending.

    Inspecting views (reset confirm, export) answer the zero-state for a
    fresh browser instead of starting a session it never asked for.
    """
    return not _session_for(request).progress().started


def intake_view(request: HttpRequest):
    """The intake form: registration facts, consent copy, then the chat.

    A valid submit opens the session (id minted by ``TutorSession.start``)
    and writes the matching ledger row in the same request, so every
    participant in the chat has a row in the research record before their
    first message. An invalid submit is answered with the form again, the
    field errors above the fields: the intake carries no default
    participant (spec #33), so a blank name, group or level is refused.

    A ledger hiccup is logged and never blocks the learner: the chat is
    the lesson, the row is the research record, and a database outage
    must not be the reason a class cannot start.
    """
    if _intake_pending(request) is False:
        # Already opened: a resubmitted form must not restart a running
        # session, and Back into the form lands in the chat.
        return redirect("chat")

    if request.method == "POST":
        form = IntakeForm(request.POST)
        if form.is_valid():
            intake = Intake(
                name=form.cleaned_data["name"].strip(),
                group=form.cleaned_data["group"].strip(),
                level=form.cleaned_data["level"],
            )
            session = _session_for(request)
            session.start(intake)
            session_id = session.progress().session_id
            try:
                open_session(intake, session_id)
            except Exception:  # pragma: no cover - infrastructure hiccup
                logger.exception(
                    "Ledger row missing for session %s", session_id
                )
            logger.info(
                "Session %s opened for group %s", session_id, intake.group
            )
            return redirect("chat")
    else:
        form = IntakeForm()

    return render(
        request,
        "tutor/intake.html",
        {
            "form": form,
            # Cohort names already in the ledger, for the form's datalist.
            "groups": Group.objects.order_by("name").values_list("name", flat=True)[:60],
        },
    )


def terms_view(request: HttpRequest):
    """Static consent page, linked from the intake form (ticket #37 AC).

    Read-only by design: consent copy the learner can return to after the
    intake, with no session and no state to touch.
    """
    return render(request, "tutor/terms.html")


def chat_view(request: HttpRequest):
    """Chat interface, driven entirely by the TutorSession module.

    The view never branches on the current state: the module decides which
    navigation options are available and attaches them to the current
    assistant turn; the template renders exactly one option list per turn.
    A rejected input is surfaced by the module too — the unanswered user
    turn carries its ``rejection`` copy and the template renders it.

    Method shapes the response: a POST is a submission and is answered with a
    redirect back to this page (POST-Redirect-GET, issue #34), so the page a
    browser re-requests on reload is a GET that submits nothing. Only a GET
    renders.
    """
    if _intake_pending(request):
        return redirect("intake")

    session = _session_for(request)

    if request.method == "POST":
        text = request.POST.get("user_input", "").strip()
        if text:
            session.submit(text)
        # Every submission answers with a redirect, blank text included; the
        # docstring says why (issue #34).
        return redirect("chat")

    summary = session.progress()
    turns = session.turns()

    return render(
        request,
        "tutor/chat.html",
        {
            "turns": turns,
            "summary": summary,
            "is_end": summary.finished,
        },
    )


def reset_confirm_view(request: HttpRequest):
    """Confirm page shown before wiping the session (GET only).

    Shows what a reset would wipe via the module's Summary; a session that
    was never started renders the plain confirmation card — progress()
    answers the zero-state for it.
    """
    session = _session_for(request)
    summary = session.progress()
    return render(request, "tutor/reset_confirm.html", {"summary": summary})


def reset_view(request: HttpRequest):
    """Reset the session. POST-only to protect against CSRF-triggered wipes.

    Lands on the intake form, not the chat: a wipe erases the registration
    facts too, so the learner re-supplies them (ticket #37).
    """
    if request.method != "POST":
        return redirect("reset_confirm")

    session = _session_for(request)
    try:
        session.reset()
    except Exception:
        logger.exception("Session reset failed for client %s", request.META.get("REMOTE_ADDR"))
        raise
    logger.info("Session reset for client %s", request.META.get("REMOTE_ADDR"))
    return redirect("intake")


def main_menu_view(request: HttpRequest):
    """Standalone progress overview page, driven entirely by the module's Summary.

    The view never branches on the current state: every figure (percentage,
    step counts, task lists, completed sets, level, participant name) comes
    from ``TutorSession.progress()``.
    """
    if _intake_pending(request):
        return redirect("intake")

    summary = _session_for(request).progress()
    return render(
        request,
        "tutor/main_menu.html",
        {"summary": summary},
    )


def export_view(request: HttpRequest):
    """Session export, composed from the module's turns, progress, and identity.

    No raw session keys are read: the payload is built from
    ``TutorSession.turns()``, ``TutorSession.progress()``, and the Summary's
    session id. The intake gate keeps the rule "an export belongs to a
    named participant": a browser that never registered has no session id
    to name a file after, so it is sent to the form.
    """
    if _intake_pending(request):
        return redirect("intake")

    session = _session_for(request)
    summary = session.progress()
    data = {
        "session_id": summary.session_id,
        # The registered level once at the header (spec #16 C1-9 AC2):
        # a session's research record is read with its level visible,
        # not buried in the progress panel.
        "level": summary.level,
        "turns": [asdict(turn) for turn in session.turns()],
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
