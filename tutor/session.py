"""Storage seam, session-state value types, and LLM injection for the tutor.

This module lays down the prefactor deliverables for issue #2 so that the
``TutorSession`` module (issue #3) can stand on a single seam instead of
reaching into the Django session and the LLM service directly:

- :class:`State` -- everything a session persists.
- :class:`Turn` -- one speaker turn in the chat history.
- :class:`Summary` -- the derived presentation view the menu and export views
  will read instead of recomputing progress themselves.
- :class:`Storage` -- a small ``load`` / ``save`` / ``clear`` seam, with an
  in-memory :class:`MemoryStorage` (tests) and a :class:`SessionStorage`
  (production) adapter.
- :class:`Feedback` -- the injectable ``feedback(...)`` callable whose default
  is the existing :func:`tutor.llm.get_llm_feedback`.

Nothing here changes existing behavior: the current views
keep running exactly as before. This only introduces the types and seam the
next module will depend on.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, fields
from typing import Any, Optional, Protocol, runtime_checkable

from .llm import get_llm_feedback

# ---------------------------------------------------------------------------
# Session-state value types
# ---------------------------------------------------------------------------


@dataclass
class State:
    """Everything a tutor session persists.

    The fields mirror the keys the Django session currently holds, so the
    storage adapters can round-trip a ``State`` without changing the on-wire
    format the existing views read.
    """

    session_id: str
    current_state: str
    user_data: dict[str, Any]
    scenario: dict[str, Any]
    chat_history: list[dict[str, Any]]
    retry_count: int = 0


@dataclass
class Turn:
    """One speaker turn in the chat history.

    ``options`` carries the option map for assistant turns and is ``None``
    for user turns. ``state`` is the state key the turn was produced in.
    """

    role: str
    message: str
    state: str
    options: Optional[dict[str, str]]
    timestamp: str


@dataclass
class Summary:
    """Derived presentation view the menu and export views will read.

    Carries the progress metrics and completion data the views currently
    recompute, so ``TutorSession.progress()`` (issue #3) can return it and the
    views stop branching on ``current_state``. Defaults describe an untouched
    session.
    """

    # Progress metrics.
    status_badge: str = "not_started"
    percentage: int = 0
    current_step: int = 0
    total_steps: int = 15
    completed_steps_count: int = 0
    analysis_progress: dict[str, Any] = field(default_factory=dict)
    roleplay_progress: dict[str, Any] = field(default_factory=dict)
    # Completion / presentation data the views read.
    completed_option_values: list[str] = field(default_factory=list)
    completed_roles: list[str] = field(default_factory=list)
    completed_modes: list[str] = field(default_factory=list)
    analysis_tasks: list[tuple[str, str]] = field(default_factory=list)
    role_tasks: list[tuple[str, str]] = field(default_factory=list)
    opened_tasks: list[str] = field(default_factory=list)
    # Context.
    level: Optional[str] = None
    phase: str = ""
    # Identity (the chat sidebar and export link need these; the module is the
    # only place that knows them, so the Summary carries them out).
    user_name: Optional[str] = None
    session_id: str = ""


# ---------------------------------------------------------------------------
# Storage seam
# ---------------------------------------------------------------------------

# The session keys a State maps onto. Keeping them in one place is what makes
# the Django adapter behavior-neutral: it writes exactly the keys the current
# views already read.
_SESSION_KEYS = [f.name for f in fields(State)]

# Per-key defaults the adapters fall back to when a stored session is
# incomplete. ``current_state`` is the marker of an initialized session; load()
# returns None without it, so its default is never actually used.
_KEY_DEFAULTS: dict[str, Any] = {
    "session_id": "",
    "current_state": None,
    "user_data": {},
    "scenario": {},
    "chat_history": [],
    "retry_count": 0,
}


@runtime_checkable
class Storage(Protocol):
    """Small seam the module depends on instead of a concrete backend."""

    def load(self) -> Optional[State]:
        """Return the stored :class:`State`, or ``None`` if there is none."""
        ...

    def save(self, state: State) -> None:
        """Persist the given :class:`State`."""
        ...

    def clear(self) -> None:
        """Remove the stored :class:`State`."""
        ...


class MemoryStorage:
    """In-memory adapter backed by a plain dict (one session per instance).

    Stores each :class:`State` field under its name and deep-copies at the
    save/load boundary, so a round trip reads back an equal but independent
    copy, mirroring how a real backend serializes state and keeping a saved
    copy insulated from later mutation of the original.
    """

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def load(self) -> Optional[State]:
        if "current_state" not in self._data:
            return None
        return State(
            **{
                name: copy.deepcopy(self._data.get(name, _KEY_DEFAULTS[name]))
                for name in _SESSION_KEYS
            }
        )

    def save(self, state: State) -> None:
        self._data = {name: copy.deepcopy(getattr(state, name)) for name in _SESSION_KEYS}

    def clear(self) -> None:
        self._data = {}


class SessionStorage:
    """Production adapter backed by a Django session object.

    Named ``SessionStorage`` to match ADR-0001. Maps :class:`State` fields onto
    the same per-key session format the existing code uses, so routing a
    session through the seam changes nothing about the format the current
    views read.
    Assigning each key marks the session modified, so no dirtiness handling is
    needed.
    """

    def __init__(self, session: Any) -> None:
        self._session = session

    def load(self) -> Optional[State]:
        s = self._session
        # ``current_state`` is the marker of an initialized session.
        if "current_state" not in s:
            return None
        return State(**{name: s.get(name, _KEY_DEFAULTS[name]) for name in _SESSION_KEYS})

    def save(self, state: State) -> None:
        for name in _SESSION_KEYS:
            self._session[name] = getattr(state, name)

    def clear(self) -> None:
        for name in _SESSION_KEYS:
            self._session.pop(name, None)


# ---------------------------------------------------------------------------
# LLM injection seam
# ---------------------------------------------------------------------------


@runtime_checkable
class Feedback(Protocol):
    """The injectable ``feedback(...)`` callable the module uses for LLM
    feedback.

    The signature matches :func:`tutor.llm.get_llm_feedback` exactly, so the
    existing service is a valid default and a deterministic fake can stand in
    for tests without any network call. Returns ``(feedback_text, failed)``.
    """

    def __call__(
        self,
        user_answer: str,
        role_name: Optional[str],
        user_name: str,
        level: str,
        task_question: Optional[str] = None,
    ) -> tuple[str, bool]:
        ...


#: Default feedback dependency -- the existing LLM feedback service.
default_feedback: Feedback = get_llm_feedback
