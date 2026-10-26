"""Structural tests for the state transition table (ticket #8).

The table in :mod:`tutor.transitions` is the single source of state
transition mechanics — one data row per concrete scenario state
(``end`` excluded, 44 rows in total). This module pins down its shape:

- the row keys coincide with the scenario state keys minus ``end``;
- every next/back target names a known state, or a bare axis base the
  row registry resolves with a level through the seam (spec #16 C1-2);
- every effect references a valid item or user-data key;
- every row carries the full field set, well-formed.

Fixture coherence and row-by-row agreement with the legacy routing
are checked in the second part of this module.
"""

import copy
import re

from django.test import SimpleTestCase

from .data import ROLE_BY_VALUE, ROLE_LABELS, ROLE_STEP_KEYS, SCENARIO
from .session import MemoryStorage, State
from .transitions import (
    EFFECT_OPS,
    ITEM_STATUSES,
    ROW_FIELDS,
    ROW_REGISTRY,
    TRANSITIONS,
    USER_DATA_KEYS,
    USER_DATA_SOURCES,
    row_for,
    validate_expanded,
    validate_transitions,
)
from .transitions._registry import LEVEL_SUFFIXES, split_state
from .tutor_session import (
    ITEM_KEYS,
    _BACK_LABEL,
    _LEVEL_BY_VALUE,
    TutorSession,
    _parse_scores,
    _sanitize_name,
)

NON_TERMINAL_STATES = set(SCENARIO["states"]) - {"end"}

#: Bare base names of the level axis. A target may spell one (spec #16
#: C1-2): the row registry resolves it with a level through the seam, so
#: it names no scenario state of its own.
AXIS_BASES = {
    base
    for base, level in ROW_REGISTRY
    if level is not None
}


