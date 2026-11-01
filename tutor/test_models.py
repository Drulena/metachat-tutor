"""Tests for the session ledger schema: Group, SessionRecord, Assessment.

ADR-0007 decisions 3, 5, 6 and 8 define the shape, and #36 states the
contract: the tables exist from a single ``0001_initial``, group names are
casefold-unique while keeping the first-entered casing, ``session_id`` is
the canonical 36-character UUID v7 text, and ``finished_at`` starts null
because a null stamp is what makes a session abandoned. Tests go through
the public entry points - the manager helper, the ORM, and ``migrate``.
"""

from __future__ import annotations

import os
import tempfile

from django.core.management import call_command
from django.db import IntegrityError, connections, transaction
from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase, TestCase

from .ids import uuid7
from .models import Assessment, Group, SessionRecord
from .test_ids import CANONICAL_TEXT


class GroupTests(TestCase):
    """Casefold-unique group rows that keep the casing they were entered in."""

    def test_lookup_returns_the_existing_row_for_a_differently_cased_name(self):
        """A name that differs only in case reuses the row rather than minting one."""
        first, created = Group.objects.get_or_create_casefolded("Group Alpha")
        self.assertTrue(created)
        reused, re_created = Group.objects.get_or_create_casefolded("GROUP ALPHA")
        self.assertFalse(re_created)
        self.assertEqual(reused.pk, first.pk)
        self.assertEqual(Group.objects.count(), 1)

    def test_lookup_keeps_the_first_entered_casing(self):
        """The stored name is the casing of the first submission, not the lookup."""
        Group.objects.get_or_create_casefolded("Blue Tigers")
        group, _ = Group.objects.get_or_create_casefolded("blue tigers")
        self.assertEqual(group.name, "Blue Tigers")

    def test_names_beyond_case_stay_separate(self):
        """Groups that differ by more than case are distinct rows."""
        blue, _ = Group.objects.get_or_create_casefolded("Blue Tigers")
        red, created = Group.objects.get_or_create_casefolded("Red Tigers")
        self.assertTrue(created)
        self.assertNotEqual(blue.pk, red.pk)
        self.assertEqual(sorted(g.name for g in Group.objects.all()), ["Blue Tigers", "Red Tigers"])

class SessionRecordTests(TestCase):
    """One ledger row per session: id, level, timestamps, group, chain."""

    def test_row_is_addressed_by_the_canonical_v7_text(self):
        """The session id column carries the 36-character v7 text the mint gives."""
        session_id = uuid7()
        record = SessionRecord.objects.create(
            session_id=session_id, level="beginner", user_name="Stacy"
        )
        self.assertRegex(record.session_id, CANONICAL_TEXT)
        self.assertEqual(
            SessionRecord.objects.get(session_id=session_id).pk, record.pk
        )

    def test_two_rows_cannot_share_a_session_id(self):
        """The session id is the unique handle the export filename is built from."""
        taken = SessionRecord.objects.create(
            session_id=uuid7(), level="beginner", user_name="Stacy"
        )
        with transaction.atomic(), self.assertRaises(IntegrityError):
            SessionRecord.objects.create(
                session_id=taken.session_id, level="advanced", user_name="Ben"
            )

    def test_a_fresh_row_is_unfinished_and_chains_to_the_session_it_replaces(self):
        """A null finished_at marks an open session; previous_session is the reset trail."""
        abandoned = SessionRecord.objects.create(
            session_id=uuid7(), level="beginner", user_name="Stacy"
        )
        successor = SessionRecord.objects.create(
            session_id=uuid7(),
            level="beginner",
            user_name="Stacy",
            previous_session=abandoned,
        )
        self.assertIsNone(successor.finished_at)
        self.assertEqual(successor.previous_session.pk, abandoned.pk)
        self.assertEqual(list(abandoned.next_sessions.all()), [successor])

    def test_row_keeps_its_group_name_and_chat_entries_verbatim(self):
        """The group links by key; chat_history holds the entries as the chat stored them."""
        group, _ = Group.objects.get_or_create_casefolded("Blue Tigers")
        entry = {
            "role": "user",
            "content": "Stacy 101",
            "state": "pretest",
            "timestamp": "2026-01-01T00:00:00",
        }
        record = SessionRecord.objects.create(
            session_id=uuid7(), level="beginner", user_name="Stacy",
            group=group, chat_history=[entry],
        )
        record.refresh_from_db()
        self.assertEqual(record.group.name, "Blue Tigers")
        self.assertEqual(record.chat_history, [entry])

    def test_row_starts_with_activity_timestamps_and_no_reflection(self):
        """created_at and updated_at exist from the start; reflection is empty text."""
        record = SessionRecord.objects.create(
            session_id=uuid7(), level="intermediate", user_name="Stacy"
        )
        record.refresh_from_db()
        self.assertIsNotNone(record.created_at)
        self.assertIsNotNone(record.updated_at)
        self.assertEqual(record.reflection, "")


