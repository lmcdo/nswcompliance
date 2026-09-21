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
        # latest_approved_batch: which extraction run would be committed. It unpacks
        # (created_at, count) pairs, so returning the header rows here raised
        # "not enough values to unpack" and failed the commit it exists to measure.
        if "GROUP BY created_at" in self.sql:
            return list(self.db.get("batches", [("2026-09-20T00:00:00Z", 1)]))
        # enforce_fidelity: the graded rows of that batch. None by default, so the
        # fidelity guard is a no-op in a suite about section loss -- and, because it
        # declines to judge an ungraded batch rather than passing it, that is a
        # deliberate abstention and not a silent pass.
        if "fidelity_status" in self.sql:
            return list(self.db.get("graded", []))
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


def _wire(monkeypatch, before_headers, after_headers, graded=()):
    db = {"headers": list(before_headers), "graded": list(graded)}
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


# ---------------------------------------------------------------------------
# The fidelity guard, wired through the same main().
#
# dcp_fidelity_gate grades every queued row against the council's own PDF and writes
# fidelity_status. Measured 2026-09-20: this worker contained no reference to that
# column at all, so a row the gate had checked against the source and rejected
# committed exactly like a verified one. These pin that it now cannot.
# ---------------------------------------------------------------------------

def _graded(good, bad):
    return ([(f"ok{i}", "grounded", "") for i in range(good)]
            + [(f"bad{i}", "failed", "section_collapsed") for i in range(bad)])


def test_a_batch_that_fails_its_own_source_check_is_refused(monkeypatch, capsys):
    """Sections and rule counts both survive here -- 20 -> 18, an ordinary amendment
    that commits in the test above. The ONLY thing wrong is that a quarter of the rows
    do not match the PDF they claim to come from, which nothing on this path could see."""
    conn = _wire(monkeypatch, headers("2.25", 20, 48), headers("2.25", 18, 44),
                 graded=_graded(90, 30))
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    rc = dca.main()

    assert conn.commits == 0, "a batch a quarter of which failed verification committed"
    assert rc == 1
    assert "REFUSED" in capsys.readouterr().out


def test_a_batch_within_the_bar_still_commits(monkeypatch):
    """Confusable negative. 2 of 120 is 1.7% -- what a normal re-read does. A guard that
    refused this would be switched off within a week."""
    conn = _wire(monkeypatch, headers("2.25", 20, 48), headers("2.25", 18, 44),
                 graded=_graded(118, 2))
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    assert dca.main() != 1 and conn.commits == 1


def test_an_ungraded_batch_is_not_silently_passed_as_clean(monkeypatch, capsys):
    """No graded rows means the gate never looked, which is not the same as passing.
    The commit proceeds -- refusing every ungraded chapter would stop the pipeline
    dead -- but it must SAY so, or 'no news' reads as verification that never happened."""
    conn = _wire(monkeypatch, headers("2.25", 20, 48), headers("2.25", 18, 44), graded=())
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    dca.main()

    out = capsys.readouterr().out
    assert conn.commits == 1
    assert "not judged" in out, "an unchecked batch passed without saying it was unchecked"


def test_the_fidelity_override_is_separate_from_the_section_loss_one(monkeypatch):
    """--allow-section-loss must not double as permission to publish rows the source
    check rejected. They are different decisions and one person may be entitled to make
    only one of them."""
    conn = _wire(monkeypatch, headers("2.25", 20, 48), headers("2.25", 18, 44),
                 graded=_graded(90, 30))
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit",
                                      "--allow-section-loss", f"{COUNCIL}/{CHAPTER}"])
    assert dca.main() == 1 and conn.commits == 0

    conn2 = _wire(monkeypatch, headers("2.25", 20, 48), headers("2.25", 18, 44),
                  graded=_graded(90, 30))
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit",
                                      "--allow-fidelity", f"{COUNCIL}/{CHAPTER}"])
    assert dca.main() != 1 and conn2.commits == 1
