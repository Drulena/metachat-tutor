"""Scenario base state ``analysis_feedback_2`` of the MetaChat Tutor.

Part of the pure-data scenario definition; see :mod:`tutor.scenarios`
for the assembled ``SCENARIO`` dict and
:func:`tutor.scenarios.randomize_scenario` for task randomization.

Spec #16 C1-7 (ADR-0006): the level axis is a parameter. The three
level texts live side by side in one level-keyed map and the assembly
keys each entry under the base state name with the level as a key, not a
suffix, so level copy cannot drift: the framing of the feedback — the reading instruction naming
the level, the model-answer lead-in and the option map — is shared,
and only the wording that differs between the levels sits in the map:
the feedback line, the model answer (the advanced level has none) and
the call to action (the beginner level names the role-play step it
walks to, the other two share the tap invitation). The model-answer
lead-in is where the generated feedback is spliced in
(``tutor.tutor_session._ANALYSIS_MARKERS``): it sits in the two lower
levels and is absent at the advanced one, exactly as before.
"""

#: The shared framing of the feedback copy (spec #16 C1-7): the reading
#: instruction names the level, then the feedback line, then the model
#: answer, then the call to action. ``{user_name}`` is the placeholder
#: filled in when the turn is rendered.
_HEAD = "📖 **Read the feedback for you, {user_name} ("
_HEAD_TAIL = "), carefully and make notes:**"
_MODEL_ANSWER = "**📋 Model answer:** "
_PARAGRAPH = "\n\n"

#: The shared option map of the feedback state (all levels). The label
#: ends in one keycap — DIGIT TWO, VARIATION SELECTOR-16, COMBINING
#: ENCLOSING KEYCAP — the exact codepoints the original copy carried.
_OPTIONS = {"next": "Proceed to Step2️⃣", "back": "Back to menu"}


def _text(level: str, wording: dict[str, str | None]) -> str:
    """Assemble one level's feedback copy: the shared frame around its wording.

    ``wording`` is one entry of :data:`_COPY`: the feedback line, the
    model answer quoting it (``None`` at the advanced level) and the
    call to action closing the analysis arc.
    """
    parts = [f"{_HEAD}{level.capitalize()}{_HEAD_TAIL}", wording["feedback"]]
    if wording["model_answer"] is not None:
        parts.append(_MODEL_ANSWER + wording["model_answer"])
    parts.append(wording["cta"])
    return _PARAGRAPH.join(parts)


#: The per-level wording of the axis, side by side (spec #16 C1-7): the
#: feedback line, the model answer that answers it (the advanced level
#: has none) and the call to action — the beginner level names the step
#: the learner is on the way to, the two other levels share the tap
#: invitation.
_COPY: dict[str, dict[str, str | None]] = {
    "beginner": {
        "feedback": "You're right! **ALL CAPS** feels like shouting online.",
        "model_answer": "'The message uses ALL CAPS and multiple exclamation marks, which is like shouting online.'",
        "cta": "👇**Click the button below to proceed to Step 2: Role-play**",
    },
    "intermediate": {
        "feedback": "Key techniques: Alternating caps (mockery) and multiple exclamation marks (shouting).",
        "model_answer": "'The message uses **tHaT's NoT** with alternating caps to mock, and **!!!** to shout.'",
        "cta": "👇**Tap *next* to proceed:**",
    },
    "advanced": {
        "feedback": "Techniques: ALL CAPS (irony), ellipsis (dramatic pause), 🙄 emoji (sarcasm), #facepalm (meta-commentary).",
        "model_answer": None,
        "cta": "👇**Tap *next* to proceed:**",
    },
}

#: The feedback states, keyed by level (spec #16 C1-7). The assembly
#: keys this map under the base state name (C1-9); the options are
#: shared (``dict`` copies guard every mutation).
STATE: dict[str, dict] = {
    level: {"message": _text(level, wording), "options": _OPTIONS}
    for level, wording in _COPY.items()
}
