"""Review history on an older PDF does not stop a chapter's current approval from committing.

prior-art-checked: tests/test_dcp_commit_approved_records_hash.py, test_dcp_commit_refuses_section_loss.py and
test_dcp_commit_rederives_precinct_keys.py all replace find_committable_chapters with a stub returning
hash_variants=1, so none of them runs its SQL. This runs the real query against an in-memory SQLite database, which
supports COUNT(DISTINCT ...) FILTER and MAX(...) FILTER the same way Postgres does.

Measured 2026-09-15: every Woollahra chapter had 2-3 distinct source hashes across all of its queue rows but only 1
among its approved rows. The query counted superseded and rejected history too, so each chapter would have been
skipped as "approved rows span multiple source hashes", or as a stale approval when MAX picked an old hash, however
carefully its current rows were reviewed.
"""
import os
import sqlite3
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://x")
os.environ.setdefault("R2_BUCKET_NAME", "x")
os.environ.setdefault("R2_ACCESS_KEY_ID", "x")
os.environ.setdefault("R2_SECRET_ACCESS_KEY", "x")
os.environ.setdefault("R2_ACCOUNT_ID", "x")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import dcp_commit_approved as dca  # noqa: E402

CURRENT, OLDER = "h2-current", "h9-older"  # the older hash sorts LAST, so an unfiltered MAX picks it


def _cursor(queue, registry_hash=CURRENT):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE dcp_chapter_registry (council TEXT, chapter_key TEXT, content_hash TEXT, is_active BOOLEAN)")
    con.execute("CREATE TABLE dcp_review_queue (council TEXT, chapter_key TEXT, status TEXT, source_content_hash TEXT)")
    con.execute("INSERT INTO dcp_chapter_registry VALUES ('woollahra', 'chapter-e3', ?, 1)", (registry_hash,))
    con.executemany("INSERT INTO dcp_review_queue VALUES ('woollahra', 'chapter-e3', ?, ?)", queue)
    return con.cursor()


def _rows(status, source_hash, n):
    return [(status, source_hash)] * n


def test_superseded_history_on_an_older_pdf_does_not_block_the_current_approval():
    cur = _cursor(_rows("approved", CURRENT, 3) + _rows("superseded", OLDER, 5))
    [chapter] = dca.find_committable_chapters(cur)
    assert chapter["hash_variants"] == 1, "old superseded rows were counted as a second version of the approval"
    assert chapter["approved_hash"] == CURRENT, "the approval was dated to a PDF nobody approved against"


def test_rejected_history_on_an_older_pdf_does_not_block_either():
    cur = _cursor(_rows("approved", CURRENT, 2) + _rows("rejected", OLDER, 4))
    [chapter] = dca.find_committable_chapters(cur)
    assert chapter["hash_variants"] == 1 and chapter["approved_hash"] == CURRENT


def test_approvals_that_span_two_pdfs_are_still_reported_as_two():
    """Confusable negative: the guard must keep catching an approval that really is mixed."""
    cur = _cursor(_rows("approved", CURRENT, 2) + _rows("approved", OLDER, 2))
    [chapter] = dca.find_committable_chapters(cur)
    assert chapter["hash_variants"] == 2


def test_a_pending_row_or_a_rejection_on_the_current_pdf_still_blocks():
    assert dca.find_committable_chapters(_cursor(_rows("approved", CURRENT, 2) + _rows("pending", CURRENT, 1))) == []
    assert dca.find_committable_chapters(_cursor(_rows("approved", CURRENT, 2) + _rows("rejected", CURRENT, 1))) == []
