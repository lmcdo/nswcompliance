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
ANEF_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "wsa_anef_live.json"
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
    def test_adg_none_renders_not_assessed_never_a_verdict(self):
        """THE fix-1 PDF pin (output-grounding, 2026-08-03): adg_compliant None
        (noon scenario missing/errored) must render "Not assessed" — checked
        BEFORE the height-provenance branches so no numeric noon-shadow claim
        is made either. The old code fell through to "ADG concern". FAILS on
        pre-change code."""
        text, style, source = build_shadow_row(
            _shadow_result("spatial_overlays", adg_compliant=None)
        )
        assert text.startswith("Not assessed")
        assert "No shadow verdict" in text
        assert "ADG concern" not in text
        assert "%" not in text            # no numeric claim from an errored noon
        assert style == "note"

    def test_adg_none_with_default_height_makes_no_percent_claim(self):
        """Even on the assumed-envelope path, adg None must short-circuit
        before the '0% at Jun 21 noon' wording (the old order made that claim
        from an errored scenario)."""
        text, style, source = build_shadow_row(
            _shadow_result("default", adg_compliant=None)
        )
        assert text.startswith("Not assessed")
        assert "%" not in text

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
        # Secondary dwelling (#684): the SEPP fallback constants and any literal
        # 450 m² / R1-R4 eligibility figure must never return to the generator —
        # figures render only from injected housing_sepp_standards config.
        "_SD_FALLBACK",
        "450 m²",
        "≥ 450",
        '{"R1", "R2", "R3", "R4"}',
        # Corridors (Section 11): we state LRA map presence, authority and
        # instrument — never acquisition intent or likelihood.
        "will be acquired",
        "compulsory acquisition is proposed",
        # TOD uplift (Section 12) is FLOOR ONLY — the ceiling is held back.
        # Reading either engine CEILING field into the generator would wire the
        # held-back "up to N dwellings" number into a legal document. ("development
        # potential" is NOT forbidden — it is legitimately used elsewhere, e.g. the
        # existing-GFA disclosure note; the guard targets the ceiling specifically.)
        "max_permitted_dwellings",
        "max_permitted_form",
        "ceiling_dwellings",
        "ceiling_dev_type=_",   # engine call in this file must pass ceiling=None
        # Climate section (Section 13/12) is MODELLED PROJECTIONS ONLY — never a
        # hazard verdict, insurability call, or safety statement. These rendered
        # phrases must never enter the generator. (The bare stem "insurab" is NOT
        # source-checkable here — the negating comment "NO insurability claim"
        # contains it legitimately; the RENDERED-output guard in
        # test_conveyancing_climate.py::TestNoVerdictLanguage covers that seam.)
        "at risk of flood",
        "at risk of bushfire",
        "will flood",
        "will burn",
        "is uninsurable",
        "not insurable",
        "unsafe to",
        # Climate composite score / band is barred (#699, legal assessment):
        "climate_risk_score(",   # the composite scorer must NOT be wired into the PDF
        "climate risk score",
    ]

    # Regex patterns (as opposed to literal substrings) forbidden in the
    # generator source — a rendered dwelling-COUNT ceiling phrased as a yield.
    FORBIDDEN_PATTERNS = [
        r"yield of \d",
        r"up to \d+ dwelling",
        r'up to.*\{[^}]*dwelling',   # interpolated "up to {n} dwellings" sentence
    ]

    def test_generator_contains_no_forbidden_claims(self):
        src = GENERATOR_PATH.read_text(encoding="utf-8")
        for phrase in self.FORBIDDEN:
            assert phrase not in src, (
                f"Forbidden claim reintroduced into generate_conveyancing_report.py: {phrase!r}"
            )

    def test_generator_contains_no_forbidden_patterns(self):
        import re as _re
        src = GENERATOR_PATH.read_text(encoding="utf-8")
        for pat in self.FORBIDDEN_PATTERNS:
            assert not _re.search(pat, src), (
                f"Forbidden pattern reintroduced into generate_conveyancing_report.py: {pat!r}"
            )

    # Structures & Records (Section 13) — the defining constraint: the RENDERED
    # output must never state or imply a structure is unauthorised. A runtime
    # scan (not a source scan — the docstring legitimately names the rule) across
    # every branch of the builder. Full coverage lives in
    # tests/test_conveyancing_structures.py; this is the central belt-and-braces.
    STRUCT_FORBIDDEN_FRAMINGS = [
        "unapproved", "illegal", "unauthorised", "unauthorized",
        "non-compliant", "noncompliant", "breach", "without consent", "no approval",
    ]

    def test_structures_section_emits_no_verdict_word_on_any_branch(self):
        from generate_conveyancing_report import build_structures_records_lines
        branches = [
            build_structures_records_lines(None, records_status="failed"),
            build_structures_records_lines(None),
            build_structures_records_lines([]),
            build_structures_records_lines([{"pan": "PAN-1", "app_type": "Development Application",
                                             "dev_type": "Dwelling", "date": "2022-01-01",
                                             "status": "Determined"}]),
            build_structures_records_lines([], detections=[{"label": "cabin", "confidence": 0.9}]),
            build_structures_records_lines([{"dev_type": "studio"}],
                                           detections=[{"label": "studio", "confidence": 0.9}]),
        ]
        for out in branches:
            strings = [out.get("intro"), out.get("status_line"), out.get("detection_note")]
            strings += (out.get("record_lines") or []) + (out.get("gap_lines") or [])
            blob = " ".join(s for s in strings if s).lower()
            for word in self.STRUCT_FORBIDDEN_FRAMINGS:
                assert word not in blob, f"verdict framing {word!r} in structures output: {blob!r}"


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
# 10. Secondary-dwelling truth (#684) — same rule as land tax: figures render
#     only from injected housing_sepp_standards config, absence is fail-visible
# ---------------------------------------------------------------------------

