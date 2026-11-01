"""Scenario state ``posttest`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**📋 POST-TEST**\n\nRate the same three messages again:\n\nA▪️*'Your idea is wrong. Fix it.'*\n\nB▪️*'I see your point, but have you considered... 🤔'*\n\nC▪️*'THIS IS TERRIBLE!!!'*\n\n⬇️**Tap a number under each message.**",
    "validation": "^[1-5] [1-5] [1-5]$",
    # The prompts the gate offers as one 1-5 chip row each, in the order they
    # submit (ticket #48). "prompt" quotes the line from the message above, so
    # the page can put the control under the question it answers; the picks go
    # out as the string the validation regex above and the row's "accept"
    # pattern already read (ADR-0007 decision 6).
    "scales": [
        {"letter": "A", "prompt": "'Your idea is wrong. Fix it.'"},
        {"letter": "B", "prompt": "'I see your point, but have you considered... 🤔'"},
        {"letter": "C", "prompt": "'THIS IS TERRIBLE!!!'"},
    ],
}