class TransitionTableShapeTests(SimpleTestCase):
    def test_rows_cover_every_non_terminal_scenario_state(self):
        self.assertEqual(set(TRANSITIONS), NON_TERMINAL_STATES)
        self.assertEqual(len(TRANSITIONS), 44)

    def test_every_row_carries_the_full_field_set(self):
        for state, row in TRANSITIONS.items():
            with self.subTest(state=state):
                self.assertEqual(set(row), set(ROW_FIELDS), state)

    def test_validator_accepts_the_table(self):
        self.assertEqual(validate_transitions(), [])

    def test_validator_detects_a_missing_row(self):
        table = copy.deepcopy(TRANSITIONS)
        del table["start"]
        violations = validate_transitions(table)
        self.assertTrue(any("start" in v for v in violations))

    def test_validator_detects_an_unknown_target(self):
        table = copy.deepcopy(TRANSITIONS)
        table["start"]["next"] = "nowhere"
        violations = validate_transitions(table)
        self.assertTrue(any("nowhere" in v for v in violations))

    def test_validator_detects_an_invalid_effect_key(self):
        table = copy.deepcopy(TRANSITIONS)
        table["start"]["effects"] = [("set-item", "no_such_item", "completed")]
        violations = validate_transitions(table)
        self.assertTrue(any("no_such_item" in v for v in violations))

    def test_next_targets_name_known_states(self):
        # Seam-aware (spec #16 C1-2): a target is a scenario state, or a
        # bare axis base the registry resolves with a level.
        states = set(SCENARIO["states"])
        for state, row in TRANSITIONS.items():
            next_ = row["next"]
            with self.subTest(state=state):
                if isinstance(next_, dict):
                    self.assertTrue(next_)
                    for value, target in next_.items():
                        self.assertTrue(
                            target in states or target in AXIS_BASES,
                            f"{state} value {value!r} -> {target!r}",
                        )
                elif next_ is not None:
                    self.assertTrue(next_ in states or next_ in AXIS_BASES)

    def test_back_target_is_none_only_at_start(self):
        # Seam-aware (spec #16 C1-2): a bare axis base back target
        # resolves through the seam at the row's level.
        states = set(SCENARIO["states"])
        for state, row in TRANSITIONS.items():
            back = row["back"]
            with self.subTest(state=state):
                if state == "start":
                    self.assertIsNone(back)
                else:
                    self.assertTrue(back in states or back in AXIS_BASES)

    def test_effects_reference_valid_keys(self):
        for state, row in TRANSITIONS.items():
            for effects in self._effect_lists(row):
                for effect in effects:
                    with self.subTest(state=state, effect=effect):
                        self.assertIn(effect[0], EFFECT_OPS)
                        self.assertEqual(len(effect), 3)
                        if effect[0] == "set-item":
                            self.assertIn(effect[1], ITEM_KEYS)
                            self.assertIn(effect[2], ITEM_STATUSES)
                        else:
                            self.assertIn(effect[1], USER_DATA_KEYS)
                            source = effect[2]
                            self.assertTrue(
                                source in USER_DATA_SOURCES
                                or source.startswith("literal:"),
                                source,
                            )

    def test_effects_align_with_the_next_map(self):
        for state, row in TRANSITIONS.items():
            with self.subTest(state=state):
                if isinstance(row["next"], dict):
                    self.assertIsInstance(row["effects"], dict)
                    self.assertEqual(set(row["effects"]), set(row["next"]))
                else:
                    self.assertIsInstance(row["effects"], list)

    def test_feedback_rows_offer_every_command_they_route(self):
        """Issue #13: a role-play feedback turn offers what its row routes.

        The row's 'next' map is the machine's capability set; the scenario state
        must offer exactly those commands plus 'back'. 'revise' is routed in
        every role-play feedback row, so it has to be offered in every one of
        them — the Empath used to be the only role that offered it.
        """
        for state, row in TRANSITIONS.items():
            if not state.startswith("roleplay_feedback_"):
                continue
            with self.subTest(state=state):
                options = SCENARIO["states"][state].get("options")
                self.assertIsNotNone(options, f"{state} offers no options")
                self.assertEqual(set(options), set(row["next"]) | {"back"})
                self.assertEqual(options["revise"], "✏️ Revise")

    def test_accept_gate_is_well_formed(self):
        for state, row in TRANSITIONS.items():
            accept = row["accept"]
            with self.subTest(state=state):
                if accept is None:
                    continue  # no gate: the legacy if-chain validates nothing
                if isinstance(accept, str):
                    re.compile(accept)  # must be a valid pattern
                else:
                    self.assertIsInstance(accept, list)
                    self.assertTrue(accept)
                    self.assertTrue(all(isinstance(v, str) for v in accept))

    def test_scalar_fields_are_well_formed(self):
        for state, row in TRANSITIONS.items():
            with self.subTest(state=state):
                self.assertIsInstance(row["nav"], dict)
                self.assertTrue(
                    all(isinstance(k, str) and isinstance(v, str) for k, v in row["nav"].items())
                )
                self.assertIsInstance(row["retryable"], bool)
                # The item field mirrors ``_state_to_item``, so every key it
                # yields must be a real completion-model item — the last
                # phantom (``"role_idea"``, from the abbreviated
                # ``roleplay_feedback_idea`` key) is gone (issue #12).
                if row["item"] is not None:
                    self.assertIsInstance(row["item"], str)
                    self.assertIn(row["item"], ITEM_KEYS, state)
                self.assertIsInstance(row["phase"], str)
                self.assertTrue(row["phase"])

    @staticmethod
    def _effect_lists(row):
        if isinstance(row["effects"], dict):
            return row["effects"].values()
        return [row["effects"]]


class RowRegistryTests(SimpleTestCase):
    """The ``(base state, level)`` pair registry and its seam (#17)."""

    AXIS_BASES = (
        "after_registration",
        "analysis_intro",
        "analysis_task_1",
        "analysis_task_2",
        "analysis_feedback_1",
        "analysis_feedback_2",
    )

    def test_pair_registry_covers_the_table_one_to_one(self):
        self.assertEqual(set(ROW_REGISTRY), {split_state(s) for s in TRANSITIONS})
        self.assertEqual(len(ROW_REGISTRY), 44)
        axis_pairs = [pair for pair in ROW_REGISTRY if pair[1] is not None]
        self.assertEqual(len(axis_pairs), 18)  # 6 bases x 3 levels
        self.assertEqual(len(ROW_REGISTRY) - len(axis_pairs), 26)
        for name, row in TRANSITIONS.items():
            self.assertIs(ROW_REGISTRY[split_state(name)], row)

    def test_row_for_resolves_axis_pairs_from_base_and_level(self):
        for base in self.AXIS_BASES:
            for level in LEVEL_SUFFIXES:
                with self.subTest(base=base, level=level):
                    legacy = f"{base}_{level}"
                    self.assertIs(row_for(base, level), TRANSITIONS[legacy])

    def test_row_for_prefers_the_suffix_embedded_in_the_name(self):
        # History entries are self-describing: a suffixed name resolves
        # to its own row even when the session's registered level
        # differs (the mid-session level change is not reachable —
        # spec #16 C1-3 pins this).
        self.assertIs(
            row_for("analysis_task_1_beginner", "advanced"),
            TRANSITIONS["analysis_task_1_beginner"],
        )
        self.assertIs(
            row_for("analysis_task_1_beginner"),
            TRANSITIONS["analysis_task_1_beginner"],
        )

    def test_row_for_resolves_single_form_states_at_any_level(self):
        for state in ("pretest", "role_menu", "data_collection"):
            self.assertIs(row_for(state, "advanced"), TRANSITIONS[state])
            self.assertIs(row_for(state), TRANSITIONS[state])

    def test_row_for_returns_none_for_unknown_pairs(self):
        # A bare axis base is not a node: without a level it must not
        # silently resolve, exactly like a miss on the flat table.
        self.assertIsNone(row_for("analysis_task_1"))
        self.assertIsNone(row_for("analysis_task_1", "novice"))
        self.assertIsNone(row_for("no_such_state", "beginner"))
        self.assertIsNone(row_for("no_such_state"))


