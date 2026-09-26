#!/usr/bin/env python3
# prior-art-checked: the verdict is citation_proof.prove_label (the same rule as
# dcp_citation_status.py for regulatory_provisions), and page lines come from the DQ-111
# probe's chapter_lines cache. This only applies them to dcp_setback_controls, which 076
# could not cover: 954 of its current rows have no provision_id.
"""Store, per served setback control, whether its clause label is printed on the council's page.

WHY
---
The conveyancing PDF, the Brief, the DCP controls card and the parking API all print
dcp_setback_controls.section_ref. Those labels were written by hand, by regex and by AI, and
never checked. The serving layer (conveyancing_db.fetch_dcp_setbacks) shows a clause only when
this verdict is proven, imprecise or external; otherwise it shows the page.

WHAT IT DOES
------------
For every served row (is_current, not needs_review):
  external  -- a state instrument (lga nsw_statewide, or a chapter key "_external_*"):
               outside this check, shown as before (as LEP/SEPP rows are in 076).
  no_source -- the chapter's PDF cannot be read.
  otherwise -- citation_proof.prove_label(section_ref, source_text, page lines, pdf_page).
Only rows whose verdict CHANGED are written. Dry run by default; --apply writes.

USAGE
-----
  python scripts/dcp_setback_citation_status.py                 # dry run, all councils
  python scripts/dcp_setback_citation_status.py --council bayside --apply
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

STATUSES = ("proven", "imprecise", "partial", "not_proven", "unjudged", "text_not_found",
            "no_source", "external")
BATCH = 500

SERVED_SQL = """
SELECT s.id, s.lga, s.source_chapter_key, s.section_ref, reg.r2_current_path,
       s.source_text, s.pdf_page
FROM dcp_setback_controls s
LEFT JOIN dcp_chapter_registry reg
  ON reg.council = s.lga AND reg.chapter_key = s.source_chapter_key AND reg.is_active
WHERE s.is_current AND (s.needs_review IS NULL OR s.needs_review = FALSE)
"""


def is_external(lga: str | None, chapter_key: str | None) -> bool:
    """A state instrument's control: outside the council-page check."""
    return lga == "nsw_statewide" or (chapter_key or "").startswith("_external_")


def label_of(section_ref: str | None) -> str:
    """The printed label: "plan-file.pdf#2.9.3(a)" and "general-residential-dcp-2026#C4.1.1"
    carry a file or plan name before '#'; only the part after it is printed."""
    return (section_ref or "").split("#")[-1]


def plan_updates(verdicts: dict[int, str], current: dict[int, str | None]) -> list[tuple[int, str]]:
    """(id, status) for every row whose verdict differs from what is stored. Pure."""
    bad = {v for v in verdicts.values() if v not in STATUSES}
    if bad:
        raise ValueError(f"unknown citation status {sorted(bad)}")
    return sorted((i, v) for i, v in verdicts.items() if current.get(i) != v)


def judge_rows(rows, readings_for) -> dict[int, str]:
    """Verdicts for served rows. readings_for(r2_path) -> readings, or raises when unreadable."""
    import citation_proof as cp
    by_pdf = defaultdict(list)
    verdicts: dict[int, str] = {}
    for rid, lga, key, ref, r2_path, text, page in rows:
        if is_external(lga, key):
            verdicts[rid] = "external"
        elif not r2_path:
            verdicts[rid] = "no_source"
        else:
            by_pdf[r2_path].append((rid, ref, text, page))
    for r2_path, rs in by_pdf.items():
        try:
            readings = readings_for(r2_path)
        except Exception as e:  # noqa: BLE001 -- a missing PDF is a verdict, not a crash
            print(f"  no source for {r2_path}: {str(e)[:80]}", flush=True)
            verdicts.update({rid: "no_source" for rid, *_ in rs})
            continue
        for rid, ref, text, page in rs:
            verdicts[rid] = cp.prove_label(label_of(ref), text, readings, page)["status"]
    return verdicts


