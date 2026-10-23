"""r2_monitor.retry_rate_limited: on HTTP 429, pause the whole host, longer each time, within a budget.

Real case (run 2, 2026-10-23, dcp_monitor_chapter_results run_id=2): all 36 rate_limited
chapters were on www.innerwest.nsw.gov.au, in a repeating pattern of ~15 checked then 5-7
blocked. The old code waited at most 60 s once, then skipped -- so each block lost 5-7 chapters.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import os  # noqa: E402

# r2_monitor reads these at import; nothing here touches R2 or the database.
for _k in ("R2_ACCOUNT_ID", "R2_BUCKET_NAME", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "DATABASE_URL"):
    os.environ.setdefault(_k, "unused-in-this-test")

import r2_monitor as m  # noqa: E402

IW = "https://www.innerwest.nsw.gov.au/ArticleDocuments/x/chapter.pdf"


class Host:
    """A host that answers 429 until `blocked_for` seconds of sleeping have passed."""

    def __init__(self, blocked_for: float):
        self.blocked_for, self.slept, self.heads = blocked_for, 0.0, 0

    def sleep(self, s):
        self.slept += s

    def head(self, url):
        self.heads += 1
        return {"status": 429} if self.slept < self.blocked_for else {"status": 200}


@pytest.fixture(autouse=True)
def _fresh():
    m._host_pause_spent.clear()
    yield
    m._host_pause_spent.clear()


def test_block_longer_than_old_60s_wait_is_recovered():
    # Known-wrong case: the old code slept 60 s once and skipped. A 3-minute block now recovers.
    h = Host(blocked_for=170)
    assert m.retry_rate_limited(IW, head=h.head, sleep=h.sleep)["status"] == 200
    assert h.slept >= 170


def test_block_past_the_listed_pauses_is_recovered_within_budget():
    # Sol HIGH: blocked 500 s; the three listed pauses end at 480 s with 1,320 s of budget left.
    h = Host(blocked_for=500)
    assert m.retry_rate_limited(IW, head=h.head, sleep=h.sleep)["status"] == 200


def test_short_block_recovers_on_first_pause():
    h = Host(blocked_for=30)
    assert m.retry_rate_limited(IW, head=h.head, sleep=h.sleep)["status"] == 200
    assert h.heads == 1 and h.slept == m.HOST_PAUSES[0]


def test_pauses_grow():
    assert list(m.HOST_PAUSES) == sorted(m.HOST_PAUSES) and m.HOST_PAUSES[0] < m.HOST_PAUSES[-1]


def test_permanent_block_stops_at_budget_and_reports_429():
    h = Host(blocked_for=10 ** 9)
    spent = 0.0
    for _ in range(50):  # 50 chapters on one blocked host
        assert m.retry_rate_limited(IW, head=h.head, sleep=h.sleep)["status"] == 429
    assert h.slept <= m.HOST_PAUSE_BUDGET
    heads_at_budget = h.heads
    m.retry_rate_limited(IW, head=h.head, sleep=h.sleep)
    assert h.heads == heads_at_budget  # budget spent: no more requests to the host at all
    assert h.slept == pytest.approx(m.HOST_PAUSE_BUDGET)
    spent = m._host_pause_spent[m._get_domain(IW)]
    assert spent == pytest.approx(h.slept)


def test_budget_is_per_host():
    h = Host(blocked_for=10 ** 9)
    for _ in range(20):
        m.retry_rate_limited(IW, head=h.head, sleep=h.sleep)
    other = Host(blocked_for=30)
    assert m.retry_rate_limited("https://www.cityofsydney.nsw.gov.au/a.pdf",
                                head=other.head, sleep=other.sleep)["status"] == 200


def test_non_429_answer_is_returned_as_is():
    # A 403 after a pause is not a rate limit: hand it back for the caller's WAF path.
    calls = []
    ans = m.retry_rate_limited(IW, head=lambda u: calls.append(u) or {"status": 403}, sleep=lambda s: None)
    assert ans["status"] == 403 and len(calls) == 1


def test_pause_order_is_listed_then_longest_repeated():
    slept = []
    m.retry_rate_limited(IW, head=lambda u: {"status": 429}, sleep=slept.append)
    assert slept[:4] == [60.0, 120.0, 300.0, 300.0]
    assert sum(slept) == pytest.approx(m.HOST_PAUSE_BUDGET)
