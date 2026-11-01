"""The ledger mirrors every submission; the pages never read it (ticket #38).

ADR-0007 decisions 1, 2 and 7: one row per session, opened by the intake form,
written through on every submission, chains through a reset. The chat keeps
answering the pages from its own storage, so a ledger that is missing, stale
or deleted never reaches the learner.
"""

from django.test import Client, TestCase

from .models import Assessment, SessionRecord
from .session import SessionStorage


INTAKE = {"name": "Alice", "group": "Alpha", "level": "beginner"}
OTHER_INTAKE = {"name": "Bella", "group": "Beta crew", "level": "advanced"}


def _open(client, payload=INTAKE):
    """Submit the intake form, landing the chat page and its ledger row."""
    response = client.post("/", payload)
    assert response.status_code == 302
    return SessionRecord.objects.get(session_id=_session_id(client))


def _session_id(client) -> str:
    """The id the chat minted, read from the browser copy of the session."""
    return SessionStorage(client.session).load().session_id


def _entries(client):
    """The chat history the browser copy holds, entry dicts and all."""
    return SessionStorage(client.session).load().chat_history


def _strand(client, state: str):
    """Move the chat to ``state`` without walking the graph to it.

    Saving the browser session object is what the middleware does at the end
    of every response; without that write the next request reads the old state
    back, and the answer lands on the state the chat was really on.
    """
    store = client.session
    record = SessionStorage(store).load()
    record.current_state = state
    SessionStorage(store).save(record)
    store.save()  # the object written, not a fresh one: the property mints a new store


class WriteThroughTests(TestCase):
    """What a submission leaves on the row."""

    def setUp(self):
        self.client = Client()

    def test_two_exchanges_land_on_the_row_verbatim_in_order(self):
        """The row holds the same entry dicts the browser is shown, in submit
        order - role, content, state, timestamp and the assistant metadata
        included (ADR-0007 decision 2).
        """
        row = _open(self.client)
        self.client.post("/chat/", {"user_input": "3 4 5"})
        self.client.post("/chat/", {"user_input": "1"})
        row.refresh_from_db()
        stored = _entries(self.client)
        self.assertGreater(len(stored), 3, "the chat did append the exchanges")
        self.assertEqual(row.chat_history, stored)
        self.assertEqual(
            [entry["role"] for entry in row.chat_history],
            ["assistant", "user", "assistant", "user", "assistant"],
        )
        self.assertEqual(row.chat_history[1]["content"], "3 4 5")
        self.assertEqual(row.chat_history[1]["state"], "pretest")

    def test_a_submission_advances_the_row_last_activity(self):
        """updated_at is the activity stamp: a submission moves it."""
        row = _open(self.client)
        before = row.updated_at
        self.client.post("/chat/", {"user_input": "3 4 5"})
        row.refresh_from_db()
        self.assertGreater(row.updated_at, before)

    def test_the_pretest_answer_lands_as_a_child_row(self):
        """The pretest gate records its raw answer and its parsed scores.

        The scores are the same three ints _parse_scores reads, in order.
        """
        row = _open(self.client)
        self.client.post("/chat/", {"user_input": "3 4 5"})
        answer = Assessment.objects.get(session=row, kind="pretest")
        self.assertEqual(answer.raw_answer, "3 4 5")
        self.assertEqual(answer.scores, [3, 4, 5])

    def test_a_rejected_gate_answer_lands_no_child_row(self):
        """Only gate acceptance scores: an answer the gate refuses is a
        dropped input, and the chat log keeps it flagged as such.
        """
        row = _open(self.client)
        self.client.post("/chat/", {"user_input": "3 4"})
        self.assertEqual(Assessment.objects.count(), 0)
        row.refresh_from_db()
        self.assertTrue(row.chat_history[-1].get("rejected"))

    def test_the_posttest_answer_lands_as_a_child_row(self):
        """The posttest gate writes the same shape under its own kind."""
        row = _open(self.client)
        _strand(self.client, "posttest")
        self.client.post("/chat/", {"user_input": "4 4 4"})
        answer = Assessment.objects.get(session=row, kind="posttest")
        self.assertEqual(answer.raw_answer, "4 4 4")
        self.assertEqual(answer.scores, [4, 4, 4])

    def test_the_reflection_answer_fills_the_row(self):
        """Reflection acceptance fills the row field, verbatim."""
        row = _open(self.client)
        _strand(self.client, "reflection")
        self.client.post("/chat/", {"user_input": "A long reflection on the session"})
        row.refresh_from_db()
        self.assertEqual(row.reflection, "A long reflection on the session")

    def test_a_nav_command_writes_no_gate_and_no_reflection(self):
        """'back' appends no answer entry, so it mirrors the appended reply
        only: no score row, no reflection, no crash.
        """
        row = _open(self.client)
        self.client.post("/chat/", {"user_input": "3 4 5"})
        _strand(self.client, "reflection")
        self.client.post("/chat/", {"user_input": "back"})
        self.assertEqual(Assessment.objects.count(), 1)  # the pretest answer only
        row.refresh_from_db()
        self.assertEqual(row.reflection, "")


