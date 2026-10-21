"""Scenario state ``roleplay_feedback_empath`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "📖 **Read the feedback for you, {user_name} (Empath), carefully and make notes:**\n\n**Criteria check:**\n✅ Used @mention to address them?\n✅ Explicitly validated feelings?\n✅ Offered support without advice?\n✅ Used warm emoji (❤️, 🤗)?\n\n**📋 Model answer:** *'@ student, that sounds incredibly hard. ❤️ It's completely understandable to feel hurt after such direct criticism. Your feelings are valid, and it's okay to take time to process this. I'm here to listen.'*\n\n👇**Click *revise* to improve your answer, *next* to choose the next Role, or *back* to return to menu:**",
    "input_type": "text",
    "validation": ".+",
    "options": {
        "revise": "✏️ Revise",
        "next": "➡️ Next Role",
        "back": "⬅️ Back to Menu",
    },
    "next_state": "role_menu",
}