def _sepp_standards_db() -> dict:
    """Shape produced by conveyancing_db.load_regulatory_configs from the
    housing_sepp_standards min_lot_size row (numeric_value cast to float)."""
    return {"sd_min_lot": 450.0, "sd_zones": {"R1", "R2", "R3", "R4"}}


def _sd_rows(results: list[dict]) -> list[dict]:
    return [r for r in results if "secondary dwelling" in r["question"].lower()]


class TestSecondaryDwellingTruth:
    def _run(self, sepp_standards, zone="R2", lot_area=500, is_strata=False):
        from generate_conveyancing_report import calc_feasibility
        return _sd_rows(calc_feasibility(
            {"zone": zone}, {"lot_area_m2": lot_area, "land_value": 900_000}, [],
            is_strata=is_strata, sepp_standards=sepp_standards, tax_config=None,
        ))

    def test_config_present_renders_injected_figure(self):
        """Mutation check: the rendered minimum comes from the config, not any
        constant — inject a non-450 figure and it must appear."""
        rows = self._run({"sd_min_lot": 600.0, "sd_zones": {"R2"}}, lot_area=650)
        assert len(rows) == 1
        assert rows[0]["answer"] == "Likely permissible"
        assert "600 m²" in rows[0]["basis"]
        assert "450" not in rows[0]["basis"]

    def test_config_present_below_minimum_uses_injected_figure(self):
        rows = self._run(_sepp_standards_db(), lot_area=300)
        assert rows[0]["answer"] == "Unlikely — lot too small"
        assert "450 m²" in rows[0]["basis"]           # from the injected config
        assert "Cl 53(1)(b)" in rows[0]["basis"]

    def test_config_absent_renders_not_assessed_no_figures(self):
        """Mutation check: restoring any hardcoded fallback fails this — an
        absent config must never produce an eligibility figure or zone claim."""
        import re as _re
        rows = self._run(None)
        assert len(rows) == 1
        assert rows[0]["answer"] == "Not assessed"
        assert rows[0]["flag"] == "warn"
        blob = rows[0]["answer"] + " " + rows[0]["basis"]
        assert not _re.search(r"\d+\s*m²", blob)
        assert "450" not in blob
        assert "unavailable" in rows[0]["basis"]

    def test_partial_config_fails_visible_not_partial_figures(self):
        """A config missing either key renders 'Not assessed' — half-loaded
        standards must not mix with any default."""
        for partial in ({"sd_min_lot": 450.0}, {"sd_zones": {"R1", "R2"}}, {}):
            rows = self._run(partial)
            assert rows[0]["answer"] == "Not assessed", partial

    def test_strata_branch_unaffected_by_absent_config(self):
        rows = self._run(None, is_strata=True)
        assert rows[0]["answer"] == "Not applicable — strata lot"

    def test_corrupt_injected_config_fails_visible(self):
        """Sol review of #816: calc_feasibility re-validates at its own
        boundary — a zero/NaN minimum or a null zone entry from any caller
        must render 'Not assessed', never pass every lot or crash sorted()."""
        for corrupt in (
            {"sd_min_lot": 0, "sd_zones": {"R2"}},
            {"sd_min_lot": float("nan"), "sd_zones": {"R2"}},
            {"sd_min_lot": 450.0, "sd_zones": {"R1", None}},
        ):
            rows = self._run(corrupt)
            assert rows[0]["answer"] == "Not assessed", corrupt

    def test_lot_area_unavailable_uses_injected_figure(self):
        rows = self._run(_sepp_standards_db(), lot_area=None)
        assert rows[0]["answer"] == "Lot area unavailable"
        assert "450 m²" in rows[0]["basis"]           # interpolated, not literal

    def test_db_loader_contains_no_fallback_constants(self):
        """Source guard one level up (#684): conveyancing_db must not
        reintroduce the 450 / R1-R4 defaults the loader used to carry."""
        src = (_ROOT / "scripts" / "conveyancing_db.py").read_text(encoding="utf-8")
        for phrase in ("else 450", 'else {"R1"', "fallback 450", "fallback 60"):
            assert phrase not in src, f"SEPP fallback reintroduced in conveyancing_db.py: {phrase!r}"

    def test_cdc_never_screens_from_sd_zone_set(self):
        """#820 PR-2: the CDC row renders ONLY from the engine result. With no
        cdc_result, a fully-populated SEPP Housing config must still render
        'Not assessed' — the secondary-dwelling zone screen is gone for good."""
        from generate_conveyancing_report import calc_feasibility
        rows = [r for r in calc_feasibility(
            {"zone": "R2"}, {"lot_area_m2": 500, "land_value": 900_000}, [],
            is_strata=False,
            sepp_standards={"sd_min_lot": 450.0, "sd_zones": {"R1", "R2"}},
            tax_config=None,
        ) if "Complying Development" in r["question"]]
        assert len(rows) == 1
        assert rows[0]["answer"] == "Not assessed"


