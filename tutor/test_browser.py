"""The learner pages, painted by a real browser.

The Django test client hands back bytes and never parses them, so a page a browser
refuses to paint can pass every view test. The tutor.test_pages module parses the
markup and covers structure; this module asks a real browser: the tab label, the
text a learner reads, the stylesheet the layout used, and every console error,
thrown script, dead request and 4xx the page produced.

Two constraints shape the code:

#. The browser is the one already installed on the machine - the msedge channel by
   default, overridable with BROWSER_CHANNEL - headless, one tab at a time: no 150
   MB browser download and no parallel browsers. A machine with neither Edge nor
   Chrome skips the module, so "manage.py test tutor" stays green in a bare
   container.
#. Playwright's synchronous API runs its event loop in the calling thread, and
   Django refuses every database call from a thread with a running loop
   (SynchronousOnlyOperation). All browser work therefore happens on a worker
   thread that owns the loop, while the test class touches the database on the main
   thread: drive hands a page to a scenario function, runs it on that thread, joins,
   and the main thread makes the assertion.

Run only these checks with::

    uv run manage.py test tutor.test_browser
"""

import contextlib
import os
import threading
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

#: The tab label each page owes the learner; mirrors tutor.test_pages.
TITLES = {
    "intake": "Start a Session - MetaChat Tutor",
    "terms": "Data Collection - MetaChat Tutor",
    "chat": "MetaChat Tutor - Research Edition",
    "menu": "MetaChat Tutor - Progress Overview",
    "reset confirm": "Reset Session - MetaChat Tutor",
}

#: The intake facts one browser session opens with.
BROWSER_INTAKE = {"name": "E2E Alice", "group": "E2E Alpha", "level": "beginner"}

#: The chat inputs from the pretest answer to the terminal screen. The intake form
#: carries the registration facts (ticket #37), so the walk starts at the pretest;
#: the tail walks one role to the end (ticket #39). The same route as the
#: single-role path in tutor.test_tutor_session.
WALK_TO_END = (
    "3 4 5",  # pretest -> the registration axis
    "1",  # -> analysis intro
    "yes",  # -> analysis task 1
    "Answer to task one",  # -> analysis feedback 1
    "next",  # -> analysis task 2
    "Answer to task two",  # -> analysis feedback 2
    "next",  # -> roleplay intro
    "continue",  # -> role menu
    "1",  # -> the mediator role
    "I mediate the conflict",  # -> roleplay feedback
    "next",  # -> role menu, mediator completed
    "finish",  # -> reflection
    "A long reflection",  # -> posttest
    "4 4 4",  # -> data collection, the terminal screen
)

#: A pick per prompt for the assessment gates' chip form (tickets #40 and #48):
#: the taps compose into this string joined with spaces, the answer the gate has
#: always taken.
RATING_PICKS = ("2", "4", "5")

#: The phone width the research participants use (spec #26).
VIEWPORT = {"width": 420, "height": 760}

#: A quotation mark, spelled once so the selectors below stay readable.
Q = chr(34)


def channel():
    """The browser channel to drive: BROWSER_CHANNEL, Edge by default."""
    return os.environ.get("BROWSER_CHANNEL", "msedge")


def attribute(name, value):
    """The CSS fragment matching an attribute carrying a quoted value."""
    return f"[{name}={Q}{value}{Q}]"


@contextlib.contextmanager
def owned_page():
    """Yield one page from a browser launched on the calling thread.

    The caller owns the loop this browser runs on, which is why drive calls it on
    a worker thread. A Playwright failure propagates: setUpClass turns it into a
    skip, drive turns it into the test's failure.
    """
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, channel=channel())
        page = browser.new_page(viewport=VIEWPORT)
        try:
            yield page
        finally:
            browser.close()


#: A single quote, for the JavaScript fragments the assertions evaluate.
APOS = chr(39)

#: The script reading the background the layout painted on the main region.
PAINTED_BACKGROUND = (
    "() => { const target = document.querySelector("
    + APOS + "main" + APOS + ")"
    + " || document.body; return getComputedStyle(target).backgroundColor; }"
);


def wire(page, problems):
    """Record every failure channel the learner would feel.

    Args:
        page: The page to watch.
        problems: The list each breakage is appended to.
    """

    def on_console(message):
        if message.type == "error":
            problems.append(f"console error: {message.text}")

    def on_requestfailed(request):
        reason = (request.failure or {}).get("errorText", "")
        problems.append(f"request failed: {request.url} {reason}".strip())

    def on_response(response):
        if response.status >= 400:
            problems.append(f"HTTP {response.status} {response.url}")

    page.on("console", on_console)
    page.on("pageerror", lambda error: problems.append(f"page error: {error}"))
    page.on("requestfailed", on_requestfailed)
    page.on("response", on_response)


