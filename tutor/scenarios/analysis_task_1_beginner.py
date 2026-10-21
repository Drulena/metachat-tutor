"""Scenario state ``analysis_task_1_beginner`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**📝 TASK 1: Softening Criticism (Beginner)**\n\nContext: {context}\n\nOriginal message: *{message}*\n\n❓ **Question:** Which emoji(s) would you add to the END of this message to make it sound kinder? Explain your choice.\n\n*Hint: {hint}*\n\n⬇️**Type your answer and tap Enter:**",
    "input_type": "text",
    "validation": ".+",
    "next_state": "analysis_feedback_1_beginner",
}
