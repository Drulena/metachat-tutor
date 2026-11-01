"""The research ledger side of the intake seam (tickets #37, #38).

The chat state stays in the Django session; the durable research record
lives in the database (ticket #36 schema). This module is the only
place that writes a ledger row, so the pair "one chat session, one row"
is enforced by construction: :func:`open_session` runs at the intake
submit and :func:`record_assessment` at every assessable-answer submit.
"""

from __future__ import annotations

from .models import Assessment, Group, SessionRecord
from .session import Intake


def open_session(intake: Intake, session_id: str) -> SessionRecord:
    """Create the ledger row the intake form implies, and return it.

    ``session_id`` is the id the chat minted for this session, so the
    export file name and the row key are the same text. The group is
    matched case-insensitively and created on first sight, keeping the
    casing first entered (#36): a cohort types the same group in
    different cases and must land on one filter value.
    """
    group, _created = Group.objects.get_or_create_casefolded(intake.group)
    return SessionRecord.objects.create(
        session_id=session_id,
        user_name=intake.name,
        level=intake.level,
        group=group,
    )


def record_assessment(record: SessionRecord, kind: str, raw_answer: str, scores: list) -> Assessment:
    """Append one assessable answer to the ledger under ``record``.

    Append-only: a resubmitted answer is a second row, never an update,
    so the last row per kind is the answer the score report reads and the
    earlier ones stay visible as revision history (#38).
    """
    return Assessment.objects.create(
        session=record,
        kind=kind,
        raw_answer=raw_answer,
        scores=list(scores),
    )


def link_previous(current_session_id: str, previous_session_id: str) -> None:
    """Record that ``current_session_id`` replaced ``previous_session_id``.

    Both lookups tolerate a missing row: a reset of a session that never
    reached the ledger must not break the reset.
    """
    previous = SessionRecord.objects.filter(session_id=previous_session_id).first()
    if previous is None:
        return
    SessionRecord.objects.filter(session_id=current_session_id).update(
        previous_session=previous
    )
