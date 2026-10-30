"""Transition row for scenario state ``role_menu``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.
"""

BASE = "role_menu"

ROW = {
    "next": {
        "1": "role_mediator",
        "2": "role_logical",
        "3": "role_idea_generator",
        "4": "role_researcher",
        "5": "role_interpreter",
        "6": "role_advocate",
        "7": "role_judge",
        "8": "role_peacemaker",
        "9": "role_empath",
        "finish": "reflection",
    },
    "back": "roleplay_intro",
    "nav": {"finish": "Finish roles"},
    "retryable": False,
    "item": None,
    "phase": "roleplay",
    "accept": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "finish"],
    "effects": {
        "1": [
            ("set-user-data", "current_role", "mapped-role"),
            ("set-item", "role_mediator", "in_progress"),
        ],
        "2": [
            ("set-user-data", "current_role", "mapped-role"),
            ("set-item", "role_logical", "in_progress"),
        ],
        "3": [
            ("set-user-data", "current_role", "mapped-role"),
            ("set-item", "role_idea_generator", "in_progress"),
        ],
        "4": [
            ("set-user-data", "current_role", "mapped-role"),
            ("set-item", "role_researcher", "in_progress"),
        ],
        "5": [
            ("set-user-data", "current_role", "mapped-role"),
            ("set-item", "role_interpreter", "in_progress"),
        ],
        "6": [
            ("set-user-data", "current_role", "mapped-role"),
            ("set-item", "role_advocate", "in_progress"),
        ],
        "7": [
            ("set-user-data", "current_role", "mapped-role"),
            ("set-item", "role_judge", "in_progress"),
        ],
        "8": [
            ("set-user-data", "current_role", "mapped-role"),
            ("set-item", "role_peacemaker", "in_progress"),
        ],
        "9": [
            ("set-user-data", "current_role", "mapped-role"),
            ("set-item", "role_empath", "in_progress"),
        ],
        "finish": [],
    },
    "rejected": "Choose one of the numbered roles, finish, or back.",
    "fixture": {
        "user_data": {
            "user_name": "Test Learner",
            "level": "beginner",
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
            "mode_roleplay": "completed",
        },
    },
}
