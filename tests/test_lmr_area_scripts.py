"""The area-check accuracy scripts: the scorer must fail the pipeline step on a bad result, and the test script must import.

Each runs in a child process: these are command-line scripts, and tests/conftest_mocks.py stubs pyproj in this process.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCORE = ROOT / "scripts" / "lmr_area" / "area_check_score.py"
TEST_SCRIPT = ROOT / "scripts" / "lmr_area" / "area_check_test.py"


def lot(fix: str, judge: str, judge_walk: float) -> dict:
    return {"address": "x", "anchor": "a", "fix": fix, "fix_code": "walk", "judge": judge, "judge_walk": judge_walk,
            "fix_low": judge_walk - 50, "fix_high": judge_walk + 50, "fix_lean": None, "fix_extra_m": 0}


def run_score(tmp_path: Path, lots: list[dict]) -> subprocess.CompletedProcess:
    (tmp_path / "r.json").write_text(json.dumps({"lots": lots}), encoding="utf-8")
    return subprocess.run([sys.executable, str(SCORE), "r.json"], env={**os.environ, "LMR_WORK": str(tmp_path)},
                          capture_output=True, text=True, timeout=60)


def test_scorer_exits_zero_when_every_check_passes(tmp_path):
    lots = [lot("yes", "yes", 500) for _ in range(10)] + [lot("no", "no", 1500) for _ in range(10)]
    r = run_score(tmp_path, lots)
    assert r.returncode == 0, r.stdout[-600:] + r.stderr[-600:]


def test_scorer_exits_nonzero_on_wrong_yes(tmp_path):
    lots = [lot("yes", "no", 1500) for _ in range(10)] + [lot("no", "no", 1500) for _ in range(10)]
    r = run_score(tmp_path, lots)
    assert r.returncode == 1 and "FAIL" in r.stdout


def test_scorer_exits_nonzero_when_a_break_it_control_passes(tmp_path):
    lots = [lot("yes", "yes", 500) for _ in range(20)]  # "always yes" would match 100%: the sample cannot tell a working check from a stub
    r = run_score(tmp_path, lots)
    assert r.returncode == 1 and "PASS (test too weak)" in r.stdout


def test_test_script_imports_without_name_error():
    r = subprocess.run([sys.executable, str(TEST_SCRIPT), "--help"], capture_output=True, text=True, timeout=60, cwd=ROOT)
    assert "NameError" not in r.stderr, r.stderr[-600:]
    assert r.returncode == 0, r.stderr[-600:]
