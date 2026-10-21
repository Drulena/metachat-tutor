"""Transition row for scenario state ``after_registration_advanced``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.
"""

ROW = {
    "next": {"1": "analysis_intro_advanced", "2": "roleplay_intro"},
    "back": "after_registration_advanced",
    "nav": {},
    "retryable": False,
    "item": None,
    "phase": "registration",
    "accept": ["1", "2"],
    "effects": {
        "1": [("set-item", "mode_analysis", "completed")],
        "2": [("set-item", "mode_roleplay", "completed")],
    },
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
