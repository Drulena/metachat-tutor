"""Transition row for the base state ``analysis_intro``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.

Spec #16 C1-3 (ADR-0006): the level axis is a parameter — this one
module replaces the three triplet modules and the seam generates the
axis: :func:`axis_rows` keys the rows by suffixed name at assembly,
:func:`with_fixture_level` injects the level into the one fixture dict.
Targets spell base names, resolved by the row registry: ``back`` spells
the registration base state, converted in the preceding ticket (spec #16
C1-2), and ``next`` embeds the row level, joined by :func:`join_state`
at the construction point, because the analysis task axis is converted
in the following ticket (spec #16 C1-4).
"""

from ._registry import LEVEL_SUFFIXES, join_state, with_fixture_level

#: The base state name; :func:`axis_rows` generates the suffixed keys.
BASE = "analysis_intro"

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
        "analysis_task_1": "not_started",
        "analysis_task_2": "not_started",
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
        "next": join_state("analysis_task_1", level),
        "back": "after_registration",
        "nav": {"yes": "Yes"},
        "retryable": False,
        "item": "analysis_task_1",
        "phase": "analysis",
        "accept": ["yes"],
        "effects": [("set-item", "analysis_task_1", "in_progress")],
        "rejected": "Please confirm you want to proceed with the analysis.",
        "fixture": with_fixture_level(_FIXTURE, level),
    }


#: The level-keyed row map: the assembly generates the suffixed keys with
#: :func:`axis_rows` — suffixed names appear in no row module.
ROWS: dict[str, dict] = {level: _row(level) for level in LEVEL_SUFFIXES}
