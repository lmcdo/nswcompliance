"""
Unit tests for services/bushfire_prescreen.py.

Pure-logic functions only — no DB, no network calls.

Covers:
  _is_in_nsw           — bounding box acceptance/rejection
  _BAL_LOOKUP          — all 4 vegetation categories
  _FIRE_SIGNAL_MAP     — all 4 vegetation categories
  _build_compliance    — state legislation, CDC pathway, 10/50 clearing, heritage exceptions
  _compute_confidence  — 3 tiers
  _build_data_sources  — conditional source list
  _query_rfs_bfpl      — out-of-NSW returns null (via _is_in_nsw)
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.bushfire_prescreen import (
    _is_in_nsw,
    _BAL_LOOKUP,
    _FIRE_SIGNAL_MAP,
    _build_compliance,
    _compute_confidence,
    _build_data_sources,
    _DATA_SOURCE_RFS,
    _DATA_SOURCE_SPATIAL,
    _S414_TRIGGERS,
    _NSW_BBOX,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rfs_result(**kwargs) -> dict:
    """Build a minimal RFS result dict."""
    base = {
        "is_bushfire_prone": None,
        "designation_source": None,
        "designation_category": None,
        "designation_guideline": None,
        "estimated_bal_band": None,
        "bal_assessment_likely_required": None,
        "fire_signal": "unavailable",
        "data_currency": "unknown",
    }
    base.update(kwargs)
    return base


def _prone_rfs(category="Vegetation Category 2", bal="BAL-29", signal="moderate"):
    return _rfs_result(
        is_bushfire_prone=True,
        designation_source=_DATA_SOURCE_RFS,
        designation_category=category,
        estimated_bal_band=bal,
        bal_assessment_likely_required=True,
        fire_signal=signal,
        data_currency="2026-05-01",
    )


def _not_prone_rfs():
    return _rfs_result(
        is_bushfire_prone=False,
        estimated_bal_band="BAL-LOW",
        bal_assessment_likely_required=False,
        fire_signal="none",
        data_currency="2026-05-01",
    )


# ---------------------------------------------------------------------------
# _is_in_nsw — bounding box
# ---------------------------------------------------------------------------

class TestIsInNSW:
    def test_sydney_cbd(self):
        assert _is_in_nsw(-33.8688, 151.2093) is True

    def test_blue_mountains(self):
        assert _is_in_nsw(-33.7150, 150.3120) is True

    def test_broken_hill_edge(self):
        """Broken Hill is ~141.45 lng — inside NSW bbox."""
        assert _is_in_nsw(-31.9505, 141.45) is True

    def test_melbourne_rejected(self):
        assert _is_in_nsw(-37.8136, 144.9631) is False

    def test_brisbane_rejected(self):
        assert _is_in_nsw(-27.4698, 153.0251) is False

    def test_perth_rejected(self):
        assert _is_in_nsw(-31.9505, 115.8605) is False

    def test_adelaide_rejected(self):
        assert _is_in_nsw(-34.9285, 138.6007) is False

    def test_bbox_min_corner(self):
        """Exact min corner of NSW bbox should be inside."""
        assert _is_in_nsw(_NSW_BBOX["min_lat"], _NSW_BBOX["min_lng"]) is True

    def test_bbox_max_corner(self):
        assert _is_in_nsw(_NSW_BBOX["max_lat"], _NSW_BBOX["max_lng"]) is True


# ---------------------------------------------------------------------------
# _BAL_LOOKUP — all categories
# ---------------------------------------------------------------------------

class TestBALLookup:
    def test_vegetation_buffer(self):
        bal, required = _BAL_LOOKUP["vegetation buffer"]
        assert bal == "BAL-12.5"
        assert required is True

    def test_vegetation_category_3(self):
        bal, required = _BAL_LOOKUP["vegetation category 3"]
        assert bal == "BAL-19"
        assert required is True

    def test_vegetation_category_2(self):
        bal, required = _BAL_LOOKUP["vegetation category 2"]
        assert bal == "BAL-29"
        assert required is True

    def test_vegetation_category_1(self):
        bal, required = _BAL_LOOKUP["vegetation category 1"]
        assert bal == "BAL-40 to BAL-FZ"
        assert required is True

    def test_unknown_category_not_in_lookup(self):
        assert "something else" not in _BAL_LOOKUP


# ---------------------------------------------------------------------------
# _FIRE_SIGNAL_MAP — all categories
# ---------------------------------------------------------------------------

class TestFireSignalMap:
    def test_buffer_is_low(self):
        assert _FIRE_SIGNAL_MAP["vegetation buffer"] == "low"

    def test_cat3_is_low(self):
        assert _FIRE_SIGNAL_MAP["vegetation category 3"] == "low"

    def test_cat2_is_moderate(self):
        assert _FIRE_SIGNAL_MAP["vegetation category 2"] == "moderate"

    def test_cat1_is_elevated(self):
        assert _FIRE_SIGNAL_MAP["vegetation category 1"] == "elevated"


# ---------------------------------------------------------------------------
# _build_compliance — bushfire prone
# ---------------------------------------------------------------------------

class TestBuildComplianceProne:
    def test_state_legislation_set(self):
        c = _build_compliance(_prone_rfs(), [], "R2")
        assert "s4.14" in c["state_legislation"]
        assert "Rural Fires Act" in c["state_legislation"]

    def test_rfs_referral_required(self):
        c = _build_compliance(_prone_rfs(), [], "R2")
        assert c["rfs_referral_required"] is True

    def test_rfs_triggers_present(self):
        c = _build_compliance(_prone_rfs(), [], "R2")
        assert c["rfs_referral_triggers"] == _S414_TRIGGERS

    def test_cdc_available_bal_29(self):
        c = _build_compliance(_prone_rfs(bal="BAL-29"), [], "R2")
        assert c["cdc_pathway_available"] is True

    def test_cdc_unavailable_bal_fz(self):
        c = _build_compliance(_prone_rfs(bal="BAL-40 to BAL-FZ"), [], "R2")
        assert c["cdc_pathway_available"] is False

    def test_cdc_available_bal_low(self):
        c = _build_compliance(_prone_rfs(bal="BAL-12.5"), [], "R2")
        assert c["cdc_pathway_available"] is True

    def test_clearing_entitled_when_prone(self):
        c = _build_compliance(_prone_rfs(), [], "R2")
        assert c["clearing_10_50_entitled"] is True

    def test_clearing_standard_no_heritage(self):
        """No heritage overlay → standard 10/50 entitlements text."""
        c = _build_compliance(_prone_rfs(), [], "R2")
        assert "Standard 10/50" in c["clearing_10_50_exceptions"]
        assert "Heritage" not in c["clearing_10_50_exceptions"]

    def test_clearing_heritage_exception(self):
        """Heritage overlay present → heritage restriction warning."""
        heritage = [{"type": "heritage", "value": "Heritage Conservation Area", "source": "spatial_overlays"}]
        c = _build_compliance(_prone_rfs(), heritage, "R2")
        assert "Heritage" in c["clearing_10_50_exceptions"]
        assert "restricted" in c["clearing_10_50_exceptions"].lower()

    def test_zone_passed_through(self):
        c = _build_compliance(_prone_rfs(), [], "R2")
        assert c["zone"] == "R2"

    def test_compliance_depth_state_level(self):
        c = _build_compliance(_prone_rfs(), [], "R2")
        assert c["compliance_depth"] == "state-level"

    def test_legislation_url_set(self):
        c = _build_compliance(_prone_rfs(), [], "R2")
        assert c["legislation_url"] is not None
        assert "sec-4.14" in c["legislation_url"]

    def test_consultant_costs_present(self):
        c = _build_compliance(_prone_rfs(), [], "R2")
        assert c["estimated_consultant_costs"] is not None

    def test_cross_overlays_included(self):
        flood = {"type": "flood", "value": "Flood Planning Area", "source": "spatial_overlays"}
        c = _build_compliance(_prone_rfs(), [flood], "R2")
        assert c["cross_overlays"] == [flood]


# ---------------------------------------------------------------------------
# _build_compliance — not bushfire prone
# ---------------------------------------------------------------------------

class TestBuildComplianceNotProne:
    def test_legislation_null(self):
        c = _build_compliance(_not_prone_rfs(), [], "R2")
        assert c["state_legislation"] is None

    def test_rfs_referral_not_required(self):
        c = _build_compliance(_not_prone_rfs(), [], "R2")
        assert c["rfs_referral_required"] is False

    def test_triggers_null(self):
        c = _build_compliance(_not_prone_rfs(), [], "R2")
        assert c["rfs_referral_triggers"] is None

    def test_clearing_not_entitled(self):
        c = _build_compliance(_not_prone_rfs(), [], "R2")
        assert c["clearing_10_50_entitled"] is False

    def test_clearing_exceptions_null(self):
        c = _build_compliance(_not_prone_rfs(), [], "R2")
        assert c["clearing_10_50_exceptions"] is None

    def test_consultant_costs_null(self):
        c = _build_compliance(_not_prone_rfs(), [], "R2")
        assert c["estimated_consultant_costs"] is None


# ---------------------------------------------------------------------------
# _build_compliance — unknown (null is_bushfire_prone)
# ---------------------------------------------------------------------------

class TestBuildComplianceUnknown:
    def test_rfs_referral_null(self):
        c = _build_compliance(_rfs_result(), [], "R2")
        assert c["rfs_referral_required"] is None

    def test_cdc_null_when_bal_unknown(self):
        c = _build_compliance(_rfs_result(), [], "R2")
        assert c["cdc_pathway_available"] is None

    def test_clearing_null(self):
        c = _build_compliance(_rfs_result(), [], "R2")
        assert c["clearing_10_50_entitled"] is None
        assert c["clearing_10_50_exceptions"] is None


# ---------------------------------------------------------------------------
# _compute_confidence
# ---------------------------------------------------------------------------

class TestComputeConfidence:
    def test_high_all_data(self):
        flood = {"type": "flood", "value": "FPA"}
        c = _compute_confidence(_prone_rfs(), [flood], "R2")
        assert c == "high"

    def test_medium_zone_only(self):
        c = _compute_confidence(_prone_rfs(), [], "R2")
        assert c == "medium"

    def test_medium_overlay_no_zone(self):
        flood = {"type": "flood", "value": "FPA"}
        c = _compute_confidence(_prone_rfs(), [flood], None)
        assert c == "medium"

    def test_medium_rfs_only(self):
        c = _compute_confidence(_prone_rfs(), [], None)
        assert c == "medium"

    def test_low_rfs_failed(self):
        c = _compute_confidence(_rfs_result(), [], None)
        assert c == "low"


# ---------------------------------------------------------------------------
# _build_data_sources
# ---------------------------------------------------------------------------

class TestBuildDataSources:
    def test_rfs_only(self):
        s = _build_data_sources(_prone_rfs(), [])
        assert s == [_DATA_SOURCE_RFS]

    def test_rfs_plus_spatial(self):
        flood = {"type": "flood", "value": "FPA"}
        s = _build_data_sources(_prone_rfs(), [flood])
        assert _DATA_SOURCE_RFS in s
        assert _DATA_SOURCE_SPATIAL in s


# ---------------------------------------------------------------------------
# _S414_TRIGGERS content
# ---------------------------------------------------------------------------

class TestS414Triggers:
    def test_has_three_triggers(self):
        assert len(_S414_TRIGGERS) == 3

    def test_subdivision_in_triggers(self):
        assert any("subdivision" in t.lower() for t in _S414_TRIGGERS)

    def test_special_fire_protection_in_triggers(self):
        assert any("special fire protection" in t.lower() for t in _S414_TRIGGERS)
