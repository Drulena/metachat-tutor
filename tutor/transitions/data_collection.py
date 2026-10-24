"""Transition row for scenario state ``data_collection``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.
"""

ROW = {
    "next": "end",
    "back": "after_registration_beginner",
    "nav": {"exit": "Exit"},
    "retryable": False,
    "item": None,
    "phase": "data_collection",
    "accept": ["exit"],
    "effects": [],
    "rejected": "Tell me your name: type 'name <your name>', then pick a level, or type 'back'.",
    "fixture": {
        "user_data": {
            "user_name": "Test Learner",
            "level": "beginner",
            "pretest_scores": [3, 4, 5],
            "posttest_scores": [4, 4, 4],
            "current_role": "role_mediator",
            "current_role_variant": None,
        },
        "items": {
            "pretest": "completed",
            "level_assessment": "completed",
            "analysis_task_1": "not_started",
            "analysis_task_2": "not_started",
            "role_mediator": "completed",
            "role_logical": "not_started",
            "role_idea_generator": "not_started",
            "role_researcher": "not_started",
            "role_interpreter": "not_started",
            "role_advocate": "not_started",
            "role_judge": "not_started",
            "role_peacemaker": "not_started",
            "role_empath": "not_started",
            "reflection": "completed",
            "posttest": "completed",
            "mode_analysis": "not_started",
            "mode_roleplay": "completed",
        },
    },
}
