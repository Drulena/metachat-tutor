"""Scenario state ``analysis_feedback_1_beginner`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "📖 **Read the feedback for you, {user_name} (Beginner), carefully and make notes:**\n\nGreat start! Adding a friendly emoji like 🙂 or 😊 can make criticism feel more supportive.\n\n**📋 Model answer:** 'This essay has some areas to work on 🙂. Let's look at them together.'\n\n👇**Tap *next* to proceed to Task 2:**",
    "options": {"next": "Next Task", "back": "Back to menu"},
}
