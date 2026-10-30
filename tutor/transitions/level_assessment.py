"""Transition row for scenario state ``level_assessment``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.
"""

BASE = "level_assessment"

ROW = {
    # The accept map targets the registration BASE state (spec #16
    # C1-2, ADR-0006): the parsed-level effect lands the session's
    # level and the row registry resolves the pair — no suffixed
    # target literal survives in this row's accept map.
    "next": {
        "1": "after_registration",
        "2": "after_registration",
        "3": "after_registration",
    },
    "back": "pretest",  # true predecessor (C1-8)
    "nav": {},
    "retryable": False,
    "item": "level_assessment",
    "phase": "registration",
    "accept": ["1", "2", "3"],
    "effects": {
        "1": [
            ("set-user-data", "level", "parsed-level"),
            ("set-item", "level_assessment", "completed"),
        ],
        "2": [
            ("set-user-data", "level", "parsed-level"),
            ("set-item", "level_assessment", "completed"),
        ],
        "3": [
            ("set-user-data", "level", "parsed-level"),
            ("set-item", "level_assessment", "completed"),
        ],
    },
    "rejected": "Choose a level by number, or type 'back'.",
    "fixture": {
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
            "level_assessment": "not_started",
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
    },
}
