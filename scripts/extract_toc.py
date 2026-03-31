#!/usr/bin/env python3
"""Extract TOC entries from a DCP chapter PDF and write to dcp_table_of_contents.

Two extraction modes:
  toc-page     Scan early pages for a printed table-of-contents page
               (5+ section-code hits on one page). Parses section->page number pairs.
  heading-scan Walk every page with SECTION_RE. Records the first page each heading
               appears; derives page_end as next_heading_page - 1.

Auto mode tries toc-page first, falls back to heading-scan.

Exit codes:
  0   Success — min_sections reached, entries written/printed
  1   Error (bad args, PDF unreadable, DB failure)
  2   Catch-all only — fewer than min_sections found; a depth=0 catch-all entry
      is output instead. Requires manual follow-up.

Usage:
  python scripts/extract_toc.py \\
      --pdf <local_path_or_r2_key> \\
      --document-id <doc_id> \\
      --council <council_slug> \\
      [--mode auto|toc-page|heading-scan] \\
      [--output sql|db|both] \\
      [--min-sections 3] \\
      [--replace] \\
      [--dry-run]

Examples:
  # Auto mode, print SQL only
  python scripts/extract_toc.py \\
      --pdf "dcps/ashfield/chapter_f3.pdf" \\
      --document-id "Inner_West_Ashfield_DCP_2016__chapter_f3_dwelling_houses" \\
      --council ashfield --output sql

  # Write directly to DB (production)
  python scripts/extract_toc.py \\
      --pdf r2:dcps/ashfield/chapter_f3.pdf \\
      --document-id "Inner_West_Ashfield_DCP_2016__chapter_f3_dwelling_houses" \\
      --council ashfield --output db

  # Heading scan only, 5 min sections required
  python scripts/extract_toc.py \\
      --pdf /tmp/chapter.pdf \\
      --document-id "Some_DCP__chapter_name" \\
      --council leichhardt \\
      --mode heading-scan --min-sections 5 --output both
"""

import argparse
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import boto3
import pdfplumber
import psycopg2


# ── Env loading ────────────────────────────────────────────────────────────────

def _load_env() -> dict:
    """Load env vars from root .env (R2 creds) and frontend-nextjs/.env.local (DB URL)."""
    env = {}
    candidates = [
        Path(__file__).parent.parent / ".env",
        Path(__file__).parent.parent / "frontend-nextjs" / ".env.local",
        Path(__file__).parent.parent / ".env.local",
    ]
    for path in candidates:
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


# ── Regex patterns ──────────────────────────────────────────────────────────────

# Default section heading pattern (mirrors DCPExtractor.SECTION_RE).
SECTION_RE = re.compile(r'^([A-Z]?\d+(?:\.\d+)*)\s+([A-Z][^\n]+)$', re.MULTILINE)

# Per-council SECTION_RE overrides (mirrors COUNCIL_SECTION_RE_OVERRIDES in extractor).
COUNCIL_SECTION_RE: dict[str, re.Pattern] = {
    "ku_ring_gai": re.compile(
        r'^([A-Z]?\d+\.\d+(?:\.\d+)*)\s+([A-Z][^\n]+)$', re.MULTILINE
    ),
    "marrickville": re.compile(
        r'^([A-Z]\d+(?:\.\d+)*|\d+(?:\.\d+)+)\s+([A-Z][^\n]+)$', re.MULTILINE
    ),
    "woollahra": re.compile(
        r'^([A-Z]\d+\.\d[\d.]*)\s+([A-Z][^\n]+)$', re.MULTILINE
    ),
}

# Matches a printed TOC line: section_number + title + dotted leaders / spaces + page_number.
# e.g. "2.1  Active Street Frontages ........... 4"
# e.g. "B-s1 Active Street Frontages         4"
TOC_LINE_RE = re.compile(
    r'^([A-Z]?\d+(?:[.\-]\d+)*(?:[.\-][A-Za-z]\S*)?)\s+'  # section number (allows B-s1)
    r'(.+?)'                                                 # title (non-greedy)
    r'(?:\s*[.·]{3,}\s*|\s{3,})'                           # dotted leaders OR 3+ spaces
    r'(\d+)\s*$',                                            # page number
    re.MULTILINE,
)

# Number of TOC-line hits on a page to treat it as a printed TOC page.
TOC_PAGE_HIT_THRESHOLD = 5


# ── Depth inference ─────────────────────────────────────────────────────────────

def _infer_depth(section_number: str) -> int:
    """Infer nesting depth from section_number dot/dash count.

    Examples:
        "1"      -> 1
        "2.1"    -> 2
        "2.1.3"  -> 3
        "B-s1"   -> 2  (one separator)
        "intro"  -> 1
    """
    separators = section_number.count(".") + section_number.count("-")
    return separators + 1


