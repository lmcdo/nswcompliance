#!/usr/bin/env python3
# prior-art-checked: the rows and cached page lines are dcp_citation_status's own
# (dq_probe_section_code_not_in_source.SERVED_SQL shape, chapter_lines cache format); the
# locating rule is scripts/rule_page_locator.py, shared with the AI reader. Nothing else
# records whether a served rule's pdf_page holds it (migration 079 header).
"""Make every served DCP rule's page link open the page the rule is on.

WHY
---
The AI reader stored the first page of its 12-page chunk for each rule it returned
(scripts/ai_extractor.py). Measured 2026-09-26 over all 237 served chapter PDFs: 45% of
17,489 served rules linked to a page that does not hold them. Councils also print their
own page numbers ("B5", "14-117"), which a reader of the printed plan looks for.

WHAT IT DOES
------------
Per served rule, against the chapter PDF the citation check reads (r2_current_path):
  on_page     the stored page holds the rule                 -> kept
  moved       the rule is on one other page, confirmed by an ordered 8-word run -> corrected
  unresolved  several candidate pages, or the two locators disagree  -> NOT moved, listed
  not_found / too_short / no_source                          -> not moved
and the page number printed on that page, when a neighbouring page confirms it.
Writes pdf_page, page_range (shifted by the same distance), printed_page_label, page_check,
page_checked_at, page_source_path (migration 079). Dry run by default.

USAGE
-----
  python scripts/dcp_page_repair.py                          # dry run, all councils
  python scripts/dcp_page_repair.py --council ashfield --apply
  python scripts/dcp_page_repair.py --check                  # exit 1 if a served rule is unchecked
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import rule_page_locator as rpl  # noqa: E402

BATCH = 500
MARGIN = 0.08
SERVED_SQL = """
SELECT rp.id, rp.source_council, rp.pdf_page, rp.page_range, rp.provision_text,
       reg.r2_current_path, reg.r2_public_pdf_url,
       rp.printed_page_label, rp.page_check, rp.page_source_path
FROM regulatory_provisions rp
JOIN dcp_chapter_registry reg
  ON reg.council = rp.source_council AND reg.chapter_key = rp.source_chapter_key AND reg.is_active
WHERE rp.is_current AND rp.v2_is_actionable AND rp.source_council IS NOT NULL
"""


# -- pure planning -------------------------------------------------------------------

def shift_range(page_range, stored: int | None, new: int) -> list[int]:
    """The rule's page span moved by the same distance as its first page. Pure."""
    if not page_range or stored is None:
        return [new]
    d = new - stored
    return [p + d for p in page_range]


def plan_row(row: dict, page: int | None, verdict: str, labels: dict[int, str]) -> dict:
    """The values this row should carry. Pure. Only a 'moved' verdict changes the page."""
    stored = row["pdf_page"]
    new_page = page if verdict == "moved" else stored
    new_range = (shift_range(row["page_range"], stored, page) if verdict == "moved"
                 else row["page_range"])
    shown = page if verdict in ("on_page", "moved") else None
    return {"id": row["id"], "pdf_page": new_page, "page_range": new_range,
            "printed_page_label": labels.get(shown) if shown else None,
            "page_check": verdict, "page_source_path": row["r2_current_path"]}


def changed(row: dict, plan: dict) -> bool:
    return any(row.get(k) != plan[k] for k in
               ("pdf_page", "page_range", "printed_page_label", "page_check", "page_source_path"))


# -- reading one PDF (worker process) ------------------------------------------------

def _s3():
    import boto3
    return boto3.client(
        "s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")


def _margins(pdf_path: str) -> dict[int, list[str]]:
    """Header/footer lines per page, as printed (case kept)."""
    import fitz
    out = {}
    with fitz.open(pdf_path) as doc:
        for pno, page in enumerate(doc, 1):
            h = page.rect.height or 1
            ls = []
            for b in page.get_text("dict")["blocks"]:
                for ln in b.get("lines") or []:
                    y0, y1 = ln["bbox"][1], ln["bbox"][3]
                    if y1 < MARGIN * h or y0 > (1 - MARGIN) * h:
                        t = " ".join(s["text"] for s in ln["spans"]).strip()
                        if t:
                            ls.append(t)
            out[pno] = ls
    return out


