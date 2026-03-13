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

# Enrichment pipeline — imported here so extraction + enrichment run as one command.
# sys.path is extended so this script can be run from any working directory.
sys.path.insert(0, str(Path(__file__).parent.parent))
from enrichment.pipeline import (
    run_actionability_classification,
    run_layer_tagging,
    run_applicability_tagging,
)

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
    # All page numbers are PDF physical pages (1-indexed), verified against pdfplumber output.
    # Pages 1–11: cover/TOC/policy — excluded.
    # Part B — General Controls
    ("B1",  "Waste",                                          12,  23),
    ("B2",  "Ecologically Sustainable Development",           24,  35),
    ("B3",  "Landscaping, Biodiversity and Vegetation",       36,  48),
    ("B4",  "Coastal Risk Management",                        49,  49),
    ("B5",  "Water Management",                               50,  61),
    ("B6",  "Accessibility and Adaptability",                 62,  66),
    ("B7",  "Transport",                                      67,  86),
    ("B8",  "Heritage",                                       87, 114),
    ("B9",  "Safety",                                        115, 116),
    ("B10", "Public Art",                                    117, 117),
    ("B11", "Design Excellence",                             118, 119),
    ("B12", "Subdivision",                                   120, 121),
    ("B13", "Excavation",                                    122, 124),
    ("B14", "Advertising and Signage",                       125, 135),
    ("B15", "Public Domain",                                 136, 146),
    ("B16", "Inter-War Buildings",                           147, 150),
    ("B17", "Social Impact Assessment",                      151, 151),
    # Pages 152–185: Part B annexures + Part C intro — excluded.
    # Part C — Residential Development
    ("C1",  "Low Density Residential",                       186, 218),
    ("C2",  "Other Residential Development",                 219, 249),
    # Page 250: Part D contents — excluded.
    # Part D — Commercial Development
    ("D1",  "Commercial and Retail Development",             251, 258),
    ("D2",  "Outdoor Dining",                                259, 259),
    # Pages 260–261: Part E intro/contents — excluded.
    # Part E — Site Specific Development
    ("E1",  "Bondi Junction",                                262, 315),
    ("E2",  "Bondi Beachfront Area",                         316, 338),
    ("E3",  "Local Village Centres",                         339, 373),
    ("E4",  "Special Character Areas",                       374, 379),
    ("E5",  "113 Macpherson Street Bronte",                  380, 385),
    ("E6",  "194-214 Oxford Street",                         386, 394),
    ("E7",  "Edina Estate",                                  395, 413),
    # Pages 414–458: Part E annexures — excluded.
    # Page 459: Part F contents — excluded.
    # Part F — Development Specific
    ("F1",  "Shared Residential Accommodation",              460, 461),
    ("F2",  "Tourist and Visitor Accommodation",             462, 465),
    ("F3",  "Child Care Centres",                            466, 466),
    ("F4",  "Places of Public Worship",                      467, 472),
    ("F5",  "Horticulture",                                  473, 473),
    # Pages 474+: Definitions — excluded.
]

COUNCIL_PAGE_RANGES: dict[str, list[tuple[str, str, int, int]]] = {
    "waverley": WAVERLEY_PAGE_RANGES,
}

