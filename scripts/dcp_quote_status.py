#!/usr/bin/env python3
# prior-art-checked: scripts/dcp_citation_status.py stores whether a CLAUSE NUMBER is printed
# on the page (citation_status); scripts/council_quote.py copies text out of a chapter for
# re-extraction. Neither answers "is this stored quote the council's exact words on the cited
# page". The matching here is the one that measured the 235 proven rows on 2026-10-29
# (~/.claude/plans/ce-quote-check-evidence-2026-10-29/qc.py), kept identical on purpose.
"""Store, per DCP number rule, whether its quote is printed word for word on the cited page.

WHY
---
Number rules were typed as summaries and served as if they were the council's words (876
served, 235 proven, 2026-10-29). Migration 120 holds every current row whose quote_status is
not 'verbatim', so this script is what lets a rule be served at all.

VERDICTS (dcp_setback_controls.quote_status, migration 119)
  verbatim    on pdf_page, or across the break between pdf_page and a neighbour
  wrong_page  elsewhere in the same chapter PDF (fix pdf_page, then re-run)
  not_found   nowhere in the chapter PDF
  no_source   no chapter PDF, no page, no quote, or a PDF with no text layer

Matching ignores case, spacing, punctuation and curly quotes/dashes; it keeps letters,
digits, '.' and '%'. It is exact otherwise: no fuzzy match is ever 'verbatim'.

USAGE
  python scripts/dcp_quote_status.py                    # dry run, every current row
  python scripts/dcp_quote_status.py --council woollahra
  python scripts/dcp_quote_status.py --apply            # back up, then write changed verdicts
"""
from __future__ import annotations

import argparse
import datetime
import io
import json
import logging
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERDICTS = ("verbatim", "wrong_page", "not_found", "no_source")
_DROP = "‘’“”–—−­"


def norm(text: str) -> str:
    """Lower-case and keep only letters, digits, '.' and '%'."""
    t = text.lower()
    for ch in _DROP:
        t = t.replace(ch, "")
    return re.sub(r"[^a-z0-9.%]", "", t)


def classify(quote: str | None, pages: list[str] | None, pdf_page: int | None) -> str:
    """Verdict for one quote against a chapter's page texts (raw, 1-based by position).

    pages is None when the PDF could not be read.
    """
    if not quote or not quote.strip() or not pdf_page or pages is None:
        return "no_source"
    np = [norm(p) for p in pages]
    if not any(np):
        return "no_source"
    q = norm(quote)
    if not q:
        return "no_source"
    i = pdf_page - 1
    if 0 <= i < len(np):
        here = [np[i]]
        if i > 0:
            here.append(np[i - 1] + np[i])
        if i + 1 < len(np):
            here.append(np[i] + np[i + 1])
        if any(q in t for t in here):
            return "verbatim"
    if any(q in t for t in np) or any(q in a + b for a, b in zip(np, np[1:])):
        return "wrong_page"
    return "not_found"


def changed(rows: list[tuple[int, str | None]], verdicts: dict[int, str]) -> list[tuple[int, str]]:
    """(id, new verdict) for rows whose stored verdict differs. Refuses an unknown verdict."""
    out = []
    for rid, old in rows:
        new = verdicts[rid]
        if new not in VERDICTS:
            raise ValueError(f"unknown verdict {new!r} for row {rid}")
        if new != old:
            out.append((rid, new))
    return out


ROWS_SQL = """
SELECT s.id, s.lga, s.source_text, s.pdf_page, s.quote_status, s.source_chapter_key,
       s.citation_source_path,
       COALESCE((SELECT r.r2_current_path FROM dcp_chapter_registry r
                 WHERE r.chapter_key = s.source_chapter_key AND r.council = s.lga
                   AND r.is_active LIMIT 1),
                s.citation_source_path)
FROM dcp_setback_controls s
WHERE s.is_current AND (%(council)s::text IS NULL OR s.lga = %(council)s)
ORDER BY s.id
"""


