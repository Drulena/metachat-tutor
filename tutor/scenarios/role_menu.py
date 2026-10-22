"""Scenario state ``role_menu`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**❇️ CONSTRUCTIVE COMMUNICATIVE ROLES**\n\n \n\n🔹1 - Mediator (de-escalates conflicts)\n🔹2 - Logical Expert (highlights contradictions)\n🔹3 - Idea Generator (sparks creative thinking)\n🔹4 - Researcher (conducts cultural inquiry)\n🔹5 - Interpreter (facilitates cultural bridging)\n🔹6 - Advocate (defends a person/idea)\n🔹7 - Judge (evaluates arguments from all the sides)\n🔹8 - Peacemaker (offers compromise)\n🔹9 - Empath (provides emotional support)\n\n📌 👇**Tap the button below to choose a role**\n\n\Once completed all the roles, tap *Finish* to proceed to Reflection🏁",
    "options": {
        "1": "Mediator",
        "2": "Logical Expert",
        "3": "Idea Generator",
        "4": "Researcher",
        "5": "Interpreter",
        "6": "Advocate",
        "7": "Judge",
        "8": "Peacemaker",
        "9": "Empath",
        "finish": "Finish roles",
        "back": "Back to Role-Play Intro",
    },
}
