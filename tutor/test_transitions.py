"""Structural tests for the state transition registry (ticket #8, #25).

The registry in :mod:`tutor.transitions` is the single source of state
transition mechanics — one data row per graph node, a ``(base state,
level)`` pair (``end`` excluded, 44 pairs in total; spec #16 C1-9,
ADR-0006). This module pins down its shape:

- the registry pairs cover the scenario's base state names minus
  ``end`` — the six axis bases at every level, the rest single-form;
- every next/back target names a known scenario state by base name
  (spec #16 C1-9: no target spells a level suffix);
- every effect references a valid item or user-data key;
- every row carries the full field set, well-formed.

Fixture coherence and row-by-row agreement with the legacy routing
are checked in the second part of this module.
"""

import copy
import inspect
import re

from django.test import SimpleTestCase

from .data import ROLE_BY_VALUE, ROLE_LABELS, ROLE_STEP_KEYS, SCENARIO
from .scenarios import (
    after_registration as after_registration_scenario,
    analysis_feedback_1 as analysis_feedback_1_scenario,
    analysis_feedback_2 as analysis_feedback_2_scenario,
    analysis_intro as analysis_intro_scenario,
    analysis_task_1 as analysis_task_1_scenario,
    analysis_task_2 as analysis_task_2_scenario,
)
from .session import MemoryStorage, State
from .transitions import (
    EFFECT_OPS,
    ITEM_STATUSES,
    ROW_FIELDS,
    ROW_REGISTRY,
    USER_DATA_KEYS,
    USER_DATA_SOURCES,
    analysis_task_1,
    role_menu,
    row_for,
    start,
    validate_transitions,
)
from .transitions._registry import LEVEL_KEYS
from .transitions._validate import AXIS_BASES
from .test_tutor_session import ROLE_MENU_COPY
from .tutor_session import (
    ITEM_KEYS,
    _BACK_LABEL,
    _LEVEL_BY_VALUE,
    TutorSession,
    _parse_scores,
    _sanitize_name,
)

NON_TERMINAL_STATES = set(SCENARIO["states"]) - {"end"}


def _single_form_pairs():
    """The ``(state, None)`` registry keys — every base outside the axis."""
    return {(base, None) for base in NON_TERMINAL_STATES} - {
        (base, None) for base in AXIS_BASES
    }


def _axis_pairs():
    """The axis ``(base, level)`` keys, spelled from the axis bases and
    the level axis — never from a suffixed name."""
    return {(base, level) for base in AXIS_BASES for level in LEVEL_KEYS}


