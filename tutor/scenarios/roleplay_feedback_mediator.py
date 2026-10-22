"""Scenario state ``roleplay_feedback_mediator`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "📖 **Read the feedback for you, {user_name} (Mediator), carefully and make notes:**\n\n**Criteria check:**\n✅ @mention used correctly?\n✅ Acknowledged concern before redirecting?\n✅ Proposed constructive next step?\n✅ Used calm emoji (🕊️, 🤝)?\n\n**📋 Model answer:** *'@ {aggressor}, I see your concern about productivity. 🤝 Let's look at the research together and find a balanced approach that works for everyone.'*\n\n👇**Click *revise* to improve your answer, *next* to choose the next Role, or *back* to return to menu:**",
    "validation": ".+",
    "options": {
        "revise": "✏️ Revise",
        "next": "➡️ Next Role",
        "back": "⬅️ Back to Menu",
    },
}
