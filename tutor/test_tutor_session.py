"""Behavioral tests for :class:`tutor.tutor_session.TutorSession` (ticket #3).

Runs against :class:`~tutor.session.MemoryStorage` and a deterministic
fake LLM — no network, no Django session, no view code.
"""

from dataclasses import fields

from django.test import SimpleTestCase

from .data import ANALYSIS_LABELS, ANALYSIS_STEP_KEYS, ROLE_LABELS, ROLE_STEP_KEYS, SCENARIO, STEP_KEYS, randomize_scenario
from .session import MemoryStorage, State, Summary
from .tutor_session import TutorSession

#: Input sequence that drives a fresh session to the role menu.
#: Shared with :mod:`tutor.test_views` so the two test modules cannot drift.
ROLE_MENU_INPUTS = [
    "Alice",            # start -> pretest
    "3 4 5",            # pretest -> level_assessment
    "2",                # level_assessment -> after_registration_intermediate
    "1",                # -> analysis_intro_intermediate
    "yes",              # -> analysis_task_1_intermediate
    "Answer to task one",   # -> analysis_feedback_1_intermediate
    "next",             # -> analysis_task_2_intermediate
    "Answer to task two",   # -> analysis_feedback_2_intermediate
    "next",             # -> roleplay_intro
    "continue",         # -> role_menu
]


class FakeLLM:
    """Deterministic feedback callable matching the Feedback protocol."""

    def __init__(self, fail_times: int = 0, text: str = "LLM-OUT") -> None:
        self.fail_times = fail_times
        self.text = text
        self.calls: list[tuple] = []

    def __call__(
        self,
        user_answer: str,
        role_name: str | None,
        user_name: str,
        level: str,
        task_question: str | None = None,
    ) -> tuple[str, bool]:
        self.calls.append((user_answer, role_name, user_name, level, task_question))
        if len(self.calls) <= self.fail_times:
            return "**🤖 LLM Feedback (API not configured):** test failure", True
        return self.text, False


