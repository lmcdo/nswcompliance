#!/usr/bin/env python3
# prior-art-checked: the browser is REUSED, not added. scripts/legislation_monitor.py
# already drives headless Chromium through Playwright (_get_playwright_browser) to get past
# Cloudflare, so this borrows that dependency rather than introducing wkhtmltopdf or
# weasyprint. Four sweeps, 2026-09-18:
#  (1) DB: dcp_chapter_registry rows read live below; no new table or column.
#  (2) Frontend: nothing renders a council document; the UI links to the stored PDF.
#  (3) Python: grep print-to-pdf/wkhtmltopdf/weasyprint across scripts/, services/,
#      enrichment/ returns legislation_monitor.py (Cloudflare fetch, no rendering) and
#      services/modal_inference.py (unrelated). r2_monitor.py has no content_type branch,
#      so an HTML source has nowhere to go today.
#  (4) Plans + memory: project-northern-beaches-frozen-source-url-2026-09 records the
#      problem and names no fix.
"""A council DCP published as an ePlanning book, not a PDF.

Northern Beaches serves Warringah DCP 2011 from a URL ending
"...as amended 7 May 2016.pdf" on a shared S3 bucket. That file is immutable, so its hash
can never change and every freshness check reads green while telling us nothing. The
council is on **amendment 23** — Part G10 commenced 15 September 2025 — and publishes the
current plan only as an online book with no PDF at all.

The book exposes a server-side export of the whole plan:

    .../ePlanning/live/Common/Output/Report.aspx?tag=Default&hid=6&children=true&page=book

Measured 2026-09-18: HTTP 200, 2.87 MB of HTML, 528k characters of text carrying Part G10
and the amendment schedule. Rendered headlessly it becomes a 294-page PDF whose text
matches a human's own browser print of the same URL (Part G10 9 hits in both, 'setback' 332
in both; the character counts differ by 0.4%, which is pagination).

So the fix is not a new pipeline: render the export, store it like any other council PDF,
and point the registry at the live URL so the monitor can finally see a change.

Dry run by default; --apply writes, after a CSV backup of the registry row.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

REPO = Path(__file__).resolve().parents[1]

#: The councils whose plan is an HTML book, with the export that renders the whole thing.
#: Keyed exactly as the registry keys them, so a typo cannot silently target nothing.
HTML_BOOK_SOURCES = {
    ("northern_beaches", "warringah-dcp-2011-full"):
        "https://eservices.northernbeaches.nsw.gov.au/ePlanning/live/Common/Output/"
        "Report.aspx?tag=Default&hid=6&children=true&page=book",
}

#: Below this the render did not produce a document. The real one is ~25 MB / 294 pages;
#: a challenge page or an error screen renders to a few hundred KB at most.
MIN_RENDER_BYTES = 2_000_000


def _env() -> dict:
    out = dict(os.environ)
    env_path = REPO / ".env"
    if not env_path.exists():  # a worktree has no .env of its own
        head, sep, _tail = str(REPO).partition(".claude")
        env_path = Path(head if sep else str(REPO)) / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            key, sep, value = line.partition("=")
            if sep and value.strip():
                out.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    return out


def render_book(url: str, dest: Path) -> Path:
    """The export as a PDF, via the same headless Chromium legislation_monitor.py uses."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True,
                                     args=["--disable-blink-features=AutomationControlled"])
        try:
            page = browser.new_page()
            # The book is one very large document; it finishes loading long after
            # 'load' fires, so wait for the network to settle rather than a fixed sleep.
            page.goto(url, wait_until="networkidle", timeout=180_000)
            page.pdf(path=str(dest), format="A4", print_background=False,
                     margin={"top": "10mm", "bottom": "10mm",
                             "left": "10mm", "right": "10mm"})
        finally:
            browser.close()
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--council", default="northern_beaches")
    ap.add_argument("--chapter", default="warringah-dcp-2011-full")
    ap.add_argument("--apply", action="store_true", help="write; omit for a dry run")
    args = ap.parse_args()

    key = (args.council, args.chapter)
    url = HTML_BOOK_SOURCES.get(key)
    if not url:
        print(f"{args.council}/{args.chapter} is not a registered HTML-book source; "
              f"known: {sorted(HTML_BOOK_SOURCES)}")
        return 1

    env = _env()
    stamp = f"{datetime.now(timezone.utc):%Y-%m-%d}"
    work = Path(env.get("CLAUDE_JOB_DIR", str(REPO))) / "tmp"
    work.mkdir(parents=True, exist_ok=True)
    pdf = work / f"{args.council}__{args.chapter}__{stamp}.pdf"

    print(f"rendering {url}")
    render_book(url, pdf)
    size = pdf.stat().st_size
    print(f"    rendered {size:,} bytes -> {pdf}")
    if size < MIN_RENDER_BYTES:
        print(f"    REFUSED: under {MIN_RENDER_BYTES:,} bytes — that is a challenge or "
              f"error page, not the plan")
        return 1

    body = pdf.read_bytes()
    if not body.startswith(b"%PDF-"):
        print("    REFUSED: rendered file is not a PDF")
        return 1
    digest = hashlib.sha256(body).hexdigest()

    import fitz
    with fitz.open(pdf) as doc:
        text = " ".join(doc[i].get_text() for i in range(doc.page_count))
        pages = doc.page_count
    print(f"    {pages} pages, {len(text):,} characters of text")
    # The render must contain the plan, not a shell. Checked against the document's own
    # words rather than a byte count, because a styled error page can be large.
    for probe in ("Warringah Development Control Plan", "AMENDMENT SCHEDULE"):
        if probe.lower() not in text.lower():
            print(f"    REFUSED: rendered document does not contain {probe!r}")
            return 1

    r2_path = f"source-pdfs/dcps/{args.council}/v-html-{stamp}/{args.chapter}.pdf"

    conn = psycopg2.connect(env["DATABASE_URL"], connect_timeout=25)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '30s'")
            cur.execute("""
                SELECT id, council_url, r2_current_path, content_hash, url_content_length,
                       needs_extraction, r2_public_pdf_url
                FROM dcp_chapter_registry WHERE council = %s AND chapter_key = %s
            """, key)
            row = cur.fetchone()
            if not row:
                print(f"    REFUSED: no registry row for {args.council}/{args.chapter}")
                return 1
            reg_id, old_url, old_path, old_hash, old_len, old_needs, old_public = row

            # The public link must move with the copy. Leaving it behind is not cosmetic:
            # conveyancing_db.py serves COALESCE(r2_public_pdf_url, council_url, ...) as
            # the link under a rule, so the reader would open the superseded document the
            # rule is no longer read from. That is the defect the OC-8 sub-check was added
            # for on 2026-09-14, when 15 chapters had it and Waverley DCP 2022's link
            # opened a 490-page PDF while its rules cited the 448-page one.
            #
            # The base is learned from this row rather than hardcoded. confirm_chapter.py
            # and add_new_chapter.py already hold identical copies of the bucket URL and a
            # third would be one more place to miss on a bucket change; taking the prefix
            # off this row's own link keeps the new URL on whatever bucket the old one used.
            # If it cannot be observed it is not guessed -- a wrong base is a link to
            # nothing, which looks like a missing document rather than a broken script.
            public_url = None
            if old_public and old_path and old_public.endswith("/" + old_path):
                public_url = old_public[: -len(old_path)] + r2_path
            elif old_public:
                print(f"    REFUSED: r2_public_pdf_url does not end with r2_current_path, "
                      f"so the bucket base cannot be read off it.\n"
                      f"      public : {old_public}\n      path   : {old_path}")
                return 1

            print(f"\n  registry row {reg_id}")
            print(f"    council_url : {old_url}\n               -> {url}")
            print(f"    r2_path     : {old_path}\n               -> {r2_path}")
            print(f"    public_url  : {old_public}\n               -> {public_url}")
            print(f"    content_hash: {(old_hash or '')[:16]} -> {digest[:16]}")
            print(f"    url_content_length: {old_len} -> {size:,}")
            print(f"    needs_extraction: {old_needs} -> True")

            backup = (REPO / "data" / "db_rollback_backups"
                      / f"dcp_chapter_registry_pre_html_repoint_{args.council}_"
                        f"{datetime.now(timezone.utc):%Y-%m-%d_%H%M}"
                        f"{'' if args.apply else '_dryrun'}.csv")
            backup.parent.mkdir(parents=True, exist_ok=True)
            with open(backup, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["id", "council", "chapter_key", "council_url_before",
                            "r2_current_path_before", "content_hash_before",
                            "url_content_length_before", "needs_extraction_before",
                            "r2_public_pdf_url_before"])
                w.writerow([reg_id, args.council, args.chapter, old_url, old_path,
                            old_hash, old_len, old_needs, old_public])
            print(f"    backup {backup}")

            if not args.apply:
                conn.rollback()
                print("\nDRY RUN — nothing uploaded, nothing written. "
                      "Re-run with --apply to commit.")
                return 0

            import boto3
            s3 = boto3.client(
                "s3", endpoint_url=f"https://{env['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                aws_access_key_id=env["R2_ACCESS_KEY_ID"],
                aws_secret_access_key=env["R2_SECRET_ACCESS_KEY"], region_name="auto")
            s3.put_object(Bucket=env["R2_BUCKET_NAME"], Key=r2_path, Body=body,
                          ContentType="application/pdf")
            print(f"    uploaded -> r2://{env['R2_BUCKET_NAME']}/{r2_path}")

            # needs_extraction is set so the chapter is re-read from the new copy. The
            # extracted-from hash is deliberately NOT touched: leaving it as it was keeps
            # DQ-70 counting these provisions as read from a superseded document, which
            # they still are until that re-read lands.
            cur.execute("""
                UPDATE dcp_chapter_registry
                SET council_url = %s, r2_current_path = %s, content_hash = %s,
                    url_content_length = %s, url_last_checked = NOW(),
                    url_last_changed = NOW(), check_failures = 0, needs_extraction = TRUE,
                    r2_public_pdf_url = COALESCE(%s, r2_public_pdf_url)
                WHERE id = %s
            """, (url, r2_path, digest, size, public_url, reg_id))
            conn.commit()
            print(f"\nAPPLIED — {args.council}/{args.chapter} now tracks the live export.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
