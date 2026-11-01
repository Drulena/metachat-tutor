"""Intake form tests: the front page, its gates and the row it opens (ticket #37).

The learner is known before the first message, so every test here starts on
the front page and reads what the chat and the ledger say afterwards. Uses the
Django test client, which keeps one browser session (cookies) across requests.
"""

import json

from django.test import TestCase

from .models import Group, SessionRecord


class IntakeFormTests(TestCase):
    """What the front page asks and what it refuses."""

    def test_front_page_offers_name_group_and_level(self):
        """A visitor with no session gets the intake form on ``/``."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "intake-form")
        self.assertContains(response, "Your name")
        self.assertContains(response, "Group")
        self.assertContains(response, "Beginner")

    def test_front_page_links_the_data_collection_terms(self):
        """Consent is collected by the footer link the form ships with."""
        response = self.client.get("/")
        self.assertContains(response, "/terms/")
        terms = self.client.get("/terms/")
        self.assertEqual(terms.status_code, 200)
        self.assertContains(terms, "data collection")

    def test_submissions_without_the_required_answers_are_refused(self):
        """Blank name, blank group and a missing level never open a chat."""
        for payload in (
            {"name": "", "group": "Alpha", "level": "beginner"},
            {"name": "Alice", "group": "", "level": "beginner"},
            {"name": "Alice", "group": "Alpha", "level": ""},
            {"name": "Alice", "group": "Alpha", "level": "wizard"},
        ):
            response = self.client.post("/", payload)
            self.assertEqual(response.status_code, 200, payload)
            self.assertContains(response, "intake-form")
            self.assertEqual(SessionRecord.objects.count(), 0, payload)


class IntakeOpensTheChatTests(TestCase):
    """A submission opens the chat and the ledger row beside it."""

    def submit(
        self, name: str = "Alice", group: str = "Alpha", level: str = "beginner"
    ):
        """Submit the intake form and return the redirect."""
        return self.client.post(
            "/", {"name": name, "group": group, "level": level}
        )

    def test_submission_lands_on_the_chat_greeted_by_the_typed_name(self):
        """The first chat screen greets the learner by the name they typed."""
        response = self.submit()
        self.assertRedirects(response, "/chat/")
        chat = self.client.get("/chat/")
        self.assertContains(chat, "Nice to meet you, Alice")

    def test_submission_opens_a_ledger_row_with_group_and_level(self):
        """The row carries the group, the level and the id the chat shows."""
        self.submit(group="Alpha")
        row = SessionRecord.objects.get()
        self.assertEqual(row.user_name, "Alice")
        self.assertEqual(row.level, "beginner")
        self.assertEqual(row.group.name, "Alpha")
        self.assertIsNone(row.finished_at)
        export = self.client.get("/export/")
        self.assertEqual(export.status_code, 200)
        self.assertEqual(json.loads(export.content)["session_id"], row.session_id)

    def test_a_reused_group_name_gains_a_row_not_a_second_group(self):
        """A differently-cased repeat of a known group reuses the row."""
        Group.objects.create(name="Alpha crew", lookup_key="alpha crew")
        self.submit(group="ALPHA CREW")
        self.assertEqual(Group.objects.count(), 1)
        self.assertEqual(SessionRecord.objects.get().group.name, "Alpha crew")

    def test_the_pretest_is_the_first_question_the_chat_asks(self):
        """Registration is behind: the chat asks the pretest, not the name."""
        self.submit()
        chat = self.client.get("/chat/")
        self.assertContains(chat, "PRE-TEST")


class ChatGateTests(TestCase):
    """Every chat view waits for the intake form; the reset returns to it."""

    def test_chat_pages_redirect_to_the_front_page_while_intake_is_pending(self):
        """A fresh browser sees the intake form, never a bare chat."""
        for path in ("/chat/", "/menu/", "/export/"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302, path)
            self.assertEqual(response.url, "/", path)

    def test_reset_starts_from_a_fresh_intake_form(self):
        """After a reset the front page asks again, empty."""
        self.client.post("/", {"name": "Alice", "group": "Alpha", "level": "beginner"})
        self.client.post("/reset/")
        response = self.client.get("/")
        self.assertContains(response, "intake-form")
        self.assertNotContains(response, "value=\"Alice\"")
        self.assertRedirects(self.client.get("/chat/"), "/")
