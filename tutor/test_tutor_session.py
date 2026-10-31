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
from .transitions import (
    ROW_REGISTRY,
    after_registration,
    analysis_feedback_1,
    analysis_feedback_2,
    analysis_intro,
    analysis_task_1,
    analysis_task_2,
    row_for,
)
from .tutor_session import TutorSession

#: Input sequence that drives a fresh session to the role menu.
#: Shared with :mod:`tutor.test_views` so the two test modules cannot drift.
ROLE_MENU_INPUTS = [
    "Alice",            # start -> pretest
    "3 4 5",            # pretest -> level_assessment
    "2",                # level_assessment -> after_registration (base name, C1-2)
    "1",                # -> analysis_intro (base name, C1-3)
    "yes",              # -> analysis_task_1 (base name, C1-4)
    "Answer to task one",   # -> analysis_feedback_1 (base name, C1-5)
    "next",             # -> analysis_task_2 (base name, C1-6)
    "Answer to task two",   # -> analysis_feedback_2 (base name, C1-7)
    "next",             # -> roleplay_intro
    "continue",         # -> role_menu
]

#: (level, registration digit) pairs covering the whole level axis
#: (ADR-0006); mirrors the ``level_assessment`` row's value -> state map.
LEVEL_DIGITS = [("beginner", "1"), ("intermediate", "2"), ("advanced", "3")]


def row_statuses(summary: Summary) -> dict[str, str]:
    """The ``{key: status}`` map of every section row in a Summary."""
    return {row.key: row.status for section in summary.sections for row in section.rows}


def offers(turn) -> dict:
    """Flat ``{value: (label, kind)}`` map over a turn's typed options (#15)."""
    return {opt.value: (opt.label, opt.kind) for opt in (turn.options or [])}


#: The module's generic rejection copy (``tutor_session._GENERIC_REJECTION``).
#: Shared with :mod:`tutor.test_options` / :mod:`tutor.test_views`: every
#: pinning of the copy lives here, once (code-review #15, duplication).
GENERIC_REJECTION = (
    "That answer is not recognized: choose one of the offered options, type "
    "'back', 'finish', 'restart' (to erase and start over), 'export' (to "
    "download the transcript), 'help' (for a summary of the rules), 'idea' "
    "(to generate an idea for the assignments, when the task asks for one), "
    "or 'next' (to advance one page). In data collection, type 'name <your "
    "name>'. The task's own options are shown beneath the question."
)

#: The role-menu row's bespoke rejection copy (rows/role_menu.py).
ROLE_MENU_COPY = "Choose one of the numbered roles, finish, or back."

#: The registration row's own rejection copy (transitions/after_registration.py),
#: worded away from the back invitation now that registration is the point of
#: no return (spec #16 C1-8). Shared with :mod:`tutor.test_views`.
REGISTRATION_REJECTION = "Choose the level to continue with."

