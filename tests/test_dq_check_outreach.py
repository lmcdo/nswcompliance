"""The outreach stop signal in scripts/dq_check.py (--outreach).

prior-art-checked: extends tests/test_dq_check.py's subject without touching its fixtures; that file
tests the DQ ledger against the committed markdown and would need a real ledger for every case. These
tests drive _outreach() and run_one() with in-memory rows, so each exit code is forced, not assumed.

Spec: ~/.claude/plans/ce-outreach-readiness-benchmark-SPEC-2026-09-11.md, claim set decided 2026-09-14.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "dq_check.py"
_CHECKS = _ROOT / ".claude" / "dq_checks.json"


def _load():
    spec = importlib.util.spec_from_file_location("dq_check_outreach_under_test", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def dq():
    return _load()


def _row(declared: str, check=("python", "-c", "pass"), **extra) -> dict:
    return {"kind": "outreach_claim", "claim": "a claim", "declared": declared,
            "check": list(check) if check else None, "blocks_outreach": True, **extra}


def _run(dq, monkeypatch, rows: dict, verdicts: dict[str, tuple[str, str]]) -> int:
    monkeypatch.setattr(dq, "load_checks", lambda: rows)
    monkeypatch.setattr(dq, "run_one", lambda cid, spec, verbose=False: verdicts[cid])
    return dq._outreach()


def test_ready_only_when_every_blocking_claim_is_true_and_passes(dq, monkeypatch):
    rows = {"OC-1": _row("true"), "OC-2": _row("true")}
    ok = ("OK", "declared 'true' and the check agrees")
    assert _run(dq, monkeypatch, rows, {"OC-1": ok, "OC-2": ok}) == 0


def test_a_claim_known_false_is_not_ready_but_not_a_failure(dq, monkeypatch):
    rows = {"OC-1": _row("true"), "OC-2": _row("false")}
    ok = ("OK", "agrees")
    assert _run(dq, monkeypatch, rows, {"OC-1": ok, "OC-2": ok}) == 3


def test_a_claim_with_no_check_is_never_ready(dq, monkeypatch):
    rows = {"OC-1": _row("true"), "OC-2": _row("false", check=None, why_no_check="needs a probe")}
    verdicts = {"OC-1": ("OK", "agrees"), "OC-2": ("NO-CHECK", "needs a probe")}
    assert _run(dq, monkeypatch, rows, verdicts) == 3


def test_a_contradicted_claim_fails_whatever_else_is_true(dq, monkeypatch):
    rows = {"OC-1": _row("true"), "OC-2": _row("false"), "OC-3": _row("true")}
    verdicts = {"OC-1": ("OK", "agrees"), "OC-2": ("OK", "agrees"), "OC-3": ("RED", "declared TRUE but fails")}
    assert _run(dq, monkeypatch, rows, verdicts) == 1


def test_could_not_verify_is_never_ready(dq, monkeypatch):
    rows = {"OC-1": _row("true"), "OC-2": _row("true")}
    verdicts = {"OC-1": ("OK", "agrees"), "OC-2": ("UNKNOWN", "no database")}
    assert _run(dq, monkeypatch, rows, verdicts) == 2
    rows = {"OC-1": _row("unverifiable")}
    assert _run(dq, monkeypatch, rows, {}) == 2


def test_rows_that_do_not_block_outreach_are_ignored(dq, monkeypatch):
    rows = {"OC-1": _row("true"), "OC-9": {**_row("false"), "blocks_outreach": False},
            "DQ-1": {"declared": "open", "check": None}}
    assert _run(dq, monkeypatch, rows, {"OC-1": ("OK", "agrees")}) == 0


def test_no_blocking_rows_at_all_is_a_failure_not_a_pass(dq, monkeypatch):
    assert _run(dq, monkeypatch, {"DQ-1": {"declared": "open"}}, {}) == 1


@pytest.mark.parametrize("declared,exit_code,verdict", [
    ("true", 0, "OK"), ("true", 1, "RED"),
    ("false", 1, "OK"), ("false", 0, "RED"),
])
def test_run_one_enforces_true_and_false_both_ways(dq, declared, exit_code, verdict):
    spec = {"declared": declared, "check": ["python", "-c", f"import sys; sys.exit({exit_code})"]}
    got, detail = dq.run_one("OC-1", spec)
    assert got == verdict, detail
    if verdict == "RED":
        assert declared.upper() in detail


def test_outreach_rows_are_not_ledger_orphans(dq, monkeypatch):
    """OC rows are not markdown ledger rows; the coverage check must not call them orphans."""
    real = dq.load_checks()
    monkeypatch.setattr(dq, "load_checks", lambda: {**real, "OC-99": _row("false")})
    monkeypatch.setattr("sys.argv", ["dq_check.py", "--coverage"])
    assert dq.main() == 0


def test_the_committed_claim_set_matches_the_decision():
    """The 2026-09-14 decision: 17 claims, 14 and 15 retired (their rows assert the claim is gone),
    every row blocks outreach, and every declared state is one the runner enforces."""
    checks = json.loads(_CHECKS.read_text(encoding="utf-8"))["checks"]
    oc = {k: v for k, v in checks.items() if k.startswith("OC-")}
    assert sorted(oc, key=lambda k: int(k[3:])) == [f"OC-{i}" for i in range(1, 18)]
    for cid, row in oc.items():
        assert row.get("blocks_outreach") is True, cid
        assert row.get("declared") in {"true", "false", "unverifiable"}, cid
        assert row.get("claim"), cid
        assert row.get("check") or row.get("why_no_check"), f"{cid} has neither a check nor a reason"
    assert "retired" in oc["OC-14"]["claim"].lower() and "retired" in oc["OC-15"]["claim"].lower()
