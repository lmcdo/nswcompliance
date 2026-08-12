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


def test_accepts_a_node_command(qg, critical):
    """A node harness is a real check and must not be rejected for being JS.

    Added 2026-08-12. The CI workflows are checked by
    scripts/main_red_alarm_logic_check.js, and the gate rejected that command
    outright because `node` and `.js` were absent from _LOOKS_RUNNABLE_RE while
    `python`, `.py`, `.sh` and `.ts` were present. A gate that rejects genuine
    checks on the basis of language teaches people to reword commands until it
    shuts up, which is how the whole falsifiability idea dies.
    """
    errors = qg.check_falsifiable(
        {"falsifiable_check": {
            "command": "node scripts/main_red_alarm_logic_check.js .github/workflows/main-red-alarm.yml",
            "fails_when": "any of the six decision paths returns the wrong state; 4 of the 6 must report broken",
            "observed_red": "ran it against the broken workflow and 4 of the 6 paths reported broken, exit 1",
        }},
        critical,
    )
    assert not errors, f"the gate rejected a runnable node command: {errors}"


def test_widening_for_node_did_not_admit_prose(qg, critical):
    """The counterweight to the test above.

    Adding alternations to _LOOKS_RUNNABLE_RE trades false rejections for the
    risk of false acceptances, so the widening is only safe while plain English
    is still refused. Note the bait: this sentence contains the word "nodes",
    which a careless \\b-less pattern would match.
    """
    errors = qg.check_falsifiable(
        {"falsifiable_check": {
            "command": "inspect the graph nodes and confirm the counts look right",
            "fails_when": "any stored zone code is absent from that LGA land use table",
        }},
        critical,
    )
    assert any("does not look" in e and "runnable" in e for e in errors), (
        "widening the runnable-command pattern let prose through"
    )


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
            "observed_red": "before the repair it printed 14 offending rows and exited 1",
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


# ── file_line is derived, never typed ───────────────────────────────────────

def test_resolve_file_lines_fixes_a_stale_number(qg, tmp_path):
    """A stale line number must be corrected from the AST, not reported at.

    Added 2026-08-12 after hand-typed line numbers were rejected five times in
    one session, each costing a full gate round trip to fix a number a parser
    computes in milliseconds. Deriving it removes the class.
    """
    import json

    (tmp_path / "scripts").mkdir()
    src = tmp_path / "scripts" / "thing.py"
    src.write_text("# a\n# b\n# c\ndef target():\n    return 1\n", encoding="utf-8")

    report = tmp_path / "r.json"
    report.write_text(json.dumps({
        "functions": [{"name": "target", "file_line": "scripts/thing.py:99999"}]
    }), encoding="utf-8")

    notes = qg.resolve_file_lines(str(report), str(tmp_path))

    assert notes, "a stale line was left uncorrected"
    written = json.loads(report.read_text(encoding="utf-8"))
    assert written["functions"][0]["file_line"] == "scripts/thing.py:4"


def test_resolve_file_lines_does_not_repoint_a_missing_function(qg, tmp_path):
    """The FILE and NAME stay the author's claim; only the line is derived.

    Silently repointing a reference at a same-named function elsewhere would
    convert a caught error into a wrong reference that passes — the opposite of
    what this gate is for.
    """
    import json

    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "thing.py").write_text("def other():\n    pass\n",
                                                   encoding="utf-8")
    report = tmp_path / "r.json"
    report.write_text(json.dumps({
        "functions": [{"name": "absent", "file_line": "scripts/thing.py:1"}]
    }), encoding="utf-8")

    notes = qg.resolve_file_lines(str(report), str(tmp_path))

    assert any("not defined" in n for n in notes)
    written = json.loads(report.read_text(encoding="utf-8"))
    assert written["functions"][0]["file_line"] == "scripts/thing.py:1", (
        "an absent function was silently repointed instead of reported"
    )


# ── Practice 2: watch it fail first ──────────────────────────────────────────

def test_rejects_a_check_nobody_watched_fail(qg, critical):
    """A prediction is not evidence.

    DQ-30 shipped broken behind a "0% drift" verification that could not fail in
    any circumstance, and nobody had ever seen it red. Requiring the OUTPUT the
    check printed while the defect was present is the cheapest available proof
    that somebody ran it against the broken state.
    """
    errors = qg.check_falsifiable(
        {"falsifiable_check": {
            "command": "python scripts/validate_zone_code_validity.py",
            "fails_when": "it exits non-zero when any stored zone code is absent from "
                          "lep_zone_coverage for that row's LGA",
        }},
        critical,
    )
    assert any("observed_red" in e for e in errors), (
        "the gate accepted a check nobody had watched fail"
    )


def test_rejects_observed_red_that_is_a_claim_not_an_output(qg, critical):
    """"It failed" is the assertion under test, not evidence for it."""
    errors = qg.check_falsifiable(
        {"falsifiable_check": {
            "command": "python scripts/validate_zone_code_validity.py",
            "fails_when": "it exits non-zero when any stored zone code is absent from "
                          "lep_zone_coverage for that row's LGA",
            "observed_red": "yes",
        }},
        critical,
    )
    assert any("observed_red" in e for e in errors)
