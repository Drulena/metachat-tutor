"""Scenario state ``data_collection`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "🎓 **🎉 RESEARCH SESSION COMPLETE, {user_name}!**\n\nThank you for participating!\n\n---\n\n**📤 TO SUBMIT YOUR WORK:**\n\n1️⃣Click the **Export Chat History** button in the left sidebar\n2️⃣Save the downloaded JSON file\n3️⃣Upload the file to this Google Form:\n🔗 **https://forms.gle/V2eyTz1kJRXJxv266**\n\nYour chat history contains:\n✅ Your name\n✅ Pre-test and post-test scores\n✅ All your answers with timestamps\n✅ Your reflection\n\n---\n\n🏁 **That's it! You can exit this chat now and return to your study course. Good luck!**\n\n👇**Tap *exit* to finish the interaction**",
    "options": {"exit": "Exit"},
}
