"""Scenario state ``analysis_feedback_2_intermediate`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "📖 **Read the feedback for you, {user_name} (Intermediate), carefully and make notes:**\n\nKey techniques: Alternating caps (mockery) and multiple exclamation marks (shouting).\n\n**📋 Model answer:** 'The message uses **tHaT's NoT** with alternating caps to mock, and **!!!** to shout.'\n\n👇**Tap *next* to proceed:**",
    "options": {"next": "Proceed to Step2️⃣", "back": "Back to menu"},
    "next_state": {
        "next": "roleplay_intro",
        "back": "analysis_intro_intermediate",
    },
}
