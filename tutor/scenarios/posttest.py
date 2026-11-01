"""Scenario state ``posttest`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**📋 POST-TEST**\n\nRate the same three messages again:\n\nA▪️*'Your idea is wrong. Fix it.'*\n\nB▪️*'I see your point, but have you considered... 🤔'*\n\nC▪️*'THIS IS TERRIBLE!!!'*\n\n⬇️**Choose a rating for A, B and C from the dropdowns:**",
    "validation": "^[1-5] [1-5] [1-5]$",
    # The prompts the gate offers as one 1-5 dropdown each, in the order they
    # submit (ticket #40). The page sends the picks as the string the validation
    # regex above and the row's 'accept' pattern already read (ADR-0007 d6).
    "scales": ["A", "B", "C"],
}
