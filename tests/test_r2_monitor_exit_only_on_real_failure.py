"""dcp-monitor exits 1 only for a real failure, not for a blocked chapter, a council server error or a list page.

Real data: Railway showed dcp-monitor CRASHED on every run (2026-09-01 .. 2026-10-25). Runs 5, 7, 8 and 9 each had
exactly one 'failed' chapter -- northern_beaches warringah-dcp-2011-full, 'HEAD returned HTTP 503' -- plus 16
WAF-blocked chapters that the code counted as failed despite its own comment saying it did not.
"""
import re
from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "scripts" / "r2_monitor.py").read_text(encoding="utf-8")


def _block_after(marker: str, n: int = 900) -> str:
    i = SRC.index(marker)
    return SRC[i:i + n]


def test_failed_is_counted_in_exactly_one_place():
    # The one left is the per-chapter real error path (content/parse/DB). Before: 3 places.
    assert len(re.findall(r'results\["failed"\] \+= 1', SRC)) == 1


def test_a_waf_blocked_chapter_is_bucketed_not_failed():
    blk = _block_after('[WAF] HTTP 403 — access denied, skipping (not counted as failure)')
    assert 'results["waf_blocked"].append' in blk and 'results["failed"] +=' not in blk.split("continue")[0]


def test_a_server_error_is_transient():
    blk = _block_after("if isinstance(head_status, int) and head_status >= 500:")
    assert "raise TransientFetchError(" in blk.split("\n\n")[0] or "raise TransientFetchError(" in blk[:700]


def test_a_list_page_error_is_recorded_not_failed():
    blk = _block_after("# counting them here as well would double-count every one.", 600)
    assert 'results["hub_errors"].append' in blk and 'results["failed"] +=' not in blk
    assert '"hub_errors": [],' in SRC


def test_exit_code_contract_unchanged(monkeypatch):
    import os
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    for k in ("R2_ACCOUNT_ID", "R2_BUCKET_NAME", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "DATABASE_URL"):
        if not os.environ.get(k):
            monkeypatch.setenv(k, "unused-in-this-test")  # restored after the test (Sol)
    import r2_monitor as m
    assert m.run_exit_code(0, 0) == 0 and m.run_exit_code(3, 0) == 2 and m.run_exit_code(0, 1) == 1
