"""Regression tests for issue #745 D1 (WOfS band order) and D2 (BurstIL-as-IFD).

D1 (live-reproduced): the DEA WCS returns bands in an unstable order per
location. Positional reads turned a count value into a fake 100% flood
frequency on dry lots (Concord AND rural Dubbo), firing a false user-facing
flood constraint. Values below are the ACTUAL live probe values from the
audit — not synthetic.

D2 (live-reproduced): the ARR Data Hub endpoint never serves BOM IFD; the old
code consumed the BurstIL storm initial-loss table and labelled it as the
1% AEP 60-minute rainfall depth.
"""

import math
from unittest.mock import patch

import pytest

from services.flood_truth import _wofs_frequency_from_bands
from services.portal_constraints import fetch_arr_ifd


class TestWofsBandSelection:
    def test_concord_swapped_order_returns_true_frequency_not_100(self):
        # Live Concord response: band 3 was count_clear=635 — the old code
        # returned 100.0 for a bone-dry suburban lot.
        raw = _wofs_frequency_from_bands(
            ["count_wet", "frequency", "count_clear"],
            [0.0, 0.00039682540227659047, 635.0],
        )
        assert raw == pytest.approx(0.000396825, rel=1e-4)

    def test_documented_order_still_works(self):
        # Live Parramatta River response (order matched the docs).
        raw = _wofs_frequency_from_bands(
            ["count_wet", "count_clear", "frequency"],
            [4.0, 748.0, 0.005012961104512215],
        )
        assert raw == pytest.approx(0.005013, rel=1e-4)

    def test_dubbo_dry_point_swapped_order(self):
        # Live rural Dubbo response: genuinely dry, band 3 was count_clear=654.
        raw = _wofs_frequency_from_bands(
            ["count_wet", "frequency", "count_clear"],
            [0.0, 0.0, 654.0],
        )
        assert raw == 0.0  # dry means 0.0, not None and never 100

    def test_no_frequency_band_fails_closed_never_positional(self):
        # Missing/blank descriptions must NOT fall back to reading a position.
        assert _wofs_frequency_from_bands([], [0.0, 0.5, 654.0]) is None
        assert _wofs_frequency_from_bands(
            [None, None, None], [0.0, 0.5, 654.0]) is None
        assert _wofs_frequency_from_bands(
            ["count_wet", "count_clear", "band_3"], [0.0, 748.0, 0.5]) is None

    def test_out_of_range_value_fails_closed_not_clamped(self):
        # The old >1.0 clamp converted stray counts into "100%". A frequency
        # can never exceed 1.0 — out-of-range must return None, never a value.
        assert _wofs_frequency_from_bands(["frequency"], [635.0]) is None
        assert _wofs_frequency_from_bands(["frequency"], [1.0001]) is None
        assert _wofs_frequency_from_bands(["frequency"], [-0.1]) is None

    def test_nodata_and_nan_fail_closed(self):
        assert _wofs_frequency_from_bands(["frequency"], [-999.0]) is None
        assert _wofs_frequency_from_bands(["frequency"], [float("nan")]) is None

    def test_boundary_values_pass(self):
        assert _wofs_frequency_from_bands(["frequency"], [0.0]) == 0.0
        assert _wofs_frequency_from_bands(["frequency"], [1.0]) == 1.0

    def test_case_insensitive_band_name(self):
        assert _wofs_frequency_from_bands(
            ["Count_Wet", "FREQUENCY"], [3.0, 0.25]) == 0.25


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class TestArrIfdFailClosed:
    def test_burstil_only_payload_returns_none(self):
        # The live endpoint shape: BurstIL present, no IFD layer. The old code
        # served 6.8 mm from this table as the 1% AEP 60-min depth.
        payload = {"layers": {"BurstIL": {
            "index": [60, 90, 120],
            "columns": ["50", "20", "10", "5", "2", "1"],
            "data": [[1.2, 2.0, 3.1, 4.4, 5.6, 6.8],
                     [1.4, 2.2, 3.4, 4.8, 6.0, 7.2],
                     [1.5, 2.4, 3.7, 5.1, 6.4, 7.6]],
        }}}
        with patch("services.portal_constraints.requests.get",
                   return_value=_FakeResponse(payload)):
            assert fetch_arr_ifd(-33.8697, 151.103) is None

    def test_genuine_ifd_layer_is_served_with_sane_magnitude(self):
        # Future-proofing: if the hub ever serves a real IFD table, it flows
        # through — and the value magnitude is Sydney-plausible (mm depths).
        payload = {"layers": {
            "BurstIL": {"index": [60], "columns": ["1"], "data": [[6.8]]},
            "IFD": {"index": [30, 60, 120],
                    "columns": ["63.2", "10", "1"],
                    "data": [[30.1, 55.2, 78.9],
                             [38.4, 68.7, 96.3],
                             [47.2, 84.1, 118.0]]},
        }}
        with patch("services.portal_constraints.requests.get",
                   return_value=_FakeResponse(payload)):
            result = fetch_arr_ifd(-33.8697, 151.103)
        assert result is not None
        assert result["ifd_1pct_60min_mm"] == 96.3  # the IFD row, never BurstIL's 6.8

    def test_empty_layers_returns_none(self):
        with patch("services.portal_constraints.requests.get",
                   return_value=_FakeResponse({"layers": {}})):
            assert fetch_arr_ifd(-33.8697, 151.103) is None
