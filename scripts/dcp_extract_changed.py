#!/usr/bin/env python3
"""
DCP Chapter Extraction Pipeline
================================
Queries dcp_chapter_registry for chapters with needs_extraction=TRUE,
downloads each chapter PDF from R2, extracts provisions with pdfplumber,
and updates the database atomically per chapter.

If a chapter fails, it rolls back — old provisions stay live and
needs_extraction stays TRUE so the next monitor run retries automatically.

Usage:
    python3 scripts/dcp_extract_changed.py               # extract all flagged chapters
    python3 scripts/dcp_extract_changed.py --council marrickville
    python3 scripts/dcp_extract_changed.py --dry-run     # extract but no DB writes

Exit codes:
    0 = nothing to extract (no needs_extraction=TRUE rows)
    1 = at least one chapter was attempted and all failed
    2 = at least one chapter extracted successfully
"""

import argparse
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import boto3
import pdfplumber
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

R2_ACCOUNT_ID        = os.environ["R2_ACCOUNT_ID"]
R2_BUCKET_NAME       = os.environ["R2_BUCKET_NAME"]
R2_ACCESS_KEY_ID     = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
DATABASE_URL         = os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"]

R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"


# ── Council-specific page range configs ─────────────────────────────────────
# Used as fallback when SECTION_RE can't detect chapter boundaries (e.g., multi-line headers).
# Tuple format: (section_key, title, page_start, page_end)  — 1-indexed page numbers.

WAVERLEY_PAGE_RANGES: list[tuple[str, str, int, int]] = [
    # Pages 1–3 are cover/TOC/policy — excluded deliberately, not inserted as provisions.
    # Pages 150–183 are index/TOC for Part C onwards — also excluded.
    ("B1",  "Waste",                                    4,  15),
    ("B2",  "Sustainability",                          16,  27),
    ("B3",  "Landscaping",                             28,  40),
    ("B4",  "Coastal Hazards",                         41,  52),  # B4/B5 share range
    ("B5",  "Water Management",                        41,  52),
    ("B6",  "Accessibility",                           53,  57),
    ("B7",  "Transport and Parking",                   58,  77),
    ("B8",  "Heritage",                                78, 105),
    ("B9",  "Safety and Security",                    106, 107),
    ("B10", "Public Art",                             108, 108),
    ("B11", "Design Excellence",                      109, 110),
    ("B12", "Subdivision",                            111, 112),
    ("B13", "Excavation and Earthworks",              113, 115),
    ("B14", "Signage and Advertising",                116, 137),
    ("B16", "Inter-War Buildings",                    138, 141),
    ("B17", "Social Impact Assessment",               142, 149),
    ("C1",  "Low Density Residential",                184, 216),
    ("C2",  "Medium to High Density Residential",     217, 247),
    ("D1",  "Commercial Premises",                    248, 255),
    ("D2",  "Mixed Use",                              256, 256),
    ("E1",  "Bondi Junction Centre",                  257, 310),
    ("E2",  "Bondi Beachfront Area",                  311, 333),
    ("E3",  "Local Village Centres",                  334, 368),
    ("E4",  "Special Character Areas",                369, 374),
    ("E5",  "113 Macpherson Street Bronte",           375, 453),
    ("F1",  "Shared Accommodation",                   454, 455),
    ("F2",  "Tourist and Visitor Accommodation",      456, 490),
]

COUNCIL_PAGE_RANGES: dict[str, list[tuple[str, str, int, int]]] = {
    "waverley": WAVERLEY_PAGE_RANGES,
}


# ── PDF Extraction ──────────────────────────────────────────────────────────

