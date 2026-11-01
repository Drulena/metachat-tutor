"""The terminal screen is the last stop, and the ledger knows it (ticket #39).

ADR-0007 decision 4: the ``end`` state is retired, ``data_collection`` is the
terminal screen - no back edge, no exit navigation, a completed banner - and
``finished_at`` is stamped on entering it. Non-null is what "finished" means
for the admin and every filter, and a reset never clears the stamp.
"""

from django.test import Client, SimpleTestCase, TestCase

from .scenarios import SCENARIO
from .testing import OTHER_INTAKE, INTAKE, open_intake, state_of, strand
from .transitions import ROW_REGISTRY, validate_transitions

REFLECTION = "I learned to name the role I was playing before answering."
POSTTEST_ANSWER = "4 4 4"
TERMINAL = "data_collection"


class TerminalScreenTests(TestCase):
    """What arriving at the terminal screen does to the row and the page."""

    def setUp(self):
        self.client = Client()
        self.row = open_intake(self.client)
        self.client.post("/chat/", {"user_input": "3 4 5"})

    def _finish(self) -> None:
        """Walk the last steps: reflection, posttest, the terminal screen."""
        strand(self.client, "reflection")
        self.client.post("/chat/", {"user_input": REFLECTION})
        self.client.post("/chat/", {"user_input": POSTTEST_ANSWER})

    def test_entering_the_terminal_screen_stamps_the_row(self):
        """The stamp arrives with the session, on arrival, once (decision 4)."""
        self._finish()
        self.assertEqual(state_of(self.client), TERMINAL, "the walk did not arrive")
        self.row.refresh_from_db()
        self.assertIsNotNone(self.row.finished_at)

    def test_the_stamp_never_moves_again(self):
        """Stamped exactly once: later activity leaves it alone.

        ``updated_at`` is the activity stamp; ``finished_at`` is the moment
        the session reached its end, so re-reading it after more traffic has
        to give the same value.
        """
        self._finish()
        self.row.refresh_from_db()
        stamped = self.row.finished_at
        for text in ("exit", "back", "1", "Main Menu"):
            self.client.post("/chat/", {"user_input": text})
        self.row.refresh_from_db()
        self.assertEqual(self.row.finished_at, stamped)

    def test_the_completed_banner_replaces_the_input_area(self):
        """The banner is the completed signal; the composer is gone (the AC)."""
        self._finish()
        page = self.client.get("/chat/")
        self.assertContains(page, "session-complete")
        # The composer is the input area: its placeholder is the markup that
        # says a learner can still type. (The page script names the form by
        # id unconditionally, so the id is not the signal.)
        self.assertNotContains(page, "Type your answer here")

    def test_the_terminal_screen_offers_no_back_and_no_exit(self):
        """No back, no exit, no menu link on the last screen."""
        self._finish()
        page = self.client.get("/chat/")
        self.assertNotContains(page, 'data-value="exit"')
        self.assertNotContains(page, 'data-value="back"')
        self.assertNotContains(page, "Main Menu")

    def test_no_input_leaves_the_terminal_screen(self):
        """The screen cannot be left: every input is answered on the spot."""
        self._finish()
        for text in ("exit", "back", "1", "retry"):
            self.client.post("/chat/", {"user_input": text})
            self.assertEqual(state_of(self.client), TERMINAL, f"{text!r} left the screen")
        page = self.client.get("/chat/")
        self.assertContains(page, "complete")

    def test_the_export_reports_the_session_finished(self):
        """The payload says the same thing the ledger does."""
        self._finish()
        payload = self.client.get("/export/")
        self.assertTrue(payload.json()["progress"]["finished"])

    def test_a_session_that_never_arrives_keeps_the_stamp_null(self):
        """An in-progress session is an unstamped row (decision 7)."""
        self.client.post("/chat/", {"user_input": "1"})
        self.row.refresh_from_db()
        self.assertIsNone(self.row.finished_at)

    def test_a_reset_after_finishing_starts_an_unstamped_row(self):
        """The finished stamp is the old row's; the successor starts open.

        A stamp is never cleared (decision 4), so the abandoned row keeps
        the session it finished, and the chain names it (decision 7).
        """
        self._finish()
        self.row.refresh_from_db()
        stamped = self.row.finished_at
        self.assertIsNotNone(stamped)
        self.client.post("/reset/")
        fresh = open_intake(self.client, OTHER_INTAKE)
        self.row.refresh_from_db()
        self.assertEqual(self.row.finished_at, stamped, "the stamp was cleared")
        self.assertIsNone(fresh.finished_at, "a fresh session is not finished")
        self.assertEqual(fresh.previous_session_id, self.row.id)


class EndStateRetiredTests(SimpleTestCase):
    """The ``end`` state is gone from the table, not just from the flow."""

    def test_end_is_no_longer_a_scenario_state(self):
        self.assertNotIn("end", SCENARIO["states"])

    def test_no_row_targets_end(self):
        for pair, row in ROW_REGISTRY.items():
            targets = [row.get("next"), row.get("back")]
            if isinstance(row.get("next"), dict):
                targets = list(row["next"].values()) + [row.get("back")]
            for target in targets:
                with self.subTest(pair=pair, target=target):
                    self.assertNotEqual(target, "end")

    def test_the_reduced_table_still_validates(self):
        """The AC: registry validation passes with the reduced table."""
        self.assertEqual(validate_transitions(), [])

    def test_the_terminal_row_names_its_own_phase(self):
        """The terminal row is the screen with no way out, not a signpost.

        ``next`` and ``back`` are both None and the nav map is empty, and
        the row's own phase is the one the panel reads as finished - the
        banner key, since the retired ``end`` state no longer spells it.
        """
        row = ROW_REGISTRY[(TERMINAL, None)]
        self.assertIsNone(row["next"])
        self.assertIsNone(row["back"])
        self.assertEqual(row["nav"], {})
        self.assertEqual(row["phase"], "finished")

