"""Scenario state ``reflection`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**💭 REFLECTION**\n\nPlease answer briefly:\n\n1️⃣ What new insight about metagraphemes did you gain?\n\n2️⃣ Which role was the most challenging for you? Why?\n\n⌨️**Type your reflection:**",
    "input_type": "text",
    "validation": ".+",
    "next_state": "posttest",
}