def judge_pdf(args) -> tuple[list[dict], dict]:
    """(plans, stats) for one chapter PDF's rows."""
    r2_path, rows, cache_dir = args
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    import citation_proof as cp
    import dq_probe_section_code_not_in_source as probe
    cache = Path(cache_dir)
    local = cache / "pdf" / (probe._cache_file(cache, r2_path).stem + ".pdf")
    try:
        if not local.exists():
            local.parent.mkdir(parents=True, exist_ok=True)
            _s3().download_file(os.environ["R2_BUCKET_NAME"], r2_path, str(local))
        lines_file = probe._cache_file(cache, r2_path)
        if not lines_file.exists():
            lines, width = cp.read_raw_lines(str(local))
            lines_file.write_text(json.dumps({"width": width, "lines": [
                [x.page, x.y, x.x, x.text] for x in lines]}), encoding="utf-8")
        data = json.loads(lines_file.read_text(encoding="utf-8"))
        readings = cp.both_orders([cp.Line(*x) for x in data["lines"]], data["width"])
        margins = _margins(str(local))
    except Exception as e:  # noqa: BLE001 -- an unreadable PDF is a verdict, not a crash
        print(f"  no source for {r2_path}: {str(e)[:100]}", flush=True)
        return [plan_row(r, None, "no_source", {}) for r in rows], {"pages": 0, "labelled": 0}
    docs = []
    # Both reading orders; running headers/footers already dropped. Contents pages are kept:
    # rows extracted FROM a contents page are printed only there.
    for ch in readings:
        by_page = defaultdict(list)
        for ln in ch.lines:
            by_page[ln.page].append(ln.text)
        docs.append(rpl.Doc({p: "\n".join(ts) for p, ts in by_page.items()}))
    labels = rpl.printed_labels(margins)
    k = rpl.batch_size([r["pdf_page"] for r in rows])
    plans = []
    for r in rows:
        stored = r["pdf_page"]
        window = range(stored, stored + k) if (k and stored) else None
        page, verdict = rpl.locate(r["provision_text"], docs, stored, window)
        plans.append(plan_row(r, page, verdict, labels))
    return plans, {"pages": len(margins), "labelled": len(labels), "batch": k,
                   "numbering": rpl.page_numbering(margins) if labels else []}


# -- database ------------------------------------------------------------------------

# prior-art-checked: reuse not viable because the guard's matches are pip/rich vendored code and the
# legislation monitor; dcp_citation_status checks its own 078 column inline the same way.
def has_079(conn) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM information_schema.columns WHERE table_name = "
                "'regulatory_provisions' AND column_name = 'page_check'")
    return cur.fetchone() is not None


def fetch(conn, council: str | None) -> list[dict]:
    cur = conn.cursor()
    sql, params = SERVED_SQL, []
    if not has_079(conn):       # a dry run may precede the migration: nothing checked yet
        sql = sql.replace("rp.printed_page_label, rp.page_check, rp.page_source_path",
                          "NULL AS printed_page_label, NULL AS page_check, NULL AS page_source_path")
    if council:
        sql += " AND rp.source_council = %s"
        params.append(council)
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def check(conn) -> int:
    """Exit 1 when any served council DCP rule has no page verdict for its current PDF."""
    cur = conn.cursor()
    cur.execute("""
        SELECT coalesce(rp.page_check, 'UNCHECKED'), count(*),
               count(*) FILTER (WHERE rp.page_check IS NULL
                                  OR rp.page_source_path IS DISTINCT FROM reg.r2_current_path)
        FROM regulatory_provisions rp
        JOIN dcp_chapter_registry reg
          ON reg.council = rp.source_council AND reg.chapter_key = rp.source_chapter_key AND reg.is_active
        WHERE rp.is_current AND rp.v2_is_actionable AND rp.source_council IS NOT NULL
        GROUP BY 1 ORDER BY 2 DESC""")
    rows = cur.fetchall()
    stale = sum(s for _k, _n, s in rows)
    for k, n, _s in rows:
        print(f"  {n:6}  {k}")
    print(f"  {stale:6}  never checked, or judged on a PDF that is no longer the chapter's current one")
    if stale:
        print("FAIL: served rules whose page link was never checked against their current PDF. "
              "Run `python scripts/dcp_page_repair.py --apply`.")
        return 1
    print("OK: every served rule's page link was checked against its current PDF.")
    return 0


