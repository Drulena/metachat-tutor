"""Scenario state ``posttest`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**📋 POST-TEST**\n\nRate the same three messages again:\n\n⬇️**Tap a number under each message.**",
    "validation": "^[1-5] [1-5] [1-5]$",
    # The same three task lines the pretest rated, printed inside the rows
    # below the message (ticket #48); the posttest asks for the SAME messages,
    # so these literals match the pretest's exactly. The picks go out as the
    # string the validation regex above and the row's "accept" pattern already
    # read (ADR-0007 decision 6).
    "scales": [
        {"letter": "A", "prompt": "'Your idea is wrong. Fix it.'"},
        {"letter": "B", "prompt": "'I see your point, but have you considered... 🤔'"},
        {"letter": "C", "prompt": "'THIS IS TERRIBLE!!!'"},
    ],
}
