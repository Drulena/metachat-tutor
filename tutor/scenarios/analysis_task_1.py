"""Scenario base state ``analysis_task_1`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.

Spec #16 C1-4 (ADR-0006): the level axis is a parameter. The three
level texts live side by side in one level-keyed map and the assembly
keys each entry under the base state name with the level as a key, not a
suffix, so level copy cannot drift: the framing of the task — the heading, the context line, the
question lead-in and the answer prompt — is shared, and only the
wording that differs between the levels sits in the map.
"""

#: The shared framing of the task copy (spec #16 C1-4): the heading
#: names the level, then the context and the message under review, then
#: the question, its hint and the answer prompt. ``{context}``,
#: ``{message}`` and ``{hint}`` are the randomization placeholders
#: filled in by :func:`tutor.scenarios.randomize_scenario`.
_HEAD = "**📝 TASK 1: Softening Criticism ("
_ANSWER_PROMPT = "⬇️**Type your answer"

#: The accept gate of every level of this state: any non-empty answer
#: (the state has no options — the learner types the answer).
_VALIDATION = ".+"


def _text(level: str, wording: dict[str, str]) -> str:
    """Assemble one level's task copy: the shared frame around its wording.

    ``wording`` is one entry of :data:`_COPY`: the message under
    review, the question, its hint line and the tail of the answer
    prompt.
    """
    return (
        f"{_HEAD}{level.capitalize()})**\n\n"
        "Context: {context}\n\n"
        f"Original message: {wording['message_field']}\n\n"
        f"❓ **Question:** {wording['question']}\n\n"
        f"{wording['hint_line']}\n\n"
        f"{_ANSWER_PROMPT}{wording['prompt_tail']}"
    )


#: The per-level wording of the axis, side by side (spec #16 C1-4): the
#: message under review (quoted at the two lower levels, bare at the
#: advanced one), the question, the hint line (the bulb marks the
#: intermediate level) and the tail of the answer prompt.
_COPY: dict[str, dict[str, str]] = {
    "beginner": {
        "message_field": "*{message}*",
        "question": "Which emoji(s) would you add to the END of this message to make it sound kinder? Explain your choice.",
        "hint_line": "*Hint: {hint}*",
        "prompt_tail": " and tap Enter:**",
    },
    "intermediate": {
        "message_field": "*{message}*",
        "question": "Which emoji(s) would you add to signal openness to dialogue?",
        "hint_line": "💡*Hint: {hint}*",
        "prompt_tail": " and tap Enter:**",
    },
    "advanced": {
        "message_field": "{message}",
        "question": "Where would you place emojis to maintain professionalism?",
        "hint_line": "*Hint: {hint}*",
        "prompt_tail": ":**",
    },
}

#: The task states, keyed by level (spec #16 C1-4). The assembly keys
#: this map under the base state name (C1-9); a state carries no options
#: — the answer is free text.
STATE: dict[str, dict] = {
    level: {"message": _text(level, wording), "validation": _VALIDATION}
    for level, wording in _COPY.items()
}
