"""LLM response parsing — the student sees only the feedback, never the model's thoughts.

The provider can return the model's chain-of-thought in ``reasoning`` (and a
proxy may return no ``content`` at all). Surfacing that text to the learner is
a defect (owner report, issue #15 follow-up): the parser takes ``content`` /
``text`` only; a reasoning-only choice is a miss that falls through to the
demo-failure path. Seam: the chat-completions response JSON consumed by
``get_llm_feedback``.
"""

import os
import unittest
from unittest import mock

from .llm import _response_text


class ResponseTextTests(unittest.TestCase):
    def test_chat_content_wins(self):
        result = {"choices": [{"message": {"content": "Nice work on the emoji."}}]}
        self.assertEqual(_response_text(result), "Nice work on the emoji.")

    def test_reasoning_is_never_surfaced(self):
        result = {
            "choices": [
                {"message": {"reasoning": "We need to evaluate student answer \"adsf\". Likely..."}}
            ]
        }
        self.assertIsNone(_response_text(result))

    def test_content_wins_over_reasoning(self):
        result = {
            "choices": [
                {"message": {"content": "Feedback.", "reasoning": "Internal monologue."}}
            ]
        }
        self.assertEqual(_response_text(result), "Feedback.")

    def test_legacy_text_field(self):
        result = {"choices": [{"text": "Legacy feedback."}]}
        self.assertEqual(_response_text(result), "Legacy feedback.")

    def test_blank_content_is_a_miss(self):
        result = {"choices": [{"message": {"content": "   "}}]}
        self.assertIsNone(_response_text(result))

    def test_html_entities_are_unescaped(self):
        result = {"choices": [{"message": {"content": "A &amp; B"}}]}
        self.assertEqual(_response_text(result), "A & B")

    def test_non_dict_result_is_a_miss(self):
        self.assertIsNone(_response_text("not json"))

    def test_no_choices_is_a_miss(self):
        self.assertIsNone(_response_text({"choices": []}))


class ResponseTextProviderTests(unittest.TestCase):
    """The anthropic wire protocol answers with content blocks (issue #15)."""

    def test_text_blocks_are_surfaced(self):
        result = {"content": [{"type": "thinking", "thinking": "hidden"},
                              {"type": "text", "text": "Nice work."}]}
        self.assertEqual(_response_text(result, "anthropic"), "Nice work.")

    def test_multiple_text_blocks_join(self):
        result = {"content": [{"type": "text", "text": "Part one."},
                              {"type": "text", "text": "Part two."}]}
        self.assertEqual(_response_text(result, "anthropic"),
                         "Part one.\nPart two.")

    def test_thinking_only_is_a_miss(self):
        result = {"content": [{"type": "thinking", "thinking": "hidden"}]}
        self.assertIsNone(_response_text(result, "anthropic"))

    def test_html_entities_are_unescaped(self):
        result = {"content": [{"type": "text", "text": "A &amp; B"}]}
        self.assertEqual(_response_text(result, "anthropic"), "A & B")


class ResponseTextMistralTests(unittest.TestCase):
    def test_assistant_outputs_are_surfaced(self):
        result = {"outputs": [
            {"type": "message.output", "role": "assistant", "content": "Part one."},
            {"type": "message.output", "role": "assistant", "content": "Part two."},
        ]}
        self.assertEqual(_response_text(result, "mistral"), "Part one.\nPart two.")

    def test_non_output_entries_are_skipped(self):
        result = {"outputs": [{"type": "entry", "role": "tool", "content": "n/a"},
                              {"type": "message.output", "role": "assistant",
                               "content": "Real answer."}]}
        self.assertEqual(_response_text(result, "mistral"), "Real answer.")

    def test_html_entities_are_unescaped(self):
        result = {"outputs": [{"type": "message.output", "role": "assistant",
                               "content": "A &amp; B"}]}
        self.assertEqual(_response_text(result, "mistral"), "A & B")


