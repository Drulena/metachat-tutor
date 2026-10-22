"""Scenario state ``role_peacemaker`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**🎭 ROLE: Peacemaker**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Conflict:** {conflict}\n\n**Discussion➡️** *{user1}*\n*{user2}*\n\n**Task:** {task}\n\n*You MUST:*\n 🔺use @mention to address both parties\n 🔺identify the VALID concern behind each position\n 🔺propose a specific compromise\n 🔺add a peace emoji (🕊️, ☮️, 🤝)\n\n⌨️**Type your response:**",
    "validation": ".+",
}
