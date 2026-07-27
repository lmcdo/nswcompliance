"""Estuarine tidal inundation — fetcher three-state + golden section wording.

Contract (scripts/generate_conveyancing_report.py):

  get_coastal_inundation_live →
    {"status": "failed"}                → "not assessed" (NEVER an extent claim)
    {"status": "outside", ...}          → checked non-intersection
    {"status": "intersects", "years"}   → per-year most-frequent tier, figures
                                          READ from the stored rows

  build_coastal_inundation_lines → render-state dict; the scope sentence
  ("estuarine ... does NOT cover open-coast/surf ...") must ride with every
  extent claim so "estuarine" can never read as general coastal coverage.

Break-it classes guarded:
  CI-1: a DB failure rendering as "outside the mapped extent" (false clear on
        a canal-estate lot) — failed and outside must stay distinct.
  CI-2: composing a frequency figure instead of reading it from the row.
  CI-3: an "intersects" payload with no parseable year silently rendering an
        empty extent claim.

Pure-logic tests: no live DB, no reportlab rendering.
"""

import re
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT / "services"))
sys.path.insert(0, str(_ROOT))

import generate_conveyancing_report as gcr  # noqa: E402
from generate_conveyancing_report import (  # noqa: E402
    _coastal_year_row,
    build_coastal_inundation_lines,
    get_coastal_inundation_live,
)

_ROW_2050_F1 = ("estuary_inund_2025_s370_y2050_f1",
                "SSP3-7.0 · 2050 · exceeded 1.0 days/year (0.274%)", 1.0)
_ROW_2050_F4 = ("estuary_inund_2025_s370_y2050_f4",
                "SSP3-7.0 · 2050 · exceeded 182.5 days/year (50%)", 182.5)
_ROW_2100_F2 = ("estuary_inund_2025_s370_y2100_f2",
                "SSP3-7.0 · 2100 · exceeded 3.65 days/year (1%)", 3.65)

# The pre-PR liability list — none of these may appear in rendered coastal text.
_LIABILITY_RE = re.compile(
    r"\b(safe|feasible|compliant|recommend|suitable|adequate|sufficient|"
    r"approved|guaranteed|certified|confirmed|verified|ensure|assure|"
    r"accurate|definitive|comprehensive|reliable)\b",
    re.IGNORECASE,
)


class _FakeCursor:
    def __init__(self, rows, layer_present=True):
        self._rows = rows
        self._layer_present = layer_present
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return self._rows

    def fetchone(self):
        # Only the layer-presence probe calls fetchone.
        return (1,) if self._layer_present else None

    def close(self):
        pass


class _FakeConn:
    def __init__(self, rows, layer_present=True):
        self.cursor_obj = _FakeCursor(rows, layer_present=layer_present)
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def close(self):
        self.closed = True


def _install_fake_db(monkeypatch, rows, layer_present=True):
    conn = _FakeConn(rows, layer_present=layer_present)
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/fake")
    monkeypatch.setattr(gcr.psycopg2, "connect", lambda *_a, **_k: conn)
    return conn


# ---------------------------------------------------------------------------
# Fetcher — three-state semantics
# ---------------------------------------------------------------------------

