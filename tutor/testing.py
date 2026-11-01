"""Shared browser scaffolding for the ledger-facing tests (tickets #38, #39).

Named ``testing`` and not ``test_*`` so the discovery walk does not collect
it as a suite of its own: it holds no assertions, only the moves every
intake-and-chat test repeats - open the form, move the chat to a named
state, read the browser copy back.
"""

from __future__ import annotations

from .models import SessionRecord
from .session import SessionStorage

INTAKE = {"name": "Alice", "group": "Alpha", "level": "beginner"}
OTHER_INTAKE = {"name": "Bella", "group": "Beta crew", "level": "advanced"}


def open_intake(client, payload: dict = INTAKE) -> SessionRecord:
    """Submit the intake form, landing the chat page and its ledger row."""
    response = client.post("/", payload)
    assert response.status_code == 302, response.content[:200]
    return SessionRecord.objects.get(session_id=session_id(client))


def session_id(client) -> str:
    """The id the chat minted, read from the browser copy of the session."""
    return SessionStorage(client.session).load().session_id


def entries(client) -> list[dict]:
    """The chat history the browser copy holds, entry dicts and all."""
    return SessionStorage(client.session).load().chat_history


def state_of(client) -> str:
    """The state the chat is on, as the browser copy spells it."""
    return SessionStorage(client.session).load().current_state


def strand(client, state: str) -> None:
    """Move the chat to ``state`` without walking the graph to it.

    Saving the browser session object is what the middleware does at the end
    of every response; without that write the next request reads the old
    state back, and the answer lands on the state the chat was really on.
    """
    store = client.session
    record = SessionStorage(store).load()
    record.current_state = state
    SessionStorage(store).save(record)
    store.save()  # the object written, not a fresh one: the property mints a new store

