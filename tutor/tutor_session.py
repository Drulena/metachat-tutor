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
view shows (percentage, step counters, task lists, completed value sets)
is derived from that single model. Legacy states saved before this module
(parallel ``completed_*`` / ``opened_tasks`` lists) are migrated to the
items model on load.
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
    State,
    Storage,
    Summary,
    Turn,
    default_feedback,
)
from .transitions import TRANSITIONS

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


def _phase_of(current: str) -> str:
    """Coarse lifecycle phase for the Summary, from the transition row.

    The terminal ``end`` state has no row (the table covers the
    non-terminal states only), so it falls back to ``"finished"``.
    """
    row = TRANSITIONS.get(current)
    if row is not None:
        return row["phase"]
    return "finished" if current == "end" else ""


def _migrate_items(state: State) -> None:
    """Build the canonical items model from a legacy state's parallel lists.

    Legacy states (created before this module) carry completion as three
    separate lists; ``opened_tasks`` doubles as the in-progress signal.
    """
    if "items" in state.user_data:
        return
    items = {key: "not_started" for key in ITEM_KEYS}
    for key in set(state.user_data.get("completed_steps", [])) | set(
        state.user_data.get("completed_roles", [])
    ):
        if key in items:
            items[key] = "completed"
    for slug in state.user_data.get("completed_tasks", []):
        base = "_".join(slug.split("_")[:3]) if slug.startswith("analysis_task_") else slug
        if base in items:
            items[base] = "completed"
    if "analysis" in state.user_data.get("completed_modes", []):
        items["mode_analysis"] = "completed"
    if "roleplay" in state.user_data.get("completed_modes", []):
        items["mode_roleplay"] = "completed"
    for slug in state.user_data.get("opened_tasks", []):
        base = "_".join(slug.split("_")[:3]) if slug.startswith("analysis_task_") else slug
        if base in items and items[base] != "completed":
            items[base] = "in_progress"
    current = state.current_state
    if current.startswith(("analysis_task_", "roleplay_feedback_")) or current in ROLE_STEP_KEYS:
        item = TRANSITIONS.get(current, {}).get("item")
        if item is not None and items.get(item) == "not_started":
            items[item] = "in_progress"
    state.user_data["items"] = items


#: State keys renamed after sessions had already stored them. A session left
#: in flight at a retired key finds no transition row and no scenario state,
#: so every input is rejected and the learner is stuck on a stale turn; the
#: key is rewritten on load instead.
LEGACY_STATE_KEYS = {
    "roleplay_feedback_idea": "roleplay_feedback_idea_generator",
}


def _migrate_state_key(state: State) -> None:
    """Rewrite a stored retired state key to its normalized successor (issue #12)."""
    target = LEGACY_STATE_KEYS.get(state.current_state)
    if target is not None:
        state.current_state = target