# ── Per-chapter page ranges (for councils with per-chapter PDFs) ─────────────
# Key: (council, chapter_key) → page ranges within that chapter's PDF.
# Checked BEFORE COUNCIL_PAGE_RANGES — allows per-chapter config for councils
# that have separate PDFs per chapter (unlike Waverley which is one PDF).
COUNCIL_CHAPTER_RANGES: dict[tuple[str, str], list[tuple[str, str, int, int]]] = {
    # Ashfield DCP 2016: per-chapter PDFs, "Part X" structure.
    # Pages 1-3 of each chapter are cover/TOC — skip them.
    # Chapters G (Definitions), H (Amendments), preliminary are non-provision.
    ("ashfield", "chapter-a-miscellaneous"): [
        ("A-Part1",  "Site and Context Analysis",       4,   7),
        ("A-Part2",  "Good Design",                     8,  12),
        ("A-Part3",  "Flood Hazard",                   13,  23),
        ("A-Part4",  "Solar Access and Overshadowing",  24,  26),
        ("A-Part5",  "Landscaping",                    27,  30),
        ("A-Part6",  "Safety by Design",               31,  33),
        ("A-Part7",  "Access and Mobility",            34,  52),
        ("A-Part8",  "Parking",                        53,  89),
        ("A-Part9",  "Subdivision",                    90,  93),
        ("A-Part10", "Signs and Advertising",          94, 110),
        ("A-Part11", "Fencing",                       111, 113),
        ("A-Part12", "Telecommunications Facilities", 114, 116),
        ("A-Part13", "Development Near Rail Corridors", 117, 120),
        ("A-Part14", "Contaminated Land",             121, 123),
        ("A-Part15", "Stormwater Management",         124, 126),
    ],
    ("ashfield", "chapter-b-public-domain"): [
        ("B-Part1",  "Public Domain",                   4,  11),
    ],
    ("ashfield", "chapter-c-sustainability"): [
        ("C-Part1",  "Building Sustainability",         3,   9),
        ("C-Part2",  "Water Sensitive Urban Design",   10,  12),
        ("C-Part3",  "Waste and Recycling",            13,  76),
        ("C-Part4",  "Tree Management",                77,  85),
        ("C-Part5",  "GreenWay",                       86,  90),
    ],
    ("ashfield", "chapter-d-precinct-guidelines"): [
        ("D-Part1",  "Ashfield Town Centre",            3,  42),
        ("D-Part2",  "Ashfield East",                  43,  59),
        ("D-Part3",  "Croydon South",                  60,  85),
        ("D-Part4",  "Haberfield",                     86, 111),
        ("D-Part5",  "Hurlstone Park",                112, 157),
        ("D-Part6",  "Summer Hill",                   158, 170),
        ("D-Part7",  "Ashfield South",                171, 181),
        ("D-Part8",  "Canterbury Road",               182, 204),
    ],
    ("ashfield", "chapter-e1-heritage"): [
        # E1 has 392 pages and high SECTION_RE hit rate (175%) — let regex handle it.
        # Include full range so page-range mode is used (skips cover pages 1-2).
        ("E1-Heritage", "Heritage Items and Conservation Areas", 3, 392),
    ],
    ("ashfield", "chapter-e2-haberfield"): [
        ("E2-Haberfield", "Haberfield Neighbourhood",  2,  22),
    ],
    ("ashfield", "chapter-f-dev-category"): [
        ("F-Part1",  "Dwelling Houses and Dual Occupancies",  3,  28),
        ("F-Part2",  "Multi-Dwelling Housing",               29,  36),
        ("F-Part3",  "Residential Flat Buildings",           37,  49),
        ("F-Part4",  "Boarding Houses",                      50,  55),
        ("F-Part5",  "Commercial and Industrial",            56,  65),
        ("F-Part6",  "Childcare Centres",                    66,  72),
        ("F-Part7",  "Sex Industry",                         73,  78),
        ("F-Part8",  "Car Showrooms",                        79,  85),
    ],
}

# ── Within-section sub-section splitting patterns ────────────────────────────
# When a page-range section contains numbered sub-sections, these patterns
# split each section into multiple finer-grained provisions.
# Each pattern must have two capturing groups: (sub_number, sub_title).
# Patterns are applied in sequence — each splits the output of the previous level.
# Group 1 (sub_number) may be empty string for keyword-only headings (e.g. Objectives).
# Add new councils here — no other code changes required.
COUNCIL_SUBSECTION_PATTERNS: dict[str, list[re.Pattern]] = {
    # Waverley DCP 2022: two-level split.
    # Level 1: numbered sub-sections like "1.1 DEMOLITION AND CONSTRUCTION"
    # Level 2: Objectives/Controls keyword headings within each sub-section
    "waverley": [
        re.compile(r"(?m)^(\d+\.\d+)\s+([A-Z][A-Z0-9\s/&(),.-]+)$"),
        re.compile(
            r"(?m)^()(General Objectives|General Controls|Objectives|Controls"
            r"|Design Guidance|Performance Criteria)\s*$"
        ),
    ],
    # Ashfield DCP 2016: two-level split.
    # Level 1: keyword headings (Performance Criteria, Design Solutions, etc.)
    # Level 2: PC/DS/O/C numbered markers within each keyword section.
    #   Heritage chapters use O1..O3 + C1..C54 (each on own line).
    #   Parking/Precinct chapters use two-column table format where PC starts
    #   the line and DS appears mid-line — splitting at line-start markers keeps
    #   each PC+DS pair together as one compliance unit.
    "ashfield": [
        re.compile(
            r"(?m)^()(Performance Criteria|Design Solutions?|Application"
            r"|Objectives?|Purpose|General Requirements)\s*$"
        ),
        re.compile(
            r"(?m)^((?:PC|DS|O|C)\d+(?:\.\d+)?)[.\s]+(.+?)$"
        ),
    ],
}


