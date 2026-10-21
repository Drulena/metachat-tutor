"""Scenario state ``role_researcher`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**🎭 ROLE: Researcher**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Discussion➡️** *{user1}*\n*{user2}*\n\n**Task:** {task}\n\n*You MUST:*\n 🔺use @mention to address the person\n 🔺ask at least TWO specific questions about cultural practices\n 🔺add a thoughtful emoji (🤔, 🧐, 📚)\n\n⌨️**Type your response:**",
    "input_type": "text",
    "validation": ".+",
    "next_state": "roleplay_feedback_researcher",
}
