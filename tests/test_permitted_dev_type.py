"""GATE-1pt2 range model — realistic built-form FLOOR + permitted CEILING.

The engine no longer selects ``densest(permitted)`` as a single dev_type (that
over-reported: shop_top_housing is permitted-with-consent in low-density R2). Instead:

- the **zone tier** sets the realism ceiling (R2=dual-occ, R3=multi-dwelling,
  R4=residential-flat) — Standard-Instrument structural metadata that only ever caps;
- the **LGA permitted list** filters the form downward (legality);
- the result is a RANGE: an as-of-right floor (dwelling_house) and a permitted ceiling
  (densest form ≤ zone tier ∩ permitted), the realistic upside subject to a DA.

These tests pin the over-report guard (a permitted use denser than the zone tier is
never selected), the LGA-name normalisation that re-enabled the join, and the fail-safe.
"""
import pytest

import services.intelligence_brief as ib
from services.intelligence_brief import (
    _ceiling_within_tier,
    _realistic_forms,
    _norm_lga,
    _bare_lga_from_epi,
    _ZONE_TIER_CEILING,
)


# --- the zone-tier ceiling policy (pure) ------------------------------------

@pytest.mark.parametrize("zone,permitted,expected", [
    # R4 high density: residential flat building is the ceiling and is permitted.
    ("R4", {"residential_flat_building", "dwelling_house"}, "residential_flat_building"),
    # R3 medium density: multi-dwelling is the ceiling.
    ("R3", {"multi_dwelling_housing", "dwelling_house"}, "multi_dwelling_housing"),
    # OVER-REPORT GUARD: RFB is permitted in this R3 but is DENSER than the R3 tier —
    # it must be capped to multi_dwelling_housing, not selected.
    ("R3", {"residential_flat_building", "multi_dwelling_housing", "dwelling_house"},
     "multi_dwelling_housing"),
    # OVER-REPORT GUARD: shop_top is permitted-with-consent in low-density R2 but is
    # above the R2 tier — must be capped to dual_occupancy (the 17-address sweep bug).
    ("R2", {"shop_top_housing", "dual_occupancy", "dwelling_house"}, "dual_occupancy"),
    # R2 with only houses permitted -> dwelling_house.
    ("R2", {"dwelling_house"}, "dwelling_house"),
    # R5 large lot: ceiling is dwelling_house even if denser forms appear permitted.
    ("R5", {"residential_flat_building", "dwelling_house"}, "dwelling_house"),
    # Nothing permitted -> conservative default.
    ("R2", set(), "dwelling_house"),
    # Unknown / non-residential zone -> conservative default tier.
    ("B4", {"residential_flat_building"}, "dwelling_house"),
])
def test_ceiling_within_tier(zone, permitted, expected):
    assert _ceiling_within_tier(zone, permitted) == expected


def test_every_zone_tier_value_is_a_known_engine_form():
    for form in _ZONE_TIER_CEILING.values():
        assert form in ib._ENGINE_FORM_DENSITY


# --- LGA name normalisation (re-enables the join) ---------------------------

def test_norm_lga_collapses_council_naming_variants():
    # All of these refer to the same council and must reduce to the same key.
    assert _norm_lga("Canada Bay Council") == _norm_lga("Canada Bay") == "canada bay"
    assert _norm_lga("Strathfield Municipal Council") == "strathfield"
    assert _norm_lga("Council of the City of Sydney") == "sydney"
    assert _norm_lga("The Hills Shire") == _norm_lga("The Hills Shire Council") == "hills"
    assert _norm_lga("Canterbury-Bankstown") == "canterbury bankstown"


def test_norm_lga_keeps_the_25_table_lgas_distinct():
    tbl = ["Bayside", "Blacktown", "Burwood", "Camden", "Campbelltown", "Canada Bay",
           "Canterbury-Bankstown", "Cumberland", "Fairfield", "Georges River", "Hornsby",
           "Inner West", "Ku-Ring-Gai", "Liverpool", "Northern Beaches", "Parramatta",
           "Penrith", "Randwick", "Ryde", "Strathfield", "Sutherland Shire", "Sydney",
           "The Hills Shire", "Waverley", "Woollahra"]
    keys = [_norm_lga(x) for x in tbl]
    assert len(set(keys)) == len(keys)  # no cross-match


def test_bare_lga_from_epi():
    assert _bare_lga_from_epi("Canada Bay Local Environmental Plan 2013") == "Canada Bay"
    assert _bare_lga_from_epi("Sutherland Shire LEP 2015") == "Sutherland Shire"
    assert _bare_lga_from_epi("not an instrument name") is None
    assert _bare_lga_from_epi("") is None


# --- _realistic_forms over a mocked DB --------------------------------------

class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows
    def execute(self, *a, **k):
        return None
    def fetchall(self):
        return self._rows


class _FakeConn:
    def __init__(self, rows):
        self._rows = rows
    def cursor(self):
        return _FakeCursor(self._rows)
    def close(self):
        return None


def test_realistic_forms_r4_lifts_to_residential_flat(monkeypatch):
    rows = [("Inner West", "residential_flat_buildings"), ("Inner West", "dwelling_houses")]
    monkeypatch.setattr(ib, "_get_db_conn", lambda: _FakeConn(rows))
    floor, ceiling = _realistic_forms("R4", "Inner West Council")  # suffixed name still matches
    assert floor == "dwelling_house"
    assert ceiling == "residential_flat_building"


def test_realistic_forms_r2_caps_shop_top_to_dual_occ(monkeypatch):
    # Penrith R2 genuinely permits shop_top_housing (the sweep finding) — must NOT lift.
    rows = [("Penrith", "shop_top_housing"), ("Penrith", "dual_occupancies"),
            ("Penrith", "dwelling_houses")]
    monkeypatch.setattr(ib, "_get_db_conn", lambda: _FakeConn(rows))
    floor, ceiling = _realistic_forms("R2", "Penrith City Council")
    assert (floor, ceiling) == ("dwelling_house", "dual_occupancy")


def test_realistic_forms_failsafe_on_missing_inputs():
    assert _realistic_forms(None, "Inner West") == ("dwelling_house", "dwelling_house")
    assert _realistic_forms("R4", None) == ("dwelling_house", "dwelling_house")


def test_realistic_forms_failsafe_on_db_error(monkeypatch):
    def _boom():
        raise RuntimeError("DB down")
    monkeypatch.setattr(ib, "_get_db_conn", _boom)
    assert _realistic_forms("R4", "Inner West") == ("dwelling_house", "dwelling_house")


def test_realistic_forms_unonboarded_lga_is_conservative(monkeypatch):
    # zone rows exist for other LGAs but none match the requested one -> dwelling_house.
    rows = [("Inner West", "residential_flat_buildings")]
    monkeypatch.setattr(ib, "_get_db_conn", lambda: _FakeConn(rows))
    assert _realistic_forms("R4", "Wollongong") == ("dwelling_house", "dwelling_house")
