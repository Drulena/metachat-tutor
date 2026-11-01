"""The ledger seam: writes from the chat, one read for the export (ADR-0007).

The ledger is a research artefact: the intake form opens a row, every
submission appends to it, and no page reads it - the Summary stays the sole
presentation source (decision 1). The single read is the export, which hands
the gate answers to the uploaded artefact (decision 6). Every function here is
therefore tolerant of a missing row: a learner never loses a chat to a
database hiccup, and the miss is logged for the maintainer to see.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional, Sequence

from django.db import transaction
from django.utils import timezone

from .models import Assessment, Group, SessionRecord
from .session import Intake

logger = logging.getLogger(__name__)


def _row(session_id: str) -> Optional[SessionRecord]:
    """The row a write belongs to; a miss is logged, never raised.

    The row is born at the intake form, so a miss means the intake never
    reached the ledger: the chat carries on, and the exchange is lost to
    research - a gap the log names, not a failure the learner sees.
    """
    row = SessionRecord.objects.filter(session_id=session_id).first()
    if row is None:
        logger.warning(
            "No ledger row for session %s; this exchange is not mirrored.", session_id
        )
    return row


def open_session(
    intake: Intake,
    session_id: str,
    entries: Sequence[dict] = (),
    previous_session_id: Optional[str] = None,
) -> SessionRecord:
    """Create the row an intake opens, carrying the chat's opening entries.

    ``session_id`` is the id the chat minted in the same request, so the
    row, the export file and the admin name one session (decision 3). The
    group is found case-insensitively and created on a miss, keeping the
    first-entered spelling (decision 5). ``entries`` seeds the dialogue log
    with the welcome turn the chat opened on, so the row is complete from
    its first write (decision 2); ``previous_session_id`` chains a reset
    (decision 7).
    """
    group, _created = Group.objects.get_or_create_casefolded(intake.group)
    previous = (
        SessionRecord.objects.filter(session_id=previous_session_id).first()
        if previous_session_id
        else None
    )
    return SessionRecord.objects.create(
        session_id=session_id,
        user_name=intake.name,
        level=intake.level,
        group=group,
        previous_session=previous,
        chat_history=list(entries),
    )


@transaction.atomic
def append_entries(session_id: str, entries: Sequence[dict]) -> None:
    """Append the entries the chat just produced, verbatim, in submit order.

    Append-only at the code level (decision 2): the entry dicts go in as the
    chat wrote them - role, content, state, timestamp and the assistant
    metadata - and no earlier entry is touched. The save rides
    ``updated_at`` along as the last-activity stamp (decision 4).
    """
    if not entries:
        return
    row = _row(session_id)
    if row is None:
        return
    row.chat_history = [*list(row.chat_history), *list(entries)]
    row.save(update_fields=["chat_history", "updated_at"])


def record_assessment(
    session_id: str,
    kind: str,
    raw_answer: str,
    scores: Sequence[int],
    rated: Sequence[Mapping[str, Any]] = (),
) -> None:
    """Append a gate's answer as a child row, at acceptance (decision 6).

    The raw answer is what the learner submitted, the scores are the ints the
    gate parsed from it, and rated is the task lines the gate offered them in
    - written at acceptance, because that is the one moment the copy a learner
    saw is known for certain (ticket #48: the lines print in the form, not in
    the chat transcript). A new selector test is a new kind string; the model's
    choices document the set, the database does not close it.
    """
    row = _row(session_id)
    if row is None:
        return
    Assessment.objects.create(
        session=row,
        kind=kind,
        raw_answer=raw_answer,
        scores=list(scores),
        rated=[dict(item) for item in rated],
    )


def mark_finished(session_id: str) -> None:
    """Stamp the row the moment its session reaches the terminal screen.

    A non-null ``finished_at`` is what "finished" means for the admin and
    for every filter (ADR-0007 decision 4). The stamp is written once and
    never moved again, so the write is conditional on the field being empty:
    a row that already carries a stamp is left exactly as it is, whatever
    traffic follows, and two concurrent arrivals cannot disagree.
    """
    if _row(session_id) is None:
        return
    stamped = SessionRecord.objects.filter(session_id=session_id).filter(
        finished_at__isnull=True
    ).update(finished_at=timezone.now())
    if stamped:
        logger.info("Ledger row for session %s stamped finished.", session_id)


def fill_reflection(session_id: str, text: str) -> None:
    """Fill the row's reflection field, verbatim, on acceptance (decision 1).

    A learner who re-answers the reflection keeps the newest answer: the
    field is the answer they left the session with, not a transcript.
    """
    row = _row(session_id)
    if row is None:
        return
    row.reflection = text
    row.save(update_fields=["reflection", "updated_at"])


def assessment_rows(session_id: str) -> list[dict]:
    """The gate answers a session left behind, oldest first (decision 6).

    The export's one read of the ledger: the uploaded artefact carries every
    answer with its numbers and the lines it rated, so an analysis needs no
    database to re-read it. A session the ledger never heard of has no answers
    to hand over - an empty list, the tolerance the writers keep, and no log
    line: nothing was lost to find.
    """
    row = SessionRecord.objects.filter(session_id=session_id).first()
    if row is None:
        return []
    return [
        {
            "kind": answer.kind,
            "raw_answer": answer.raw_answer,
            "scores": list(answer.scores),
            "rated": list(answer.rated),
            "created_at": answer.created_at.isoformat(),
        }
        for answer in Assessment.objects.filter(session=row).order_by(
            "created_at", "id"
        )
    ]