class PromptContractTests(unittest.TestCase):
    """The prompt must demand student-facing output only — the owner's rule."""

    def _prompt(self, env=None, **kwargs):
        from . import llm

        captured: dict = {}

        class _Resp:
            status_code = 200

            @staticmethod
            def json():
                return {"choices": [{"message": {"content": "ok"}}]}

        def _post(url, headers, json, timeout):
            captured["payload"] = json
            return _Resp()

        settings = {"LLM_API_KEY": "test-key", "LLM_PROVIDER": "openai"}
        settings.update(env or {})
        args = {"user_answer": "answer", "role_name": None,
                "user_name": "Bob", "level": "beginner",
                "task_question": "TASK 1?"}
        args.update(kwargs)
        with mock.patch.dict(os.environ, settings):
            with mock.patch.object(llm.requests, "post", _post):
                llm.get_llm_feedback(**args)
        return captured["payload"]["messages"][0]["content"]

    def test_prompt_forbids_reasoning_text(self):
        self.assertIn("Return only the feedback text", self._prompt())

    def test_prompt_states_the_feedback_length_limit(self):
        # The instruction's budget is one number the owner tunes (issue #15):
        # the prompt must carry it, not a literal typed twice.
        from . import llm

        self.assertIn(f"max {llm._MAX_FEEDBACK_CHARS} characters",
                      self._prompt())

    def test_prompt_length_limit_follows_the_constant(self):
        from . import llm

        with mock.patch.object(llm, "_MAX_FEEDBACK_CHARS", 600):
            self.assertIn("max 600 characters", self._prompt())

    def test_prompt_shape_is_pinned(self):
        # The full prompt is the product contract the owner tuned by hand —
        # a golden pin so refactors and edits cannot drift it silently.
        from .data import THEORETICAL_BASE

        self.assertEqual(
            self._prompt(),
            f"{THEORETICAL_BASE}\n\n"
            "Always use English to respond.\n"
            "When discussing emojis, use the actual Unicode emoji character "
            "(e.g., \U0001f642 not the word 'smiley').\n"
            "Student: Bob\nLevel: beginner\n"
            "Selected role: none\n\n"
            "--- TASK QUESTION ---\nTASK 1?\n\n"
            "--- STUDENT ANSWER ---\nanswer\n\n"
            "--- INSTRUCTION ---\n"
            "Evaluate the student's answer based on the theoretical framework "
            "above. Check whether they identified/applied metagrapheme tools "
            "correctly for their level. Give brief constructive feedback "
            "(max 500 characters). Be supportive and specific. "
            "Return only the feedback text the student should read. "
            "No reasoning, no analysis notes, no preamble.",
        )

    def test_no_requests_attempted_without_api_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            from . import llm
            with mock.patch.object(llm.requests, "post", _boom):
                text, failed = llm.get_llm_feedback("a", None, "B", "beginner", "q")
        self.assertTrue(failed)
        self.assertIn("not configured", text)


class FallbackCopyTests(unittest.TestCase):
    """The demo banner names the failure and answers with the tuned hint."""

    def _fallback(self, env, **kwargs):
        from . import llm

        class _Resp:
            status_code = 429

            @staticmethod
            def json():
                return {}

        def _post(*args, **kwargs):
            return _Resp()

        with mock.patch.dict(os.environ, env):
            with mock.patch.object(llm.requests, "post", _post):
                args = {"user_answer": "answer", "role_name": None,
                        "user_name": "Bob", "level": "beginner",
                        "task_question": "TASK 1?"}
                args.update(kwargs)
                return llm.get_llm_feedback(**args)

    def test_task_hint_per_task_question(self):
        env = {"LLM_API_KEY": "key", "LLM_URL": "https://api.example/v1",
               "LLM_MODEL": "m"}
        text, failed = self._fallback(env)
        self.assertTrue(failed)
        self.assertIn("HTTP 429", text)
        self.assertIn("friendly emoji like \U0001f642", text)
        text, _ = self._fallback(env, task_question="TASK 2: combine")
        self.assertIn("multiple metagrapheme techniques", text)
        text, _ = self._fallback(env, task_question="something else")
        self.assertIn("Review the criteria", text)


