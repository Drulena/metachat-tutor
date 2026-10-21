"""Scenario state ``analysis_task_1_advanced`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**📝 TASK 1: Softening Criticism (Advanced)**\n\nContext: {context}\n\nOriginal message: {message}\n\n❓ **Question:** Where would you place emojis to maintain professionalism?\n\n*Hint: {hint}*\n\n⬇️**Type your answer:**",
    "input_type": "text",
    "validation": ".+",
    "next_state": "analysis_feedback_1_advanced",
}
