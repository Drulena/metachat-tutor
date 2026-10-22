"""Scenario state ``roleplay_feedback_logical`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "📖 **Read the feedback for you, {user_name} (Logical Expert), carefully and make notes:**\n\n**Criteria check:**\n✅ Used **bold** to highlight flaws?\n✅ Asked clarifying question?\n✅ Used thinking emoji (🤔, 🧐)?\n\n**📋 Model answer:** *'**'Grammar is useless'** is an overgeneralization. 🤔 Could you clarify what you mean? Research shows grammar instruction helps accuracy, while immersion builds fluency. Both have value.'*\n\n👇**Click *revise* to improve your answer, *next* to choose the next Role, or *back* to return to menu:**",
    "validation": ".+",
    "options": {
        "revise": "✏️ Revise",
        "next": "➡️ Next Role",
        "back": "⬅️ Back to Menu",
    },
}
