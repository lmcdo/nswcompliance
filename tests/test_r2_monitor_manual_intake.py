"""Manual intake: a PDF a person downloaded is fed through the monitor's own write path.

Known case (2026-11-02): sutherlandshire.nsw.gov.au answers 403 to the hub page and every chapter PDF, Zyte
included. Chapters 2 and 4 held the right content_hash with r2_current_path NULL, so every run skipped them as
"unchanged" against a file that was never stored, and their 28 number rules could never be proven.
"""
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

sys.modules.setdefault("boto3", MagicMock())
sys.modules.setdefault("botocore", MagicMock())
if "botocore.exceptions" not in sys.modules:
    _m = types.ModuleType("botocore.exceptions")

    class ClientError(Exception):
        pass

    _m.ClientError = ClientError
    sys.modules["botocore.exceptions"] = _m

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
for _var in ("R2_ACCOUNT_ID", "R2_BUCKET_NAME", "R2_ACCESS_KEY_ID",
             "R2_SECRET_ACCESS_KEY", "DATABASE_URL"):
    os.environ.setdefault(_var, f"test-{_var.lower()}")

import r2_monitor  # noqa: E402

PDF = b"%PDF-1.7\n" + b"x" * 5000
COLS = ["id", "council", "dcp_name", "chapter_key", "chapter_label", "council_url", "council_page_url",
        "hub_expected_count", "hub_last_pdf_count", "r2_current_path", "r2_version_label",
        "url_last_downloaded", "content_hash", "url_content_length", "url_etag", "check_failures",
        "is_spatial", "is_inert"]


def _row(cid, key, content_hash=None, r2_path=None):
    return (cid, "sutherland_shire", "Sutherland Shire DCP 2015", key, key, f"https://council/{key}.pdf",
            "https://council/hub", None, None, r2_path, None, None, content_hash, None, None, 0, False, False)


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


@pytest.fixture
def run(monkeypatch, tmp_path):
    def blocked(*a, **k):
        raise AssertionError("manual intake must not call the council")

    monkeypatch.setattr(r2_monitor, "head_request", blocked)
    monkeypatch.setattr(r2_monitor, "download_pdf", blocked)
    monkeypatch.setattr(r2_monitor, "send_telegram", lambda m: None)
    monkeypatch.setattr(r2_monitor.time, "sleep", lambda s: None)
    monkeypatch.setitem(r2_monitor.HUB_SCRAPERS, "sutherland_shire", blocked)

    def go(rows, body=PDF, key="ch2"):
        f = tmp_path / "ch.pdf"
        f.write_bytes(body)
        conn, s3 = _Conn(rows), MagicMock()
        res = r2_monitor.run_monitor("sutherland_shire", s3, conn, manual_key=key, manual_file=str(f))
        return res, conn.cur.sql, s3
    return go


def _registry_writes(sql):
    return [(s, p) for s, p in sql if s.startswith("UPDATE dcp_chapter_registry SET r2_current_path")]


def test_known_case_hash_set_but_no_file_is_stored_and_queued(run):
    h = r2_monitor.sha256(PDF)
    res, sql, s3 = run([_row(1, "ch2", content_hash=h)])
    assert s3.put_object.call_count == 1
    (s, p), = _registry_writes(sql)
    assert p[0].startswith("source-pdfs/dcps/sutherland_shire/") and p[3] == h
    assert p[5] is None and p[6] is None          # no ETag / Last-Modified invented
    assert p[10] is True                          # needs_extraction
    assert len(res["changed"]) == 1


def test_only_the_named_chapter_is_touched(run):
    res, sql, s3 = run([_row(1, "ch2"), _row(2, "ch4", content_hash=r2_monitor.sha256(PDF))], key="ch4")
    (s, p), = _registry_writes(sql)
    assert p[-1] == 2


def test_same_file_already_stored_is_unchanged(run):
    h = r2_monitor.sha256(PDF)
    res, sql, s3 = run([_row(1, "ch2", content_hash=h, r2_path="source-pdfs/dcps/sutherland_shire/v1.0-baseline/ch2.pdf")])
    assert s3.put_object.call_count == 0 and not _registry_writes(sql)
    assert res["unchanged"] == 1


def test_a_non_pdf_is_refused_and_writes_nothing(run):
    res, sql, s3 = run([_row(1, "ch2")], body=b"<!DOCTYPE html>" + b"x" * 5000)
    assert s3.put_object.call_count == 0 and not _registry_writes(sql)
    assert res["changed"] == []


def test_a_normal_run_still_downloads_a_hash_with_no_file():
    src = open(r2_monitor.__file__, encoding="utf-8").read()
    assert "force=force or not r2_path" in src
    assert "if new_hash == stored_hash and r2_path:" in src


def test_file_without_key_is_refused_inside_run_monitor(tmp_path):
    f = tmp_path / "ch.pdf"
    f.write_bytes(PDF)
    with pytest.raises(ValueError):
        r2_monitor.run_monitor("sutherland_shire", MagicMock(), _Conn([_row(1, "ch2")]), manual_file=str(f))


def test_a_different_valid_pdf_is_refused_not_stored_as_an_amendment(run):
    # Sol finding: Chapter 4's PDF fed under the Chapter 2 key. Registry holds Chapter 2's hash.
    res, sql, s3 = run([_row(1, "ch2", content_hash="a" * 64)])
    assert s3.put_object.call_count == 0 and not _registry_writes(sql)
    assert res["failed"] == 1 and res["changed"] == []


def test_a_named_new_hash_is_accepted_as_an_amendment(monkeypatch, tmp_path):
    for name in ("head_request", "download_pdf"):
        monkeypatch.setattr(r2_monitor, name, lambda *a, **k: (_ for _ in ()).throw(AssertionError(name)))
    monkeypatch.setattr(r2_monitor, "send_telegram", lambda m: None)
    monkeypatch.setattr(r2_monitor.time, "sleep", lambda s: None)
    f = tmp_path / "ch.pdf"
    f.write_bytes(PDF)
    conn, s3 = _Conn([_row(1, "ch2", content_hash="a" * 64, r2_path="source-pdfs/dcps/sutherland_shire/v1.0-baseline/ch2.pdf")]), MagicMock()
    s3.get_object.side_effect = Exception("no old copy")  # re-export gate fails open, as in production
    res = r2_monitor.run_monitor("sutherland_shire", s3, conn, manual_key="ch2", manual_file=str(f),
                                 manual_expect_sha256=r2_monitor.sha256(PDF))
    assert s3.put_object.call_count == 1 and len(res["changed"]) == 1


def test_a_mistyped_key_fails_loudly(run):
    with pytest.raises(RuntimeError, match="matched 0"):
        run([_row(1, "ch2")], key="ch2x")


def test_a_chapter_with_no_recorded_hash_needs_the_hash_named(run):
    # Sol 2nd pass: content_hash NULL must not mean "any file will do".
    res, sql, s3 = run([_row(1, "ch2", content_hash=None)])
    assert s3.put_object.call_count == 0 and not _registry_writes(sql)
    assert res["failed"] == 1
