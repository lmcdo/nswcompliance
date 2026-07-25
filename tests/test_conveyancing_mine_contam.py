"""Golden-sentence tests for the mine subsidence + contaminated land risk rows.

Three-state contract (services/conveyancing.py wrappers →
scripts/generate_conveyancing_report.py builders):

  {"status": "found", "data": {...}} → warn row stating the finding
  {"status": "empty"}                → checked clear (ok)
  {"status": "failed"} / None / junk → "Not assessed" (note) — NEVER "Clear"

The break-it class guarded here is WO-2: the underlying portal fetchers return
None both for genuine absence and cannot signal their own failure, so any path
that lets a failure render as "Clear" silently understates legal exposure in a
conveyancer-facing document.

Pure-logic tests: no live HTTP, no reportlab rendering.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT / "services"))
sys.path.insert(0, str(_ROOT))

from generate_conveyancing_report import (  # noqa: E402
    build_contaminated_land_row,
    build_mine_subsidence_row,
)


# ---------------------------------------------------------------------------
# Mine subsidence row
# ---------------------------------------------------------------------------

class TestMineSubsidenceRow:
    def test_found_names_district_and_act(self):
        text, style, source = build_mine_subsidence_row(
            {"status": "found", "data": {"district_name": "Newcastle", "last_update": "2024"}}
        )
        assert "Newcastle Mine Subsidence District" in text
        assert "Coal Mine Subsidence Compensation Act 2017" in text
        assert "Subsidence Advisory NSW" in text
        assert style == "warn"
        assert "live query" in source

    def test_found_with_missing_name_stays_generic_warn(self):
        text, style, _ = build_mine_subsidence_row({"status": "found", "data": {}})
        assert "a proclaimed mine subsidence district" in text
        assert style == "warn"
        assert "Clear" not in text

    def test_found_with_none_data_does_not_crash(self):
        text, style, _ = build_mine_subsidence_row({"status": "found", "data": None})
        assert style == "warn"
        assert "mine subsidence district" in text.lower()

    def test_empty_renders_checked_clear(self):
        text, style, _ = build_mine_subsidence_row({"status": "empty"})
        assert text.startswith("Clear")
        assert "live query" in text
        assert style == "ok"

    def test_failed_renders_not_assessed_never_clear(self):
        text, style, _ = build_mine_subsidence_row({"status": "failed"})
        assert text.startswith("Not assessed")
        assert "s10.7" in text
        assert "Clear" not in text
        assert style == "note"

    def test_none_payload_renders_not_assessed(self):
        text, style, _ = build_mine_subsidence_row(None)
        assert text.startswith("Not assessed")
        assert style == "note"

    def test_unrecognised_status_fails_closed(self):
        text, style, _ = build_mine_subsidence_row({"status": "banana"})
        assert text.startswith("Not assessed")
        assert style == "note"


# ---------------------------------------------------------------------------
# Contaminated land row
# ---------------------------------------------------------------------------

def _found(count=1, **site):
    base_site = {
        "name": "Former Gasworks", "street": "1 Test St", "suburb": "Millers Point",
        "management_class": "Regulation under CLM Act", "distance_m": 320,
    }
    base_site.update(site)
    return {"status": "found", "data": {"has_notified_sites": True,
                                        "site_count": count, "nearest_site": base_site}}


class TestContaminatedLandRow:
    def test_found_states_count_nearest_and_proximity_caveat(self):
        text, style, source = build_contaminated_land_row(_found())
        assert "1 notified site on the EPA contaminated land register within 500 m" in text
        assert "Former Gasworks, Millers Point" in text
        assert "~320 m away" in text
        assert "Regulation under CLM Act" in text
        # The buffered query records proximity — the sentence must never claim
        # the subject lot itself is contaminated.
        assert "not contamination of the subject lot" in text
        assert style == "warn"
        assert "500 m radius" in source

    def test_found_plural_sites(self):
        text, _, _ = build_contaminated_land_row(_found(count=3))
        assert "3 notified sites" in text

    def test_found_with_missing_nearest_site_still_renders(self):
        payload = {"status": "found", "data": {"site_count": 2, "nearest_site": None}}
        text, style, _ = build_contaminated_land_row(payload)
        assert "2 notified sites" in text
        assert "Nearest:" not in text
        assert style == "warn"

    def test_found_with_missing_distance_omits_distance_fragment(self):
        text, _, _ = build_contaminated_land_row(_found(distance_m=None))
        assert "~" not in text
        assert "Former Gasworks" in text

    def test_empty_renders_clear_with_register_scope_caveat(self):
        text, style, _ = build_contaminated_land_row({"status": "empty"})
        assert text.startswith("Clear")
        # The register only holds NOTIFIED sites — the clear sentence must not
        # overstate what was checked.
        assert "notified sites only" in text
        assert "not a complete record" in text
        assert style == "ok"

    def test_failed_renders_not_assessed_never_clear(self):
        text, style, _ = build_contaminated_land_row({"status": "failed"})
        assert text.startswith("Not assessed")
        assert "s10.7(5)" in text
        assert "Clear" not in text
        assert style == "note"

    def test_none_payload_renders_not_assessed(self):
        text, style, _ = build_contaminated_land_row(None)
        assert text.startswith("Not assessed")
        assert style == "note"

    def test_zero_site_count_found_falls_back_to_one(self):
        # A "found" payload with a falsy count would read "0 notified sites" —
        # the builder floors it at 1 because found means at least one feature.
        payload = {"status": "found", "data": {"site_count": 0, "nearest_site": None}}
        text, _, _ = build_contaminated_land_row(payload)
        assert "1 notified site" in text
