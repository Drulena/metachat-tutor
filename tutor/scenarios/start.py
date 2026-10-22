"""Scenario state ``start`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "Nice to meet you, {user_name}!\n\n⌨️**Type your name and group again to confirm:**",
    "validation": ".+",
}
