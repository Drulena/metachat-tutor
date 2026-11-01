"""Scenario state ``pretest`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    # The greeting moved here from the retired "start" state: the intake
    # form (ticket #37) supplies the name, so the chat opens greeted.
        "message": "Nice to meet you, {user_name}!\n\n**📋 PRE-TEST: Diagnostic Assessment**\n\nBefore we begin the training, please rate these three messages on a scale from 1 (destructive) to 5 (constructive):\n\nA▪️*'Your suggestion is wrong. Fix it.'*\n\nB▪️*'I see your point, but have you considered... 🤔'*\n\nC▪️*'THIS IS AWFUL!!!'*\n\n⬇️**Type three numbers separated by spaces (e.g., '1 5 2') and tap Enter:**",
    "validation": "^[1-5] [1-5] [1-5]$",
}
