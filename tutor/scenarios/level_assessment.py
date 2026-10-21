"""Scenario state ``level_assessment`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**📊 Self-Assessment: Your Experience Level**\n\nPlease evaluate your experience with online discussions in English:\n\n▫️1▫️ Beginner = I rarely participate in online discussions\n\n▫️2▫️ Intermediate = I read regularly, sometimes post\n\n▫️3▫️ Advanced = I actively participate in professional discussions\n\n👇**Tap the button below**",
    "options": {"1": "Beginner", "2": "Intermediate", "3": "Advanced"},
    "next_state": {
        "1": "after_registration_beginner",
        "2": "after_registration_intermediate",
        "3": "after_registration_advanced",
    },
}
