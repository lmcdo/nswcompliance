# prior-art-checked: no test of brief_templates condition cleaning existed; this is its twin of
# frontend-nextjs/__tests__/lib/dcp/public-condition.test.ts.
"""The paid report shows a stored condition the same way the page does (pilot audit 2026-11-10)."""
import pytest

from services.brief_templates import public_condition


@pytest.mark.parametrize("raw, shown", [
    ("NO FIGURE: 9 m low side / 12 m high side", "9 m low side / 12 m high side"),
    ("FSR-CONTROLLED: site coverage governed by Floor Space Ratio", "site coverage governed by Floor Space Ratio"),
    ("NO FIGURE: 9 m. NOT yet stored: numeric field pending", "9 m."),
    ("Tiers apply. Tiers >900m2 = 6.5m are NOT yet stored. Corner lots differ.", "Tiers apply. Corner lots differ."),
    ("NOTE: measured from the boundary", "NOTE: measured from the boundary"),
])
def test_internal_tags_and_notes_are_cut(raw, shown):
    assert public_condition(raw) == shown


@pytest.mark.parametrize("raw", [None, "", "NO FIGURE:", "NOT yet stored: everything"])
def test_nothing_left_is_empty(raw):
    assert public_condition(raw) == ""
