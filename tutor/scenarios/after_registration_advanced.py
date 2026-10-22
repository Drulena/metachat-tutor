"""Scenario state ``after_registration_advanced`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "Thank you, {user_name}! (Level: Advanced)\n\n**📌 IMPORTANT INSTRUCTIONS:**\n•🔙Go back anytime by typing *back*, or clicking the button below.\n•👈Track **your progress** via the **left sidebar**.\n\nChoose how to start your practice👇\n\n",
    "options": {"1": "Step1️⃣: ANALYSIS", "2": "Step2️⃣: ROLE-PLAY"},
}
