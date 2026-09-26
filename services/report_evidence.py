"""What a paid report showed, and what each citation was checked against.

prior-art-checked: services/audit_trail.py writes the row (hash-chained and append-only since
migration 078); it records data-source responses, not the citations a customer was shown. The
conveyancing report wrote no audit row at all (0 of 887 rows, 2026-09-26). This module only
builds the evidence payload; audit_trail stays the one writer.

The question it answers, for any delivered report: which rules and clause labels did the customer
see, was each label proven on the council's page, and which version of that page was it checked
against? A clause is shown only when proven (migration 077); the source path is the chapter PDF the
verdict was judged on (migration 078).
"""
from __future__ import annotations

import hashlib
import uuid


def is_report_id(value: object) -> bool:
    """A report id is a UUID: report_audit_trail.report_id is a uuid column, so any other value
    would make the required audit write fail after the report was already built."""
    try:
        uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return False
    return True


def file_sha256(path: str) -> str:
    """The delivered file's fingerprint: the audit row names exactly which bytes were delivered."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def setback_citations(dcp_setbacks: dict | None) -> list[dict]:
    """One entry per setback control printed in the report, with its citation evidence."""
    if not dcp_setbacks:
        return []
    out = []
    for group in ("setbacks", "sd_setbacks"):
        for e in dcp_setbacks.get(group) or []:
            out.append({
                "control_id": e.get("control_id"),
                "control": e.get("semantic_type") or e.get("type"),
                "value_min": e.get("value_min"),
                "value_max": e.get("value_max"),
                "unit": e.get("unit"),
                "clause_shown": e.get("clause") or None,
                "citation_status": e.get("citation_status"),
                "checked_against": e.get("citation_source_path"),
                "pdf_page": e.get("pdf_page"),
                "source_chapter_key": e.get("source_chapter_key"),
            })
    return out


def conveyancing_evidence(dcp_setbacks: dict | None, lep_clauses: list | None,
                          pdf_sha256: str, r2_key: str) -> tuple[dict, dict]:
    """(intermediate_calculations, output_summary) for the conveyancing report's audit row."""
    citations = setback_citations(dcp_setbacks)
    intermediate = {
        "dcp_name": (dcp_setbacks or {}).get("dcp_name"),
        "dcp_as_at": (dcp_setbacks or {}).get("as_at"),
        "setback_citations": citations,
        "lep_clauses": [{"number": c.get("number"), "source": c.get("source")}
                        for c in (lep_clauses or []) if isinstance(c, dict)],
    }
    summary = {
        # Written when the file is built, BEFORE upload: this row proves what was generated. A
        # failed upload adds a second 'delivery_failed' row; a delivered report has none.
        "recorded_at": "generated_before_upload",
        "pdf_sha256": pdf_sha256,
        "r2_key": r2_key,
        "setbacks_shown": len(citations),
        "clauses_shown": sum(1 for c in citations if c.get("clause_shown")),
    }
    return intermediate, summary