# ── PDF utilities ──────────────────────────────────────────────────────────────

def _page_text(page) -> str:
    """Extract text from a pdfplumber page, tolerating extraction errors."""
    try:
        return page.extract_text() or ""
    except Exception:
        return ""


# ── TOC-page mode ──────────────────────────────────────────────────────────────

def extract_from_toc_page(
    pdf_path: Path,
    council: str,
    scan_pages: int = 6,
) -> list[dict]:
    """Scan first `scan_pages` pages for a printed TOC page and parse section entries.

    Returns a list of dicts with keys: section_number, section_title, page_start, page_end, depth.
    page_end is None for the last section (or when only one entry).
    Returns [] if no TOC page detected.
    """
    section_re = COUNCIL_SECTION_RE.get(council, SECTION_RE)

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        pages_to_scan = min(scan_pages, total)

        toc_entries: list[tuple[str, str, int]] = []  # (number, title, page)

        for page_num in range(pages_to_scan):
            page = pdf.pages[page_num]
            text = _page_text(page)

            # Check if this page looks like a printed TOC (5+ section-code hits).
            toc_hits = len(section_re.findall(text))
            if toc_hits < TOC_PAGE_HIT_THRESHOLD:
                continue

            # Parse TOC lines on this page.
            matches = TOC_LINE_RE.findall(text)
            if len(matches) >= 3:
                toc_entries = [(m[0].strip(), m[1].strip(), int(m[2])) for m in matches]
                print(f"  [toc-page] found TOC page at pdf page {page_num + 1} "
                      f"({len(toc_entries)} entries)")
                break

    if not toc_entries:
        return []

    # Build result: page_end = next entry's page_start - 1; last gets None.
    # Clamp page_end to >= page_start to handle same-page consecutive entries.
    results = []
    for i, (num, title, page_start) in enumerate(toc_entries):
        if i < len(toc_entries) - 1:
            raw_end = toc_entries[i + 1][2] - 1
            page_end = max(page_start, raw_end)
        else:
            page_end = None
        results.append({
            "section_number": num,
            "section_title":  title,
            "page_start":     page_start,
            "page_end":       page_end,
            "depth":          _infer_depth(num),
        })

    return results


# ── Heading-scan mode ──────────────────────────────────────────────────────────

def extract_from_heading_scan(
    pdf_path: Path,
    council: str,
) -> list[dict]:
    """Walk every page detecting section headings via SECTION_RE.

    Skips TOC pages (5+ hits guard). Records the first page each heading
    appears. Derives page_end as next_heading_page - 1. Last section gets
    page_end = None.

    Returns list of dicts: section_number, section_title, page_start, page_end, depth.
    """
    section_re = COUNCIL_SECTION_RE.get(council, SECTION_RE)

    # (section_number, section_title, first_page)
    headings: list[tuple[str, str, int]] = []
    seen_codes: set[str] = set()

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for page_num, page in enumerate(pdf.pages, start=1):
            text = _page_text(page)

            # TOC page guard — skip if 5+ hits (same as extractor).
            toc_hits = len(section_re.findall(text))
            if toc_hits >= TOC_PAGE_HIT_THRESHOLD:
                continue

            match = section_re.search(text)
            if not match:
                continue

            code  = match.group(1)
            title = match.group(2).strip()

            # Skip if we've already seen this code (running page header).
            if code in seen_codes:
                continue
            # Also skip if code is a parent of an already-seen child
            # (e.g. "2.1" after seeing "2.1.3" would be a header bleed-through).
            if any(s.startswith(code + ".") for s in seen_codes):
                continue

            seen_codes.add(code)
            headings.append((code, title, page_num))

    if not headings:
        return []

    results = []
    for i, (code, title, page_start) in enumerate(headings):
        if i < len(headings) - 1:
            raw_end = headings[i + 1][2] - 1
            page_end = max(page_start, raw_end)
        else:
            page_end = None
        results.append({
            "section_number": code,
            "section_title":  title,
            "page_start":     page_start,
            "page_end":       page_end,
            "depth":          _infer_depth(code),
        })

    return results


# ── Catch-all fallback ──────────────────────────────────────────────────────────

def make_catch_all(document_id: str) -> list[dict]:
    """Return a single depth=0 catch-all entry covering all pages."""
    # Extract a short label from document_id for the title.
    label = document_id.split("__")[-1].replace("_", " ").title() if "__" in document_id else document_id
    return [{
        "section_number": "general",
        "section_title":  label,
        "page_start":     1,
        "page_end":       None,
        "depth":          0,
    }]


# ── Validation ────────────────────────────────────────────────────────────────

