"""Classify a newly found council document from its OWN cover text, not the link text.

prior-art-checked: date patterns are reused from scripts/extract_dcp_stated_dates.py
(_STATEMENTS, MONTHS, _to_year); that script scans whole local PDFs for the plan's stored
commencement, this one decides what a newly linked document is. No existing code does that:
r2_monitor._auto_register_chapter classifies by link label only and dedupes by slug only.

Why: the monitor registers every unknown link on a council's DCP page as `auto_detected` and
waits for a person. Measured 2026-10-23 on the 28 waiting rows: 3 were files we already serve,
about 20 were guidelines / specifications / policies, and 2 were DCP chapters we do not cover.

A DCP takes effect when the council publishes its approval notice on its own website, or a
later day named in it (EP&A Regulation 2021 cl 14(4)). The cover usually states that date. It
is read from the cover only, never from an amendment-history table, whose dates belong to
earlier editions.

Verdicts (every unsure case is `red`, for a person):
  duplicate   same file (sha256) or same address as another row of the same council
  not_dcp     the cover names another kind of document and does not call itself a DCP
  dcp         the cover calls itself a Development Control Plan; `effective` is the one
              commencement date the cover states, else None and `needs_person`
  red         no readable text, or the cover names no kind of document

Deterministic text matching only. Nothing here interprets a rule.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import date
from urllib.parse import unquote

from extract_dcp_stated_dates import MONTHS, _STATEMENTS, _to_year

COVER_CHARS = 600
COVER_END = re.compile(r"table of contents|amendment history|\bcontents\b", re.I)
DCP_WORDS = re.compile(r"development\s+control\s+plan|\bDCP\b", re.I)
OTHER_KINDS = re.compile(
    r"technical\s+specification|guidelines?\b|\bpolicy\b|public\s+domain\s+plan|checklist|"
    r"infrastructure\s+strategy|design\s+guide|landscape\s+code|fact\s+sheet|"
    r"documentation\s+guide|participation\s+plan",
    re.I,
)
DRAFT = re.compile(r"\bdraft\b", re.I)


def cover_text(first_pages: list[str]) -> str:
    """The cover: start of page 1 up to the first contents / amendment-history heading."""
    page1 = " ".join((first_pages[0] if first_pages else "").split())
    head = page1[:COVER_CHARS]
    m = COVER_END.search(head)
    return head[: m.start()] if m else head


def effective_dates(cover: str) -> set[date]:
    """Every distinct commencement ('effective' kind) date stated on the cover."""
    found: set[date] = set()
    for pat, kind in _STATEMENTS:
        if kind != "effective":
            continue
        for g in pat.findall(cover):
            try:
                if g[1].lower() in MONTHS:
                    found.add(date(int(g[2]), MONTHS[g[1].lower()], int(g[0])))
                else:
                    found.add(date(_to_year(int(g[2])), int(g[1]), int(g[0])))
            except (ValueError, KeyError):
                continue
    return found


def _norm_url(url: str | None) -> str:
    return unquote(url or "").strip().lower().rstrip("/")


def classify(doc: dict, registry: list[dict], today: date) -> dict:
    """Verdict for one document.

    Args:
        doc: {id, url, sha256?, first_pages_text?: [str]}
        registry: the other rows of the same council: {id, council_url, content_hash}
        today: the day the verdict is for
    """
    for row in registry:
        if row["id"] == doc["id"]:
            continue
        if doc.get("sha256") and doc["sha256"] == row.get("content_hash"):
            return {"verdict": "duplicate", "of": row["id"], "why": "same file (sha256)"}
        if _norm_url(doc.get("url")) and _norm_url(doc.get("url")) == _norm_url(row.get("council_url")):
            return {"verdict": "duplicate", "of": row["id"], "why": "same address"}

    if doc.get("error"):
        return {"verdict": "red", "why": f"could not read the document ({doc['error']})"}
    cover = cover_text(doc.get("first_pages_text") or [])
    if not cover:
        return {"verdict": "red", "why": "no readable text on the first page"}
    if DCP_WORDS.search(cover):
        dates = effective_dates(cover)
        out = {"verdict": "dcp", "draft": bool(DRAFT.search(cover)), "quote": cover[:200]}
        if len(dates) == 1:
            (d,) = dates
            out.update(effective=d.isoformat(), in_force=d <= today, needs_person=False)
        else:
            out.update(effective=None, in_force=None, needs_person=True,
                       why="no commencement date on the cover" if not dates
                       else "more than one commencement date on the cover")
        return out
    kind = OTHER_KINDS.search(cover)
    if kind:
        return {"verdict": "not_dcp", "why": f"cover says '{kind.group(0)}'", "quote": cover[:200]}
    return {"verdict": "red", "why": "cover names no kind of document"}


# ── Running it on the registry ────────────────────────────────────────────────
# A verdict that settles the row rejects it; the rest stay `auto_detected` (so the alarm's
# new_doc_undecided_3d keeps them red for a person) and are tagged so they are not
# downloaded again every run. A failed download is not tagged: it is retried next run.
SETTLED = {"duplicate": "rejected", "not_dcp": "rejected"}
WAITING_TAG = {"dcp": "dcp_needs_person", "red": "unreadable"}
COVER_PAGES = 3


def read_document(data: bytes) -> dict:
    """sha256 and the first pages' text of a downloaded file."""
    import hashlib
    import io

    out: dict = {"sha256": hashlib.sha256(data).hexdigest()}
    if not data.startswith(b"%PDF-"):
        out["error"] = "not_pdf"
        return out
    try:
        import pypdf
        pdf = pypdf.PdfReader(io.BytesIO(data))
        out["first_pages_text"] = [pdf.pages[i].extract_text() or ""
                                   for i in range(min(COVER_PAGES, len(pdf.pages)))]
    except Exception as e:  # noqa: BLE001 - a damaged PDF is a red verdict, not a crash
        out["error"] = f"unreadable_pdf:{type(e).__name__}"
    return out