def backup(rows: list[dict], ids: set[int]) -> Path:
    out = ROOT / "data" / "db_rollback_backups" / (
        f"regulatory_provisions_pre_page_repair_{datetime.now():%Y-%m-%d_%H%M}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "pdf_page", "page_range", "printed_page_label", "page_check", "page_source_path"])
        for r in rows:
            if r["id"] in ids:
                w.writerow([r["id"], r["pdf_page"], json.dumps(r["page_range"]), r["printed_page_label"],
                            r["page_check"], r["page_source_path"]])
    return out


def write(conn, todo: list[dict]) -> int:
    cur = conn.cursor()
    n = 0
    for i in range(0, len(todo), BATCH):
        c = todo[i:i + BATCH]
        cur.execute(
            "UPDATE regulatory_provisions p SET pdf_page = v.pg, "
            "page_range = CASE WHEN v.rng IS NULL THEN NULL "
            "  ELSE ARRAY(SELECT jsonb_array_elements_text(v.rng::jsonb)::int) END, "
            "printed_page_label = v.lbl, page_check = v.chk, page_source_path = v.src, "
            "page_checked_at = clock_timestamp() "
            "FROM unnest(%s::bigint[], %s::int[], %s::text[], %s::text[], %s::text[], %s::text[]) "
            "  AS v(id, pg, rng, lbl, chk, src) "
            "WHERE p.id = v.id AND p.is_current "
            # Only onto the PDF still in force (a chapter republished mid-run keeps no stale verdict).
            "AND EXISTS (SELECT 1 FROM dcp_chapter_registry reg WHERE reg.is_active "
            "AND reg.council = p.source_council AND reg.chapter_key = p.source_chapter_key "
            "AND reg.r2_current_path IS NOT DISTINCT FROM v.src)",
            ([t["id"] for t in c], [t["pdf_page"] for t in c],
             [None if t["page_range"] is None else json.dumps(list(t["page_range"])) for t in c],
             [t["printed_page_label"] for t in c], [t["page_check"] for t in c],
             [t["page_source_path"] for t in c]))
        n += cur.rowcount
        conn.commit()
    return n


def write_numbering(conn, stats: dict) -> int:
    """Each chapter PDF's page numbering onto its registry row (migration 079), for the PDF
    that is still the chapter's current one."""
    cur = conn.cursor()
    n = 0
    for path, st in stats.items():
        cur.execute("UPDATE dcp_chapter_registry SET page_numbering = %s::jsonb, page_numbering_path = %s "
                    "WHERE is_active AND r2_current_path = %s",
                    (json.dumps(st.get("numbering") or []), path, path))
        n += cur.rowcount
    conn.commit()
    return n


def report(rows: list[dict], plans: list[dict], stats: dict, sample_path: Path) -> list[dict]:
    by_id = {r["id"]: r for r in rows}
    per = defaultdict(Counter)
    for p in plans:
        per[by_id[p["id"]]["source_council"]][p["page_check"]] += 1
    total = Counter(p["page_check"] for p in plans)
    print(f"rules {len(plans)}  PDFs {len(stats)}")
    for k, n in total.most_common():
        print(f"  {n:6}  {k}")
    labelled = sum(1 for p in plans if p["printed_page_label"])
    print(f"  {labelled:6}  with a printed page number")
    numbered = [st for st in stats.values() if st.get("numbering")]
    print(f"  {len(numbered):6}  of {len(stats)} chapter PDFs have page numbering "
          f"({sum(st['labelled'] for st in numbered)} of {sum(st['pages'] for st in stats.values())} pages labelled)")
    print("\nper council: on_page / moved / unresolved / not_found / too_short / no_source / printed label")
    for co, c in sorted(per.items()):
        lab = sum(1 for p in plans if p["printed_page_label"] and by_id[p["id"]]["source_council"] == co)
        print(f"  {co:22} " + " ".join(f"{c[k]:5}" for k in rpl.VERDICTS) + f"   {lab:5}")
    todo = [p for p in plans if changed(by_id[p["id"]], p)]
    with sample_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "council", "verdict", "old_page", "new_page", "printed_label", "open_this_link"])
        for p in todo:
            r = by_id[p["id"]]
            url = r["r2_public_pdf_url"]
            w.writerow([p["id"], r["source_council"], p["page_check"], r["pdf_page"], p["pdf_page"],
                        p["printed_page_label"], f"{url}#page={p['pdf_page']}" if url and p["pdf_page"] else ""])
    print(f"\n  {len(todo):6}  rows to write   (every one listed with its link: {sample_path})")
    return todo


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().splitlines()[0])
    ap.add_argument("--council", help="Only this council.")
    ap.add_argument("--apply", action="store_true", help="Write. Without it nothing changes.")
    ap.add_argument("--check", action="store_true", help="Only report whether every link was checked.")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cache-dir", default=str(Path(tempfile.gettempdir()) / "dq111_lines"))
    ap.add_argument("--out", default=str(Path(tempfile.gettempdir()) / "dcp_page_repair_plan.csv"))
    args = ap.parse_args()

    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    try:
        conn.cursor().execute("SET statement_timeout = '30000'")
        if (args.check or args.apply) and not has_079(conn):
            print("page_check column missing -- run migrations/079_rule_page_check.sql first.")
            return 1
        if args.check:
            return check(conn)
        rows = fetch(conn, args.council)
        by_pdf = defaultdict(list)
        for r in rows:
            by_pdf[r["r2_current_path"]].append(r)
        Path(args.cache_dir).mkdir(parents=True, exist_ok=True)
        plans, stats = [], {}
        jobs = [(p, rs, args.cache_dir) for p, rs in by_pdf.items() if p]
        plans += [plan_row(r, None, "no_source", {}) for r in by_pdf.get(None, [])]
        with ProcessPoolExecutor(max_workers=max(1, args.workers)) as ex:
            for (path, _rs, _c), (got, st) in zip(jobs, ex.map(judge_pdf, jobs)):
                plans += got
                stats[path] = st
        todo = report(rows, plans, stats, Path(args.out))
        if not args.apply:
            print("DRY RUN -- nothing written. Open a few links in the file above, then re-run with --apply.")
            return 0
        saved = backup(rows, {t["id"] for t in todo})
        print(f"backup: {saved}")
        print(f"WROTE {write(conn, todo)} rows.")
        print(f"numbering recorded for {write_numbering(conn, stats)} chapter PDFs.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
