"""Scenario state ``roleplay_feedback_peacemaker`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "📖 **Read the feedback for you, {user_name} (Peacemaker), carefully and make notes:**\n\n**Criteria check:**\n✅ Used @mention for both parties?\n✅ Identified valid concerns?\n✅ Proposed specific compromise?\n✅ Used peace emoji (🕊️, 🤝)?\n\n**📋 Model answer:** *'@ Student A and @ Student B, I hear both of you. 🤝 Student A, your concern about fair contribution is valid. Student B, your feeling of being controlled is also valid. Let's create a shared task list where responsibilities are visible to all.'*\n\n👇**Click *revise* to improve your answer, *next* to choose the next Role, or *back* to return to menu:**",
    "input_type": "text",
    "validation": ".+",
    "next_state": "role_menu",
}
