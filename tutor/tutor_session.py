"""TutorSession — a deep module over the storage seam (ticket #3).

Owns the full 15-step session lifecycle behind five public methods:

- ``start() -> Turn``       — begin a fresh session, return the welcome turn
- ``submit(text) -> Turn``  — advance the machine with user input
- ``turns() -> list[Turn]`` — the chat history; navigation options are
  assembled on the current assistant turn only
- ``progress() -> Summary`` — every progress figure derived from the one
  canonical per-item completion model
- ``reset() -> None``       — clear the stored session

The module never touches ``request.session``: it loads and saves
:class:`~tutor.session.State` through a :class:`~tutor.session.Storage`
adapter and receives LLM feedback as an injected callable
(:func:`tutor.llm.get_llm_feedback` by default). Completion is stored as
``user_data["items"]`` — a mapping of every assessable item to
``not_started`` / ``in_progress`` / ``completed`` — and every figure the
views show (percentage, step counters, section rows with their status) is
derived from that single model; the templates branch on nothing.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Optional

from .data import (
    ANALYSIS_LABELS,
    ANALYSIS_STEP_KEYS,
    ROLE_BY_VALUE,
    ROLE_LABELS,
    ROLE_STEP_KEYS,
    SCENARIO,
    STEP_KEYS,
    TOTAL_STEPS,
    randomize_scenario,
)
from .llm import get_llm_feedback
from .session import (
    Feedback,
    ProgressRow,
    ProgressSection,
    State,
    Storage,
    Summary,
    Turn,
    TurnOption,
    default_feedback,
)
from .transitions import join_state, row_for, split_state

#: The one canonical completion model: every assessable item plus the two
#: mode choices. ``data_collection`` is deliberately NOT an item — the old
#: code listed it as a 16th "step" which could push the percentage past 100.
ITEM_KEYS: tuple[str, ...] = tuple(STEP_KEYS) + ("mode_analysis", "mode_roleplay")

_LEVEL_BY_VALUE: dict[str, str] = {
    "1": "beginner",
    "2": "intermediate",
    "3": "advanced",
}
_LEVEL_BY_NAME: dict[str, str] = {value: key for key, value in _LEVEL_BY_VALUE.items()}

_MAX_INPUT_LENGTH = 5000
_MAX_NAME_LENGTH = 50
_NAME_PLACEHOLDER = "student"

_ANALYSIS_MARKERS = ("\n\n**📋 Model answer:**", "\n\n▶️")
_ROLEPLAY_MARKERS = ("\n\n▶️",)

_BACK_LABEL = "⬅️ Back"

#: The module's fallback copy for rows that declare ``rejected: None``
#: (ADR-0005: rejection is the module's question, so the fallback string
#: lives here, not in the view).
_GENERIC_REJECTION = (
    "That answer is not recognized: choose one of the offered options, type "
    "'back', 'finish', 'restart' (to erase and start over), 'export' (to "
    "download the transcript), 'help' (for a summary of the rules), 'idea' "
    "(to generate an idea for the assignments, when the task asks for one), "
    "or 'next' (to advance one page). In data collection, type 'name <your "
    "name>'. The task's own options are shown beneath the question."
)


def _sanitize_name(raw: str) -> str:
    """Strip HTML tags and cap the length of a captured name."""
    clean = re.sub(r"<[^>]*>", "", raw).strip()
    return clean[:_MAX_NAME_LENGTH] if clean else raw[:_MAX_NAME_LENGTH]


def _parse_scores(text: str) -> Optional[list[int]]:
    """Parse ``a b c`` into three ints, each 1..5, else ``None``."""
    parts = text.split()
    if len(parts) != 3:
        return None
    try:
        scores = [int(part) for part in parts]
    except ValueError:
        return None
    if not all(1 <= score <= 5 for score in scores):
        return None
    return scores


def _phase_of(current: str, level: Optional[str] = None) -> str:
    """Coarse lifecycle phase for the Summary, from the transition row.

    Resolved through the row_for seam (spec #16 C1-1): a suffixed
    history name is self-describing, the session's registered level
    resolves any bare base name. The terminal ``end`` state has no row
    (the registry covers the non-terminal states only), so it falls
    back to ``"finished"``.
    """
    row = row_for(current, level)
    if row is not None:
        return row["phase"]
    return "finished" if current == "end" else ""


class TutorSession:
    """The session lifecycle as a deep module over a :class:`Storage` seam."""

    def __init__(self, storage: Storage, feedback: Feedback = default_feedback) -> None:
        self._storage = storage
        self._feedback = feedback
        self._state: Optional[State] = None

    # ------------------------------------------------------------------ API

    def start(self) -> Turn:
        """Begin a session and return the current turn.

        Idempotent: if a session already exists (in memory or on disk),
        its current turn is returned unchanged.
        """
        existing = self._load()
        if existing is not None:
            self._state = existing
            return self._make_turn(existing, existing.chat_history[-1], is_current=True)
        state = self._new_state()
        self._append_assistant_turn(state)
        self._storage.save(state)
        self._state = state
        return self._make_turn(state, state.chat_history[-1], is_current=True)

    def submit(self, text: str) -> Turn:
        """Feed one user input to the machine and return the new current turn."""
        state = self._require_state()
        text = (text or "")[:_MAX_INPUT_LENGTH]
        command = text.lower()
        row = row_for(state.current_state, state.user_data.get("level")) or {}

        if command == "back":
            self._go_back(state)
        elif command == "retry" and row.get("retryable"):
            self._retry(state)
        else:
            new_state, accepted = self._route(state, text)
            # Routing decides the flag: an input it drops is flagged as
            # unanswered so turns() can pair it with the row's rejection
            # copy (issue #15) — the view never infers rejection.
            self._append_user_turn(state, text, rejected=not accepted)
            if accepted and new_state is not None:
                state.current_state = new_state
                if new_state != "end":
                    self._append_assistant_turn(state)

        self._storage.save(state)
        current = state.chat_history[-1]
        return self._make_turn(
            state,
            current,
            is_current=True,
            rejection=self._rejection_copy(state, current),
        )

    def turns(self) -> list[Turn]:
        """The chat history; navigation options on the current turn only.

        Each assistant turn also carries ``used_value`` — the option the
        learner used to answer it, read from the user entry that follows
        (issue #14). A user turn whose input the routing dropped carries
        ``rejection`` — the row's own copy (issue #15).
        """
        state = self._require_state()
        history = state.chat_history
        return [
            self._make_turn(
                state,
                entry,
                is_current=index == len(history) - 1,
                used_value=self._used_value(
                    entry,
                    history[index + 1] if index + 1 < len(history) else None,
                    state.user_data.get("level"),
                ),
                rejection=self._rejection_copy(state, entry),
            )
            for index, entry in enumerate(history)
        ]

    def progress(self) -> Summary:
        """Every progress figure, derived from the canonical items model.

        Never raises: an untouched session answers with the zero-state
        Summary — rows all ``not_started``, counts zero, ``started`` False —
        instead of throwing. ``turns()`` and ``submit()`` keep their
        start-precondition (issue #14).
        """
        state = self._load()
        if state is None:
            return Summary(sections=self._sections({}))
        # A row saved before the ledger (ADR-0004's stranded row) has no
        # items: the never-raises promise above keeps the pages rendering
        # and the reset reachable — a KeyError here is a 500 per render.
        items = state.user_data.get("items", {})
        ud = state.user_data
        current = state.current_state

        completed = [key for key in STEP_KEYS if items.get(key) == "completed"]
        count = len(completed)
        percentage = int(count / TOTAL_STEPS * 100) if TOTAL_STEPS else 0

        return Summary(
            sections=self._sections(items),
            started=True,
            percentage=percentage,
            total_steps=TOTAL_STEPS,
            completed_steps_count=count,
            finished=_phase_of(current, ud.get("level")) == "finished",
            level=ud.get("level"),
            user_name=ud.get("user_name"),
            session_id=state.session_id,
        )

    def _sections(self, items: dict[str, str]) -> list[ProgressSection]:
        """Group the completion model into the sections the pages render.

        The module owns the section order and the heading wording; every row
        carries its own status, so a page renders a badge straight from the
        row and never re-derives status from a completed count — the two pages
        cannot disagree (issue #14, GLOSSARY "completion model"). Row keys are
        the completion-model item keys.
        """
        analysis_rows = [
            ProgressRow(key, ANALYSIS_LABELS[key], items.get(key, "not_started"))
            for key in ANALYSIS_STEP_KEYS
        ]
        role_rows = [
            ProgressRow(key, ROLE_LABELS[key], items.get(key, "not_started"))
            for key in ROLE_STEP_KEYS
        ]
        return [
            ProgressSection(
                "📝 Analysis Tasks",
                analysis_rows,
                sum(1 for row in analysis_rows if row.status == "completed"),
                len(analysis_rows),
            ),
            ProgressSection(
                "🎭 Communication Roles",
                role_rows,
                sum(1 for row in role_rows if row.status == "completed"),
                len(role_rows),
            ),
        ]

    def reset(self) -> None:
        """Clear the stored session."""
        self._storage.clear()
        self._state = None

    # ------------------------------------------------------------- lifecycle

    def _new_state(self) -> State:
        return State(
            session_id=uuid.uuid4().hex,
            current_state="start",
            user_data={
                "user_name": None,
                "level": None,
                "pretest_scores": None,
                "posttest_scores": None,
                "current_role": None,
                "current_role_variant": None,
                "items": {key: "not_started" for key in ITEM_KEYS},
            },
            scenario=randomize_scenario(SCENARIO),
            chat_history=[],
            retry_count=0,
        )

    def _require_state(self) -> State:
        if self._state is None:
            self._state = self._load()
        if self._state is None:
            raise RuntimeError("no active session — call start() first")
        return self._state

    def _load(self) -> Optional[State]:
        return self._storage.load()

    # --------------------------------------------------------------- routing

    def _route(self, state: State, text: str) -> tuple[Optional[str], bool]:
        """Route one input in the current state via the transition table.

        Returns ``(next_state, accepted)``; ``accepted`` False means the
        input was rejected for this state (the caller emits no transition).
        The row's ``accept`` is the single validation gate; ``next`` gives
        the target (a plain state, or a per-input mapping); ``effects``
        mutate the completion model / user data for the accepted input.
        """
        row = row_for(state.current_state, state.user_data.get("level"))
        if row is None:
            return None, False

        command = text.lower()
        accept = row.get("accept")
        if accept is not None:
            if isinstance(accept, str):
                if not re.fullmatch(accept, text):
                    return None, False
            elif command not in accept:
                return None, False

        next_spec = row.get("next")
        if next_spec is None:
            return None, False
        if isinstance(next_spec, dict):
            target = next_spec.get(command)
            if target is None:
                return None, False
        else:
            target = next_spec

        self._apply_effects(row, command, text, state)
        return target, True

    def _apply_effects(self, row: dict, command: str, text: str, state: State) -> None:
        """Apply the row's ``effects`` for the accepted input."""
        effects = row.get("effects")
        if not effects:
            return
        if isinstance(row.get("next"), dict):
            effects = effects.get(command)
        if not effects:
            return
        ud = state.user_data
        # An accepted input on a pre-ledger row writes the ledger on the
        # spot: no legacy key is renamed, so this is not a migration
        # (ADR-0004) — it just stops the effect from KeyErrors.
        items = ud.setdefault("items", {})
        for op, key, third in effects:
            if op == "set-item":
                items[key] = third
            elif op == "set-user-data":
                ud[key] = self._resolve_source(third, text)

    def _resolve_source(self, source: str, text: str) -> object:
        """Resolve an effect source to a concrete user-data value."""
        if source == "sanitized-name":
            tokens = text.split()
            return _sanitize_name(tokens[0] if tokens else text)
        if source == "parsed-scores":
            return _parse_scores(text)
        if source == "parsed-level":
            return _LEVEL_BY_VALUE.get(text)
        if source == "mapped-role":
            return ROLE_BY_VALUE.get(text)
        if source.startswith("literal:"):
            return source[len("literal:"):]
        return None

    def _go_back(self, state: State) -> None:
        state.retry_count = 0
        current = state.current_state
        back = (row_for(current, state.user_data.get("level")) or {}).get("back")
        if back is None:
            # ``start`` has no back target: a typed ``back`` there is an
            # unrecognized input — flagged, so the turn carries the row's
            # rejection copy (d5).
            self._append_user_turn(state, "back", rejected=True)
            return
        if back.startswith("after_registration_"):
            level = state.user_data.get("level") or "beginner"
            back = f"after_registration_{level}"
        # The typed ``back`` answers the current offer — mark it (synthesised
        # edge, no user entry follows; the stamp is the marking).
        if state.chat_history:
            state.chat_history[-1]["used_value"] = "back"
        state.current_state = back
        # The old handle_back re-appended the assistant turn even when the
        # state did not change (e.g. from after_registration_*).
        self._append_assistant_turn(state)

    def _retry(self, state: State) -> None:
        state.retry_count += 1
        message, failed = self._build_message(state)
        entry = state.chat_history[-1]
        entry["content"] = message
        entry["timestamp"] = datetime.now().isoformat()
        # ``retry`` answers the failed offer in place — mark it (no user
        # entry follows; the stamp is the marking).
        entry["used_value"] = "retry"
        entry["llm_failed"] = failed
        if not failed:
            state.retry_count = 0

    # -------------------------------------------------------------- messages

    def _scenario_entry(self, state: State, name: str) -> Optional[dict]:
        """The scenario entry for one state name — the construction point.

        Spec #16 C1-2 (ADR-0006): landing targets spell base names, so
        the scenario lookup joins the session's level onto a bare axis
        base (``"after_registration"`` + ``"beginner"`` →
        ``"after_registration_beginner"``). A suffix embedded in the
        name is self-describing and wins, as in :func:`row_for`.
        Returns ``None`` for an unknown state, like :meth:`dict.get`.
        """
        states = state.scenario["states"]
        data = states.get(name)
        if data is not None:
            return data
        base, embedded = split_state(name)
        if embedded is None:
            level = state.user_data.get("level")
            if level is not None:
                return states.get(join_state(base, level))
        return None

    def _scenario_state_data(self, state: State) -> Optional[dict]:
        """The scenario entry for the current state (see _scenario_entry)."""
        return self._scenario_entry(state, state.current_state)

    def _build_message(self, state: State) -> tuple[str, bool]:
        current = state.current_state
        ud = state.user_data
        state_data = self._scenario_state_data(state)
        if state_data is None:
            raise KeyError(current)
        message = state_data["message"]

        task_context: Optional[str] = None
        role_name: Optional[str] = None
        # The task-question lookup goes through the construction point too:
        # at a base state name (spec #16 C1-5) the sibling task is named by
        # base, and _scenario_entry joins the session's level onto it.
        if "analysis_feedback_1" in current:
            entry = self._scenario_entry(state, current.replace("feedback_1", "task_1"))
            if entry is not None:
                task_context = entry["message"]
        elif "analysis_feedback_2" in current:
            entry = self._scenario_entry(state, current.replace("feedback_2", "task_2"))
            if entry is not None:
                task_context = entry["message"]
        elif "roleplay_feedback" in current:
            role_name = current.replace("roleplay_feedback_", "")
            entry = self._scenario_entry(state, f"role_{role_name}")
            if entry is not None:
                task_context = entry["message"]

        history = state.chat_history
        user_answer = history[-1]["content"] if history else ""

        llm_failed = False
        if task_context and ud.get("user_name") and ud.get("level"):
            llm_output, llm_failed = self._feedback(
                user_name=ud["user_name"],
                level=ud["level"],
                role_name=role_name,
                user_answer=user_answer,
                task_question=task_context,
            )
            if llm_output:
                markers = _ROLEPLAY_MARKERS if "roleplay_feedback" in current else _ANALYSIS_MARKERS
                for marker in markers:
                    parts = message.split(marker, 1)
                    if len(parts) == 2:
                        header = parts[0].split("\n\n", 1)[0]
                        message = header + "\n\n" + llm_output + marker + parts[1]
                        break
                else:
                    message = message.split("\n\n", 1)[0] + "\n\n" + llm_output

        name = (ud.get("user_name") or "").strip()
        message = message.replace("{user_name}", name or _NAME_PLACEHOLDER)
        if "{level}" in message and ud.get("level"):
            message = message.replace("{level}", ud["level"])

        return message, llm_failed

    def _append_assistant_turn(self, state: State) -> None:
        state_data = self._scenario_state_data(state)
        if state_data is None:
            return
        message, llm_failed = self._build_message(state)
        options = state_data.get("options")
        state.chat_history.append(
            {
                "role": "assistant",
                "content": message,
                "state": state.current_state,
                "timestamp": datetime.now().isoformat(),
                "options": dict(options) if options else None,
                "llm_failed": llm_failed,
            }
        )

    def _append_user_turn(self, state: State, text: str, rejected: bool = False) -> None:
        entry = {
            "role": "user",
            "content": text,
            "state": state.current_state,
            "timestamp": datetime.now().isoformat(),
        }
        if rejected:
            # Routing dropped the input: flag it so the turn carries the
            # row's rejection copy (ADR-0005 d5).
            entry["rejected"] = True
        state.chat_history.append(entry)

    # ----------------------------------------------------------------- turns

    def _make_turn(
        self,
        state: State,
        entry: dict,
        is_current: bool,
        used_value: Optional[str] = None,
        rejection: Optional[str] = None,
    ) -> Turn:
        """Project a chat-history entry into a Turn for the views.

        Options carry their kind by routing origin (GLOSSARY "option kind",
        ADR-0005); on a clash the scenario label wins and the nav kind stays.
        ``used_value`` / ``rejection`` are paired by the caller — the caller
        knows the history adjacency; this method does not.
        """
        # Synthesised edges (back/retry) stamp the answered entry directly —
        # no user entry follows them, so the stamp is the marking.
        used_value = used_value or entry.get("used_value")
        options = entry.get("options")
        if entry.get("role") == "assistant" and (is_current or options):
            # One typed set for every rendered turn (ADR-0005): kind is
            # tested against the transition row at render time, so a
            # rendered answer keeps the routing origin that made it.
            nav_offers: dict[str, tuple[str, str]] = {}
            if is_current:
                # Nav offers first: the row's nav map plus the synthesised
                # back/retry edges; scenario options come after.
                nav_offers = dict(self._navigation_options(state, entry))
                nav_values = set(nav_offers)
            else:
                # The row's nav map and declared back/retry edges are the
                # values routing treats as navigation (ratified Q3).
                # History entries are self-describing: a suffixed name
                # resolves its own row; a bare base name — the
                # registration landing (spec #16 C1-2) — resolves with
                # the session's level, immutable after the pick (C1-3).
                nav_values = self._nav_values(
                    row_for(entry["state"], state.user_data.get("level")) or {}
                )
            merged: dict[str, tuple[str, str]] = dict(nav_offers)
            for value, label in (options or {}).items():
                # On a clash the scenario-defined label wins (presentation)
                # and the kind stays the nav offer's (routing origin).
                kind = (
                    nav_offers[value][1] if value in nav_offers
                    else "nav" if value in nav_values
                    else "choice"
                )
                merged[value] = (label, kind)
            # A content option whose step is in the ledger is completed —
            # the pages render the mark, they never compute it (issue #15).
            # Role options carry the ROLE_BY_VALUE value; map to ledger keys.
            offered_choices = {value for value, pair in merged.items() if pair[1] == "choice"}
            items = state.user_data.get("items", {})
            completed = {
                value
                for value in offered_choices
                if ROLE_BY_VALUE.get(value)
                and items.get(ROLE_BY_VALUE[value]) == "completed"
            }
            options = [
                TurnOption(value, label, kind)
                for value, (label, kind) in merged.items()
                if kind != "choice"
            ] + [
                TurnOption(value, label, "choice", value in completed)
                for value, (label, kind) in merged.items()
                if kind == "choice"
            ]
        return Turn(
            role=entry["role"],
            message=entry["content"],
            state=entry["state"],
            options=options,
            timestamp=entry["timestamp"],
            used_value=used_value,
            # An unanswered user entry carries its own rejection flag (d5):
            # submit() stamps it when routing drops the input; in turns()
            # the flag rides on the stored entry, so derive the copy there.
            rejection=rejection if rejection is not None else self._rejection_copy(state, entry),
        )

    def _rejection_copy(self, state: State, entry: dict) -> Optional[str]:
        """The row-owned copy for an unanswered, rejected user entry.

        The flag rides on the chat entry (``submit()`` sets it when routing
        drops the input). The row's ``rejected`` copy wins; rows that declare
        ``None`` get the module's generic fallback (ADR-0005, issue #15).
        The entry's state resolves through the seam: a suffixed name is
        self-describing, a bare base name (the registration landing,
        spec #16 C1-2) resolves with the session's level.
        """
        if entry.get("role") != "user" or not entry.get("rejected"):
            return None
        row = row_for(entry.get("state", ""), state.user_data.get("level"))
        if row is None:
            # The structural "no row" case (the ``end`` state after the
            # completion): no composer, so no banner copy (ADR-0005 d5).
            return None
        return row.get("rejected") if row.get("rejected") is not None else _GENERIC_REJECTION

    def _used_value(
        self, entry: dict, following: Optional[dict], level: Optional[str]
    ) -> Optional[str]:
        """The option value the learner used to answer this assistant entry.

        ``chat_history`` is a flat list, so the answer to an entry is the
        entry right after it. The value counts when it matches one of the
        scenario options stored on the entry, one of the transition row's
        ``nav`` values for the entry's state (navigation options are not
        stored on entries), or the synthesised edges — ``back`` (everywhere
        but ``start``) and ``retry`` on a failed LLM entry (issue #15).
        The entry's state resolves through the seam: a suffixed name is
        self-describing, a bare base name (the registration landing,
        spec #16 C1-2) resolves with the session ``level``.
        Free-text answers mark nothing; so does any turn with no user entry
        after it (the newest turn).
        """
        if entry.get("role") != "assistant" or following is None:
            return None
        if following.get("role") != "user":
            return None
        value = following.get("content")
        stored = entry.get("options")
        if stored and value in stored:
            return value
        nav = (row_for(entry.get("state", ""), level) or {}).get("nav", {})
        if value in nav:
            return value
        if value == "back" and entry.get("state") != "start":
            return value
        if value == "retry" and entry.get("llm_failed"):
            return value
        return None

    def _navigation_options(self, state: State, entry: dict) -> dict[str, tuple[str, str]]:
        """Navigation offers for the current assistant turn, with kinds.

        Every offer from the transition row's ``nav`` map and the synthesised
        ``back`` edge is kind ``nav`` (GLOSSARY "option kind" — the routing
        origin). On a failed LLM message the retry offer (kind ``retry``)
        replaces the advance options (up to 3 tries). ``back`` is absent at
        ``start`` — there is nothing to go back to on the welcome turn.
        """
        current = state.current_state
        row = row_for(current, state.user_data.get("level")) or {}
        if entry.get("llm_failed") and state.retry_count < 3:
            navigation: dict[str, tuple[str, str]] = {}
            if current != "start":
                navigation["back"] = (_BACK_LABEL, "nav")
            navigation["retry"] = (f"🔄 Retry LLM ({max(state.retry_count, 1)}/3)", "retry")
            return navigation
        navigation = {
            value: (label, "nav") for value, label in row.get("nav", {}).items()
        }
        if current != "start":
            navigation["back"] = (_BACK_LABEL, "nav")
        return navigation

    @staticmethod
    def _nav_values(row: dict) -> set[str]:
        """Returns the values the transition row treats as navigation.

        Its ``nav`` map plus a declared ``back`` edge — the values the
        current turn synthesises as nav offers; a scenario option is
        ``choice`` only when routing never treats it as navigation
        (ADR-0005 d2, ratified Q3). ``retry`` is not here: it is only
        ever synthesised for a failed LLM message, never stored.
        """
        values = set(row.get("nav", {}))
        if row.get("back") is not None:
            values.add("back")
        return values
