"""Smoke tests for the thin Django views (menu, export, reset).

The views are thin adapters: each composes the ``TutorSession`` module and
renders its ``Summary`` / turns. These tests seed a session *through the
module* (with a deterministic fake feedback), then exercise each view
read-only and assert the output is faithful to the module's state.

Seam: the Django HTTP views (menu, export, reset, reset_confirm) -- the
public HTTP boundary. The module itself is tested in ``test_tutor_session.py``.
"""

import html as html_module
from dataclasses import asdict

from django.test import TestCase

from .session import SessionStorage
from .test_tutor_session import FakeLLM, ROLE_MENU_INPUTS
from .tutor_session import TutorSession


def _drive(client, inputs):
    """Seed a ``TutorSession`` on the Django test client's session store.

    Returns the module session. The store is saved so the views (which build
    their own ``TutorSession`` over ``request.session``) observe the same state.
    """
    store = client.session
    fake = FakeLLM()
    session = TutorSession(SessionStorage(store), fake)
    session.start()
    for text in inputs:
        session.submit(text)
    store.save()
    return session


def _task_cell(html: str, label: str) -> str:
    """The ``<li class="task-item">`` block that carries ``label``."""
    start = html.index(label)
    begin = html.rindex('<li class="task-item">', 0, start)
    end = html.index("</li>", start)
    return html[begin:end]


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

    def test_task_row_shows_the_same_status_on_both_pages(self):
        """Issue #14: the sidebar and the overview cannot disagree about a row.

        Drives the session to analysis task 2 — task 1 completed, task 2 in
        progress. Before the Summary answered the status question, the chat
        sidebar inferred status from a completed count and showed task 2 as
        "Completed" while the overview page showed it "Not Started". Both pages
        now render the badge straight from the row's own status.
        """
        client = self.client
        _drive(client, ["Alice", "3 4 5", "2", "1", "yes", "Answer to task one", "next"])
        for path in ("/menu/", "/"):  # overview page, chat page (sidebar fragment)
            html = client.get(path).content.decode()
            cell = _task_cell(html, "Task 2: Aggressive Formatting")
            self.assertIn("badge-in-progress", cell, f"{path} lost the in-progress badge")
            self.assertNotIn("badge-completed", cell, f"{path} overstates task 2")
            self.assertNotIn("badge-not-started", cell, f"{path} understates task 2")

    def test_chat_marks_the_option_the_learner_used(self):
        """Issue #14: the chat page marks an option used from the turn's own
        used_value. Anchored per prompt: the mode the learner picked ('1')
        shows used on the mode menu; the mode they did not pick ('2') does
        not — value '2' alone is not unique (the level prompt offers it too)."""
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        html = client.get("/").content.decode()
        self.assertIn('data-value="1" data-used="true">Step1️⃣: ANALYSIS', html)
        self.assertNotIn('data-value="2" data-used="true">Step2️⃣', html)


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
        self.assertTrue(data["progress"]["started"])
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
        self.assertFalse(data["progress"]["started"])


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


class ChatRejectionTests(TestCase):
    """A rejected input answers with the row's own copy (ticket #15)."""

    ROLE_MENU_COPY = "Choose one of the numbered roles, finish, or back."
    GENERIC = (
        "That answer is not recognized: choose one of the offered options, type "
        "'back', 'finish', 'restart' (to erase and start over), 'export' (to "
        "download the transcript), 'help' (for a summary of the rules), 'idea' "
        "(to generate an idea for the assignments, when the task asks for one), "
        "or 'next' (to advance one page). In data collection, type 'name <your "
        "name>'. The task's own options are shown beneath the question."
    )

    def test_chat_shows_bespoke_copy_beneath_the_input(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)  # ends at role_menu
        client.post("/", {"user_input": "not a role"})
        html = client.get("/").content.decode()
        self.assertIn(self.ROLE_MENU_COPY, html)
        self.assertLess(html.index("not a role"), html.index(self.ROLE_MENU_COPY))

    def test_chat_generic_never_inferred(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        client.post("/", {"user_input": "not a role"})
        html = client.get("/").content.decode()
        self.assertNotIn(self.GENERIC, html)
        self.assertEqual(html.count(self.ROLE_MENU_COPY), 1)

    def test_chat_pre_registration_has_no_rejection(self):
        client = self.client
        client.get("/")  # auto-start: data_collection, unregistered
        client.post("/", {"user_input": "asdasd"})  # a bare name is accepted as a name
        html = client.get("/").content.decode()
        self.assertNotIn(self.GENERIC, html)
        self.assertNotIn(self.ROLE_MENU_COPY, html)

    def test_chat_no_rejection_when_the_answer_lands(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        client.post("/", {"user_input": "1"})  # a role menu choice lands
        html = client.get("/").content.decode()
        self.assertNotIn(self.ROLE_MENU_COPY, html)
        self.assertNotIn(self.GENERIC, html)

    def test_chat_nav_state_falls_back_to_generic_copy(self):
        client = self.client
        # Ends at an analysis-feedback state: nav-only accept, row has no copy.
        _drive(client, ROLE_MENU_INPUTS[:8])
        client.post("/", {"user_input": "no such task"})
        html = html_module.unescape(client.get("/").content.decode())
        self.assertIn(self.GENERIC, html)


class ChatSidebarGateTests(TestCase):
    """Grill Q6 (#15): the sidebar progress panel gates on started, not on
    registration — a session that exists shows the zero-state rows, agreeing
    with the main menu; the export link stays gated on registration."""

    def test_chat_shows_the_panel_before_registration(self):
        client = self.client
        html = client.get("/").content.decode()  # auto-start, unregistered
        self.assertIn("Overall Progress", html)
        self.assertNotIn("Export Chat History", html)

    def test_registered_chat_offers_export(self):
        client = self.client
        _drive(client, ["Alice"])
        self.assertIn("Export Chat History", client.get("/").content.decode())
