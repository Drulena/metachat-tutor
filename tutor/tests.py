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

        result = get_llm_feedback(
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

        result = get_llm_feedback(
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

        result = get_llm_feedback(
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


class DoubleEscapeRegressionTest(SimpleTestCase):
    """Регрессионный тест: LLM-вывод не должен содержать дважды экранированные
    HTML-сущности.

    get_llm_feedback() уже вызывает html.unescape() на строке ответа LLM.
    Если get_current_message() повторно применяет html.escape(), а затем
    шаблонный фильтр markdown() экранирует снова, пользователь видит
    буквальные символы сущностей (например ``&#x27;`` вместо апострофа).

    Тест проверяет полный путь: get_llm_feedback() → get_current_message().
    Должен ПАДАТЬ (RED) до исправления и ПРОХОДИТЬ (GREEN) после.
    """

    def _make_request(self, scenario_states, current_state, user_data):
        """Создать mock-запрос с нужным состоянием сессии."""
        from unittest.mock import MagicMock

        request = MagicMock()
        request.session = {
            "scenario": {"states": scenario_states},
            "current_state": current_state,
            "user_data": user_data,
            "chat_history": [{"content": "test answer", "role": "user"}],
        }
        return request

    @patch("tutor.state_machine.get_llm_feedback")
    def test_apostrophe_not_double_escaped(self, mock_llm):
        """LLM-ответ с обычным апострофом не должен быть экранирован повторно.

        get_llm_feedback() возвращает ``It's fine`` (без HTML-сущностей).
        get_current_message() не должен превращать апостроф в ``&#x27;``.
        """
        from .state_machine import get_current_message

        mock_llm.return_value = "It's a great answer!"

        # Нужны оба состояния: analysis_task (контекст) и analysis_feedback (вызов LLM)
        scenario_states = {
            "analysis_task_1_beginner": {
                "message": "📝 TASK 1: Analyse the text.",
            },
            "analysis_feedback_1_beginner": {
                "message": "📊 Feedback\n\n🤖 LLM feedback will appear here.\n\n📋 Model answer:",
            },
        }
        request = self._make_request(
            scenario_states=scenario_states,
            current_state="analysis_feedback_1_beginner",
            user_data={
                "user_name": "TestStudent",
                "level": "beginner",
                "current_role": None,
            },
        )

        result = get_current_message(request)

        # Апостроф должен остаться обычным символом, а не стать HTML-сущностью
        self.assertNotIn("&#x27;", result)
        self.assertNotIn("&apos;", result)
        self.assertIn("It's", result)

    @patch("tutor.state_machine.get_llm_feedback")
    def test_quotation_marks_not_double_escaped(self, mock_llm):
        """Кавычки LLM не должны экранироваться повторно.

        get_llm_feedback() возвращает текст с обычными кавычками.
        get_current_message() не должен превращать их в ``&quot;``.
        """
        from .state_machine import get_current_message

        mock_llm.return_value = 'He said "hello" to her.'

        scenario_states = {
            "analysis_task_2_beginner": {
                "message": "📝 TASK 2: Evaluate the dialogue.",
            },
            "analysis_feedback_2_beginner": {
                "message": "📊 Feedback\n\n🤖 LLM feedback.\n\n📋 Model answer:",
            },
        }
        request = self._make_request(
            scenario_states=scenario_states,
            current_state="analysis_feedback_2_beginner",
            user_data={
                "user_name": "TestStudent",
                "level": "beginner",
                "current_role": None,
            },
        )

        result = get_current_message(request)

        self.assertNotIn("&quot;", result)
        self.assertNotIn("&#34;", result)
        self.assertIn('"hello"', result)

    @patch("tutor.state_machine.get_llm_feedback")
    def test_ampersand_not_double_escaped(self, mock_llm):
        """Ampersand LLM не должен экранироваться повторно.

        get_llm_feedback() возвращает ``A & B``.
        get_current_message() не должен превращать ``&`` в ``&amp;``.
        """
        from .state_machine import get_current_message

        mock_llm.return_value = "Use A & B together."

        scenario_states = {
            "analysis_task_1_beginner": {
                "message": "📝 TASK 1: Analyse the text.",
            },
            "analysis_feedback_1_beginner": {
                "message": "📊 Feedback\n\n🤖 LLM feedback.\n\n📋 Model answer:",
            },
        }
        request = self._make_request(
            scenario_states=scenario_states,
            current_state="analysis_feedback_1_beginner",
            user_data={
                "user_name": "TestStudent",
                "level": "beginner",
                "current_role": None,
            },
        )

        result = get_current_message(request)

        self.assertNotIn("&amp;", result)
        self.assertIn("A & B", result)


class ModelAnswerRemovalTest(SimpleTestCase):
    """Regression test: Model answer section must NOT appear in role-play
    feedback, but MUST appear in analysis feedback.

    The Model answer section is injected via marker-based splitting in
    get_current_message() (state_machine.py).  This mechanism is shared
    between analysis and role-play feedback.  The fix (to be implemented)
    should skip the Model answer marker for role-play feedback states
    (detected by ``roleplay_feedback`` in current_state).

    These tests capture that requirement.
    - test_roleplay_feedback_no_model_answer should FAIL (RED) against the
      current code because the fix has not been applied yet.
    - test_analysis_feedback_has_model_answer should PASS (GREEN) against
      the current code.
    """

    def _make_request(self, scenario_states, current_state, user_data):
        """Create a mock request with the required session state."""
        request = MagicMock()
        request.session = {
            "scenario": {"states": scenario_states},
            "current_state": current_state,
            "user_data": user_data,
            "chat_history": [{"content": "test answer", "role": "user"}],
        }
        return request

    @patch("tutor.state_machine.get_llm_feedback")
    def test_roleplay_feedback_no_model_answer(self, mock_llm):
        """Role-play feedback must NOT contain the Model answer section.

        get_current_message() currently injects the LLM output *above* the
        ``📋 Model answer:`` marker, preserving the marker and its static
        content.  After the fix, role-play feedback states should skip the
        Model answer marker entirely so the user never sees it.

        This test should FAIL (RED) against the current code because the
        Model answer section is still present in role-play feedback.
        """
        from .state_machine import get_current_message

        mock_llm.return_value = "Great mediator response!"

        # The roleplay_feedback_mediator message includes the Model answer
        # marker (see scenarios.py line 350).
        scenario_states = {
            "role_mediator": {
                "message": "**🎭 ROLE: Mediator**\n\nWrite a mediator response.",
            },
            "roleplay_feedback_mediator": {
                "message": (
                    "📖 **Read the feedback for you, {user_name} (Mediator), carefully and make notes:**\n\n"
                    "**Criteria check:**\n"
                    "✅ @mention used correctly?\n\n"
                    "**📋 Model answer:** *'@ aggressor, I see your concern. 🤝'*\n\n"
                    "▶️ **Type 'revise' to improve your answer, 'next' to choose the next Role, or 'back' to return to menu:**"
                ),
            },
        }
        request = self._make_request(
            scenario_states=scenario_states,
            current_state="roleplay_feedback_mediator",
            user_data={
                "user_name": "TestStudent",
                "level": "beginner",
                "current_role": "role_mediator",
            },
        )

        result = get_current_message(request)

        # The role-play feedback must NOT contain the Model answer section.
        # After the fix, this assertion should pass.  Currently it FAILS
        # because get_current_message() still injects LLM output above the
        # Model answer marker, preserving the marker in the output.
        self.assertNotIn("Model answer", result)

    @patch("tutor.state_machine.get_llm_feedback")
    def test_analysis_feedback_has_model_answer(self, mock_llm):
        """Analysis feedback MUST still contain the Model answer section.

        The fix should only skip the Model answer marker for role-play
        feedback states.  Analysis feedback states must continue to show
        the Model answer section as before.

        This test should PASS (GREEN) against the current code.
        """
        from .state_machine import get_current_message

        mock_llm.return_value = "Good analysis!"

        # The analysis_feedback_1_beginner message includes the Model answer
        # marker (see scenarios.py line 275).
        scenario_states = {
            "analysis_task_1_beginner": {
                "message": "📝 TASK 1: Analyse the text.",
            },
            "analysis_feedback_1_beginner": {
                "message": (
                    "📖 **Read the feedback for you, {user_name} (Beginner), carefully and make notes:**\n\n"
                    "Great start!\n\n"
                    "**📋 Model answer:** 'This essay has some areas to work on 🙂.'\n\n"
                    "▶️ **Type 'next' to continue to Task 2:**"
                ),
            },
        }
        request = self._make_request(
            scenario_states=scenario_states,
            current_state="analysis_feedback_1_beginner",
            user_data={
                "user_name": "TestStudent",
                "level": "beginner",
                "current_role": None,
            },
        )

        result = get_current_message(request)

        # Analysis feedback must still contain the Model answer section.
        self.assertIn("Model answer", result)