# ── Text cleanup patterns (per-council) ──────────────────────────────────────
# Lines matching any of these regexes are removed from extracted text.
# Used to filter out reversed PDF sidebar text, watermarks, etc.
COUNCIL_TEXT_CLEANUP: dict[str, list[re.Pattern]] = {
    "ashfield": [
        # Reversed sidebar text from rotated text boxes in Ashfield PDFs.
        # Each PDF has the chapter name reversed in a vertical sidebar.
        re.compile(r'suoenallecsiM'),      # Miscellaneous
        re.compile(r'ytilibaniatsuS'),      # Sustainability
        re.compile(r'senilediuG'),          # Guidelines
        re.compile(r'tcnicerP'),            # Precinct
        re.compile(r'niamoD'),              # Domain (Public Domain)
        re.compile(r'cilbuP'),              # Public
        re.compile(r'egatireH'),            # Heritage
        re.compile(r'dleifrebah'),          # Haberfield (case insensitive)
        re.compile(r'yrogetaC'),            # Category
        re.compile(r'tnempoleveD'),         # Development
        re.compile(r'retpahC'),             # Chapter
        re.compile(r'dleifhsA'),            # Ashfield
        re.compile(r'tseW'),               # West (in "Inner West")
        # Short reversed lines: "traP" = Part, etc.
        re.compile(r'^[a-z]{3,20}\s*$', re.MULTILINE),  # Pure lowercase-only lines (reversed words)
    ],
}


def _clean_page_text(text: str, council: str | None) -> str:
    """Remove council-specific garbage lines from extracted page text."""
    if not council or council not in COUNCIL_TEXT_CLEANUP:
        return text
    patterns = COUNCIL_TEXT_CLEANUP[council]
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        if any(pat.search(line) for pat in patterns):
            continue
        cleaned.append(line)
    return '\n'.join(cleaned)


# ── PDF Extraction ──────────────────────────────────────────────────────────

