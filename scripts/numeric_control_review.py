#!/usr/bin/env python3
"""
Numeric Control Review — diff existing dcp_setback_controls against PDF tables.

When a DCP chapter PDF changes, this script:
1. Downloads the new PDF from R2
2. Extracts all tables with pdfplumber
3. Parses numeric values from table cells using regex
4. Loads existing control rows for that chapter from DB
5. Produces a structured diff (old → new) as a review artifact

Usage:
    # Review a specific chapter after a detected change
    python scripts/numeric_control_review.py --council canterbury_bankstown --chapter ch3-2-parking

    # Dry run — no DB reads, just extract tables from a local PDF
    python scripts/numeric_control_review.py --pdf path/to/file.pdf

    # Review all chapters flagged needs_review
    python scripts/numeric_control_review.py --flagged
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Heavy deps imported lazily — allows testing pure logic without pdfplumber/psycopg2
try:
    import pdfplumber
except ImportError:
    pdfplumber = None  # type: ignore[assignment]

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None  # type: ignore[assignment]

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*a, **kw):  # type: ignore[misc]
        pass

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

# ---------------------------------------------------------------------------
# Table cell parsing — regex for numeric values in table cells
# ---------------------------------------------------------------------------

# Patterns ordered most-specific-first to avoid partial matches
CELL_PATTERNS = [
    # Range: "1.5-2.0" or "1.5 to 2.0" or "1.5 – 2.0"
    (re.compile(r"(\d+\.?\d*)\s*(?:to|–|-)\s*(\d+\.?\d*)"), "range"),
    # Fraction per unit: "0.2 per dwelling" or "1.5 spaces/dwelling"
    (re.compile(r"(\d+\.?\d*)\s*(?:spaces?/?|per\s+)"), "rate"),
    # Percentage: "30%" or "30 %"
    (re.compile(r"(\d+\.?\d*)\s*%"), "percent"),
    # Dimension with unit: "6m" or "6 m" or "6 metres"
    (re.compile(r"(\d+\.?\d*)\s*(?:m(?:etres?)?|mm)\b"), "dimension"),
    # Plain number (last resort)
    (re.compile(r"^[\s]*(\d+\.?\d*)[\s]*$"), "plain"),
]

# Keywords in table headers that suggest control type
HEADER_KEYWORDS = {
    "bicycle_parking": ["bicycle", "bike", "cycle"],
    "car_parking": ["parking", "car space", "vehicle", "garage"],
    "front_setback": ["front setback", "front boundary"],
    "side_setback": ["side setback", "side boundary"],
    "rear_setback": ["rear setback", "rear boundary"],
    "max_site_coverage": ["site coverage", "building coverage"],
    "landscaping_min": ["landscap", "soft surface", "pervious"],
    "deep_soil_min": ["deep soil"],
    "max_building_height": ["height", "storeys"],
    "floor_space_ratio": ["fsr", "floor space ratio"],
    "solar_access_hours": ["solar", "sunlight", "daylight"],
    "private_open_space": ["private open space", "pos", "private outdoor"],
    "communal_open_space_min": ["communal open space", "common open space"],
    "tree_canopy_min": ["tree canopy", "canopy cover"],
    "max_impervious_area": ["impervious"],
}

# Keywords in row headers that suggest dev type
DEV_TYPE_KEYWORDS = {
    "dwelling_house": ["dwelling house", "detached dwelling", "single dwelling"],
    "secondary_dwelling": ["secondary dwelling", "granny flat"],
    "dual_occupancy": ["dual occupancy", "semi-detached", "duplex"],
    "attached_dwelling": ["attached dwelling", "terrace", "townhouse"],
    "multi_dwelling_housing": ["multi dwelling", "villa", "townhouse development"],
    "residential_flat_building": ["residential flat", "rfb", "apartment", "flat building"],
    "shop_top_housing": ["shop top", "mixed use", "commercial/residential"],
    "boarding_house": ["boarding house"],
    "seniors_housing": ["seniors", "aged care", "over 55"],
    "group_home": ["group home"],
}


def parse_cell_value(cell: str) -> Optional[dict]:
    """Extract numeric value(s) from a table cell string.

    Returns dict with value_min, value_max, unit keys, or None if no number found.
    """
    if not cell or not cell.strip():
        return None

    text = cell.strip()

    # Skip non-numeric cells
    if not re.search(r"\d", text):
        return None

    for pattern, ptype in CELL_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue

        if ptype == "range":
            return {
                "value_min": float(match.group(1)),
                "value_max": float(match.group(2)),
                "unit": _detect_unit(text),
                "source_text": text,
            }
        elif ptype == "percent":
            return {
                "value_min": float(match.group(1)),
                "value_max": None,
                "unit": "%",
                "source_text": text,
            }
        elif ptype == "dimension":
            val = float(match.group(1))
            return {
                "value_min": val,
                "value_max": None,
                "unit": "m",
                "source_text": text,
            }
        else:
            return {
                "value_min": float(match.group(1)),
                "value_max": None,
                "unit": _detect_unit(text),
                "source_text": text,
            }

    return None


def _detect_unit(text: str) -> Optional[str]:
    """Detect unit from surrounding text."""
    t = text.lower()
    if "%" in t:
        return "%"
    if re.search(r"m(?:etre)?s?\b", t):
        return "m"
    if "storey" in t:
        return "storeys"
    if "space" in t or "per dwelling" in t or "per unit" in t:
        return "spaces/dwelling"
    if "m²" in t or "m2" in t or "sqm" in t:
        return "m2"
    return None


def classify_header(header: str) -> Optional[str]:
    """Map a table column header to a control_type."""
    h = header.lower().strip()
    for control_type, keywords in HEADER_KEYWORDS.items():
        for kw in keywords:
            if kw in h:
                return control_type
    return None


def classify_dev_type(row_header: str) -> Optional[str]:
    """Map a table row header to a dev_type."""
    h = row_header.lower().strip()
    for dev_type, keywords in DEV_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in h:
                return dev_type
    return None


# ---------------------------------------------------------------------------
# PDF table extraction
# ---------------------------------------------------------------------------

def extract_tables_from_pdf(pdf_path: str) -> list[dict]:
    """Extract all tables from a PDF and parse their numeric content.

    Returns list of dicts, each representing a parsed table with:
    - page: page number
    - headers: list of column header strings
    - rows: list of parsed row dicts
    - control_types: detected control types from headers
    """
    parsed_tables = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables() or []
            for tbl_idx, table_data in enumerate(tables):
                if not table_data or len(table_data) < 2:
                    continue

                parsed = _parse_table(table_data, page_num)
                if parsed and parsed["rows"]:
                    parsed_tables.append(parsed)

    return parsed_tables


def _parse_table(table_data: list[list], page_num: int) -> Optional[dict]:
    """Parse a pdfplumber table into structured control rows."""
    headers = [str(cell or "").strip() for cell in table_data[0]]

    # Check if any header matches a known control type
    col_types = {}
    for col_idx, header in enumerate(headers):
        ct = classify_header(header)
        if ct:
            col_types[col_idx] = ct

    if not col_types:
        return None

    rows = []
    for row_data in table_data[1:]:
        if not row_data:
            continue

        cells = [str(cell or "").strip() for cell in row_data]

        # First column is typically the dev type / category
        row_label = cells[0] if cells else ""
        dev_type = classify_dev_type(row_label)

        for col_idx, control_type in col_types.items():
            if col_idx >= len(cells):
                continue

            parsed = parse_cell_value(cells[col_idx])
            if parsed:
                rows.append({
                    "dev_type": dev_type,
                    "dev_type_raw": row_label,
                    "control_type": control_type,
                    "value_min": parsed["value_min"],
                    "value_max": parsed["value_max"],
                    "unit": parsed["unit"],
                    "source_text": parsed["source_text"],
                    "page": page_num,
                    "condition": _extract_condition(cells, col_idx, row_label),
                })

    return {
        "page": page_num,
        "headers": headers,
        "control_types": list(col_types.values()),
        "rows": rows,
    }


def _extract_condition(cells: list[str], value_col: int, row_label: str) -> Optional[str]:
    """Extract condition text from adjacent cells or row label qualifiers."""
    # Check for bedroom/size qualifiers in the row label
    qualifiers = re.findall(
        r"(\d+\s*(?:or\s+(?:more|less|fewer))?\s*bed(?:room)?s?|"
        r"studio|"
        r"(?:within|beyond|[<>≤≥])\s*\d+\s*m(?:\s+(?:of|from))?|"
        r"(?:zone\s+\w+))",
        row_label,
        re.IGNORECASE,
    )
    if qualifiers:
        return "; ".join(qualifiers)
    return None


# ---------------------------------------------------------------------------
# DB operations
# ---------------------------------------------------------------------------

def load_existing_controls(council: str, chapter_key: str) -> list[dict]:
    """Load current dcp_setback_controls rows for a specific chapter."""
    if not DATABASE_URL:
        return []

    sql = """
        SELECT id, dev_type, control_type, value_min, value_max, unit,
               condition, source_text, section_ref, needs_review
        FROM dcp_setback_controls
        WHERE lga = %s
          AND source_chapter_key = %s
          AND is_current = TRUE
        ORDER BY dev_type, control_type
    """

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (council, chapter_key))
            return [dict(row) for row in cur.fetchall()]
    finally:
        if conn:
            conn.close()


def load_flagged_chapters() -> list[dict]:
    """Find all chapters with control rows flagged needs_review."""
    if not DATABASE_URL:
        return []

    sql = """
        SELECT DISTINCT lga, source_chapter_key, review_reason,
               COUNT(*) as flagged_count
        FROM dcp_setback_controls
        WHERE needs_review = TRUE AND is_current = TRUE
              AND source_chapter_key IS NOT NULL
        GROUP BY lga, source_chapter_key, review_reason
        ORDER BY lga, source_chapter_key
    """

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]
    finally:
        if conn:
            conn.close()


def get_r2_pdf_path(council: str, chapter_key: str) -> Optional[str]:
    """Get the current R2 PDF path for a chapter."""
    if not DATABASE_URL:
        return None

    sql = """
        SELECT r2_current_path FROM dcp_chapter_registry
        WHERE council = %s AND chapter_key = %s
    """

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute(sql, (council, chapter_key))
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Diff engine
# ---------------------------------------------------------------------------

def diff_controls(existing: list[dict], extracted: list[dict]) -> dict:
    """Compare existing DB rows against newly extracted values.

    Returns dict with:
    - matched: rows where values match (no action needed)
    - changed: rows where values differ (needs human review)
    - new: extracted rows not found in existing (potential additions)
    - missing: existing rows not found in extraction (may have been removed)
    """
    matched = []
    changed = []
    new_rows = []
    missing = []

    # Build lookup from existing rows: (dev_type, control_type, condition) → row
    existing_lookup = {}
    for row in existing:
        key = (row["dev_type"], row["control_type"], row.get("condition"))
        existing_lookup[key] = row

    # Build lookup from extracted rows
    extracted_lookup = {}
    for row in extracted:
        if not row.get("dev_type"):
            continue
        key = (row["dev_type"], row["control_type"], row.get("condition"))
        extracted_lookup[key] = row

    # Compare
    for key, ext_row in extracted_lookup.items():
        if key in existing_lookup:
            db_row = existing_lookup[key]
            if _values_match(db_row, ext_row):
                matched.append({"db": db_row, "pdf": ext_row})
            else:
                changed.append({"db": db_row, "pdf": ext_row})
        else:
            new_rows.append(ext_row)

    for key, db_row in existing_lookup.items():
        if key not in extracted_lookup:
            missing.append(db_row)

    return {
        "matched": matched,
        "changed": changed,
        "new": new_rows,
        "missing": missing,
    }


def _values_match(db_row: dict, ext_row: dict) -> bool:
    """Check if numeric values match between DB and extracted row."""
    db_min = float(db_row["value_min"]) if db_row.get("value_min") is not None else None
    db_max = float(db_row["value_max"]) if db_row.get("value_max") is not None else None
    ext_min = ext_row.get("value_min")
    ext_max = ext_row.get("value_max")

    if db_min != ext_min:
        return False
    if db_max != ext_max:
        return False
    return True


# ---------------------------------------------------------------------------
# Review artifact output
# ---------------------------------------------------------------------------

def format_review(council: str, chapter_key: str, diff: dict,
                  extracted_tables: list[dict]) -> str:
    """Format a human-readable review artifact."""
    lines = [
        f"# Numeric Control Review: {council} / {chapter_key}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    # Summary
    lines.append("## Summary")
    lines.append(f"- Matched (no change): {len(diff['matched'])}")
    lines.append(f"- Changed (needs review): {len(diff['changed'])}")
    lines.append(f"- New (potential additions): {len(diff['new'])}")
    lines.append(f"- Missing from PDF (may be removed): {len(diff['missing'])}")
    lines.append("")

    # Tables found
    lines.append(f"## Tables extracted: {len(extracted_tables)}")
    for t in extracted_tables:
        lines.append(f"- Page {t['page']}: {', '.join(t['control_types'])} ({len(t['rows'])} values)")
    lines.append("")

    # Changed values — the critical section
    if diff["changed"]:
        lines.append("## CHANGED VALUES (review required)")
        lines.append("")
        for item in diff["changed"]:
            db = item["db"]
            pdf = item["pdf"]
            lines.append(f"### {db['dev_type']} / {db['control_type']}")
            lines.append(f"  DB:  min={db.get('value_min')} max={db.get('value_max')} unit={db.get('unit')}")
            lines.append(f"  PDF: min={pdf.get('value_min')} max={pdf.get('value_max')} unit={pdf.get('unit')}")
            lines.append(f"  PDF source: \"{pdf.get('source_text', '')}\"")
            if db.get("condition"):
                lines.append(f"  Condition: {db['condition']}")
            lines.append(f"  DB row ID: {db['id']}")
            lines.append("")

    # New rows
    if diff["new"]:
        lines.append("## NEW VALUES (potential additions)")
        lines.append("")
        for row in diff["new"]:
            lines.append(f"- {row.get('dev_type', '?')} / {row['control_type']}: "
                         f"min={row.get('value_min')} max={row.get('value_max')} "
                         f"unit={row.get('unit')} — \"{row.get('source_text', '')}\"")
        lines.append("")

    # Missing rows
    if diff["missing"]:
        lines.append("## MISSING FROM PDF (may have been removed)")
        lines.append("")
        for row in diff["missing"]:
            lines.append(f"- {row['dev_type']} / {row['control_type']}: "
                         f"min={row.get('value_min')} max={row.get('value_max')} "
                         f"(DB row ID: {row['id']})")
        lines.append("")

    # Matched (collapsed)
    if diff["matched"]:
        lines.append(f"## Matched ({len(diff['matched'])} rows — no action needed)")
        for item in diff["matched"]:
            db = item["db"]
            lines.append(f"- {db['dev_type']} / {db['control_type']}: "
                         f"min={db.get('value_min')} max={db.get('value_max')}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Review numeric controls against PDF tables")
    parser.add_argument("--council", help="Council slug (e.g. canterbury_bankstown)")
    parser.add_argument("--chapter", help="Chapter key (e.g. ch3-2-parking)")
    parser.add_argument("--pdf", help="Local PDF path (skips R2 download)")
    parser.add_argument("--flagged", action="store_true",
                        help="List all chapters with flagged control rows")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    args = parser.parse_args()

    if args.flagged:
        flagged = load_flagged_chapters()
        if not flagged:
            print("No chapters with flagged control rows.")
            return 0
        print(f"\n{'='*70}")
        print(f"Chapters with flagged control rows: {len(flagged)}")
        print(f"{'='*70}")
        for f in flagged:
            print(f"  {f['lga']} / {f['source_chapter_key']}: "
                  f"{f['flagged_count']} rows ({f['review_reason']})")
        return 0

    if args.pdf:
        # Local PDF mode — extract tables only, no DB comparison
        tables = extract_tables_from_pdf(args.pdf)
        print(f"\nExtracted {len(tables)} tables with numeric content:")
        for t in tables:
            print(f"\n  Page {t['page']}: {', '.join(t['control_types'])}")
            print(f"  Headers: {t['headers']}")
            for row in t["rows"]:
                print(f"    {row.get('dev_type', '?'):30s} {row['control_type']:25s} "
                      f"min={row.get('value_min')} max={row.get('value_max')} "
                      f"unit={row.get('unit')} — \"{row.get('source_text', '')}\"")
        return 0

    if not args.council or not args.chapter:
        parser.error("--council and --chapter are required (or use --pdf or --flagged)")

    # Full review: load existing, extract from PDF, diff
    print(f"Reviewing: {args.council} / {args.chapter}")

    # Load existing control rows
    existing = load_existing_controls(args.council, args.chapter)
    print(f"  Existing DB rows: {len(existing)}")

    # Get PDF path from R2
    pdf_path = args.pdf
    if not pdf_path:
        r2_path = get_r2_pdf_path(args.council, args.chapter)
        if not r2_path:
            print(f"  ERROR: No R2 path found for {args.council}/{args.chapter}")
            return 1
        # Download from R2 to temp file
        pdf_path = _download_from_r2(r2_path)
        if not pdf_path:
            print(f"  ERROR: Failed to download {r2_path} from R2")
            return 1

    # Extract tables
    tables = extract_tables_from_pdf(pdf_path)
    all_extracted = []
    for t in tables:
        all_extracted.extend(t["rows"])
    print(f"  Tables found: {len(tables)}, values extracted: {len(all_extracted)}")

    # Diff
    result = diff_controls(existing, all_extracted)

    # Format review
    review_text = format_review(args.council, args.chapter, result, tables)

    if args.output:
        Path(args.output).write_text(review_text, encoding="utf-8")
        print(f"  Review written to: {args.output}")
    else:
        print(f"\n{review_text}")

    # Exit code: 0 = no changes, 2 = changes found
    if result["changed"] or result["new"] or result["missing"]:
        return 2
    return 0


def _download_from_r2(r2_path: str) -> Optional[str]:
    """Download a PDF from R2 to a temp file."""
    try:
        import boto3
        import tempfile

        r2_account_id = os.environ.get("R2_ACCOUNT_ID")
        r2_access_key = os.environ.get("R2_ACCESS_KEY_ID")
        r2_secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")
        r2_bucket = os.environ.get("R2_BUCKET_NAME")

        if not all([r2_account_id, r2_access_key, r2_secret_key, r2_bucket]):
            print("  WARNING: R2 credentials not set — cannot download PDF")
            return None

        s3 = boto3.client(
            "s3",
            endpoint_url=f"https://{r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=r2_access_key,
            aws_secret_access_key=r2_secret_key,
        )

        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        s3.download_file(r2_bucket, r2_path, tmp.name)
        return tmp.name

    except Exception as e:
        print(f"  R2 download error: {e}")
        return None


if __name__ == "__main__":
    sys.exit(main())
