"""Every page a learner can open must paint: a closed head, a
resolving stylesheet and visible text.

A page whose <title> is never closed swallows the rest of the document as title
text - the browser paints a blank page while every Django test still passes,
because the test client hands back raw bytes and never parses them. These checks
parse the response the way a browser would, so that class of bug has a signal in
the suite that runs in a second.
"""

import re
from html.parser import HTMLParser
from unittest import TestCase

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import Client, TestCase as DjangoTestCase

from .testing import INTAKE, open_intake

#: Raw-text elements: their content is text until the matching end tag, so an
#: unclosed one swallows everything that follows it.
_RAW_TEXT = ("title", "textarea", "script", "style")


class _RawTextParser(HTMLParser):
    """Collect the raw-text elements a browser would be left waiting to close."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.unclosed = []
        self.titles = 0

    def handle_starttag(self, tag, attrs):
        if tag in _RAW_TEXT:
            self.unclosed.append(tag)
            if tag == "title":
                self.titles += 1

    def handle_endtag(self, tag):
        if tag in _RAW_TEXT and tag in self.unclosed:
            self.unclosed.remove(tag)


def head_violations(html):
    """Return the reasons a browser would not paint this document.

    Args:
        html: The rendered page, exactly as served to the browser.

    Returns:
        A list of human-readable problems; empty when the document parses.
    """
    parser = _RawTextParser()
    parser.feed(html)
    parser.close()
    violations = [f"unclosed <{tag}> swallows the rest of the document"
                  for tag in parser.unclosed]
    if parser.titles == 0:
        violations.append("the page has no <title>")
    elif parser.titles > 1:
        violations.append(f"the page declares {parser.titles} <title> elements")
    return violations


def visible_text(html):
    """Strip the markup and scripts, leaving what the learner would read.

    Args:
        html: The rendered page.

    Returns:
        The page text with runs of whitespace collapsed to single spaces.
    """
    text = re.sub(r"<script[\s\S]*?</script>", " ", html)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())



#: The tab label each page owes the learner.
EXPECTED_TITLES = {
    "intake": "Start a Session - MetaChat Tutor",
    "terms": "Data Collection - MetaChat Tutor",
    "chat": "MetaChat Tutor - Research Edition",
    "menu": "MetaChat Tutor - Progress Overview",
    "reset_confirm": "Reset Session - MetaChat Tutor",
}


def page_title(html):
    """Return the tab label the browser would show.

    Args:
        html: The rendered page.

    Returns:
        The title's text, or None when no title element is closed.
    """
    match = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    return match.group(1).strip() if match else None


def stray_markup(html):
    """Return the head's text runs ending in a stray angle bracket.

    A closing tag written as ">" leaves the bracket in the title text, so the
    tab reads "…Tutor>" and the head carries debris.

    Args:
        html: The rendered page.

    Returns:
        The offending runs of text; empty for a clean head.
    """
    head = re.search(r"<head>([\s\S]*?)</head>", html, re.I)
    if head is None:
        return []
    text = re.sub(r"<[^>]*>", " ", head.group(1))
    return re.findall(r"\S*>", text)


class DetectorTests(TestCase):
    """The guard must go red on the bug it is here for."""

    def test_flags_a_title_closed_only_by_a_stray_angle_bracket(self):
        broken = (
            "<head><title>Start a Session - MetaChat Tutor>"
            '<link rel="stylesheet" href="/static/tutor/style.css"></head>'
            "<body><main>Fill this in</main></body>"
        )
        self.assertEqual(
            head_violations(broken),
            ["unclosed <title> swallows the rest of the document"],
        )

    def test_flags_a_head_whose_closing_tag_lost_its_name(self):
        broken = "<head><title>Start a Session - MetaChat Tutor></head><body></body>"
        self.assertIsNone(page_title(broken))
        self.assertEqual(stray_markup(broken), ["Tutor>"])

    def test_accepts_a_well_formed_head(self):
        good = (
            "<head><title>Start a Session</title>"
            '<link rel="stylesheet" href="/static/tutor/style.css"></head>'
            "<body><main>Fill this in</main></body>"
        )
        self.assertEqual(head_violations(good), [])


class PagePaintsTests(DjangoTestCase):
    """Each public page parses, links a stylesheet that loads, shows text."""

    def setUp(self):
        self.client = Client()

    def _pages(self):
        """Return (name, response) for every page a learner can reach."""
        pages = [("intake", self.client.get("/")),
                 ("terms", self.client.get("/terms/"))]
        open_intake(self.client, INTAKE)
        pages.extend([("chat", self.client.get("/chat/")),
                      ("menu", self.client.get("/menu/")),
                      ("reset_confirm", self.client.get("/reset/confirm/"))])
        return pages

    def test_every_page_parses_as_a_browser_would(self):
        for name, response in self._pages():
            with self.subTest(page=name):
                self.assertEqual(response.status_code, 200)
                self.assertEqual(head_violations(response.content.decode()), [])

    def test_every_page_links_a_stylesheet_the_finders_can_serve(self):
        for name, response in self._pages():
            with self.subTest(page=name):
                html = response.content.decode()
                hrefs = (
                    re.findall('<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"', html)
                    + re.findall('<link[^>]+href="([^"]+)"[^>]+rel="stylesheet"', html)
                )
                self.assertTrue(hrefs, f"{name} loads no stylesheet")
                for href in hrefs:
                    # The test client never serves static files, so ask the
                    # finders for the file the browser's request resolves to.
                    relative = href.removeprefix(settings.STATIC_URL).lstrip("/")
                    self.assertIsNotNone(finders.find(relative), href)

    def test_every_page_declares_its_title(self):
        for name, response in self._pages():
            with self.subTest(page=name):
                html = response.content.decode()
                self.assertEqual(page_title(html), EXPECTED_TITLES[name])
                self.assertEqual(stray_markup(html), [])

    def test_every_page_shows_visible_text(self):
        for name, response in self._pages():
            with self.subTest(page=name):
                self.assertGreater(len(visible_text(response.content.decode())),
                                   40, name)
