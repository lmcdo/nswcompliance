"""The house page and the DQ-153 red number must say the same thing.

The red number (scripts/dq_probe_live.py PROBES["DQ-153"]) and the page notice
(frontend-nextjs/lib/plan-confirmed.ts) were written in two languages. A Sol review
found them disagreeing once (30 days on the page, 14 in the probe; a never-checked
chapter counted red but silent on the page). These tests keep them in step.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))

import manual_intake  # noqa: E402

_PLAN_TS = (_ROOT / "frontend-nextjs" / "lib" / "plan-confirmed.ts").read_text(encoding="utf-8")
_real_db = pytest.mark.skipif(os.getenv("PYTEST_REAL_DB") != "1", reason="set PYTEST_REAL_DB=1 to run against the real database")


def _page_sql() -> str:
    return re.search(r"PLAN_CONFIRMED_SQL = `(.*?)`", _PLAN_TS, re.S).group(1)


def test_page_and_red_number_use_the_same_number_of_days():
    import dq_probe_live

    page_days = int(re.search(r"PLAN_STALE_AFTER_DAYS\s*=\s*(\d+)", _PLAN_TS).group(1))
    probe_days = int(re.search(r"interval '(\d+) days'", dq_probe_live.PROBES["DQ-153"][1]).group(1))
    assert page_days == probe_days == manual_intake.STALE_DAYS


def test_page_query_has_the_same_three_signals_as_the_probe():
    import dq_probe_live

    probe = " ".join(dq_probe_live.PROBES["DQ-153"][1].split())
    page = " ".join(_page_sql().split())
    for piece in ("= 'waf_blocked'", "ORDER BY x.checked_at DESC, x.id DESC LIMIT 1", "url_last_checked IS NULL"):
        assert piece in page and piece in probe, piece


@pytest.mark.database
@_real_db
def test_page_shows_a_notice_for_exactly_the_councils_the_red_number_counts():
    """Run the page's own SQL for every serving council on the live database. The councils that would show a
    notice (over 14 days, never checked, or blocked) must be exactly the councils manual_intake lists."""
    import datetime as dt

    import dq_db

    sql = _page_sql().replace("$1", "%s")
    listed = {r["council"] for r in manual_intake.blocked_chapters()}
    conn = dq_db.connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT r.council FROM dcp_chapter_registry r WHERE r.is_active AND r.doc_type = 'dcp' "
            "AND EXISTS (SELECT 1 FROM regulatory_provisions p WHERE p.source_council = r.council "
            "AND p.source_chapter_key = r.chapter_key AND p.is_current AND p.v2_is_actionable)"
        )
        councils = [c for (c,) in cur.fetchall()]
        now = dt.datetime.now(dt.timezone.utc)
        shows = set()
        for c in councils:
            cur.execute(sql, (c,))
            chapters, oldest, never, blocked = cur.fetchone()
            if chapters and (blocked or never or (oldest is not None and now - oldest > dt.timedelta(days=14))):
                shows.add(c)
    finally:
        conn.close()
    assert councils, "no serving councils read: the comparison would prove nothing"
    assert shows == listed
