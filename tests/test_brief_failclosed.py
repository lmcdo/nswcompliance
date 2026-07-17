"""S1 fail-closed: the _unwrap_or_default helper preserves the failure signal,
and the failsoft lint blocks the silent-false-negative anti-pattern.

This is the railguard for the strata/overlay/controls class — a FAILED fetch must
never be re-stamped as a confident AUTHORITATIVE negative.
"""
import os
import subprocess
import sys
import textwrap
from unittest.mock import MagicMock

from services.intelligence_brief import (
    _unwrap_or_default,
    _build_planning_controls,
    _build_environmental,
    DataField,
    ConfidenceLevel,
)
from services.constraint_models import ShadowScenario
from conveyancing_db import fetch_nearby_das

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINT = os.path.join(REPO, "scripts", "lint_brief_failsoft.py")

NA = ConfidenceLevel.NOT_AVAILABLE
AUTH = ConfidenceLevel.AUTHORITATIVE
_CONTROLS = {"zone": "R2", "height": "9", "fsr": "0.5:1", "flood_epi": False}
_OVERLAYS = {"overlays": [], "covered_layers": [], "proximity_m": {}}


# --- WO-4: nearby-DA cost key-null -----------------------------------------

def test_nearby_da_includes_cost_of_development():
    # The row: (pid, addr, suburb, status, lat, lng, lodged, det, dev_type, cost).
    # Place it at the query point so it passes the distance filter.
    lat, lng = -33.86, 151.10
    row = ("DA/1", "1 Smith St", "Concord", "Approved", lat, lng, "2025-06-01", None, None, 250000)
    cur = MagicMock()
    cur.fetchall.return_value = [row]
    conn = MagicMock()
    conn.cursor.return_value = cur
    out = fetch_nearby_das(conn, lat, lng, radius_m=200)
    assert len(out) == 1
    assert out[0]["cost_of_development"] == 250000  # WO-4: was omitted -> always null


# --- WO-5: dead sun-geometry fields removed --------------------------------

def test_shadow_scenario_drops_dead_sun_fields():
    # The shadow service never emits these and nothing renders them — they must
    # be gone so there's no always-null field reading a key that isn't produced.
    assert "sun_altitude_deg" not in ShadowScenario.model_fields
    assert "sun_azimuth_deg" not in ShadowScenario.model_fields
    # the real shadow-direction datum stays
    assert "shadow_direction_deg" in ShadowScenario.model_fields


# --- WO-3: controls fail-closed --------------------------------------------

def test_controls_failed_is_not_available():
    pc = _build_planning_controls({}, _OVERLAYS, controls_failed=True)
    assert pc.zone.confidence == NA
    assert pc.height.confidence == NA
    assert pc.fsr.confidence == NA


def test_controls_success_stays_authoritative():
    pc = _build_planning_controls(_CONTROLS, _OVERLAYS, controls_failed=False)
    assert pc.zone.confidence == AUTH
    assert pc.zone.value == "R2"


def test_controls_failed_does_not_downgrade_lot_dimensions():
    # lot_dims comes from geometry/area, not controls — a controls failure must not blank it.
    pc = _build_planning_controls({}, _OVERLAYS, lot_area_m2=500.0, controls_failed=True)
    assert pc.lot_dimensions.confidence == AUTH
    assert pc.lot_dimensions.value is not None


# --- WO-2: environmental overlays fail-closed ------------------------------

def test_overlays_failed_blanks_overlay_fields_not_authoritative():
    env = _build_environmental(_CONTROLS, _OVERLAYS, None, overlays_failed=True, controls_failed=False)
    # purely overlay-derived -> NOT_AVAILABLE on overlay failure
    assert env.overlays.confidence == NA
    assert env.overlay_coverage.confidence == NA


def test_flood_epi_survives_when_only_overlays_fail():
    # overlays failed but controls succeeded -> flood_epi keeps the portal answer, not NOT_AVAILABLE.
    env = _build_environmental(_CONTROLS, _OVERLAYS, None, overlays_failed=True, controls_failed=False)
    assert env.flood_epi.confidence == AUTH


def test_flood_epi_not_available_when_both_sources_fail():
    env = _build_environmental({}, _OVERLAYS, None, overlays_failed=True, controls_failed=True)
    assert env.flood_epi.confidence == NA
    assert env.flood_epi.value is None