class LedgerIsWriteOnlyTests(TestCase):
    """The ledger is a research artefact: the pages answer from the Summary.

    ADR-0007 decision 1. A missing row never reaches the learner - not on a
    page, not on a submission.
    """

    def setUp(self):
        self.client = Client()

    def test_the_pages_answer_with_the_row_deleted(self):
        row = _open(self.client)
        self.client.post("/chat/", {"user_input": "3 4 5"})
        SessionRecord.objects.all().delete()
        page = self.client.get("/chat/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Alice")
        self.assertContains(page, "PRE-TEST")

    def test_a_submission_still_lands_with_the_row_deleted(self):
        """A ledger hiccup is logged, never thrown at the learner."""
        row = _open(self.client)
        SessionRecord.objects.all().delete()
        with self.assertLogs("tutor.ledger", level="WARNING") as logs:
            response = self.client.post("/chat/", {"user_input": "3 4 5"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SessionStorage(self.client.session).load().current_state, "after_registration")
        self.assertTrue(any("ledger row" in line for line in logs.output))


class ResetChainTests(TestCase):
    """Reset chains: the abandoned row is the new row's predecessor (#38)."""

    def setUp(self):
        self.client = Client()

    def test_reset_chains_the_new_row_to_the_abandoned_one(self):
        """The wipe abandons the row (finished_at stays null) and the next
        intake opens a fresh row that names it as the session it replaced.
        """
        abandoned = _open(self.client)
        self.client.post("/chat/", {"user_input": "3 4 5"})
        self.client.post("/reset/")
        self.assertEqual(self.client.get("/chat/").status_code, 302, "a fresh intake first")
        form = self.client.get("/")
        self.assertNotContains(form, "Alice")
        fresh = _open(self.client, OTHER_INTAKE)
        abandoned.refresh_from_db()
        self.assertIsNone(abandoned.finished_at)
        self.assertEqual(fresh.previous_session_id, abandoned.id)
        self.assertNotEqual(fresh.session_id, abandoned.session_id)
        self.assertEqual(fresh.user_name, "Bella")

    def test_a_reset_with_no_previous_row_chains_to_nothing(self):
        """An intake that replaces nothing leaves the link empty."""
        fresh = _open(self.client)
        self.assertIsNone(fresh.previous_session_id)


class ConcurrentSessionsTests(TestCase):
    """Two learners at once write to their own rows - no interleaving."""

    def test_two_browsers_write_their_own_entries(self):
        alice = Client()
        bella = Client()
        alice_row = _open(alice, INTAKE)
        bella_row = _open(bella, OTHER_INTAKE)
        alice.post("/chat/", {"user_input": "3 4 5"})
        bella.post("/chat/", {"user_input": "1 2 3"})
        alice.post("/chat/", {"user_input": "1"})
        bella.post("/chat/", {"user_input": "2"})
        alice_row.refresh_from_db()
        bella_row.refresh_from_db()
        # The welcome plus one exchange per submission, same shape as Alice.
        self.assertEqual(
            [entry["role"] for entry in bella_row.chat_history],
            ["assistant", "user", "assistant", "user", "assistant"],
        )
        self.assertEqual([e["role"] for e in alice_row.chat_history], ["assistant", "user", "assistant", "user", "assistant"])
        self.assertEqual(bella_row.chat_history[1]["content"], "1 2 3")
        self.assertEqual(alice_row.chat_history[1]["content"], "3 4 5")
        self.assertEqual(Assessment.objects.filter(session=bella_row, scores=[1, 2, 3]).count(), 1)
        self.assertEqual(Assessment.objects.filter(session=alice_row, scores=[3, 4, 5]).count(), 1)

