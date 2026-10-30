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
from unittest import mock

from django.test import TestCase

from .session import SessionStorage
from .test_tutor_session import (
    FakeLLM,
    GENERIC_REJECTION,
    REGISTRATION_OPTIONS,
    ROLE_MENU_COPY,
    ROLE_MENU_INPUTS,
)
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


def _fake_feedback(*args, **kwargs):
    """Stand-in for the LLM feedback callable on HTTP-built sessions."""
    return "Feedback.", False


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

    def test_in_progress_task_keeps_the_next_row_not_started_on_both_pages(self):
        """Issue #14 acceptance: task 1 in progress → task 2 ⬜ on BOTH pages.

        The reported state: analysis task 1 in progress, task 2 never opened.
        The sidebar used to stamp ✅ Completed on task 2 through a positional
        fallback over a completed count while the overview page said ⬜ Not
        Started. Each row now answers for itself, so this state agrees too.
        """
        client = self.client
        _drive(client, ["Alice", "3 4 5", "2", "1", "yes"])  # -> task 1 in progress
        for path in ("/menu/", "/"):  # overview page, chat page (sidebar fragment)
            html = client.get(path).content.decode()
            cell = _task_cell(html, "Task 1: Softening Criticism")
            self.assertIn("badge-in-progress", cell, f"{path} lost task 1's badge")
            cell = _task_cell(html, "Task 2: Aggressive Formatting")
            self.assertIn("badge-not-started", cell, f"{path} understates task 2")
            self.assertNotIn("badge-completed", cell, f"{path} overstates task 2")

    def test_chat_marks_the_option_the_learner_used(self):
        """Issue #14: the chat page marks an option used from the turn's own
        used_value. Anchored per prompt: the mode the learner picked ('1')
        shows used on the mode menu; the mode they did not pick ('2') does
        not — value '2' alone is not unique (the level prompt offers it too)."""
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        html = client.get("/").content.decode()
        self.assertIn(
            f'data-value="1" data-used="true">{REGISTRATION_OPTIONS["1"]}', html
        )
        self.assertNotIn(
            f'data-value="2" data-used="true">{REGISTRATION_OPTIONS["2"]}', html
        )

    def test_menu_has_no_leaked_template_comment(self):
        """Django's {# ... #} comments are single-line; the multi-line header
        in task_group.html rendered as literal text on both pages."""
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        for path in ("/menu/", "/"):
            page = html_module.unescape(client.get(path).content.decode())
            self.assertNotIn("computes nothing", page, f"{path} leaked the template comment")


