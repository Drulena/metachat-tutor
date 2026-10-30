"""Transition row for the base state ``analysis_task_2``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.

Spec #16 C1-6 (ADR-0006): the level axis is a parameter — this one
module replaces the three triplet modules and the seam generates the
axis: :func:`axis_rows` keys the rows by suffixed name at assembly,
:func:`with_fixture_level` injects the level into the one fixture
dict. `back` spells the intro base state, converted in an earlier
ticket (spec #16 C1-3), so the seam resolves it with the session's
level. `next` spells the feedback-2 base state, converted in the
following ticket (spec #16 C1-7), so the seam resolves it with the
session's level - the exception that named the feedback-2 axis by
level inside this row retires there.
"""

from ._registry import LEVEL_SUFFIXES, with_fixture_level

#: The base state name; :func:`axis_rows` generates the suffixed keys.
BASE = "analysis_task_2"

#: The one per-base fixture dict (ADR-0006 decision 6): the seam
#: generates the axis by injecting ``user_data["level"]`` per level.
_FIXTURE = {
    "user_data": {
        "user_name": "Test Learner",
        "level": None,
        "pretest_scores": [3, 4, 5],
        "posttest_scores": None,
        "current_role": None,
        "current_role_variant": None,
    },
    "items": {
        "pretest": "completed",
        "level_assessment": "completed",
        "analysis_task_1": "completed",
        "analysis_task_2": "in_progress",
        "role_mediator": "not_started",
        "role_logical": "not_started",
        "role_idea_generator": "not_started",
        "role_researcher": "not_started",
        "role_interpreter": "not_started",
        "role_advocate": "not_started",
        "role_judge": "not_started",
        "role_peacemaker": "not_started",
        "role_empath": "not_started",
        "reflection": "not_started",
        "posttest": "not_started",
        "mode_analysis": "completed",
        "mode_roleplay": "not_started",
    },
}


def _row(level: str) -> dict:
    """Build the axis row for one level; level targets come from the seam."""
    return {
        "next": "analysis_feedback_2",
        "back": "analysis_intro",
        "nav": {},
        "retryable": False,
        "item": "analysis_task_2",
        "phase": "analysis",
        "accept": None,
        "effects": [("set-item", "analysis_task_2", "completed")],
        "rejected": None,
        "fixture": with_fixture_level(_FIXTURE, level),
    }


#: The level-keyed row map: the assembly generates the suffixed keys with
#: :func:`axis_rows` — suffixed names appear in no row module.
ROWS: dict[str, dict] = {level: _row(level) for level in LEVEL_SUFFIXES}
