"""Tests for the storage seam, session-state value types, and LLM injection.

These cover the prefactor deliverables for issue #2 ("Build the storage seam,
session-state types, and LLM injection"):

- ``State`` / ``Turn`` / ``Summary`` value types with exactly the described fields.
- A storage seam (``load`` / ``save`` / ``clear``) with an in-memory
  (``MemoryStorage``) and a Django-session (``SessionStorage``) adapter,
  each of which round-trips a saved ``State`` unchanged and clears it.
- The LLM exposed as an injectable ``feedback(...)`` callable whose default is
  the existing feedback service; substituting a fake returns the fake's result
  with no network call.

Nothing here touches existing views, templates, or behavior; it only pins down
the seam the ``TutorSession`` module (issue #3) will stand on.
"""

from __future__ import annotations

from dataclasses import fields
from unittest.mock import patch

from django.contrib.sessions.backends.cache import SessionStore
from django.test import SimpleTestCase

from .llm import get_llm_feedback
from .session import (
    SessionStorage,
    MemoryStorage,
    State,
    Storage,
    Summary,
    Turn,
    default_feedback,
)


def _sample_state() -> State:
    """Build a representative State to round-trip through the adapters."""
    return State(
        session_id="sample-session-id",
        current_state="role_mediator",
        user_data={
            "user_name": "Stacy",
            "level": "beginner",
            "completed_roles": ["role_mediator"],
            "completed_steps": ["pretest"],
        },
        scenario={
            "bot_name": "MetaChat Tutor",
            "welcome_message": "welcome",
            "states": {"start": {"message": "Nice to meet you, {user_name}!"}},
        },
        chat_history=[
            {
                "role": "user",
                "content": "Stacy 101",
                "state": "start",
                "timestamp": "2026-01-01T00:00:00",
            },
            {
                "role": "assistant",
                "content": "Nice to meet you, Stacy!",
                "state": "start",
                "timestamp": "2026-01-01T00:00:01",
                "options": {"1": "Beginner"},
            },
        ],
        retry_count=2,
    )


class StateValueTypeTest(SimpleTestCase):
    """``State`` carries exactly the six fields a session persists."""

    def test_state_fields_match_spec(self):
        names = [f.name for f in fields(State)]
        self.assertEqual(
            names,
            [
                "session_id",
                "current_state",
                "user_data",
                "scenario",
                "chat_history",
                "retry_count",
            ],
        )

    def test_state_roundtrip_values(self):
        state = _sample_state()
        self.assertEqual(state.session_id, "sample-session-id")
        self.assertEqual(state.current_state, "role_mediator")
        self.assertEqual(state.retry_count, 2)
        self.assertIn("states", state.scenario)
        self.assertEqual(len(state.chat_history), 2)


class TurnValueTypeTest(SimpleTestCase):
    """``Turn`` = speaker's role, message text, state key, options, timestamp."""

    def test_turn_fields_match_spec(self):
        names = [f.name for f in fields(Turn)]
        self.assertEqual(names, ["role", "message", "state", "options", "timestamp"])

    def test_assistant_turn_carries_options(self):
        turn = Turn(
            role="assistant",
            message="Hello",
            state="start",
            options={"1": "Beginner"},
            timestamp="2026-01-01T00:00:00",
        )
        self.assertEqual(turn.options, {"1": "Beginner"})

    def test_user_turn_has_no_options(self):
        turn = Turn(
            role="user",
            message="Stacy 101",
            state="start",
            options=None,
            timestamp="2026-01-01T00:00:00",
        )
        self.assertIsNone(turn.options)


class SummaryValueTypeTest(SimpleTestCase):
    """``Summary`` is the derived presentation view the views will read."""

    def test_summary_fields_match_spec(self):
        names = [f.name for f in fields(Summary)]
        self.assertEqual(
            names,
            [
                "sections",
                "percentage",
                "total_steps",
                "completed_steps_count",
                "completed_option_values",
                "finished",
                "level",
                "user_name",
                "session_id",
            ],
        )

    def test_summary_defaults(self):
        summary = Summary()
        self.assertEqual(summary.sections, [])
        self.assertEqual(summary.percentage, 0)
        self.assertEqual(summary.total_steps, 15)
        self.assertEqual(summary.completed_steps_count, 0)
        self.assertEqual(summary.completed_option_values, [])
        self.assertFalse(summary.finished)
        self.assertIsNone(summary.level)


