"""A new council file is held aside (migration 125) until the reviewed rules are published.

Why: re-pointing the live registry row at intake sent live page links to the new file at the old page
numbers and fired the proof-clearing triggers (Waverley Amdt 6, 2026-11-10: DQ-145 131 -> 3,077).
"""
import os
import re
import sys
import types
from unittest.mock import MagicMock

import pytest

sys.modules.setdefault("boto3", MagicMock())
sys.modules.setdefault("botocore", MagicMock())
if "botocore.exceptions" not in sys.modules:
    _m = types.ModuleType("botocore.exceptions")
    _m.ClientError = type("ClientError", (Exception,), {})
    sys.modules["botocore.exceptions"] = _m
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
for _var in ("R2_ACCOUNT_ID", "R2_BUCKET_NAME", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "DATABASE_URL"):
    os.environ.setdefault(_var, f"test-{_var.lower()}")

import r2_monitor  # noqa: E402
from scripts import dcp_staged  # noqa: E402

OLD = b"%PDF-1.7\n" + b"o" * 5000
NEW = b"%PDF-1.7\n" + b"n" * 5000
LIVE_PATH = "source-pdfs/dcps/penrith/v1.1-2026-03-16/c2.pdf"
COLS = ["id", "council", "dcp_name", "chapter_key", "chapter_label", "council_url", "council_page_url",
        "hub_expected_count", "hub_last_pdf_count", "r2_current_path", "r2_version_label",
        "url_last_downloaded", "content_hash", "url_content_length", "url_etag", "check_failures",
        "staged_content_hash", "staged_version_label", "is_spatial", "is_inert"]


def _row(live_hash, r2_path=LIVE_PATH, staged_hash=None, staged_version=None):
    return (1, "penrith", "Penrith DCP", "c2", "c2", "https://council/c2.pdf", "https://council/hub",
            None, None, r2_path, "v1.1-2026-03-16" if r2_path else None, None, live_hash, None, None, 0,
            staged_hash, staged_version, False, False)


class _Cur:
    def __init__(self, rows):
        self.rows, self.sql, self.description, self.rowcount = rows, [], [(c,) for c in COLS], 0

    def execute(self, sql, params=None):
        self.sql.append((" ".join(sql.split()), params))

    def fetchall(self):
        return self.rows

    def close(self):
        pass


class _Conn:
    def __init__(self, rows):
        self.cur = _Cur(rows)

    def cursor(self):
        return self.cur

    def commit(self):
        pass


def _intake(monkeypatch, tmp_path, row, body):
    def blocked(*a, **k):
        raise AssertionError("manual intake must not call the council")
    monkeypatch.setattr(r2_monitor, "head_request", blocked)
    monkeypatch.setattr(r2_monitor, "download_pdf", blocked)
    monkeypatch.setattr(r2_monitor, "send_telegram", lambda m: None)
    monkeypatch.setattr(r2_monitor.time, "sleep", lambda s: None)
    monkeypatch.setitem(r2_monitor.HUB_SCRAPERS, "penrith", blocked)
    f = tmp_path / "c.pdf"
    f.write_bytes(body)
    conn, s3 = _Conn([row]), MagicMock()
    s3.get_object.side_effect = Exception("no old copy")   # re-export gate fails open, as in production
    res = r2_monitor.run_monitor("penrith", s3, conn, manual_key="c2", manual_file=str(f),
                                 manual_expect_sha256=r2_monitor.sha256(body))
    return res, conn.cur.sql, s3


def _sets_live_path(sql):
    return [s for s, _ in sql if re.search(r"SET r2_current_path\s*=", s)]


def _stages(sql):
    return [(s, p) for s, p in sql if "SET staged_r2_path" in s]


def test_an_amendment_is_staged_and_the_live_row_does_not_move(monkeypatch, tmp_path):
    res, sql, s3 = _intake(monkeypatch, tmp_path, _row(r2_monitor.sha256(OLD)), NEW)
    assert s3.put_object.call_count == 1                      # the file is kept
    assert not _sets_live_path(sql)                           # r2_current_path / content_hash untouched
    (s, p), = _stages(sql)
    assert p[3] == r2_monitor.sha256(NEW) and p[0].startswith("source-pdfs/dcps/penrith/")
    assert p[0] != LIVE_PATH
    assert any("needs_extraction=TRUE" in s for s, _ in sql)  # the extractor is told to read it
    assert len(res["changed"]) == 1


def test_the_same_new_file_again_is_not_a_second_change(monkeypatch, tmp_path):
    h = r2_monitor.sha256(NEW)
    res, sql, s3 = _intake(monkeypatch, tmp_path,
                           _row(r2_monitor.sha256(OLD), staged_hash=h, staged_version="v1.2-x"), NEW)
    assert s3.put_object.call_count == 0 and not _stages(sql) and not _sets_live_path(sql)
    assert res["changed"] == [] and res["unchanged"] == 1


def test_a_newer_file_replaces_the_staged_one_with_a_later_version_label(monkeypatch, tmp_path):
    NEWER = b"%PDF-1.7\n" + b"z" * 5000
    res, sql, s3 = _intake(monkeypatch, tmp_path,
                           _row(r2_monitor.sha256(OLD), staged_hash=r2_monitor.sha256(NEW),
                                staged_version="v1.2-2026-10-26"), NEWER)
    (s, p), = _stages(sql)
    assert p[3] == r2_monitor.sha256(NEWER) and "v1.2-2026-10-26" not in p[1]
    assert not _sets_live_path(sql)


def test_a_first_load_has_nothing_to_protect_and_goes_live(monkeypatch, tmp_path):
    res, sql, s3 = _intake(monkeypatch, tmp_path, _row(r2_monitor.sha256(NEW), r2_path=None), NEW)
    assert _sets_live_path(sql) and not _stages(sql)


def test_publish_staged_moves_live_columns_and_clears_the_staging():
    cur = _Cur([])
    cur.rowcount = 1
    assert dcp_staged.publish_staged(cur, "penrith", "c2") is True
    s, p = cur.sql[0]
    assert "r2_current_path = staged_r2_path" in s and "content_hash = staged_content_hash" in s
    assert "r2_public_pdf_url = staged_public_pdf_url" in s and "staged_r2_path = NULL" in s
    assert "AND staged_r2_path IS NOT NULL" in s and p == ("penrith", "c2")


def test_publish_staged_with_nothing_staged_reports_false():
    assert dcp_staged.publish_staged(_Cur([]), "penrith", "c2") is False


def test_the_commit_worker_publishes_the_file_in_the_same_transaction_as_the_rules():
    src = open(os.path.join(os.path.dirname(__file__), "..", "scripts", "dcp_commit_approved.py"),
               encoding="utf-8").read()
    i_pub = src.index("publish_staged(cur, council, chapter_key)")
    i_flag = src.index('"UPDATE dcp_chapter_registry SET needs_extraction=FALSE')
    i_commit = src.index("conn.commit()", i_flag)
    assert i_pub < i_flag < i_commit
    assert "COALESCE(staged_content_hash, content_hash) AS content_hash" in src


@pytest.mark.parametrize("script", ["dcp_extract_changed.py", "dcp_approve_proven.py", "dcp_watchdog.py"])
def test_every_reader_of_the_update_chain_reads_the_effective_hash(script):
    src = open(os.path.join(os.path.dirname(__file__), "..", "scripts", script), encoding="utf-8").read()
    assert "staged_content_hash" in src
    assert not re.search(r"source_content_hash = (reg|r|dcp_chapter_registry)\.content_hash", src)
