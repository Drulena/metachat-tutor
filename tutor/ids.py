"""UUID version 7 minting for the session ledger's ``session_id``.

Python 3.11 has no ``uuid.uuid7`` - it lands in 3.14 - so this module
assembles the layout ADR-0007 decision 3 asks for: 48 bits of Unix
milliseconds, the version and variant nibbles, and 74 bits of randomness
carrying a per-millisecond counter so a burst of ids is strictly
increasing. Ids come back as canonical lowercase 36-character text, the
shape the ledger column, the export filenames and the chat pages carry.
"""

from __future__ import annotations

import threading
import time
import uuid

__all__ = ["uuid7"]

_MILLISECOND_BITS = 48
_MILLISECOND_MASK = (1 << _MILLISECOND_BITS) - 1
_LOW_BITS = 74  # rand_a (12) + rand_b (62): everything below the version nibble
_LOW_MASK = (1 << _LOW_BITS) - 1
_RAND_A_SHIFT = 62
_COUNTER_BITS = 12
_COUNTER_MASK = (1 << _COUNTER_BITS) - 1

_lock = threading.Lock()
_last_millisecond = 0
_last_low = 0


def _random_low() -> int:
    """Return 74 random bits, split the way a v7 lays them out."""
    return uuid.uuid4().int & _LOW_MASK


def _next_millisecond() -> tuple[int, int]:
    """Return the millisecond and low bits for the next id, never repeating one.

    Within a millisecond the low bits count up, so ids minted in the same
    millisecond - and ids minted while the clock has not advanced - stay in
    generation order. Running out of counter steps moves to the next
    millisecond rather than wrapping.
    """
    global _last_millisecond, _last_low

    millisecond = int(time.time() * 1000) & _MILLISECOND_MASK
    if millisecond <= _last_millisecond:
        millisecond = _last_millisecond
        low = _last_low + 1
        if low >> _LOW_BITS:  # the counter stepped past the 74 random bits
            millisecond += 1
            low = _random_low()
    else:
        low = _random_low()

    _last_millisecond = millisecond
    _last_low = low
    return millisecond, low


def _to_text(millisecond: int, low: int) -> str:
    """Assemble the v7 bit layout and render it as canonical UUID text."""
    rand_a = (low >> _RAND_A_SHIFT) & _COUNTER_MASK
    rand_b = low & ((1 << _RAND_A_SHIFT) - 1)
    value = (
        (millisecond << 80)
        | 0x7 << 76  # version nibble
        | rand_a << 64
        | 0b10 << 62  # RFC 4122 variant
        | rand_b
    )
    return str(uuid.UUID(int=value))


def uuid7() -> str:
    """Return a fresh UUID version 7 as canonical 36-character text."""
    with _lock:
        millisecond, low = _next_millisecond()
    return _to_text(millisecond, low)
