"""The quality report must not crash on a rule with no section heading (ku_ring_gai, 2026-10-13: 8 such rows;
the crash made the gate fail and the run skip enrichment).

prior-art-checked: no existing test drives report_granularity with a NULL header.
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import dcp_quality_report as dqr  # noqa: E402


def test_header_prints_are_null_safe():
    src = inspect.getsource(dqr)
    assert "w['header'][:60]" not in src and "m['header'][:50]" not in src
    assert "(w['header'] or '(no heading)')" in src and "(m['header'] or '(no heading)')" in src
