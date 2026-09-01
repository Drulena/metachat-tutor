"""Django models for the MetaChat Tutor application.

The app primarily relies on Django sessions for state management.
``SessionRecord`` provides an optional persistent store for exported
session data (e.g. for research analysis).
"""

from __future__ import annotations

from django.db import models


class SessionRecord(models.Model):
    """Stores an exported MetaChat Tutor session for research purposes.

    Each record corresponds to one completed tutoring session. The full
    conversation history and scoring data are kept as JSON blobs so the
    schema stays flexible across scenario changes.
    """

    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    user_name: models.CharField = models.CharField(max_length=256)
    level: models.CharField = models.CharField(
        max_length=32,
        choices=[
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
        ],
    )

    pretest_scores: models.JSONField = models.JSONField(
        default=list,
        blank=True,
        help_text="Three integers [1-5] from the pre-test.",
    )
    posttest_scores: models.JSONField = models.JSONField(
        default=list,
        blank=True,
        help_text="Three integers [1-5] from the post-test.",
    )

    chat_history: models.JSONField = models.JSONField(
        default=list,
        blank=True,
        help_text="Full conversation log as a list of message dicts.",
    )
    reflection: models.TextField = models.TextField(blank=True, default="")

    session_key: models.CharField = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Django session key associated with this record.",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"SessionRecord({self.user_name}, {self.level}, {self.created_at:%Y-%m-%d})"
        )
