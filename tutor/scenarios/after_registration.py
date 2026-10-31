"""Scenario base state ``after_registration`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.

Spec #16 C1-2 (ADR-0006): the level axis is a parameter. The three
level texts live side by side in a level-keyed map and the assembly
keys each entry under the base state name with the level as a key, not a
suffix, so level copy cannot drift: the strings are byte-identical at every level except the level
word embedded in the greeting, which :func:`_text` embeds from the
axis value.
"""

#: The shared option map of the registration state (all levels).
_OPTIONS = {"1": "Step1️⃣: ANALYSIS", "2": "Step2️⃣: ROLE-PLAY"}


def _text(level_word: str) -> str:
    """Build the registration copy, embedding the level word in the greeting."""
    return (
        "Thank you, {user_name}! (Level: " + level_word + ")\n\n"
        "**📌 IMPORTANT INSTRUCTIONS:**\n"
        "•🔙Go back anytime by typing *back*, or clicking the button below.\n"
        "•👈Track **your progress** via the **left sidebar**.\n\n"
        "Choose how to start your practice👇\n\n"
    )


#: The registration states, keyed by level (spec #16 C1-2). The
#: assembly keys this map under the base state name (C1-9); the
#: options are shared (``dict`` copies guard every mutation).
STATE: dict[str, dict] = {
    level: {"message": _text(level.capitalize()), "options": _OPTIONS}
    for level in ("beginner", "intermediate", "advanced")
}
