"""Tests for the UUID v7 helper minting the ledger's ``session_id``.

ADR-0007 decision 3 pins the id: canonical lowercase 36-character text,
version nibble 7, RFC 4122 variant, a 48-bit Unix-millisecond prefix that
tracks the wall clock, and monotonic ordering so a burst of ids sorts by
creation. Every assertion reads the id from the outside - through its text
form and ``uuid.UUID`` - not from any private helper.
"""

from __future__ import annotations

import re
import time
import uuid

from django.test import SimpleTestCase

from .ids import uuid7

CANONICAL_TEXT = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def _millisecond_prefix(text: str) -> int:
    """Return the leading 48 bits of an id: its Unix-ms timestamp field."""
    return int(text.replace("-", "")[:12], 16)


class Uuid7Tests(SimpleTestCase):
    """The id shape and ordering the ledger rows and export filenames use."""

    def test_id_is_canonical_lowercase_text(self) -> None:
        """A minted id is 36 lowercase hex characters with four dashes."""
        text = uuid7()
        self.assertEqual(len(text), 36)
        self.assertRegex(text, CANONICAL_TEXT)

    def test_id_reports_version_seven_and_rfc4122_variant(self) -> None:
        """Parses as a version-7 UUID of the RFC 4122 variant."""
        parsed = uuid.UUID(uuid7())
        self.assertEqual(parsed.version, 7)
        self.assertEqual(parsed.variant, uuid.RFC_4122)

    def test_id_prefix_tracks_the_wall_clock(self) -> None:
        """The 48-bit prefix is the generation time in Unix milliseconds."""
        before = int(time.time() * 1000)
        text = uuid7()
        after = int(time.time() * 1000)
        prefix = _millisecond_prefix(text)
        self.assertGreaterEqual(prefix, before)
        self.assertLessEqual(prefix, after)

    def test_ids_generated_in_a_burst_sort_in_generation_order(self) -> None:
        """A run of ids is strictly increasing, textually and numerically."""
        batch = [uuid7() for _ in range(500)]
        self.assertEqual(len(set(batch)), 500)
        self.assertEqual(batch, sorted(batch))
        numbers = [int(text.replace("-", ""), 16) for text in batch]
        self.assertEqual(numbers, sorted(numbers))

    def test_later_id_is_not_older_than_an_earlier_one(self) -> None:
        """Ordering survives a clock tick between two ids."""
        first = uuid7()
        time.sleep(0.002)
        second = uuid7()
        self.assertGreater(second, first)
        self.assertGreater(_millisecond_prefix(second), _millisecond_prefix(first))