class ProviderShapeTests(unittest.TestCase):
    """LLM_PROVIDER picks the wire protocol; owner-pasted URLs are accepted.

    Two adapters, not three SDKs: the openai-compatible shape covers
    OpenAI, Mistral, OpenRouter, Cerebras and local servers; anthropic
    answers a genuinely different protocol (x-api-key, /v1/messages,
    content blocks).
    """

    def _run(self, env, resp_json, status=200):
        from . import llm

        captured: dict = {}

        class _Resp:
            status_code = status

            @staticmethod
            def json():
                return resp_json

        def _post(url, headers, json, timeout):
            captured.setdefault("calls", []).append(
                {"url": url, "headers": headers, "payload": json}
            )
            return _Resp()

        with mock.patch.dict(os.environ, env, clear=False):
            with mock.patch.object(llm.requests, "post", _post):
                text, failed = llm.get_llm_feedback(
                    "answer", None, "Bob", "beginner", "TASK 1?"
                )
        return text, failed, captured

    def test_anthropic_protocol_shape(self):
        # The owner pastes the anthropic docs URL verbatim (…/v1/messages).
        text, failed, calls = self._run(
            {"LLM_API_KEY": "sk-ant-test", "LLM_PROVIDER": "anthropic",
             "LLM_URL": "https://api.anthropic.com/v1/messages",
             "LLM_MODEL": "claude-sonnet-4-5"},
            {"content": [{"type": "text", "text": "Claude answers."}]},
        )
        self.assertEqual([c["url"] for c in calls["calls"]],
                         ["https://api.anthropic.com/v1/messages"])
        headers = calls["calls"][0]["headers"]
        self.assertEqual(headers["x-api-key"], "sk-ant-test")
        self.assertEqual(headers["anthropic-version"], "2023-06-01")
        payload = calls["calls"][0]["payload"]
        self.assertEqual(payload["model"], "claude-sonnet-4-5")
        self.assertIn("max_tokens", payload)
        self.assertEqual(payload["messages"][0]["role"], "user")
        self.assertEqual(text, "Claude answers.")
        self.assertFalse(failed)

    def test_anthropic_thinking_only_fails_honestly(self):
        text, failed, _ = self._run(
            {"LLM_API_KEY": "sk-ant-test", "LLM_PROVIDER": "anthropic",
             "LLM_URL": "https://api.anthropic.com/v1",
             "LLM_MODEL": "claude-sonnet-4-5"},
            {"content": [{"type": "thinking", "thinking": "monologue"}]},
        )
        self.assertTrue(failed)
        self.assertIn("no student-facing text", text)

    def test_openai_shape_accepts_the_mistral_conversations_base(self):
        # The owner's live .env: the Mistral CONVERSATIONS URL — the
        # provider base is recovered and the chat-completions path used.
        text, failed, calls = self._run(
            {"LLM_API_KEY": "key", "LLM_PROVIDER": "openai",
             "LLM_URL": "https://api.mistral.ai/v1/conversations",
             "LLM_MODEL": "mistral-small-2506"},
            {"choices": [{"message": {"content": "Mistral answers."}}]},
        )
        self.assertEqual(calls["calls"][0]["url"],
                         "https://api.mistral.ai/v1/chat/completions")
        self.assertEqual(
            calls["calls"][0]["headers"]["Authorization"], "Bearer key",
        )
        self.assertEqual(text, "Mistral answers.")
        self.assertFalse(failed)

    def test_blank_answer_reports_the_real_reason(self):
        # A 200 with no student-facing text is a miss — the banner tells
        # the honest reason, not a NameError from the debug trail.
        text, failed, _ = self._run(
            {"LLM_API_KEY": "key", "LLM_PROVIDER": "openai",
             "LLM_URL": "https://api.mistral.ai/v1",
             "LLM_MODEL": "mistral-small-2506"},
            {"choices": [{"message": {"content": "   "}}]},
        )
        self.assertTrue(failed)
        self.assertIn("no student-facing text", text)
        self.assertNotIn("name 'choices'", text)

    def test_mistral_conversations_protocol_shape(self):
        # The owner's key answers on the CONVERSATIONS endpoint while
        # chat/completions 429s — the native shape (inputs,
        # completion_args, outputs) is its own protocol.
        text, failed, calls = self._run(
            {"LLM_API_KEY": "key", "LLM_PROVIDER": "mistral",
             "LLM_URL": "https://api.mistral.ai/v1/conversations",
             "LLM_MODEL": "mistral-small-2506"},
            {"object": "conversation.response",
             "outputs": [{"type": "message.output", "role": "assistant",
                          "content": "Mistral answers."}]},
        )
        self.assertEqual([c["url"] for c in calls["calls"]],
                         ["https://api.mistral.ai/v1/conversations"])
        headers = calls["calls"][0]["headers"]
        self.assertEqual(headers["Authorization"], "Bearer key")
        payload = calls["calls"][0]["payload"]
        self.assertEqual(payload["model"], "mistral-small-2506")
        self.assertEqual(payload["inputs"][0]["role"], "user")
        self.assertEqual(payload["completion_args"]["max_tokens"], 150)
        self.assertEqual(text, "Mistral answers.")
        self.assertFalse(failed)

    def test_mistral_empty_outputs_is_a_miss(self):
        text, failed, _ = self._run(
            {"LLM_API_KEY": "key", "LLM_PROVIDER": "mistral",
             "LLM_URL": "https://api.mistral.ai/v1",
             "LLM_MODEL": "mistral-small-2506"},
            {"object": "conversation.response", "outputs": []},
        )
        self.assertTrue(failed)
        self.assertIn("no student-facing text", text)


def _boom(*args, **kwargs):  # pragma: no cover - must never run
    raise AssertionError("requests.post must not be attempted without an API key")


if __name__ == "__main__":
    unittest.main()
