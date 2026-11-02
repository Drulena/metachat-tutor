"""The app's own configuration: the seats at the desk are the app's to set.

ADR-0007 decision 9 splits the research admin in two. A researcher reads the
ledger and nothing else; a maintainer - a superuser, the account that owns the
deployment - is the one who deletes the abandoned rows a filter has selected.
A permission group is configuration, and the app is the thing that knows what
its own models need, so the app keeps that configuration in step.

The place Django gives for work that has to happen once an app's permissions
exist is the ``post_migrate`` signal: the content types and the ``view_``
permissions are written in its own receiver phase, so a data migration cannot
promise they are there. The signal can.
"""

from __future__ import annotations

from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate

#: The name of the group the desk ships. A researcher account is made staff and
#: put in this group; the group, not the account, carries the power.
RESEARCHER_GROUP = "Researcher"

#: The whole of the researcher's power: reading the three ledger models.
#: ``add``/``change``/``delete`` are absent by design - the intake form and the
#: chat write the ledger (decision 1), and cleanup is the maintainer's act
#: (decision 7) - so a researcher who could write would be editing research
#: data, which is the one thing this desk is built to prevent.
RESEARCHER_PERMISSIONS = ("view_sessionrecord", "view_group", "view_assessment")


def ensure_researcher_group(sender, *, using: str, **kwargs) -> None:
    """State the researcher group's permissions, on every migrate.

    The app owns this group's permission list and restates it from
    ``RESEARCHER_PERMISSIONS`` on every run, so a hand-added grant is reset by
    the next migrate: "the researcher can edit the ledger" is not a state this
    app ships, and a deploy that quietly accumulates grants is how a research
    export starts leaking.

    One run per migrate: ``post_migrate`` fires for every application, and only
    the tutor app's sender is the one whose ledger permissions are being set.
    ``using`` is the alias just migrated; the ledger lives on the project's
    default, and a group written to another database is not this desk's seat.
    """
    if sender.name != "tutor" or using != DEFAULT_DB_ALIAS:
        return

    from django.contrib.auth.models import Group, Permission

    group, _created = Group.objects.using(using).get_or_create(name=RESEARCHER_GROUP)
    views = list(
        Permission.objects.using(using).filter(
            content_type__app_label="tutor",
            codename__in=RESEARCHER_PERMISSIONS,
        )
    )
    group.permissions.set(views)


class TutorConfig(AppConfig):
    """The tutor app: the chat, the ledger, and the desk over it."""

    name = "tutor"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        """Keep the desk's researcher group in step with every migration."""
        post_migrate.connect(
            ensure_researcher_group, dispatch_uid="tutor.ensure_researcher_group"
        )