class ExpandedTableTests(SimpleTestCase):
    """Validator checks over the expanded (base, level) pair table (#17)."""

    def test_expansion_validates_clean(self):
        # Graph closure, reachability over all 44 pairs, level coverage.
        self.assertEqual(validate_expanded(), [])

    def test_missing_axis_level_is_rejected(self):
        table = copy.deepcopy(TRANSITIONS)
        del table["analysis_task_1_beginner"]
        self.assertIn(
            "expanded: row module 'analysis_task_1' misses axis level 'beginner'",
            validate_expanded(table),
        )

    def test_unreachable_pair_is_rejected(self):
        table = copy.deepcopy(TRANSITIONS)
        # The level_assessment next map is the only inbound edge to the
        # advanced pair cluster: point every value at the intermediate
        # one. The beginner cluster stays reachable through the
        # single-form rows' shared back edge to after_registration_beginner.
        table["level_assessment"]["next"] = {
            value: "after_registration_intermediate" for value in ("1", "2", "3")
        }
        self.assertIn(
            "expanded: pair ('after_registration', 'advanced') "
            "is unreachable from ('start', None)",
            validate_expanded(table),
        )

    def test_target_without_pair_row_is_rejected(self):
        table = copy.deepcopy(TRANSITIONS)
        table["analysis_intro_beginner"]["next"] = "analysis_intro_beginner_beginner"
        self.assertIn(
            "expanded: 'analysis_intro_beginner': target "
            "'analysis_intro_beginner_beginner' resolves to pair "
            "('analysis_intro_beginner', 'beginner') with no row",
            validate_expanded(table),
        )

    def test_flat_validator_runs_the_expanded_checks_too(self):
        # One entry point: the flat checks and the expanded checks
        # share the single violations list.
        table = copy.deepcopy(TRANSITIONS)
        del table["analysis_task_1_beginner"]
        violations = validate_transitions(table)
        self.assertIn("missing row for state 'analysis_task_1_beginner'", violations)
        self.assertIn(
            "expanded: row module 'analysis_task_1' misses axis level 'beginner'",
            violations,
        )


class FakeFeedback:
    """Deterministic stand-in for the LLM feedback callable."""

    def __call__(self, user_answer, role_name, user_name, level, task_question=None):
        return "Feedback.", True


class FixtureCoherenceTests(SimpleTestCase):
    """Every fixture must seed a coherent session (issue criterion 3)."""

    def test_fixtures_seed_coherent_sessions(self):
        for name, row in TRANSITIONS.items():
            fixture = row["fixture"]
            ud = fixture["user_data"]
            items = fixture["items"]
            with self.subTest(state=name):
                self.assertEqual(set(ud), set(USER_DATA_KEYS))
                self.assertEqual(set(items), set(ITEM_KEYS))
                for status in items.values():
                    self.assertIn(status, ITEM_STATUSES)
                for level in ("beginner", "intermediate", "advanced"):
                    if name.endswith("_" + level):
                        self.assertEqual(ud["level"], level)
                # Completion-model invariants.
                if items["pretest"] == "completed":
                    self.assertIsNotNone(ud["user_name"])
                    self.assertIsNotNone(ud["pretest_scores"])
                if items["level_assessment"] == "completed":
                    self.assertIsNotNone(ud["level"])
                if items["posttest"] == "completed":
                    self.assertIsNotNone(ud["posttest_scores"])
                    self.assertEqual(items["reflection"], "completed")
                if items["analysis_task_1"] in ("in_progress", "completed"):
                    self.assertEqual(items["mode_analysis"], "completed")
                if items["analysis_task_2"] in ("in_progress", "completed"):
                    self.assertEqual(items["analysis_task_1"], "completed")
                for mode in ("mode_analysis", "mode_roleplay"):
                    if items[mode] == "completed":
                        self.assertEqual(items["level_assessment"], "completed")
                for role in ROLE_STEP_KEYS:
                    if items[role] in ("in_progress", "completed"):
                        self.assertEqual(ud["current_role"], role)
                if ud["current_role"] is not None:
                    self.assertNotEqual(items[ud["current_role"]], "not_started")


