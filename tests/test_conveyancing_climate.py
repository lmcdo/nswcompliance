"""Golden + adversarial tests for the conveyancing PDF climate-projection layer.

Guards SPEC CORRECTIONS C1/C3/C5/C6 (ce-conveyancing-climate-indicators plan):
  - C1: projections only — NO composite score / band / verdict is rendered.
  - C3: four distinct data states (present / no_coverage / out_of_domain /
        unavailable); a projection number appears ONLY in "present".
  - C5: every number carries a scenario (SSP) + epoch label.
  - C6: numbers are interpolated from the summary (never hardcoded); the
        mid/late epochs and baseline slot are not swapped; the enumerated
        mutations below each fail.

Fixtures (tests/fixtures/climate_narclim.json) are LIVE query_narclim_summary
reads — differentiated across three locations, which is itself the anti-hardcode
guard (a hardcoded builder renders all three identically).
"""
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT / "services"))
sys.path.insert(0, str(_ROOT))

from generate_conveyancing_report import (  # noqa: E402
    build_climate_lines,
    _climate_metric_rows,
)
from services import climate_risk_raster as crr  # noqa: E402

FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "climate_narclim.json").read_text(encoding="utf-8")
)
CONCORD = FIXTURES["concord_calm"]["summary"]
KATOOMBA = FIXTURES["katoomba_bushfire"]["summary"]
BOWRAL = FIXTURES["bowral_regression"]["summary"]

# The whole point of the feature: factual metrics, never a verdict. These must
# never appear in ANY rendered climate string (legal pre-read + liability
# scanner). Checked case-insensitively against rendered OUTPUT (not source, so
# a negating code comment like "NO insurability claim" is not a false positive).
FORBIDDEN_FRAMINGS = [
    "at risk", "insurab", "uninsurab", "safe from", "will flood", "will burn",
    "hazardous", "dangerous", "unsafe",
]
# Liability scanner banned verdict words (docs/qa/language-audit) — a climate
# metric must not smuggle any of these in.
SCANNER_BANNED = [
    "safe", "feasible", "compliant", "should", "recommend", "suitable",
    "adequate", "sufficient", "approved", "guaranteed", "certified",
    "confirmed", "verified", "ensure", "assure", "accurate", "definitive",
    "comprehensive", "reliable",
]


def _present(summary):
    return build_climate_lines({"state": "present", "summary": summary}, report_date="08 July 2026")


def _all_strings(out: dict):
    """Every user-facing string a rendered section would emit."""
    parts = list(out.get("rows") or [])
    for k in ("framing", "source_line", "status_line", "grid_note"):
        if out.get(k):
            parts.append(out[k])
    return parts


# ---------------------------------------------------------------------------
# 1. Present state — golden values, interpolation, epoch/scenario labelling
# ---------------------------------------------------------------------------