def _task_slug(key: str, level: Optional[str]) -> str:
    """The legacy task slug for a canonical item ("" if not expressible)."""
    if key.startswith("analysis_task_"):
        return f"{key}_{level}" if level else ""
    if key in ROLE_STEP_KEYS:
        return key
    return ""


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
        row = TRANSITIONS.get(state.current_state, {})

        if command == "back":
            self._go_back(state)
        elif command == "retry" and row.get("retryable"):
            self._retry(state)
        else:
            self._append_user_turn(state, text)
            new_state, accepted = self._route(state, text)
            if accepted and new_state is not None:
                state.current_state = new_state
                if new_state != "end":
                    self._append_assistant_turn(state)

        self._storage.save(state)
        return self._make_turn(state, state.chat_history[-1], is_current=True)

    def turns(self) -> list[Turn]:
        """The chat history; navigation options on the current turn only."""
        state = self._require_state()
        history = state.chat_history
        return [
            self._make_turn(state, entry, is_current=index == len(history) - 1)
            for index, entry in enumerate(history)
        ]

    def progress(self) -> Summary:
        """Every progress figure, derived from the canonical items model."""
        state = self._require_state()
        items = state.user_data["items"]
        ud = state.user_data
        current = state.current_state

        completed = [key for key in STEP_KEYS if items.get(key) == "completed"]
        count = len(completed)
        percentage = int(count / TOTAL_STEPS * 100) if TOTAL_STEPS else 0
        badge = "not_started" if count == 0 else ("completed" if count == TOTAL_STEPS else "in_progress")

        item = TRANSITIONS.get(current, {}).get("item")
        current_step = STEP_KEYS.index(item) + 1 if item in STEP_KEYS else 0

        analysis_done = sum(1 for key in ANALYSIS_STEP_KEYS if items.get(key) == "completed")
        roleplay_done = sum(1 for key in ROLE_STEP_KEYS if items.get(key) == "completed")

        completed_option_values: list[str] = []
        if current == "role_menu":
            completed_option_values = [
                value
                for value in ROLE_BY_VALUE
                if items.get(ROLE_BY_VALUE[value]) == "completed"
            ]
        elif current.startswith("after_registration_"):
            if items.get("mode_analysis") == "completed":
                completed_option_values.append("1")
            if items.get("mode_roleplay") == "completed":
                completed_option_values.append("2")
        elif current == "level_assessment" and ud.get("level"):
            completed_option_values.append(_LEVEL_BY_NAME.get(ud["level"], ""))

        level = ud.get("level")
        opened = [
            slug
            for key in ITEM_KEYS
            if items.get(key) == "in_progress" and (slug := _task_slug(key, level))
        ]

        return Summary(
            status_badge=badge,
            percentage=percentage,
            current_step=current_step,
            total_steps=TOTAL_STEPS,
            completed_steps_count=count,
            analysis_progress={
                "completed": analysis_done,
                "total": len(ANALYSIS_STEP_KEYS),
                "percentage": int(analysis_done / len(ANALYSIS_STEP_KEYS) * 100),
            },
            roleplay_progress={
                "completed": roleplay_done,
                "total": len(ROLE_STEP_KEYS),
                "percentage": int(roleplay_done / len(ROLE_STEP_KEYS) * 100),
            },
            completed_option_values=completed_option_values,
            completed_roles=[key for key in ROLE_STEP_KEYS if items.get(key) == "completed"],
            completed_modes=[
                name
                for name, key in (("analysis", "mode_analysis"), ("roleplay", "mode_roleplay"))
                if items.get(key) == "completed"
            ],
            analysis_tasks=[(key, ANALYSIS_LABELS[key]) for key in ANALYSIS_STEP_KEYS],
            role_tasks=[(key, ROLE_LABELS[key]) for key in ROLE_STEP_KEYS],
            opened_tasks=opened,
            level=level,
            phase=_phase_of(current),
            user_name=ud.get("user_name"),
            session_id=state.session_id,
        )

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
        state = self._storage.load()
        if state is not None:
            _migrate_state_key(state)
            _migrate_items(state)
        return state

    # --------------------------------------------------------------- routing

    def _route(self, state: State, text: str) -> tuple[Optional[str], bool]:
        """Route one input in the current state via the transition table.

        Returns ``(next_state, accepted)``; ``accepted`` False means the
        input was rejected for this state (the caller emits no transition).
        The row's ``accept`` is the single validation gate; ``next`` gives
        the target (a plain state, or a per-input mapping); ``effects``
        mutate the completion model / user data for the accepted input.
        """
        row = TRANSITIONS.get(state.current_state)
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
        items = ud["items"]
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
        back = TRANSITIONS.get(current, {}).get("back")
        if back is None:
            # ``start`` has no back target: a typed ``back`` there is an
            # unrecognized input (user turn only, no transition).
            self._append_user_turn(state, "back")
            return
        if back.startswith("after_registration_"):
            level = state.user_data.get("level") or "beginner"
            back = f"after_registration_{level}"
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
        entry["llm_failed"] = failed
        if not failed:
            state.retry_count = 0

    # -------------------------------------------------------------- messages

    def _build_message(self, state: State) -> tuple[str, bool]:
        scenario = state.scenario
        current = state.current_state
        ud = state.user_data
        state_data = scenario["states"][current]
        message = state_data["message"]

        task_context: Optional[str] = None
        role_name: Optional[str] = None
        if "analysis_feedback_1" in current:
            task_state = current.replace("feedback_1", "task_1")
            if task_state in scenario["states"]:
                task_context = scenario["states"][task_state]["message"]
        elif "analysis_feedback_2" in current:
            task_state = current.replace("feedback_2", "task_2")
            if task_state in scenario["states"]:
                task_context = scenario["states"][task_state]["message"]
        elif "roleplay_feedback" in current:
            role_name = current.replace("roleplay_feedback_", "")
            task_state = f"role_{role_name}"
            if task_state in scenario["states"]:
                task_context = scenario["states"][task_state]["message"]

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
        state_data = state.scenario["states"].get(state.current_state)
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

    def _append_user_turn(self, state: State, text: str) -> None:
        state.chat_history.append(
            {
                "role": "user",
                "content": text,
                "state": state.current_state,
                "timestamp": datetime.now().isoformat(),
            }
        )

    # ----------------------------------------------------------------- turns

    def _make_turn(self, state: State, entry: dict, is_current: bool) -> Turn:
        options = entry.get("options")
        if is_current and entry.get("role") == "assistant":
            navigation = self._navigation_options(state, entry)
            options = {**navigation, **(options or {})}
        return Turn(
            role=entry["role"],
            message=entry["content"],
            state=entry["state"],
            options=options,
            timestamp=entry["timestamp"],
        )

    def _navigation_options(self, state: State, entry: dict) -> dict[str, str]:
        """Navigation options for the current assistant turn only.

        ``back`` is available in every state except ``start`` (there is
        nothing to go back to on the welcome turn). On a failed LLM
        message the retry option replaces the advance option (up to 3
        tries). Advance/finish options come from the transition row's
        ``nav``; scenario-defined options win on clashes.
        """
        current = state.current_state
        row = TRANSITIONS.get(current, {})
        if entry.get("llm_failed") and state.retry_count < 3:
            navigation: dict[str, str] = {}
            if current != "start":
                navigation["back"] = _BACK_LABEL
            navigation["retry"] = f"🔄 Retry LLM ({max(state.retry_count, 1)}/3)"
            return navigation
        navigation = dict(row.get("nav", {}))
        if current != "start":
            navigation["back"] = _BACK_LABEL
        return navigation