class TestCoastalFetcher:
    def test_no_database_url_fails_not_outside(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        assert get_coastal_inundation_live(-33.5, 151.3)["status"] == "failed"

    def test_connect_error_fails_not_outside(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://fake/fake")

        def _boom(*_a, **_k):
            raise RuntimeError("db down")

        monkeypatch.setattr(gcr.psycopg2, "connect", _boom)
        assert get_coastal_inundation_live(-33.5, 151.3)["status"] == "failed"

    def test_no_rows_is_checked_outside_only_after_presence_probe(self, monkeypatch):
        conn = _install_fake_db(monkeypatch, [], layer_present=True)
        out = get_coastal_inundation_live(-33.71, 150.31)
        assert out["status"] == "outside"
        assert out["query_basis"] == "point"
        assert len(conn.cursor_obj.executed) == 2   # intersection + presence probe
        assert conn.closed

    def test_no_rows_with_layer_absent_fails_closed(self, monkeypatch):
        # Deleted/never-loaded layer must read "not assessed", never a
        # universal outside-the-extent all-clear (Sol finding 2).
        _install_fake_db(monkeypatch, [], layer_present=False)
        assert get_coastal_inundation_live(-33.71, 150.31)["status"] == "failed"

    def test_lot_wkt_uses_lot_polygon_basis(self, monkeypatch):
        conn = _install_fake_db(monkeypatch, [])
        out = get_coastal_inundation_live(
            -33.5, 151.3, lot_wkt="POLYGON((151.3 -33.5,151.31 -33.5,151.31 -33.51,151.3 -33.5))"
        )
        assert out["query_basis"] == "lot"
        sql, params = conn.cursor_obj.executed[0]
        assert "ST_GeomFromText" in sql
        assert "coastal_inundation" in sql

    def test_point_fallback_passes_lng_lat(self, monkeypatch):
        conn = _install_fake_db(monkeypatch, [])
        get_coastal_inundation_live(-33.5, 151.3)
        sql, params = conn.cursor_obj.executed[0]
        assert "ST_Point" in sql
        assert params == (gcr._COASTAL_IK_LIKE, 151.3, -33.5)

    def test_query_scoped_to_2025_publication(self, monkeypatch):
        # A later publication/scenario loaded under the same layer_type must
        # never render under the 2025 SSP3-7.0 attribution (Sol finding 1).
        conn = _install_fake_db(monkeypatch, [])
        get_coastal_inundation_live(
            -33.5, 151.3, lot_wkt="POLYGON((151.3 -33.5,151.31 -33.5,151.31 -33.51,151.3 -33.5))"
        )
        sql, params = conn.cursor_obj.executed[0]
        assert "instrument_key LIKE" in sql
        assert params[0].startswith(r"estuary\_inund\_2025\_s370")
        assert params[0].endswith("%")

    def test_most_frequent_tier_selected_per_year(self, monkeypatch):
        _install_fake_db(monkeypatch, [_ROW_2050_F1, _ROW_2050_F4, _ROW_2100_F2])
        out = get_coastal_inundation_live(-33.5, 151.3)
        assert out["status"] == "intersects"
        assert out["years"][2050]["days_per_year"] == 182.5   # f4 beats f1
        assert "50%" in out["years"][2050]["value"]
        assert out["years"][2100]["days_per_year"] == 3.65

    def test_year_figures_read_from_rows_never_composed(self, monkeypatch):
        _install_fake_db(monkeypatch, [_ROW_2100_F2])
        out = get_coastal_inundation_live(-33.5, 151.3)
        assert out["years"][2100]["value"] == _ROW_2100_F2[1]

    def test_malformed_rows_skipped_all_malformed_fails_closed(self, monkeypatch):
        _install_fake_db(monkeypatch, [("junk_key", "junk", 1.0),
                                       ("estuary_inund_2025_s370_y2050_f1", "v", None)])
        # Rows intersected but none parseable — a data defect must NOT render
        # as a checked outside (CI-3).
        assert get_coastal_inundation_live(-33.5, 151.3)["status"] == "failed"

    def test_malformed_row_does_not_poison_valid_year(self, monkeypatch):
        _install_fake_db(monkeypatch, [("junk_key", "junk", 9.9), _ROW_2050_F1])
        out = get_coastal_inundation_live(-33.5, 151.3)
        assert out["status"] == "intersects"
        assert list(out["years"]) == [2050]


# ---------------------------------------------------------------------------
# Per-year sentence — figures read, not composed
# ---------------------------------------------------------------------------

class TestCoastalYearRow:
    def test_reads_days_and_pct_from_row(self):
        row = _coastal_year_row(2050, {"days_per_year": 182.5,
                                       "value": _ROW_2050_F4[1]})
        assert "2050" in row
        assert "182.5 days per year" in row
        assert "(50% of days)" in row
        assert "SSP3-7.0" in row

    def test_missing_days_returns_none_never_a_sentence(self):
        assert _coastal_year_row(2050, {"value": "whatever"}) is None
        assert _coastal_year_row(2050, {}) is None

    def test_unparseable_pct_omits_parenthetical(self):
        row = _coastal_year_row(2100, {"days_per_year": 3.65, "value": "no pct here"})
        assert "3.65 days per year" in row
        assert "(" not in row.split("days per year")[1].split(",")[0]


# ---------------------------------------------------------------------------
# Section builder — render states + golden wording
# ---------------------------------------------------------------------------

class TestBuildCoastalLines:
    def test_none_payload_omits_section(self):
        assert build_coastal_inundation_lines(None)["render"] is False

    def test_unrecognised_status_omits_section(self):
        assert build_coastal_inundation_lines({"status": "banana"})["render"] is False

    def test_failed_renders_not_assessed_without_extent_claim(self):
        out = build_coastal_inundation_lines({"status": "failed"})
        assert out["render"] is True
        assert out["state"] == "failed"
        assert "not assessed" in out["status_line"].lower()
        assert "outside" not in out["status_line"].lower()   # CI-1
        assert out["rows"] == []
        assert out["source_line"] is None

    def test_outside_carries_scope_and_source(self):
        out = build_coastal_inundation_lines(
            {"status": "outside", "query_basis": "lot"},
            report_date="25 July 2026",
        )
        assert out["state"] == "outside"
        assert "outside the mapped estuarine tidal inundation extent" in out["status_line"]
        assert "does NOT cover open-coast/surf" in out["scope_line"]
        assert "NSW Estuarine Inundation" in out["source_line"]
        assert "25 July 2026" in out["source_line"]
        assert out["basis_note"] is None

    def test_intersects_renders_rows_sorted_by_year(self):
        out = build_coastal_inundation_lines({
            "status": "intersects", "query_basis": "lot",
            "years": {2100: {"days_per_year": 3.65, "value": _ROW_2100_F2[1]},
                      2050: {"days_per_year": 182.5, "value": _ROW_2050_F4[1]}},
        })
        assert out["state"] == "intersects"
        assert len(out["rows"]) == 2
        assert out["rows"][0].startswith("2050")
        assert out["rows"][1].startswith("2100")
        assert out["framing"] is not None
        assert out["scope_line"] is not None
        assert out["source_line"] is not None

    def test_point_basis_gets_caveat_note(self):
        out = build_coastal_inundation_lines({
            "status": "intersects", "query_basis": "point",
            "years": {2050: {"days_per_year": 1.0, "value": _ROW_2050_F1[1]}},
        })
        assert out["basis_note"] is not None
        assert "lot polygon was unavailable" in out["basis_note"]

    def test_string_year_keys_tolerated(self):
        # JSON round-trips turn int keys into strings — must not crash or drop.
        out = build_coastal_inundation_lines({
            "status": "intersects", "query_basis": "lot",
            "years": {"2050": {"days_per_year": 182.5, "value": _ROW_2050_F4[1]}},
        })
        assert out["state"] == "intersects"
        assert out["rows"][0].startswith("2050")

    def test_intersects_with_nothing_renderable_fails_closed(self):
        out = build_coastal_inundation_lines(
            {"status": "intersects", "query_basis": "lot", "years": {}}
        )
        assert out["state"] == "failed"                       # CI-3
        assert "not assessed" in out["status_line"].lower()
        assert out["rows"] == []
        assert out["source_line"] is None

    def test_no_verdict_or_liability_language_in_any_state(self):
        payloads = [
            {"status": "failed"},
            {"status": "outside", "query_basis": "point"},
            {"status": "intersects", "query_basis": "point",
             "years": {2050: {"days_per_year": 182.5, "value": _ROW_2050_F4[1]},
                       2100: {"days_per_year": 3.65, "value": _ROW_2100_F2[1]}}},
        ]
        for payload in payloads:
            out = build_coastal_inundation_lines(payload, report_date="25 July 2026")
            emitted = " ".join(
                s for s in ([out["framing"], out["scope_line"], out["source_line"],
                             out["status_line"], out["basis_note"]] + out["rows"]) if s
            )
            assert not _LIABILITY_RE.search(emitted), emitted
            assert "at risk" not in emitted.lower()

    def test_every_extent_claim_scoped_estuarine(self):
        # The coverage anchor is "estuarine" — an extent claim without the
        # scope sentence lets "coastal" coverage be inferred.
        for payload in ({"status": "outside", "query_basis": "lot"},
                        {"status": "intersects", "query_basis": "lot",
                         "years": {2050: {"days_per_year": 1.0,
                                          "value": _ROW_2050_F1[1]}}}):
            out = build_coastal_inundation_lines(payload)
            assert "estuarine" in out["scope_line"].lower()
