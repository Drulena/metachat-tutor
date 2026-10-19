"""Regression tests for tutor/llm.py — HTML entity unescaping.

The LLM API may return text containing HTML entities (e.g. ``&quot;`` for
a plain double-quote).  These entities should be unescaped to their Unicode
equivalents before the text is surfaced to the user.

These tests capture that requirement.  They are expected to FAIL (RED) until
the fix is applied in ``llm.py``.
"""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from .llm import get_llm_feedback


class HTMLUnescapeLLMOutputTest(SimpleTestCase):
    """Verify that get_llm_feedback() unescapes HTML entities in LLM output."""

    def _fake_llm_response(self, text: str) -> MagicMock:
        """Build a minimal ``requests.post``-compatible mock response."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": text,
                    }
                }
            ]
        }
        return response

    @patch("tutor.llm.os.getenv")
    @patch("tutor.llm.requests.post")
    def test_quotes_not_html_entities(self, mock_post, mock_getenv):
        """LLM output containing &quot; must be unescaped to a plain quote."""
        html_entity_text = "He said &quot;hello&quot; to her."
        expected_text = 'He said "hello" to her.'

        mock_getenv.side_effect = lambda key, *a: (
            "fake-key" if key == "LLM_API_KEY" else a[0] if a else None
        )
        mock_post.return_value = self._fake_llm_response(html_entity_text)

        result, failed = get_llm_feedback(
            user_answer="test answer",
            role_name="mediator",
            user_name="TestStudent",
            level="beginner",
            task_question="TASK 1",
        )

        self.assertNotIn("&quot;", result)
        self.assertIn("hello", result)

    @patch("tutor.llm.os.getenv")
    @patch("tutor.llm.requests.post")
    def test_ampersand_not_html_entities(self, mock_post, mock_getenv):
        """LLM output containing &amp; must be unescaped to a plain &."""
        html_entity_text = "Use A &amp; B together."
        expected_text = "Use A & B together."

        mock_getenv.side_effect = lambda key, *a: (
            "fake-key" if key == "LLM_API_KEY" else a[0] if a else None
        )
        mock_post.return_value = self._fake_llm_response(html_entity_text)

        result, failed = get_llm_feedback(
            user_answer="test answer",
            role_name="mediator",
            user_name="TestStudent",
            level="beginner",
            task_question="TASK 1",
        )

        self.assertNotIn("&amp;", result)
        self.assertIn("A & B", result)

    @patch("tutor.llm.os.getenv")
    @patch("tutor.llm.requests.post")
    def test_mixed_html_entities(self, mock_post, mock_getenv):
        """Multiple HTML entities in LLM output are all unescaped."""
        html_entity_text = "&quot;He&quot; said &amp; she left &lt;early&gt;."
        expected_text = '"He" said & she left <early>.'

        mock_getenv.side_effect = lambda key, *a: (
            "fake-key" if key == "LLM_API_KEY" else a[0] if a else None
        )
        mock_post.return_value = self._fake_llm_response(html_entity_text)

        result, failed = get_llm_feedback(
            user_answer="test answer",
            role_name="mediator",
            user_name="TestStudent",
            level="beginner",
            task_question="TASK 1",
        )

        self.assertNotIn("&quot;", result)
        self.assertNotIn("&amp;", result)
        self.assertNotIn("&lt;", result)
        self.assertNotIn("&gt;", result)


