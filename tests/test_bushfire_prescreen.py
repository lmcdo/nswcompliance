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
    ALGORITHM_VERSION,
    build_cache_manifest,
    build_live_manifest,
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

    def test_rfs_referral_unknown_without_a_proposal(self):
        """Prone land alone never yields a blanket True — referral (s100B Rural
        Fires Act) attaches to the proposal type, so without one it's None."""
        c = _build_compliance(_prone_rfs(), [], "R2")
        assert c["rfs_referral_required"] is None

    def test_rfs_triggers_always_populated_when_prone(self):
        c = _build_compliance(_prone_rfs(), [], "R2")
        assert c["rfs_referral_triggers"] == _S414_TRIGGERS

    def test_rfs_referral_note_present_when_prone(self):
        c = _build_compliance(_prone_rfs(), [], "R2")
        assert c["rfs_referral_note"] is not None
        assert "only if the proposal matches a trigger" in c["rfs_referral_note"]
        assert "Planning for Bush Fire Protection" in c["rfs_referral_note"]

    def test_cdc_available_bal_29(self):
        c = _build_compliance(_prone_rfs(bal="BAL-29"), [], "R2")
        assert c["cdc_pathway_available"] is True

    def test_cdc_unavailable_bal_fz(self):
        c = _build_compliance(_prone_rfs(bal="BAL-40 to BAL-FZ"), [], "R2")
        assert c["cdc_pathway_available"] is False

    def test_cdc_available_bal_low(self):
        c = _build_compliance(_prone_rfs(bal="BAL-12.5"), [], "R2")
        assert c["cdc_pathway_available"] is True

    def test_clearing_unknown_when_prone(self):
        """10/50 follows the RFS entitlement-area map, not bare BFPL status —
        a prone lot is None (unknown) until that map is checked."""
        c = _build_compliance(_prone_rfs(), [], "R2")
        assert c["clearing_10_50_entitled"] is None

    def test_clearing_conditional_wording_no_heritage(self):
        """No heritage overlay → conditional entitlement-area wording."""
        c = _build_compliance(_prone_rfs(), [], "R2")
        assert "RFS 10/50 entitlement area map" in c["clearing_10_50_exceptions"]
        assert "RFS online 10/50 tool" in c["clearing_10_50_exceptions"]
        assert "threatened species habitat" in c["clearing_10_50_exceptions"]
        assert "heritage" not in c["clearing_10_50_exceptions"].lower()

    def test_clearing_heritage_exception(self):
        """Heritage overlay present → conditional wording plus heritage restriction."""
        heritage = [{"type": "heritage", "value": "Heritage Conservation Area", "source": "spatial_overlays"}]
        c = _build_compliance(_prone_rfs(), heritage, "R2")
        assert "RFS 10/50 entitlement area map" in c["clearing_10_50_exceptions"]
        assert "heritage" in c["clearing_10_50_exceptions"].lower()
        assert "restrict" in c["clearing_10_50_exceptions"].lower()

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

    def test_rfs_referral_note_null(self):
        c = _build_compliance(_not_prone_rfs(), [], "R2")
        assert c["rfs_referral_note"] is None

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

    def test_rfs_note_and_triggers_null_when_unknown(self):
        c = _build_compliance(_rfs_result(), [], "R2")
        assert c["rfs_referral_note"] is None
        assert c["rfs_referral_triggers"] is None

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


# ---------------------------------------------------------------------------
# Execution manifest — provenance for every report row
# ---------------------------------------------------------------------------

from datetime import date as _date

from services.execution_manifest import MANIFEST_KEY  # noqa: E402


