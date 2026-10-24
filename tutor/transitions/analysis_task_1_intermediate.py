"""Transition row for scenario state ``analysis_task_1_intermediate``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.
"""

ROW = {
    "next": "analysis_feedback_1_intermediate",
    "back": "analysis_intro_intermediate",
    "nav": {},
    "retryable": False,
    "item": "analysis_task_1",
    "phase": "analysis",
    "accept": None,
    "effects": [("set-item", "analysis_task_1", "completed")],
    "rejected": None,
    "fixture": {
        "user_data": {
            "user_name": "Test Learner",
            "level": "intermediate",
            "pretest_scores": [3, 4, 5],
            "posttest_scores": None,
            "current_role": None,
            "current_role_variant": None,
        },
        "items": {
            "pretest": "completed",
            "level_assessment": "completed",
            "analysis_task_1": "in_progress",
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
    },
}
