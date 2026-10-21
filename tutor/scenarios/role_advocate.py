"""Scenario state ``role_advocate`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**🎭 ROLE: Advocate**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Person under criticism:** {user1}\n\n**Quote➡️** *{critic}*\n\n**Task:** {task}\n\n*You MUST:*\n 🔺use @mention to acknowledge the critic first\n 🔺provide at least TWO reasons for fair consideration\n 🔺add a protective emoji (🛡️, 💪, 🤲)\n\n⌨️**Type your response:**",
    "input_type": "text",
    "validation": ".+",
    "next_state": "roleplay_feedback_advocate",
}