class TransitionTableShapeTests(SimpleTestCase):
    def test_rows_cover_every_non_terminal_scenario_state(self):
        # Coverage over the SCENARIO: every non-terminal base state has
        # rows — an axis base exactly one pair per level, every other
        # base exactly its single-form pair (spec #16 C1-9).
        by_base: dict[str, int] = {}
        for base, _level in ROW_REGISTRY:
            by_base[base] = by_base.get(base, 0) + 1
        self.assertEqual(set(by_base), NON_TERMINAL_STATES)
        for base, count in by_base.items():
            with self.subTest(base=base):
                want = 3 if base in AXIS_BASES else 1
                self.assertEqual(count, want)

    def test_every_row_carries_the_full_field_set(self):
        for pair, row in ROW_REGISTRY.items():
            with self.subTest(pair=pair):
                self.assertEqual(set(row), set(ROW_FIELDS), pair)

    def test_validator_accepts_the_table(self):
        self.assertEqual(validate_transitions(), [])

    def test_validator_detects_a_missing_row(self):
        table = copy.deepcopy(ROW_REGISTRY)
        del table[("start", None)]
        violations = validate_transitions(table)
        self.assertTrue(any("start" in v for v in violations))

    def test_validator_detects_an_unknown_target(self):
        table = copy.deepcopy(ROW_REGISTRY)
        table[("start", None)]["next"] = "nowhere"
        violations = validate_transitions(table)
        self.assertTrue(any("nowhere" in v for v in violations))

    def test_validator_detects_an_invalid_effect_key(self):
        table = copy.deepcopy(ROW_REGISTRY)
        table[("start", None)]["effects"] = [
            ("set-item", "no_such_item", "completed")
        ]
        violations = validate_transitions(table)
        self.assertTrue(any("no_such_item" in v for v in violations))

    def test_next_targets_name_known_states(self):
        # Spec #16 C1-9: every target spells a scenario state by base
        # name — no bare axis bases, no suffix spellings; the pair
        # algebra resolves them.
        states = set(SCENARIO["states"])
        for pair, row in ROW_REGISTRY.items():
            next_ = row["next"]
            with self.subTest(pair=pair):
                if isinstance(next_, dict):
                    self.assertTrue(next_)
                    for value, target in next_.items():
                        self.assertIn(target, states, f"{pair} value {value!r}")
                elif next_ is not None:
                    self.assertIn(next_, states)

    def test_back_target_is_none_only_at_start_and_registration(self):
        # Spec #16 C1-9: back targets name scenario states by base.
        # The registration axis joins ``start`` in declaring None —
        # the point of no return (spec #16 C1-8, ADR-0006 decision 2).
        states = set(SCENARIO["states"])
        for pair, row in ROW_REGISTRY.items():
            base, _level = pair
            back = row["back"]
            with self.subTest(pair=pair):
                if base == "start" or base == "after_registration":
                    self.assertIsNone(back)
                else:
                    self.assertIn(back, states)

    def test_effects_reference_valid_keys(self):
        for pair, row in ROW_REGISTRY.items():
            for effects in self._effect_lists(row):
                for effect in effects:
                    with self.subTest(pair=pair, effect=effect):
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
        for pair, row in ROW_REGISTRY.items():
            with self.subTest(pair=pair):
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
        for pair, row in ROW_REGISTRY.items():
            base = pair[0]
            if not base.startswith("roleplay_feedback_"):
                continue
            with self.subTest(pair=pair):
                options = SCENARIO["states"][base].get("options")
                self.assertIsNotNone(options, f"{base} offers no options")
                self.assertEqual(set(options), set(row["next"]) | {"back"})
                self.assertEqual(options["revise"], "✏️ Revise")

    def test_accept_gate_is_well_formed(self):
        for pair, row in ROW_REGISTRY.items():
            accept = row["accept"]
            with self.subTest(pair=pair):
                if accept is None:
                    continue  # no gate: the legacy if-chain validates nothing
                if isinstance(accept, str):
                    re.compile(accept)  # must be a valid pattern
                else:
                    self.assertIsInstance(accept, list)
                    self.assertTrue(accept)
                    self.assertTrue(all(isinstance(v, str) for v in accept))

    def test_scalar_fields_are_well_formed(self):
        for pair, row in ROW_REGISTRY.items():
            with self.subTest(pair=pair):
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
                    self.assertIn(row["item"], ITEM_KEYS, pair)
                self.assertIsInstance(row["phase"], str)
                self.assertTrue(row["phase"])

    @staticmethod
    def _effect_lists(row):
        if isinstance(row["effects"], dict):
            return row["effects"].values()
        return [row["effects"]]


