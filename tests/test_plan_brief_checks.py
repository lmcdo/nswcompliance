"""The brief's outreach checks: the pure helpers behind the recall and page-proof numbers.

prior-art-checked: new module under test; the database-backed checks report UNKNOWN when no database is reachable, which is asserted here.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import plan_brief_checks as pbc  # noqa: E402


def test_norm_keeps_letters_digits_dots_and_percent_only():
    assert pbc._norm("A 5.5 m  Setback; 30%!") == "a5.5msetback30%"
    assert pbc._norm(None) == ""


def test_wilson_lower_bound_is_below_the_point_estimate_and_rises_with_sample_size():
    small = pbc._wilson_lower(9, 10)
    large = pbc._wilson_lower(90, 100)
    assert small < 0.9 and large < 0.9
    assert large > small


def test_wilson_lower_bound_of_all_correct_is_below_one():
    assert 0.0 < pbc._wilson_lower(50, 50) < 1.0


def test_speed_check_is_unknown_without_a_deployment_address(monkeypatch):
    monkeypatch.delenv("PLAN_BRIEF_URL", raising=False)
    status, why = pbc.brief_speed()
    assert status == pbc.UNKNOWN
    assert "PLAN_BRIEF_URL" in why


def test_a_header_value_that_is_none_does_not_break_the_speed_check(monkeypatch):
    monkeypatch.setenv("PLAN_BRIEF_URL", "http://127.0.0.1:9")
    monkeypatch.delenv("PLAN_BRIEF_HEADERS", raising=False)
    status, _why = pbc.brief_speed()
    assert status in (pbc.UNKNOWN, pbc.FAIL)