def validate_entries(entries: list[dict]) -> list[str]:
    """Return list of error strings; empty list means valid."""
    errors = []
    for i, e in enumerate(entries):
        if not isinstance(e["page_start"], int) or e["page_start"] < 1:
            errors.append(f"Entry {i}: page_start {e['page_start']!r} must be a positive integer")
        if e["page_end"] is not None:
            if not isinstance(e["page_end"], int) or e["page_end"] < e["page_start"]:
                errors.append(
                    f"Entry {i}: page_end {e['page_end']!r} must be >= page_start {e['page_start']}"
                )
    # Check for strict overlaps (a_end > b_page_start means a crosses into b's territory).
    # Same-page adjacency (a_end == b_page_start) is allowed — it means two sections
    # share a page boundary, which is normal when sub-sections share a parent's first page.
    for i in range(len(entries) - 1):
        a, b = entries[i], entries[i + 1]
        a_end = a["page_end"] if a["page_end"] is not None else b["page_start"] - 1
        if a_end > b["page_start"]:
            errors.append(
                f"Overlap: [{a['section_number']}] p{a['page_start']}-{a_end} "
                f"overlaps [{b['section_number']}] p{b['page_start']}"
            )
    return errors


# ── SQL output ─────────────────────────────────────────────────────────────────

