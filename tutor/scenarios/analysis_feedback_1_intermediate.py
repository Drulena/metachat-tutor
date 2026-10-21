"""Scenario state ``analysis_feedback_1_intermediate`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "📖 **Read the feedback for you, {user_name} (Intermediate), carefully and make notes:**\n\nGood approach! A friendly emoji like 🙂 or 🤔 acts as an 'emotional cushion'.\n\n**📋 Model answer:** 'I think the data in this part might need a second look 🤔.'\n\n👇**Tap *next* to continue:**",
    "options": {"next": "Next Task", "back": "Back to menu"},
    "next_state": {
        "next": "analysis_task_2_intermediate",
        "back": "analysis_intro_intermediate",
    },
}
