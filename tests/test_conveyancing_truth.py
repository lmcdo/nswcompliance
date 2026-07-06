"""Golden-sentence truth tests for the conveyancing PDF pipeline.

Guards the five live-verified integrity defects from the Bowral audit
(38 Park Rd Bowral, propId 1119594, verified against live NSW sources
2026-07-06 — see ~/.claude/plans/ce-conveyancing-integrity-remediation-2026-07.md):

  D1  fabricated "LEP maximum height" attribution when the shadow model used
      the 9 m default envelope
  D2  silent drop of unrecognised layerintersect groups (missed the Sydney
      Drinking Water Catchment constraint)
  D3  "Not mapped in NSW state layer for this LGA" blaming the state layer for
      OUR ingest gap + bushfire never checked live
  D4  blanket "NOT disclosed in a standard s10.7(2)" claims (bushfire/flood are
      prescribed certificate matters, EP&A Reg 2021 Sch 2)
  D5  9 m classified-road setback wrongly attributed to TI SEPP s2.120
  D6  confidence "high" despite assumed heights / coverage gaps

Pure-logic tests: recorded fixture, no live HTTP, no reportlab rendering.
"""

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT / "services"))
sys.path.insert(0, str(_ROOT))

from generate_conveyancing_report import (  # noqa: E402
    ANEF_NOTE,
    build_anef_note,
    build_anef_row,
    build_bushfire_row,
    build_land_tax_rows,
    build_shadow_row,
    build_unmapped_note,
    parse_controls,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "bowral_layerintersect.json"
ANEF_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mascot_anef_resolved.json"
GENERATOR_PATH = _ROOT / "scripts" / "generate_conveyancing_report.py"


def _bowral_raw() -> list[dict]:
    with open(FIXTURE_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _shadow_result(height_source: str, height_m: float = 9.0, noon_fraction: float = 0.0,
                   adg_compliant: bool = True, overlaps: bool = False) -> dict:
    """Minimal shadow outputs dict as returned by /pipeline/shadow."""
    return {
        "height_m": height_m,
        "height_source": height_source,
        "adg_compliant": adg_compliant,
        "scenarios": [
            {
                "scenario": "jun21_12pm",
                "shadow_overlap_fraction": noon_fraction,
                "overlaps_subject_lot": overlaps,
            },
        ],
    }


# ---------------------------------------------------------------------------
# 1-2. Shadow row provenance (D1)
# ---------------------------------------------------------------------------

class TestShadowRowProvenance:
    def test_default_height_never_claims_lep(self):
        """G1-1: default envelope → no LEP attribution anywhere in the row."""
        text, style, source = build_shadow_row(_shadow_result("default"))
        assert "LEP maximum height" not in text
        assert "no LEP height limit is mapped for this lot" in text
        assert "assumed envelope" in text
        assert "NSW LEP" not in source
        assert source == "assumed envelope · shadow model"

    def test_default_height_never_asserts_clear(self):
        """A verdict of "Clear" must never be built from an assumed envelope."""
        text, style, source = build_shadow_row(
            _shadow_result("default", noon_fraction=0.0, adg_compliant=True)
        )
        assert not text.startswith("Clear")
        assert "Not determinable from LEP controls" in text
        assert "taller merit-assessed build is possible" in text
        assert style != "ok"

    def test_spatial_overlays_height_allows_lep_attribution(self):
        """G1-2: real LEP height (9.0, spatial_overlays) → LEP attribution allowed."""
        text, style, source = build_shadow_row(
            _shadow_result("spatial_overlays", height_m=9.0)
        )
        assert "LEP maximum height of buildings: 9.0 m" in text
        assert source == "NSW LEP · shadow model"

    def test_portal_height_allows_lep_attribution(self):
        text, style, source = build_shadow_row(
            _shadow_result("planning_portal", height_m=8.5)
        )
        assert source == "NSW LEP · shadow model"

    def test_no_shadow_result_is_not_assessed(self):
        text, style, source = build_shadow_row(None)
        assert text == "Not assessed"
        assert style == "note"
        assert "NSW LEP" not in source

    def test_missing_height_source_fails_closed(self):
        """Unknown provenance must never be attributed to the LEP."""
        result = _shadow_result("spatial_overlays")
        del result["height_source"]
        text, style, source = build_shadow_row(result)
        assert "LEP maximum height" not in text
        assert "NSW LEP" not in source
        assert not text.startswith("Clear")


# ---------------------------------------------------------------------------
# 3-4. parse_controls fail-open capture (D2)
# ---------------------------------------------------------------------------

class TestParseControlsFailOpen:
    def test_bowral_fixture_captures_sdwc(self):
        """G1-3: the exact Bowral regression — SDWC must appear as a named constraint."""
        out = parse_controls(_bowral_raw())
        assert out["sdwc"] is not None
        assert out["sdwc"]["layer"] == "Sydney Drinking Water Catchment Map"
        assert "Part 6.2 and 6.5" in out["sdwc"]["label"]
        assert "Biodiversity and Conservation) 2021" in out["sdwc"]["label"]

    def test_bowral_fixture_captures_other_instruments(self):
        """Regional Plan Boundary and Local Aboriginal Land Council must not vanish."""
        out = parse_controls(_bowral_raw())
        layers = {oi["layer"] for oi in out["other_instruments"]}
        assert "Regional Plan Boundary" in layers
        assert "Local Aboriginal Land Council" in layers

    def test_bowral_fixture_known_controls_still_parse(self):
        """The fail-open branch must not disturb recognised groups."""
        out = parse_controls(_bowral_raw())
        assert out["zone"] == "R3"
        assert out["zone_full"] == "Medium Density Residential"
        assert out["lot_size"] == "700"
        # Special Provisions Class values survive (Water Use 40%, climate zones 6/24)
        classes = {ov.get("class") for ov in out["sepp_overlays"]}
        assert "40%" in classes
        assert "6" in classes
        assert "24" in classes

    def test_unknown_layer_group_is_captured_not_dropped(self):
        """G1-4 mutation check: deleting the else branch must fail this test."""
        raw = [{
            "layerName": "Zombie Test Layer",
            "results": [{"title": "Zombie Provision 99"}],
        }]
        out = parse_controls(raw)
        assert len(out["other_instruments"]) == 1
        assert out["other_instruments"][0]["layer"] == "Zombie Test Layer"
        assert out["other_instruments"][0]["titles"] == ["Zombie Provision 99"]

    def test_empty_results_block_not_captured(self):
        raw = [{"layerName": "Zombie Test Layer", "results": []}]
        out = parse_controls(raw)
        assert out["other_instruments"] == []


# ---------------------------------------------------------------------------
# 5. Unmapped-coverage footnote wording (D3)
# ---------------------------------------------------------------------------

class TestUnmappedNote:
    def test_owns_the_gap_never_blames_state_layer(self):
        """G1-5: the note owns OUR ingest gap; never asserts the NSW layer lacks data."""
        note = build_unmapped_note(set())
        assert note is not None
        assert "PlotDetect's ingested" in note
        assert "NSW state layer for this LGA" not in note
        assert "not a statement about the council's own mapping" in note

    def test_bushfire_never_in_unmapped_list(self):
        """Bushfire is live-checked against RFS — coverage footnote must not list it."""
        note = build_unmapped_note(set())  # nothing covered at all
        assert "bushfire" not in note.lower()

    def test_fully_covered_returns_none(self):
        covered = {"flood", "riparian", "wetlands", "landslide", "biodiversity"}
        assert build_unmapped_note(covered) is None

    def test_unknown_coverage_returns_none(self):
        assert build_unmapped_note(None) is None


# ---------------------------------------------------------------------------
# 6. Live bushfire row semantics (D3)
# ---------------------------------------------------------------------------

class TestBushfireRowSemantics:
    def test_live_prone_is_alert_with_category(self):
        text, style, source = build_bushfire_row(
            {"is_bushfire_prone": True, "designation_category": "Vegetation Category 1"},
            None,
        )
        assert style == "alert"
        assert "Vegetation Category 1" in text
        assert "live query" in source

    def test_live_clear_cites_live_rfs(self):
        text, style, source = build_bushfire_row({"is_bushfire_prone": False}, None)
        assert style == "ok"
        assert text.startswith("Clear")
        assert "live query" in text

    def test_live_failure_is_never_clear(self):
        """A failed RFS query must render 'Not assessed', never 'Clear'."""
        for failed in (None, {"is_bushfire_prone": None}):
            text, style, source = build_bushfire_row(failed, None)
            assert "Clear" not in text
            assert text.startswith("Not assessed")
            assert style == "note"

    def test_live_failure_falls_back_to_postgis_hit(self):
        """Ingested hit still surfaces (alert) when the live query fails."""
        text, style, source = build_bushfire_row(
            None, {"layer_type": "bushfire", "value": "Category 2"},
        )
        assert style == "alert"
        assert "Category 2" in text
        assert "Clear" not in text


# ---------------------------------------------------------------------------
# 7. Static-claims guard (D4/D5) — forbidden wording must not be reintroduced
# ---------------------------------------------------------------------------

class TestStaticClaimsGuard:
    FORBIDDEN = [
        # D4: blanket claim — bushfire/flood ARE prescribed s10.7(2) matters
        "NOT disclosed in a standard s10.7",
        "None of these layers are disclosed in a standard s10.7",
        "None of these layers appear in a standard s10.7",
        # D5: Codes SEPP CDC standard wrongly attributed to TI SEPP s2.120
        "9 m minimum setback from classified road",
        # D3: our ingest gap blamed on the NSW state layer
        "Not mapped in NSW state layer for this LGA",
        # D1: fixed "NSW LEP" source label on the shadow row regardless of source
        'risk_rows.append(["Northern Development Shadow Risk", shadow_flag, "NSW LEP',
        # Land tax: hardcoded threshold constants must never return to the
        # generator — a fallback constant IS a hardcoded regulatory value and
        # rendered silently-stale figures in a legal document.
        "_LT_FALLBACK",
        "1_075_000",
        "1075000",
        "1,075,000",
    ]

    def test_generator_contains_no_forbidden_claims(self):
        src = GENERATOR_PATH.read_text(encoding="utf-8")
        for phrase in self.FORBIDDEN:
            assert phrase not in src, (
                f"Forbidden claim reintroduced into generate_conveyancing_report.py: {phrase!r}"
            )


# ---------------------------------------------------------------------------
# 8. Integrity-aware confidence (D6 / QA-S7)
# ---------------------------------------------------------------------------

class TestConfidenceIntegrity:
    @staticmethod
    def _full_controls():
        return {"zone": "R3", "height": "9.5", "fsr": "0.5:1"}

    @staticmethod
    def _full_valuation():
        return {"lot_area_m2": 4096}

    def _compute(self, **kwargs):
        from conveyancing import _compute_confidence
        return _compute_confidence(
            self._full_controls(), [{"layer_type": "flood"}], self._full_valuation(),
            **kwargs,
        )

    def test_bowral_profile_is_not_high(self):
        """G1-8: unmapped layers + default shadow height must cap below 'high'."""
        rating = self._compute(covered_layers=set(), shadow_height_source="default")
        assert rating != "high"

    def test_unmapped_layers_alone_cap_at_medium(self):
        rating = self._compute(covered_layers={"flood"})  # riparian etc. missing
        assert rating == "medium"

    def test_default_shadow_height_alone_caps_at_medium(self):
        full = {"flood", "riparian", "wetlands", "landslide", "biodiversity"}
        rating = self._compute(covered_layers=full, shadow_height_source="default")
        assert rating == "medium"

    def test_two_live_failures_cap_at_low(self):
        full = {"flood", "riparian", "wetlands", "landslide", "biodiversity"}
        rating = self._compute(covered_layers=full, live_query_failures=2)
        assert rating == "low"

    def test_clean_full_profile_still_high(self):
        """Regression guard: a metro report with full coverage keeps 'high'."""
        full = {"flood", "riparian", "wetlands", "landslide", "biodiversity"}
        rating = self._compute(covered_layers=full, shadow_height_source="spatial_overlays")
        assert rating == "high"

    def test_missing_tax_config_caps_at_medium(self):
        """A report whose land-tax section rendered 'Not assessed' must not claim 'high'."""
        full = {"flood", "riparian", "wetlands", "landslide", "biodiversity"}
        rating = self._compute(covered_layers=full, tax_config_missing=True)
        assert rating == "medium"


# ---------------------------------------------------------------------------
# 9. Land tax truth (Slice A) — date-stamped figures, fail-visible absence
# ---------------------------------------------------------------------------

def _tax_config_2026() -> dict:
    """Recorded Revenue NSW figures (thresholds-and-rates page, fetched
    2026-07-06; general/premium thresholds frozen from 1 Jan 2025)."""
    return {
        "tax_year": 2026,
        "threshold_dollars": 1_075_000,
        "rate": 0.016,
        "base_amount_dollars": 100,
        "premium_threshold_dollars": 6_571_000,
        "premium_rate": 0.02,
    }


class TestLandTaxTruth:
    def test_config_present_sentence_carries_tax_year(self):
        """Every rendered threshold figure carries the DB row's own tax_year."""
        rows = build_land_tax_rows(1_500_000, _tax_config_2026())
        assert len(rows) == 1
        row = rows[0]
        assert "2026" in row["question"]
        assert "2026 threshold $1,075,000" in row["basis"]
        assert row["flag"] == "warn"

    def test_below_threshold_sentence_carries_tax_year(self):
        rows = build_land_tax_rows(900_000, _tax_config_2026())
        row = rows[0]
        assert row["answer"] == "Below threshold — nil"
        assert "2026 threshold $1,075,000" in row["basis"]

    def test_config_absent_renders_not_assessed_no_figures(self):
        """Mutation check: restoring any hardcoded fallback figures fails this —
        an absent config must never produce a dollar amount."""
        import re as _re
        rows = build_land_tax_rows(1_500_000, None)
        assert len(rows) == 1
        row = rows[0]
        assert row["answer"] == "Not assessed"
        assert row["flag"] == "warn"
        assert not _re.search(r"\$\s*\d", row["answer"] + " " + row["basis"])
        assert "unavailable" in row["basis"]
        # the expected year is named so the reader knows WHICH year is missing
        from datetime import date as _date
        assert str(_date.today().year) in row["basis"]

    def test_config_absent_logs_warning(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING):
            build_land_tax_rows(1_500_000, None)
        assert any("land tax config unavailable" in r.message for r in caplog.records)

    def test_stale_year_renders_with_own_year_and_warns(self, caplog):
        """A stale row renders — its visible year keeps it honest — but loudly."""
        import logging
        stale = dict(_tax_config_2026(), tax_year=2025)
        with caplog.at_level(logging.WARNING):
            rows = build_land_tax_rows(1_500_000, stale)
        row = rows[0]
        assert "2025" in row["question"]
        assert "2025 threshold" in row["basis"]
        assert any("2025" in r.message and "current land tax year" in r.message
                   for r in caplog.records)

    def test_strata_has_no_land_tax_row(self):
        """calc_feasibility: strata suppresses land tax even with config absent."""
        from generate_conveyancing_report import calc_feasibility
        results = calc_feasibility(
            {"zone": "R2"}, {"lot_area_m2": 500, "land_value": 1_500_000}, [],
            is_strata=True, tax_config=None,
        )
        assert not [r for r in results if "land tax" in r["question"].lower()]

    def test_calc_feasibility_config_absent_end_to_end(self):
        from generate_conveyancing_report import calc_feasibility
        results = calc_feasibility(
            {"zone": "R2"}, {"lot_area_m2": 500, "land_value": 1_500_000}, [],
            tax_config=None,
        )
        lt = [r for r in results if "land tax" in r["question"].lower()]
        assert len(lt) == 1
        assert lt[0]["answer"] == "Not assessed"


# ---------------------------------------------------------------------------
# 10. ANEF row + note (Slice B) — three-state, value data-derived
# ---------------------------------------------------------------------------

def _mascot_resolved() -> dict:
    with open(ANEF_FIXTURE_PATH, encoding="utf-8") as fh:
        return json.load(fh)["resolved"]


_ANEF_HIT = {"layer_type": "anef", "value": "", "instrument": None, "lga": None}


class TestAnefRowSemantics:
    def test_value_found_renders_level_source_and_vintage(self):
        """Mascot golden fixture: value, airport and ANEF vintage all render."""
        text, style, source = build_anef_row(_mascot_resolved(), _ANEF_HIT)
        assert "ANEF 35" in text
        assert "Sydney Airport ANEF 2039" in text
        assert style == "warn"
        assert "ANEF value lookup" in source

    def test_regional_code_renders_verbatim(self):
        """Live ePlanning band codes (e.g. '25-30') render verbatim, not a
        parsed lower bound presented as exact."""
        regional = {"status": "found", "anef_level": 25, "anef_code": "25-30",
                    "airport": None, "anef_version": None,
                    "source": "eplanning_protection_live"}
        text, style, source = build_anef_row(regional, _ANEF_HIT)
        assert "ANEF 25-30" in text
        assert "live query" in text

    def test_empty_keeps_todays_wording(self):
        text, style, source = build_anef_row({"status": "empty"}, _ANEF_HIT)
        assert text == "Aircraft noise contour — ANEF applies"
        assert source == "PostGIS"

    def test_lookup_not_run_keeps_todays_wording(self):
        text, style, source = build_anef_row(None, _ANEF_HIT)
        assert text == "Aircraft noise contour — ANEF applies"

    def test_failed_is_explicit_never_silent(self):
        """A failed value lookup states 'not assessed' — the overlay hit itself
        still renders (the ingest said the contour applies)."""
        text, style, source = build_anef_row({"status": "failed"}, _ANEF_HIT)
        assert "ANEF applies" in text
        assert "not assessed" in text
        assert "unavailable" in text

    def test_no_hit_no_value_omits_row(self):
        """Bowral regression: no ingested overlay and no resolved value → no
        row; a failed lookup on a lot with no mapped contour is a non-event."""
        assert build_anef_row(None, None) is None
        assert build_anef_row({"status": "empty"}, None) is None
        assert build_anef_row({"status": "failed"}, None) is None

    def test_value_without_ingest_hit_still_renders(self):
        """Mascot gap (verified 2026-07-06): anef_zones resolves 35 but the
        ingest has no anef polygon — the resolved contour must NOT vanish.
        Mutation check: restoring `return None` for this state fails here."""
        row = build_anef_row(_mascot_resolved(), None)
        assert row is not None
        text, style, source = row
        assert "ANEF 35" in text
        assert source == "ANEF value lookup"
        assert "PostGIS" not in source

    def test_synthetic_hit_not_attributed_to_postgis(self):
        """Provenance: a synthesized overlay (instrument ANEF_VALUE_LOOKUP)
        must not carry a PostGIS source label."""
        synthetic = {"layer_type": "anef", "value": "ANEF 35",
                     "instrument": "ANEF_VALUE_LOOKUP", "lga": None}
        text, style, source = build_anef_row(_mascot_resolved(), synthetic)
        assert source == "ANEF value lookup"
        assert "PostGIS" not in source


class TestAnefNote:
    def test_found_note_states_value_and_drops_obtain_instruction(self):
        note = build_anef_note(_mascot_resolved())
        assert "ANEF contour value at this location: 35" in note
        assert "Sydney Airport ANEF 2039" in note
        # the "obtain the value externally" instruction is the NO-value fallback
        assert "obtain the ANEF value from the relevant airport authority" not in note
        # the liability-audited AS 2021 / TI-SEPP wording is preserved verbatim
        assert "Under SEPP (Transport and Infrastructure) 2021 and AS 2021" in note

    def test_empty_and_not_run_fall_back_to_static_note(self):
        assert build_anef_note({"status": "empty"}) is None
        assert build_anef_note(None) is None

    def test_failed_note_appends_explicit_not_assessed(self):
        note = build_anef_note({"status": "failed"})
        assert note.startswith(ANEF_NOTE)
        assert "not assessed" in note

    def test_static_anef_note_fallback_wording_preserved(self):
        """Golden: the honest no-value fallback wording survives the split."""
        assert "obtain the ANEF value from the relevant airport authority" in ANEF_NOTE
        assert ANEF_NOTE.startswith("Aircraft Noise Contour — this property falls within")
        assert ANEF_NOTE.endswith("Source: NSW Government ArcGIS spatial overlay (ANEF mapping).")


class TestResolveAnefValueThreeState:
    """The shared resolver must distinguish empty from failed (mutation check:
    swallowing the DB exception into a None/'empty' result fails these)."""

    def _resolver(self):
        import portal_constraints
        return portal_constraints

    def test_db_failure_is_failed_not_empty(self, monkeypatch):
        pc = self._resolver()
        def _boom(lat, lng):
            raise RuntimeError("db down")
        monkeypatch.setattr(pc, "fetch_anef_zone_exact", _boom)
        assert pc.resolve_anef_value(-33.9, 151.2)["status"] == "failed"

    def test_sydney_hit_is_found(self, monkeypatch):
        pc = self._resolver()
        monkeypatch.setattr(
            pc, "fetch_anef_zone_exact",
            lambda lat, lng: {"anef_level": 35, "airport": "Sydney", "anef_version": "ANEF 2039"},
        )
        out = pc.resolve_anef_value(-33.9, 151.2)
        assert out["status"] == "found"
        assert out["anef_level"] == 35
        assert out["source"] == "anef_zones"
        assert out["anef_version"] == "ANEF 2039"

    def test_no_hit_anywhere_is_empty(self, monkeypatch):
        pc = self._resolver()
        monkeypatch.setattr(pc, "fetch_anef_zone_exact", lambda lat, lng: None)
        monkeypatch.setattr(pc, "fetch_anef", lambda lat, lng: None)
        assert pc.resolve_anef_value(-33.9, 151.2)["status"] == "empty"

    def test_regional_failure_is_failed(self, monkeypatch):
        pc = self._resolver()
        monkeypatch.setattr(pc, "fetch_anef_zone_exact", lambda lat, lng: None)
        def _boom(lat, lng):
            raise RuntimeError("arcgis timeout")
        monkeypatch.setattr(pc, "fetch_anef", _boom)
        assert pc.resolve_anef_value(-33.9, 151.2)["status"] == "failed"

    def test_regional_hit_is_found_with_code(self, monkeypatch):
        pc = self._resolver()
        monkeypatch.setattr(pc, "fetch_anef_zone_exact", lambda lat, lng: None)
        monkeypatch.setattr(
            pc, "fetch_anef",
            lambda lat, lng: {"in_anef_zone": True, "anef_level": 25, "anef_code": "25-30"},
        )
        out = pc.resolve_anef_value(-33.9, 151.2)
        assert out["status"] == "found"
        assert out["anef_code"] == "25-30"
        assert out["source"] == "eplanning_protection_live"
