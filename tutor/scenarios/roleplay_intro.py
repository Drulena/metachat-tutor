"""Scenario state ``roleplay_intro`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**Step2️⃣: ROLE-PLAY**\n\nIn this stage, you'll practice constructive communication roles in simulated online discussions.\n\n",
    "options": {
        "continue": "View Available Roles",
        "back": "Back to Main Menu",
    },
}
