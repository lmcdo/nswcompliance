"""Unit tests for the lot-index validation harness pure helpers."""
from __future__ import annotations

from scripts.validate_lot_index import _classify, _drift_rate


class TestClassify:
    def test_exact_match(self):
        assert _classify(0.5, 0.5, 0.01) == "match"

    def test_match_within_tolerance(self):
        assert _classify(0.5, 0.505, 0.01) == "match"

    def test_mismatch_beyond_tolerance(self):
        assert _classify(0.5, 0.7, 0.01) == "mismatch"

    def test_height_stale_case(self):
        # the 9m-stored vs 53m-live drift the harness exists to catch
        assert _classify(9.0, 53.0, 0.5) == "mismatch"

    def test_both_null(self):
        assert _classify(None, None, 0.01) == "both_null"

    def test_live_only(self):
        # source has a value the index is missing → counts as drift
        assert _classify(None, 0.5, 0.01) == "live_only"

    def test_stored_only(self):
        assert _classify(0.5, None, 0.01) == "stored_only"


class TestDriftRate:
    def test_counts_mismatch_and_live_only(self):
        # (1 mismatch + 1 live_only) / (10 comparable, both_null excluded) = 0.2
        rate = _drift_rate({"match": 8, "mismatch": 1, "live_only": 1, "both_null": 5})
        assert rate == 0.2

    def test_both_null_excluded_from_denominator(self):
        assert _drift_rate({"both_null": 3}) == 0.0

    def test_all_match_zero_drift(self):
        assert _drift_rate({"match": 10}) == 0.0

    def test_stored_only_not_counted_as_drift(self):
        # stored_only (index has a value the point-query missed) is not drift here
        assert _drift_rate({"match": 9, "stored_only": 1}) == 0.0
