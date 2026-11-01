"""Transition row for scenario state ``data_collection``.

Part of the pure-data transition table (ticket #8); see
:mod:`tutor.transitions` for the row schema and
:func:`tutor.transitions.validate_transitions` for validation.
"""

BASE = "data_collection"

ROW = {
    # The terminal screen (ticket #39, ADR-0007 decision 4). The machine
    # stops here: no next, no back edge, no nav map. Routing therefore
    # answers every input on the spot with this row's own copy - the
    # learner cannot leave, and the retired ``end`` state has nothing left
    # to hand the session on to. ``phase`` is the banner key the panel
    # reads as finished, spelled by the row now that no state name does.
    "next": None,
    "back": None,
    "nav": {},
    "retryable": False,
    "item": None,
    "phase": "finished",
    "accept": None,
    "effects": [],
    "rejected": (
        "The session is complete - there is nothing left to answer. "
        "Export your chat history from the sidebar."
    ),
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
