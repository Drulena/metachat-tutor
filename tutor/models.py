"""Django models for the MetaChat Tutor application.

The chat pages read Django session storage; the models here are the research
ledger written beside it (ADR-0007): ``Group`` is the filter dimension,
``SessionRecord`` one row per session, ``Assessment`` the scored answers.
Pages never read the ledger.
"""

from __future__ import annotations

from django.db import models, transaction

class GroupManager(models.Manager):
    """Manager that looks groups up casefolded, the way the intake form needs it."""

    def get_or_create_casefolded(self, name: str) -> tuple["Group", bool]:
        """Return the group for ``name`` and whether this call created it.

        Parameters:
            name: The group name as the learner typed it. The lookup is
                casefolded, so "Blue Tigers" and "blue tigers" are one group;
                the row keeps the casing it was first entered with.
        """
        key = name.casefold()
        try:
            return self.get(lookup_key=key), False
        except self.model.DoesNotExist:
            with transaction.atomic():
                return self.create(name=name, lookup_key=key), True


class Group(models.Model):
    """A learner group: the filter dimension the research ledger is cut by.

    The name is display data kept in its first-entered casing; ``lookup_key``
    is the casefolded form that makes the identity, so one group is one row
    however it is spelled. The intake form is the only writer, through
    ``get_or_create_casefolded``.
    """

    objects = GroupManager()

    name: models.CharField = models.CharField(max_length=256)
    lookup_key: models.CharField = models.CharField(max_length=256, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class SessionRecord(models.Model):
    """One session's ledger row: the write-through record kept beside the chat.

    Created when the intake form submits and appended to on every chat
    submit, so ``updated_at`` reads as last activity and a null
    ``finished_at`` is what makes a session abandoned (ADR-0007 decisions 1
    and 7). ``session_id`` is the mint's canonical UUID v7 text - the same
    string the chat pages, the export filename and the Summary carry. The
    chat pages never read this row; the Summary stays the presentation source.
    """

    LEVEL_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]

    session_id: models.CharField = models.CharField(
        max_length=36,
        unique=True,
        help_text="Canonical UUID v7 text; the unique index orders rows by creation.",
    )

    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)
    finished_at: models.DateTimeField = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Stamped on entering the terminal screen; never cleared.",
    )

    user_name: models.CharField = models.CharField(max_length=256)
    level: models.CharField = models.CharField(max_length=32, choices=LEVEL_CHOICES)
    group: models.ForeignKey = models.ForeignKey(
        Group,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sessions",
    )
    previous_session: models.ForeignKey = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="next_sessions",
        help_text="The session this one replaced after a reset.",
    )

    chat_history: models.JSONField = models.JSONField(
        default=list,
        blank=True,
        help_text="Chat entries appended verbatim, append-only, in submit order.",
    )
    reflection: models.TextField = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"SessionRecord({self.session_id}, {self.level}, {self.created_at:%Y-%m-%d})"


class Assessment(models.Model):
    """A scored answer set beside a session: pretest, posttest, later tests.

    ``kind`` stays open - the two choices are what the chat flow scores
    today, and a future test adds a value without touching the schema.
    ``raw_answer`` is what the learner submitted ("a b c"); ``scores`` are
    the numbers derived from it. The selector UI is a later ticket (#40).
    """

    KIND_PRETEST = "pretest"
    KIND_POSTTEST = "posttest"
    KIND_CHOICES = [
        (KIND_PRETEST, "Pretest"),
        (KIND_POSTTEST, "Posttest"),
    ]

    session: models.ForeignKey = models.ForeignKey(
        SessionRecord, on_delete=models.CASCADE, related_name="assessments"
    )
    kind: models.CharField = models.CharField(max_length=32, choices=KIND_CHOICES)
    raw_answer: models.TextField = models.TextField(blank=True, default="")
    scores: models.JSONField = models.JSONField(default=list, blank=True)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "assessments"

    def __str__(self) -> str:
        return f"Assessment({self.session_id}, {self.kind})"
