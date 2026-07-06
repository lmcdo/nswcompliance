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
    build_bushfire_row,
    build_shadow_row,
    build_unmapped_note,
    parse_controls,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "bowral_layerintersect.json"
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