class RowRegistryTests(SimpleTestCase):
    """The ``(base state, level)`` pair registry and its seam (#17, #25)."""

    def test_pair_registry_covers_the_table_one_to_one(self):
        # C1-9: the registry IS the table — pair composition, and the
        # rows are the modules' own row objects (no copy step).
        self.assertEqual(set(ROW_REGISTRY), _single_form_pairs() | _axis_pairs())
        self.assertEqual(len(ROW_REGISTRY), 44)
        axis_pairs = [pair for pair in ROW_REGISTRY if pair[1] is not None]
        self.assertEqual(len(axis_pairs), 18)  # 6 bases x 3 levels
        self.assertEqual(len(ROW_REGISTRY) - len(axis_pairs), 26)
        self.assertIs(ROW_REGISTRY[("start", None)], start.ROW)
        self.assertIs(ROW_REGISTRY[("role_menu", None)], role_menu.ROW)
        self.assertIs(
            ROW_REGISTRY[("analysis_task_1", "beginner")],
            analysis_task_1.ROWS["beginner"],
        )

    def test_row_for_resolves_axis_pairs_from_base_and_level(self):
        for base in AXIS_BASES:
            for level in LEVEL_KEYS:
                with self.subTest(base=base, level=level):
                    self.assertIs(row_for(base, level), ROW_REGISTRY[(base, level)])

    def test_row_for_resolves_no_suffixed_name(self):
        # C1-9 retires the suffix spelling: a name that carries the
        # level as a suffix is not a node — it resolves to nothing,
        # the same as any unknown state. The name is composed at
        # runtime; no suffixed literal is spelled in this module.
        for base in AXIS_BASES:
            for level in LEVEL_KEYS:
                suffixed = f"{base}_{level}"
                with self.subTest(base=base, level=level):
                    self.assertIsNone(row_for(suffixed, "advanced"))
                    self.assertIsNone(row_for(suffixed))

    def test_row_for_resolves_single_form_states_at_any_level(self):
        for state in ("pretest", "role_menu", "data_collection"):
            self.assertIs(row_for(state, "advanced"), ROW_REGISTRY[(state, None)])
            self.assertIs(row_for(state), ROW_REGISTRY[(state, None)])

    def test_row_for_returns_none_for_unknown_pairs(self):
        # A bare axis base is not a node: without a level it must not
        # silently resolve, exactly like a miss on the flat table.
        self.assertIsNone(row_for("analysis_task_1"))
        self.assertIsNone(row_for("analysis_task_1", "novice"))
        self.assertIsNone(row_for("no_such_state", "beginner"))
        self.assertIsNone(row_for("no_such_state"))


class GraphChecksTests(SimpleTestCase):
    """Validator graph checks over the pair registry — closure,
    reachability, level coverage (spec #16 C1-1, folded into the
    registry by C1-9; the ``graph:`` message prefix is kept)."""

    def test_graph_checks_pass_on_the_real_table(self):
        # Graph closure, reachability over all 44 pairs, level coverage.
        self.assertEqual(validate_transitions(), [])

    def test_missing_axis_level_is_rejected(self):
        table = copy.deepcopy(ROW_REGISTRY)
        del table[("analysis_task_1", "beginner")]
        self.assertIn(
            "graph: row module 'analysis_task_1' misses axis level 'beginner'",
            validate_transitions(table),
        )

    def test_unreachable_pair_is_rejected(self):
        table = copy.deepcopy(ROW_REGISTRY)
        # Only two kinds of edges lead into the role-play cluster: the
        # analysis arc's feedback_2 rows and registration's role-play
        # option. Detour every level path's feedback_2 to the reflection
        # and every registration's role-play option to the analysis arc —
        # the cluster drops out of the BFS. (Registration's back is
        # retired: point of no return; single-form rows' back spells the
        # BASE name, so no back edge leads forward into the cluster.)
        for level in LEVEL_KEYS:
            pair = ("analysis_feedback_2", level)
            table[pair] = {**table[pair], "next": "reflection"}
            pair = ("after_registration", level)
            table[pair] = {
                **table[pair],
                "next": {"1": "analysis_intro", "2": "analysis_intro"},
            }
        self.assertIn(
            "graph: pair ('roleplay_intro', None) "
            "is unreachable from ('start', None)",
            validate_transitions(table),
        )

    def test_no_row_spells_a_suffixed_registration_target(self):
        """Ticket #24 AC[3]: the registration target is spelled by the
        named mechanism — the BASE name resolved with the session's
        level at the construction point — never as a suffixed literal."""
        spelled = {
            f"after_registration_{level}" for level in LEVEL_KEYS
        }
        self.assertEqual([t for t in self._all_targets(ROW_REGISTRY) if t in spelled], [])

    def test_no_path_reaches_level_assessment_after_registration(self):
        """Ticket #24 AC[1]: the point of no return — no next, back, nav,
        or self edge from any registration level leads back to the level
        assessment, the pretest, or start; the only escape is reset."""
        for level in LEVEL_KEYS:
            reached = self._reachable_pairs(("after_registration", level))
            self.assertNotIn(("level_assessment", None), reached)
            self.assertNotIn(("pretest", None), reached)
            self.assertNotIn(("start", None), reached)

    def test_go_back_has_no_prefix_repair(self):
        """Ticket #24 AC[3]: the runtime prefix-repair in _go_back is
        deleted — no back target is rewritten by string surgery."""
        source = inspect.getsource(TutorSession._go_back)
        self.assertNotIn("startswith", source)
        self.assertNotIn("after_registration_", source)

    @staticmethod
    def _all_targets(table):
        """Every state name a table can route to: next values, back,
        nav values."""
        targets = []
        for row in table.values():
            nxt = row.get("next")
            if isinstance(nxt, str):
                targets.append(nxt)
            elif isinstance(nxt, dict):
                targets.extend(nxt.values())
            if row.get("back") is not None:
                targets.append(row["back"])
            targets.extend((row.get("nav") or {}).values())
        return targets

    @staticmethod
    def _reachable_pairs(origin):
        """BFS over (state, level) pairs following next, back, and nav
        edges, resolving a bare axis base with the BFS's fixed level —
        the session's construction-point rule at one level. Targets
        spell base names (spec #16 C1-9): no suffix splitting."""
        level = origin[1]
        reached, queue = set(), [origin]
        while queue:
            pair = queue.pop()
            if pair in reached:
                continue
            reached.add(pair)
            row = ROW_REGISTRY.get(pair)
            if row is None:
                continue
            for target in GraphChecksTests._all_targets({"r": row}):
                if (target, level) in ROW_REGISTRY:
                    queue.append((target, level))
                else:
                    queue.append((target, None))
        return reached

    def test_target_without_pair_row_is_rejected(self):
        table = copy.deepcopy(ROW_REGISTRY)
        # A target that (mis)spells a suffixed name resolves to the
        # self-describing pair and is reported: the retired spelling
        # must never enter the graph (spec #16 C1-9 AC1). The name is
        # composed at runtime from the level axis.
        level = "beginner"
        table[("analysis_intro", level)]["next"] = f"analysis_intro_{level}_{level}"
        self.assertIn(
            f"graph: ('analysis_intro', '{level}'): target "
            f"'analysis_intro_{level}_{level}' resolves to pair "
            f"('analysis_intro_{level}', '{level}') with no row",
            validate_transitions(table),
        )

    def test_row_checks_and_graph_checks_share_one_violations_list(self):
        # One entry point: the row-shape checks and the graph checks
        # share the single violations list (the expand step is gone).
        table = copy.deepcopy(ROW_REGISTRY)
        del table[("analysis_task_1", "beginner")]
        self.assertIn(
            "graph: row module 'analysis_task_1' misses axis level 'beginner'",
            validate_transitions(table),
        )
        for level in ("intermediate", "advanced"):
            del table[("analysis_task_1", level)]
        self.assertIn(
            "missing row for state 'analysis_task_1'",
            validate_transitions(table),
        )


