"""Scenario state ``analysis_feedback_2_beginner`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "📖 **Read the feedback for you, {user_name} (Beginner), carefully and make notes:**\n\nYou're right! **ALL CAPS** feels like shouting online.\n\n**📋 Model answer:** 'The message uses ALL CAPS and multiple exclamation marks, which is like shouting online.'\n\n👇**Click the button below to proceed to Step 2: Role-play**",
    "options": {"next": "Proceed to Step2️⃣", "back": "Back to menu"},
}