class MemoryStorageRoundTripTest(SimpleTestCase):
    """In-memory adapter: save -> load back unchanged; clear removes it."""

    def test_initial_load_is_none(self):
        self.assertIsNone(MemoryStorage().load())

    def test_save_load_roundtrip(self):
        store = MemoryStorage()
        original = _sample_state()
        store.save(original)
        self.assertEqual(store.load(), original)

    def test_clear_removes_state(self):
        store = MemoryStorage()
        store.save(_sample_state())
        store.clear()
        self.assertIsNone(store.load())

    def test_saved_copy_is_independent_of_original(self):
        store = MemoryStorage()
        original = _sample_state()
        store.save(original)
        # Mutating the original after save must not corrupt the stored copy.
        original.user_data["user_name"] = "CHANGED"
        original.chat_history.append({"role": "user", "content": "extra"})
        loaded = store.load()
        self.assertEqual(loaded.user_data["user_name"], "Stacy")
        self.assertEqual(len(loaded.chat_history), 2)


class SessionStorageRoundTripTest(SimpleTestCase):
    """Django-session adapter: save -> load back unchanged; clear removes it."""

    def _store(self) -> SessionStore:
        return SessionStore()

    def test_initial_load_is_none(self):
        self.assertIsNone(SessionStorage(self._store()).load())

    def test_save_load_roundtrip(self):
        storage = SessionStorage(self._store())
        original = _sample_state()
        storage.save(original)
        self.assertEqual(storage.load(), original)

    def test_clear_removes_state(self):
        storage = SessionStorage(self._store())
        storage.save(_sample_state())
        storage.clear()
        self.assertIsNone(storage.load())

    def test_adapters_implement_storage_protocol(self):
        self.assertIsInstance(MemoryStorage(), Storage)
        self.assertIsInstance(SessionStorage(self._store()), Storage)


class FeedbackInjectionTest(SimpleTestCase):
    """LLM is an injectable feedback(...) callable, defaulting to the existing service."""

    def test_default_feedback_is_existing_service(self):
        self.assertIs(default_feedback, get_llm_feedback)

    def test_default_feedback_no_network_without_api_key(self):
        with (
            patch("tutor.llm.os.getenv", return_value=None),
            patch("tutor.llm.requests.post") as mock_post,
        ):
            text, failed = default_feedback(
                user_answer="an answer",
                role_name="mediator",
                user_name="Stacy",
                level="beginner",
                task_question="TASK 1",
            )
        self.assertIsInstance(text, str)
        self.assertTrue(failed)
        mock_post.assert_not_called()

    def test_substituted_fake_returns_its_result_without_network(self):
        seen: dict[str, object] = {}

        def fake(
            user_answer: str,
            role_name,
            user_name: str,
            level: str,
            task_question=None,
        ):
            seen.update(
                user_answer=user_answer,
                role_name=role_name,
                user_name=user_name,
                level=level,
                task_question=task_question,
            )
            return ("DETERMINISTIC FEEDBACK", False)

        # The module (issue #3) will call the injected callable exactly the way
        # the current state machine does: keyword args, (text, failed) result.
        with patch("tutor.llm.requests.post") as mock_post:
            text, failed = fake(
                user_answer="my answer",
                role_name="mediator",
                user_name="Stacy",
                level="beginner",
                task_question="TASK 1",
            )
        self.assertEqual((text, failed), ("DETERMINISTIC FEEDBACK", False))
        self.assertEqual(seen["user_name"], "Stacy")
        self.assertEqual(seen["role_name"], "mediator")
        self.assertEqual(seen["task_question"], "TASK 1")
        mock_post.assert_not_called()