class LegacyParityTests(SimpleTestCase):
    """The table-driven routing must honour the row data (post-migration).

    During the expand step (#8) these tests proved the table reproduced the
    legacy if-chains exactly (acceptance criterion 4). The migrate step (#9)
    removed those if-chains, making the table the single source of truth;
    what remains here pins down that the table-driven ``_route`` /
    ``_go_back`` / ``_navigation_options`` read the row data correctly.
    """

    #: Sample accepted input per accept-pattern. States with ``accept=None``
    #: have no gate in the legacy if-chain and use NO_GATE_SAMPLE.
    SAMPLES = {
        "^[1-5] [1-5] [1-5]$": "3 4 5",
    }
    REJECTIONS = {
        "^[1-5] [1-5] [1-5]$": "1 2",
    }
    NO_GATE_SAMPLE = "A coherent answer"

    def _session(self):
        return TutorSession(MemoryStorage(), feedback=FakeFeedback())

    def _make_state(self, name, row):
        fixture = row["fixture"]
        user_data = copy.deepcopy(fixture["user_data"])
        # The legacy session stores the completion model INSIDE user_data.
        user_data["items"] = copy.deepcopy(fixture["items"])
        return State(
            session_id="parity",
            current_state=name,
            user_data=user_data,
            scenario=SCENARIO,
            chat_history=[],
        )

    def _accepted_inputs(self, row):
        accept = row["accept"]
        if accept is None:
            return [self.NO_GATE_SAMPLE]
        if isinstance(accept, str):
            return [self.SAMPLES[accept]]
        return list(accept)

    def _rejected_input(self, name, row):
        accept = row["accept"]
        if accept is None:
            return None  # no gate: every input is accepted by the legacy
        if isinstance(accept, str):
            return self.REJECTIONS[accept]
        for candidate in ("0", "back", "nope", "6 7 8", "x"):
            if candidate not in accept:
                return candidate
        self.fail(f"no rejection sample for {name!r}")

    def test_accepted_inputs_route_to_table_targets(self):
        for name, row in TRANSITIONS.items():
            for value in self._accepted_inputs(row):
                with self.subTest(state=name, value=value):
                    state = self._make_state(name, row)
                    next_state, accepted = self._session()._route(state, value)
                    expected = row["next"] if isinstance(row["next"], str) else row["next"][value]
                    self.assertTrue(accepted, "routing rejected a table-accepted input")
                    self.assertEqual(next_state, expected)

    def test_rejected_inputs_are_rejected_by_legacy(self):
        for name, row in TRANSITIONS.items():
            value = self._rejected_input(name, row)
            if value is None:
                continue  # no gate: nothing to reject
            with self.subTest(state=name, value=value):
                state = self._make_state(name, row)
                next_state, accepted = self._session()._route(state, value)
                self.assertFalse(accepted)
                self.assertIsNone(next_state)

    def _resolve_source(self, source, state, value):
        if source == "sanitized-name":
            tokens = value.split()
            return _sanitize_name(tokens[0] if tokens else value)
        if source == "parsed-scores":
            return _parse_scores(value)
        if source == "parsed-level":
            return _LEVEL_BY_VALUE[value]
        if source == "mapped-role":
            return ROLE_BY_VALUE[value]
        if source.startswith("literal:"):
            return source[len("literal:"):]
        self.fail(f"unknown effect source {source!r}")

    def _apply_table_effects(self, row, value, state):
        effects = row["effects"]
        if isinstance(effects, dict):
            effects = effects[value]
        ud = state.user_data
        items = ud["items"]
        for effect in effects:
            op, key, operand = effect
            if op == "set-item":
                items[key] = operand
            elif op == "set-user-data":
                ud[key] = self._resolve_source(operand, state, value)
            else:
                self.fail(f"unknown effect op {op!r}")

    def test_effects_match_legacy_side_effects(self):
        for name, row in TRANSITIONS.items():
            for value in self._accepted_inputs(row):
                with self.subTest(state=name, value=value):
                    legacy_state = self._make_state(name, row)
                    self._session()._route(legacy_state, value)
                    table_state = self._make_state(name, row)
                    self._apply_table_effects(row, value, table_state)
                    self.assertEqual(
                        table_state.user_data["items"],
                        legacy_state.user_data["items"],
                        "items mismatch",
                    )
                    for key in USER_DATA_KEYS:
                        self.assertEqual(
                            table_state.user_data[key],
                            legacy_state.user_data[key],
                            f"user_data[{key!r}] mismatch",
                        )

    def test_back_targets_match_legacy_go_back(self):
        for name, row in TRANSITIONS.items():
            with self.subTest(state=name):
                if name == "start":
                    self.assertIsNone(row["back"])
                    continue
                state = self._make_state(name, row)
                self._session()._go_back(state)
                self.assertEqual(state.current_state, row["back"])

    def test_nav_options_match_legacy_navigation(self):
        entry = {"role": "assistant", "llm_failed": False}
        for name, row in TRANSITIONS.items():
            with self.subTest(state=name):
                state = self._make_state(name, row)
                nav = self._session()._navigation_options(state, entry)
                # Typed contract (ADR-0005): every nav offer carries its kind;
                # the synthesised back edge is nav too.
                expected = {value: (label, "nav") for value, label in row["nav"].items()}
                if name != "start":
                    expected["back"] = (_BACK_LABEL, "nav")
                self.assertEqual(nav, expected)

    def test_nav_offers_retry_at_every_state_after_llm_failure(self):
        # Legacy nav-level behaviour: on ``llm_failed`` the "retry" option is
        # offered at EVERY state (not only the feedback ones) while
        # ``retry_count < 3``. That stays in nav assembly, not in the rows.
        entry = {"role": "assistant", "llm_failed": True}
        for name, row in TRANSITIONS.items():
            with self.subTest(state=name):
                state = self._make_state(name, row)
                nav = self._session()._navigation_options(state, entry)
                self.assertIn("retry", nav)


