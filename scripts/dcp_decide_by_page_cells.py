#!/usr/bin/env python3
# prior-art-checked: dcp_approve_proven.py approves only rows council_quote proves EXACT and leaves table rows,
# short rows and non-rules for a person; the only other way to record a verdict was the /internal/dcp-review
# page (a signed-in browser). Nothing scripted the remainder. This reuses CHAPTER_ROWS_SQL from
# dcp_approve_proven and dcp_page_repair._s3 for the PDF.
"""Decide the review-queue rows dcp_approve_proven.py leaves behind, by checking each against the chapter's PDF.

WHY. After the proven pass a chapter cannot publish until every pending row is approved or skipped
(dcp_commit_approved.find_committable_chapters). The rows left are table cells, short rows and text that is not
a requirement. Waverley Amendment 6 (2026-11-11): 140 left; deciding them meant a signed-in browser.

RULE, each row re-judged here against the chapter's CURRENT file (staged if one is held aside):
  APPROVE  an added/changed row that states a requirement (a figure or "must/minimum/maximum/is to/are to")
           AND every one of its cells (split on '|' and line breaks, >3 chars) is printed on its stated page
           or the page either side. The words then come from the council's page, which is the rule we serve.
  SKIP     everything else: not a requirement (history, colour tables, contents lines), a removed row, or a row
           with any cell not found on the page. 'skipped' neither publishes nor blocks (migration 124).
A skipped 'changed' row that would leave a live rule unreplaced is still caught by the commit's section-loss
guard, which refuses the publish rather than drop it silently.

Dry run by default. --apply writes status/reviewed_by/reviewed_at/review_reason only, on rows still pending,
after a CSV backup of every row it touches. Rollback: restore status 'pending' for reviewed_by = REVIEWER rows
in the backup.

usage: python scripts/dcp_decide_by_page_cells.py --chapters council/chapter[,council/chapter] [--apply]
"""
from __future__ import annotations

import argparse
import atexit
import csv
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dcp_approve_proven import CHAPTER_ROWS_SQL  # noqa: E402

REVIEWER = "auto:page_cells"
REASON_OK = "every cell of this requirement is printed on its stated PDF page (dcp_decide_by_page_cells)"
REASON_SKIP = "not a requirement, a removal, or a cell not on its stated page; left out (dcp_decide_by_page_cells)"

_SUP = str.maketrans({"²": "2", "³": "3"})
NOT_A_RULE = re.compile(
    r"(table of contents|^#\s*\S*\s*contents\b|executive summary|history|description of the site|"
    r"assessment of significance|criterion \(|colour name|national trust)", re.I | re.M)


def norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").translate(_SUP).lower()).strip()


def cells(text: str | None) -> list[str]:
    """The pieces a requirement row is made of: its body (heading line dropped) split on table bars and lines."""
    body = re.sub(r"^#[^\n]*\n+", "", text or "")
    return [c.strip() for c in re.split(r"\||\n", body) if len(c.strip()) > 3]


def decide(change_type: str, text: str | None, page_text: str) -> str:
    """'approve' or 'skip' for one queued row, given the normalised text of its page and the pages either side."""
    if change_type == "removed" or not text:
        return "skip"
    if NOT_A_RULE.search(text):
        return "skip"
    body = norm(re.sub(r"^#[^\n]*\n+", "", text))
    if not body:
        return "skip"
    if body in page_text:  # the whole body is printed, in order, on its page
        return "approve"
    if "|" not in text:  # prose must match whole; only table rows may match cell by cell
        return "skip"
    parts = cells(text)
    return "approve" if parts and all(norm(p) in page_text for p in parts) else "skip"


def is_lead_in(text: str | None) -> bool:
    return (text or "").rstrip().endswith(":")


def page_window(pages: list[str], page: int | None) -> str:
    if not page:
        return ""
    return " ".join(norm(pages[p - 1]) for p in (page - 1, page, page + 1) if 0 < p <= len(pages))


def load_pages(r2_path: str) -> list[str]:
    import fitz
    import dcp_page_repair as dpr
    data = dpr._s3().get_object(Bucket=os.environ["R2_BUCKET_NAME"], Key=r2_path)["Body"].read()
    with fitz.open(stream=data, filetype="pdf") as doc:
        return [p.get_text() for p in doc]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--redo-own-skips", action="store_true",
                    help="also re-decide rows this script skipped earlier (reviewed_by REVIEWER, status skipped)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    atexit.register(lambda: conn.close())
    cur = conn.cursor()
    cur.execute("SET lock_timeout = '5s'")
    cur.execute("SET statement_timeout = '30s'")

    approve, skip, touched = [], [], []
    for council, key in (tuple(x.split("/")) for x in a.chapters.split(",") if x):
        sql = CHAPTER_ROWS_SQL
        if a.redo_own_skips:
            sql = sql.replace("q.status = 'pending'",
                              f"(q.status = 'pending' OR (q.status = 'skipped' AND q.reviewed_by = '{REVIEWER}'))")
        cur.execute(sql, (council, key))
        rows = cur.fetchall()
        if not rows:
            print(f"{council}/{key}: no pending rows on the chapter's current file")
            continue
        pages = load_pages(rows[0][5])
        verdicts = {r[0]: decide(r[1], r[3], page_window(pages, r[4])) for r in rows}
        # a lead-in ("...the following:") is kept only when an item under it on the same page is kept too
        kept_pages = {r[4] for r in rows if verdicts[r[0]] == "approve" and not is_lead_in(r[3])}
        for r in rows:
            if verdicts[r[0]] == "approve" and is_lead_in(r[3]) and r[4] not in kept_pages:
                verdicts[r[0]] = "skip"
        ok = no = 0
        for qid, change_type, ref, text, page, *_ in rows:
            verdict = verdicts[qid]
            (approve if verdict == "approve" else skip).append(qid)
            touched.append((qid, council, key, change_type, ref, verdict))
            ok += verdict == "approve"
            no += verdict == "skip"
        print(f"{council}/{key}: pending {len(rows)} -> approve {ok}, skip {no}")

    print(f"TOTAL approve {len(approve)}, skip {len(skip)}")
    if not a.apply:
        print("dry run: nothing written")
        return 0
    if not touched:
        return 0
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    backup = root / "data" / "db_rollback_backups" / f"dcp_review_queue_pre_page_cells_{stamp}.csv"
    backup.parent.mkdir(parents=True, exist_ok=True)
    with backup.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "council", "chapter_key", "change_type", "ref_number", "verdict", "status_before"])
        for t in touched:
            w.writerow([*t, "pending"])
    print(f"backup: {backup}")
    cur.execute("""UPDATE dcp_review_queue SET status = 'approved', reviewed_by = %s, reviewed_at = now(),
                   review_reason = %s WHERE id = ANY(%s) AND (status = 'pending' OR (status = 'skipped' AND reviewed_by = %s))""", (REVIEWER, REASON_OK, approve, REVIEWER))
    n_ok = cur.rowcount
    cur.execute("""UPDATE dcp_review_queue SET status = 'skipped', reviewed_by = %s, reviewed_at = now(),
                   review_reason = %s WHERE id = ANY(%s) AND (status = 'pending' OR (status = 'skipped' AND reviewed_by = %s))""", (REVIEWER, REASON_SKIP, skip, REVIEWER))
    n_skip = cur.rowcount
    conn.commit()
    print(f"WRITTEN: approved {n_ok}, skipped {n_skip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
