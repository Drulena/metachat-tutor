"""Scenario state ``role_logical`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**🎭 ROLE: Logical Expert**\n\n**Scenario:** {scenario} \n\n**Context:** {context} \n\n**Debate➡️** *{user1}*\n*{user2}*\n\n**Task:** {task}\n\n*You MUST:*\n 🔺use **bold** (\*-symbol at the beginning and the end of the word, e.g. \*\*hello\*\*) to identify each logical flaw\n 🔺ask at least ONE clarifying question\n 🔺add a thinking emoji (🤔, 🧐, 📊)\n\n⌨️**Type your response:**",
    "validation": ".+",
}
