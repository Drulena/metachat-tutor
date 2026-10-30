"""Transition row for scenario state ``roleplay_feedback_interpreter``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.
"""

BASE = "roleplay_feedback_interpreter"

ROW = {
    "next": {"revise": "role_interpreter", "next": "role_menu"},
    "back": "role_menu",
    "nav": {"next": "Next"},
    "retryable": True,
    "item": "role_interpreter",
    "phase": "roleplay",
    "accept": ["revise", "next"],
    "effects": {
        "revise": [("set-item", "role_interpreter", "in_progress")],
        "next": [("set-item", "role_interpreter", "completed")],
    },
    "rejected": None,
    "fixture": {
        "user_data": {
            "user_name": "Test Learner",
            "level": "beginner",
            "pretest_scores": [3, 4, 5],
            "posttest_scores": None,
            "current_role": "role_interpreter",
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
            "role_interpreter": "in_progress",
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