class TutorSessionTests(SimpleTestCase):
    def make_session(self, llm: FakeLLM | None = None, started: bool = True):
        storage = MemoryStorage()
        llm = llm if llm is not None else FakeLLM()
        session = TutorSession(storage, llm)
        if started:
            session.start()
        return session, storage, llm

    def drive(self, session: TutorSession, *inputs: str) -> TutorSession:
        for text in inputs:
            session.submit(text)
        return session

    def state_of(self, storage: MemoryStorage) -> State:
        state = storage.load()
        self.assertIsNotNone(state)
        return state

    # ------------------------------------------------------------- starting

    def test_start_creates_fresh_session_and_welcome_turn(self):
        session, storage, _ = self.make_session()
        turn = session.turns()[-1]
        self.assertEqual(turn.role, "assistant")
        self.assertEqual(turn.state, "start")
        self.assertIn("Nice to meet you", turn.message)

        state = self.state_of(storage)
        self.assertEqual(state.current_state, "start")
        self.assertEqual(len(state.chat_history), 1)
        self.assertTrue(all(v == "not_started" for v in state.user_data["items"].values()))

    def test_progress_before_any_input_is_all_zero_summary(self):
        session, _, _ = self.make_session()
        summary = session.progress()
        self.assertEqual(summary.status_badge, "not_started")
        self.assertEqual(summary.percentage, 0)
        self.assertEqual(summary.current_step, 0)
        self.assertEqual(summary.total_steps, 15)
        self.assertEqual(summary.completed_steps_count, 0)
        self.assertEqual(summary.analysis_progress, {"completed": 0, "total": 2, "percentage": 0})
        self.assertEqual(summary.roleplay_progress, {"completed": 0, "total": 9, "percentage": 0})
        self.assertEqual(summary.completed_option_values, [])
        self.assertEqual(summary.completed_roles, [])
        self.assertEqual(summary.completed_modes, [])
        self.assertEqual(summary.opened_tasks, [])
        self.assertIsNone(summary.level)
        self.assertEqual(summary.phase, "registration")
        self.assertIsNone(summary.user_name)
        self.assertTrue(summary.session_id)  # a started session always has an id

    def test_first_turn_uses_placeholder_when_name_unavailable(self):
        session, _, _ = self.make_session()
        turn = session.turns()[-1]
        self.assertIn("Nice to meet you, student!", turn.message)
        self.assertNotIn("{user_name}", turn.message)

    def test_blank_name_renders_placeholder_in_later_turns(self):
        session, _, _ = self.make_session()
        self.drive(session, "   ", "3 4 5", "1")  # whitespace-only name -> beginner
        turn = session.turns()[-1]
        self.assertIn("Thank you, student! (Level: Beginner)", turn.message)
        self.assertNotIn("{user_name}", turn.message)

    def test_captured_name_renders_in_later_turns(self):
        session, _, _ = self.make_session()
        self.drive(session, "Alice", "3 4 5", "2")
        turn = session.turns()[-1]
        self.assertIn("Thank you, Alice! (Level: Intermediate)", turn.message)
        self.assertNotIn("{user_name}", turn.message)

    def test_summary_exposes_all_seventeen_fields(self):
        session, _, _ = self.make_session()
        summary = session.progress()
        names = [f.name for f in fields(Summary)]
        self.assertEqual(
            names,
            [
                "status_badge", "percentage", "current_step", "total_steps",
                "completed_steps_count", "analysis_progress", "roleplay_progress",
                "completed_option_values", "completed_roles", "completed_modes",
                "analysis_tasks", "role_tasks", "opened_tasks", "level", "phase",
                "user_name", "session_id",
            ],
        )
        self.assertEqual(summary.analysis_tasks, [(k, ANALYSIS_LABELS[k]) for k in ANALYSIS_STEP_KEYS])
        self.assertEqual(summary.role_tasks, [(k, ROLE_LABELS[k]) for k in ROLE_STEP_KEYS])

    def test_reset_clears_the_stored_session(self):
        session, storage, _ = self.make_session()
        session.reset()
        self.assertIsNone(storage.load())
        # and a fresh start works afterwards
        turn = session.start()
        self.assertEqual(turn.state, "start")

    def test_submit_requires_a_started_session(self):
        session, _, _ = self.make_session(started=False)
        with self.assertRaises(RuntimeError):
            session.submit("hi")
        with self.assertRaises(RuntimeError):
            session.turns()
        with self.assertRaises(RuntimeError):
            session.progress()

    # -------------------------------------------------------- happy path

    def drive_to_role_menu(self, session: TutorSession) -> TutorSession:
        return self.drive(session, *ROLE_MENU_INPUTS)

    def test_full_single_role_path_reaches_end(self):
        session, storage, _ = self.make_session()
        self.drive_to_role_menu(session)
        self.drive(
            session,
            "1",                # -> role_mediator
            "I mediate the conflict",  # -> roleplay_feedback_mediator
            "next",             # -> role_menu (mediator completed)
            "finish",           # -> reflection
            "A long reflection",  # -> posttest
            "4 4 4",            # -> data_collection
            "exit",             # -> end
        )
        self.assertEqual(self.state_of(storage).current_state, "end")

        summary = session.progress()
        self.assertEqual(summary.status_badge, "in_progress")
        self.assertEqual(summary.percentage, 46)  # 7 of 15 items
        self.assertEqual(summary.current_step, 0)
        self.assertEqual(summary.phase, "finished")
        self.assertEqual(summary.completed_roles, ["role_mediator"])
        self.assertEqual(summary.completed_modes, ["analysis"])  # path picks "1"
        self.assertEqual(summary.analysis_progress, {"completed": 2, "total": 2, "percentage": 100})
        self.assertEqual(summary.roleplay_progress, {"completed": 1, "total": 9, "percentage": 11})
        # the final turn is the user's "exit" — no assistant turn at "end"
        last = session.turns()[-1]
        self.assertEqual(last.role, "user")
        # the user turn records the state it was submitted in
        self.assertEqual(last.state, "data_collection")
        self.assertIsNone(last.options)

    def test_idea_generator_path_yields_the_feedback_turn(self):
        """Issue #12: the Idea Generator gets a feedback turn like every other role.

        The state key the routing lands on must be a state the scenario
        defines, so the assistant turn is appended, the role's task context
        reaches the LLM, and the options match the other feedback states.
        """
        llm = FakeLLM()
        session, storage, _ = self.make_session(llm=llm)
        self.drive_to_role_menu(session)
        self.drive(session, "3")
        self.assertEqual(self.state_of(storage).current_state, "role_idea_generator")
        turn = self.drive(session, "Two ideas, **bold** and 💡").turns()[-1]

        self.assertEqual(
            self.state_of(storage).current_state, "roleplay_feedback_idea_generator"
        )
        # the assistant feedback turn is appended, not silently dropped
        self.assertEqual(turn.role, "assistant")
        self.assertEqual(turn.state, "roleplay_feedback_idea_generator")
        # the role's answer and task context reach the LLM, and its output shows
        self.assertEqual(llm.calls[-1][1], "idea_generator")
        self.assertEqual(llm.calls[-1][0], "Two ideas, **bold** and 💡")
        self.assertIn("LLM-OUT", turn.message)

        # the same options as every other role's feedback state offers
        mediator, _, _ = self.make_session()
        self.drive_to_role_menu(mediator)
        self.drive(mediator, "1", "I mediate")
        self.assertEqual(turn.options, mediator.turns()[-1].options)

        # the feedback state maps to the real completion-model item, not a phantom
        summary = session.progress()
        self.assertEqual(summary.current_step, STEP_KEYS.index("role_idea_generator") + 1)
        self.assertEqual(summary.completed_roles, [])  # completes on "next", not here
        self.drive(session, "next")
        self.assertEqual(session.progress().completed_roles, ["role_idea_generator"])

    def test_all_items_completed_gives_full_summary(self):
        session, storage, _ = self.make_session()
        state = self.state_of(storage)
        for key in state.user_data["items"]:
            state.user_data["items"][key] = "completed"
        storage.save(state)
        fresh = TutorSession(storage)
        summary = fresh.progress()
        self.assertEqual(summary.status_badge, "completed")
        self.assertEqual(summary.percentage, 100)
        self.assertEqual(summary.completed_steps_count, 15)
        self.assertEqual(len(summary.completed_roles), 9)

    # ----------------------------------------------------------- navigation

    def test_navigation_options_only_on_current_assistant_turn(self):
        session, _, _ = self.make_session()
        self.drive_to_role_menu(session)
        turns = session.turns()

        intro_turn = next(t for t in turns if t.state == "roleplay_intro" and t.role == "assistant")
        # no navigation options on earlier assistant turns
        self.assertNotIn("finish", intro_turn.options)
        self.assertNotIn("retry", intro_turn.options)
        self.assertNotIn("next", intro_turn.options)
        # scenario options from that state are preserved
        self.assertEqual(intro_turn.options, {"continue": "View Available Roles", "back": "Back to Main Menu"})

        current = turns[-1]
        self.assertEqual(current.state, "role_menu")
        self.assertIn("finish", current.options)
        self.assertEqual(current.options["finish"], "Finish roles")
        # scenario label wins on the clash
        self.assertEqual(current.options["back"], "Back to Role-Play Intro")
        self.assertIn("1", current.options)

    def test_advance_option_matches_current_state(self):
        paths = {
            "analysis_intro_intermediate": ["Alice", "3 4 5", "2", "1"],
            "analysis_feedback_1_intermediate": ["Alice", "3 4 5", "2", "1", "yes", "Answer one"],
            "roleplay_intro": ["Alice", "3 4 5", "2", "1", "yes", "A1", "next", "A2", "next"],
            "roleplay_feedback_mediator": ["Alice", "3 4 5", "2", "1", "yes", "A1", "next", "A2",
                                          "next", "continue", "1", "I mediate"],
            "data_collection": ["Alice", "3 4 5", "2", "1", "yes", "A1", "next", "A2", "next",
                                "continue", "1", "I mediate", "next", "finish",
                                "Reflections", "4 4 4"],
        }
        keys = {
            "analysis_intro_intermediate": "yes",
            "analysis_feedback_1_intermediate": "next",
            "roleplay_intro": "continue",
            "roleplay_feedback_mediator": "next",
            "data_collection": "exit",
        }
        for target, path in paths.items():
            with self.subTest(target=target):
                session, storage, _ = self.make_session()
                self.drive(session, *path)
                self.assertEqual(self.state_of(storage).current_state, target)
                options = session.turns()[-1].options
                self.assertIn(keys[target], options, f"missing {keys[target]!r} on {target}")

    # ----------------------------------------------------------------- back

    def test_back_from_roleplay_feedback_returns_to_menu_without_completing(self):
        session, storage, _ = self.make_session()
        self.drive_to_role_menu(session)
        self.drive(session, "1", "I mediate")
        self.assertEqual(self.state_of(storage).current_state, "roleplay_feedback_mediator")
        # the role is in_progress at feedback (completes only on "next")
        self.assertEqual(session.progress().completed_roles, [])
        session.submit("back")
        self.assertEqual(self.state_of(storage).current_state, "role_menu")
        # "back" is intercepted by the global handler before routing, so the
        # role stays in_progress (old-app parity)
        self.assertEqual(session.progress().completed_roles, [])

    def test_back_from_analysis_task_returns_to_analysis_intro(self):
        session, storage, _ = self.make_session()
        self.drive(session, "Alice", "3 4 5", "2", "1", "yes")
        self.assertEqual(self.state_of(storage).current_state, "analysis_task_1_intermediate")
        session.submit("back")
        self.assertEqual(self.state_of(storage).current_state, "analysis_intro_intermediate")

    def test_back_from_role_menu_returns_to_roleplay_intro(self):
        session, storage, _ = self.make_session()
        self.drive_to_role_menu(session)
        session.submit("back")
        self.assertEqual(self.state_of(storage).current_state, "roleplay_intro")

    def test_back_from_pretest_lands_in_a_valid_state(self):
        session, storage, _ = self.make_session()
        session.submit("Alice")
        self.assertEqual(self.state_of(storage).current_state, "pretest")
        session.submit("back")
        self.assertEqual(self.state_of(storage).current_state, "after_registration_beginner")

    def test_back_at_start_is_unrecognized_input(self):
        session, storage, _ = self.make_session()
        turns_before = len(session.turns())
        session.submit("back")
        turns = session.turns()
        # Accepted delta (ticket #9): typed "back" at start is an
        # unrecognized input — the user turn is recorded, no assistant
        # re-prompt is appended, and the state stays at start.
        self.assertEqual(len(turns), turns_before + 1)
        self.assertEqual(turns[-1].role, "user")
        self.assertEqual(self.state_of(storage).current_state, "start")

    # --------------------------------------------------------------- retry

    def test_retry_flow_updates_last_assistant_turn_in_place(self):
        llm = FakeLLM(fail_times=4, text="LLM-OUT")
        session, storage, _ = self.make_session(llm=llm)
        self.drive_to_role_menu(session)
        self.drive(session, "1", "I mediate")

        current = session.turns()[-1]
        self.assertEqual(current.state, "roleplay_feedback_mediator")
        self.assertEqual(current.options["retry"], "🔄 Retry LLM (1/3)")

        user_count_before = sum(1 for t in session.turns() if t.role == "user")
        session.submit("retry")
        # no user turn appended for retry
        self.assertEqual(sum(1 for t in session.turns() if t.role == "user"), user_count_before)
        self.assertEqual(session.turns()[-1].options["retry"], "🔄 Retry LLM (1/3)")

        session.submit("retry")
        current = session.turns()[-1]
        self.assertNotIn("retry", current.options)
        self.assertIn("next", current.options)
        self.assertIn("LLM-OUT", current.message)

    def test_retry_is_ignored_outside_feedback_states(self):
        session, storage, _ = self.make_session()
        self.drive_to_role_menu(session)
        session.submit("retry")
        self.assertEqual(self.state_of(storage).current_state, "role_menu")
        self.assertEqual(session.turns()[-1].role, "user")

    # ------------------------------------------- cutover navigation matrix
    # Issue #4: the chat view and template no longer compute navigation from
    # ``current_state``. The module's ``Turn.options`` on the current assistant
    # turn is the single source of truth, so the old rendered-HTML navigation
    # tests (deleted from ``tests.py``) are carried over here as structured
    # assertions against exact option dicts — in-memory adapter + fake LLM.

    def test_cutover_navigation_matrix(self):
        # state -> (drive path from start, expected exact options dict)
        matrix = {
            "start": (
                [],
                {},  # welcome turn: no navigation (nothing to go back to)
            ),
            "level_assessment": (
                ["Alice", "3 4 5"],
                {
                    "back": "⬅️ Back",
                    "1": "Beginner",
                    "2": "Intermediate",
                    "3": "Advanced",
                },
            ),
            "after_registration_intermediate": (
                ["Alice", "3 4 5", "2"],
                {
                    "back": "⬅️ Back",
                    "1": "Step1️⃣: ANALYSIS",
                    "2": "Step2️⃣: ROLE-PLAY",
                },
            ),
            "analysis_intro_intermediate": (
                ["Alice", "3 4 5", "2", "1"],
                {"back": "Back to menu", "yes": "Yes, proceed"},
            ),
            # Non-nav states: only the always-available back button.
            "analysis_task_1_intermediate": (
                ["Alice", "3 4 5", "2", "1", "yes"],
                {"back": "⬅️ Back"},
            ),
            "role_mediator": (
                ["Alice", "3 4 5", "2", "1", "yes", "Answer one", "next",
                 "Answer two", "next", "continue", "1"],
                {"back": "⬅️ Back"},
            ),
            "roleplay_intro": (
                ["Alice", "3 4 5", "2", "1", "yes", "Answer one", "next",
                 "Answer two", "next"],
                {"continue": "View Available Roles", "back": "Back to Main Menu"},
            ),
            "role_menu": (
                ["Alice", "3 4 5", "2", "1", "yes", "Answer one", "next",
                 "Answer two", "next", "continue"],
                {
                    "back": "Back to Role-Play Intro",
                    "1": "Mediator", "2": "Logical Expert", "3": "Idea Generator",
                    "4": "Researcher", "5": "Interpreter", "6": "Advocate",
                    "7": "Judge", "8": "Peacemaker", "9": "Empath",
                    "finish": "Finish roles",
                },
            ),
            # data_collection: the scenario's exit label matches the nav label.
            "data_collection": (
                ["Alice", "3 4 5", "2", "1", "yes", "Answer one", "next",
                 "Answer two", "next", "continue", "1", "I mediate", "next",
                 "finish", "A long reflection", "4 4 4"],
                {"back": "⬅️ Back", "exit": "Exit"},
            ),
        }
        for state, (path, expected) in matrix.items():
            with self.subTest(state=state):
                session, storage, _ = self.make_session()
                self.drive(session, *path)
                self.assertEqual(self.state_of(storage).current_state, state)
                current = session.turns()[-1]
                self.assertEqual(current.role, "assistant")
                self.assertEqual(current.options, expected)

    def test_cutover_feedback_llm_success_options(self):
        session, _, _ = self.make_session()
        self.drive(session, "Alice", "3 4 5", "2", "1", "yes", "Answer one")
        current = session.turns()[-1]
        self.assertEqual(current.options, {"back": "Back to menu", "next": "Next Task"})

    def test_cutover_feedback_llm_failure_options(self):
        session, _, _ = self.make_session(llm=FakeLLM(fail_times=1))
        self.drive(session, "Alice", "3 4 5", "2", "1", "yes", "Answer one")
        current = session.turns()[-1]
        # retry replaces the advance option; the scenario's next survives the merge.
        self.assertEqual(
            current.options,
            {"back": "Back to menu", "retry": "🔄 Retry LLM (1/3)", "next": "Next Task"},
        )

    def test_cutover_roleplay_feedback_llm_failure_options(self):
        session, _, _ = self.make_session(llm=FakeLLM(fail_times=3))
        self.drive(session, "Alice", "3 4 5", "2", "1", "yes", "Answer one", "next",
                   "Answer two", "next", "continue", "1", "I mediate")
        current = session.turns()[-1]
        # roleplay_feedback_* states carry no scenario options, so the
        # llm_failed merge yields nav-only buttons (no scenario 'next' to keep).
        self.assertEqual(
            current.options,
            {"back": "⬅️ Back", "retry": "🔄 Retry LLM (1/3)"},
        )

    def test_cutover_end_turn_has_no_options(self):
        session, _, _ = self.make_session()
        self.drive(session, "Alice", "3 4 5", "2", "1", "yes", "Answer one", "next",
                   "Answer two", "next", "continue", "1", "I mediate", "next",
                   "finish", "A long reflection", "4 4 4", "exit")
        last = session.turns()[-1]
        self.assertEqual(last.role, "user")
        self.assertEqual(last.message, "exit")
        self.assertIsNone(last.options)

    # ------------------------------------------------------------ LLM wiring

    def test_feedback_called_with_feedback_state_context(self):
        llm = FakeLLM()
        session, _, _ = self.make_session(llm=llm)
        self.drive_to_role_menu(session)
        baseline = len(llm.calls)  # analysis feedback states already called it
        self.drive(session, "1", "I mediate")

        self.assertEqual(len(llm.calls), baseline + 1)
        user_answer, role_name, user_name, level, task_question = llm.calls[-1]
        self.assertEqual(user_answer, "I mediate")
        self.assertEqual(role_name, "mediator")
        self.assertEqual(user_name, "Alice")
        self.assertEqual(level, "intermediate")
        self.assertIn("ROLE: Mediator", task_question or "")

    def test_feedback_not_called_outside_feedback_states(self):
        llm = FakeLLM()
        session, _, _ = self.make_session(llm=llm)
        self.drive(session, "Alice", "3 4 5", "2", "1")
        self.assertEqual(llm.calls, [])

    # ---------------------------------------------------------- bad inputs

    def test_invalid_pretest_scores_keep_state(self):
        session, storage, _ = self.make_session()
        session.submit("Alice")
        session.submit("not numbers")
        self.assertEqual(self.state_of(storage).current_state, "pretest")
        self.assertEqual(session.turns()[-1].role, "user")

    def test_invalid_level_choice_keeps_state(self):
        session, storage, _ = self.make_session()
        self.drive(session, "Alice", "3 4 5")
        session.submit("4")
        self.assertEqual(self.state_of(storage).current_state, "level_assessment")

    def test_analysis_intro_ignores_anything_but_yes(self):
        session, storage, _ = self.make_session()
        self.drive(session, "Alice", "3 4 5", "2", "1")
        turns_before = len(session.turns())
        session.submit("no")
        self.assertEqual(self.state_of(storage).current_state, "analysis_intro_intermediate")
        self.assertEqual(len(session.turns()), turns_before + 1)  # only the user turn

    def test_role_menu_rejects_non_roles(self):
        session, storage, _ = self.make_session()
        self.drive_to_role_menu(session)
        for junk in ("0", "10", "abc"):
            with self.subTest(junk=junk):
                session.submit(junk)
                self.assertEqual(self.state_of(storage).current_state, "role_menu")

    # ------------------------------------------------- canonical completion

    def test_current_step_tracks_current_state(self):
        session, storage, _ = self.make_session()
        self.drive(session, "Alice", "3 4 5", "2", "1")
        self.assertEqual(session.progress().current_step, 3)  # analysis_task_1
        self.drive(session, "yes", "Answer")
        self.assertEqual(session.progress().current_step, 3)  # feedback_1 same item
        self.drive(session, "next", "Answer two", "next", "continue")
        self.assertEqual(session.progress().current_step, 0)   # role_menu has no item

    def test_user_turns_carry_no_options(self):
        session, _, _ = self.make_session()
        self.drive(session, "Alice", "3 4 5")
        user_turns = [t for t in session.turns() if t.role == "user"]
        self.assertEqual(len(user_turns), 2)
        for turn in user_turns:
            self.assertIsNone(turn.options)

    def test_start_is_idempotent(self):
        session, storage, _ = self.make_session()
        self.drive(session, "Alice", "3 4 5")

        before = self.state_of(storage)
        turns_before = session.turns()

        again = session.start()

        self.assertEqual(again.state, before.current_state)
        self.assertEqual(
            [(t.role, t.message) for t in session.turns()],
            [(t.role, t.message) for t in turns_before],
        )
        self.assertEqual(self.state_of(storage).current_state, before.current_state)

    def test_saved_state_preserves_items_model(self):
        session, storage, _ = self.make_session()
        self.drive_to_role_menu(session)
        self.drive(session, "1", "I mediate", "next")

        items = self.state_of(storage).user_data["items"]
        self.assertEqual(items["analysis_task_1"], "completed")
        self.assertEqual(items["analysis_task_2"], "completed")
        self.assertEqual(items["role_mediator"], "completed")
        self.assertEqual(items["mode_analysis"], "completed")

        reloaded = TutorSession(storage)
        self.assertEqual(reloaded.progress().completed_roles, ["role_mediator"])
        self.assertEqual(reloaded.progress().percentage, 33)  # 5 of 15 steps

    def test_legacy_state_migrates_to_items_model(self):
        storage = MemoryStorage()
        legacy = State(
            session_id="legacy",
            current_state="role_mediator",
            user_data={
                "user_name": "Alice",
                "level": "intermediate",
                "pretest_scores": [3, 4, 5],
                "posttest_scores": None,
                "current_role": "role_mediator",
                "current_role_variant": None,
                "completed_steps": ["pretest", "level_assessment", "analysis_task_1", "analysis_task_2"],
                "completed_roles": [],
                "completed_modes": ["analysis", "roleplay"],
                "opened_tasks": ["role_mediator"],
                "completed_tasks": ["analysis_task_1_intermediate", "analysis_task_2_intermediate"],
            },
            scenario=randomize_scenario(SCENARIO),
            chat_history=[],
        )
        storage.save(legacy)

        session = TutorSession(storage)
        summary = session.progress()
        self.assertEqual(summary.percentage, 26)  # 4 of 15 step items (modes excluded)
        self.assertEqual(summary.completed_modes, ["analysis", "roleplay"])
        self.assertEqual(summary.completed_roles, [])
        self.assertEqual(summary.opened_tasks, ["role_mediator"])

        # the migration persists on the next save; continue from the migrated state
        session.submit("I mediate")
        saved = self.state_of(storage)
        # the role answer does not complete the role (only feedback "next" does)
        self.assertEqual(saved.user_data["items"]["role_mediator"], "in_progress")
        self.assertEqual(saved.current_state, "roleplay_feedback_mediator")

    def test_stored_legacy_idea_feedback_key_keeps_working(self):
        """Issue #12: a session stored at the retired key is normalized on load.

        At the retired key there is no transition row and no scenario state, so
        every input is rejected and the learner is stranded on a stale turn;
        the key rewrite keeps the session routable instead.
        """
        session, storage, _ = self.make_session()
        self.drive_to_role_menu(session)
        self.drive(session, "3", "Two ideas, **bold** and 💡")

        state = self.state_of(storage)
        state.current_state = "roleplay_feedback_idea"  # what a live session stored
        storage.save(state)

        fresh = TutorSession(storage)
        self.assertEqual(fresh.turns()[-1].role, "assistant")
        turn = fresh.submit("next")
        self.assertEqual(self.state_of(storage).current_state, "role_menu")
        self.assertEqual(turn.role, "assistant")
        self.assertEqual(fresh.progress().completed_roles, ["role_idea_generator"])
