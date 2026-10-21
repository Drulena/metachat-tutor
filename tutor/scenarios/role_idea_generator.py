"""Scenario state ``role_idea_generator`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**🎭 ROLE: Idea Generator**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Current discussion➡️** *{quote}*\n\n**Task:** {task}\n\n*You MUST:*\n 🔺use **bold** or *italics* (\*-symbol at the beginning and the end of the word, e.g. \*\*bold\*\* or \*italics\*) to emphasize your key innovative idea\n 🔺add at least ONE creativity emoji (💡, 🚀, ✨)\n 🔺propose at least TWO distinct new ideas\n\n⌨️**Type your response:**",
    "input_type": "text",
    "validation": ".+",
    "next_state": "roleplay_feedback_idea",
}
