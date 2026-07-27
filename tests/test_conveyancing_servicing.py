"""Golden-sentence tests for the Sydney Water GSP servicing risk row.

Three-state contract (services/gsp_servicing.fetch_gsp_servicing →
scripts/generate_conveyancing_report.build_servicing_row):

  {"status": "found", "data": {"ww":..,"dw":..}} → in a growth-servicing area
  {"status": "empty"}   → NOT in a GSP precinct — established-suburb gap ("note",
                          never "clear"; capacity is a Section 73 question)
  {"status": "failed"} / None / junk → "Not assessed" ("note"), never a clear result

Break-it guarded: a failed or out-of-precinct lookup must never read as
"serviceable"/"clear" in a conveyancer document, and the DSP figure must be
presented as a CPI-excluded base charge with Sydney Water attribution + link.
Pure-logic: no DB, no reportlab.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT / "services"))
sys.path.insert(0, str(_ROOT))

from generate_conveyancing_report import build_servicing_row  # noqa: E402
from gsp_servicing import GSP_SOURCE, GSP_URL  # noqa: E402

_WW = {"status_code": "IN_DELIVERY", "constrained": False, "timeframe": "FY26",
       "dsp_price_per_et": 17686.52, "growth_area": "South West Growth Area"}
_DW = {"status_code": "PLANNED", "constrained": False, "timeframe": "FY 28 - FY30",
       "dsp_price_per_et": 3623.16, "growth_area": "South West Growth Area"}


class TestServicingFound:
    def test_found_lists_both_products_and_area(self):
        text, style, source = build_servicing_row(
            {"status": "found", "data": {"ww": _WW, "dw": _DW}})
        assert "South West Growth Area" in text
        assert "Wastewater" in text and "drinking water" in text
        assert "trunk servicing in delivery" in text
        assert style in ("note", "warn")
        assert source == GSP_SOURCE

    def test_found_shows_dsp_as_base_charge(self):
        text, _, _ = build_servicing_row(
            {"status": "found", "data": {"ww": _WW, "dw": None}})
        assert "base DSP" in text
        assert "17,687" in text or "17,686" in text  # rounded base figure present
        assert "exclude CPI" in text  # never presented as the live charge

    def test_found_never_claims_serviceable_or_ready(self):
        text, _, _ = build_servicing_row(
            {"status": "found", "data": {"ww": _WW, "dw": _DW}})
        low = text.lower()
        assert "serviceable" not in low
        assert "does not make a site service-ready" in low  # the honest caveat

    def test_constrained_sets_warn_and_states_constraint(self):
        ww = {**_WW, "constrained": True}
        text, style, _ = build_servicing_row(
            {"status": "found", "data": {"ww": ww, "dw": _DW}})
        assert style == "warn"
        assert "capacity and timescale constraints" in text

    def test_unconstrained_is_note(self):
        _, style, _ = build_servicing_row(
            {"status": "found", "data": {"ww": _WW, "dw": _DW}})
        assert style == "note"

    def test_no_timeframe_noted_is_suppressed(self):
        ww = {**_WW, "timeframe": "No timeframe noted."}
        text, _, _ = build_servicing_row(
            {"status": "found", "data": {"ww": ww, "dw": None}})
        assert "No timeframe noted" not in text

    def test_missing_price_omits_dsp_phrase(self):
        ww = {**_WW, "dsp_price_per_et": None}
        text, _, _ = build_servicing_row(
            {"status": "found", "data": {"ww": ww, "dw": None}})
        assert "base DSP" not in text


class TestServicingEmpty:
    def test_empty_points_to_section_73_not_clear(self):
        text, style, source = build_servicing_row({"status": "empty"})
        assert style == "note"
        assert "Section 73" in text
        assert "clear" not in text.lower()  # out-of-precinct is NOT a clear result
        assert source == GSP_SOURCE


class TestServicingNotAssessed:
    def test_failed_is_not_assessed(self):
        text, style, _ = build_servicing_row({"status": "failed"})
        assert "Not assessed" in text
        assert style == "note"

    def test_none_is_not_assessed(self):
        text, _, _ = build_servicing_row(None)
        assert "Not assessed" in text

    def test_junk_status_is_not_assessed(self):
        text, _, _ = build_servicing_row({"status": "banana"})
        assert "Not assessed" in text


class TestServicingAttribution:
    def test_all_states_attribute_sydney_water(self):
        for payload in ({"status": "found", "data": {"ww": _WW, "dw": _DW}},
                        {"status": "empty"}, {"status": "failed"}, None):
            _, _, source = build_servicing_row(payload)
            assert source == GSP_SOURCE
            assert "Sydney Water" in source

    def test_link_constant_is_the_gsp_page(self):
        assert GSP_URL.startswith("https://www.sydneywater.com.au/")
        assert "growth-servicing-plan" in GSP_URL