class TestPresentGolden:
    def test_concord_renders_three_variables(self):
        out = _present(CONCORD)
        assert out["render"] is True
        assert out["state"] == "present"
        assert len(out["rows"]) == 3  # hot days, temp, rainfall

    def test_concord_baseline_hot_days_is_real_and_labelled(self):
        # 26.96 -> 27, tagged as baseline (2015-2024). A swap that put a late
        # value in the baseline slot would break this exact substring.
        out = _present(CONCORD)
        hot = next(r for r in out["rows"] if "35" in r)
        assert "27 in the baseline period (2015–2024)" in hot

    def test_concord_late_century_ssp370_is_real_and_at_right_epoch(self):
        # 53.61 -> 54 must sit in the 2080-2099 slot under SSP3-7.0, NOT 2050.
        out = _present(CONCORD)
        hot = next(r for r in out["rows"] if "35" in r)
        assert "54 (SSP3-7.0) by 2080–2099" in hot
        assert "54 (SSP3-7.0) by 2050–2069" not in hot  # epoch not swapped

    def test_concord_mid_century_ssp370_is_real_and_at_right_epoch(self):
        # 44.75 -> 45 at 2050-2069 under SSP3-7.0.
        out = _present(CONCORD)
        hot = next(r for r in out["rows"] if "35" in r)
        assert "45 (SSP3-7.0) by 2050–2069" in hot

    def test_katoomba_all_four_scenario_epoch_cells_pinned(self):
        # Katoomba hot-days values are mutually distinct (baseline 5; 2050: 9/14;
        # 2080: 13/24), so this pins every scenario×epoch cell. Kills a mid<->late
        # epoch swap on EITHER scenario and a dropped SSP label on EITHER epoch —
        # weaknesses a "SSP in row" check alone let survive.
        hot = next(r for r in _present(KATOOMBA)["rows"] if "35" in r)
        assert "5 in the baseline period (2015–2024)" in hot   # 4.62
        assert "9 (SSP2-4.5) or 14 (SSP3-7.0) by 2050–2069" in hot   # 9.32 / 13.79
        assert "13 (SSP2-4.5) or 24 (SSP3-7.0) by 2080–2099" in hot  # 13.24 / 23.84

    def test_temperature_row_uses_real_values(self):
        out = _present(CONCORD)
        temp = next(r for r in out["rows"] if "temperature" in r)
        assert "20.9°C in the baseline period (2015–2024)" in temp  # 20.87 -> 20.9
        assert "24.0°C (SSP3-7.0) by 2080–2099" in temp             # 24.01 -> 24.0

    def test_rainfall_row_renders_decrease_factually(self):
        # Bowral precip falls (baseline 1.75 -> 1.45 SSP3-7.0). It must render
        # the numbers, NOT a "drought"/"at risk" verdict.
        out = _present(BOWRAL)
        rain = next(r for r in out["rows"] if "rainfall" in r)
        assert "1.75 mm in the baseline period (2015–2024)" in rain
        assert "1.45 mm (SSP3-7.0) by 2080–2099" in rain

    def test_every_metric_row_carries_both_scenarios_and_epochs(self):
        for summary in (CONCORD, KATOOMBA, BOWRAL):
            out = _present(summary)
            for row in out["rows"]:
                assert "SSP2-4.5" in row and "SSP3-7.0" in row, row
                assert "2015–2024" in row and "2080–2099" in row, row

    def test_grid_distance_note_is_real(self):
        out = _present(CONCORD)
        assert "0.69 km" in (out["grid_note"] or "")

    def test_source_line_names_dataset_scenarios_epochs_and_date(self):
        out = _present(CONCORD)
        src = out["source_line"]
        assert "NARCliM 2.0" in src and "AdaptNSW" in src
        assert "SSP2-4.5" in src and "SSP3-7.0" in src
        assert "2015–2024" in src and "2080–2099" in src
        assert "08 July 2026" in src  # currency stamped


# ---------------------------------------------------------------------------
# 2. Anti-hardcode — three real locations render three different figures
# ---------------------------------------------------------------------------

class TestInterpolationNotHardcoded:
    def test_baseline_hot_days_differ_across_locations(self):
        # Concord 27, Katoomba 5, Bowral 9 — a hardcoded builder cannot do this.
        c = next(r for r in _present(CONCORD)["rows"] if "35" in r)
        k = next(r for r in _present(KATOOMBA)["rows"] if "35" in r)
        b = next(r for r in _present(BOWRAL)["rows"] if "35" in r)
        assert "27 in the baseline" in c
        assert "5 in the baseline" in k
        assert "9 in the baseline" in b
        assert c != k != b

    def test_rendered_numbers_are_all_traceable_to_the_summary(self):
        # Every projection figure in the rows must equal a summary value at the
        # row's rounding. Epoch years and scenario labels are excluded — only
        # the value tokens are checked. Kills fabricated/mutated numbers.
        summary = CONCORD
        rows = _climate_metric_rows(summary)
        allowed = set()
        for v in summary.values():
            allowed.add(f"{v:.0f}")
            allowed.add(f"{v:.1f}")
            allowed.add(f"{v:.2f}")
        # Strip known label tokens (years, scenario codes) before scanning.
        LABELS = {"2015", "2024", "2050", "2069", "2080", "2099", "2", "4", "5", "3", "7", "0", "35"}
        for row in rows:
            # value tokens appear immediately before a unit/scenario or ' in the'
            for m in re.finditer(r"(\d+\.\d+|\d+)(?=°C| mm| \(SSP| in the)", row):
                tok = m.group(1)
                if tok in LABELS:
                    continue
                assert tok in allowed, f"untraceable number {tok!r} in row: {row}"