# ---------------------------------------------------------------------------
# CDC row from the engine (#820 PR-2) — the row renders the CdcScreenResult
# verdict and never claims eligibility
# ---------------------------------------------------------------------------

class TestCdcRowFromEngine:
    def _run(self, cdc_result, zone="R2"):
        from generate_conveyancing_report import calc_feasibility
        return [r for r in calc_feasibility(
            {"zone": zone}, {"lot_area_m2": 500, "land_value": 900_000}, [],
            is_strata=False, sepp_standards=None, tax_config=None,
            cdc_result=cdc_result,
        ) if "Complying Development" in r["question"]]

    @staticmethod
    def _result(eligible="maybe", exclusions=(), warnings=(), checks=("Zone", "Lot size"), unchecked=()):
        import sys as _sys, os as _os
        _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), ".."))
        from services.cdc_screen import CdcExclusion, CdcScreenResult
        return CdcScreenResult(
            eligible=eligible,
            exclusions=[CdcExclusion(**e) for e in exclusions],
            warnings=list(warnings), checks_performed=list(checks),
            unchecked=list(unchecked),
        )

    def test_no_result_renders_not_assessed(self):
        rows = self._run(None)
        assert rows[0]["answer"] == "Not assessed"
        assert rows[0]["flag"] == "warn"

    def test_definite_exclusion_renders_excluded_with_citation(self):
        rows = self._run(self._result(eligible="no", exclusions=[{
            "reason": "Zone B2 is not in the zones this code applies to",
            "constraint": "zone", "severity": "definite",
            "source": "SEPP (Exempt and Complying Development Codes) 2008, cl 3.1(3)(a)",
        }]))
        assert rows[0]["answer"] == "Excluded (Housing Code) — zone"
        assert rows[0]["flag"] == "alert"
        assert "cl 3.1(3)(a)" in rows[0]["basis"]
        # Scope honesty: a Housing Code negative never rules out other codes
        assert "other complying development pathways were not assessed" in rows[0]["basis"].lower()
        assert "full DA" not in rows[0]["basis"]

    def test_likely_exclusion_renders_restricted_not_excluded(self):
        rows = self._run(self._result(exclusions=[{
            "reason": "Flood risk constraint mapped on this land — a certifier must assess",
            "constraint": "flood", "severity": "likely", "source": "NSW Planning Portal",
        }]))
        assert rows[0]["answer"] == "Restricted — flood risk"
        assert rows[0]["flag"] == "warn"

    def test_clear_screen_never_claims_eligibility(self):
        """The old row said 'Potentially eligible'; the engine-backed row
        states what was screened and defers the verdict to a certifier."""
        rows = self._run(self._result(warnings=["Not screened (data unavailable): heritage item."]))
        assert rows[0]["flag"] == "ok"
        assert "eligible" not in rows[0]["answer"].lower()
        assert "Not screened" in rows[0]["basis"]
        assert "certifier" in rows[0]["basis"]

    def test_strata_branch_unchanged(self):
        from generate_conveyancing_report import calc_feasibility
        rows = [r for r in calc_feasibility(
            {"zone": "R2"}, {"lot_area_m2": None, "land_value": 900_000}, [],
            is_strata=True, sepp_standards=None, tax_config=None,
            cdc_result=self._result(),
        ) if "Complying Development" in r["question"]]
        assert rows[0]["answer"] == "Unit alterations only — strata by-laws apply"


