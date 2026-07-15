#!/usr/bin/env python3
"""
Extract secondary dwelling setback controls — dev_type_organized DCPs.

Councils: Ku-ring-gai (part_4_1_secondary_dwellings), Ashfield (needs OCR re-parse first).

Strategy: The DCP has a dedicated secondary dwelling chapter. We query
provisions from that chapter key, run NumericExtractor on each, and
write structured rows to dcp_setback_controls with
applicability = 'secondary_dwelling_specific'.

Usage:
    python enrichment/extractors/extract_secondary_setbacks_dev_type_organized.py \
        --council ku_ring_gai \
        --chapter-key part_4_1_secondary_dwellings \
        --dry-run

    # Ashfield: after Mistral OCR 3 re-parse, pass clean text file instead of DB text
    python enrichment/extractors/extract_secondary_setbacks_dev_type_organized.py \
        --council ashfield \
        --chapter-key "chapter_f__f2_secondary_dwellings" \
        --clean-text-file data/ashfield_f2_clean.md
"""

import os
import sys
import json
import argparse
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from enrichment.extractors.numeric_extractor import NumericExtractor


# ---------------------------------------------------------------------------
# Control type mapping — map extractor value_type + context → our control_type
# ---------------------------------------------------------------------------

def map_control_type(value_type: str, context: Optional[str], unit: Optional[str]) -> Optional[str]:
    """Map NumericExtractor output to dcp_setback_controls.control_type."""
    if value_type == 'setback':
        ctx = (context or '').lower()
        if 'rear' in ctx or 'back' in ctx:
            return 'rear_setback'
        if 'side' in ctx or 'lateral' in ctx:
            return 'side_setback'
        if 'front' in ctx or 'street' in ctx or 'primary' in ctx:
            return 'front_setback'
        if 'principal' in ctx or 'from dwelling' in ctx:
            return 'separation_from_dwelling'
        return None  # No context — skip; ambiguous values cause more harm than good
    if value_type == 'separation':
        return 'separation_from_dwelling'
    if value_type == 'height':
        if unit == 'storeys':
            return 'max_height'
        return 'max_height'
    if value_type in ('fsr', 'floor_space_ratio'):
        return 'max_floor_area'
    if value_type == 'site_coverage':
        return 'max_site_coverage'
    if value_type == 'landscaping':
        return 'landscaping_min'
    if value_type == 'lot_area':
        return None  # Not a design control — skip
    return None


def make_source_snippet(text: str, max_len: int = 250) -> str:
    """Return first max_len chars of text, stripped."""
    t = ' '.join(text.split())  # normalise whitespace
    return t[:max_len] if len(t) > max_len else t


def get_connection():
    return psycopg2.connect(os.environ['SUPABASE_DB_URL'])


def fetch_chapter_provisions(conn, council: str, chapter_key: str) -> list[dict]:
    """Fetch all provisions matching the council + chapter key pattern."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, ref_number, provision_text, source_chapter_key, v2_topic
            FROM regulatory_provisions
            WHERE source_council = %s
              AND is_current = TRUE
              AND source_chapter_key ILIKE %s
            ORDER BY id
            """,
            (council, f'%{chapter_key}%'),
        )
        return [dict(r) for r in cur.fetchall()]


