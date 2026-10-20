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


def _state_to_item(state: str) -> Optional[str]:
    """Map a scenario state to the canonical item it represents."""
    if state == "pretest":
        return "pretest"
    if state == "level_assessment":
        return "level_assessment"
    if state.startswith("analysis_intro_") or state.startswith(
        ("analysis_task_1", "analysis_feedback_1")
    ):
        return "analysis_task_1"
    if state.startswith(("analysis_task_2", "analysis_feedback_2")):
        return "analysis_task_2"
    if state.startswith("roleplay_feedback_"):
        return "role_" + state.replace("roleplay_feedback_", "")
    if state in ROLE_STEP_KEYS:
        return state
    if state == "reflection":
        return "reflection"
    if state == "posttest":
        return "posttest"
    return None


def _phase(state: str) -> str:
    """Coarse lifecycle phase for the Summary, derived from the state."""
    if state == "end":
        return "finished"
    if state in ("start", "pretest", "level_assessment") or state.startswith(
        "after_registration_"
    ):
        return "registration"
    if state.startswith("analysis_"):
        return "analysis"
    if (
        state in ("roleplay_intro", "role_menu")
        or state.startswith("roleplay_feedback_")
        or state in ROLE_STEP_KEYS
    ):
        return "roleplay"
    if state == "reflection":
        return "reflection"
    if state == "posttest":
        return "posttest"
    if state == "data_collection":
        return "data_collection"
    return ""


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
        item = _state_to_item(current)
        if item is not None and items.get(item) == "not_started":
            items[item] = "in_progress"
    state.user_data["items"] = items


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

        if command == "back":
            self._go_back(state)
        elif command == "retry" and self._is_feedback_state(state.current_state):
            self._retry(state)
        else:
            self._append_user_turn(state, text)
            if self._matches_validation(state, text):
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

        item = _state_to_item(current)
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
            phase=_phase(current),
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
            _migrate_items(state)
        return state

    # --------------------------------------------------------------- routing

    @staticmethod
    def _is_feedback_state(state: str) -> bool:
        return state.startswith(("analysis_feedback_", "roleplay_feedback_"))

    @staticmethod
    def _matches_validation(state: State, text: str) -> bool:
        """Scenario validation gate (the old process_input checked this too)."""
        pattern = state.scenario["states"].get(state.current_state, {}).get("validation")
        return not pattern or bool(re.fullmatch(pattern, text))

    def _route(self, state: State, text: str) -> tuple[Optional[str], bool]:
        """Route one input in the current state.

        Returns ``(next_state, accepted)``; ``accepted`` False means the
        input was rejected for this state (the caller emits no transition).
        """
        current = state.current_state
        ud = state.user_data
        items = state.user_data["items"]
        command = text.lower()
        level = ud.get("level")

        if current == "start":
            tokens = text.split()
            ud["user_name"] = _sanitize_name(tokens[0] if tokens else text)
            return "pretest", True

        if current in ("pretest", "posttest"):
            scores = _parse_scores(text)
            if scores is None:
                return None, False
            key = "pretest" if current == "pretest" else "posttest"
            ud[f"{key}_scores"] = scores
            items[key] = "completed"
            return ("level_assessment" if key == "pretest" else "data_collection"), True

        if current == "level_assessment":
            if text not in _LEVEL_BY_VALUE:
                return None, False
            ud["level"] = _LEVEL_BY_VALUE[text]
            items["level_assessment"] = "completed"
            return f"after_registration_{ud['level']}", True

        if current.startswith("after_registration_"):
            if level is None:
                return None, False
            if text == "1":
                items["mode_analysis"] = "completed"
                return f"analysis_intro_{level}", True
            if text == "2":
                items["mode_roleplay"] = "completed"
                return "roleplay_intro", True
            return None, False

        if current.startswith("analysis_intro_"):
            if command == "yes":
                items["analysis_task_1"] = "in_progress"
                return current.replace("intro", "task_1"), True
            return None, False

        if current.startswith("analysis_task_"):
            number = "1" if current.startswith("analysis_task_1") else "2"
            items[f"analysis_task_{number}"] = "completed"
            return current.replace("task", "feedback"), True

        if current.startswith("analysis_feedback_"):
            number = "1" if "feedback_1" in current else "2"
            if command != "next":
                return None, False
            items[f"analysis_task_{number}"] = "completed"
            if number == "1":
                items["analysis_task_2"] = "in_progress"
                return current.replace("feedback_1", "task_2"), True
            return "roleplay_intro", True

        if current == "roleplay_intro":
            if command == "continue":
                return "role_menu", True
            return None, False

        if current == "role_menu":
            if command == "finish":
                return "reflection", True
            if text in ROLE_BY_VALUE:
                role = ROLE_BY_VALUE[text]
                ud["current_role"] = role
                items[role] = "in_progress"
                return role, True
            return None, False

        if current.startswith("role_"):
            role = current
            if role not in ROLE_STEP_KEYS:
                return None, False
            # Completes only at roleplay_feedback next/back (old-app parity).
            return f"roleplay_feedback_{role.replace('role_', '')}", True

        if current.startswith("roleplay_feedback_"):
            role = ud.get("current_role") or "role_mediator"
            if command == "revise":
                items[role] = "in_progress"
                return role, True
            # "back" never reaches here: submit() routes it to _go_back first,
            # mirroring the old process_input global interception.
            if command == "next":
                items[role] = "completed"
                return "role_menu", True
            return None, False

        if current == "reflection":
            items["reflection"] = "completed"
            return "posttest", True

        if current == "data_collection":
            if command == "exit":
                return "end", True
            return None, False

        return None, False

    def _go_back(self, state: State) -> None:
        state.retry_count = 0
        current = state.current_state
        level = state.user_data.get("level") or "beginner"
        if current.startswith(("analysis_task_", "analysis_feedback_")):
            target = f"analysis_intro_{level}"
        elif current.startswith("analysis_intro_"):
            target = f"after_registration_{level}"
        elif current == "role_menu":
            target = "roleplay_intro"
        elif current == "roleplay_intro":
            target = f"after_registration_{level}"
        elif current.startswith("roleplay_feedback_"):
            target = "role_menu"
        else:
            target = f"after_registration_{level}"
        # The old handle_back re-appended the assistant turn even when the
        # state did not change (e.g. from after_registration_*).
        state.current_state = target
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

        if ud.get("user_name"):
            message = message.replace("{user_name}", ud["user_name"])
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
        tries); ``finish`` appears on the role menu. Scenario-defined
        options win on clashes.
        """
        navigation: dict[str, str] = {}
        current = state.current_state
        if current != "start":
            navigation["back"] = _BACK_LABEL
        if entry.get("llm_failed") and state.retry_count < 3:
            navigation["retry"] = f"🔄 Retry LLM ({max(state.retry_count, 1)}/3)"
        else:
            if self._is_feedback_state(current):
                navigation["next"] = "Next"
            elif current == "roleplay_intro":
                navigation["continue"] = "Continue"
            elif current.startswith("analysis_intro_"):
                navigation["yes"] = "Yes"
            elif current == "data_collection":
                navigation["exit"] = "Exit"
        if current == "role_menu":
            navigation["finish"] = "Finish roles"
        return navigation