class FakeFeedback:
    """Deterministic stand-in for the LLM feedback callable."""

    def __call__(self, user_answer, role_name, user_name, level, task_question=None):
        return "Feedback.", True


class FixtureCoherenceTests(SimpleTestCase):
    """Every fixture must seed a coherent session (issue criterion 3)."""

    def test_fixtures_seed_coherent_sessions(self):
        for pair, row in ROW_REGISTRY.items():
            base, level = pair
            fixture = row["fixture"]
            ud = fixture["user_data"]
            items = fixture["items"]
            with self.subTest(pair=pair):
                self.assertEqual(set(ud), set(USER_DATA_KEYS))
                self.assertEqual(set(items), set(ITEM_KEYS))
                for status in items.values():
                    self.assertIn(status, ITEM_STATUSES)
                # The axis fixture carries its pair's level (generated
                # by the seam, spec #16 C1-2..C1-7); the level axis
                # values come from the module, not a name suffix.
                if level is not None:
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
        for (name, _level), row in ROW_REGISTRY.items():
            for value in self._accepted_inputs(row):
                with self.subTest(state=name, value=value):
                    state = self._make_state(name, row)
                    next_state, accepted = self._session()._route(state, value)
                    expected = row["next"] if isinstance(row["next"], str) else row["next"][value]
                    self.assertTrue(accepted, "routing rejected a table-accepted input")
                    self.assertEqual(next_state, expected)

    def test_rejected_inputs_are_rejected_by_legacy(self):
        for (name, _level), row in ROW_REGISTRY.items():
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
        for (name, _level), row in ROW_REGISTRY.items():
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

    def test_back_targets_match_legacy_go_back_except_the_point_of_no_return(self):
        for (name, _level), row in ROW_REGISTRY.items():
            with self.subTest(state=name):
                if name == "start" or name == "after_registration":
                    # Point of no return (spec #16 C1-8): no back edge,
                    # so _go_back treats the typed command as rejected
                    # input and the state stays put.
                    self.assertIsNone(row["back"])
                    state = self._make_state(name, row)
                    self._session()._go_back(state)
                    self.assertEqual(state.current_state, name)
                    continue
                state = self._make_state(name, row)
                self._session()._go_back(state)
                self.assertEqual(state.current_state, row["back"])

    def test_nav_options_match_legacy_navigation(self):
        entry = {"role": "assistant", "llm_failed": False}
        for (name, _level), row in ROW_REGISTRY.items():
            with self.subTest(state=name):
                state = self._make_state(name, row)
                nav = self._session()._navigation_options(state, entry)
                # Typed contract (ADR-0005): every nav offer carries its kind;
                # the synthesised back edge is nav too. The offer follows the
                # row's back edge (spec #16 C1-8): start and the registration
                # axis (None) offer none; every other row offers one.
                expected = {value: (label, "nav") for value, label in row["nav"].items()}
                if row["back"] is not None:
                    expected["back"] = (_BACK_LABEL, "nav")
                self.assertEqual(nav, expected)

    def test_nav_offers_retry_at_every_state_after_llm_failure(self):
        # Legacy nav-level behaviour: on ``llm_failed`` the "retry" option is
        # offered at EVERY state (not only the feedback ones) while
        # ``retry_count < 3``. That stays in nav assembly, not in the rows.
        entry = {"role": "assistant", "llm_failed": True}
        for (name, _level), row in ROW_REGISTRY.items():
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
        for pair, row in ROW_REGISTRY.items():
            with self.subTest(pair=pair):
                self.assertIn("rejected", row)
                self.assertTrue(row["rejected"] is None or isinstance(row["rejected"], str))

    def test_validator_rejects_a_non_string_copy(self):
        table = copy.deepcopy(ROW_REGISTRY)
        table[("role_menu", None)]["rejected"] = 123
        violations = validate_transitions(table)
        self.assertTrue(any("rejected" in v for v in violations), violations)

    def test_bespoke_rows_carry_their_copy(self):
        # The role-menu string is pinned once, in
        # test_tutor_session.ROLE_MENU_COPY; the intro copy is bespoke
        # to this table and lives here.
        expected = {
            ("role_menu", None): ROLE_MENU_COPY,
            ("analysis_intro", "beginner"): (
                "Please confirm you want to proceed with the analysis."
            ),
        }
        for pair, copy_text in expected.items():
            with self.subTest(pair=pair):
                self.assertEqual(ROW_REGISTRY[pair]["rejected"], copy_text)


