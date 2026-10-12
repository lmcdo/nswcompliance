"""Database side of scripts/council_quote.py: read the served rules, store the verdicts (migration 111).

prior-art-checked: split out of council_quote.py (500-line limit); the only writer of the quote columns.
"""
from __future__ import annotations

import collections
import csv
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fetch(council: str | None, ids: list[int] | None, chapter: str | None = None) -> list[dict]:
    import psycopg2
    import dcp_page_repair as dpr
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        conn.cursor().execute("SET statement_timeout = 30000")
        rows = dpr.fetch(conn, council)
    finally:
        conn.close()
    return [r for r in rows if (not ids or r["id"] in ids)
            and (chapter is None or r["source_chapter_key"] == chapter)]


def write(res: list[dict]) -> int:
    """Store each verdict (migration 111). One transaction per chapter, by primary key, and only
    where the rule's text is still the text that was judged -- a row edited meanwhile keeps NULL,
    which the nightly check reports. Returns rows written."""
    import psycopg2
    from psycopg2.extras import execute_values
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    backup = ROOT / "data" / "db_rollback_backups" / f"regulatory_provisions_pre_council_quote_{stamp}.csv"
    backup.parent.mkdir(parents=True, exist_ok=True)
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = 30000")
        cur.execute("SELECT id, council_quote, quote_page, quote_source_path, quote_status, quote_reason, "
                    "quote_checked_at FROM regulatory_provisions WHERE id = ANY(%s)", ([r["id"] for r in res],))
        with backup.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([d[0] for d in cur.description])
            w.writerows(cur.fetchall())
        conn.commit()
        print(f"backup: {backup}")
        by = collections.defaultdict(list)
        for r in res:
            if r["reason"] == "pdf_unreadable":   # a failed download is no verdict: keep what is stored
                continue
            usable = r["status"] in ("exact", "recovered")
            by[r["source_path"]].append((
                r["id"], r["text_md5"], (r["quote"].replace("\x00", "") if usable else None),
                r.get("quote_page") if usable else None, r["source_path"] if usable else None,
                r["status"], r["reason"], r["source_path"]))
        stored: set[int] = set()       # ids THIS run updated, from RETURNING -- not inferred from stamps
        for _path, vals in by.items():
            # Only while the PDF judged is still the chapter's active one: a new PDF in between
            # voids quotes (migration 111), and this must not write the old PDF's back.
            # prior-art-checked: tightens this module's own writer; no other writer of these columns.
            got = execute_values(cur, """
                UPDATE regulatory_provisions rp
                   SET council_quote = v.q, quote_page = v.pg, quote_source_path = v.src,
                       quote_status = v.st, quote_reason = v.why, quote_checked_at = now()
                  FROM (VALUES %s) AS v(id, md5, q, pg, src, st, why, judged)
                  JOIN dcp_chapter_registry reg ON reg.r2_current_path = v.judged AND reg.is_active
                 WHERE rp.id = v.id AND md5(rp.provision_text) = v.md5 AND rp.is_current
                   AND reg.council = rp.source_council AND reg.chapter_key = rp.source_chapter_key
                RETURNING rp.id""",
                vals, template="(%s::int, %s, %s::text, %s::int, %s::text, %s, %s, %s)", page_size=500,
                fetch=True)
            conn.commit()
            stored.update(row[0] for row in got)
        return len(stored)
    finally:
        conn.close()
