"""Data-side semantic validator for dcp_setback_controls (the gate that was missing).

These lock the deterministic signals that catch a setback value mislabelled vs its
source clause — the class of defect (Burwood front 9m/15m from non-setback clauses
P8/P39) that schema validation, the change-only review queue, and the consuming-
engine routing tests all let through. False-positive guards ensure legitimate
tiered controls and terse setback-table rows are NOT flagged.
"""

import pytest

from scripts.validate_dcp_setbacks import (
    conflict_groups,
    foreign_language,
    implausible_magnitude,
    placeholder_rows,
    audit_setback_controls,
    high_severity,
)

# High-severity baseline recorded 2026-06-24 over the live dcp_setback_controls
# table (28 LGAs, 1001 rows). This is a RATCHET: it may only ever be reduced as
# bad rows are corrected, never increased. A new extraction that adds a mislabelled
# setback fails this gate.
LIVE_HIGH_SEVERITY_BASELINE = 10


def _row(**kw):
    base = {
        "lga": "test", "control_type": "front_setback", "dev_type": "dwelling_house",
        "value_min": 6.0, "value_max": None, "unit": "m",
        "condition": None, "source_text": "Front setback shall be 6m to the street boundary.",
        "section_ref": "x",
    }
    base.update(kw)
    return base


# --- CONFLICT (high) -------------------------------------------------------

class TestConflict:
    def test_unconditioned_conflict_is_flagged(self):
        rows = [_row(value_min=9.0, condition=None), _row(value_min=15.0, condition=None)]
        out = conflict_groups(rows)
        assert len(out) == 1 and out[0]["severity"] == "high"

    def test_conflict_with_a_condition_is_not_flagged(self):
        # Tiered control — a condition lets the engine disambiguate; not a defect.
        rows = [_row(value_min=3.0, condition="lots 200-300m2"),
                _row(value_min=6.0, condition="lots >900m2")]
        assert conflict_groups(rows) == []

    def test_single_value_is_not_a_conflict(self):
        assert conflict_groups([_row(value_min=6.0)]) == []


# --- FOREIGN (high) --------------------------------------------------------

class TestForeign:
    def test_duplex_streetscape_clause_flagged(self):
        # Burwood P39 — the real 15m row.
        rows = [_row(value_min=15.0, source_text=(
            "P39 Duplex development will not be supported in streets and sites subject "
            "to Building Appearance and Streetscape Provisions under Section 4.5."))]
        out = foreign_language(rows)
        assert len(out) == 1 and out[0]["severity"] == "high"

    def test_between_facades_separation_flagged(self):
        # Camden — a building-separation rule mislabelled as a front setback.
        rows = [_row(value_min=12.0, source_text=(
            "provide a minimum of 12m between front facades within the development"))]
        assert len(foreign_language(rows)) == 1

    def test_genuine_setback_clause_not_flagged(self):
        rows = [_row(source_text="The front setback shall be a minimum of 6m to the street boundary.")]
        assert foreign_language(rows) == []

    def test_terse_storey_tiered_setback_not_flagged(self):
        # "One storey - 3.5 metres" is a real (terse) rear-setback table row; the
        # word 'storey' alone must NOT trigger a foreign-language flag.
        rows = [_row(control_type="rear_setback", value_min=3.5,
                     source_text="C12 vi. b. One storey - 3.5 metres")]
        assert foreign_language(rows) == []


# --- MAGNITUDE + PLACEHOLDER (advisory) ------------------------------------

class TestAdvisorySignals:
    def test_implausible_front_setback_flagged_advisory(self):
        out = implausible_magnitude([_row(value_min=15.0)])
        assert len(out) == 1 and out[0]["severity"] == "advisory"

    def test_normal_front_setback_not_flagged(self):
        assert implausible_magnitude([_row(value_min=6.0)]) == []

    def test_placeholder_row_flagged_advisory(self):
        rows = [_row(control_type="private_open_space", value_min=24.0,
                     condition="Assumed standard NSW POS min — verify against DCP")]
        out = placeholder_rows(rows)
        assert len(out) == 1 and out[0]["severity"] == "advisory"


# --- Integration: the real Burwood case ------------------------------------

class TestBurwoodRegression:
    def test_burwood_front_setbacks_flagged_high(self):
        rows = [
            _row(value_min=9.0, condition=None,
                 source_text="P8 A full two storey single dwelling would not be considered appropriate"),
            _row(value_min=15.0, condition=None,
                 source_text="P39 Duplex development will not be supported ... Streetscape Provisions"),
            _row(control_type="side_setback", value_min=0.9,
                 source_text="Side setback minimum 0.9m to the boundary."),
            _row(control_type="rear_setback", value_min=3.0,
                 source_text="Rear setback minimum 3m to the rear boundary."),
        ]
        findings = audit_setback_controls(rows)
        highs = high_severity(findings)
        # Caught by CONFLICT (9 vs 15, no condition) AND FOREIGN (P39 duplex/streetscape).
        assert highs, "Burwood front setbacks must be flagged high-severity"
        signals = {f["signal"] for f in highs}
        assert "CONFLICT" in signals and "FOREIGN" in signals
        # The clean side/rear setbacks must NOT be flagged.
        assert not any(f["control_type"] in ("side_setback", "rear_setback") for f in highs)


# --- Standing ratchet over the live table (runs under `pytest -m database`) -

@pytest.mark.database
def test_live_high_severity_within_baseline():
    """The number of high-severity setback defects in production must not grow.

    Runs only when DATABASE_URL is set (the maintenance cron / local). Reduce
    LIVE_HIGH_SEVERITY_BASELINE as the flagged rows are corrected; never raise it.
    """
    from scripts.validate_dcp_setbacks import _fetch_rows

    rows = _fetch_rows()
    highs = high_severity(audit_setback_controls(rows))
    assert len(highs) <= LIVE_HIGH_SEVERITY_BASELINE, (
        f"{len(highs)} high-severity setback defects exceeds the baseline of "
        f"{LIVE_HIGH_SEVERITY_BASELINE} — a new extraction likely mislabelled a "
        f"setback. Offenders: "
        + "; ".join(f"{f['lga']}/{f['control_type']}/{f['signal']}" for f in highs)
    )
