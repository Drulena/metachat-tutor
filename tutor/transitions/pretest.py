"""Transition row for scenario state ``pretest``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.
"""

BASE = "pretest"

ROW = {
    # The intake form registered the level, so the pretest answer hands the
    # session straight to the axis (ADR-0006 amendment 2026-11-01).
    "next": "after_registration",
    "back": None,  # the intake form sits behind the point of no return
    "nav": {},
    "retryable": False,
    "item": "pretest",
    "phase": "registration",
    "accept": "^[1-5] [1-5] [1-5]$",
    "effects": [
        ("set-user-data", "pretest_scores", "parsed-scores"),
        ("set-item", "pretest", "completed"),
    ],
    "rejected": "Type your answer to the pretest task: three numbers from 1 to 5 separated by spaces.",
    "fixture": {
        "user_data": {
            "user_name": "Test Learner",
            "level": "beginner",
            "pretest_scores": None,
            "posttest_scores": None,
            "current_role": None,
            "current_role_variant": None,
        },
        "items": {
            "pretest": "not_started",
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
