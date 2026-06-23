"""Hard, OFFLINE gate over what the insert scripts would write.

Closes the "runs only periodically" gap: this runs in normal pytest (no DB), so
every commit is checked. It rebuilds the exact value each insert script would
write (NULL for unverified rows) and runs the write-time gate over it — so a
future edit that adds a guessed value to POS_ROWS / SOLAR_ROWS, or breaks the
NULL-for-unverified logic, fails the build immediately.
"""

from scripts.insert_private_open_space import POS_ROWS
from scripts.insert_solar_access_hours import SOLAR_ROWS
from services.extracted_data_integrity import assert_clean_row


def _effective(row):
    """Mirror the insert scripts: unverified rows store NULL, not the value."""
    return None if row["needs_review"] else row["value_min"]


def test_pos_rows_would_insert_clean():
    for r in POS_ROWS:
        assert_clean_row(
            {"value_min": _effective(r), "condition": r["condition"], "source_text": r["source_text"]},
            value_field="value_min", marker_fields=["condition", "source_text"],
        )


def test_solar_rows_would_insert_clean():
    for r in SOLAR_ROWS:
        assert_clean_row(
            {"value_min": _effective(r), "condition": r["condition"], "source_text": r["source_text"]},
            value_field="value_min", marker_fields=["condition", "source_text"],
        )


def test_gate_would_catch_a_regression():
    # If someone added a verified row whose value is actually a guess, the gate fires.
    bad = {"value_min": 24, "condition": "Assumed standard NSW POS min — verify", "source_text": ""}
    import pytest
    with pytest.raises(ValueError):
        assert_clean_row(bad, value_field="value_min", marker_fields=["condition", "source_text"])
