"""Migration 113 against a throwaway Postgres: unproven NEW state-law text cannot be served; proof appliers still pass.

Needs PostgreSQL server binaries (initdb, pg_ctl): found on PATH, in $PG_BIN, or under C:/Program Files/PostgreSQL/*/bin.
Skips with that reason otherwise, and without PYTEST_REAL_DB=1 (conftest_mocks stubs psycopg2). Never touches
DATABASE_URL:  PYTEST_REAL_DB=1 python -m pytest -m database tests/test_migration_113_state_law_gate.py -o addopts=
"""
import glob
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")
# deselected by default like every real-database test; it uses a throwaway local server, never DATABASE_URL
pytestmark = pytest.mark.database
MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / "113_state_law_publish_gate.sql"


def _pg_bin():
    for cand in [os.environ.get("PG_BIN")] + [str(Path(p).parent) for p in [shutil.which("initdb")] if p] \
            + sorted(glob.glob("C:/Program Files/PostgreSQL/*/bin"), reverse=True) + sorted(glob.glob("/usr/lib/postgresql/*/bin"), reverse=True):
        exe = ".exe" if sys.platform == "win32" else ""
        if cand and Path(cand, "initdb" + exe).exists() and Path(cand, "pg_ctl" + exe).exists():
            return Path(cand)
    return None


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    if os.environ.get("PYTEST_REAL_DB") != "1":
        pytest.skip("psycopg2 is stubbed by conftest_mocks; run with PYTEST_REAL_DB=1 (never touches DATABASE_URL)")
    b = _pg_bin()
    if b is None:
        pytest.skip("no PostgreSQL server binaries (initdb/pg_ctl); set PG_BIN to run the migration 113 trigger test")
    data = tmp_path_factory.mktemp("pg") / "data"
    subprocess.run([str(b / "initdb"), "-D", str(data), "-U", "t", "-A", "trust", "-E", "UTF8"], check=True,
                   capture_output=True)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    log = data.parent / "pg.log"
    # no capture_output: the server inherits the pipes and the call would never return (Windows)
    subprocess.run([str(b / "pg_ctl"), "-D", str(data), "-l", str(log), "-w", "-t", "60", "-o",
                    f"-p {port} -h 127.0.0.1", "start"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   stdin=subprocess.DEVNULL, timeout=90)
    try:
        conn = psycopg2.connect(host="127.0.0.1", port=port, user="t", dbname="postgres")
        cur = conn.cursor()
        cur.execute("""CREATE TABLE regulatory_provisions (id serial PRIMARY KEY, document_id text, ref_number text,
            provision_text text, source_council text, is_current boolean, v2_is_actionable boolean,
            citation_status text, citation_source_path text, citation_checked_at timestamptz)""")
        cur.execute(MIGRATION.read_text(encoding="utf-8"))
        conn.commit()
        yield conn
        conn.close()
    finally:
        subprocess.run([str(b / "pg_ctl"), "-D", str(data), "-m", "immediate", "stop"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=60)


def _ins(cur, council=None, served=True, status=None, text="t"):
    cur.execute("INSERT INTO regulatory_provisions (document_id, ref_number, provision_text, source_council, is_current,"
                " v2_is_actionable, citation_status) VALUES ('D', '1', %s, %s, TRUE, %s, %s) RETURNING id",
                (text, council, served, status))
    return cur.fetchone()[0]


def _commit_fails(conn) -> bool:
    try:
        conn.commit()
        return False
    except psycopg2.Error as e:
        conn.rollback()
        return e.pgcode == "23514"


def test_unproven_new_state_row_cannot_be_served(db):
    _ins(db.cursor())
    assert _commit_fails(db)


def test_proven_withheld_and_council_rows_insert(db):
    cur = db.cursor()
    _ins(cur, status="proven")
    _ins(cur, served=False)
    _ins(cur, council="hornsby")
    db.commit()


def test_text_change_then_proof_in_one_transaction_passes(db):
    cur = db.cursor()
    rid = _ins(cur, status="proven")
    db.commit()
    cur.execute("UPDATE regulatory_provisions SET provision_text = 'new words' WHERE id = %s", (rid,))
    cur.execute("SELECT citation_status FROM regulatory_provisions WHERE id = %s", (rid,))
    assert cur.fetchone()[0] is None                       # the text change voided the proof
    cur.execute("UPDATE regulatory_provisions SET citation_status = 'proven', citation_checked_at = now() WHERE id = %s",
                (rid,))
    db.commit()                                            # the applier's shape: text, then proof, one transaction


def test_text_change_left_unproven_is_refused(db):
    cur = db.cursor()
    rid = _ins(cur, status="proven")
    db.commit()
    cur.execute("UPDATE regulatory_provisions SET provision_text = 'other words' WHERE id = %s", (rid,))
    assert _commit_fails(db)


def test_reenabling_or_turning_council_row_into_state_law_needs_proof(db):
    cur = db.cursor()
    a = _ins(cur, served=False)
    c = _ins(cur, council="hornsby")
    db.commit()
    cur.execute("UPDATE regulatory_provisions SET v2_is_actionable = TRUE WHERE id = %s", (a,))
    assert _commit_fails(db)
    cur = db.cursor()
    cur.execute("UPDATE regulatory_provisions SET source_council = NULL WHERE id = %s", (c,))
    assert _commit_fails(db)


def test_backlog_row_untouched_or_relabelled_still_serves(db):
    cur = db.cursor()
    cur.execute("ALTER TABLE regulatory_provisions DISABLE TRIGGER trg_rp_state_law_publish_gate")
    rid = _ins(cur)                                        # a 2026-10-17 backlog row: served, unproven
    cur.execute("ALTER TABLE regulatory_provisions ENABLE TRIGGER trg_rp_state_law_publish_gate")
    db.commit()
    cur.execute("UPDATE regulatory_provisions SET ref_number = 'Section 2' WHERE id = %s", (rid,))
    cur.execute("UPDATE regulatory_provisions SET citation_status = 'partial' WHERE id = %s", (rid,))
    db.commit()                                            # no new text: allowed


def test_refreshing_the_timestamp_alone_keeps_no_proof(db):
    cur = db.cursor()
    rid = _ins(cur, status="proven")
    db.commit()
    cur.execute("UPDATE regulatory_provisions SET provision_text = 'B', citation_checked_at = now() WHERE id = %s", (rid,))
    assert _commit_fails(db)
    cur = db.cursor()   # a revert that supplies both a new check time and a new evidence path keeps its proof
    cur.execute("UPDATE regulatory_provisions SET provision_text = 'C', citation_checked_at = now(), "
                "citation_source_path = 'https://legislation.nsw.gov.au/x#sec.1', citation_status = 'proven' WHERE id = %s",
                (rid,))
    db.commit()


def test_proven_council_row_turned_state_law_loses_its_proof(db):
    cur = db.cursor()
    rid = _ins(cur, council="hornsby", status="proven")
    db.commit()
    cur.execute("UPDATE regulatory_provisions SET source_council = NULL WHERE id = %s", (rid,))
    assert _commit_fails(db)


def test_blanking_the_evidence_with_new_text_keeps_no_proof(db):
    cur = db.cursor()
    rid = _ins(cur, status="proven")
    cur.execute("UPDATE regulatory_provisions SET citation_checked_at = now(), citation_source_path = 'p' WHERE id = %s",
                (rid,))
    db.commit()
    cur.execute("UPDATE regulatory_provisions SET provision_text = 'D', citation_checked_at = NULL, "
                "citation_source_path = NULL WHERE id = %s", (rid,))
    assert _commit_fails(db)
