"""dcp_page_repair --apply re-measures DQ-145 and says so when the run re-judged proven rules.

2026-10-18: the Ku-ring-gai page repair re-judged two older, already-proven rules as unresolved; only a person
re-measuring noticed. The script now prints DQ-145 before and after, and exits 3 when it rose.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import dcp_page_repair as r  # noqa: E402


def test_a_rise_is_reported_with_the_re_prove_command_and_exit_3(capsys):
    assert r.report_unproven(107, 109, "ku_ring_gai") == 3
    out = capsys.readouterr().out
    assert "107 before, 109 after" in out and "ROSE by 2" in out
    assert "page_proof_council.py --council ku_ring_gai" in out


def test_no_rise_exits_0():
    assert r.report_unproven(107, 107, None) == 0
    assert r.report_unproven(107, 100, None) == 0


def test_an_unmeasured_run_says_so_and_fails_loudly(capsys):
    assert r.report_unproven(None, 107, None) == 4
    assert r.report_unproven(107, None, None) == 4
    assert "not measured" in capsys.readouterr().out


def test_apply_measures_before_and_after_the_write():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "scripts" / "dcp_page_repair.py").read_text(encoding="utf-8")
    before, write, after = (src.index("before = unproven_count(conn)"), src.index("write(conn, todo)"),
                            src.index("report_unproven(before, unproven_count(conn), args.council)"))
    assert before < write < after
