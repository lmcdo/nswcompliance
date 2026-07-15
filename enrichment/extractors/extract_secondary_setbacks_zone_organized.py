#!/usr/bin/env python3
"""
Extract secondary dwelling setback controls — zone_organized DCPs.

Councils: Marrickville, City of Sydney, Waverley (partial).

Strategy:
  - Query the dedicated secondary dwelling provision (e.g. Marrickville C11)
  - Also query the referenced general dwelling provision to resolve cross-references
    (e.g. Marrickville C10iii which C11 defers to for rear setback)
  - Run NumericExtractor on both; prefer secondary-dwelling-specific row
  - Write with applicability = 'secondary_dwelling_specific'

Usage:
    # Marrickville: C11 is the secondary dwelling provision; C10 is the general dwelling ref
    python enrichment/extractors/extract_secondary_setbacks_zone_organized.py \
        --council marrickville \
        --secondary-ref "Marrickville_DCP_2011__part4_s1_low_density__O14_controls_C11" \
        --general-ref "Marrickville_DCP_2011__part4_s1_low_density__O14_controls_C10" \
        --dry-run

    # City of Sydney: Section 4 secondary dwelling provisions
    python enrichment/extractors/extract_secondary_setbacks_zone_organized.py \
        --council city_of_sydney \
        --secondary-chapter "section_4" \
        --secondary-dev-type-filter "secondary dwelling" \
        --dry-run
"""

import os
import sys
import argparse
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from enrichment.extractors.numeric_extractor import NumericExtractor


def map_control_type(value_type: str, context: Optional[str], unit: Optional[str]) -> Optional[str]:
    if value_type == 'setback':
        ctx = (context or '').lower()
        if 'rear' in ctx or 'back' in ctx:
            return 'rear_setback'
        if 'side' in ctx or 'lateral' in ctx:
            return 'side_setback'
        if 'front' in ctx or 'street' in ctx or 'primary' in ctx:
            return 'front_setback'
        if 'principal' in ctx or 'from dwelling' in ctx or 'separation' in ctx:
            return 'separation_from_dwelling'
        return None  # Context-free setback: don't guess for zone_organized
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
    return None


def make_source_snippet(text: str, max_len: int = 250) -> str:
    t = ' '.join(text.split())
    return t[:max_len] if len(t) > max_len else t


def get_connection():
    return psycopg2.connect(os.environ['SUPABASE_DB_URL'])


def fetch_by_ref(conn, ref_number: str) -> Optional[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id, ref_number, provision_text FROM regulatory_provisions "
            "WHERE ref_number = %s AND is_current = TRUE",
            (ref_number,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def fetch_by_chapter(conn, council: str, chapter_key: str, dev_type_filter: Optional[str] = None) -> list[dict]:
    """Fetch provisions from a chapter, optionally filtered by dev type array."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if dev_type_filter:
            cur.execute(
                """
                SELECT id, ref_number, provision_text
                FROM regulatory_provisions
                WHERE source_council = %s
                  AND is_current = TRUE
                  AND source_chapter_key ILIKE %s
                  AND v2_applicable_dev_types @> %s::text[]
                ORDER BY id
                """,
                (council, f'%{chapter_key}%', [dev_type_filter]),
            )
        else:
            cur.execute(
                """
                SELECT id, ref_number, provision_text
                FROM regulatory_provisions
                WHERE source_council = %s
                  AND is_current = TRUE
                  AND source_chapter_key ILIKE %s
                ORDER BY id
                """,
                (council, f'%{chapter_key}%'),
            )
        return [dict(r) for r in cur.fetchall()]


def extract_provision(
    prov: dict,
    lga: str,
    applicability: str,
    extractor: NumericExtractor,
) -> list[dict]:
    text = prov.get('provision_text') or ''
    if not text.strip():
        return []

    result = extractor.extract(text)
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


def insert_controls(conn, rows: list[dict], dry_run: bool) -> int:
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
            cur.execute(
                "SELECT 1 FROM dcp_setback_controls "
                "WHERE provision_id = %s AND control_type = %s "
                "AND COALESCE(condition, '') = COALESCE(%s, '') "
                "AND COALESCE(value_min::text, '') = COALESCE(%s::text, '') "
                "AND COALESCE(value_max::text, '') = COALESCE(%s::text, '')",
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    r.get('provision_id'), r['lga'], r.get('dev_type', 'secondary_dwelling'),
                    r['control_type'], r.get('value_min'), r.get('value_max'),
                    r.get('unit'), r.get('condition'), r['applicability'],
                    r.get('source_text'), r.get('section_ref'),
                ),
            )
            inserted += 1
    conn.commit()
    return inserted


def main():
    parser = argparse.ArgumentParser(description='Extract secondary dwelling setbacks — zone_organized DCPs')
    parser.add_argument('--council', required=True)
    # Mode A: specific ref numbers (Marrickville C11 + C10 cross-ref)
    parser.add_argument('--secondary-ref', help='ref_number of the secondary dwelling provision (e.g. C11)')
    parser.add_argument('--general-ref', help='ref_number of the general dwelling provision to cross-reference')
    # Mode B: chapter key (City of Sydney section_4)
    parser.add_argument('--secondary-chapter', help='Chapter key substring for secondary dwelling provisions')
    parser.add_argument('--secondary-dev-type-filter', help='v2_applicable_dev_types filter string (optional)')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    extractor = NumericExtractor()
    conn = get_connection()

    try:
        all_rows: list[dict] = []

        if args.secondary_ref:
            # Mode A: ref-based lookup (Marrickville)
            sec_prov = fetch_by_ref(conn, args.secondary_ref)
            if not sec_prov:
                print(f"Provision not found: {args.secondary_ref}")
                return
            print(f"Secondary dwelling provision: {sec_prov['ref_number']} ({len(sec_prov['provision_text'] or '')} chars)")
            all_rows.extend(extract_provision(sec_prov, args.council, 'secondary_dwelling_specific', extractor))

            if args.general_ref:
                gen_prov = fetch_by_ref(conn, args.general_ref)
                if gen_prov:
                    print(f"General dwelling provision (cross-ref): {gen_prov['ref_number']}")
                    # Mark as secondary_dwelling_specific since C11 explicitly defers to C10
                    all_rows.extend(extract_provision(gen_prov, args.council, 'secondary_dwelling_specific', extractor))

        elif args.secondary_chapter:
            # Mode B: chapter-based lookup (City of Sydney)
            provisions = fetch_by_chapter(conn, args.council, args.secondary_chapter, args.secondary_dev_type_filter)
            print(f"Found {len(provisions)} provisions in {args.secondary_chapter}")
            for p in provisions:
                all_rows.extend(extract_provision(p, args.council, 'secondary_dwelling_specific', extractor))
        else:
            parser.error('Provide either --secondary-ref or --secondary-chapter')

        # Deduplicate by control_type (keep first — most specific)
        seen = set()
        deduped = []
        for r in all_rows:
            key = (r['control_type'], str(r.get('value_min')), str(r.get('value_max')))
            if key not in seen:
                seen.add(key)
                deduped.append(r)

        print(f"Extracted {len(deduped)} control rows (after dedup)")
        n = insert_controls(conn, deduped, args.dry_run)
        print(f"{'Would insert' if args.dry_run else 'Inserted'}: {n} rows")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
