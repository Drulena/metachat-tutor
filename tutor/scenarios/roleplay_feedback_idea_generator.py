"""Scenario state ``roleplay_feedback_idea_generator`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "📖 **Read the feedback for you, {user_name} (Idea Generator), carefully and make notes:**\n\n**Criteria check:**\n✅ Used **bold** or *italics* for key ideas?\n✅ Used creativity emoji (💡, 🚀, ✨)?\n✅ Proposed at least TWO distinct ideas?\n\n**📋 Model answer:** *'What if we tried **a gamified approach** with points and levels? 🚀 Or we could create **cross-cultural conversation pairs** where partners teach each other phrases in their languages? ✨ Both could increase engagement significantly.'*\n\n👇**Click *revise* to improve your answer, *next* to choose the next Role, or *back* to return to menu:**",
    "validation": ".+",
}
