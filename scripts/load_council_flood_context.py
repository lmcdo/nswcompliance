"""Load council_flood_context (migration 118) from verified research.

Only CONFIRMED facts are written: each fact's page was fetched and contained the
fact's key words (verify step, 2026-10-29). Unconfirmed facts are dropped, never
stored as if true. A NULL field means "not found or not confirmed".

Usage:
  python scripts/load_council_flood_context.py --file data/council_flood_context/verified_2026-10-29.json --dry-run
  python scripts/load_council_flood_context.py --file ... --apply

prior-art-checked: no table or script holds per-council flood information;
frontend-nextjs/lib/lga-data/flood-lgas.ts is unsourced marketing copy (24 of 32
feature counts wrong, 2026-10-29) and is not reused.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _confirmed(x):
    return x if isinstance(x, dict) and x.get("confirmed") else None


def rows_from(records: list[dict]) -> list[tuple]:
    rows = []
    for r in records:
        council = (r.get("council") or "").strip().upper()
        if not council:
            continue
        v, c, f = _confirmed(r.get("viewer")), _confirmed(r.get("certificate")), _confirmed(r.get("fpl"))
        # fpl_quote must be the council's own words: a search-summary paraphrase
        # or an elided ("...") quote is not stored, even if its numbers matched.
        if f and any(t in (f.get("quote") or "").lower() for t in ("search summary", "...", "…", "paraphrase")):
            f = None
        data = [{"label": d.get("label"), "url": d.get("url"), "licence": d.get("licence")}
                for d in (r.get("data") or []) if d.get("confirmed")]
        rows.append((
            council,
            v and v.get("label"), v and v.get("url"),
            c and c.get("label"), c and c.get("url"), c and c.get("fee"),
            f and f.get("quote"), f and f.get("url"),
            None,  # layers_note: never confirmed by opening a viewer; left empty
            json.dumps(data),
            r.get("checked") or "2026-10-29",
        ))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    rows = rows_from(json.loads(Path(a.file).read_text(encoding="utf-8")))
    filled = sum(1 for r in rows if any(r[1:9]) or r[9] != "[]")
    print(f"councils {len(rows)}; with at least one confirmed fact {filled}")
    if a.dry_run:
        for r in rows[:5]:
            print("  ", r[0], "| viewer" if r[2] else "", "| certificate" if r[4] else "", "| fpl" if r[7] else "",
                  f"| data {len(json.loads(r[9]))}")
        return 0
    import psycopg2
    from dotenv import load_dotenv
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from dq_db import main_checkout  # a worktree has no .env of its own (DQ-54)
    load_dotenv(main_checkout() / ".env")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        _write(conn, rows)
    finally:
        conn.close()
    return 0


def _write(conn, rows: list[tuple]) -> None:
    with conn, conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO council_flood_context
                 (lga_name, viewer_label, viewer_url, certificate_label, certificate_url, certificate_fee,
                  fpl_quote, fpl_url, layers_note, data_sources, checked_on)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
               ON CONFLICT (lga_name) DO UPDATE SET
                 viewer_label=EXCLUDED.viewer_label, viewer_url=EXCLUDED.viewer_url,
                 certificate_label=EXCLUDED.certificate_label, certificate_url=EXCLUDED.certificate_url,
                 certificate_fee=EXCLUDED.certificate_fee, fpl_quote=EXCLUDED.fpl_quote, fpl_url=EXCLUDED.fpl_url,
                 layers_note=EXCLUDED.layers_note, data_sources=EXCLUDED.data_sources,
                 checked_on=EXCLUDED.checked_on, updated_at=now()""",
            rows,
        )
        # The file is the whole truth: a council dropped from a corrected file
        # loses its row, so a withdrawn fact never stays live (cross-review).
        cur.execute("DELETE FROM council_flood_context WHERE NOT (lga_name = ANY(%s))",
                    ([r[0] for r in rows],))
        print("rows removed (not in file):", cur.rowcount)
        cur.execute("SELECT count(*) FROM council_flood_context")
        print("rows now in council_flood_context:", cur.fetchone()[0])


if __name__ == "__main__":
    sys.exit(main())
