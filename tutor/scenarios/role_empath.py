"""Scenario state ``role_empath`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**🎭 ROLE: Empath**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Emotional state:** {emotional_state}\n\n**Comment section➡️** *{user1}*\n\n**Task:** {task}\n\n*You MUST:*\n 🔺use @mention to address the person\n 🔺explicitly VALIDATE their feelings\n 🔺offer support WITHOUT giving advice\n 🔺add a warm emoji (❤️, 🤗, 💗)\n\n⌨️**Type your response:**",
    "validation": ".+",
}
