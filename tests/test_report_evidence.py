"""The paid report's evidence trail (migration 078).

Pins: a conveyancing report is never delivered without its audit record; the record names each
setback shown, its clause verdict and the PDF it was checked against, and the delivered file's
fingerprint; a malformed report id is refused before any work; the writers store the judged PDF.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT))

import importlib.util  # noqa: E402

import dcp_citation_status as RP  # noqa: E402
import report_evidence as E  # noqa: E402

# conftest_mocks replaces `audit_trail` in sys.modules with a stub; load the real module and
# install it for each test, so the code under test imports the real one.
_spec = importlib.util.spec_from_file_location("_real_audit_trail", ROOT / "services" / "audit_trail.py")
audit_trail = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit_trail)


@pytest.fixture(autouse=True)
def _real_audit_trail(monkeypatch):
    monkeypatch.setitem(sys.modules, "audit_trail", audit_trail)

SETBACKS = {
    "dcp_name": "Woollahra DCP 2015",
    "setbacks": [{"control_id": 7, "semantic_type": "front_setback", "value_min": 6.0, "unit": "m",
                  "clause": "C2.1, p. 12", "citation_status": "proven",
                  "citation_source_path": "dcp/woollahra/c2-v3.pdf", "pdf_page": 12,
                  "source_chapter_key": "c2"}],
    "sd_setbacks": [{"control_id": 9, "semantic_type": "side_setback", "value_min": 0.9, "unit": "m",
                     "clause": "", "citation_status": "not_proven",
                     "citation_source_path": "dcp/woollahra/c2-v3.pdf", "pdf_page": 14}],
}


def test_the_record_names_every_setback_shown_with_its_verdict_and_source():
    inter, summary = E.conveyancing_evidence(SETBACKS, [{"number": "6.9", "source": "LEP"}], "ab" * 32, "k")
    cites = inter["setback_citations"]
    assert [c["control_id"] for c in cites] == [7, 9]
    assert cites[0] == {**cites[0], "clause_shown": "C2.1, p. 12", "citation_status": "proven",
                        "checked_against": "dcp/woollahra/c2-v3.pdf"}
    assert cites[1]["clause_shown"] is None and cites[1]["citation_status"] == "not_proven"
    assert summary == {"recorded_at": "generated_before_upload", "pdf_sha256": "ab" * 32, "r2_key": "k",
                       "setbacks_shown": 2, "clauses_shown": 1}
    assert inter["lep_clauses"] == [{"number": "6.9", "source": "LEP"}]


def test_no_setbacks_is_an_empty_record_not_a_crash():
    inter, summary = E.conveyancing_evidence(None, None, "x", "k")
    assert inter["setback_citations"] == [] and summary["setbacks_shown"] == 0


def test_file_fingerprint(tmp_path):
    f = tmp_path / "r.pdf"
    f.write_bytes(b"pdf")
    import hashlib
    assert E.file_sha256(str(f)) == hashlib.sha256(b"pdf").hexdigest()


@pytest.mark.parametrize("value, ok", [
    ("793604ba-6713-4a29-b80b-4e17476ba8a3", True), ("not-a-uuid", False), ("", False), (None, False)])
def test_report_id_must_be_a_uuid(value, ok):
    assert E.is_report_id(value) is ok


def _failing_conn():
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.execute.side_effect = RuntimeError("db down")
    return conn


def test_a_required_audit_write_that_fails_raises(monkeypatch):
    monkeypatch.setattr(audit_trail, "_get_conn", _failing_conn)
    with pytest.raises(audit_trail.AuditTrailError):
        audit_trail.log_audit_trail("793604ba-6713-4a29-b80b-4e17476ba8a3", "conveyancing", {}, [], {},
                                    "v1", required=True)


def test_an_optional_audit_write_that_fails_does_not_raise(monkeypatch):
    monkeypatch.setattr(audit_trail, "_get_conn", _failing_conn)
    audit_trail.log_audit_trail("793604ba-6713-4a29-b80b-4e17476ba8a3", "flood", {}, [], {}, "v1")


def test_the_paid_report_is_refused_when_its_audit_record_fails(monkeypatch, tmp_path):
    from fastapi import HTTPException
    import conveyancing as C
    pdf = tmp_path / "r.pdf"
    pdf.write_bytes(b"pdf")

    def fail(**kw):
        assert kw["required"] is True and kw["pipeline_name"] == "conveyancing"
        raise audit_trail.AuditTrailError("no")
    monkeypatch.setattr(audit_trail, "log_audit_trail", fail)
    monkeypatch.setattr(audit_trail, "get_current_disclaimer_version", lambda p: "v1")
    req = MagicMock(report_id="793604ba-6713-4a29-b80b-4e17476ba8a3", prop_id=None)
    with pytest.raises(HTTPException) as ei:
        C._write_conveyancing_audit(req, "1 X St", -33.8, 151.2, str(pdf), SETBACKS, [])
    assert ei.value.status_code == 503


def test_the_paid_report_writes_its_evidence(monkeypatch, tmp_path):
    import conveyancing as C
    pdf = tmp_path / "r.pdf"
    pdf.write_bytes(b"pdf")
    got = {}
    monkeypatch.setattr(audit_trail, "log_audit_trail", lambda **kw: got.update(kw))
    monkeypatch.setattr(audit_trail, "get_current_disclaimer_version", lambda p: "v1")
    req = MagicMock(report_id="793604ba-6713-4a29-b80b-4e17476ba8a3", prop_id="42")
    C._write_conveyancing_audit(req, "1 X St", -33.8, 151.2, str(pdf), SETBACKS, [])
    assert got["required"] is True
    assert got["output_summary"]["r2_key"] == "conveyancing/793604ba-6713-4a29-b80b-4e17476ba8a3.pdf"
    assert len(got["intermediate_calculations"]["setback_citations"]) == 2


def test_rp_writer_rewrites_a_verdict_whose_judged_pdf_changed():
    # same verdict, new PDF -> written, so the record names the PDF actually checked
    assert RP.plan_writes({1: "proven"}, {1: "new.pdf"}, {1: ("proven", "old.pdf")}) == [(1, "proven", "new.pdf")]
    assert RP.plan_writes({1: "proven"}, {1: "same.pdf"}, {1: ("proven", "same.pdf")}) == []
    with pytest.raises(ValueError):
        RP.plan_writes({1: "maybe"}, {}, {})


def test_migration_078_chains_and_locks_the_audit_trail():
    sql = (ROOT / "migrations" / "078_evidence_trail.sql").read_text(encoding="utf-8")
    for must in ("BEFORE INSERT ON report_audit_trail", "BEFORE UPDATE OR DELETE ON report_audit_trail",
                 "BEFORE TRUNCATE ON report_audit_trail", "pg_advisory_xact_lock",
                 "AFTER UPDATE OF r2_current_path, is_active ON dcp_chapter_registry"):
        assert must in sql, must
    assert "\x08" not in sql


def test_the_pdf_endpoint_checks_the_id_first_and_audits_before_upload():
    import inspect
    import conveyancing as C
    src = inspect.getsource(C.generate_conveyancing_pdf)
    idx = {k: src.index(k) for k in ("is_report_id(req.report_id)", "_load_pipeline_cache(",
                                     "_write_conveyancing_audit(", "_upload_to_r2(")}
    assert idx["is_report_id(req.report_id)"] < idx["_load_pipeline_cache("]
    assert idx["_write_conveyancing_audit("] < idx["_upload_to_r2("]


def test_the_newest_row_cannot_be_removed_unnoticed():
    import verify_audit_chain as V
    assert V.tail_problem((5, "h5", 5, "h5")) is None
    assert "removed from the end" in V.tail_problem((6, "h6", 5, "h5"))
    assert V.tail_problem(None) == "no tail checkpoint"


def test_a_failed_upload_is_recorded_as_undelivered(monkeypatch):
    import conveyancing as C
    got = {}
    monkeypatch.setattr(audit_trail, "log_audit_trail", lambda **kw: got.update(kw))
    monkeypatch.setattr(audit_trail, "get_current_disclaimer_version", lambda p: "v1")
    C._record_delivery_failure(MagicMock(report_id="793604ba-6713-4a29-b80b-4e17476ba8a3", prop_id=None))
    assert got["output_summary"]["recorded_at"] == "delivery_failed"
    assert not got.get("required")


def test_writers_only_write_onto_the_pdf_still_in_force():
    for p in ("dcp_citation_status.py", "dcp_setback_citation_status.py"):
        src = (ROOT / "scripts" / p).read_text(encoding="utf-8")
        assert "reg.r2_current_path IS NOT DISTINCT FROM v.src" in src, p
