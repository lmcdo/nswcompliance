"""A new council document that fails to register must fail the run, loudly.

Before 2026-10-26 `_auto_register_chapter` raising was printed and rolled back, nothing
was recorded, the run did not fail, and `hub_last_pdf_count` was still moved to the new
count -- so the next run's delta no longer showed the new document. A new DCP chapter
could go untracked behind a clean-looking run (code-quality review, monitor finding 1).
"""
from __future__ import annotations

import os
import sys
import types
from unittest.mock import MagicMock

sys.modules.setdefault("boto3", MagicMock())
sys.modules.setdefault("botocore", MagicMock())
if "botocore.exceptions" not in sys.modules:
    _m = types.ModuleType("botocore.exceptions")

    class ClientError(Exception):
        pass

    _m.ClientError = ClientError
    sys.modules["botocore.exceptions"] = _m

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
for _k in ("R2_ACCOUNT_ID", "R2_BUCKET_NAME", "R2_ACCESS_KEY_ID",
           "R2_SECRET_ACCESS_KEY", "DATABASE_URL"):
    os.environ.setdefault(_k, "test-placeholder-not-a-credential")

import r2_monitor  # noqa: E402

COLS = ["id", "council", "dcp_name", "chapter_key", "chapter_label", "council_url",
        "council_page_url", "hub_expected_count", "hub_last_pdf_count", "r2_current_path",
        "r2_version_label", "url_last_downloaded", "content_hash", "url_content_length",
        "url_etag", "check_failures", "is_spatial", "is_inert"]
ROW = (1, "testcouncil", "Test DCP", "part-a", "Part A", None, "https://c.example/dcp",
       None, 1, None, None, None, None, None, None, 0, False, False)


class FakeCursor:
    def __init__(self, log):
        self.log, self.description, self.rowcount = log, [(c,) for c in COLS], 0

    def execute(self, sql, params=None):
        self.log.append(" ".join(sql.split()))

    def fetchall(self):
        return [ROW]

    def fetchone(self):
        return None

    def close(self):
        pass


class FakeConn:
    def __init__(self):
        self.sql: list[str] = []

    def cursor(self):
        return FakeCursor(self.sql)

    def commit(self):
        pass

    def rollback(self):
        pass


def _run(monkeypatch, register):
    new = {"url": "https://c.example/new.pdf", "label": "Part Z (new)", "chapter_key": None}
    monkeypatch.setitem(r2_monitor.HUB_SCRAPERS, "testcouncil", lambda *a, **k: [new, new])
    monkeypatch.setattr(r2_monitor, "diff_urls",
                        lambda *a, **k: r2_monitor.DiffResult(added=[new]))
    monkeypatch.setattr(r2_monitor, "_auto_register_chapter", register)
    monkeypatch.setattr(r2_monitor, "_send_discovery_digest", lambda *a, **k: None)
    monkeypatch.setattr(r2_monitor, "send_telegram", lambda *a, **k: None)
    conn = FakeConn()
    results = r2_monitor.run_monitor("testcouncil", MagicMock(), conn)
    return results, conn.sql


def _boom(*a, **k):
    raise RuntimeError("insert failed")


def test_a_failed_registration_fails_the_run(monkeypatch):
    results, _ = _run(monkeypatch, _boom)
    # Counted in its own bucket; main() adds it to real_failed, which exits 1.
    assert len(results.get("register_failed", [])) == 1
    assert "Part Z (new)" in results["register_failed"][0]
    src = open(r2_monitor.__file__, encoding="utf-8").read()
    assert 'real_failed = results["failed"] + len(results.get("register_failed", []))' in src


def test_a_failed_registration_keeps_the_old_document_count(monkeypatch):
    _, sql = _run(monkeypatch, _boom)
    assert not any("SET hub_last_pdf_count" in s for s in sql), (
        "the count moved, so the next run will not see the new document again")


def test_a_good_registration_still_moves_the_count(monkeypatch):
    results, sql = _run(monkeypatch, lambda *a, **k: {"status": "registered"})
    assert results.get("register_failed", []) == []
    assert any("SET hub_last_pdf_count" in s for s in sql)