def insert_controls(conn, rows: list[dict], dry_run: bool) -> int:
    """Insert extracted controls, skip duplicates on (provision_id, control_type, condition)."""
    if not rows:
        return 0
    if dry_run:
        for r in rows:
            print(f"  [DRY-RUN] {r['lga']} | {r['control_type']} | "
                  f"min={r.get('value_min')} max={r.get('value_max')} {r.get('unit')} | "
                  f"{r.get('applicability')} | {r.get('section_ref')}")
        return len(rows)

    inserted = 0
    with conn.cursor() as cur:
        for r in rows:
            # Skip if (provision_id, control_type, condition) already exists
            cur.execute(
                """
                SELECT 1 FROM dcp_setback_controls
                WHERE provision_id = %s AND control_type = %s
                  AND COALESCE(condition, '') = COALESCE(%s, '')
                  AND COALESCE(value_min::text, '') = COALESCE(%s::text, '')
                  AND COALESCE(value_max::text, '') = COALESCE(%s::text, '')
                """,
                (r.get('provision_id'), r['control_type'], r.get('condition'),
                 r.get('value_min'), r.get('value_max')),
            )
            if cur.fetchone():
                continue
            cur.execute(
                """
                INSERT INTO dcp_setback_controls
                  (provision_id, lga, dev_type, control_type,
                   value_min, value_max, unit, condition,
                   applicability, source_text, section_ref)
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    r.get('provision_id'),
                    r['lga'],
                    r.get('dev_type', 'secondary_dwelling'),
                    r['control_type'],
                    r.get('value_min'),
                    r.get('value_max'),
                    r.get('unit'),
                    r.get('condition'),
                    r['applicability'],
                    r.get('source_text'),
                    r.get('section_ref'),
                ),
            )
            inserted += 1
    conn.commit()
    return inserted


def extract_from_provisions(
    provisions: list[dict],
    lga: str,
    applicability: str,
    extractor: NumericExtractor,
) -> list[dict]:
    """Run extraction on a list of provisions and return rows to insert."""
    rows = []
    for prov in provisions:
        text = prov.get('provision_text') or ''
        if not text.strip():
            continue

        result = extractor.extract(text)
        if not result['has_numeric']:
            continue

        for v in result['values']:
            ctrl = map_control_type(
                v.get('value_type', ''),
                v.get('context'),
                v.get('unit'),
            )
            if ctrl is None:
                continue

            # For setbacks: we need at least one of min/max/exact
            value_min = v.get('value_min') or (v.get('value_exact') if 'min' in ctrl or 'setback' in ctrl or 'separation' in ctrl else None)
            value_max = v.get('value_max') or (v.get('value_exact') if 'max' in ctrl or 'height' in ctrl or 'coverage' in ctrl or 'area_max' in ctrl else None)

            if value_min is None and value_max is None:
                continue

            rows.append({
                'provision_id': prov['id'],
                'lga': lga,
                'dev_type': 'secondary_dwelling',
                'control_type': ctrl,
                'value_min': value_min,
                'value_max': value_max,
                'unit': v.get('unit'),
                'condition': None,
                'applicability': applicability,
                'source_text': make_source_snippet(text),
                'section_ref': prov.get('ref_number'),
            })

    return rows


def extract_from_clean_text(
    clean_text: str,
    lga: str,
    extractor: NumericExtractor,
) -> list[dict]:
    """Extract from a clean text string (post-OCR re-parse) with no DB provision_id."""
    result = extractor.extract(clean_text)
    rows = []
    for v in result['values']:
        ctrl = map_control_type(v.get('value_type', ''), v.get('context'), v.get('unit'))
        if ctrl is None:
            continue

        value_min = v.get('value_min') or (v.get('value_exact') if 'min' in ctrl or 'setback' in ctrl or 'separation' in ctrl else None)
        value_max = v.get('value_max') or (v.get('value_exact') if 'max' in ctrl or 'height' in ctrl or 'coverage' in ctrl or 'area_max' in ctrl else None)

        if value_min is None and value_max is None:
            continue

        rows.append({
            'provision_id': None,
            'lga': lga,
            'dev_type': 'secondary_dwelling',
            'control_type': ctrl,
            'value_min': value_min,
            'value_max': value_max,
            'unit': v.get('unit'),
            'condition': None,
            'applicability': 'secondary_dwelling_specific',
            'source_text': make_source_snippet(clean_text),
            'section_ref': f'{lga}_secondary_dwelling_chapter',
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description='Extract secondary dwelling setbacks — dev_type_organized DCPs')
    parser.add_argument('--council', required=True, help='e.g. ku_ring_gai')
    parser.add_argument('--chapter-key', required=True, help='Substring matched against source_chapter_key')
    parser.add_argument('--clean-text-file', help='Path to clean text file (post-OCR re-parse, bypasses DB text)')
    parser.add_argument('--dry-run', action='store_true', help='Print rows without inserting')
    args = parser.parse_args()

    extractor = NumericExtractor()
    conn = get_connection()

    try:
        if args.clean_text_file:
            with open(args.clean_text_file, 'r', encoding='utf-8') as f:
                clean_text = f.read()
            print(f"Loaded clean text ({len(clean_text)} chars) from {args.clean_text_file}")
            rows = extract_from_clean_text(clean_text, args.council, extractor)
        else:
            provisions = fetch_chapter_provisions(conn, args.council, args.chapter_key)
            print(f"Found {len(provisions)} provisions for {args.council} / {args.chapter_key}")
            if not provisions:
                print("No provisions found. Check council name and chapter key.")
                return
            rows = extract_from_provisions(provisions, args.council, 'secondary_dwelling_specific', extractor)

        print(f"Extracted {len(rows)} control rows")
        n = insert_controls(conn, rows, args.dry_run)
        print(f"{'Would insert' if args.dry_run else 'Inserted'}: {n} rows")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