class DCPExtractor:
    """Extract provisions from a single DCP chapter PDF using pdfplumber."""

    # Matches section numbers like "4.1.5", "2", "B1", or "C1.2" followed by a Title-cased heading.
    # [A-Z]? makes the letter prefix optional so both numeric-only and letter-prefixed
    # section codes (e.g. Waverley's "B1 WASTE", "C1 Low Density") are matched.
    SECTION_RE = re.compile(r'^([A-Z]?\d+(?:\.\d+)*)\s+([A-Z][^\n]+)$', re.MULTILINE)

    def __init__(self, pdf_path: Path, document_id: str, council: str | None = None):
        self.pdf_path = pdf_path
        self.document_id = document_id
        self.council = council
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
                text = _clean_page_text(text, self.council)
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
        self,
        ranges: list[tuple[str, str, int, int]],
        subsection_patterns: list[re.Pattern] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Extract sections using explicit page-range config.
        Used when SECTION_RE cannot detect chapter boundaries (e.g. multi-line headers).

        Args:
            ranges:               list of (section_key, title, page_start, page_end) — 1-indexed
            subsection_patterns:  optional list of regexes (two groups: sub_num, sub_title).
                                  Applied in sequence — each pattern splits the output of
                                  the previous level, enabling multi-level granularity.
                                  Group 1 (sub_num) may be empty for keyword-only headings.
                                  Configured per-council in COUNCIL_SUBSECTION_PATTERNS.
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
                    text = _clean_page_text(text, self.council)
                    content += f"\n\n{text}"
                    pages_included.append(page_num)
                    for tbl in page.extract_tables() or []:
                        html = self._table_to_html(tbl)
                        if html:
                            tables.append({"html": html, "page": page_num})

                if subsection_patterns:
                    # First pattern splits the raw page-range content
                    sub_secs = split_content_at_subsections(
                        content, section_key, title, page_start, clipped_end,
                        tables, subsection_patterns[0],
                    )
                    # Subsequent patterns split each result of the previous level.
                    # Non-actionable sections (intro/objectives) are still passed
                    # to deeper levels — they may contain sub-markers (e.g. Heritage
                    # O/C markers inside an "Objectives" section) that need splitting.
                    # Each sub-provision gets its own actionability assessment.
                    for pattern in subsection_patterns[1:]:
                        further_split: list[dict[str, Any]] = []
                        for sec in sub_secs:
                            further = split_content_at_subsections(
                                sec["content"],
                                sec["section_number"],
                                sec["section_title"],
                                sec["page_start"],
                                sec["page_end"],
                                sec["tables"],
                                pattern,
                                parent_text_heading=sec.get("text_heading"),
                            )
                            further_split.extend(further)
                        sub_secs = further_split
                    sections.extend(sub_secs)
                else:
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
        # text_heading overrides the default heading so sub-section provisions start
        # with the parent code (e.g. "B1 Waste —") which the LayerTopicTagger needs
        # to extract the correct section code via progressive prefix stripping.
        heading = section.get("text_heading") or f"{section['section_number']} {section['section_title']}"
        full_text = f"# {heading}\n\n{content}"
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


