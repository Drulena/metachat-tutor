"""Transition row for scenario state ``analysis_feedback_2_advanced``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.
"""

ROW = {
    "next": "roleplay_intro",
    "back": "analysis_intro_advanced",
    "nav": {"next": "Next"},
    "retryable": True,
    "item": "analysis_task_2",
    "phase": "analysis",
    "accept": ["next"],
    "effects": [("set-item", "analysis_task_2", "completed")],
    "fixture": {
        "user_data": {
            "user_name": "Test Learner",
            "level": "advanced",
            "pretest_scores": [3, 4, 5],
            "posttest_scores": None,
            "current_role": None,
            "current_role_variant": None,
        },
        "items": {
            "pretest": "completed",
            "level_assessment": "completed",
            "analysis_task_1": "completed",
            "analysis_task_2": "completed",
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