class ChatOptionRenderingTests(TestCase):
    """Owner review pass (issue #15): utility offers sit in their own row
    after the choices, choices keep the scenario's order, and a finished
    role's option is marked completed."""

    def _last_block(self, html):
        """The current offer's markup: from the last option block to </main>.

        The chat page keeps older turns' option markup on screen, so option
        assertions must be anchored to the current offer only.
        """
        start = html.rindex('<div class="message-options">')
        return html[start:html.index("</main>", start)]

    def _button_markup(self, html):
        """The HTML of every option button in the current offer, in render order."""
        block = self._last_block(html)
        start = 0
        markup = []
        while True:
            i = block.find('class="option-btn', start)
            if i < 0:
                return markup
            j = block.find("</button>", i)
            markup.append(block[i:j])
            start = j + 1

    def _choice_labels(self, html):
        return [m.split(">", 1)[1] for m in self._button_markup(html)
                if "system-btn" not in m and "option-completed" not in m]

    def test_chat_offers_utilities_in_a_separate_row_after_choices(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        html = client.get("/").content.decode()
        block = self._last_block(html)
        choices_div = block.index('<div class="message-options">')
        system_div = block.index('<div class="system-options">')
        self.assertLess(choices_div, system_div, "the utility row must render after the choices")
        between = block[choices_div:system_div]
        self.assertNotIn("Back to Menu", between, "nav buttons must not sit among the choices")

    def test_chat_choices_render_in_scenario_order(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        html = client.get("/").content.decode()
        self.assertEqual(
            self._choice_labels(html)[:4],
            ["Mediator", "Logical Expert", "Idea Generator", "Researcher"],
        )

    def test_finished_role_option_is_marked_completed(self):
        client = self.client
        # Finish role 1 (the feedback accepts 'next'), landing back on the
        # role menu with role_mediator recorded in the ledger. HTTP submits
        # build their own session, so the module's feedback callable is
        # pinned for the request window.
        with mock.patch("tutor.llm.get_llm_feedback", _fake_feedback):
            _drive(client, ROLE_MENU_INPUTS)
            client.post("/", {"user_input": "1"})
            client.post("/", {"user_input": "I mediate the conflict"})
            client.post("/", {"user_input": "next"})
        html = client.get("/").content.decode()
        buttons = self._button_markup(html)
        done = [m for m in buttons if "option-completed" in m]
        self.assertEqual(len(done), 1, f"exactly one completed option, got {len(done)}")
        self.assertIn("Mediator", done[0])
        self.assertNotIn("system-btn", done[0], "a utility offer is never option-completed")
        self.assertNotIn('data-value="2"', done[0], "the untouched role 2 stays open")

    def test_chat_has_no_leaked_template_comment(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        page = html_module.unescape(client.get("/").content.decode())
        self.assertNotIn("computes nothing", page)

    def test_chat_has_no_leaked_offer_comment(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        page = html_module.unescape(client.get("/").content.decode())
        self.assertNotIn("Choices first in the scenario", page)
        self.assertNotIn("own row after them", page)

    def test_options_block_has_a_single_separator(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        html = client.get("/").content.decode()
        block = self._last_block(html)
        between = block[block.index('<div class="message-options">'):
                        block.index('<div class="system-options">')]
        self.assertNotIn("style=", between, "one separator: the utility row adds none")

    def test_back_renders_before_the_advancing_offer(self):
        client = self.client
        # The template's system row renders back/retry first, advancing nav
        # after. role_menu's nav map carries "finish" (✅ Finish) and the
        # synthesised back lands in the same row — back must precede finish.
        # (Feedback rows' "next" is a scenario-loop value → choices row.)
        _drive(client, ROLE_MENU_INPUTS)
        html = client.get("/").content.decode()
        system = self._last_block(html).split('<div class="system-options">', 1)[1]
        self.assertLess(system.index("data-value=\"back\""), system.index("data-value=\"finish\""))

    def test_completed_role_stays_clickable_but_marked(self):
        """A finished role's offer is marked, not dead (issue #15 owner pass):
        the markup stays an enabled button, and clicking it re-opens the role -
        rehearsal is allowed; the role is not de facto inaccessible."""
        client = self.client
        with mock.patch("tutor.llm.get_llm_feedback", _fake_feedback):
            _drive(client, ROLE_MENU_INPUTS)
            client.post("/", {"user_input": "1"})
            client.post("/", {"user_input": "I mediate the conflict"})
            client.post("/", {"user_input": "next"})
            html = client.get("/").content.decode()
            done = [m for m in self._button_markup(html) if "option-completed" in m]
            self.assertEqual(len(done), 1)
            self.assertIn('data-value="1"', done[0], "the finished role stays clickable markup")
            page = client.post("/", {"user_input": "1"}).content.decode()
        self.assertIn("ROLE: Mediator", page, "the finished role re-opens on click")
        self.assertNotIn(ROLE_MENU_COPY, page)


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
        # wire schema (issue #14): exactly the nine Summary fields on the wire —
        # the lifecycle pair and the sections in, the eleven flat fields out.
        self.assertEqual(
            sorted(data["progress"]),
            sorted(
                [
                    "sections", "started", "percentage", "total_steps",
                    "completed_steps_count", "finished",
                    "level", "user_name", "session_id",
                ]
            ),
        )
        self.assertIn("used_value", data["turns"][0])
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
    """A rejected input answers with the row's own copy (ticket #15).

    The copy constants are shared from :mod:`tutor.test_tutor_session` —
    every pinning of the module's strings lives there, once.
    """

    def test_chat_shows_bespoke_copy_beneath_the_input(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)  # ends at role_menu
        client.post("/", {"user_input": "not a role"})
        html = client.get("/").content.decode()
        self.assertIn(ROLE_MENU_COPY, html)
        self.assertLess(html.index("not a role"), html.index(ROLE_MENU_COPY))

    def test_chat_generic_never_inferred(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        client.post("/", {"user_input": "not a role"})
        html = client.get("/").content.decode()
        self.assertNotIn(GENERIC_REJECTION, html)
        self.assertEqual(html.count(ROLE_MENU_COPY), 1)

    def test_chat_pre_registration_has_no_rejection(self):
        client = self.client
        client.get("/")  # auto-start: data_collection, unregistered
        client.post("/", {"user_input": "asdasd"})  # a bare name is accepted as a name
        html = client.get("/").content.decode()
        self.assertNotIn(GENERIC_REJECTION, html)
        self.assertNotIn(ROLE_MENU_COPY, html)

    def test_chat_no_rejection_when_the_answer_lands(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        client.post("/", {"user_input": "1"})  # a role menu choice lands
        html = client.get("/").content.decode()
        self.assertNotIn(ROLE_MENU_COPY, html)
        self.assertNotIn(GENERIC_REJECTION, html)

    def test_chat_nav_state_falls_back_to_generic_copy(self):
        client = self.client
        # Ends at an analysis-feedback state: nav-only accept, row has no copy.
        _drive(client, ROLE_MENU_INPUTS[:8])
        client.post("/", {"user_input": "no such task"})
        html = html_module.unescape(client.get("/").content.decode())
        self.assertIn(GENERIC_REJECTION, html)


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

    def test_main_menu_shows_the_same_zero_state_panel_as_chat(self):
        # The pages cannot disagree (Q6 #15): the main menu gates its
        # progress block on started like the chat sidebar — an
        # auto-started, unregistered session shows the zero-state panel
        # on both, export stays gated on registration on both.
        client = self.client
        menu = client.get("/menu/").content.decode()
        chat = client.get("/").content.decode()
        self.assertIn("steps completed", menu)
        self.assertIn("Overall Progress", chat)
        self.assertNotIn("Export Chat History", menu)
        self.assertNotIn("Export Chat History", chat)


class FaviconTests(TestCase):
    """Every page links the project favicon — a rendered-page rule, the
    tab is the whole surface a browser shows."""

    def test_every_page_links_the_svg_favicon(self):
        _drive(self.client, ROLE_MENU_INPUTS)
        for path in ("/", "/menu/", "/reset/confirm/"):
            html = self.client.get(path).content.decode()
            self.assertIn('rel="icon"', html, path)
            self.assertIn("/static/tutor/favicon.svg", html, path)
