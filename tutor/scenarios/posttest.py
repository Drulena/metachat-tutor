"""Scenario state ``posttest`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    "message": "**📋 POST-TEST**\n\nRate the same three messages again:\n\nA▪️*'Your idea is wrong. Fix it.'*\n\nB▪️*'I see your point, but have you considered... 🤔'*\n\nC▪️*'THIS IS TERRIBLE!!!'*\n\n⬇️**Type three numbers (e.g., '1 5 2'):**",
    "validation": "^[1-5] [1-5] [1-5]$",
}
