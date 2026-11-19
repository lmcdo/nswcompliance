"""Read-only council data for the site evidence statement: the council's own controls and the council files held.

Both functions return {"status": "ok" | "none" | "unreadable", ...}: an unreadable database is never shown as "no rows".
Connection is read-only with a short timeout, like services/lmr_area_lga.py.

prior-art-checked: no existing reader joins dcp_setback_controls with dcp_source_versions for one lot; lmr_area_lga._connect is
private to that module and returns None without DATABASE_URL, so the same read-only options are repeated here (10 lines).
"""
from __future__ import annotations

import logging
import os
from typing import Any, Callable, Optional

from services.council_key import to_council_key

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT_S = 3
STATEMENT_TIMEOUT_MS = 5000
DEV_TYPE = "dwelling_house"

_CONTROLS_SQL = (
    "SELECT control_type, dev_type, value_min, value_max, unit, condition, applicability, source_text, section_ref, pdf_page, "
    "source_chapter_key, dcp_version, effective_date FROM dcp_setback_controls "
    "WHERE lga = %s AND dev_type = %s AND is_current AND COALESCE(needs_review, false) = false "
    "ORDER BY source_chapter_key, section_ref, control_type"
)
_FILES_SQL = (
    "SELECT v.chapter_key, v.version_label, v.captured_at, v.superseded_at, r.url_last_modified, r.council_url "
    "FROM dcp_source_versions_dated v LEFT JOIN dcp_chapter_registry r ON r.council = v.council AND r.chapter_key = v.chapter_key AND r.is_active "
    "WHERE v.council = %s AND v.event = 'stored' ORDER BY v.chapter_key, v.captured_at DESC"
)


def _connect() -> Any:
    import psycopg2

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return None
    return psycopg2.connect(dsn, connect_timeout=CONNECT_TIMEOUT_S,
                            options=f"-c statement_timeout={STATEMENT_TIMEOUT_MS} -c default_transaction_read_only=on")


def _iso(v: Any) -> Optional[str]:
    return v.isoformat() if hasattr(v, "isoformat") else (str(v) if v is not None else None)


def _num(v: Any) -> Optional[float]:
    return float(v) if v is not None else None


def _run(sql: str, args: tuple, connect: Optional[Callable[[], Any]]) -> Optional[list]:
    """Rows, or None when the database could not be read."""
    conn = None
    try:
        conn = (connect or _connect)()
        if conn is None:
            return None
        cur = conn.cursor()
        cur.execute(sql, args)
        return cur.fetchall()
    except Exception as exc:  # noqa: BLE001 -- an unreadable database is reported as unreadable, never as empty
        logger.warning("evidence council read failed: %s", exc)
        return None
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass


def council_controls(lga: Optional[str], *, connect: Optional[Callable[[], Any]] = None) -> dict:
    """The council's own current controls for a dwelling house, with the council's words, clause and page. Rows under review are left out."""
    key = to_council_key(lga)
    if key is None:
        return {"status": "unreadable", "council": None, "reason": "the council for this lot is not known", "controls": []}
    rows = _run(_CONTROLS_SQL, (key, DEV_TYPE), connect)
    if rows is None:
        return {"status": "unreadable", "council": key, "reason": "the controls database did not answer", "controls": []}
    controls = [{"control_type": r[0], "dev_type": r[1], "value_min": _num(r[2]), "value_max": _num(r[3]), "unit": r[4], "condition": r[5],
                 "applicability": r[6], "council_words": r[7], "clause": r[8], "page": r[9], "chapter": r[10], "plan_version": r[11],
                 "effective_date": _iso(r[12])} for r in rows]
    return {"status": "ok" if controls else "none", "council": key, "dev_type": DEV_TYPE, "controls": controls}


def council_files(lga: Optional[str], *, connect: Optional[Callable[[], Any]] = None) -> dict:
    """Council files we hold, by chapter, newest first. The council's own file date is recorded for the current file only."""
    key = to_council_key(lga)
    if key is None:
        return {"status": "unreadable", "council": None, "reason": "the council for this lot is not known", "files": []}
    rows = _run(_FILES_SQL, (key,), connect)
    if rows is None:
        return {"status": "unreadable", "council": key, "reason": "the file ledger did not answer", "files": []}
    files = []
    for chapter, version, captured, superseded, last_modified, url in rows:
        current = superseded is None
        files.append({"chapter": chapter, "version": version, "held_from": _iso(captured), "replaced_on": _iso(superseded), "current": current,
                      "council_file_date": last_modified if current else None,
                      "council_file_date_note": None if current else "not kept for earlier versions",
                      "council_url": url if current else None})
    return {"status": "ok" if files else "none", "council": key, "files": files}
