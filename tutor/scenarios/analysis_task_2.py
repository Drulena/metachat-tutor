"""Scenario base state ``analysis_task_2`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.

Spec #16 C1-6 (ADR-0006): the level axis is a parameter. The three
level texts live side by side in one level-keyed map and the assembly
generates the suffixed scenario keys from it, so level copy cannot
drift: the framing of the task — the heading, the message under
review and the question lead-in — is shared, and only the wording that
differs between the levels sits in the map: the question, the quoted
message at the beginner level, the hint line (the bulb marks the two
lower levels, the advanced one gets no hint) and the answer prompt
(the advanced level asks for a full analysis, not a short answer).
"""

#: The shared framing of the task copy (spec #16 C1-6): the heading
#: names the level, then the message under review, then the question,
#: its hint (the two lower levels) and the answer prompt. ``{message}``
#: and ``{hint}`` are the randomization placeholders filled in by
#: :func:`tutor.scenarios.randomize_scenario`.
_HEAD = "**📝 TASK 2: Recognizing Aggressive Formatting ("
_ANSWER_PROMPT = "⬇️**Type your answer and tap Enter:**"

#: The accept gate of every level of this state: any non-empty answer
#: (the state has no options — the learner types the answer).
_VALIDATION = ".+"


def _text(level: str, wording: dict[str, str]) -> str:
    """Assemble one level's task copy: the shared frame around its wording.

    ``wording`` is one entry of :data:`_COPY`: the message under
    review, the question, its hint line (empty at the advanced level,
    which omits the hint block) and the answer prompt.
    """
    hint = wording["hint_line"]
    return (
        f"{_HEAD}{level.capitalize()})**\n\n"
        f"Message: {wording['message_field']}\n\n"
        f"❓ **Question:** {wording['question']}\n\n"
        + (f"{hint}\n\n" if hint else "")
        + wording["prompt"]
    )


#: The per-level wording of the axis, side by side (spec #16 C1-6): the
#: message under review (quoted at the beginner level), the question,
#: the hint line (shared by the two lower levels) and the answer
#: prompt (shared by the two lower levels; the advanced level's asks
#: for the whole analysis).
_COPY: dict[str, dict[str, str]] = {
    "beginner": {
        "message_field": "*{message}*",
        "question": "What makes this message feel aggressive? Identify ONE technique.",
        "hint_line": "💡*Hint: {hint}*",
        "prompt": _ANSWER_PROMPT,
    },
    "intermediate": {
        "message_field": "{message}",
        "question": "Identify TWO metagrapheme techniques used here.",
        "hint_line": "💡*Hint: {hint}*",
        "prompt": _ANSWER_PROMPT,
    },
    "advanced": {
        "message_field": "{message}",
        "question": "Analyze ALL metagrapheme techniques used here.",
        "hint_line": "",
        "prompt": "⌨️**Type your analysis:**",
    },
}

#: The task states, keyed by level (spec #16 C1-6). The assembly spells
#: each suffixed scenario key from this map; a state carries no options
#: — the answer is free text.
STATE: dict[str, dict] = {
    level: {"message": _text(level, wording), "validation": _VALIDATION}
    for level, wording in _COPY.items()
}
