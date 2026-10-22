"""Scenario state ``role_interpreter`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**🎭 ROLE: Interpreter**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Discussion➡️** *{user1}*\n*{user2}*\n\n**Task:** {task}\n\n*You MUST:*\n 🔺use **bold** (\*-symbol at the beginning and the end of the word, e.g. \*\*hello\*\*) to highlight the key cultural difference\n 🔺explain both intended meaning AND how it was misinterpreted\n 🔺add a bridging emoji (🤝, 🌉, 💬)\n\n⌨️**Type your response:**",
    "validation": ".+",
}
