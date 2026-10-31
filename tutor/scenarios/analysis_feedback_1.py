"""Scenario base state ``analysis_feedback_1`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.

Spec #16 C1-5 (ADR-0006): the level axis is a parameter. The three
level texts live side by side in one level-keyed map and the assembly
keys each entry under the base state name with the level as a key, not a
suffix, so level copy cannot drift: the framing of the feedback — the reading instruction naming
the level, the model-answer lead-in and the call to action — is
shared, and only the wording that differs between the levels sits in
the map. The model-answer lead-in is where the generated feedback is
spliced in (``tutor.tutor_session._ANALYSIS_MARKERS``): it sits in the
two lower levels and is absent at the advanced one, exactly as before.
Ticket #27: the axis is the one scenario constant — the ``LEVELS``
keys of :mod:`tutor.scenarios.common` — and :data:`_COPY` supplies the
level wording at each point of it.
"""

from .common import LEVELS

#: The shared framing of the feedback copy (spec #16 C1-5): the reading
#: instruction names the level, then the feedback line, then the model
#: answer, then the tap invitation. ``{user_name}`` is the placeholder
#: filled in when the turn is rendered.
_HEAD = "📖 **Read the feedback for you, {user_name} ("
_HEAD_TAIL = "), carefully and make notes:**"
_MODEL_ANSWER = "**📋 Model answer:** "
_TAP = "👇**Tap *next* to "
_TAP_TAIL = "**"
_PARAGRAPH = "\n\n"

#: The shared option map of the feedback state (all levels).
_OPTIONS = {"next": "Next Task", "back": "Back to menu"}


def _text(level: str, wording: dict[str, str | None]) -> str:
    """Assemble one level's feedback copy: the shared frame around its wording.

    ``wording`` is one entry of :data:`_COPY`: the feedback line, the
    model answer quoting it (``None`` at the advanced level) and the
    tail of the tap invitation.
    """
    parts = [f"{_HEAD}{level.capitalize()}{_HEAD_TAIL}", wording["feedback"]]
    if wording["model_answer"] is not None:
        parts.append(_MODEL_ANSWER + wording["model_answer"])
    parts.append(f"{_TAP}{wording['tap_tail']}{_TAP_TAIL}")
    return _PARAGRAPH.join(parts)


#: The per-level wording of the axis, side by side (spec #16 C1-5): the
#: feedback line, the model answer that answers it (the advanced level
#: has none) and the tail of the tap invitation (the beginner level
#: names the task the learner is on the way to).
_COPY: dict[str, dict[str, str | None]] = {
    "beginner": {
        "feedback": "Great start! Adding a friendly emoji like 🙂 or 😊 can make criticism feel more supportive.",
        "model_answer": "'This essay has some areas to work on 🙂. Let's look at them together.'",
        "tap_tail": "proceed to Task 2:",
    },
    "intermediate": {
        "feedback": "Good approach! A friendly emoji like 🙂 or 🤔 acts as an 'emotional cushion'.",
        "model_answer": "'I think the data in this part might need a second look 🤔.'",
        "tap_tail": "continue:",
    },
    "advanced": {
        "feedback": "For complex feedback, emoji after the main critique softens tone.",
        "model_answer": None,
        "tap_tail": "continue:",
    },
}

#: The feedback states, keyed by level (spec #16 C1-5), the axis read
#: from :data:`LEVELS` over the wording map (ticket #27). The assembly
#: keys this map under the base state name (C1-9); the options are
#: shared (``dict`` copies guard every mutation).
STATE: dict[str, dict] = {
    level: {"message": _text(level, _COPY[level]), "options": _OPTIONS}
    for level in LEVELS
}
