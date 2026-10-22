"""classify_pending against the REAL registry, inside one transaction that is rolled back.

Why: the runner's SELECT and its guarded UPDATEs are SQL; canned rows cannot show a wrong
predicate. Each test inserts its own waiting row, runs, checks, and rolls back: nothing is written.

Run: PYTEST_REAL_DB=1 DATABASE_URL=<pooler url> pytest -m database tests/test_verifyops_classify_real_db.py -o addopts=
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

pytestmark = pytest.mark.database
DOCS = {d["id"]: d for d in json.loads(
    (ROOT / "tests/fixtures/verifyops/new_docs_2026-10-23.json").read_text(encoding="utf-8"))}


@pytest.fixture
def conn():
    if os.environ.get("PYTEST_REAL_DB") != "1" or not os.environ.get("DATABASE_URL"):
        pytest.skip("Real-DB test: PYTEST_REAL_DB=1 DATABASE_URL=... pytest -m database")
    import psycopg2
    real = psycopg2.connect(os.environ["DATABASE_URL"], options="-c statement_timeout=30000")

    class OneTransaction:
        """The real connection, except commit does nothing: the test rolls everything back."""
        cursor = real.cursor
        rollback = real.rollback

        @staticmethod
        def commit():
            pass

    yield OneTransaction()
    real.rollback()
    real.close()


def _waiting_row(cur, url: str) -> int:
    cur.execute("""INSERT INTO dcp_chapter_registry (council, dcp_name, doc_type, chapter_key, chapter_label,
                       council_url, is_active, needs_extraction, registration_status, check_failures,
                       created_at, updated_at)
                   VALUES ('zz_test_council', 'Test DCP', 'dcp', %s, 'Test document', %s,
                       FALSE, FALSE, 'auto_detected', 0, NOW(), NOW()) RETURNING id""", ("zz_" + url.lower(), url))
    return cur.fetchone()[0]


def _state(cur, row_id):
    cur.execute("SELECT registration_status, detected_category FROM dcp_chapter_registry WHERE id = %s", (row_id,))
    return cur.fetchone()


def _only(conn, row_id):
    """Restrict pending() to the test row so real waiting rows are never downloaded."""
    import verifyops_classify as V
    real = V.pending
    return lambda c: [r for r in real(c) if r["id"] == row_id]


def test_a_guideline_is_rejected_as_not_dcp(conn, monkeypatch):
    import verifyops_classify as V
    cur = conn.cursor()
    rid = _waiting_row(cur, "https://zz.test/guideline.pdf")
    monkeypatch.setattr(V, "pending", _only(conn, rid))
    monkeypatch.setattr(V, "read_document", lambda b: {"sha256": "x", "first_pages_text": DOCS[807]["first_pages_text"]})
    assert V.classify_pending(conn, lambda u: b"", date(2026, 10, 23), dry_run=False) == {"not_dcp": 1}
    assert _state(cur, rid) == ("rejected", "not_dcp")


def test_a_dcp_with_no_date_stays_waiting_and_is_not_fetched_again(conn, monkeypatch):
    import verifyops_classify as V
    cur = conn.cursor()
    rid = _waiting_row(cur, "https://zz.test/chapter.pdf")
    monkeypatch.setattr(V, "read_document", lambda b: {"sha256": "y", "first_pages_text": DOCS[814]["first_pages_text"]})
    only = _only(conn, rid)
    monkeypatch.setattr(V, "pending", only)
    assert V.classify_pending(conn, lambda u: b"", date(2026, 10, 23), dry_run=False) == {"dcp": 1}
    assert _state(cur, rid) == ("auto_detected", "dcp_needs_person")
    assert only(conn) == []                       # the real pending() query now skips it


def test_the_same_address_as_another_row_is_a_duplicate(conn, monkeypatch):
    import verifyops_classify as V
    cur = conn.cursor()
    first = _waiting_row(cur, "https://zz.test/same.pdf")
    cur.execute("UPDATE dcp_chapter_registry SET registration_status = 'confirmed' WHERE id = %s", (first,))
    rid = _waiting_row(cur, "https://ZZ.test/same.pdf/")
    monkeypatch.setattr(V, "pending", _only(conn, rid))
    monkeypatch.setattr(V, "read_document", lambda b: {"sha256": "z", "first_pages_text": ["anything"]})
    assert V.classify_pending(conn, lambda u: b"", date(2026, 10, 23), dry_run=False) == {"duplicate": 1}
    assert _state(cur, rid) == ("rejected", "duplicate")


def test_a_failed_download_is_untouched_and_retried(conn, monkeypatch):
    import verifyops_classify as V
    cur = conn.cursor()
    rid = _waiting_row(cur, "https://zz.test/down.pdf")
    monkeypatch.setattr(V, "pending", _only(conn, rid))

    def boom(u):
        raise ConnectionError
    assert V.classify_pending(conn, boom, date(2026, 10, 23), dry_run=False) == {"retry": 1}
    assert _state(cur, rid) == ("auto_detected", None)


def test_dry_run_writes_nothing(conn, monkeypatch):
    import verifyops_classify as V
    cur = conn.cursor()
    rid = _waiting_row(cur, "https://zz.test/dry.pdf")
    monkeypatch.setattr(V, "pending", _only(conn, rid))
    monkeypatch.setattr(V, "read_document", lambda b: {"sha256": "w", "first_pages_text": DOCS[807]["first_pages_text"]})
    V.classify_pending(conn, lambda u: b"", date(2026, 10, 23), dry_run=True)
    assert _state(cur, rid) == ("auto_detected", None)


def test_a_row_already_decided_is_never_overwritten(conn):
    import verifyops_classify as V
    cur = conn.cursor()
    rid = _waiting_row(cur, "https://zz.test/decided.pdf")
    cur.execute("UPDATE dcp_chapter_registry SET registration_status = 'confirmed' WHERE id = %s", (rid,))
    assert V.write_verdict(conn, rid, {"verdict": "not_dcp"}) == 0
    assert _state(cur, rid)[0] == "confirmed"
