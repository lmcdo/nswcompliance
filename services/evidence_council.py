"""Read-only council data for the site evidence statement: the council's own controls and the council files held.

Both functions return {"status": "ok" | "none" | "unreadable", ...}: an unreadable database is never shown as "no rows".
Connection is read-only with a short timeout, like services/lmr_area_lga.py.

prior-art-checked: the council controls come from scripts/conveyancing_db.fetch_dcp_setbacks, the one guarded producer of this fact (precinct-specific,
zone and under-review rows are dropped there; a clause label is shown only when proven). No second query of dcp_setback_controls here (the producer
ratchet, scripts/page_integrity/lint_producers.py, forbids one). lmr_area_lga._connect is private to that module, so its read-only options are repeated.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Callable, Optional

from services.council_key import to_council_key

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT_S = 3
STATEMENT_TIMEOUT_MS = 8000   # fetch_dcp_setbacks runs several small reads
DEV_TYPE = "dwelling_house"

_VERSION_CHECK_SQL = (
    "SELECT v.control_id, s.version_label, v.verdict, v.quote_sha256, v.pdf_page FROM dcp_quote_version_check v "
    "JOIN dcp_setback_controls c ON c.id = v.control_id AND c.is_current AND c.lga = v.council AND c.source_chapter_key = v.chapter_key "
    "JOIN dcp_source_versions s ON s.r2_key = v.r2_key AND s.event = 'stored' AND s.council = v.council "
    "WHERE v.control_id = ANY(%s) ORDER BY v.control_id, s.version_label"
)
VERDICT_WORDS = {
    "verbatim": "Same words on the cited page",
    "wrong_page": "Same words, on a different page of this file",
    "not_found": "These words were not found in this file",
    "no_source": "This file could not be read",
}
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


def _default_fetch(conn: Any, key: str) -> Optional[dict]:
    try:
        from scripts.conveyancing_db import fetch_dcp_setbacks
    except ImportError:  # the image copies scripts/ files flat next to services/
        from conveyancing_db import fetch_dcp_setbacks
    return fetch_dcp_setbacks(conn, key, raise_on_error=True)


def _version_checks(ids: list[int], quotes: dict[int, Optional[str]], pages: dict[int, Optional[int]], connect: Optional[Callable[[], Any]],
                    rows_fn: Optional[Callable[[list[int]], Optional[list]]]) -> dict[int, dict]:
    """Stored quote-on-page verdicts per control and file version (migration 127). A check made on an older wording of the quote, or for a different page than the control cites now, is marked stale."""
    import hashlib

    if not ids:
        return {}
    rows = rows_fn(ids) if rows_fn else _run(_VERSION_CHECK_SQL, (ids,), connect)
    if rows is None:
        return {i: {"status": "unreadable", "versions": []} for i in ids}
    out: dict[int, dict] = {i: {"status": "none", "versions": []} for i in ids}
    for cid, label, verdict, sha, page in rows:
        if cid not in out:
            continue
        now_sha = hashlib.sha256((quotes.get(cid) or "").encode("utf-8")).hexdigest()
        out[cid]["status"] = "ok"
        out[cid]["versions"].append({"version": label, "verdict": verdict, "result_words": VERDICT_WORDS.get(verdict, verdict),
                                     "checked_page": page, "stale": sha != now_sha or page != pages.get(cid)})
    return out


def council_controls(lga: Optional[str], *, connect: Optional[Callable[[], Any]] = None,
                     fetch: Optional[Callable[[Any, str], Optional[dict]]] = None,
                     version_rows: Optional[Callable[[list[int]], Optional[list]]] = None) -> dict:
    """The council's own current dwelling house controls, with its words, clause and page, from the one guarded producer.

    status: ok (rows), none (the producer found no current rows), unreadable (council unknown or the database did not answer).
    A clause label proven against the council's page is "clause" with clause_shown true; an unproven stored label is returned as
    "clause" with clause_shown false, so the page can say so.
    """
    key = to_council_key(lga)
    if key is None:
        return {"status": "unreadable", "council": None, "reason": "the council for this lot is not known", "controls": []}
    conn = None
    try:
        conn = (connect or _connect)()
        if conn is None:
            return {"status": "unreadable", "council": key, "reason": "the controls database did not answer", "controls": []}
        data = (fetch or _default_fetch)(conn, key)
    except Exception as exc:  # noqa: BLE001 -- an unreadable database is reported as unreadable, never as empty
        logger.warning("evidence council controls failed: %s", exc)
        return {"status": "unreadable", "council": key, "reason": "the controls database did not answer", "controls": []}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
    rows = [e for e in ((data or {}).get("setbacks") or []) if e.get("dev_type") == DEV_TYPE]
    checks = _version_checks([e["control_id"] for e in rows if isinstance(e.get("control_id"), int)],  # noqa: bracket-access -- guarded by the isinstance test on the same line
                             {e["control_id"]: e.get("source_text") for e in rows if isinstance(e.get("control_id"), int)},  # noqa: bracket-access -- same guard
                             {e["control_id"]: e.get("pdf_page") for e in rows if isinstance(e.get("control_id"), int)},  # noqa: bracket-access -- same guard
                             connect, version_rows)
    controls = [{"control_id": e.get("control_id"), "version_checks": checks.get(e.get("control_id"), {"status": "none", "versions": []}),
                 "label": e.get("type"), "control_type": e.get("semantic_type"), "dev_type": e.get("dev_type"), "value_min": e.get("value_min"), "value_max": e.get("value_max"),
                 "unit": e.get("unit"), "requirement": e.get("requirement"), "condition": e.get("notes") or None,
                 "applicability": e.get("applicability"), "council_words": e.get("source_text"),
                 "clause": e.get("clause") or e.get("clause_unchecked") or None, "clause_shown": bool(e.get("clause_shown")),
                 "page": e.get("pdf_page"), "chapter": e.get("source_chapter_key"), "plan_version": e.get("dcp_version")} for e in rows]
    return {"status": "ok" if controls else "none", "council": key, "dev_type": DEV_TYPE, "as_at_line": (data or {}).get("as_at_line"), "controls": controls}


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
