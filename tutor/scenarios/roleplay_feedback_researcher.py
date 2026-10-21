"""Scenario state ``roleplay_feedback_researcher`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "📖 **Read the feedback for you, {user_name} (Researcher), carefully and make notes:**\n\n**Criteria check:**\n✅ Used @mention correctly?\n✅ Asked TWO specific cultural questions?\n✅ Used thoughtful emoji (🤔, 🧐, 📚)?\n\n**📋 Model answer:** *'@speaker, you mentioned directness is respectful in your culture. 📚 Could you tell me how criticism is typically framed in professional settings there? And are there situations where indirectness might be preferred?'*\n\n👇**Click *revise* to improve your answer, *next* to choose the next Role, or *back* to return to menu:**",
    "input_type": "text",
    "validation": ".+",
    "next_state": "role_menu",
}
