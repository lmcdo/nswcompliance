"""OC-20 part (c): DQ-145 is a ratchet that may only fall, and it can fail.

prior-art-checked: tests for a sub-check added to scripts/outreach_claim_checks.py; the other sub-check
tests (test_outreach_claim_checks_plan_and_zone.py, _ranges_and_citations.py) cover different functions.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import dq_probe_live  # noqa: E402
import outreach_claim_checks as occ  # noqa: E402


class _Cursor:
    def __init__(self, count, seen, fail=False):
        self._count, self._seen, self._fail = count, seen, fail

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        if self._fail:
            raise RuntimeError("column does not exist")
        self._seen.append((sql, params))

    def fetchone(self):
        return (self._count,)


class _Conn:
    def __init__(self, count, fail=False):
        self.count, self.fail, self.seen = count, fail, []

    def cursor(self):
        return _Cursor(self.count, self.seen, self.fail)

    def close(self):
        pass


def _run(monkeypatch, conn):
    monkeypatch.setattr(occ, "_connect", lambda: conn)
    return occ.unproven_citations_only_fall()


def test_at_ceiling_passes(monkeypatch):
    verdict, detail = _run(monkeypatch, _Conn(occ.DQ145_CEILING))
    assert verdict == occ.PASS
    assert str(occ.DQ145_CEILING) in detail


def test_one_above_ceiling_fails(monkeypatch):
    verdict, _ = _run(monkeypatch, _Conn(occ.DQ145_CEILING + 1))
    assert verdict == occ.FAIL


def test_falling_passes(monkeypatch):
    assert _run(monkeypatch, _Conn(0))[0] == occ.PASS


def test_no_database_is_unknown_not_pass(monkeypatch):
    monkeypatch.setattr(occ, "_connect", lambda: None)
    assert occ.unproven_citations_only_fall()[0] == occ.UNKNOWN


def test_broken_query_fails(monkeypatch):
    assert _run(monkeypatch, _Conn(0, fail=True))[0] == occ.FAIL


def test_runs_the_dq145_probe_sql_itself(monkeypatch):
    conn = _Conn(5)
    _run(monkeypatch, conn)
    _headline, sql, params, _meaning = dq_probe_live.PROBES["DQ-145"]
    assert conn.seen == [(sql, params)]


def test_oc20_is_wired_with_all_three_parts():
    checks = occ.CLAIMS["OC-20"]
    assert occ.unproven_citations_only_fall in checks
    assert len(checks) >= 3
