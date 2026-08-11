"""Golden tests — conveyancing PDF TOD-catchment uplift section (FLOOR ONLY).

Scope decision (2026-07-07): the paid conveyancing PDF renders the TOD
catchment disclosure + instrument attribution + the conservative as-of-right
baseline from the capacity engine. It does NOT quantify the uplift ceiling
(the "up to N dwellings" figure). The block suppresses on strata and non-TOD
lots. Every figure comes from the engine result object — never composed here.

Fixtures are recorded live responses (2026-07-07) for 67 Warialda St Kogarah
(propId 1545912, R4, in a SEPP Housing TOD catchment):
  kogarah_tod_catchment.json   fetch_tod_catchment result (in_tod True)
  kogarah_capacity_floor.json  compute_constraint_arithmetic floor result

Pure-logic: the engine + ArcGIS seams are monkeypatched, no live HTTP.
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
    build_tod_uplift_lines,
    get_tod_uplift_live,
)

FIXTURES = Path(__file__).parent / "fixtures" / "tod_uplift"


def _fx(name: str):
    with open(FIXTURES / name, encoding="utf-8") as fh:
        return json.load(fh)


class _Capacity:
    """Attribute-access stand-in for ConstraintArithmeticResult (the builder
    reads the engine result via getattr — recorded fixture drives it)."""

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def _kogarah_capacity(**overrides):
    data = dict(_fx("kogarah_capacity_floor.json"))
    data.update(overrides)
    return _Capacity(**data)


def _kogarah_tod():
    return dict(_fx("kogarah_tod_catchment.json"))


# ---------------------------------------------------------------------------
# build_tod_uplift_lines — render gate + floor-only content
# ---------------------------------------------------------------------------

class TestTodUpliftRenderGate:
    def test_not_in_tod_does_not_render(self):
        out = build_tod_uplift_lines({"in_tod": False}, _kogarah_capacity(), False)
        assert out["render"] is False

    def test_tod_lookup_failed_renders_not_assessed_never_vanishes(self):
        """THE fix-4 pin: fetch_tod_catchment None (both layers failed) must
        RENDER as not-assessed. The old doctrine returned render False —
        the section vanished, indistinguishable from 'checked, not in a
        catchment' (DQ-36's silent-omission twin). FAILS on pre-change code."""
        out = build_tod_uplift_lines(None, _kogarah_capacity(), False)
        assert out["render"] is True
        assert out["not_assessed"] is True
        assert "could not be completed" in out["disclosure"]
        assert "no claim" in out["disclosure"].lower()
        # No uplift/held-back content for an unknown catchment:
        assert out["held_line"] is None
        assert out["ledger"] == []

    def test_tod_lookup_failed_on_strata_stays_suppressed(self):
        """Strata suppression outranks the failed-check disclosure — a single
        strata lot is not independently redevelopable either way."""
        out = build_tod_uplift_lines(None, _kogarah_capacity(), True)
        assert out["render"] is False

    def test_strata_lot_suppresses_block(self):
        """A single strata lot is not independently redevelopable → no block."""
        out = build_tod_uplift_lines(_kogarah_tod(), _kogarah_capacity(), True)
        assert out["render"] is False

    def test_in_tod_non_strata_with_capacity_renders(self):
        out = build_tod_uplift_lines(_kogarah_tod(), _kogarah_capacity(), False)
        assert out["render"] is True
        assert out["not_assessed"] is False

    def test_in_tod_capacity_none_is_not_assessed_not_silent(self):
        """In a TOD catchment but the engine failed → the catchment is STILL
        disclosed and the baseline states 'Not assessed', never a fabricated
        figure. Mutation: returning render False here hides a known TOD lot."""
        out = build_tod_uplift_lines(_kogarah_tod(), None, False)
        assert out["render"] is True
        assert out["not_assessed"] is True
        assert out["baseline"].startswith("Not assessed")
        assert not re.search(r"\d+\s*m", out["baseline"])  # no envelope figure


class TestTodUpliftFloorContent:
    def test_disclosure_names_the_instrument_verbatim(self):
        out = build_tod_uplift_lines(_kogarah_tod(), _kogarah_capacity(), False)
        assert "Transport Oriented Development (TOD) catchment" in out["disclosure"]
        assert "State Environmental Planning Policy (Housing) 2021" in out["disclosure"]

    def test_baseline_dwelling_count_comes_from_engine_result(self):
        """Mutation guard: the dwelling number is READ from the engine object.
        A hard-coded number would not track this override."""
        out1 = build_tod_uplift_lines(_kogarah_tod(), _kogarah_capacity(), False)
        assert "1 dwelling (detached dwelling)" in out1["baseline"]
        out5 = build_tod_uplift_lines(
            _kogarah_tod(),
            _kogarah_capacity(as_of_right_dwellings=5, as_of_right_form="multi_dwelling_housing"),
            False,
        )
        assert "5 dwellings (multi-dwelling housing)" in out5["baseline"]

    def test_baseline_gfa_and_binding_from_engine(self):
        out = build_tod_uplift_lines(_kogarah_tod(), _kogarah_capacity(), False)
        assert "904 m² gross floor area" in out["baseline"]
        assert "FSR is the binding control on maximum GFA" in out["baseline"]

    def test_baseline_states_subject_to_da(self):
        out = build_tod_uplift_lines(_kogarah_tod(), _kogarah_capacity(), False)
        assert "subject to a development application" in out["baseline"]

    def test_held_line_present_and_names_the_hold_back(self):
        out = build_tod_uplift_lines(_kogarah_tod(), _kogarah_capacity(), False)
        assert "does not quantify that upper limit" in out["held_line"]
        assert "State Environmental Planning Policy (Housing) 2021" in out["held_line"]

    def test_ceiling_is_never_quantified_anywhere_in_block(self):
        """The whole point of floor-only: no 'up to N', no ceiling dwelling
        count, no max_permitted figure anywhere in the rendered strings."""
        cap = _kogarah_capacity(
            max_permitted_form="residential_flat_building",
            max_permitted_dwellings=17,
            ceiling_from_lmr=True,
        )
        out = build_tod_uplift_lines(_kogarah_tod(), cap, False)
        blob = " ".join(filter(None, [
            out["disclosure"], out["baseline"], out["held_line"], out["scope"],
            *out["ledger"],
        ]))
        assert "up to" not in blob.lower()
        assert "17" not in blob
        assert "residential flat" not in blob.lower()
        assert "ceiling" not in blob.lower()

    def test_ledger_names_inputs_and_engine_gaps(self):
        out = build_tod_uplift_lines(_kogarah_tod(), _kogarah_capacity(), False,
                                     lot_area_source="NSW Valuer General")
        ledger = " | ".join(out["ledger"])
        assert "Lot area: 904 m² (NSW Valuer General)" in ledger
        assert "LEP height limit: 14.5 m" in ledger
        assert "LEP floor space ratio: 1" in ledger
        # the engine's own gap wording is carried into the ledger verbatim
        assert any("No DCP setback controls" in row for row in out["ledger"])

    def test_missing_inputs_named_not_defaulted(self):
        """A baseline without its inputs named is the D1 defect class — missing
        LEP controls render as 'not available', never a silent default."""
        cap = _kogarah_capacity(lep_height_m=None, lep_fsr=None, gaps=[])
        out = build_tod_uplift_lines(_kogarah_tod(), cap, False)
        ledger = " | ".join(out["ledger"])
        assert "LEP height limit: not available" in ledger
        assert "LEP floor space ratio: not available" in ledger

    def test_scope_line_disclaims_approval_outcome(self):
        out = build_tod_uplift_lines(_kogarah_tod(), _kogarah_capacity(), False)
        assert "not\na development approval outcome" in out["scope"] or \
               "not a development approval outcome" in out["scope"]
        assert "consent authority" in out["scope"]


# ---------------------------------------------------------------------------
# get_tod_uplift_live — fetch orchestration (floor-only, engine gated)
# ---------------------------------------------------------------------------

class TestGetTodUpliftLive:
    def _patch(self, monkeypatch, tod_result=None, tod_exc=None, capture=None):
        import portal_constraints as pc
        import constraint_arithmetic as ca

        def _fetch(lat, lng):
            if tod_exc:
                raise tod_exc
            return tod_result

        def _compute(**kwargs):
            if capture is not None:
                capture.update(kwargs)
            return _kogarah_capacity()

        monkeypatch.setattr(pc, "fetch_tod_catchment", _fetch)
        monkeypatch.setattr(ca, "compute_constraint_arithmetic", _compute)

    def test_not_in_tod_skips_engine(self, monkeypatch):
        cap = {}
        self._patch(monkeypatch, tod_result={"in_tod": False}, capture=cap)
        tod, capacity = get_tod_uplift_live(
            -33.9, 151.1, {"height": "9", "fsr": "0.5"}, {"lot_area_m2": 600},
        )
        assert tod == {"in_tod": False}
        assert capacity is None
        assert cap == {}  # engine never called

    def test_in_tod_runs_engine_floor_only(self, monkeypatch):
        cap = {}
        self._patch(monkeypatch, tod_result=_kogarah_tod(), capture=cap)
        tod, capacity = get_tod_uplift_live(
            -33.96, 151.13, {"height": "14.5", "fsr": "1"}, {"lot_area_m2": 904.2},
        )
        assert tod["in_tod"] is True
        assert capacity is not None
        # FLOOR ONLY — the engine must be called with no ceiling dev_type
        assert cap["ceiling_dev_type"] is None
        assert cap["dev_type"] == "dwelling_house"
        assert cap["lot_area_m2"] == 904.2

    def test_in_tod_no_lot_area_skips_engine(self, monkeypatch):
        cap = {}
        self._patch(monkeypatch, tod_result=_kogarah_tod(), capture=cap)
        tod, capacity = get_tod_uplift_live(
            -33.96, 151.13, {"height": "14.5", "fsr": "1"}, {"lot_area_m2": None},
        )
        assert tod["in_tod"] is True
        assert capacity is None
        assert cap == {}

    def test_catchment_lookup_failure_returns_none_none(self, monkeypatch):
        self._patch(monkeypatch, tod_exc=RuntimeError("both layers down"))
        tod, capacity = get_tod_uplift_live(
            -33.96, 151.13, {"height": "14.5", "fsr": "1"}, {"lot_area_m2": 904.2},
        )
        assert tod is None
        assert capacity is None