def test_environmental_genuine_success_is_authoritative():
    env = _build_environmental(_CONTROLS, _OVERLAYS, None, overlays_failed=False, controls_failed=False)
    assert env.flood_epi.confidence == AUTH
    assert env.overlays.confidence == AUTH


# --- _unwrap_or_default: three-state semantics -----------------------------

def test_failed_fetch_is_flagged():
    df = DataField(value=None, confidence=ConfidenceLevel.NOT_AVAILABLE, source="x")
    value, failed = _unwrap_or_default(df, {"is_strata": False})
    assert failed is True
    assert value == {"is_strata": False}


def test_success_with_value_not_flagged():
    df = DataField(value={"is_strata": True}, confidence=ConfidenceLevel.AUTHORITATIVE, source="x")
    value, failed = _unwrap_or_default(df, {"is_strata": False})
    assert failed is False
    assert value == {"is_strata": True}


def test_genuine_empty_is_not_a_failure():
    # value=None but confidence is NOT not_available = "queried, genuinely empty".
    # This MUST NOT be flagged as failed (that's the legitimate AUTHORITATIVE-null case).
    df = DataField(value=None, confidence=ConfidenceLevel.AUTHORITATIVE, source="x")
    value, failed = _unwrap_or_default(df, {"is_strata": False})
    assert failed is False
    assert value == {"is_strata": False}


# --- the failsoft lint actually blocks the anti-pattern --------------------

def _run_lint(tmp_path, content: str):
    f = tmp_path / "sample.py"
    f.write_text(textwrap.dedent(content))
    p = subprocess.run([sys.executable, LINT, str(f)], capture_output=True, text=True)
    return p.returncode, p.stdout


def test_lint_blocks_unannotated_anti_pattern(tmp_path):
    code, out = _run_lint(tmp_path, """
        def f(foo_df):
            x = foo_df.value or {"a": 1}
            return x
    """)
    assert code == 1
    assert "fail-soft" in out.lower()


def test_lint_blocks_computed_default(tmp_path):
    code, _ = _run_lint(tmp_path, """
        def f(controls_df):
            c = controls_df.value or parse_controls([])
            return c
    """)
    assert code == 1


def test_lint_passes_with_helper(tmp_path):
    code, _ = _run_lint(tmp_path, """
        def f(foo_df):
            value, failed = _unwrap_or_default(foo_df, {"a": 1})
            return value
    """)
    assert code == 0


def test_lint_passes_with_ok_ack(tmp_path):
    code, _ = _run_lint(tmp_path, """
        def f(foo_df):
            x = foo_df.value or {"a": 1}  # failsoft-ok: degrades correctly
            return x
    """)
    assert code == 0


def test_lint_allows_scalar_default(tmp_path):
    # `or None` / `or 0` / `or False` are harmless scalar defaults, not the
    # container/computed masking shape — they should not trip the lint.
    code, _ = _run_lint(tmp_path, """
        def f(foo_df):
            n = foo_df.value or None
            return n
    """)
    assert code == 0


# ---------------------------------------------------------------------------
# #745 D5 — legit-empty must never masquerade as a data gap
# ---------------------------------------------------------------------------


def test_coastal_legit_empty_is_not_a_gap():
    """A SUCCESSFUL overlay query with zero coastal layers is checked-CLEAR:
    it must keep a success confidence, carry NO reason, and never appear in
    collect_gaps (the live Concord brief showed it under Data Gaps)."""
    from services.intelligence_brief import ConfidenceLevel, collect_gaps
    env = _build_environmental(_CONTROLS, _OVERLAYS, None,
                               overlays_failed=False, controls_failed=False)
    ch = env.coastal_hazards
    assert ch.value is None  # no coastal layers at this fixture location
    assert ch.confidence != ConfidenceLevel.NOT_AVAILABLE
    assert ch.reason is None

    class _Stub:
        environmental_constraints = env
    gaps = [g for g in collect_gaps(_Stub()) if "coastal" in g.field.lower()]
    assert gaps == []


def test_coastal_overlay_failure_is_still_a_gap():
    """The other side of the contract: a FAILED overlay query must remain
    NOT_AVAILABLE with a reason — fail-closed is not weakened."""
    from services.intelligence_brief import ConfidenceLevel
    env = _build_environmental(_CONTROLS, _OVERLAYS, None,
                               overlays_failed=True, controls_failed=False)
    ch = env.coastal_hazards
    assert ch.confidence == ConfidenceLevel.NOT_AVAILABLE
    assert ch.reason is not None
