"""Typed options and row-owned rejection copy (ADR-0005, ticket #15).

Options are the ONE SET offered on a turn: every option is a TurnOption
with a value, a label and a kind. The kind follows the option's ROUTING
ORIGIN (choice = scenario map, nav = row nav/back, retry = LLM-failure
offer), never the map its label came from — on a clash the scenario label
wins and the kind stays nav. A rejected input answers with the CURRENT
ROW's own copy, paired onto the unanswered user turn; rows that declare
no copy fall back to the module's generic string.
"""

from django.test import SimpleTestCase

from .data import ROLE_BY_VALUE
from .session import MemoryStorage, TurnOption
from .test_tutor_session import FakeLLM, ROLE_MENU_INPUTS
from .tutor_session import TutorSession

KINDS = {"choice", "nav", "retry"}

#: The module's fallback for rows that declare no copy (``rejected: None``) —
#: pinned verbatim (it replaces the string the view used to synthesise).
GENERIC = (
    "That answer is not recognized: choose one of the offered options, type "
    "'back', 'finish', 'restart' (to erase and start over), 'export' (to "
    "download the transcript), 'help' (for a summary of the rules), 'idea' "
    "(to generate an idea for the assignments, when the task asks for one), "
    "or 'next' (to advance one page). In data collection, type 'name <your "
    "name>'. The task's own options are shown beneath the question."
)

#: The role menu's row-owned copy.
ROLE_MENU_COPY = "Choose one of the numbered roles, finish, or back."


def _session(llm=None):
    llm = llm if llm is not None else FakeLLM()
    session = TutorSession(MemoryStorage(), llm)
    session.start()
    return session


def _drive(session, *inputs):
    for text in inputs:
        session.submit(text)
    return session


class OptionKindTests(SimpleTestCase):
    def test_option_kinds_match_routing_origin(self):
        session = _drive(_session(), *ROLE_MENU_INPUTS)  # ends at role_menu
        options = session.turns()[-1].options
        self.assertIsInstance(options, list)
        self.assertTrue(all(isinstance(opt, TurnOption) for opt in options))
        kinds = {opt.value: opt.kind for opt in options}
        for value in ROLE_BY_VALUE:  # the nine scenario choices
            self.assertEqual(kinds[value], "choice")
        self.assertEqual(kinds["finish"], "nav")
        self.assertEqual(kinds["back"], "nav")
        self.assertTrue(set(kinds.values()) <= KINDS)

    def test_scenario_label_wins_on_clash(self):
        session = _drive(_session(), *ROLE_MENU_INPUTS[:4])  # analysis_intro
        yes = [opt for opt in session.turns()[-1].options if opt.value == "yes"]
        self.assertEqual(len(yes), 1, "the nav/scenario clash must yield ONE yes option")
        self.assertEqual(yes[0].label, "Yes, proceed")  # the scenario map wins
        self.assertEqual(yes[0].kind, "nav")  # the row's nav routes it

    def test_option_list_has_no_duplicate_values(self):
        for inputs in (
            ROLE_MENU_INPUTS[:4],
            ROLE_MENU_INPUTS,
            ROLE_MENU_INPUTS + ["1"],
        ):
            session = _drive(_session(), *inputs)
            values = [opt.value for opt in session.turns()[-1].options]
            self.assertEqual(len(values), len(set(values)))

    def test_retry_present_only_after_failure(self):
        session = _drive(_session(), *ROLE_MENU_INPUTS[:4])  # analysis_intro
        self.assertNotIn("retry", {opt.value for opt in session.turns()[-1].options})

        failing = _session(FakeLLM(fail_times=1))
        _drive(failing, *ROLE_MENU_INPUTS[:5], "An answer")  # task answer -> feedback fails
        kinds = {opt.value: opt.kind for opt in failing.turns()[-1].options}
        self.assertEqual(kinds.get("retry"), "retry")


class TurnRejectionTests(SimpleTestCase):
    def test_turn_rejection_is_string_or_none(self):
        session = _drive(_session(), *ROLE_MENU_INPUTS)
        session.submit("not a role")
        turns = session.turns()
        self.assertEqual(turns[-1].role, "user")
        self.assertIsInstance(turns[-1].rejection, str)
        self.assertTrue(
            all(isinstance(turn.rejection, (str, type(None))) for turn in turns)
        )

    def test_bespoke_row_owns_its_copy(self):
        session = _drive(_session(), *ROLE_MENU_INPUTS)
        session.submit("not a role")
        self.assertEqual(session.turns()[-1].rejection, ROLE_MENU_COPY)

    def test_nav_row_rejection_falls_back_to_generic(self):
        # analysis_feedback_2: closed accept (next/back), no bespoke copy
        session = _drive(_session(), *ROLE_MENU_INPUTS[:8])
        session.submit("no such task")
        self.assertEqual(session.turns()[-1].rejection, GENERIC)
