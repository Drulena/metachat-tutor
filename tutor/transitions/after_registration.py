"""Transition row for the base state ``after_registration``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.

Spec #16 C1-2 (ADR-0006): the level axis is a parameter — this one
module replaces the three triplet modules and the seam generates the
axis: :func:`axis_pairs` keys the rows by ``(base, level)`` pair at assembly,
:func:`with_fixture_level` injects the level into the one fixture
dict. Targets spell base names, resolved by the row registry at the
row's own level (ADR-0002's mechanism built at the construction
point): ``next`` names the base states the learner goes to from here
— the analysis intro since spec #16 C1-3, the role-play intro being a
single-form state — and ``back`` is ``None``: registration is the point
of no return (spec #16 C1-8, ADR-0006 decision 2); the escape from a
mis-pick is reset, not back.
"""

from ._registry import LEVEL_SUFFIXES, with_fixture_level

#: The base state name; :func:`axis_pairs` generates the pair keys.
BASE = "after_registration"

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
        "mode_analysis": "not_started",
        "mode_roleplay": "not_started",
    },
}


def _row(level: str) -> dict:
    """Build the axis row for one level; level targets come from the seam."""
    return {
        "next": {
            "1": "analysis_intro",
            "2": "roleplay_intro",
        },
        "back": None,
        "nav": {},
        "retryable": False,
        "item": None,
        "phase": "registration",
        "accept": ["1", "2"],
        "effects": {
            "1": [("set-item", "mode_analysis", "completed")],
            "2": [("set-item", "mode_roleplay", "completed")],
        },
        "rejected": "Choose the level to continue with.",
        "fixture": with_fixture_level(_FIXTURE, level),
    }


#: The level-keyed row map: the assembly generates the pair keys with
#: :func:`axis_pairs` — a state name never carries the level.
ROWS: dict[str, dict] = {level: _row(level) for level in LEVEL_SUFFIXES}
