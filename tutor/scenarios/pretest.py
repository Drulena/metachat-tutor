"""Scenario state ``pretest`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.
"""

STATE = {
    # The greeting moved here from the retired "start" state: the intake
    # form (ticket #37) supplies the name, so the chat opens greeted.
        "message": "Nice to meet you, {user_name}!\n\n**📋 PRE-TEST: Diagnostic Assessment**\n\nBefore we begin the training, please rate these three messages on a scale from 1 (destructive) to 5 (constructive):\n\n⬇️**Tap a number under each message.**",
    "validation": "^[1-5] [1-5] [1-5]$",
    # The three task lines, and the order they submit in (ticket #48): the
    # page prints each one, markdown and all, inside its own 1-5 chip row, so
    # the message above does not repeat it - the learner reads a task line
    # exactly once. Each prompt is the line exactly as the gate message used
    # to carry it - the bullet, the italics around the quote - less the letter
    # the row's badge shows, and the template renders it through the same
    # markdown filter as a message: the styling is the scenario's, not a
    # stylesheet's. The picks go out as the string the validation regex above
    # and the row's "accept" pattern already read (ADR-0007 decision 6).
    "scales": [
        {"letter": "A", "prompt": "▪️*'Your idea is wrong. Fix it.'*"},
        {"letter": "B", "prompt": "▪️*'I see your point, but have you considered... 🤔'*"},
        {"letter": "C", "prompt": "▪️*'THIS IS TERRIBLE!!!'*"},
    ],
}
