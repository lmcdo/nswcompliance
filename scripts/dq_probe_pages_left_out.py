"""DQ-112: a served chapter is missing a page of rules its source prints.

The AI reader skipped pages inside batches that returned something, so nothing
noticed (2026-09-25): Canterbury-Bankstown 6-2 went live missing pages of
objectives and principles, and the Warringah re-read would have deleted 172
printed rules. page_coverage counts it by code: a page whose sentences are
mostly absent from the chapter's live rules, and which carries rule words
(must, shall, minimum ...), was left out.

Exit 0: no served chapter is missing such a page. Exit 1: at least one is,
listed with its pages. Exit 2: could not run.

    python scripts/dq_probe_pages_left_out.py [--council X]

prior-art-checked: reuse not viable because dq_probe_section_code_not_in_source
judges each row's CITATION against the page; nothing asks the reverse question
-- which printed pages have no row at all. Lines come from page_coverage, the
same code the reader now uses to re-read skipped pages.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import page_coverage as pc  # noqa: E402

CHAPTERS_SQL = """
SELECT rp.source_council, rp.source_chapter_key, reg.r2_current_path
FROM regulatory_provisions rp
JOIN dcp_chapter_registry reg
  ON reg.council = rp.source_council AND reg.chapter_key = rp.source_chapter_key
 AND reg.is_active = TRUE AND reg.r2_current_path IS NOT NULL
WHERE rp.is_current AND rp.source_council IS NOT NULL
  AND (%(council)s IS NULL OR rp.source_council = %(council)s)
GROUP BY 1, 2, 3 ORDER BY 1, 2
"""
TEXT_SQL = """
SELECT provision_text FROM regulatory_provisions
WHERE is_current AND source_council = %s AND source_chapter_key = %s
"""


def chapter_gaps(page_lines: dict[int, list[str]], texts: list[str]) -> list[int]:
    """Pages left out that carry rule words. Pure."""
    return [p for p in pc.skipped_pages(page_lines, texts) if pc.holds_rules(page_lines[p])]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--council")
    args = ap.parse_args()
    try:
        import boto3
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
        s3 = boto3.client(
            "s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
        bucket = os.environ["R2_BUCKET_NAME"]
    except Exception as exc:  # noqa: BLE001 -- any setup failure is "could not run"
        print(f"DQ-112 could not run: {exc}")
        return 2
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30000'")
        cur.execute(CHAPTERS_SQL, {"council": args.council})
        chapters = cur.fetchall()
        bad, pages_total, unread = [], 0, []
        for council, chapter, r2 in chapters:
            cur.execute(TEXT_SQL, (council, chapter))
            texts = [row[0] or "" for row in cur.fetchall()]
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    local = os.path.join(tmp, "src.pdf")
                    s3.download_file(bucket, r2, local)
                    lines = pc.pdf_page_lines(local)
            except Exception as exc:  # noqa: BLE001 -- reported, never passed
                unread.append(f"{council}/{chapter}: {exc}")
                continue
            gaps = chapter_gaps(lines, texts)
            if gaps:
                bad.append((council, chapter, gaps))
                pages_total += len(gaps)
    finally:
        conn.close()
    print(f"served chapters checked: {len(chapters) - len(unread)} of {len(chapters)}")
    for u in unread:
        print(f"  NOT CHECKED {u}")
    print(f"CHAPTERS MISSING A PAGE OF RULES: {len(bad)} ({pages_total} pages)")
    for council, chapter, gaps in sorted(bad, key=lambda b: -len(b[2])):
        print(f"  {len(gaps):4}  {council}/{chapter}  pages {gaps}")
    if unread:
        return 2
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
