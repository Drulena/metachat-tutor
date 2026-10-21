"""Scenario state ``roleplay_feedback_interpreter`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "📖 **Read the feedback for you, {user_name} (Interpreter), carefully and make notes:**\n\n**Criteria check:**\n✅ Used **bold** for cultural difference?\n✅ Explained intended AND misinterpreted meaning?\n✅ Used bridging emoji (🤝, 🌉)?\n\n**📋 Model answer:** *'I think there's a cultural nuance here. **'Requires more careful consideration'** in Japanese often means polite disagreement. 🌉 The German preference for directness isn't wrong — it's just a different cultural expectation.'*\n\n👇**Click *revise* to improve your answer, *next* to choose the next Role, or *back* to return to menu:**",
    "input_type": "text",
    "validation": ".+",
    "next_state": "role_menu",
}
