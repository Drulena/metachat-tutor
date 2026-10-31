"""Scenario base state ``analysis_intro`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.

Spec #16 C1-3 (ADR-0006): the level axis is a parameter. The three
level texts live side by side in a level-keyed map and the assembly
keys each entry under the base state name with the level as a key, not a
suffix, so level copy cannot drift: the framing of the intro, the step heading and the *yes*
invitation, is shared; only the level body sits in the map.
"""

#: The shared framing of the intro copy: the heading, then the level
#: body, then the call to action (spec #16 C1-3).
_HEAD = "**Step1️⃣: ANALYSIS**\n\n"
_TAIL = "\n\n👇**Click *yes* to start**"

#: The level bodies, side by side on the axis (spec #16 C1-3): one map,
#: three texts, so the level wording is readable as one diff and cannot
#: drift apart.
_BODIES: dict[str, str] = {
    "beginner": "You'll learn to identify basic metagrapheme functions and practice softening simple criticism using examples of online comments.",
    "intermediate": "You'll analyze more complex examples of online comments and practice nuanced use of metagraphemes.",
    "advanced": "You'll work with complex, multi-layered examples of online comments and cultural comparisons.",
}

#: The shared option map of the intro state (all levels).
_OPTIONS = {"yes": "Yes, proceed", "back": "Back to menu"}

#: The intro states, keyed by level (spec #16 C1-3). The assembly keys
#: this map under the base state name (C1-9); the options are shared
#: (``dict`` copies guard every mutation).
STATE: dict[str, dict] = {
    level: {"message": _HEAD + body + _TAIL, "options": _OPTIONS}
    for level, body in _BODIES.items()
}