class DCPExtractor:
    """Extract provisions from a single DCP chapter PDF using pdfplumber."""

    # Matches section numbers like "4.1.5", "2", "B1", or "C1.2" followed by a Title-cased heading.
    # [A-Z]? makes the letter prefix optional so both numeric-only and letter-prefixed
    # section codes (e.g. Waverley's "B1 WASTE", "C1 Low Density") are matched.
    SECTION_RE = re.compile(r'^([A-Z]?\d+(?:\.\d+)*)\s+([A-Z][^\n]+)$', re.MULTILINE)

    def __init__(self, pdf_path: Path, document_id: str):
        self.pdf_path = pdf_path
        self.document_id = document_id
        self.page_count: int = 0

    def extract(self) -> list[dict[str, Any]]:
        """
        Return list of section dicts:
            section_number, section_title, content, tables, page_start, page_end, pages
        """
        sections: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None

        with pdfplumber.open(self.pdf_path) as pdf:
            total = len(pdf.pages)
            self.page_count = total
            for page_num, page in enumerate(pdf.pages, start=1):
                print(f"    page {page_num}/{total}", end="\r")

                text = page.extract_text() or ""
                page_tables = page.extract_tables() or []

                match = self.SECTION_RE.search(text)
                if match:
                    if current:
                        current["page_end"] = page_num - 1
                        sections.append(current)
                    current = {
                        "section_number": match.group(1),
                        "section_title": match.group(2).strip(),
                        "content": "",
                        "tables": [],
                        "page_start": page_num,
                        "page_end": page_num,
                        "pages": [page_num],
                    }

                if current:
                    current["content"] += f"\n\n{text}"
                    if page_num not in current["pages"]:
                        current["pages"].append(page_num)
                    for tbl in page_tables:
                        html = self._table_to_html(tbl)
                        if html:
                            current["tables"].append({"html": html, "page": page_num})
                else:
                    # Pre-section preamble (TOC, cover, etc.)
                    if not sections or sections[-1].get("section_number") != "preamble":
                        sections.append({
                            "section_number": "preamble",
                            "section_title": "Document Information",
                            "content": text,
                            "tables": [],
                            "page_start": page_num,
                            "page_end": page_num,
                            "pages": [page_num],
                        })
                    else:
                        sections[-1]["content"] += f"\n\n{text}"
                        sections[-1]["page_end"] = page_num
                        if page_num not in sections[-1]["pages"]:
                            sections[-1]["pages"].append(page_num)

            if current:
                current["page_end"] = total
                sections.append(current)

        print()  # clear progress line
        return sections

    def extract_by_page_ranges(
        self, ranges: list[tuple[str, str, int, int]]
    ) -> list[dict[str, Any]]:
        """
        Extract sections using explicit page-range config.
        Used as fallback when SECTION_RE can't detect headers (e.g. multi-line headers).

        Args:
            ranges: list of (section_key, title, page_start, page_end) — 1-indexed
        """
        sections: list[dict[str, Any]] = []
        with pdfplumber.open(self.pdf_path) as pdf:
            self.page_count = len(pdf.pages)
            for section_key, title, page_start, page_end in ranges:
                content = ""
                tables: list[dict] = []
                pages_included: list[int] = []
                clipped_end = min(page_end, self.page_count)
                for page_num in range(page_start, clipped_end + 1):
                    page = pdf.pages[page_num - 1]
                    text = page.extract_text() or ""
                    content += f"\n\n{text}"
                    pages_included.append(page_num)
                    for tbl in page.extract_tables() or []:
                        html = self._table_to_html(tbl)
                        if html:
                            tables.append({"html": html, "page": page_num})
                sections.append({
                    "section_number": section_key,
                    "section_title":  title,
                    "content":        content,
                    "tables":         tables,
                    "page_start":     page_start,
                    "page_end":       clipped_end,
                    "pages":          pages_included,
                })
        print()
        return sections

    def _table_to_html(self, table_data: list[list[str | None]]) -> str:
        """Convert pdfplumber table data to clean HTML."""
        if not table_data or len(table_data) < 2:
            return ""

        html = "<table>\n"
        first_row = table_data[0]
        is_header = all(
            cell and len(str(cell).strip()) < 50
            for cell in first_row
            if cell
        )

        if is_header:
            html += "<thead>\n<tr>\n"
            for cell in first_row:
                html += f"  <th>{(cell or '').strip()}</th>\n"
            html += "</tr>\n</thead>\n<tbody>\n"
            data_rows = table_data[1:]
        else:
            html += "<tbody>\n"
            data_rows = table_data

        for row in data_rows:
            html += "<tr>\n"
            for cell in row:
                html += f"  <td>{(cell or '').strip()}</td>\n"
            html += "</tr>\n"

        html += "</tbody>\n</table>"
        return html

    @staticmethod
    def clean_content(content: str) -> str:
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r'\nPage \d+\n', '\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        return content.strip()


