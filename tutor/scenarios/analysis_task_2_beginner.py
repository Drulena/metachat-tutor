"""Scenario state ``analysis_task_2_beginner`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**📝 TASK 2: Recognizing Aggressive Formatting (Beginner)**\n\nMessage: *{message}*\n\n❓ **Question:** What makes this message feel aggressive? Identify ONE technique.\n\n💡*Hint: {hint}*\n\n⬇️**Type your answer and tap Enter:**",
    "input_type": "text",
    "validation": ".+",
    "next_state": "analysis_feedback_2_beginner",
}