def pending(conn) -> list[dict]:
    cur = conn.cursor()
    cur.execute("""SELECT id, council, chapter_key, chapter_label, council_url
                   FROM dcp_chapter_registry
                   WHERE registration_status = 'auto_detected'
                     AND detected_category IS DISTINCT FROM 'dcp_needs_person'
                     AND detected_category IS DISTINCT FROM 'unreadable'
                   ORDER BY id""")
    rows = [dict(zip(("id", "council", "chapter_key", "label", "url"), r)) for r in cur.fetchall()]
    cur.close()
    return rows


def council_rows(conn, council: str) -> list[dict]:
    cur = conn.cursor()
    cur.execute("SELECT id, council_url, content_hash FROM dcp_chapter_registry WHERE council = %s",
                (council,))
    rows = [dict(zip(("id", "council_url", "content_hash"), r)) for r in cur.fetchall()]
    cur.close()
    return rows


def write_verdict(conn, row_id: int, verdict: dict) -> int:
    """Apply one verdict; guarded so it only ever touches a row still waiting. Returns rowcount."""
    v = verdict["verdict"]
    cur = conn.cursor()
    if v in SETTLED:
        cur.execute("""UPDATE dcp_chapter_registry
                       SET registration_status = %s, detected_category = %s, updated_at = NOW()
                       WHERE id = %s AND registration_status = 'auto_detected'""",
                    (SETTLED[v], v, row_id))
    else:
        cur.execute("""UPDATE dcp_chapter_registry SET detected_category = %s, updated_at = NOW()
                       WHERE id = %s AND registration_status = 'auto_detected'""",
                    (WAITING_TAG[v], row_id))
    n = cur.rowcount
    cur.close()
    return n


def classify_pending(conn, fetch, today: date, dry_run: bool) -> dict[str, int]:
    """Download, classify and (unless dry_run) record every waiting document.

    Args:
        fetch: url -> bytes (raises on a failed download)
    Returns counts per verdict, plus 'retry' for failed downloads.
    """
    counts: Counter[str] = Counter()
    for doc in pending(conn):
        try:
            doc.update(read_document(fetch(doc["url"])))
        except Exception as e:  # noqa: BLE001 - a failed download is retried next run
            counts["retry"] += 1
            print(f"    [classify] #{doc['id']} download failed ({type(e).__name__}) - retry next run")
            continue
        verdict = classify(doc, council_rows(conn, doc["council"]), today)
        counts[verdict["verdict"]] += 1
        detail = {k: verdict[k] for k in ("of", "effective", "why") if verdict.get(k)}
        print(f"    [classify] #{doc['id']} {doc['council']} '{doc['label']}' -> {verdict['verdict']} {detail}")
        if not dry_run:
            if write_verdict(conn, doc["id"], verdict) != 1:
                conn.rollback()
                raise RuntimeError(f"verdict for #{doc['id']} matched no waiting row - stopped")
            conn.commit()
    return dict(counts)


if __name__ == "__main__":  # pragma: no cover - manual run: python scripts/verifyops_classify.py [--apply]
    import os
    import sys

    import psycopg2
    import requests

    def _fetch(url: str) -> bytes:
        r = requests.get(url, timeout=90, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return r.content

    c = psycopg2.connect(os.environ["DATABASE_URL"], options="-c statement_timeout=30000")
    print(classify_pending(c, _fetch, date.today(), dry_run="--apply" not in sys.argv))
    c.close()
