"""A committed chapter records which version of its PDF the live rules came from.

prior-art-checked: extends the commit-worker tests (fakes modelled on
tests/test_dcp_commit_refuses_section_loss.py); no existing test covers the registry
update this pins.

DQ-70 counts served rules whose chapter PDF fingerprint (content_hash) differs from the
one recorded when the rules were written (provisions_extracted_from_hash). Only the
direct extraction path recorded it. The review-queue commit cleared needs_extraction and
recorded nothing, so every chapter committed after its PDF changed still read as stale --
110 served rules on 2026-09-14 -- and a chapter that really was stale looked the same.

The fake registry applies the worker's UPDATE the way Postgres would for the two forms it
can take, so a reverted UPDATE, a plain `= %s` in place of the COALESCE, and a commit that
runs past the currency guard each fail a test here.
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

COUNCIL, CHAPTER = "city_of_sydney", "section-3-general-provisions"
_COALESCE = "provisions_extracted_from_hash=COALESCE(%s,provisions_extracted_from_hash)"


class _Cur:
    def __init__(self, reg):
        self.reg = reg
        self.rowcount = 0

    def execute(self, sql, params=None):
        compact = "".join(sql.split())
        if not compact.startswith("UPDATEdcp_chapter_registry"):
            return
        assert tuple(params[-2:]) == (COUNCIL, CHAPTER), "the update is not scoped to the chapter"
        self.reg["updates"] += 1
        if "needs_extraction=FALSE" in compact:
            self.reg["needs_extraction"] = False
        if _COALESCE in compact:
            if params[0] is not None:
                self.reg["provisions_extracted_from_hash"] = params[0]
        elif "provisions_extracted_from_hash=%s" in compact:
            self.reg["provisions_extracted_from_hash"] = params[0]

    def fetchone(self):
        return (3,)

    def fetchall(self):
        return []

    def close(self):
        pass


class _Conn:
    def __init__(self, reg):
        self.reg = reg
        self.autocommit = False
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return _Cur(self.reg)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        pass


def _wire(monkeypatch, approved_hash, registry_hash="pdf-v2", commit_raises=False):
    reg = {"content_hash": registry_hash, "provisions_extracted_from_hash": "pdf-v1",
           "needs_extraction": True, "updates": 0}
    conn = _Conn(reg)
    monkeypatch.setattr(dca.psycopg2, "connect", lambda *a, **k: conn)
    monkeypatch.setattr(dca, "find_committable_chapters", lambda cur: [
        {"council": COUNCIL, "chapter_key": CHAPTER,
         "approved_hash": approved_hash, "hash_variants": 1}])
    monkeypatch.setattr(dca, "fetch_registry_chapter",
                        lambda cur, council, chapter_key: {"content_hash": reg["content_hash"]})

    def _commit(cur, council, chapter_key, allow_unqueued=False):
        if commit_raises:
            raise RuntimeError("2 live rule(s) are not in the approved queue")
        return (3, 3)

    monkeypatch.setattr(dca, "commit_reviewed_from_queue", _commit)
    monkeypatch.setattr(dca, "section_snapshot", lambda cur, council, chapter_key: None)
    monkeypatch.setattr(dca, "enforce_section_loss", lambda *a, **k: None)

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
    return conn, reg


def test_a_commit_records_the_pdf_version_the_rules_were_reviewed_against(monkeypatch):
    conn, reg = _wire(monkeypatch, approved_hash="pdf-v2")
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    dca.main()

    assert conn.commits == 1
    assert reg["needs_extraction"] is False
    assert reg["provisions_extracted_from_hash"] == "pdf-v2", (
        "the chapter was committed but still says its rules came from the old PDF, so "
        "DQ-70 cannot tell it from a chapter that really is stale")


def test_a_legacy_approval_with_no_hash_keeps_the_recorded_fingerprint(monkeypatch):
    """Rows queued before source hashes were stored cannot say which PDF they reflect.
    Writing the registry's current hash here would claim a match nobody checked."""
    conn, reg = _wire(monkeypatch, approved_hash=None)
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    dca.main()

    assert conn.commits == 1 and reg["needs_extraction"] is False
    assert reg["provisions_extracted_from_hash"] == "pdf-v1"


def test_a_stale_approval_records_nothing(monkeypatch):
    """Confusable negative: the PDF changed again after review. The currency guard skips
    the chapter, so the registry must be left exactly as it was."""
    conn, reg = _wire(monkeypatch, approved_hash="pdf-v2", registry_hash="pdf-v3")
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    dca.main()

    assert conn.commits == 0 and reg["updates"] == 0
    assert reg["provisions_extracted_from_hash"] == "pdf-v1" and reg["needs_extraction"] is True


def test_a_refused_commit_records_nothing(monkeypatch):
    conn, reg = _wire(monkeypatch, approved_hash="pdf-v2", commit_raises=True)
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py", "--commit"])

    assert dca.main() == 1
    assert conn.commits == 0 and conn.rollbacks == 1 and reg["updates"] == 0
    assert reg["provisions_extracted_from_hash"] == "pdf-v1"


def test_a_dry_run_records_nothing(monkeypatch):
    conn, reg = _wire(monkeypatch, approved_hash="pdf-v2")
    monkeypatch.setattr(sys, "argv", ["dcp_commit_approved.py"])

    dca.main()

    assert conn.commits == 0 and reg["updates"] == 0
