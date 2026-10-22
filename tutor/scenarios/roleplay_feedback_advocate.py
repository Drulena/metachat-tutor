"""Scenario state ``roleplay_feedback_advocate`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "📖 **Read the feedback for you, {user_name} (Advocate), carefully and make notes:**\n\n**Criteria check:**\n✅ Used @mention to acknowledge critic?\n✅ Provided TWO reasons for defense?\n✅ Used protective emoji (🛡️, 💪)?\n\n**📋 Model answer:** *'@ Sarah, I understand your concern about missed deadlines. 🛡️ However, Alex has been dealing with a family emergency. Also, when Alex has contributed, the quality has been excellent. Let's check in privately before judging.'*\n\n👇**Click *revise* to improve your answer, *next* to choose the next Role, or *back* to return to menu:**",
    "validation": ".+",
}
