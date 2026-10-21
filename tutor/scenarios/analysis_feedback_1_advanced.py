"""Scenario state ``analysis_feedback_1_advanced`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "📖 **Read the feedback for you, {user_name} (Advanced), carefully and make notes:**\n\nFor complex feedback, emoji after the main critique softens tone.\n\n👇**Tap *next* to continue:**",
    "options": {"next": "Next Task", "back": "Back to menu"},
    "next_state": {
        "next": "analysis_task_2_advanced",
        "back": "analysis_intro_advanced",
    },
}
