"""Transition row for scenario state ``level_assessment``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.
"""

ROW = {
    "next": {
        "1": "after_registration_beginner",
        "2": "after_registration_intermediate",
        "3": "after_registration_advanced",
    },
    "back": "after_registration_beginner",
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
