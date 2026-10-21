"""Scenario state ``analysis_task_2_advanced`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**📝 TASK 2: Recognizing Aggressive Formatting (Advanced)**\n\nMessage: {message}\n\n❓ **Question:** Analyze ALL metagrapheme techniques used here.\n\n⌨️**Type your analysis:**",
    "input_type": "text",
    "validation": ".+",
    "next_state": "analysis_feedback_2_advanced",
}