class AxisScenarioCopyTests(SimpleTestCase):
    """The axis copy stays byte-exact at every level (spec #16 C1-3, C1-4)."""

    def test_intro_message_is_byte_exact_per_level(self):
        """The map replaces three modules; the words must not move."""
        expected = {
            "beginner": "**Step1️⃣: ANALYSIS**\n\nYou'll learn to identify basic metagrapheme functions and practice softening simple criticism using examples of online comments.\n\n👇**Click *yes* to start**",
            "intermediate": "**Step1️⃣: ANALYSIS**\n\nYou'll analyze more complex examples of online comments and practice nuanced use of metagraphemes.\n\n👇**Click *yes* to start**",
            "advanced": "**Step1️⃣: ANALYSIS**\n\nYou'll work with complex, multi-layered examples of online comments and cultural comparisons.\n\n👇**Click *yes* to start**",
        }
        for level, message in expected.items():
            with self.subTest(level=level):
                self.assertEqual(
                    analysis_intro_scenario.STATE[level]["message"],
                    message,
                )

    def test_intro_framing_is_shared_across_the_axis(self):
        """Only the level body differs: heading and call to action are fixed."""
        messages = {
            level: analysis_intro_scenario.STATE[level]["message"]
            for level in LEVEL_KEYS
        }
        heads = {m.split("\n")[0] for m in messages.values()}
        self.assertEqual(heads, {"**Step1️⃣: ANALYSIS**"})
        for level in LEVEL_KEYS:
            with self.subTest(level=level):
                self.assertTrue(messages[level].endswith("\n\n👇**Click *yes* to start**"))

    def test_task_1_message_is_byte_exact_per_level(self):
        """The map replaces three modules; the words must not move.

        The task-1 axis of spec #16 C1-4 pins its three texts whole,
        byte for byte.
        """
        expected = {
            "beginner": "**📝 TASK 1: Softening Criticism (Beginner)**\n\nContext: {context}\n\nOriginal message: *{message}*\n\n❓ **Question:** Which emoji(s) would you add to the END of this message to make it sound kinder? Explain your choice.\n\n*Hint: {hint}*\n\n⬇️**Type your answer and tap Enter:**",
            "intermediate": "**📝 TASK 1: Softening Criticism (Intermediate)**\n\nContext: {context}\n\nOriginal message: *{message}*\n\n❓ **Question:** Which emoji(s) would you add to signal openness to dialogue?\n\n💡*Hint: {hint}*\n\n⬇️**Type your answer and tap Enter:**",
            "advanced": "**📝 TASK 1: Softening Criticism (Advanced)**\n\nContext: {context}\n\nOriginal message: {message}\n\n❓ **Question:** Where would you place emojis to maintain professionalism?\n\n*Hint: {hint}*\n\n⬇️**Type your answer:**",
        }
        for level, message in expected.items():
            with self.subTest(level=level):
                self.assertEqual(
                    analysis_task_1_scenario.STATE[level]["message"],
                    message,
                )

    def test_task_1_framing_is_shared_across_the_axis(self):
        """Only the level wording differs: the framing and the gate are fixed.

        The heading, the context line, the question lead-in, the answer
        prompt and the free-text gate are shared along the task-1 axis
        (spec #16 C1-4).
        """
        states = {
            level: analysis_task_1_scenario.STATE[level]
            for level in LEVEL_KEYS
        }
        for level in LEVEL_KEYS:
            with self.subTest(level=level):
                message = states[level]["message"]
                self.assertTrue(message.startswith("**📝 TASK 1: Softening Criticism ("))
                self.assertIn("**\n\nContext: {context}\n\nOriginal message: ", message)
                self.assertIn("\n\n❓ **Question:** ", message)
                self.assertIn("\n\n⬇️**Type your answer", message)
                self.assertEqual(states[level]["validation"], ".+")
        # The axis carries three distinct texts, not one text three times.
        self.assertEqual(len({state["message"] for state in states.values()}), 3)

    def test_task_2_message_is_byte_exact_per_level(self):
        """The map replaces three modules; the words must not move.

        The task-2 axis of spec #16 C1-6 pins its three texts whole,
        byte for byte: the heading, the message line (quoted at the
        beginner level), the question, and the hint line present at the
        two lower levels and absent at the advanced one.
        """
        expected = {
            "beginner": "**📝 TASK 2: Recognizing Aggressive Formatting (Beginner)**\n\nMessage: *{message}*\n\n❓ **Question:** What makes this message feel aggressive? Identify ONE technique.\n\n💡*Hint: {hint}*\n\n⬇️**Type your answer and tap Enter:**",
            "intermediate": "**📝 TASK 2: Recognizing Aggressive Formatting (Intermediate)**\n\nMessage: {message}\n\n❓ **Question:** Identify TWO metagrapheme techniques used here.\n\n💡*Hint: {hint}*\n\n⬇️**Type your answer and tap Enter:**",
            "advanced": "**📝 TASK 2: Recognizing Aggressive Formatting (Advanced)**\n\nMessage: {message}\n\n❓ **Question:** Analyze ALL metagrapheme techniques used here.\n\n⌨️**Type your analysis:**",
        }
        for level, message in expected.items():
            with self.subTest(level=level):
                self.assertEqual(
                    analysis_task_2_scenario.STATE[level]["message"],
                    message,
                )

    def test_task_2_framing_is_shared_across_the_axis(self):
        """Only the level wording differs: the framing and the gate are fixed.

        The heading, the message line and the question lead-in are shared
        along the task-2 axis (spec #16 C1-6). The hint line and the
        answer-and-Enter prompt belong to the two lower levels; the
        advanced level swaps them for the free-text analysis prompt.
        """
        states = {
            level: analysis_task_2_scenario.STATE[level]
            for level in LEVEL_KEYS
        }
        for level in LEVEL_KEYS:
            with self.subTest(level=level):
                message = states[level]["message"]
                self.assertTrue(
                    message.startswith(
                        f"**📝 TASK 2: Recognizing Aggressive Formatting "
                        f"({level.capitalize()})**\n\n"
                    )
                )
                self.assertIn("\n\nMessage: ", message)
                self.assertIn("\n\n❓ **Question:** ", message)
                self.assertEqual(states[level]["validation"], ".+")
        # The hint affordance is the two lower levels', not the advanced one's.
        for level in ("beginner", "intermediate"):
            with self.subTest(level=level):
                self.assertIn("\n\n💡*Hint: {hint}*\n\n", states[level]["message"])
        self.assertNotIn("*Hint:", states["advanced"]["message"])
        # The prompt: answer-and-Enter at the two lower levels, analysis at the advanced.
        for level in ("beginner", "intermediate"):
            with self.subTest(level=level):
                self.assertTrue(
                    states[level]["message"].endswith(
                        "\n\n⬇️**Type your answer and tap Enter:**"
                    )
                )
        self.assertTrue(
            states["advanced"]["message"].endswith("\n\n⌨️**Type your analysis:**")
        )
        # Only the beginner quotes the message the learner analyses.
        self.assertIn("\n\nMessage: *{message}*\n\n", states["beginner"]["message"])
        self.assertNotIn("Message: *{message}*", states["intermediate"]["message"])
        # The axis carries three distinct texts, not one text three times.
        self.assertEqual(len({state["message"] for state in states.values()}), 3)

    def test_feedback_1_message_is_byte_exact_per_level(self):
        """The map replaces three modules; the words must not move.

        The feedback-1 axis of spec #16 C1-5 pins its three texts whole,
        byte for byte: the level headline, the feedback line, the model
        answer (absent at the advanced level) and the call to action.
        """
        expected = {
            "beginner": "📖 **Read the feedback for you, {user_name} (Beginner), carefully and make notes:**\n\nGreat start! Adding a friendly emoji like 🙂 or 😊 can make criticism feel more supportive.\n\n**📋 Model answer:** 'This essay has some areas to work on 🙂. Let's look at them together.'\n\n👇**Tap *next* to proceed to Task 2:**",
            "intermediate": "📖 **Read the feedback for you, {user_name} (Intermediate), carefully and make notes:**\n\nGood approach! A friendly emoji like 🙂 or 🤔 acts as an 'emotional cushion'.\n\n**📋 Model answer:** 'I think the data in this part might need a second look 🤔.'\n\n👇**Tap *next* to continue:**",
            "advanced": "📖 **Read the feedback for you, {user_name} (Advanced), carefully and make notes:**\n\nFor complex feedback, emoji after the main critique softens tone.\n\n👇**Tap *next* to continue:**",
        }
        for level, message in expected.items():
            with self.subTest(level=level):
                self.assertEqual(
                    analysis_feedback_1_scenario.STATE[level]["message"],
                    message,
                )

    def test_feedback_1_framing_is_shared_across_the_axis(self):
        """Only the level wording differs: the framing and the options are fixed.

        The reading instruction naming the level, the model-answer lead-in
        (the LLM injection marker of spec #16) and the two scenario
        options are shared along the feedback-1 axis (spec #16 C1-5).
        """
        states = {
            level: analysis_feedback_1_scenario.STATE[level]
            for level in LEVEL_KEYS
        }
        for level in LEVEL_KEYS:
            with self.subTest(level=level):
                message = states[level]["message"]
                self.assertTrue(
                    message.startswith(
                        f"📖 **Read the feedback for you, {{user_name}} "
                        f"({level.capitalize()}), carefully and make notes:**\n\n"
                    )
                )
                self.assertIn("\n\n👇**Tap *next*", message)
                self.assertEqual(
                    states[level]["options"],
                    {"next": "Next Task", "back": "Back to menu"},
                )
        # The LLM injection marker sits in the two lower levels' copy, so
        # the feedback the model generates lands where the old text did.
        for level in ("beginner", "intermediate"):
            with self.subTest(level=level):
                self.assertIn("\n\n**📋 Model answer:**", states[level]["message"])
        self.assertNotIn("**📋 Model answer:**", states["advanced"]["message"])
        # The axis carries three distinct texts, not one text three times.
        self.assertEqual(len({state["message"] for state in states.values()}), 3)

    def test_feedback_2_message_is_byte_exact_per_level(self):
        """The map replaces three modules; the words must not move.

        The feedback-2 axis of spec #16 C1-7 pins its three texts whole,
        byte for byte: the reading instruction naming the level, the
        feedback line, the model answer (absent at the advanced level)
        and the call to action. This is the feedback copy the generated
        answer splices into, so the paragraph breaks sit exactly where
        the marker of :data:`tutor.tutor_session._ANALYSIS_MARKERS`
        looks for them.
        """
        expected = {
            "beginner": "📖 **Read the feedback for you, {user_name} (Beginner), carefully and make notes:**\n\nYou're right! **ALL CAPS** feels like shouting online.\n\n**📋 Model answer:** 'The message uses ALL CAPS and multiple exclamation marks, which is like shouting online.'\n\n👇**Click the button below to proceed to Step 2: Role-play**",
            "intermediate": "📖 **Read the feedback for you, {user_name} (Intermediate), carefully and make notes:**\n\nKey techniques: Alternating caps (mockery) and multiple exclamation marks (shouting).\n\n**📋 Model answer:** 'The message uses **tHaT's NoT** with alternating caps to mock, and **!!!** to shout.'\n\n👇**Tap *next* to proceed:**",
            "advanced": "📖 **Read the feedback for you, {user_name} (Advanced), carefully and make notes:**\n\nTechniques: ALL CAPS (irony), ellipsis (dramatic pause), 🙄 emoji (sarcasm), #facepalm (meta-commentary).\n\n👇**Tap *next* to proceed:**",
        }
        for level, message in expected.items():
            with self.subTest(level=level):
                self.assertEqual(
                    analysis_feedback_2_scenario.STATE[level]["message"],
                    message,
                )

    def test_feedback_2_framing_is_shared_across_the_axis(self):
        """Only the level wording differs: the framing and the options are fixed.

        The reading instruction naming the level, the model-answer
        lead-in and the two scenario options are shared along the
        feedback-2 axis (spec #16 C1-7). The model-answer lead-in is the
        LLM injection marker: it sits in the two lower levels' copy and
        is absent at the advanced one. The call to action is the
        beginner's own — from this state the learner leaves the analysis
        arc for the role-play step.
        """
        states = {
            level: analysis_feedback_2_scenario.STATE[level]
            for level in LEVEL_KEYS
        }
        for level in LEVEL_KEYS:
            with self.subTest(level=level):
                message = states[level]["message"]
                self.assertTrue(
                    message.startswith(
                        f"📖 **Read the feedback for you, {{user_name}} "
                        f"({level.capitalize()}), carefully and make notes:**\n\n"
                    )
                )
                self.assertEqual(
                    states[level]["options"],
                    # The label ends in one keycap: DIGIT TWO, VARIATION
                    # SELECTOR-16, COMBINING ENCLOSING KEYCAP — the exact
                    # codepoints the original copy carried.
                    {"next": "Proceed to Step2️⃣", "back": "Back to menu"},
                )
        # The LLM injection marker sits in the two lower levels' copy, so
        # the feedback the model generates lands where the old text did.
        for level in ("beginner", "intermediate"):
            with self.subTest(level=level):
                self.assertIn("\n\n**📋 Model answer:**", states[level]["message"])
        self.assertNotIn("**📋 Model answer:**", states["advanced"]["message"])
        # The call to action: the beginner names the step it walks to,
        # the two other levels share the tap invitation.
        self.assertTrue(
            states["beginner"]["message"].endswith(
                "\n\n👇**Click the button below to proceed to Step 2: Role-play**"
            )
        )
        for level in ("intermediate", "advanced"):
            with self.subTest(level=level):
                self.assertTrue(
                    states[level]["message"].endswith(
                        "\n\n👇**Tap *next* to proceed:**"
                    )
                )
        # The axis carries three distinct texts, not one text three times.
        self.assertEqual(len({state["message"] for state in states.values()}), 3)