#: The two options the registration scenario offers
#: (scenarios/after_registration.py). Shared with :mod:`tutor.test_views`:
#: every pinning of these labels lives here, once.
REGISTRATION_OPTIONS = {"1": "Step1️⃣: ANALYSIS", "2": "Step2️⃣: ROLE-PLAY"}


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
            "Answer to task one",  # -> analysis_feedback_1 (base name, C1-5): task 1 completed
            "next",                # -> analysis_task_2 (base name, C1-6): task 2 in progress
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

    def test_in_progress_task_leaves_later_rows_not_started(self):
        """The reported state, at the module seam: task 1 in progress.

        The analysis intro row marks task 1 ``in_progress`` on entering it;
        the task the learner never opened stays ``not_started``. The status
        is the row's own, so no page can stamp the second task Completed from
        a completed count (issue #14, GLOSSARY "completion model").
        """
        session, _, _ = self.make_session()
        self.drive(session, "Alice", "3 4 5", "2", "1", "yes")
        self.assertEqual(
            [(row.key, row.status) for row in session.progress().sections[0].rows],
            [("analysis_task_1", "in_progress"), ("analysis_task_2", "not_started")],
        )

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
                "completed_steps_count", "finished",
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

    def test_all_registered_levels_traverse_the_graph_through_submit(self):
        """#17 anchor: each registered level walks the graph end to end.

        Drives every level path through :meth:`TutorSession.submit` one
        input at a time and asserts the row reached after each step.
        Committed green before the row-registry expand (#17) and kept as
        the safety net for the base-name cutover (spec #16 C1-9): the
        sequence of reached rows must not change. Registration lands on
        the base name (spec #16 C1-2), so that step asserts the row the
        pair registry resolves with the level — the row reached before
        the cutover, by identity.
        """
        #: Per-level rows of the six axis modules (spec #16 C1-2..C1-7):
        #: the module-level maps the pair assembly is built FROM. They
        #: spell no suffixed name — the level is a key, not a suffix —
        #: so this is the independent oracle for the row landed on.
        axis_rows = {
            "after_registration": after_registration.ROWS,
            "analysis_intro": analysis_intro.ROWS,
            "analysis_task_1": analysis_task_1.ROWS,
            "analysis_feedback_1": analysis_feedback_1.ROWS,
            "analysis_task_2": analysis_task_2.ROWS,
            "analysis_feedback_2": analysis_feedback_2.ROWS,
        }
        tail = [
            "1",                    # -> role_mediator
            "I mediate the conflict",  # -> roleplay_feedback_mediator
            "next",                 # -> role_menu (mediator completed)
            "finish",               # -> reflection
            "A long reflection",    # -> posttest
            "4 4 4",                # -> data_collection
            "exit",                 # -> end
        ]
        for level, digit in LEVEL_DIGITS:
            inputs = ROLE_MENU_INPUTS[:2] + [digit] + ROLE_MENU_INPUTS[3:] + tail
            expected = [
                "pretest",
                "level_assessment",
                "after_registration",  # base name lands (spec #16 C1-2)
                "analysis_intro",       # base name lands (spec #16 C1-3)
                "analysis_task_1",        # base name lands (spec #16 C1-4)
                "analysis_feedback_1",    # base name lands (spec #16 C1-5)
                "analysis_task_2",        # base name lands (spec #16 C1-6)
                "analysis_feedback_2",    # base name lands (spec #16 C1-7)
                "roleplay_intro",
                "role_menu",
                "role_mediator",
                "roleplay_feedback_mediator",
                "role_menu",
                "reflection",
                "posttest",
                "data_collection",
                "end",
            ]
            self.assertEqual(len(inputs), len(expected))
            with self.subTest(level=level):
                session, storage, _ = self.make_session()
                for step, (text, reached) in enumerate(zip(inputs, expected), 1):
                    with self.subTest(step=step, input=text):
                        session.submit(text)
                        self.assertEqual(
                            self.state_of(storage).current_state, reached
                        )
                        if reached in axis_rows:
                            # "Asserting the row reached" is the row
                            # the suffixed flat-table name resolved to
                            # before the cutover. The seam must land on
                            # that same row, and that row's fixture
                            # must carry this level — checking row_for
                            # against its own registry would be true by
                            # construction, so the axis module's level
                            # map is the oracle here (C1-9: no suffixed
                            # spelling is spelled to look it up).
                            landed = row_for(reached, level)
                            self.assertIs(landed, axis_rows[reached][level])
                            self.assertIs(
                                landed,
                                ROW_REGISTRY[(reached, level)],
                            )
                            self.assertEqual(
                                landed["fixture"]["user_data"]["level"], level
                            )

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
        intro = offers(intro_turn)
        self.assertNotIn("finish", intro)
        self.assertNotIn("retry", intro)
        self.assertNotIn("next", intro)
        # scenario options from that state are preserved; the row's nav
        # map covers "continue" and the row declares "back", so routing
        # treats them as navigation on EVERY rendered turn (ADR-0005 d2 —
        # kind is tested against the row at render time, history included)
        self.assertEqual(
            intro,
            {"continue": ("View Available Roles", "nav"), "back": ("Back to Main Menu", "nav")},
        )

        current = turns[-1]
        self.assertEqual(current.state, "role_menu")
        current_offers = offers(current)
        self.assertIn("finish", current_offers)
        self.assertEqual(current_offers["finish"], ("Finish roles", "nav"))
        # scenario label wins on the clash; kind follows the routing origin
        self.assertEqual(current_offers["back"], ("Back to Role-Play Intro", "nav"))
        self.assertEqual(offers(current)["1"][1], "choice")

    def test_advance_option_matches_current_state(self):
        paths = {
            "analysis_intro": ["Alice", "3 4 5", "2", "1"],
            "analysis_feedback_1": ["Alice", "3 4 5", "2", "1", "yes", "Answer one"],
            "roleplay_intro": ["Alice", "3 4 5", "2", "1", "yes", "A1", "next", "A2", "next"],
            "roleplay_feedback_mediator": ["Alice", "3 4 5", "2", "1", "yes", "A1", "next", "A2",
                                          "next", "continue", "1", "I mediate"],
            "data_collection": ["Alice", "3 4 5", "2", "1", "yes", "A1", "next", "A2", "next",
                                "continue", "1", "I mediate", "next", "finish",
                                "Reflections", "4 4 4"],
        }
        keys = {
            "analysis_intro": "yes",
            "analysis_feedback_1": "next",
            "roleplay_intro": "continue",
            "roleplay_feedback_mediator": "next",
            "data_collection": "exit",
        }
        for target, path in paths.items():
            with self.subTest(target=target):
                session, storage, _ = self.make_session()
                self.drive(session, *path)
                self.assertEqual(self.state_of(storage).current_state, target)
                options = {opt.value for opt in session.turns()[-1].options}
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
                # the offer matches the routed commands: revise, next, back.
                # next is the row's nav edge (advance), back synthesised —
                # kind "nav"; revise is scenario-declared (not in the nav
                # map) — kind "choice"
                self.assertEqual(
                    offers(session.turns()[-1]),
                    {
                        "revise": ("✏️ Revise", "choice"),
                        "next": ("➡️ Next Role", "nav"),
                        "back": ("⬅️ Back to Menu", "nav"),
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
        self.assertEqual(self.state_of(storage).current_state, "analysis_task_1")
        session.submit("back")
        self.assertEqual(self.state_of(storage).current_state, "analysis_intro")

    def test_back_from_role_menu_returns_to_roleplay_intro(self):
        session, storage, _ = self.make_session()
        self.drive_to_role_menu(session)
        session.submit("back")
        self.assertEqual(self.state_of(storage).current_state, "roleplay_intro")

    def test_back_from_pretest_lands_on_the_name_and_group_screen(self):
        """Ticket #24: back at pretest goes to its TRUE predecessor — the
        name-and-group data-collection screen (``start``) — not a
        registration screen of a level the learner never picked (the
        silent-beginner-path hole closed, ADR-0006)."""
        session, storage, _ = self.make_session()
        session.submit("Alice")
        self.assertEqual(self.state_of(storage).current_state, "pretest")
        session.submit("back")
        self.assertEqual(self.state_of(storage).current_state, "start")

    def test_back_from_level_assessment_lands_on_pretest(self):
        """Ticket #24: the pre-registration chain points at true
        predecessors — level assessment backs to the pretest, so back
        never teleports past the point of no return."""
        session, storage, _ = self.make_session()
        self.drive(session, "Alice", "3 4 5")
        self.assertEqual(self.state_of(storage).current_state, "level_assessment")
        session.submit("back")
        self.assertEqual(self.state_of(storage).current_state, "pretest")

    def test_back_from_reflection_lands_on_the_registration_base_name(self):
        """Ticket #24: post-registration single-form rows spell the
        registration BASE name — the construction point resolves it with
        the session's level (the landing convention of spec #16 C1-2),
        so back at intermediate lands on the intermediate registration,
        not the beginner one."""
        session, storage, _ = self.make_session()
        self.drive_to_role_menu(session)
        self.drive(session, "1", "I mediate", "next", "finish")
        self.assertEqual(self.state_of(storage).current_state, "reflection")
        session.submit("back")
        self.assertEqual(self.state_of(storage).current_state, "after_registration")
        # the landing resolves with THIS session's level, not a literal
        self.assertIn("(Level: Intermediate)", session.turns()[-1].message)

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

    def test_back_at_registration_is_unrecognized_input(self):
        """Ticket #24 (spec #16, ADR-0006 decision 2): registration is the
        point of no return — the registration row's ``back`` is None, so
        typed "back" there is an unrecognized input exactly like at start:
        the user turn is recorded, no assistant re-prompt is appended, and
        the state stays at registration.
        """
        session, storage, _ = self.make_session()
        self.drive(session, "Alice", "3 4 5", "2")
        self.assertEqual(self.state_of(storage).current_state, "after_registration")
        turns_before = len(session.turns())
        session.submit("back")
        turns = session.turns()
        self.assertEqual(len(turns), turns_before + 1)
        self.assertEqual(turns[-1].role, "user")
        # the registration row's own copy, no longer inviting "back"
        self.assertEqual(turns[-1].rejection, REGISTRATION_REJECTION)
        self.assertEqual(self.state_of(storage).current_state, "after_registration")

    def test_back_at_registration_offers_no_back_option(self):
        """Ticket #24: with ``back: None`` the navigation panel must not
        offer a back option the command line rejects — the offer follows
        the row, so registration offers only its two options."""
        session, _, _ = self.make_session()
        self.drive(session, "Alice", "3 4 5", "2")
        self.assertEqual(
            offers(session.turns()[-1]),
            {
                "1": (REGISTRATION_OPTIONS["1"], "choice"),
                "2": (REGISTRATION_OPTIONS["2"], "choice"),
            },
        )

    def test_rejection_pairs_the_row_copy_with_the_unanswered_user_turn(self):
        session, storage, _ = self.make_session()
        self.drive(session, *ROLE_MENU_INPUTS)
        session.submit("not a role")
        turns = session.turns()
        self.assertEqual(turns[-1].role, "user")
        self.assertEqual(turns[-1].message, "not a role")
        self.assertEqual(
            turns[-1].rejection,
            ROLE_MENU_COPY,
        )

    def test_rejection_is_none_when_the_answer_lands(self):
        session, storage, _ = self.make_session()
        self.drive(session, *ROLE_MENU_INPUTS)
        session.submit("1")
        self.assertTrue(all(turn.rejection is None for turn in session.turns()))

    def test_nav_row_rejection_falls_back_to_the_generic_copy(self):
        session, storage, _ = self.make_session()
        # analysis_feedback_2: closed accept (next/back), no bespoke copy
        self.drive(session, *ROLE_MENU_INPUTS[:8])
        session.submit("no such task")
        self.assertEqual(session.turns()[-1].rejection, GENERIC_REJECTION)

    def test_states_without_a_row_carry_no_copy(self):
        """A state with no transition row — the ``end`` after the completion,
        stored legacy data, an unknown string — carries no banner copy at
        all (the structural case, ADR-0005 d5). The generic fallback is only
        for rows that declare ``rejected: None`` — exercised by
        ``test_nav_row_rejection_falls_back_to_the_generic_copy`` (#15).

        ``start`` accepts any input (the welcome answers free text), so a
        dropped input never occurs there; ``end`` is pinned by
        ``test_end_state_pairs_no_rejection_copy``.
        """
        session, _, _ = self.make_session()
        turn = session.submit("gibberish")
        self.assertIsNotNone(turn)  # accepted: the welcome answers free text
        self.assertIsNone(session.turns()[-1].rejection)

    def test_end_state_pairs_no_rejection_copy(self):
        """After the completion the UI offers no composer, and the structural
        AC holds: at ``end`` a stray input carries no banner copy at all."""
        session, storage, _ = self.make_session()
        self.drive_to_role_menu(session)
        self.drive(
            session,
            "1", "I mediate the conflict", "next",
            "finish", "A long reflection", "4 4 4", "exit",
        )
        self.assertEqual(self.state_of(storage).current_state, "end")
        session.submit("gibberish")
        self.assertEqual(session.turns()[-1].role, "user")
        self.assertIsNone(session.turns()[-1].rejection)

    def test_submit_returns_the_paired_turn(self):
        """The Turn ``submit()`` hands back is the same object ``turns()``
        reports — rejection pairing lives in one place (code-review #15)."""
        session, _, _ = self.make_session()
        self.drive(session, *ROLE_MENU_INPUTS)
        returned = session.submit("not a role")
        self.assertEqual(returned, session.turns()[-1])
        self.assertEqual(returned.rejection, ROLE_MENU_COPY)

    def test_synthesised_back_marks_used_value(self):
        """``back`` is a synthesised edge, not a row-nav value — marking it
        keeps the newest-answer rule uniform for every offered option."""
        session, _, _ = self.make_session()
        self.drive(session, *ROLE_MENU_INPUTS)
        session.submit("back")
        turns = session.turns()
        # back appends no user turn — the OLD offer it answered is marked
        self.assertEqual(turns[-1].role, "assistant")
        self.assertEqual(turns[-2].used_value, "back")

    def test_retry_marks_used_value(self):
        """``retry`` is a synthesised edge on a failed-LLM turn: answering it
        marks that turn like every other offer."""
        llm = FakeLLM(fail_times=4, text="LLM-OUT")
        session, _, _ = self.make_session(llm=llm)
        self.drive_to_role_menu(session)
        self.drive(session, "1", "I mediate")
        self.assertIn("retry", offers(session.turns()[-1]))
        session.submit("retry")
        # retry appends no user turn — the failed turn is refreshed in place
        self.assertEqual(session.turns()[-1].used_value, "retry")

    # --------------------------------------------------------------- retry

    def test_retry_flow_updates_last_assistant_turn_in_place(self):
        llm = FakeLLM(fail_times=4, text="LLM-OUT")
        session, storage, _ = self.make_session(llm=llm)
        self.drive_to_role_menu(session)
        self.drive(session, "1", "I mediate")

        current = session.turns()[-1]
        self.assertEqual(current.state, "roleplay_feedback_mediator")
        self.assertEqual(offers(current)["retry"], ("🔄 Retry LLM (1/3)", "retry"))

        user_count_before = sum(1 for t in session.turns() if t.role == "user")
        session.submit("retry")
        # no user turn appended for retry
        self.assertEqual(sum(1 for t in session.turns() if t.role == "user"), user_count_before)
        self.assertEqual(offers(session.turns()[-1])["retry"], ("🔄 Retry LLM (1/3)", "retry"))

        session.submit("retry")
        current = session.turns()[-1]
        self.assertNotIn("retry", offers(current))
        self.assertIn("next", offers(current))
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
            "after_registration": (  # base name lands (spec #16 C1-2)  # no back offer: point of no return (C1-8)
                ["Alice", "3 4 5", "2"],
                {
                    "1": REGISTRATION_OPTIONS["1"],
                    "2": REGISTRATION_OPTIONS["2"],
                },
            ),
            "analysis_intro": (
                ["Alice", "3 4 5", "2", "1"],
                {"back": "Back to menu", "yes": "Yes, proceed"},
            ),
            # Non-nav states: only the always-available back button.
            "analysis_task_1": (  # base name lands (spec #16 C1-4)
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
                # The turn string carries the base name (spec #16 C1-9 AC2):
                # axis states landed suffixed before the cutover.
                self.assertEqual(current.state, state)
                self.assertEqual(current.role, "assistant")
                self.assertEqual(
                    {opt.value: opt.label for opt in current.options},
                    expected,
                )

    def test_cutover_feedback_llm_success_options(self):
        session, _, _ = self.make_session()
        self.drive(session, "Alice", "3 4 5", "2", "1", "yes", "Answer one")
        current = session.turns()[-1]
        self.assertEqual(
            offers(current),
            # at the llm-success feedback row "next" is in the row's nav map
            # (advance offer) — kind "nav"
            {"back": ("Back to menu", "nav"), "next": ("Next Task", "nav")},
        )

    def test_cutover_feedback_llm_failure_options(self):
        session, _, _ = self.make_session(llm=FakeLLM(fail_times=1))
        self.drive(session, "Alice", "3 4 5", "2", "1", "yes", "Answer one")
        current = session.turns()[-1]
        # retry replaces the advance option; the scenario's next survives the
        # merge. "retry" is the injected retry offer, "next" a scenario value
        # (not the row's nav map) — kinds retry / choice.
        self.assertEqual(
            offers(current),
            {
                "back": ("Back to menu", "nav"),
                "retry": ("🔄 Retry LLM (1/3)", "retry"),
                "next": ("Next Task", "choice"),
            },
        )

    def test_cutover_roleplay_feedback_llm_failure_options(self):
        session, _, _ = self.make_session(llm=FakeLLM(fail_times=3))
        self.drive(session, "Alice", "3 4 5", "2", "1", "yes", "Answer one", "next",
                   "Answer two", "next", "continue", "1", "I mediate")
        current = session.turns()[-1]
        # Issue #13: the feedback states now carry scenario options, so the
        # llm_failed merge keeps them (retry added, the scenario's back label
        # winning the clash with the always-available navigation back).
        # revise/next are scenario values — kind "choice".
        self.assertEqual(
            offers(current),
            {
                "revise": ("✏️ Revise", "choice"),
                "next": ("➡️ Next Role", "choice"),
                "back": ("⬅️ Back to Menu", "nav"),
                "retry": ("🔄 Retry LLM (1/3)", "retry"),
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

    def test_analysis_feedback_context_reaches_the_llm_at_the_base_name(self):
        """Spec #16 C1-5: the task context resolves at the base state name.

        The feedback row lands on the base state, so the task context
        cannot be a suffixed-key lookup any more: it resolves through
        the seam, and the LLM gets this level's task-1 copy — byte for
        byte the entry the session's own scenario carries.
        """
        for level, digit in LEVEL_DIGITS:
            with self.subTest(level=level):
                llm = FakeLLM()
                session, storage, _ = self.make_session(llm=llm)
                self.drive(session, "Alice", "3 4 5", digit, "1", "yes", "Answer one")
                state = self.state_of(storage)
                self.assertEqual(state.current_state, "analysis_feedback_1")

                user_answer, role_name, user_name, got_level, task_question = llm.calls[-1]
                self.assertEqual(user_answer, "Answer one")
                self.assertIsNone(role_name)
                self.assertEqual((user_name, got_level), ("Alice", level))
                self.assertEqual(
                    task_question,
                    # The session's own scenario, keyed by base with the
                    # level as a key (C1-9): the randomized copy for this
                    # level, placeholders filled by the variant pass.
                    state.scenario["states"]["analysis_task_1"][level]["message"],
                )
                # The level axis landed on this level's copy, not a neighbour's.
                self.assertIn(f"Softening Criticism ({level.capitalize()})", task_question)

    def test_analysis_task_2_context_reaches_the_llm_at_the_base_name(self):
        """Spec #16 C1-6/C1-7: the task-2 context resolves at the base state name.

        The feedback-2 axis is converted in C1-7, so the state lands at
        its base name and the task sibling is named by base, never by
        surgery on a suffix: the seam joins this session's level onto
        it. The LLM must get this level's task-2 copy - byte for byte
        the entry the session's own scenario carries.
        """
        for level, digit in LEVEL_DIGITS:
            with self.subTest(level=level):
                llm = FakeLLM()
                session, storage, _ = self.make_session(llm=llm)
                self.drive(
                    session, "Alice", "3 4 5", digit, "1", "yes",
                    "Answer one", "next", "Answer two",
                )
                state = self.state_of(storage)
                # The converted row lands the base name (spec #16 C1-7).
                self.assertEqual(state.current_state, "analysis_feedback_2")

                user_answer, role_name, user_name, got_level, task_question = llm.calls[-1]
                self.assertEqual(user_answer, "Answer two")
                self.assertIsNone(role_name)
                self.assertEqual((user_name, got_level), ("Alice", level))
                self.assertEqual(
                    task_question,
                    # The session's own scenario, keyed by base with the
                    # level as a key (C1-9): the randomized copy for this
                    # level, placeholders filled by the variant pass.
                    state.scenario["states"]["analysis_task_2"][level]["message"],
                )
                # The level axis landed on this level's copy, not a neighbour's.
                self.assertIn(
                    f"Aggressive Formatting ({level.capitalize()})", task_question
                )

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
        self.assertEqual(self.state_of(storage).current_state, "analysis_intro")
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

    def test_turn_marks_the_option_the_learner_used(self):
        """A turn knows the option the learner used to answer it (issue #14):
        scenario picks and navigation picks both count; free text marks nothing;
        the newest turn was never answered, so it carries nothing."""
        session, _, _ = self.make_session()
        self.drive(session, *ROLE_MENU_INPUTS)
        used = {
            turn.state: turn.used_value
            for turn in session.turns()
            if turn.role == "assistant"
        }
        self.assertEqual(used["level_assessment"], "2")
        # The registration and intro turns are stored under their base
        # names (spec #16 C1-2 and C1-3).
        self.assertEqual(used["after_registration"], "1")
        self.assertEqual(used["analysis_intro"], "yes")
        # The task-1 turn is stored under its base name (spec #16 C1-4).
        self.assertIsNone(used["analysis_task_1"])
        self.assertIsNone(session.turns()[-1].used_value)

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

    def test_progress_on_a_pre_ledger_row_stays_zero_state(self):
        # A row saved before the ledger exists (the stranded row of
        # ADR-0004): progress() promises it never raises, so the pages
        # render and recovery — reset — is reachable. A KeyError here
        # is a 500 on every render of the deployed site.
        session, storage, _ = self.make_session()
        self.drive_to_role_menu(session)
        legacy = self.state_of(storage)
        legacy.user_data.pop("items")
        storage.save(legacy)

        summary = TutorSession(storage).progress()
        self.assertEqual(summary.completed_steps_count, 0)
        self.assertEqual(summary.percentage, 0)
        self.assertFalse(summary.finished)
        self.assertEqual(set(row_statuses(summary).values()), {"not_started"})
        self.assertEqual(summary.user_name, "Alice")

    def test_effects_on_a_pre_ledger_row_create_the_ledger(self):
        # An accepted input on a stranded row can land on a state that
        # has a transition row; its effect writes items — the ledger is
        # created on the spot, not KeyError 500. No legacy keys are
        # renamed anywhere: this is not a migration (ADR-0004).
        session, storage, _ = self.make_session()
        self.drive_to_role_menu(session)
        legacy = self.state_of(storage)
        legacy.user_data.pop("items")
        storage.save(legacy)

        TutorSession(storage).submit("1")  # role_menu accepts it
        items = self.state_of(storage).user_data["items"]
        self.assertEqual(items["role_mediator"], "in_progress")