# ---------------------------------------------------------------------------
# 3. Four data states (C3) — a number appears ONLY when present
# ---------------------------------------------------------------------------

class TestDataStates:
    def test_no_coverage_renders_line_no_number(self):
        out = build_climate_lines({"state": "no_coverage"})
        assert out["render"] is True and out["state"] == "no_coverage"
        assert not out["rows"]
        assert "not provided" in out["status_line"]

    def test_out_of_domain_is_distinct_from_unavailable(self):
        ood = build_climate_lines({"state": "out_of_domain"})
        una = build_climate_lines({"state": "unavailable"})
        assert ood["state"] == "out_of_domain"
        assert una["state"] == "unavailable"
        # Permanent geographic limit must NOT read as a fixable infra gap.
        assert ood["status_line"] != una["status_line"]
        assert "outside" in ood["status_line"].lower()
        assert "not available" in una["status_line"].lower()

    def test_unavailable_never_shows_a_projection_number(self):
        for state in ("no_coverage", "out_of_domain", "unavailable"):
            out = build_climate_lines({"state": state})
            assert out["rows"] == []
            # No projection VALUE (a number bound to a unit or scenario) leaks
            # into the honest line. "NARCliM 2.0" is a dataset name, not a metric,
            # so a bare "\d+\.\d+" check would false-positive — bind to the unit.
            assert not re.search(r"\d+(\.\d+)?\s*(°C| mm|\(SSP| by 20)", out["status_line"] or "")

    def test_absent_and_empty_render_false(self):
        for payload in (None, {}, {"state": None}):
            out = build_climate_lines(payload)
            assert out["render"] is False
            assert out["rows"] == []

    def test_empty_summary_downgrades_to_no_coverage(self):
        # present envelope but the raster returned nothing renderable — must not
        # emit an empty section, and must never invent a number.
        out = build_climate_lines({"state": "present", "summary": {}})
        assert out["render"] is True
        assert out["state"] == "no_coverage"
        assert out["rows"] == []

    def test_only_grid_distance_downgrades_to_no_coverage(self):
        out = build_climate_lines({"state": "present", "summary": {"grid_distance_km": 3.1}})
        assert out["state"] == "no_coverage"
        assert out["rows"] == []

    def test_partial_summary_renders_only_present_variables(self):
        # temp-only response: one row, not three; the absent variables are not
        # silently zero-filled.
        partial = {
            "temp_baseline": 14.0, "temp_mid_century_mid": 15.0,
            "temp_mid_century_high": 15.5, "temp_late_century_mid": 16.0,
            "temp_late_century_high": 17.0, "temp_delta_2090": 3.0,
        }
        out = build_climate_lines({"state": "present", "summary": partial})
        assert out["state"] == "present"
        assert len(out["rows"]) == 1
        assert "temperature" in out["rows"][0]


# ---------------------------------------------------------------------------
# 4. No verdict / no banned framing in ANY rendered string (C1 + liability)
# ---------------------------------------------------------------------------

