"""Scenario state ``role_menu`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**❇️ CONSTRUCTIVE COMMUNICATIVE ROLES**\n\n \n\n**CONFLICT REGULATORS:**\n🔹1 - Mediator (de-escalates conflicts)\n🔹2 - Logical Expert (highlights contradictions)\n🔹3 - Advocate (defends a person/idea)\n🔹4 - Judge (evaluates arguments from all the sides)\n🔹5 - Peacemaker (offers compromise)\n\n**SUPPORTING ROLES:**\n🔹6 - Idea Generator (sparks creative thinking)\n🔹7 - Researcher (conducts cultural inquiry)\n🔹8 - Interpreter (facilitates cultural bridging)\n\n**EMOTIONAL ROLES:**\n🔹9 - Empath (provides emotional support)\n\n📌 👇**Tap the button below to choose a role**\n\n\Once completed all the roles, tap *Finish* to proceed to Reflection🏁",
    "options": {
        "1": "Mediator",
        "2": "Logical Expert",
        "3": "Advocate",
        "4": "Judge",
        "5": "Peacemaker",
        "6": "Idea Generator",
        "7": "Researcher",
        "8": "Interpreter",
        "9": "Empath",
        "finish": "Finish roles",
        "back": "Back to Role-Play Intro",
    },
    "next_state": {
        "1": "role_mediator",
        "2": "role_logical",
        "3": "role_advocate",
        "4": "role_judge",
        "5": "role_peacemaker",
        "6": "role_idea_generator",
        "7": "role_researcher",
        # Quirk (preserved verbatim from the legacy single file): "8" is a
        # typo for ``role_interpreter``. Live routing goes through
        # ``ROLE_BY_VALUE`` (8 -> role_peacemaker), so the value is dead;
        # the transition table (tutor/transitions/role_menu.py) uses the
        # correct name.
        "8": "role_interpreterer",
        "9": "role_empath",
        "finish": "reflection",
        "back": "roleplay_intro",
    },
}
