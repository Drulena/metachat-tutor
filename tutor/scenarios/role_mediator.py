"""Scenario state ``role_mediator`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**🎭 ROLE: Mediator**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Aggressor** {aggressor} says: *{quote}*\n\n**Task:** {task}\n\n*You MUST:*\n🔺use @mention to address the aggressor\n 🔺acknowledge their concern before redirecting\n 🔺propose a constructive way forward\n 🔺insert a calm/peaceful emoji (🕊️, 🤝, 🌿)\n\n⌨️**Type your response:**",
    "input_type": "text",
    "validation": ".+",
    "next_state": "roleplay_feedback_mediator",
}