def build_provision_text(section: dict[str, Any]) -> str:
    content = DCPExtractor.clean_content(section["content"])
    if section["section_number"] != "preamble":
        full_text = f"# {section['section_number']} {section['section_title']}\n\n{content}"
    else:
        full_text = content
    if section["tables"]:
        full_text += "\n\n---\n\n"
        for j, tbl in enumerate(section["tables"]):
            full_text += f"\n\n**Table {j + 1}** (Page {tbl['page']})\n\n{tbl['html']}\n\n"
    return full_text


def build_ref_number(document_id: str, section_number: str) -> str:
    if section_number == "preamble":
        return f"{document_id}__preamble"
    return f"{document_id}__{section_number.replace('.', '_')}"


# ── Database helpers ────────────────────────────────────────────────────────

def resolve_document_id(cur, council: str, chapter_key: str, dcp_name: str) -> str:
    """
    Try to find an existing document_id used by provisions from this chapter.
    Fall back to constructing one from dcp_name + chapter_key.
    """
    cur.execute(
        """
        SELECT DISTINCT document_id
        FROM regulatory_provisions
        WHERE source_council = %s
          AND source_chapter_key = %s
          AND document_id IS NOT NULL
        LIMIT 1
        """,
        (council, chapter_key),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    # Construct: 'Marrickville DCP 2011' + 'part2-s10-parking'
    # → 'Marrickville_DCP_2011__part2_s10_parking'
    base = re.sub(r'\s+', '_', dcp_name.strip())
    chapter_slug = chapter_key.replace('-', '_')
    return f"{base}__{chapter_slug}"


def fetch_pending_chapters(cur, council_filter: str | None) -> list[dict]:
    query = """
        SELECT id, council, chapter_key, chapter_label,
               r2_current_path, r2_version_label, dcp_name
        FROM dcp_chapter_registry
        WHERE needs_extraction = TRUE
          AND is_active = TRUE
          AND r2_current_path IS NOT NULL
    """
    params: list = []
    if council_filter:
        query += " AND council = %s"
        params.append(council_filter)
    query += " ORDER BY council, sort_order"

    cur.execute(query, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


# ── Per-chapter extraction ──────────────────────────────────────────────────

def extract_chapter(
    chapter: dict,
    s3,
    conn,
    dry_run: bool,
) -> bool:
    """
    Download PDF, extract provisions, commit atomically.
    Returns True on success, False on failure.
    Old provisions stay live on failure (rollback keeps them).
    """
    council     = chapter["council"]
    chapter_key = chapter["chapter_key"]
    chapter_id  = chapter["id"]
    r2_path     = chapter["r2_current_path"]
    version     = chapter["r2_version_label"] or "unknown"
    dcp_name    = chapter["dcp_name"]

    print(f"\n  [{council}/{chapter_key}]")
    print(f"    r2: {r2_path}")

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / f"{chapter_key}.pdf"

        # 1. Download from R2
        print(f"    Downloading from R2...")
        try:
            s3.download_file(R2_BUCKET_NAME, r2_path, str(pdf_path))
        except Exception as exc:
            print(f"    [ERROR] R2 download failed: {exc}")
            return False

        print(f"    Downloaded {pdf_path.stat().st_size:,} bytes")

        # 2. Extract sections
        cur = conn.cursor()
        document_id = resolve_document_id(cur, council, chapter_key, dcp_name)
        print(f"    document_id: {document_id}")

        extractor = DCPExtractor(pdf_path, document_id)
        try:
            sections = extractor.extract()
        except Exception as exc:
            print(f"    [ERROR] PDF extraction failed: {exc}")
            cur.close()
            return False

        table_count = sum(len(s["tables"]) for s in sections)
        print(f"    Extracted: {len(sections)} sections, {table_count} tables")

        if not sections:
            print(f"    [WARN] No sections extracted — skipping chapter")
            cur.close()
            return False

        # Sanity gate: require at least 1 section per 30 pages of PDF.
        # If a page-range config exists for this council, use it as a fallback
        # instead of aborting (handles councils with multi-line section headers).
        min_sections = max(2, extractor.page_count // 30)
        if len(sections) < min_sections:
            page_ranges = COUNCIL_PAGE_RANGES.get(council)
            if page_ranges:
                print(
                    f"    [WARN] {len(sections)} sections from "
                    f"{extractor.page_count}-page PDF (min {min_sections}) "
                    f"— trying page-range fallback"
                )
                sections = extractor.extract_by_page_ranges(page_ranges)
                table_count = sum(len(s["tables"]) for s in sections)
                print(f"    Page-range fallback: {len(sections)} sections, {table_count} tables")
            else:
                verdict = "WARN" if dry_run else "ABORT"
                print(
                    f"    [{verdict}] {len(sections)} sections from "
                    f"{extractor.page_count}-page PDF (min {min_sections})"
                )
                if not dry_run:
                    cur.close()
                    return False

        if dry_run:
            print(f"    [dry-run] Would soft-delete old provisions and insert {len(sections)} new ones")
            cur.close()
            return True

        # 3. Atomic DB transaction
        now = datetime.now(timezone.utc)
        page_start = sections[0]["page_start"]
        page_end   = sections[-1]["page_end"]

        try:
            # Soft-delete existing provisions from this chapter
            cur.execute(
                """
                UPDATE regulatory_provisions
                SET is_current = FALSE
                WHERE source_chapter_key = %s
                  AND source_council = %s
                  AND is_current = TRUE
                """,
                (chapter_key, council),
            )
            soft_deleted = cur.rowcount
            print(f"    Soft-deleted {soft_deleted} old provisions")

            # Bulk INSERT new provisions
            inserted = 0
            for section in sections:
                ref_number     = build_ref_number(document_id, section["section_number"])
                provision_text = build_provision_text(section)

                is_preamble = section["section_number"] == "preamble"

                cur.execute(
                    """
                    INSERT INTO regulatory_provisions (
                        document_id,
                        ref_number,
                        section_header,
                        provision_text,
                        pdf_page,
                        pdf_source_file,
                        page_range,
                        extraction_method,
                        source_chapter_key,
                        source_council,
                        is_current,
                        v2_is_actionable
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        'pdfplumber-ci',
                        %s, %s, TRUE, %s
                    )
                    """,
                    (
                        document_id,
                        ref_number,
                        section["section_title"],
                        provision_text,
                        section["page_start"],
                        chapter_key,
                        section.get("pages", [section["page_start"]]),
                        chapter_key,
                        council,
                        False if is_preamble else None,
                    ),
                )
                inserted += 1

            # Mark chapter extracted in registry
            cur.execute(
                """
                UPDATE dcp_chapter_registry
                SET needs_extraction        = FALSE,
                    last_extracted_at       = %s,
                    last_extracted_version  = %s,
                    page_start              = %s,
                    page_end                = %s
                WHERE id = %s
                """,
                (now, version, page_start, page_end, chapter_id),
            )

            conn.commit()
            print(f"    [OK] Inserted {inserted} provisions (pages {page_start}–{page_end})")

        except Exception as exc:
            conn.rollback()
            print(f"    [ERROR] DB transaction failed — rolled back: {exc}")
            cur.close()
            return False

        cur.close()
        return True


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="DCP chapter extraction pipeline")
    parser.add_argument("--council", help="Filter to specific council")
    parser.add_argument("--dry-run", action="store_true", help="Extract but no DB writes")
    args = parser.parse_args()

    s3 = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    print("=" * 60)
    print(f"DCP Extraction Pipeline — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    if args.dry_run:
        print("DRY RUN")
    print("=" * 60)

    try:
        cur = conn.cursor()
        chapters = fetch_pending_chapters(cur, args.council)
        cur.close()
    except Exception as exc:
        print(f"[ERROR] Could not query dcp_chapter_registry: {exc}")
        conn.close()
        sys.exit(1)

    if not chapters:
        print("Nothing to extract — no chapters with needs_extraction=TRUE.")
        conn.close()
        sys.exit(0)

    print(f"Found {len(chapters)} chapter(s) to extract:")
    for ch in chapters:
        print(f"  [{ch['council']}] {ch['chapter_key']}")

    succeeded = 0
    failed    = 0

    for chapter in chapters:
        ok = extract_chapter(chapter, s3, conn, args.dry_run)
        if ok:
            succeeded += 1
        else:
            failed += 1

    conn.close()

    print(f"\n{'='*60}")
    print("EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"  Chapters attempted : {len(chapters)}")
    print(f"  Succeeded          : {succeeded}")
    print(f"  Failed             : {failed}")

    if succeeded == 0:
        print("\n  All chapters failed. Failed chapters retain needs_extraction=TRUE for retry.")
        sys.exit(1)

    if failed > 0:
        print(f"\n  {failed} chapter(s) failed — retained needs_extraction=TRUE for retry.")

    sys.exit(2)


if __name__ == "__main__":
    main()