def split_content_at_subsections(
    content: str,
    parent_key: str,
    parent_title: str,
    page_start: int,
    page_end: int,
    tables: list,
    pattern: re.Pattern,
    parent_text_heading: str | None = None,
) -> list[dict[str, Any]]:
    """
    Split a page-range section into finer-grained sub-section provisions.

    Each match of `pattern` (two groups: sub_number, sub_title) becomes its own
    provision.  Text before the first match becomes the intro provision if non-empty.
    All sub-provisions inherit page_start — intra-section page boundaries are not
    tracked at extraction time.

    Group 1 (sub_number) may be an empty string for keyword-only headings such as
    "Objectives" or "Controls" — in that case the sub_title is used for the key slug.

    parent_text_heading: when set (second-level splits), carries the heading built
    by the first-level split so deep provisions chain correctly, e.g.:
        "B1 Waste — 1.1 Demolition And Construction — Controls"

    Returns a single-element list (the original section dict) when the pattern finds
    no matches, so callers can safely call this unconditionally for every page range.
    """
    # Keyword headings that are aspirational/descriptive only — not actionable controls
    NON_ACTIONABLE_KEYWORDS = {"Objectives", "General Objectives"}

    matches = list(pattern.finditer(content))
    if not matches:
        # No split found — pass through parent's actionability (default True)
        return [{
            "section_number":   parent_key,
            "section_title":    parent_title,
            "content":          content,
            "tables":           tables,
            "page_start":       page_start,
            "page_end":         page_end,
            "pages":            [],
            **({"text_heading": parent_text_heading} if parent_text_heading else {}),
        }]

    result: list[dict[str, Any]] = []

    # Intro provision: context/description text before the first sub-heading — never actionable
    intro_text = content[:matches[0].start()].strip()
    if intro_text:
        result.append({
            "section_number":   parent_key,
            "section_title":    parent_title,
            "content":          intro_text,
            "tables":           tables,   # All tables stay with the intro provision
            "page_start":       page_start,
            "page_end":         page_end,
            "pages":            [],
            "v2_is_actionable": False,
            **({"text_heading": parent_text_heading} if parent_text_heading else {}),
        })

    # Base heading for building child headings (chains across split levels)
    base_heading = parent_text_heading or f"{parent_key} {parent_title}"

    for i, match in enumerate(matches):
        sub_num   = match.group(1)          # e.g. "1.1" or "" for Objectives/Controls
        sub_title = match.group(2).strip()  # e.g. "DEMOLITION AND CONSTRUCTION"
        end  = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[match.end():end].strip()

        # Unique key: numbered sub-sections use dots→underscores ("B1_1_1"),
        # keyword headings use slugified title ("B1_1_1_objectives").
        if sub_num:
            sub_key = f"{parent_key}_{sub_num.replace('.', '_')}"
            text_heading = f"{base_heading} \u2014 {sub_num} {sub_title.title()}"
        else:
            sub_key = f"{parent_key}_{sub_title.lower().replace(' ', '_')}"
            text_heading = f"{base_heading} \u2014 {sub_title.title()}"

        # Objectives (and any other non-actionable keywords) are descriptive goals,
        # not controls — mark them non-actionable.
        is_actionable = sub_title not in NON_ACTIONABLE_KEYWORDS

        result.append({
            "section_number":   sub_key,
            "section_title":    f"{parent_title} \u2014 {sub_title.title()}",
            "content":          body,
            "tables":           [],
            "page_start":       page_start,
            "page_end":         page_end,
            "pages":            [],
            "text_heading":     text_heading,
            "v2_is_actionable": is_actionable,
        })

    return result


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

        extractor = DCPExtractor(pdf_path, document_id, council=council)

        # If a page-range config exists for this council/chapter, use it directly.
        # This handles DCPs where SECTION_RE matches TOC entries instead of real
        # section headings (e.g. Waverley: 297 TOC hits vs ~24 real sections).
        # Per-chapter ranges checked first (for councils with separate chapter PDFs).
        page_ranges = COUNCIL_CHAPTER_RANGES.get((council, chapter_key))
        if page_ranges is None:
            page_ranges = COUNCIL_PAGE_RANGES.get(council)
        subsection_patterns = COUNCIL_SUBSECTION_PATTERNS.get(council)
        if page_ranges:
            try:
                sections = extractor.extract_by_page_ranges(page_ranges, subsection_patterns)
            except Exception as exc:
                print(f"    [ERROR] Page-range extraction failed: {exc}")
                cur.close()
                return False
            table_count = sum(len(s["tables"]) for s in sections)
            print(f"    Page-range extraction: {len(sections)} sections, {table_count} tables")
        else:
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
            min_sections = max(2, extractor.page_count // 30)
            if len(sections) < min_sections:
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
                # v2_is_actionable:
                #   False  — preamble (TOC/cover) or structural non-actionable set by
                #            split_content_at_subsections (intro text, objectives headings)
                #   NULL   — all other provisions: the enrichment pipeline's actionability
                #            phase (ActionableClassifier) will determine this before any
                #            other phase runs.
                v2_actionable = False if is_preamble else section.get("v2_is_actionable", None)

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
                        v2_actionable,
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

    # ── Quality gate ─────────────────────────────────────────────────────────
    # Check data quality before wasting resources on enrichment.
    # Gate thresholds: granularity ≥50%, text_quality ≥95%, duplicates ≥95%, pages ≥90%
    print(f"\n{'='*60}")
    print("QUALITY GATE")
    print(f"{'='*60}")

    from scripts.dcp_quality_report import check_gate
    gate_council = args.council or None
    passed, failures = check_gate(council_filter=gate_council)
    if not passed:
        print("\n  Quality gate FAILED — skipping enrichment.")
        for f in failures:
            print(f"    • {f}")
        print("\n  Fix data quality issues, then re-run extraction or run enrichment manually.")
        sys.exit(1)
    else:
        print("\n  Quality gate PASSED — proceeding to enrichment.")

    # ── Enrichment pipeline ──────────────────────────────────────────────────
    # Run automatically after any successful extraction so new provisions are
    # fully enriched without needing a separate manual command.
    # Phase order is mandatory: actionability must run before layer/applicability
    # because those phases filter WHERE v2_is_actionable = TRUE.
    print(f"\n{'='*60}")
    print("ENRICHMENT PIPELINE")
    print(f"{'='*60}")

    print("\n[1/3] Actionability classification...")
    run_actionability_classification(batch_size=500)

    print("\n[2/3] Layer + topic tagging...")
    run_layer_tagging(batch_size=500)

    print("\n[3/3] Applicability tagging...")
    run_applicability_tagging(batch_size=500)

    sys.exit(2)


if __name__ == "__main__":
    main()
