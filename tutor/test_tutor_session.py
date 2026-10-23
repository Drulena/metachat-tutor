"""Behavioral tests for :class:`tutor.tutor_session.TutorSession` (ticket #3).

Runs against :class:`~tutor.session.MemoryStorage` and a deterministic
fake LLM — no network, no Django session, no view code.
"""

from dataclasses import fields

from django.test import SimpleTestCase

from .data import (
    ANALYSIS_LABELS,
    ANALYSIS_STEP_KEYS,
    ROLE_BY_VALUE,
    ROLE_LABELS,
    ROLE_STEP_KEYS,
    STEP_KEYS,
)
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


def row_statuses(summary: Summary) -> dict[str, str]:
    """The ``{key: status}`` map of every section row in a Summary."""
    return {row.key: row.status for section in summary.sections for row in section.rows}


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
        self.assertEqual(summary.percentage, 0)
        self.assertEqual(summary.total_steps, 15)
        self.assertEqual(summary.completed_steps_count, 0)
        self.assertEqual(summary.completed_option_values, [])
        self.assertFalse(summary.finished)
        self.assertIsNone(summary.level)
        self.assertIsNone(summary.user_name)
        self.assertTrue(summary.session_id)
        self.assertTrue(summary.started)  # a started session always has an id
        self.assertTrue(summary.started)
        self.assertEqual(set(row_statuses(summary).values()), {"not_started"})

    def test_summary_task_rows_carry_their_own_status(self):
        """Every task row answers the status question from the completion model.

        A learner part-way through the analysis tasks has one task completed and
        the next in progress. Each row of the Summary's ``sections`` carries that
        item's own status (GLOSSARY "completion model": ``not_started`` /
        ``in_progress`` / ``completed``), so a page renders a badge straight from
        the row and never infers status from a completed count. Row keys are the
        completion-model item keys; the module supplies the heading wording and
        the group order.
        """
        session, _, _ = self.make_session()
        self.drive(
            session,
            "Alice", "3 4 5", "2", "1", "yes",
            "Answer to task one",  # -> analysis_feedback_1_intermediate: task 1 completed
            "next",                # -> analysis_task_2_intermediate: task 2 in progress
        )
        sections = session.progress().sections

        self.assertEqual(sections[0].title, "📝 Analysis Tasks")
        self.assertEqual(
            [(row.key, row.status) for row in sections[0].rows],
            [
                ("analysis_task_1", "completed"),
                ("analysis_task_2", "in_progress"),
            ],
        )
        self.assertEqual((sections[0].completed, sections[0].total), (1, 2))

        self.assertEqual(sections[1].title, "🎭 Communication Roles")
        self.assertEqual([row.status for row in sections[1].rows], ["not_started"] * 9)
        self.assertEqual((sections[1].completed, sections[1].total), (0, 9))
        self.assertEqual(sections[1].rows[0].key, "role_mediator")

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

    def test_summary_exposes_every_field(self):
        """The interface guard: the Summary carries exactly these fields.

        Issue #14 put ``sections`` first — the progress panel whose rows each
        answer the status question — and dropped the flat completion lists no
        page reads. A page that needs a row's status reads the row; the overall
        counters, the answered-option markers, the identity fields and the one
        yes/no question ("is this session finished?") are all the interface is.
        """
        session, _, _ = self.make_session()
        summary = session.progress()
        names = [f.name for f in fields(Summary)]
        self.assertEqual(
            names,
            [
                "sections", "started", "percentage", "total_steps",
                "completed_steps_count", "completed_option_values", "finished",
                "level", "user_name", "session_id",
            ],
        )
        self.assertEqual(
            [(s.title, [(row.key, row.label) for row in s.rows]) for s in summary.sections],
            [
                ("📝 Analysis Tasks", [(k, ANALYSIS_LABELS[k]) for k in ANALYSIS_STEP_KEYS]),
                ("🎭 Communication Roles", [(k, ROLE_LABELS[k]) for k in ROLE_STEP_KEYS]),
            ],
        )

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
        # progress() is exempt: it answers the zero-state instead of raising.

    def test_progress_on_untouched_session_is_zero_state(self):
        """An untouched session answers: nothing started, nothing finished."""
        session, _, _ = self.make_session(started=False)
        summary = session.progress()
        self.assertFalse(summary.started)
        self.assertEqual(summary.session_id, "")
        self.assertIsNone(summary.user_name)
        self.assertIsNone(summary.level)
        self.assertEqual(summary.completed_steps_count, 0)
        self.assertEqual(summary.percentage, 0)
        self.assertFalse(summary.finished)
        self.assertEqual(
            [section.completed for section in summary.sections], [0, 0]
        )
        self.assertEqual(set(row_statuses(summary).values()), {"not_started"})

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
        self.assertEqual(summary.percentage, 46)  # 7 of 15 items
        self.assertTrue(summary.finished)
        statuses = row_statuses(summary)
        self.assertEqual(statuses["analysis_task_1"], "completed")
        self.assertEqual(statuses["analysis_task_2"], "completed")
        self.assertEqual(statuses["role_mediator"], "completed")
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
        self.assertEqual(row_statuses(session.progress())["role_idea_generator"], "in_progress")
        self.drive(session, "next")
        self.assertEqual(row_statuses(session.progress())["role_idea_generator"], "completed")

    def test_all_items_completed_gives_full_summary(self):
        session, storage, _ = self.make_session()
        state = self.state_of(storage)
        for key in state.user_data["items"]:
            state.user_data["items"][key] = "completed"
        storage.save(state)
        fresh = TutorSession(storage)
        summary = fresh.progress()
        # `finished` is the lifecycle question, not this one — it lives in
        # test_full_single_role_path_reaches_end.
        self.assertEqual(summary.percentage, 100)
        self.assertEqual(summary.completed_steps_count, 15)
        self.assertEqual(set(row_statuses(summary).values()), {"completed"})

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

    def test_every_roleplay_feedback_turn_offers_revise(self):
        """Issue #13: every role-play feedback turn offers revise/next/back.

        The machine routes 'revise' in all nine feedback states (re-entering
        the current role, left in progress), but the option was offered on the
        Empath feedback turn only — the other eight accepted it typed-only.
        """
        for value, item in sorted(ROLE_BY_VALUE.items()):
            role = item[len("role_"):]
            with self.subTest(role=role):
                session, storage, _ = self.make_session()
                self.drive_to_role_menu(session)
                self.drive(session, value, "A constructive answer")
                self.assertEqual(
                    self.state_of(storage).current_state, f"roleplay_feedback_{role}"
                )
                # the offer matches the routed commands: revise, next, back
                self.assertEqual(
                    session.turns()[-1].options,
                    {
                        "revise": "✏️ Revise",
                        "next": "➡️ Next Role",
                        "back": "⬅️ Back to Menu",
                    },
                )
                # the button is not decorative: revise re-enters the role in progress
                session.submit("revise")
                self.assertEqual(self.state_of(storage).current_state, item)
                self.assertEqual(row_statuses(session.progress())[item], "in_progress")

    # ----------------------------------------------------------------- back

    def test_back_from_roleplay_feedback_returns_to_menu_without_completing(self):
        session, storage, _ = self.make_session()
        self.drive_to_role_menu(session)
        self.drive(session, "1", "I mediate")
        self.assertEqual(self.state_of(storage).current_state, "roleplay_feedback_mediator")
        # the role is in_progress at feedback (completes only on "next")
        self.assertEqual(row_statuses(session.progress())["role_mediator"], "in_progress")
        session.submit("back")
        self.assertEqual(self.state_of(storage).current_state, "role_menu")
        # "back" is intercepted by the global handler before routing, so the
        # role stays in_progress (old-app parity)
        self.assertEqual(row_statuses(session.progress())["role_mediator"], "in_progress")

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
            # Issue #13: a role-play feedback turn offers the full trio the
            # machine routes — revise re-enters the role, next the role menu.
            "roleplay_feedback_mediator": (
                ["Alice", "3 4 5", "2", "1", "yes", "Answer one", "next",
                 "Answer two", "next", "continue", "1", "I mediate"],
                {
                    "revise": "✏️ Revise",
                    "next": "➡️ Next Role",
                    "back": "⬅️ Back to Menu",
                },
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
        # Issue #13: the feedback states now carry scenario options, so the
        # llm_failed merge keeps them (retry added, the scenario's back label
        # winning the clash with the always-available navigation back).
        self.assertEqual(
            current.options,
            {
                "revise": "✏️ Revise",
                "next": "➡️ Next Role",
                "back": "⬅️ Back to Menu",
                "retry": "🔄 Retry LLM (1/3)",
            },
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

    def test_rows_track_the_task_the_learner_is_on(self):
        session, storage, _ = self.make_session()
        self.drive(session, "Alice", "3 4 5", "2", "1", "yes")
        self.assertEqual(
            row_statuses(session.progress())["analysis_task_1"], "in_progress"
        )
        self.drive(session, "Answer")
        self.assertEqual(
            row_statuses(session.progress())["analysis_task_1"], "completed"
        )
        self.drive(session, "next", "Answer two", "next", "continue")
        statuses = row_statuses(session.progress())
        self.assertEqual(statuses["analysis_task_1"], "completed")
        self.assertEqual(statuses["analysis_task_2"], "completed")

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
        self.assertEqual(row_statuses(reloaded.progress())["role_mediator"], "completed")
        self.assertEqual(reloaded.progress().percentage, 33)  # 5 of 15 steps
