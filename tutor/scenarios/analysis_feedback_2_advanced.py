"""Scenario state ``analysis_feedback_2_advanced`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "📖 **Read the feedback for you, {user_name} (Advanced), carefully and make notes:**\n\nTechniques: ALL CAPS (irony), ellipsis (dramatic pause), 🙄 emoji (sarcasm), #facepalm (meta-commentary).\n\n👇**Tap *next* to proceed:**",
    "options": {"next": "Proceed to Step2️⃣", "back": "Back to menu"},
    "next_state": {"next": "roleplay_intro", "back": "analysis_intro_advanced"},
}
