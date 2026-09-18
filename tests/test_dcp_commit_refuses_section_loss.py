"""The commit job refuses a swap that loses most of a chapter's sections.

tests/test_dcp_supersede_guard.py proves the rule. This proves the WIRING: that
dcp_commit_approved.main() measures the chapter before the swap, judges it after,
rolls back on a refusal, fails the run, and lets a named chapter through only when a
person passes --allow-section-loss for it.

The fake database holds one chapter's live section headers. The fake swap replaces
them, exactly as commit_reviewed_from_queue does to the real table inside the same
transaction. If the "before" measurement were taken after the swap, before and after
would match and the first test would go green on nothing -- so it also pins the order.
"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://x")
os.environ.setdefault("R2_BUCKET_NAME", "x")
os.environ.setdefault("R2_ACCESS_KEY_ID", "x")
os.environ.setdefault("R2_SECRET_ACCESS_KEY", "x")
os.environ.setdefault("R2_ACCOUNT_ID", "x")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import dcp_commit_approved as dca  # noqa: E402

COUNCIL, CHAPTER = "marrickville", "part4-s1-low-density"


def headers(prefix, n, rows):
    coded = [f"{prefix}.{i} Heading" for i in range(1, n + 1)]
    return coded + [None] * (rows - n)


class _Cur:
    def __init__(self, db):
        self.db = db
        self.sql = ""

    def execute(self, sql, params=None):
        self.sql = sql

    def fetchall(self):
        # snapshot() asks twice: section headers, then the scrambled rules with their
        # ratios. db["scrambled"] holds (identity, shown ref, ratio) triples; this suite
        # is about section loss, so it defaults to none and the legibility guard is a
        # no-op here rather than silently crashing the commit it is meant to judge.
        if "singles" in self.sql:
            return list(self.db.get("scrambled", []))
        return [(h,) for h in self.db["headers"]]

    def fetchone(self):
        return (len(self.db["headers"]),)

    def close(self):
        pass


class _Conn:
    def __init__(self, db):
        self.db = db
        self.autocommit = False
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return _Cur(self.db)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        pass


def _wire(monkeypatch, before_headers, after_headers):
    db = {"headers": list(before_headers)}
    conn = _Conn(db)
    monkeypatch.setattr(dca.psycopg2, "connect", lambda *a, **k: conn)
    monkeypatch.setattr(dca, "find_committable_chapters", lambda cur: [
        {"council": COUNCIL, "chapter_key": CHAPTER, "approved_hash": "h", "hash_variants": 1}])
    monkeypatch.setattr(dca, "fetch_registry_chapter",
                        lambda cur, council, chapter_key: {"content_hash": "h"})

    def _swap(cur, council, chapter_key, allow_unqueued=False):
        # Records what main() passed, so the override's wiring to the full-replace
        # completeness check is pinned too.
        _swap.seen = allow_unqueued
        db["headers"] = list(after_headers)   # the uncommitted transaction's view
        return (len(before_headers), len(after_headers))

    monkeypatch.setattr(dca, "commit_reviewed_from_queue", _swap)

    # Everything after the commit loop is out of scope here and must not reach a network.
    pipeline = type(sys)("enrichment.pipeline")
    pipeline.run_standard_enrichment = lambda **kw: {}
    pipeline.phase_failures = lambda results: []
    monkeypatch.setitem(sys.modules, "enrichment.pipeline", pipeline)
    dpk = type(sys)("derive_precinct_keys")
    dpk.run = lambda council, apply, validate: 0
    monkeypatch.setitem(sys.modules, "derive_precinct_keys", dpk)
    monkeypatch.setitem(sys.modules, "scripts.derive_precinct_keys", dpk)
    ccc = type(sys)("check_council_completeness")
    ccc.run = lambda **kw: 0
    ccc.send_telegram = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "check_council_completeness", ccc)
    monkeypatch.setitem(sys.modules, "scripts.check_council_completeness", ccc)
    return conn


def test_the_incident_swap_is_rolled_back_and_fails_the_run(monkeypatch, capsys):
    conn = _wire(monkeypatch, headers("4.1", 38, 215), headers("4.1", 8, 26))
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    rc = dca.main()

    out = capsys.readouterr().out
    assert conn.commits == 0, "a swap losing 30 of 38 sections was committed"
    assert conn.rollbacks == 1
    assert rc == 1, "a refused chapter must fail the run, or the refusal is silent"
    assert "REFUSED" in out
    assert f"--allow-section-loss {COUNCIL}/{CHAPTER}" in out


def test_the_named_override_lets_that_chapter_commit(monkeypatch):
    conn = _wire(monkeypatch, headers("4.1", 38, 215), headers("4.1", 8, 26))
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit",
                                      "--allow-section-loss", f"{COUNCIL}/{CHAPTER}"])

    rc = dca.main()

    assert conn.commits == 1 and rc != 1
    # The same override lets that chapter past the unqueued-rule check.
    assert dca.commit_reviewed_from_queue.seen is True


def test_an_override_for_another_chapter_does_not_help(monkeypatch):
    conn = _wire(monkeypatch, headers("4.1", 38, 215), headers("4.1", 8, 26))
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit",
                                      "--allow-section-loss", f"{COUNCIL}/part2-s25-stormwater"])

    assert dca.main() == 1 and conn.commits == 0
    assert dca.commit_reviewed_from_queue.seen is False


def test_an_ordinary_amendment_commits(monkeypatch):
    """Confusable negative: 20 sections -> 18 is an amendment. Refusing it would make
    the guard something people switch off."""
    conn = _wire(monkeypatch, headers("2.25", 20, 48), headers("2.25", 18, 44))
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    rc = dca.main()

    assert conn.commits == 1 and rc != 1