def render_sql(document_id: str, entries: list[dict], catch_all: bool = False) -> str:
    """Render INSERT SQL for dcp_table_of_contents."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"-- TOC entries for {document_id}",
        f"-- Generated by extract_toc.py on {now}",
    ]
    if catch_all:
        lines.append("-- WARNING: catch-all only (< min_sections). TODO: replace with real entries.")

    lines += [
        "",
        f"DELETE FROM dcp_table_of_contents WHERE document_id = '{document_id}';",
        "",
        "INSERT INTO dcp_table_of_contents",
        "  (document_id, section_number, section_title, page_start, page_end, depth)",
        "VALUES",
    ]

    value_rows = []
    for e in entries:
        page_end_sql = str(e["page_end"]) if e["page_end"] is not None else "NULL"
        title_escaped = e["section_title"].replace("'", "''")
        num_escaped   = e["section_number"].replace("'", "''")
        value_rows.append(
            f"  ('{document_id}', '{num_escaped}', '{title_escaped}', "
            f"{e['page_start']}, {page_end_sql}, {e['depth']})"
        )

    lines.append(",\n".join(value_rows))
    lines.append("ON CONFLICT DO NOTHING;")
    return "\n".join(lines)


# ── DB write ───────────────────────────────────────────────────────────────────

def write_to_db(
    conn,
    document_id: str,
    entries: list[dict],
    replace: bool = False,
    dry_run: bool = False,
) -> bool:
    """Write entries to dcp_table_of_contents. Returns True on success."""
    cur = conn.cursor()

    # Check for existing rows.
    cur.execute(
        "SELECT COUNT(*) FROM dcp_table_of_contents WHERE document_id = %s",
        (document_id,)
    )
    (existing_count,) = cur.fetchone()

    if existing_count > 0 and not replace:
        print(
            f"  [db] {existing_count} existing rows for {document_id!r}. "
            f"Pass --replace to overwrite."
        )
        cur.close()
        return False

    if dry_run:
        print(f"  [dry-run] would write {len(entries)} entries for {document_id!r} "
              f"(replacing {existing_count} existing)")
        cur.close()
        return True

    if existing_count > 0 and replace:
        cur.execute(
            "DELETE FROM dcp_table_of_contents WHERE document_id = %s",
            (document_id,)
        )
        print(f"  [db] deleted {existing_count} existing rows")

    cur.executemany(
        """
        INSERT INTO dcp_table_of_contents
          (document_id, section_number, section_title, page_start, page_end, depth)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        """,
        [
            (document_id, e["section_number"], e["section_title"],
             e["page_start"], e["page_end"], e["depth"])
            for e in entries
        ]
    )
    conn.commit()
    cur.close()
    print(f"  [db] wrote {len(entries)} entries for {document_id!r}")
    return True


# ── R2 download ────────────────────────────────────────────────────────────────

def download_from_r2(env: dict, r2_key: str, dest: Path) -> None:
    """Download a file from R2 to `dest`."""
    r2_key = r2_key.removeprefix("r2:")
    account_id   = env["R2_ACCOUNT_ID"]
    bucket       = env["R2_BUCKET_NAME"]
    access_key   = env["R2_ACCESS_KEY_ID"]
    secret_key   = env["R2_SECRET_ACCESS_KEY"]
    endpoint     = f"https://{account_id}.r2.cloudflarestorage.com"

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    print(f"  Downloading r2://{bucket}/{r2_key} ...")
    s3.download_file(bucket, r2_key, str(dest))
    print(f"  Downloaded {dest.stat().st_size:,} bytes")


# ── Core logic ─────────────────────────────────────────────────────────────────

def run(args) -> int:
    env = _load_env()

    # ── Resolve PDF path ──────────────────────────────────────────────────────
    pdf_arg: str = args.pdf
    is_r2 = pdf_arg.startswith("r2:") or (
        not Path(pdf_arg).exists() and not pdf_arg.startswith("/") and not pdf_arg[1:3] == ":\\"
    )

    tmpdir_ctx = tempfile.TemporaryDirectory() if is_r2 else None
    try:
        if is_r2:
            tmp = Path(tmpdir_ctx.name)
            local_pdf = tmp / "chapter.pdf"
            try:
                download_from_r2(env, pdf_arg, local_pdf)
            except Exception as exc:
                print(f"[ERROR] R2 download failed: {exc}", file=sys.stderr)
                return 1
        else:
            local_pdf = Path(pdf_arg)
            if not local_pdf.exists():
                print(f"[ERROR] PDF not found: {local_pdf}", file=sys.stderr)
                return 1

        # ── Extract ───────────────────────────────────────────────────────────
        document_id  = args.document_id
        council      = args.council
        mode         = args.mode
        min_sections = args.min_sections

        entries: list[dict] = []
        catch_all = False

        if mode in ("auto", "toc-page"):
            entries = extract_from_toc_page(local_pdf, council)
            if entries:
                print(f"  [toc-page] {len(entries)} sections")

        if not entries and mode in ("auto", "heading-scan"):
            entries = extract_from_heading_scan(local_pdf, council)
            if entries:
                print(f"  [heading-scan] {len(entries)} sections")

        if not entries or len(entries) < min_sections:
            if entries:
                print(f"  [warn] only {len(entries)} section(s) found (min={min_sections})")
            else:
                print(f"  [warn] no sections found")
            entries = make_catch_all(document_id)
            catch_all = True
            print(f"  Using catch-all entry. Exit code will be 2.")

        # ── Validate ──────────────────────────────────────────────────────────
        if not catch_all:
            errors = validate_entries(entries)
            if errors:
                print("[ERROR] Validation failed:", file=sys.stderr)
                for err in errors:
                    print(f"  {err}", file=sys.stderr)
                return 1

        # ── Print entries ─────────────────────────────────────────────────────
        print(f"\n  {len(entries)} entries for {document_id!r}:")
        for e in entries:
            page_end_str = str(e["page_end"]) if e["page_end"] is not None else "end"
            print(f"    [{e['section_number']:20s}] p{e['page_start']}-{page_end_str:4s} "
                  f"depth={e['depth']}  {e['section_title']}")

        # ── Output ────────────────────────────────────────────────────────────
        output = args.output
        exit_code = 2 if catch_all else 0

        if output in ("sql", "both"):
            sql = render_sql(document_id, entries, catch_all=catch_all)
            print("\n" + sql)

        if output in ("db", "both") and not args.dry_run:
            db_url = env.get("DATABASE_URL")
            if not db_url:
                print("[ERROR] DATABASE_URL not found in env", file=sys.stderr)
                return 1
            try:
                conn = psycopg2.connect(db_url, connect_timeout=15)
            except Exception as exc:
                print(f"[ERROR] DB connection failed: {exc}", file=sys.stderr)
                return 1
            ok = write_to_db(conn, document_id, entries, replace=args.replace, dry_run=False)
            conn.close()
            if not ok:
                return 1

        if output in ("db", "both") and args.dry_run:
            print(f"  [dry-run] would write {len(entries)} entries to DB")

        return exit_code

    finally:
        if tmpdir_ctx:
            tmpdir_ctx.cleanup()


# ── CLI ─────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Extract TOC entries from a DCP chapter PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--pdf", required=True,
        help="Local path to PDF, or R2 key (prefix with 'r2:' or omit for auto-detect)",
    )
    parser.add_argument(
        "--document-id", required=True,
        help="document_id value for dcp_table_of_contents rows",
    )
    parser.add_argument(
        "--council", required=True,
        help="Council slug (used to select SECTION_RE override)",
    )
    parser.add_argument(
        "--mode", choices=["auto", "toc-page", "heading-scan"], default="auto",
        help="Extraction mode (default: auto — try toc-page then heading-scan)",
    )
    parser.add_argument(
        "--output", choices=["sql", "db", "both"], default="sql",
        help="Output destination: print SQL, write to DB, or both (default: sql)",
    )
    parser.add_argument(
        "--min-sections", type=int, default=3,
        help="Minimum sections before falling back to catch-all (default: 3)",
    )
    parser.add_argument(
        "--replace", action="store_true",
        help="Delete existing rows for this document_id before inserting",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be written without actually writing to DB",
    )
    args = parser.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
