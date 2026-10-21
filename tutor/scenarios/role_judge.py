"""Scenario state ``role_judge`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**🎭 ROLE: Judge**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Discussion➡️** {discussion}\n\n**POVs:** *{points}*\n\n**Task:** {task}\n\n*You MUST:*\n 🔺use **bold** (\*-symbol at the beginning and the end of the word, e.g. \*\*hello\*\*) for the strongest point from each side\n 🔺identify what's valid in BOTH perspectives\n 🔺add a balanced emoji (⚖️, 📊, ✅)\n\n⌨️**Type your response:**",
    "input_type": "text",
    "validation": ".+",
    "next_state": "roleplay_feedback_judge",
}