# ---------------------------------------------------------------------------
# 10. ANEF row + note (Slice B) — three-state, value data-derived
# ---------------------------------------------------------------------------

def _wsa_resolved() -> dict:
    with open(ANEF_FIXTURE_PATH, encoding="utf-8") as fh:
        return json.load(fh)["resolved"]


_ANEF_HIT = {"layer_type": "anef", "value": "", "instrument": None, "lga": None}


class TestAnefRowSemantics:
    def test_value_found_renders_code_and_provenance(self):
        """WSA golden fixture: the verbatim band code and the mapping EPI both
        render — never a parsed lower bound presented as exact."""
        text, style, source = build_anef_row(_wsa_resolved(), _ANEF_HIT)
        assert "ANEF 25 - 30" in text
        assert "Western Parkland City" in text
        assert "live query" in text
        assert style == "warn"
        assert "ANEF value lookup" in source

    def test_level_only_hit_renders_numeric_level(self):
        """A hit with no band code falls back to the numeric level."""
        levelled = {"status": "found", "anef_level": 25, "anef_code": None,
                    "epi_name": None, "source": "eplanning_protection_live"}
        text, style, source = build_anef_row(levelled, _ANEF_HIT)
        assert "ANEF 25" in text
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
        """A live-mapped contour with no ingested polygon must NOT vanish
        (silent-false-negative class). Mutation check: restoring
        `return None` for this state fails here."""
        row = build_anef_row(_wsa_resolved(), None)
        assert row is not None
        text, style, source = row
        assert "ANEF 25 - 30" in text
        assert source == "ANEF value lookup"
        assert "PostGIS" not in source

    def test_synthetic_hit_not_attributed_to_postgis(self):
        """Provenance: a synthesized overlay (instrument ANEF_VALUE_LOOKUP)
        must not carry a PostGIS source label."""
        synthetic = {"layer_type": "anef", "value": "ANEF 25 - 30",
                     "instrument": "ANEF_VALUE_LOOKUP", "lga": None}
        text, style, source = build_anef_row(_wsa_resolved(), synthetic)
        assert source == "ANEF value lookup"
        assert "PostGIS" not in source


class TestAnefNote:
    def test_found_note_states_value_and_drops_obtain_instruction(self):
        note = build_anef_note(_wsa_resolved())
        assert "ANEF contour value at this location: 25 - 30" in note
        assert "Western Parkland City" in note
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
    swallowing the transport exception into an 'empty' result fails these)."""

    def _resolver(self):
        import portal_constraints
        return portal_constraints

    def test_lookup_failure_is_failed_not_empty(self, monkeypatch):
        pc = self._resolver()
        def _boom(lat, lng):
            raise RuntimeError("arcgis timeout")
        monkeypatch.setattr(pc, "fetch_anef", _boom)
        assert pc.resolve_anef_value(-33.9, 151.2)["status"] == "failed"

    def test_no_mapped_contour_is_empty(self, monkeypatch):
        pc = self._resolver()
        monkeypatch.setattr(pc, "fetch_anef", lambda lat, lng: None)
        assert pc.resolve_anef_value(-33.9, 151.2)["status"] == "empty"

    def test_live_hit_is_found_with_code_and_epi(self, monkeypatch):
        pc = self._resolver()
        monkeypatch.setattr(
            pc, "fetch_anef",
            lambda lat, lng: {"in_anef_zone": True, "anef_level": 25,
                              "anef_code": "25 - 30", "epi_name": "Liverpool Local Environmental Plan 2008"},
        )
        out = pc.resolve_anef_value(-33.9, 151.2)
        assert out["status"] == "found"
        assert out["anef_code"] == "25 - 30"
        assert out["epi_name"] == "Liverpool Local Environmental Plan 2008"
        assert out["source"] == "eplanning_protection_live"

    def test_curated_anef_zones_never_consulted(self, monkeypatch):
        """Data-quality quarantine: the coarse anef_zones digitisations must not
        feed parcel-level values into the PDF. Mutation check: re-adding the
        anef_zones step to resolve_anef_value fails this."""
        pc = self._resolver()
        def _forbidden(lat, lng):
            raise AssertionError("anef_zones consulted by resolve_anef_value")
        monkeypatch.setattr(pc, "fetch_anef_zone_exact", _forbidden)
        monkeypatch.setattr(pc, "fetch_anef", lambda lat, lng: None)
        assert pc.resolve_anef_value(-33.9, 151.2)["status"] == "empty"