class RoleMenuLabelAlignmentTests(SimpleTestCase):
    """The role menu presents the canonical role mapping (issue #11).

    The live routing map (``ROLE_BY_VALUE`` / the ``next`` of the
    ``role_menu`` row) is the canonical value-to-role correspondence; the
    scenario's option labels and message order must follow it, so a
    button never leads to a role other than the one its label names.
    """

    def test_option_labels_match_canonical_roles(self):
        options = SCENARIO["states"]["role_menu"]["options"]
        for value, role_key in ROLE_BY_VALUE.items():
            with self.subTest(value=value):
                self.assertEqual(options[value], ROLE_LABELS[role_key])

    def test_message_lists_roles_in_label_order(self):
        message = SCENARIO["states"]["role_menu"]["message"]
        found = re.findall(r"🔹(\d) - ([^(]+)", message)
        expected = [
            (value, ROLE_LABELS[ROLE_BY_VALUE[value]] + " ") for value in ROLE_BY_VALUE
        ]
        self.assertEqual(found, expected)


class RejectionCopyTests(SimpleTestCase):
    """Rows own their rejection copy; the validator checks its type (#15).

    A row declares ``rejected``: its copy for a rejected input, or ``None``
    to take the module's generic fallback. The field-set and table-shape
    tests above already pin the closed schema and the validator's acceptance
    of the real table.
    """

    def test_every_row_declares_rejected(self):
        self.assertIn("rejected", ROW_FIELDS)
        for state, row in TRANSITIONS.items():
            with self.subTest(state=state):
                self.assertIn("rejected", row)
                self.assertTrue(row["rejected"] is None or isinstance(row["rejected"], str))

    def test_validator_rejects_a_non_string_copy(self):
        table = copy.deepcopy(TRANSITIONS)
        table["role_menu"]["rejected"] = 123
        violations = validate_transitions(table)
        self.assertTrue(any("rejected" in v for v in violations), violations)

    def test_bespoke_rows_carry_their_copy(self):
        expected = {
            "role_menu": "Choose one of the numbered roles, finish, or back.",
            "analysis_intro_beginner": "Please confirm you want to proceed with the analysis.",
        }
        for state, copy_text in expected.items():
            with self.subTest(state=state):
                self.assertEqual(TRANSITIONS[state]["rejected"], copy_text)