class AssessmentTests(TestCase):
    """Scored answers as child rows beside the session, pretest and posttest."""

    def test_assessment_hangs_off_its_session_row(self):
        """An assessment names its session, kind, raw answer and scores."""
        record = SessionRecord.objects.create(
            session_id=uuid7(), level="beginner", user_name="Stacy"
        )
        Assessment.objects.create(
            session=record, kind="pretest", raw_answer="a b c", scores=[1, 2, 3]
        )
        Assessment.objects.create(
            session=record, kind="posttest", raw_answer="d e f", scores=[4, 5, 5]
        )
        kinds = {a.kind: a for a in record.assessments.all()}
        self.assertEqual(sorted(kinds), ["posttest", "pretest"])
        self.assertEqual(kinds["pretest"].raw_answer, "a b c")
        self.assertEqual(kinds["posttest"].scores, [4, 5, 5])
        self.assertIsNotNone(kinds["pretest"].created_at)

    def test_kind_stays_open_for_future_tests(self):
        """The kind column is not locked to the two current assessments."""
        record = SessionRecord.objects.create(
            session_id=uuid7(), level="beginner", user_name="Stacy"
        )
        row = Assessment.objects.create(
            session=record, kind="placement", raw_answer="a", scores=[3]
        )
        row.refresh_from_db()
        self.assertEqual(row.kind, "placement")


class FreshDatabaseMigrateTests(SimpleTestCase):
    """A brand-new database gains the ledger tables from one initial migration."""

    alias = "fresh_ledger_database"
    databases: set[str] = {"default"}

    def setUp(self) -> None:
        """Name a database file that does not exist yet."""
        self.database = os.path.join(
            tempfile.gettempdir(), f"fresh_ledger_{id(self)}.sqlite3"
        )
        if os.path.exists(self.database):
            os.unlink(self.database)

    def tearDown(self) -> None:
        """Close the connection, then drop the file it was built from."""
        if self.alias in connections.databases:
            connections[self.alias].close()
            del connections.databases[self.alias]
        if os.path.exists(self.database):
            os.unlink(self.database)

    def test_migrating_a_fresh_database_creates_the_three_ledger_tables(self):
        """``migrate`` on an empty file builds Group, SessionRecord, Assessment."""
        connections.databases[self.alias] = {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": self.database,
            "ATOMIC_REQUESTS": False,
            "CONN_MAX_AGE": 0,
            "OPTIONS": {},
            "TIME_ZONE": None,
            "AUTOCOMMIT": True,
            "CONN_HEALTH_CHECKS": False,
            "init_command": None,
            "alias": self.alias,
        }
        call_command("migrate", database=self.alias, verbosity=0)
        tables = connections[self.alias].introspection.table_names()
        self.assertIn("tutor_group", tables)
        self.assertIn("tutor_sessionrecord", tables)
        self.assertIn("tutor_assessment", tables)

    def test_the_app_has_one_initial_migration_and_nothing_older(self):
        """The greenfield history starts at 0001_initial with no shim migrations."""
        loader = MigrationLoader(connections["default"])
        names = sorted(
            name for (app, name) in loader.disk_migrations if app == "tutor"
        )
        self.assertEqual(names, ["0001_initial"])