class TestNoVerdictLanguage:
    def _every_output(self):
        outs = [_present(s) for s in (CONCORD, KATOOMBA, BOWRAL)]
        outs += [build_climate_lines({"state": s})
                 for s in ("no_coverage", "out_of_domain", "unavailable")]
        return outs

    def test_no_forbidden_framing_anywhere(self):
        for out in self._every_output():
            for s in _all_strings(out):
                low = s.lower()
                for bad in FORBIDDEN_FRAMINGS:
                    assert bad not in low, f"forbidden framing {bad!r} in: {s}"

    def test_no_scanner_banned_verdict_words(self):
        for out in self._every_output():
            for s in _all_strings(out):
                # word-boundary match so "insurance"/"value" etc. are unaffected
                low = s.lower()
                for bad in SCANNER_BANNED:
                    assert not re.search(rf"\b{re.escape(bad)}\b", low), (
                        f"scanner-banned word {bad!r} in: {s}"
                    )

    def test_no_composite_score_or_band_rendered(self):
        # C1: the section must never surface a 1-100 score or a band word.
        for out in (_present(CONCORD), _present(KATOOMBA), _present(BOWRAL)):
            joined = " ".join(_all_strings(out)).lower()
            for band in ("very high", "moderate", "low risk", "high risk",
                         "score", "out of 100", "/100"):
                assert band not in joined, f"composite framing {band!r} leaked"


# ---------------------------------------------------------------------------
# 5. Fetcher state mapping (C3) — the four states must not be collapsed
# ---------------------------------------------------------------------------

class TestNarclimStateMapping:
    def test_present_wraps_summary(self, monkeypatch):
        monkeypatch.setattr(crr, "query_narclim_summary", lambda a, b: CONCORD)
        assert crr.query_narclim_state(-33.8, 151.1) == {"state": "present", "summary": CONCORD}

    def test_value_error_is_out_of_domain(self, monkeypatch):
        def _raise(a, b):
            raise ValueError("outside domain")
        monkeypatch.setattr(crr, "query_narclim_summary", _raise)
        assert crr.query_narclim_state(-99.0, 0.0)["state"] == "out_of_domain"

    def test_file_not_found_is_unavailable(self, monkeypatch):
        def _raise(a, b):
            raise FileNotFoundError("no raster")
        monkeypatch.setattr(crr, "query_narclim_summary", _raise)
        assert crr.query_narclim_state(-33.8, 151.1)["state"] == "unavailable"

    def test_out_of_domain_and_unavailable_not_collapsed(self, monkeypatch):
        # The C3 correctness point: a domain boundary and a missing-raster gap
        # must map to DIFFERENT states (removing the ValueError branch — the C6
        # mutation — fails here).
        def _ve(a, b):
            raise ValueError()
        monkeypatch.setattr(crr, "query_narclim_summary", _ve)
        s1 = crr.query_narclim_state(0.0, 0.0)["state"]

        def _fnf(a, b):
            raise FileNotFoundError()
        monkeypatch.setattr(crr, "query_narclim_summary", _fnf)
        s2 = crr.query_narclim_state(0.0, 0.0)["state"]
        assert s1 == "out_of_domain"
        assert s2 == "unavailable"
        assert s1 != s2

    def test_empty_dict_is_no_coverage(self, monkeypatch):
        monkeypatch.setattr(crr, "query_narclim_summary", lambda a, b: {})
        assert crr.query_narclim_state(-33.8, 151.1)["state"] == "no_coverage"

    def test_summary_without_delta_is_no_coverage(self, monkeypatch):
        monkeypatch.setattr(crr, "query_narclim_summary", lambda a, b: {"grid_distance_km": 2.0})
        assert crr.query_narclim_state(-33.8, 151.1)["state"] == "no_coverage"

    def test_unexpected_exception_is_unavailable(self, monkeypatch):
        def _boom(a, b):
            raise RuntimeError("netcdf blew up")
        monkeypatch.setattr(crr, "query_narclim_summary", _boom)
        assert crr.query_narclim_state(-33.8, 151.1)["state"] == "unavailable"
