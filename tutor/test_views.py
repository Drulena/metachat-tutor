"""Smoke tests for the thin Django views (menu, export, reset).

The views are thin adapters: each composes the ``TutorSession`` module and
renders its ``Summary`` / turns. These tests seed a session *through the
module* (with a deterministic fake feedback), then exercise each view
read-only and assert the output is faithful to the module's state.

Seam: the Django HTTP views (menu, export, reset, reset_confirm) -- the
public HTTP boundary. The module itself is tested in ``test_tutor_session.py``.
"""

import html as html_module
import re
from dataclasses import asdict
from unittest import mock

from django.test import Client, TestCase

from .session import SessionStorage
from .test_tutor_session import (
    FakeLLM,
    INTAKE,
    GENERIC_REJECTION,
    REGISTRATION_OPTIONS,
    ROLE_MENU_CLOSING_LINE,
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
    session.start(INTAKE)
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


def _visible_text(html: str) -> str:
    """The page's rendered text: script and style blocks and every tag removed.

    The Session ID control (issue #32) keeps the id in an attribute, so an
    assertion on the raw body passes while the id is still on screen. What the
    learner reads is the text, and that is the surface the ticket's "not shown
    by default" question is about.
    """
    stripped = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    stripped = re.sub(r"(?s)<[^>]*>", " ", stripped)
    return html_module.unescape(stripped)


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
        # progress figure from Summary.percentage (3 of 14 steps)
        self.assertContains(resp, "21")

    def test_menu_redirects_a_browser_with_no_intake(self):
        """Ticket #37: the form opens the session, so a browser that has
        never submitted it has no progress to overview.

        Carried over from ``test_menu_on_fresh_session_starts_it``: the menu
        used to mint a session of its own.
        """
        client = self.client
        resp = client.get("/menu/")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/")

    def test_task_row_shows_the_same_status_on_both_pages(self):
        """Issue #14: the sidebar and the overview cannot disagree about a row.

        Drives the session to analysis task 2 — task 1 completed, task 2 in
        progress. Before the Summary answered the status question, the chat
        sidebar inferred status from a completed count and showed task 2 as
        "Completed" while the overview page showed it "Not Started". Both pages
        now render the badge straight from the row's own status.
        """
        client = self.client
        _drive(client, ["3 4 5", "1", "yes", "Answer to task one", "next"])
        for path in ("/menu/", "/chat/"):  # overview page, chat page (sidebar fragment)
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
        _drive(client, ["3 4 5", "1", "yes"])  # -> task 1 in progress
        for path in ("/menu/", "/chat/"):  # overview page, chat page (sidebar fragment)
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
        html = client.get("/chat/").content.decode()
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
        for path in ("/menu/", "/chat/"):
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
        html = client.get("/chat/").content.decode()
        block = self._last_block(html)
        choices_div = block.index('<div class="message-options">')
        system_div = block.index('<div class="system-options">')
        self.assertLess(choices_div, system_div, "the utility row must render after the choices")
        between = block[choices_div:system_div]
        self.assertNotIn("Back to Menu", between, "nav buttons must not sit among the choices")

    def test_chat_choices_render_in_scenario_order(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        html = client.get("/chat/").content.decode()
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
            client.post("/chat/", {"user_input": "1"})
            client.post("/chat/", {"user_input": "I mediate the conflict"})
            client.post("/chat/", {"user_input": "next"})
        html = client.get("/chat/").content.decode()
        buttons = self._button_markup(html)
        done = [m for m in buttons if "option-completed" in m]
        self.assertEqual(len(done), 1, f"exactly one completed option, got {len(done)}")
        self.assertIn("Mediator", done[0])
        self.assertNotIn("system-btn", done[0], "a utility offer is never option-completed")
        self.assertNotIn('data-value="2"', done[0], "the untouched role 2 stays open")

    def test_chat_has_no_leaked_template_comment(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        page = html_module.unescape(client.get("/chat/").content.decode())
        self.assertNotIn("computes nothing", page)

    def test_chat_has_no_leaked_offer_comment(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        page = html_module.unescape(client.get("/chat/").content.decode())
        self.assertNotIn("Choices first in the scenario", page)
        self.assertNotIn("own row after them", page)

    def test_chat_role_menu_closing_line_has_no_backslash(self):
        r"""Issue #33: the role menu's last line renders, with no stray `\`.

        A backslash before a letter is not a Python escape and the Markdown
        filter passes it through, so the rendered page is where the bug shows.
        """
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        page = html_module.unescape(client.get("/chat/").content.decode())
        rendered = ROLE_MENU_CLOSING_LINE.split(", tap")[0]
        self.assertIn(rendered, page, "the closing line must still render")
        self.assertNotIn("\\" + rendered, page, "no literal backslash before it")

    def test_options_block_has_a_single_separator(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        html = client.get("/chat/").content.decode()
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
        html = client.get("/chat/").content.decode()
        system = self._last_block(html).split('<div class="system-options">', 1)[1]
        self.assertLess(system.index("data-value=\"back\""), system.index("data-value=\"finish\""))

    def test_completed_role_stays_clickable_but_marked(self):
        """A finished role's offer is marked, not dead (issue #15 owner pass):
        the markup stays an enabled button, and clicking it re-opens the role -
        rehearsal is allowed; the role is not de facto inaccessible."""
        client = self.client
        with mock.patch("tutor.llm.get_llm_feedback", _fake_feedback):
            _drive(client, ROLE_MENU_INPUTS)
            client.post("/chat/", {"user_input": "1"})
            client.post("/chat/", {"user_input": "I mediate the conflict"})
            client.post("/chat/", {"user_input": "next"})
            html = client.get("/chat/").content.decode()
            done = [m for m in self._button_markup(html) if "option-completed" in m]
            self.assertEqual(len(done), 1)
            self.assertIn('data-value="1"', done[0], "the finished role stays clickable markup")
            # Issue #34: a submission answers with a redirect, so the page the
            # click lands on is the one the redirect resolves to.
            page = client.post("/chat/", {"user_input": "1"}, follow=True).content.decode()
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
        self.assertEqual(data["progress"]["percentage"], 21)
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
        # The registered level once at the payload header (spec #16
        # C1-9 AC2): the export names the session's level without
        # digging into the progress panel.
        self.assertEqual(data["level"], "beginner")
        self.assertEqual(data["level"], data["progress"]["level"])
        # export timestamp
        self.assertIn("export_time", data)
        # download name uses the session id
        self.assertIn(data["session_id"], resp["Content-Disposition"])

    def test_export_before_the_intake_is_refused(self):
        """Ticket #37: an export is a learner's utility, not a probe.

        The file is named after the session id, and a browser that has never
        opened a session has no id to name it: the form answers first.
        Carried over from ``test_export_on_fresh_session_is_empty``, which
        downloaded the empty representation of a session the chat used to
        mint on the first request.
        """
        resp = self.client.get("/export/")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/")


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
        # Ticket #37: a wipe erases the registration facts too, so the
        # learner lands back on the form - emptied, not prefilled.
        self.assertEqual(resp["Location"], "/")
        form = client.get("/")
        self.assertEqual(form.status_code, 200)
        self.assertNotContains(form, "Alice")
        # and the chat stays closed until a new intake opens it
        self.assertEqual(client.get("/chat/").status_code, 302)


class ChatRejectionTests(TestCase):
    """A rejected input answers with the row's own copy (ticket #15).

    The copy constants are shared from :mod:`tutor.test_tutor_session` —
    every pinning of the module's strings lives there, once.
    """

    def test_chat_shows_bespoke_copy_beneath_the_input(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)  # ends at role_menu
        client.post("/chat/", {"user_input": "not a role"})
        html = client.get("/chat/").content.decode()
        self.assertIn(ROLE_MENU_COPY, html)
        self.assertLess(html.index("not a role"), html.index(ROLE_MENU_COPY))

    def test_chat_generic_never_inferred(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        client.post("/chat/", {"user_input": "not a role"})
        html = client.get("/chat/").content.decode()
        self.assertNotIn(GENERIC_REJECTION, html)
        self.assertEqual(html.count(ROLE_MENU_COPY), 1)

    def test_an_accepted_answer_shows_no_rejection_on_the_entry_state(self):
        """Ticket #37: the form, not the chat, collects the name; an answer
        that lands on the entry state adds no rejection banner.

        Carried over from ``test_chat_pre_registration_has_no_rejection``,
        which read the free-text name step behind the form.
        """
        client = self.client
        client.post("/", {"name": "Alice", "group": "Alpha", "level": "beginner"})
        client.post("/chat/", {"user_input": "3 4 5"})  # the pretest answer lands
        html = client.get("/chat/").content.decode()
        self.assertNotIn(GENERIC_REJECTION, html)
        self.assertNotIn(ROLE_MENU_COPY, html)

    def test_chat_no_rejection_when_the_answer_lands(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        client.post("/chat/", {"user_input": "1"})  # a role menu choice lands
        html = client.get("/chat/").content.decode()
        self.assertNotIn(ROLE_MENU_COPY, html)
        self.assertNotIn(GENERIC_REJECTION, html)

    def test_chat_nav_state_falls_back_to_generic_copy(self):
        client = self.client
        # Ends at an analysis-feedback state: nav-only accept, row has no copy.
        _drive(client, ROLE_MENU_INPUTS[:6])
        client.post("/chat/", {"user_input": "no such task"})
        html = html_module.unescape(client.get("/chat/").content.decode())
        self.assertIn(GENERIC_REJECTION, html)


class ChatSubmissionTests(TestCase):
    """Issue #34: a page reload after submitting a message duplicated it.

    The chat view answered a POST with a rendered page, so the entry in the
    browser's history was the POST itself: reload re-submitted it, the module
    ran ``submit()`` a second time and appended the learner turn and its
    tutor reply again. The view
    now answers a submission with a redirect to the chat page
    (POST-Redirect-GET, the shape the reset flow already used — all state
    lives server-side in the ``TutorSession``), so the page a reload
    re-requests is a GET that submits nothing.
    """

    def _turn_count(self, response) -> int:
        """Count every chat message block rendered on the page (user + tutor)."""
        return response.content.decode().count('<div class="message ')

    def test_submit_redirects_to_the_chat_page(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        resp = client.post("/chat/", {"user_input": "1"})  # a role menu choice lands
        self.assertEqual(resp.status_code, 302, "a submission must not render the page")
        self.assertEqual(resp["Location"], "/chat/")
        # Nothing to re-issue: the history entry is a header, not a form page.
        self.assertEqual(resp.content, b"")

    def test_cached_restore_clears_the_loading_overlay(self):
        """A submission redirects, so Back/Forward restores the chat page from
        the bfcache: a snapshot taken mid-submission, loading overlay included.
        The page the browser restores ships the handler that clears it."""
        _drive(self.client, [])  # an intake-opened session: the page renders
        html = self.client.get("/chat/").content.decode()
        self.assertIn("pageshow", html)
        self.assertIn("persisted", html)

    def test_blank_submit_redirects_and_appends_nothing(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        before = self._turn_count(client.get("/chat/"))
        resp = client.post("/chat/", {"user_input": "   "})
        self.assertEqual(resp.status_code, 302, "an empty submission redirects too")
        self.assertEqual(self._turn_count(client.get("/chat/")), before)

    def test_reload_after_submit_appends_one_exchange(self):
        client = self.client
        _drive(client, ROLE_MENU_INPUTS)
        before = self._turn_count(client.get("/chat/"))
        resp = client.post("/chat/", {"user_input": "1"}, follow=True)
        # The submit answers with a redirect to the chat page - the page is a
        # GET of its own since ticket #37, so the chain names /chat/.
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.redirect_chain, [("/chat/", 302)])
        self.assertEqual(
            self._turn_count(resp), before + 2, "one user turn plus one tutor reply"
        )
        # The reload the reporter hit: the browser re-issues the page it landed
        # on, which after the redirect is a GET of the chat page.
        self.assertEqual(
            self._turn_count(client.get("/chat/")), before + 2, "the reload appended nothing"
        )


class ChatSidebarGateTests(TestCase):
    """Grill Q6 (#15): the sidebar progress panel gates on started, not on
    registration - a session that exists shows the zero-state rows, agreeing
    with the main menu; the export link stays gated on registration.

    Ticket #37 moved registration in front of the chat: an intake-opened
    session carries a participant name from its first turn, so the panel and
    the utility pair answer together. A browser with no intake never sees
    these pages at all - the gate redirects it to the form.
    """

    def test_chat_shows_the_panel_after_the_intake(self):
        """The panel and the export entry answer a session the form opened."""
        client = self.client
        _drive(client, [])
        html = client.get("/chat/").content.decode()
        self.assertIn("Overall Progress", html)
        self.assertIn("Export Chat History", html)

    def test_registered_chat_offers_export(self):
        client = self.client
        _drive(client, [])
        self.assertIn("Export Chat History", client.get("/chat/").content.decode())

    def test_registered_chat_offers_reset_beside_export(self):
        """The chat side panel offers reset, beside export, to the confirm page.

        Reset is the documented escape from a wrong level pick (GLOSSARY
        "point of no return"), so a registered learner reaches the
        reset-confirm page from the chat page: the link pairs with the export
        entry — same block, same registration gate, ``.reset-btn`` styling —
        and targets the confirm view, never the wipe endpoint itself. (#26)
        """
        client = self.client
        _drive(client, [])
        page = html_module.unescape(client.get("/chat/").content.decode())
        self.assertIn("Reset Session", page)
        self.assertIn('href="/reset/confirm/"', page)
        self.assertIn('class="reset-btn"', page)
        self.assertNotIn('href="/reset/"', page)  # the confirm page, not the wipe
        # "beside": the reset link follows the export entry it pairs with
        self.assertLess(page.index("Export Chat History"), page.index("Reset Session"))
        # {# … #} is single-line: the block's header must not reach the learner
        self.assertNotIn("Utility offers, paired", page, "the template comment leaked")

    def test_a_browser_with_no_intake_never_sees_the_utility_pair(self):
        """The reset offer shares export's gate: registration, not ``debug``.

        An intake-pending browser is sent to the form, which offers neither
        link; both land together once the Summary carries a participant
        name. The gate is the Summary, never Django's debug flag. (#26,
        ticket #37 for the new shape.)
        """
        resp = self.client.get("/chat/")
        self.assertEqual(resp.status_code, 302)
        page = self.client.get("/").content.decode()
        self.assertNotIn("Reset Session", page)
        self.assertNotIn("Export Chat History", page)

    def test_main_menu_shows_the_same_panel_as_chat(self):
        # The pages cannot disagree (Q6 #15, ticket #37): the main menu gates
        # its progress block on started like the chat sidebar, and both offer
        # the utility pair once the form has opened the session.
        client = self.client
        _drive(client, [])
        menu = client.get("/menu/").content.decode()
        chat = client.get("/chat/").content.decode()
        self.assertIn("steps completed", menu)
        self.assertIn("Overall Progress", chat)
        # The utility pair is the chat sidebar's; the overview page never offered it.
        self.assertNotIn("Export Chat History", menu)
        self.assertIn("Export Chat History", chat)


class FaviconTests(TestCase):
    """Every page links the project favicon — a rendered-page rule, the
    tab is the whole surface a browser shows."""

    def test_every_page_links_the_svg_favicon(self):
        _drive(self.client, ROLE_MENU_INPUTS)
        # An intake-opened browser: the form page answers with a redirect, so
        # its shell is read from a fresh client - every page in its own state.
        responses = [self.client.get(path, follow=True) for path in ("/chat/", "/menu/", "/terms/", "/reset/confirm/")]
        responses.append(Client().get("/"))
        for html in [r.content.decode() for r in responses]:
            self.assertIn('rel="icon"', html)
            self.assertIn("/static/tutor/favicon.svg", html)

class SessionIdInfoControlTests(TestCase):
    """Issue #32: the menu keeps the Session ID off the page, beside an info
    button on the Participant row.

    The report: the id printed as a plain line above Participant is noise the
    learner never needs and a string anyone looking at their screen reads. The
    fragment now offers an info control on the Participant row - the id reveals
    on hover/focus and lands on the clipboard on click. It reaches the page as
    the control's data attribute only, so no page text carries it.

    The fragment is included twice on the chat page (sidebar and mobile menu),
    so every assertion here is a claim about both instances.
    """

    def _registered_chat(self, client):
        """Drive a registered session and return (page html, the session id)."""
        _drive(client, [])
        sid = client.get("/export/").json()["session_id"]
        self.assertTrue(sid, "the module's id is what the control carries")
        return client.get("/chat/").content.decode(), sid

    def _participant_row(self, html):
        """The Participant row's markup, control included."""
        start = html.index('<p class="participant-row">')
        return html[start:html.index("</p>", start)]

    def test_the_plain_session_id_line_left_the_menu(self):
        client = self.client
        html, sid = self._registered_chat(client)
        self.assertNotIn(sid, _visible_text(html), "the id must not be on screen by default")
        self.assertNotIn("Session ID", _visible_text(html), "no label line left above Participant")
        self.assertIn("Participant:", _visible_text(html), "the Participant row itself stays")
        self.assertIn("Alice", _visible_text(html))

    def test_the_id_reaches_the_page_only_as_the_controls_data(self):
        client = self.client
        html, sid = self._registered_chat(client)
        self.assertEqual(
            html.count(f'data-session-id="{sid}"'), 2,
            "the id rides the control of each menu instance, and nothing else",
        )
        self.assertNotIn("<strong>Session ID:</strong>", html)
        # The reveal is JS-fed: an empty tooltip is the page's default text.
        self.assertIn('<span class="session-id-tooltip" role="tooltip"', html)
        self.assertNotIn(f">{sid}<", html, "no element's text carries the id")

    def test_the_control_sits_on_the_participant_row(self):
        client = self.client
        html, _ = self._registered_chat(client)
        row = self._participant_row(html)
        self.assertIn("Participant:", row)
        self.assertIn("Alice", row)
        self.assertIn('class="session-id-btn"', row, "the control belongs to this row")

    def test_the_control_is_a_real_button_with_an_accessible_name(self):
        client = self.client
        html, _ = self._registered_chat(client)
        row = self._participant_row(html)
        self.assertIn('<button type="button" class="session-id-btn"', row)
        self.assertIn('aria-label="Session ID', row, "the control names itself to a reader")

    def test_the_control_is_gated_on_the_participant_row(self):
        """No Participant row, no control: an unregistered session has the
        summary's empty name, and the row it hangs on is absent."""
        html = self.client.get("/chat/").content.decode()  # auto-started, unregistered
        self.assertNotIn("Participant:", _visible_text(html))
        # Asserted as rendered markup: the page's script block names both the
        # row's class and the control's, and it ships on an unregistered page.
        self.assertNotIn('<p class="participant-row">', html)
        self.assertNotIn('<button type="button" class="session-id-btn"', html)

    def test_both_menu_instances_carry_the_control(self):
        """The sidebar and the mobile menu include one fragment: the control
        behaves the same in both, so both must render it."""
        client = self.client
        html, _ = self._registered_chat(client)
        sidebar = html[html.index('<aside class="sidebar">'):html.index("</aside>")]
        mobile = html[html.index('<div id="mobile-menu"'):html.index("<script>")]
        self.assertIn('class="session-id-btn"', sidebar, "the desktop sidebar lost the control")
        self.assertIn('class="session-id-btn"', mobile, "the mobile menu lost the control")

    def test_the_reveal_and_copy_handlers_ship_with_the_page(self):
        """chat.html's script block is the app's only JS home; the control's
        reveal and clipboard behaviour is declared there, on the same page the
        fragment renders on."""
        client = self.client
        html, _ = self._registered_chat(client)
        script = html[html.index("<script>"):html.index("</script>")]
        self.assertIn(".session-id-btn", script, "the control has no handler")
        self.assertIn("data-session-id", script, "the handler never reads the id")
        self.assertIn("navigator.clipboard", script, "nothing writes the clipboard")

