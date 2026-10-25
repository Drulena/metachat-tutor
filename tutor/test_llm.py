"""LLM response parsing — the student sees only the feedback, never the model's thoughts.

The provider can return the model's chain-of-thought in ``reasoning`` (and a
proxy may return no ``content`` at all). Surfacing that text to the learner is
a defect (owner report, issue #15 follow-up): the parser takes ``content`` /
``text`` only; a reasoning-only choice is a miss that falls through to the
demo-failure path. Seam: the chat-completions response JSON consumed by
``get_llm_feedback``.
"""

import unittest

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


class PromptContractTests(unittest.TestCase):
    """The prompt must demand student-facing output only — the owner's rule."""

    def test_prompt_forbids_reasoning_text(self):
        import os
        from unittest import mock

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

        with mock.patch.dict(os.environ, {"LLM_API_KEY": "test-key"}):
            with mock.patch.object(llm.requests, "post", _post):
                text, failed = llm.get_llm_feedback("answer", None, "Bob", "beginner", "TASK 1?")
        self.assertFalse(failed)
        prompt = captured["payload"]["messages"][0]["content"]
        self.assertIn("Return only the feedback text", prompt)

    def test_no_requests_attempted_without_api_key(self):
        import os
        from unittest import mock

        from . import llm

        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(llm.requests, "post", _boom):
                text, failed = llm.get_llm_feedback("a", None, "B", "beginner", "q")
        self.assertTrue(failed)
        self.assertIn("not configured", text)


def _boom(*args, **kwargs):  # pragma: no cover - must never run
    raise AssertionError("requests.post must not be attempted without an API key")


if __name__ == "__main__":
    unittest.main()
