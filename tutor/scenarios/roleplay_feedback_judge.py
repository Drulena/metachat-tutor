"""Scenario state ``roleplay_feedback_judge`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "📖 **Read the feedback for you, {user_name} (Judge), carefully and make notes:**\n\n**Criteria check:**\n✅ Used **bold** for strongest points?\n✅ Found merit in BOTH sides?\n✅ Used balanced emoji (⚖️, 📊)?\n\n**📋 Model answer:** *'Let me assess both sides. ⚖️ Team A's **30% productivity increase** is supported by Stanford. Team B's **collaboration suffers** is backed by MIT. A hybrid model likely addresses both valid concerns.'*\n\n👇**Click *revise* to improve your answer, *next* to choose the next Role, or *back* to return to menu:**",
    "validation": ".+",
    "options": {
        "revise": "✏️ Revise",
        "next": "➡️ Next Role",
        "back": "⬅️ Back to Menu",
    },
}
