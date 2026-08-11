"""The falsifiability gate must reject the exact claim that caused DQ-30.

On 2026-08-01, DQ-30 was marked "Fixed" on the strength of a "0% drift" check:
re-run the tagger, compare its output to the stored value, observe 0% difference.
That is a self-comparison. When the code itself is wrong, drift is 0% and the
data is still broken — 241 rows, 112 of them live and served, survived it.

The project already had the rule written down ("a completion check must be able
to fail"). It did not prevent the failure, because a rule in a document is not
enforcement. These tests are the enforcement's own enforcement: if the gate ever
stops rejecting that original claim, the guard has silently rotted and this file
goes red.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_QA_GATE = Path(__file__).resolve().parents[1] / "scripts" / "qa_gate.py"


def _load():
    spec = importlib.util.spec_from_file_location("qa_gate_under_test", _QA_GATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def qg():
    return _load()


@pytest.fixture
def critical(qg):
    return qg.TIER_REQUIREMENTS["critical"]


# ── The regression that matters ──────────────────────────────────────────────

def test_rejects_the_original_dq30_claim(qg, critical):
    """The literal verification that let DQ-30 ship broken must not pass."""
    errors = qg.check_falsifiable(
        {"falsifiable_check": {
            "command": "re-run the tagger and compare to the stored values",
            "fails_when": "the recomputed output differs from what is already stored",
        }},
        critical,
    )
    assert errors, "the gate accepted the exact claim that caused DQ-30"
    assert any("SELF-COMPARISON" in e for e in errors)


def test_rejects_missing_field(qg, critical):
    errors = qg.check_falsifiable({}, critical)
    assert len(errors) == 1
    assert "MISSING" in errors[0]


def test_rejects_unrunnable_command(qg, critical):
    errors = qg.check_falsifiable(
        {"falsifiable_check": {
            "command": "eyeball the numbers and confirm they look correct",
            "fails_when": "any stored zone code is absent from that LGA land use table",
        }},
        critical,
    )
    assert any("does not look" in e and "runnable" in e for e in errors)


def test_rejects_fails_when_restating_command(qg, critical):
    cmd = "python scripts/validate_zone_code_validity.py"
    errors = qg.check_falsifiable(
        {"falsifiable_check": {"command": cmd, "fails_when": cmd}}, critical
    )
    assert any("merely repeats" in e for e in errors)


# ── It must not block legitimate work ────────────────────────────────────────

def test_accepts_a_real_ground_truth_check(qg, critical):
    """The check that actually repaired DQ-30's data must pass cleanly."""
    errors = qg.check_falsifiable(
        {"falsifiable_check": {
            "command": "python scripts/validate_zone_code_validity.py",
            "fails_when": "it exits non-zero when any stored zone code is absent from "
                          "lep_zone_coverage for that row's LGA",
        }},
        critical,
    )
    assert errors == [], f"blocked a legitimate ground-truth check: {errors}"


def test_minor_tier_is_exempt(qg):
    """Alarm fatigue is the failure mode of a gate that fires on everything
    (the DQ-34 lesson). A copy tweak has no meaningful falsifiable check."""
    assert qg.check_falsifiable({}, qg.TIER_REQUIREMENTS["minor"]) == []


def test_shallow_fails_when_is_rejected(qg, critical):
    errors = qg.check_falsifiable(
        {"falsifiable_check": {
            "command": "pytest tests/test_qa_gate_falsifiable.py",
            "fails_when": "it fails",
        }},
        critical,
    )
    assert any("too shallow" in e for e in errors)