def write_verdicts(conn, todo: list[tuple[int, str]], rows) -> int:
    """Write each verdict onto the row it was judged on, and only that row.

    A row edited while this ran (the 077 trigger cleared its verdict) no longer matches the
    lga, chapter, label, text and page that were judged, so it keeps NULL and stays hidden
    until the next run. Returns the number of rows written."""
    cur = conn.cursor()
    judged = {r[0]: r for r in rows}
    written = 0
    for i in range(0, len(todo), BATCH):
        chunk = [(rid, st, judged[rid]) for rid, st in todo[i:i + BATCH]]
        cur.execute(
            "UPDATE dcp_setback_controls s SET citation_status = v.s, citation_source_path = v.src, "
            "citation_checked_at = now() "
            "FROM unnest(%s::bigint[], %s::text[], %s::text[], %s::text[], %s::text[], %s::text[], "
            "%s::int[], %s::text[]) AS v(id, s, lga, chk, ref, txt, pg, src) "
            "WHERE s.id = v.id AND s.is_current AND s.lga IS NOT DISTINCT FROM v.lga "
            "AND s.source_chapter_key IS NOT DISTINCT FROM v.chk "
            "AND s.section_ref IS NOT DISTINCT FROM v.ref "
            "AND s.source_text IS NOT DISTINCT FROM v.txt AND s.pdf_page IS NOT DISTINCT FROM v.pg "
            # ... and onto the PDF still in force (a state instrument has none to match).
            "AND (v.s = 'external' OR EXISTS (SELECT 1 FROM dcp_chapter_registry reg "
            "WHERE reg.is_active AND reg.council = v.lga AND reg.chapter_key = v.chk "
            "AND reg.r2_current_path IS NOT DISTINCT FROM v.src))",
            ([c[0] for c in chunk], [c[1] for c in chunk], [c[2][1] for c in chunk],
             [c[2][2] for c in chunk], [c[2][3] for c in chunk], [c[2][5] for c in chunk],
             [c[2][6] for c in chunk], [c[2][4] for c in chunk]))
        written += cur.rowcount
        conn.commit()
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().splitlines()[0])
    ap.add_argument("--council", help="Only this council (its lga slug).")
    ap.add_argument("--apply", action="store_true", help="Write. Without it nothing changes.")
    ap.add_argument("--cache-dir", default=str(Path(tempfile.gettempdir()) / "dq111_lines"))
    args = ap.parse_args()

    import boto3
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    import dq_probe_section_code_not_in_source as probe

    s3 = boto3.client(
        "s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
    cache = Path(args.cache_dir)
    cache.mkdir(parents=True, exist_ok=True)

    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30000'")
        sql, params = SERVED_SQL, []
        if args.council:
            sql += " AND s.lga = %s"
            params.append(args.council)
        cur.execute(sql, params)
        rows = cur.fetchall()
        verdicts = judge_rows(
            rows, lambda p: probe.chapter_lines(s3, os.environ["R2_BUCKET_NAME"], p, cache))
        print(f"scope: {args.council or 'all councils'}  setback controls: {len(verdicts)}")
        for k, n in Counter(verdicts.values()).most_common():
            print(f"  {n:6}  {k}")
        # A catalogue lookup, not a row read: no is_current filter applies here.
        cur.execute("SELECT count(*) FROM information_schema.columns WHERE table_name = "
                    "'dcp_setback_controls' AND column_name IN ('citation_status', 'citation_source_path')")
        if cur.fetchone()[0] < 2:
            print("verdict columns missing -- run migrations/077 and 078 first. Nothing written.")
            return 0 if not args.apply else 1
        cur.execute("SELECT id, citation_status, to_jsonb(dcp_setback_controls) ->> 'citation_source_path' "
                    "FROM dcp_setback_controls WHERE id = ANY(%s) AND is_current", (list(verdicts),))
        stored = {i: (s, p) for i, s, p in cur.fetchall()}
        sources = {r[0]: r[4] for r in rows}
        plan_updates(verdicts, {})                   # refuses an unknown verdict
        todo = [(i, v) for i, v in sorted(verdicts.items()) if stored.get(i) != (v, sources.get(i))]
        print(f"  {len(todo):6}  to write (verdict or judged source changed)")
        if not args.apply:
            print("DRY RUN -- nothing written. Re-run with --apply.")
            return 0
        written = write_verdicts(conn, todo, rows)
        print(f"WROTE {written} verdicts ({len(todo) - written} rows changed while judging; left unchecked).")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
