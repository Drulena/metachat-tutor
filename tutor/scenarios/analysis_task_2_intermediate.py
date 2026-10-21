"""Scenario state ``analysis_task_2_intermediate`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**📝 TASK 2: Recognizing Aggressive Formatting (Intermediate)**\n\nMessage: {message}\n\n❓ **Question:** Identify TWO metagrapheme techniques used here.\n\n💡*Hint: {hint}*\n\n⬇️**Type your answer and tap Enter:**",
    "input_type": "text",
    "validation": ".+",
    "next_state": "analysis_feedback_2_intermediate",
}