def _r2():
    import boto3

    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    return s3, os.environ.get("R2_BUCKET_NAME") or os.environ.get("R2_BUCKET")


def _page_texts(s3, bucket: str, path: str) -> list[str] | None:
    import pypdf

    try:
        reader = pypdf.PdfReader(io.BytesIO(s3.get_object(Bucket=bucket, Key=path)["Body"].read()))
    except Exception:
        return None
    out = []
    for p in reader.pages:
        try:
            out.append(p.extract_text() or "")
        except Exception:
            out.append("")
    return out


def main() -> int:
    import psycopg2
    from dotenv import load_dotenv

    ap = argparse.ArgumentParser()
    ap.add_argument("--council")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    logging.disable(logging.CRITICAL)  # pypdf warns on every odd font
    load_dotenv(ROOT / ".env")
    conn = psycopg2.connect(os.environ["DATABASE_URL"], options="-c statement_timeout=30000")
    try:
        return _run(conn, a)
    finally:
        conn.close()


def _run(conn, a) -> int:
    cur = conn.cursor()
    cur.execute(ROWS_SQL, {"council": a.council})
    rows = cur.fetchall()
    s3, bucket = _r2()
    cache: dict[str, list[str] | None] = {}
    verdicts: dict[int, str] = {}
    for n, (rid, _lga, quote, page, _old, _ck, _csp, path) in enumerate(rows, 1):
        if path and path not in cache:
            cache[path] = _page_texts(s3, bucket, path)
        verdicts[rid] = classify(quote, cache.get(path) if path else None, page)
        if n % 50 == 0 or n == len(rows):
            print(f"DONE {n}/{len(rows)}", flush=True)
    todo = changed([(r[0], r[4]) for r in rows], verdicts)
    print("verdicts", dict(Counter(verdicts.values())))
    print("to write", len(todo), dict(Counter(v for _, v in todo)))
    if not a.apply or not todo:
        print("dry run" if not a.apply else "nothing to write")
        return 0
    ids = [rid for rid, _ in todo]
    cur.execute("SELECT id, quote_status, quote_checked_at, needs_review, review_reason "
                "FROM dcp_setback_controls WHERE id = ANY(%s)", (ids,))
    stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S")
    back = ROOT / "data" / "db_rollback_backups" / f"dcp_quote_status_pre_{stamp}.json"
    back.write_text(json.dumps([dict(id=r[0], quote_status=r[1], quote_checked_at=str(r[2]) if r[2] else None,
                                     needs_review=r[3], review_reason=r[4]) for r in cur.fetchall()]))
    print("backup", back)
    # Write a verdict only onto the exact row that was checked: if the quote, page, council,
    # chapter or source changed since it was read, nothing is written at all.
    seen = {r[0]: r for r in rows}
    n_written = 0
    for rid, v in todo:
        _, lga, quote, page, old, ck, csp, _path = seen[rid]
        cur.execute(
            "UPDATE dcp_setback_controls SET quote_status = %s, quote_checked_at = now() "
            "WHERE id = %s AND is_current AND lga = %s AND source_text IS NOT DISTINCT FROM %s "
            "AND pdf_page IS NOT DISTINCT FROM %s AND quote_status IS NOT DISTINCT FROM %s "
            "AND source_chapter_key IS NOT DISTINCT FROM %s "
            "AND citation_source_path IS NOT DISTINCT FROM %s",
            (v, rid, lga, quote, page, old, ck, csp))
        n_written += cur.rowcount
    if n_written != len(todo):
        conn.rollback()
        print(f"ABORTED: {len(todo) - n_written} row(s) changed while checking; nothing written. Re-run.")
        return 1
    conn.commit()
    cur.execute("SELECT count(*) FROM dcp_setback_controls WHERE is_current AND needs_review IS NOT TRUE")
    print(f"WROTE {len(todo)} verdicts; served now {cur.fetchone()[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
