"""Scenario state ``analysis_intro_intermediate`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**Step1️⃣: ANALYSIS**\n\nYou'll analyze more complex examples of online comments and practice nuanced use of metagraphemes.\n\n👇**Click *yes* to start**",
    "options": {"yes": "Yes, proceed", "back": "Back to menu"},
    "next_state": {
        "yes": "analysis_task_1_intermediate",
        "back": "after_registration_intermediate",
    },
}