class BrowserPaintTests(StaticLiveServerTestCase):
    """One headless browser per test, on a thread that owns its loop."""

    @classmethod
    def setUpClass(cls):
        """Probe the browser once, on a thread, and skip the module without one."""
        super().setUpClass()
        box = {}

        def probe():
            try:
                with owned_page() as page:
                    page.goto(cls.live_server_url + "/", wait_until="load")
            except PlaywrightError as exc:
                box["unavailable"] = str(exc)

        thread = threading.Thread(target=probe, daemon=True)
        thread.start()
        thread.join()
        if "unavailable" in box:
            super().tearDownClass()
            reason = box["unavailable"]
            raise unittest.SkipTest(
                f"no browser to drive (BROWSER_CHANNEL={channel()!r}): {reason}; "
                "install Edge, or run uv run playwright install chromium and set "
                "BROWSER_CHANNEL"
            )

    def setUp(self):
        """Start the list every browser channel reports its failures into."""
        super().setUp()
        self.problems: list[str] = []

    def tearDown(self):
        """Report on the main thread the breakage the page caused."""
        problems = self.problems
        super().tearDown()
        self.assertEqual(problems, [], "the page broke a channel a learner feels")

    # ------------------------------------------------------ the worker thread

    def drive(self, scenario):
        """Run scenario(page) on a browser-owning thread, then join.

        Args:
            scenario: A callable taking the page to drive. It must not touch the
                database: the database belongs to this thread.

        Raises:
            Anything the scenario raised, re-raised on this thread.
        """
        box = {}
        problems = self.problems

        def worker():
            try:
                with owned_page() as page:
                    wire(page, problems)
                    box["value"] = scenario(page)
            except BaseException as exc:
                box.setdefault("error", exc)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join()
        if "error" in box:
            raise box["error"]
        return box.get("value")

    # ----------------------------------------------------------- navigation

    def open(self, page, path):
        """Load one page of the live server."""
        return page.goto(f"{self.live_server_url}{path}", wait_until="load")

    def open_intake(self, page):
        """Fill and submit the intake form, and wait for the chat it opens."""
        self.open(page, "/")
        page.fill("#id_name", BROWSER_INTAKE["name"])
        page.fill("#id_group", BROWSER_INTAKE["group"])
        level = attribute("value", BROWSER_INTAKE["level"])
        page.check("input" + attribute("name", "level") + level)
        page.click(".intake-submit")
        page.wait_for_url("**/chat/")

    def walk(self, page, inputs):
        """Type each input into the composer and send it."""
        composer = "#main-form input" + attribute("name", "user_input")
        send = "#main-form button" + attribute("type", "submit")
        for text in inputs:
            page.fill(composer, text)
            page.click(send)
            page.wait_for_load_state("load")

    # ----------------------------------------------------------- assertions

    def assertPainted(self, page, label, title, min_text=40):
        """Assert the browser painted the page: its label, text and styles.

        Args:
            page: The page to read.
            label: What to call the page in a failure message.
            title: The tab label the page owes the learner.
            min_text: The least number of readable characters expected.
        """
        self.assertEqual(page.title(), title, f"{label}: tab label")
        text = page.locator("body").inner_text().strip()
        self.assertGreater(len(text), min_text, f"{label}: {len(text)} characters")
        self.assertGreater(
            page.evaluate("() => document.styleSheets.length"),
            0,
            f"{label}: the browser loaded no stylesheet",
        )
        painted = page.evaluate(PAINTED_BACKGROUND)
        self.assertNotEqual(painted, "rgba(0, 0, 0, 0)", f"{label}: unpainted main")

    # --------------------------------------------------------------- tests

    def test_every_page_a_learner_can_open_paints(self):
        """The form, the terms, the chat, the menu and the reset prompt."""

        def scenario(page):
            self.open(page, "/")
            self.assertPainted(page, "intake", TITLES["intake"])
            self.open(page, "/terms/")
            self.assertPainted(page, "terms", TITLES["terms"])
            self.open_intake(page)
            self.assertPainted(page, "chat", TITLES["chat"], min_text=200)
            self.open(page, "/menu/")
            self.assertPainted(page, "menu", TITLES["menu"])
            self.open(page, "/reset/confirm/")
            self.assertPainted(page, "reset confirm", TITLES["reset confirm"])

        self.drive(scenario)

    def test_the_form_asks_for_three_facts_and_opens_the_chat(self):
        """The intake is the entry state: it registers, then opens the chat."""

        def scenario(page):
            self.open(page, "/")
            self.assertPainted(page, "intake", TITLES["intake"])
            self.assertTrue(page.locator("#id_name").is_visible())
            self.assertTrue(page.locator("#id_group").is_visible())
            levels = "input" + attribute("name", "level")
            self.assertEqual(page.locator(levels).count(), 3)
            self.assertEqual(
                page.locator(".intake-consent-link").get_attribute("href"),
                "/terms/",
            )

            # An empty form refuses itself and keeps the learner on the page.
            page.click(".intake-submit")
            self.assertTrue(page.locator(".intake-form").is_visible())
            self.assertGreater(page.locator(".intake-error").count(), 0)

            self.open_intake(page)
            chat = page.locator("body").inner_text().lower()
            self.assertIn("nice to meet you, e2e alice", chat)
            self.assertIn("pre-test", chat)

        self.drive(scenario)

    def test_the_last_screen_painted_itself_out(self):
        """The terminal screen shows the banner and offers no way out."""

        def scenario(page):
            self.open_intake(page)
            self.walk(page, WALK_TO_END)
            body = page.locator("body").inner_text().lower()
            self.assertIn("close this tab whenever you are done", body)
            self.assertTrue(page.locator(".session-complete").is_visible())
            self.assertEqual(
                page.locator("#main-form").count(),
                0,
                "the terminal screen still offers a composer",
            )
            self.assertEqual(
                page.locator("#chat-messages .message:last-child button").count(),
                0,
                "the last turn offers a way out",
            )
            self.assertPainted(page, "terminal", TITLES["chat"], min_text=200)

        self.drive(scenario)


    def test_the_chip_form_answers_on_the_research_phone(self):
        """The gates' chips fit the phone the research uses and answer the gate:
        a row per prompt under the message that asks, every 40px target inside
        the 420px viewport with nothing cut off, and the third tap IS the Send -
        the picks compose into the string the gate has always taken and the page
        moves on with no rejection note (ticket #48, AC2 and AC3; the mobile
        check ticket #40 left unrun for want of a browser here).
        """

        def scenario(page):
            self.open_intake(page)
            self.assertPainted(page, "pretest chip form", TITLES["chat"], min_text=200)
            rows = page.locator(".scale-row")
            self.assertEqual(rows.count(), len(RATING_PICKS))
            chips = page.locator(".scale-chip")
            self.assertEqual(chips.count(), 5 * len(RATING_PICKS))
            width = VIEWPORT["width"]
            for index in range(chips.count()):
                box = chips.nth(index).bounding_box()
                self.assertGreaterEqual(box["height"], 40, f"chip {index}: height")
                self.assertGreaterEqual(box["width"], 40, f"chip {index}: width")
                self.assertGreaterEqual(box["x"], 0, f"chip {index}: off the left edge")
                self.assertLessEqual(
                    box["x"] + box["width"],
                    width,
                    f"chip {index}: cut off at the right edge",
                )
            self.assertLessEqual(
                page.evaluate("() => document.documentElement.scrollWidth"),
                width,
                "the chip rows overflow the phone's width",
            )
            for index, pick in enumerate(RATING_PICKS):
                rows.nth(index).locator(".scale-chip").nth(int(pick) - 1).click()
                if index + 1 < len(RATING_PICKS):
                    # The third tap submits; nothing before it may.
                    self.assertEqual(page.locator(".scale-row").count(), len(RATING_PICKS))
            page.wait_for_load_state("load")
            self.assertEqual(
                page.locator(".scale-form").count(),
                0,
                "the gate is still asking after a full selection",
            )
            self.assertEqual(page.locator(".rejection-note").count(), 0)
            self.assertPainted(page, "the gate answered", TITLES["chat"], min_text=200)

        self.drive(scenario)

    def test_a_selection_left_short_shows_the_gate_s_own_copy(self):
        """A learner who picks two of three is answered by the gate's own
        copy — the copy a half-typed answer gets — and the rows stay, so the
        missing pick is the one thing left to do (ticket #48, AC3).
        """

        def scenario(page):
            self.open_intake(page)
            rows = page.locator(".scale-row")
            rows.nth(0).locator(".scale-chip").nth(int(RATING_PICKS[0]) - 1).click()
            rows.nth(1).locator(".scale-chip").nth(int(RATING_PICKS[1]) - 1).click()
            self.assertEqual(
                rows.count(),
                len(RATING_PICKS),
                "two taps already submitted the gate",
            )
            picked = page.locator(".scale-chip.picked")
            self.assertEqual(picked.count(), 2, "the taps are not marked as picked")
            page.click("#main-form button" + attribute("type", "submit"))
            page.wait_for_load_state("load")
            self.assertIn("pretest task", page.locator(".rejection-note").inner_text())
            self.assertEqual(page.locator(".scale-row").count(), len(RATING_PICKS))

        self.drive(scenario)
