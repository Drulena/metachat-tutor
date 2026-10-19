"""Smoke tests for the thin Django views (menu, export, reset).

The views are thin adapters: each composes the ``TutorSession`` module and
renders its ``Summary`` / turns. These tests seed a session *through the
module* (with a deterministic fake feedback), then exercise each view
read-only and assert the output is faithful to the module's state.

Seam: the Django HTTP views (menu, export, reset, reset_confirm) -- the
public HTTP boundary. The module itself is tested in ``test_tutor_session.py``.
"""

from dataclasses import asdict

from django.test import TestCase

from .session import SessionStorage
from .test_tutor_session import ROLE_MENU_INPUTS
from .tutor_session import TutorSession


class _FakeLLM:
    """Deterministic feedback callable for view tests."""

    def __init__(self, text="Feedback for the answer."):
        self.text = text
        self.calls = []

    def __call__(self, user_answer, role_name, user_name, level, task_question=None):
        self.calls.append((user_answer, role_name, user_name, level))
        return (self.text, False)


def _drive(client, inputs):
    """Seed a ``TutorSession`` on the Django test client's session store.

    Returns the module session. The store is saved so the views (which build
    their own ``TutorSession`` over ``request.session``) observe the same state.
    """
    store = client.session
    fake = _FakeLLM()
    session = TutorSession(SessionStorage(store), fake)
    session.start()
    for text in inputs:
        session.submit(text)
    store.save()
    return session


class MainMenuViewTests(TestCase):
    def test_menu_renders_summary(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        resp = client.get("/menu/")
        self.assertEqual(resp.status_code, 200)
        # participant identity from Summary
        self.assertContains(resp, "Alice")
        # task labels from Summary.analysis_tasks / role_tasks
        self.assertContains(resp, "Task 1: Softening Criticism")
        self.assertContains(resp, "Task 2: Aggressive Formatting")
        self.assertContains(resp, "Mediator")
        # progress figure from Summary.percentage (4 of 15 steps)
        self.assertContains(resp, "26")

    def test_menu_on_fresh_session_starts_it(self):
        client = self.client
        resp = client.get("/menu/")
        self.assertEqual(resp.status_code, 200)


class ExportViewTests(TestCase):
    def test_export_composes_turns_and_progress(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        resp = client.get("/export/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # session identity from Summary
        self.assertTrue(data["session_id"])
        # turns composed from the module
        self.assertIsInstance(data["turns"], list)
        self.assertGreater(len(data["turns"]), 0)
        for turn in data["turns"]:
            self.assertIn("role", turn)
            self.assertIn("message", turn)
        # progress composed from Summary
        self.assertEqual(data["progress"]["percentage"], 26)
        # export timestamp
        self.assertIn("export_time", data)
        # download name uses the session id
        self.assertIn(data["session_id"], resp["Content-Disposition"])

    def test_export_on_fresh_session_is_empty(self):
        client = self.client
        resp = client.get("/export/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["turns"], [])
        self.assertEqual(data["progress"]["percentage"], 0)


class ResetViewTests(TestCase):
    def test_get_reset_redirects_to_confirm(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        resp = client.get("/reset/")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/reset/confirm/")

    def test_reset_confirm_shows_summary(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        resp = client.get("/reset/confirm/")
        self.assertEqual(resp.status_code, 200)
        # the confirmation page shows what will be wiped
        self.assertContains(resp, "Alice")

    def test_post_reset_clears_session(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        resp = client.post("/reset/")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/")
        # the session is gone: chat view starts a fresh one (no Alice)
        resp = client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Alice")