class TestExecutionManifest:
    """Every bushfire report row must record how it was made.

    ORIGIN, 2026-08-19. scripts/check_satellite_manifests.py measured
    bushfire at 0 of 65 reports carrying an execution manifest — the only
    satellite product wired to none — and the count of unprovenanced rows ROSE
    from 61 to 65 between 08-17 and 08-19, so new reports kept being written
    without provenance and the ratchet failed the build for every branch.

    A manifest cannot be backfilled: it is derivable only at computation time.
    So these tests fix the FORWARD behaviour. The 65 existing rows stay
    unprovenanced permanently, honestly counted.
    """

    def test_live_manifest_records_the_sources_actually_queried(self):
        rfs = _rfs_result(
            designation_source="NSW RFS BFPL",
            designation_category="Vegetation Category 1",
            designation_guideline="PBP 2019",
            data_currency="2024-11-01",
            fire_signal="high",
        )
        m = build_live_manifest(
            rfs, {"overlay_type": "flood_planning"}, {"overlay_type": "hca"},
            {"zone_code": "R2"}, -33.87, 151.2, 12345,
        )
        assert m["product"] == "bushfire"
        assert m["algorithm_version"] == ALGORITHM_VERSION
        rfs_id = m["inputs"]["rfs_bfpl"]
        assert rfs_id["designation_category"] == "Vegetation Category 1"
        assert rfs_id["data_currency"] == "2024-11-01"
        assert m["inputs"]["spatial_overlays"]["zone_code"] == "R2"
        assert m["inputs"]["provenance"]["served_from"] == "live_query"
        assert m["query_params"] == {"lat": -33.87, "lng": 151.2}
        assert m["parcel_identity"] == {"prop_id": 12345}

    def test_live_manifest_reads_the_result_dict_not_a_second_lookup(self):
        """The identity must MOVE with the result, or it describes another call."""
        rfs = _rfs_result(designation_category="Vegetation Buffer", data_currency="2019-01-01")
        m = build_live_manifest(rfs, None, None, None, -33.0, 151.0, None)
        assert m["inputs"]["rfs_bfpl"]["designation_category"] == "Vegetation Buffer"
        assert m["inputs"]["rfs_bfpl"]["data_currency"] == "2019-01-01"
        # absent overlays are recorded as absent, never as a default value
        assert m["inputs"]["spatial_overlays"]["flood"] is None
        assert m["inputs"]["spatial_overlays"]["heritage"] is None
        assert m["inputs"]["spatial_overlays"]["zone_code"] is None

    def test_cache_manifest_does_not_claim_a_query_that_never_happened(self):
        """The failure this guards: a cached copy labelled as a live screen.

        False provenance is worse than none, because it reads as evidence.
        """
        cached = {"run_date": _date(2026, 5, 1), "data_sources": ["NSW RFS BFPL"]}
        m = build_cache_manifest(cached, -33.87, 151.2, 999)
        prov = m["inputs"]["provenance"]
        assert prov["served_from"] == "cache"
        assert prov["served_from"] != "live_query"
        assert prov["source_run_date"] == "2026-05-01"
        assert prov["source_data_sources"] == ["NSW RFS BFPL"]  # recorded, so reported
        # It must NOT invent source identities it did not observe.
        assert "rfs_bfpl" not in m["inputs"]
        assert "spatial_overlays" not in m["inputs"]

    def test_cache_manifest_does_not_invent_a_source_it_cannot_know(self):
        """A legacy row with no recorded sources must say so, not guess.

        Raised by scripts/cross_review.py at 0.97 and correct: the first
        version defaulted a NULL data_sources to the RFS map, which asserts a
        fact about a run nobody recorded — inside the one structure whose job
        is to record what actually happened. False provenance in a manifest is
        worse than false provenance anywhere else.
        """
        m = build_cache_manifest({"run_date": _date(2026, 5, 1)}, -33.0, 151.0, None)
        assert m["inputs"]["provenance"]["source_data_sources"] is None
        m2 = build_cache_manifest({"data_sources": []}, -33.0, 151.0, None)
        assert m2["inputs"]["provenance"]["source_data_sources"] is None
        # A row that DOES record its sources still reports them.
        m3 = build_cache_manifest({"data_sources": ["NSW RFS BFPL"]}, -33.0, 151.0, None)
        assert m3["inputs"]["provenance"]["source_data_sources"] == ["NSW RFS BFPL"]

    def test_cache_manifest_survives_a_missing_run_date(self):
        """A cache row from before run_date was selected must not crash the write."""
        m = build_cache_manifest({}, -33.87, 151.2, None)
        assert m["inputs"]["provenance"]["source_run_date"] is None
        assert m["inputs"]["provenance"]["served_from"] == "cache"
        m2 = build_cache_manifest({"run_date": "2026-05-01"}, -33.87, 151.2, None)
        assert m2["inputs"]["provenance"]["source_run_date"] == "2026-05-01"

    def test_both_manifests_carry_the_key_the_ratchet_counts(self):
        """The check counts `inputs ? 'execution_manifest'` — pin that exact key.

        A manifest stored under any other key is invisible to the ratchet, which
        is how solar-yield could look like 0 coverage while writing one.
        """
        assert MANIFEST_KEY == "execution_manifest"
        for m in (build_live_manifest(_rfs_result(), None, None, None, -33.0, 151.0, None),
                  build_cache_manifest({}, -33.0, 151.0, None)):
            envelope = {"lat": -33.0, "lng": 151.0, MANIFEST_KEY: m}
            assert "execution_manifest" in envelope
            assert envelope["execution_manifest"]["product"] == "bushfire"

    def test_the_algorithm_version_is_named_not_blank(self):
        """A manifest naming no version cannot say which code made the report."""
        assert ALGORITHM_VERSION
        assert ALGORITHM_VERSION.startswith("bushfire-")
