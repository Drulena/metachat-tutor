"""Transition row for scenario state ``start``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.
"""

ROW = {
    "next": "pretest",
    "back": None,
    "nav": {},
    "retryable": False,
    "item": None,
    "phase": "registration",
    "accept": None,
    "effects": [("set-user-data", "user_name", "sanitized-name")],
    "rejected": None,
    "fixture": {
        "user_data": {
            "user_name": None,
            "level": None,
            "pretest_scores": None,
            "posttest_scores": None,
            "current_role": None,
            "current_role_variant": None,
        },
        "items": {
            "pretest": "not_started",
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
