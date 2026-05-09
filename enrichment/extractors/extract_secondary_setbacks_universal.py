#!/usr/bin/env python3
"""
Extract secondary dwelling setback controls — topic_universal DCPs.

Councils: Leichhardt, Woollahra, (Waverley Part B).

Strategy:
  - In topic_universal DCPs, there is no dedicated secondary dwelling chapter.
  - Universal residential/building_form/setback/height provisions apply to all dev types.
  - Query by v2_topic IN (...) for the council — NO v2_applicable_dev_types filter.
  - Write with applicability = 'universal_residential'.
  - UI must label these as "universal residential controls — applies to secondary dwellings".

Topics queried:
  setbacks, building_form, height, residential, site_coverage, landscaping

Usage:
    python enrichment/extractors/extract_secondary_setbacks_universal.py \
        --council leichhardt \
        --dry-run

    python enrichment/extractors/extract_secondary_setbacks_universal.py \
        --council woollahra \
        --dry-run

    # Waverley Part B only (skip Part C which is zone-specific)
    python enrichment/extractors/extract_secondary_setbacks_universal.py \
        --council waverley \
        --chapter-prefix "B" \
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


UNIVERSAL_TOPICS = ('setbacks', 'building_form', 'height', 'residential', 'site_coverage', 'landscaping')


def map_control_type(value_type: str, context: Optional[str], unit: Optional[str]) -> Optional[str]:
    if value_type == 'setback':
        ctx = (context or '').lower()
        if 'rear' in ctx or 'back' in ctx:
            return 'rear_setback'
        if 'side' in ctx or 'lateral' in ctx:
            return 'side_setback'
        if 'front' in ctx or 'street' in ctx or 'primary' in ctx:
            return 'front_setback'
        if 'principal' in ctx or 'separation' in ctx:
            return 'separation_from_dwelling'
        return None  # No context — skip ambiguous setbacks for universal type
    if value_type == 'separation':
        return 'separation_from_dwelling'
    if value_type == 'height':
        if unit == 'storeys':
            return 'height_storeys_max'
        return 'height_max'
    if value_type in ('fsr', 'floor_space_ratio'):
        return 'floor_area_max'
    if value_type == 'site_coverage':
        return 'site_coverage_max'
    if value_type == 'landscaping':
        return 'landscaping_min'
    return None


def make_source_snippet(text: str, max_len: int = 250) -> str:
    t = ' '.join(text.split())
    return t[:max_len] if len(t) > max_len else t


def get_connection():
    return psycopg2.connect(os.environ['SUPABASE_DB_URL'])


def fetch_universal_provisions(
    conn,
    council: str,
    topics: tuple[str, ...],
    chapter_prefix: Optional[str],
) -> list[dict]:
    """Fetch provisions by topic — no dev_type filter (universal chapters)."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        base_sql = """
            SELECT id, ref_number, provision_text, source_chapter_key, v2_topic
            FROM regulatory_provisions
            WHERE source_council = %s
              AND is_current = TRUE
              AND v2_topic = ANY(%s)
              AND provision_text IS NOT NULL
              AND length(provision_text) > 30
        """
        params: list = [council, list(topics)]

        if chapter_prefix:
            base_sql += " AND source_chapter_key ILIKE %s"
            params.append(f'{chapter_prefix}%')

        base_sql += " ORDER BY v2_topic, id"
        cur.execute(base_sql, params)
        return [dict(r) for r in cur.fetchall()]


def extract_provision(
    prov: dict,
    lga: str,
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
            'applicability': 'universal_residential',
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
                  f"universal | {r.get('section_ref')}")
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
    parser = argparse.ArgumentParser(description='Extract secondary dwelling setbacks — topic_universal DCPs')
    parser.add_argument('--council', required=True, help='e.g. leichhardt, woollahra')
    parser.add_argument('--chapter-prefix', help='Restrict to chapters starting with this prefix (e.g. "B" for Waverley Part B)')
    parser.add_argument('--topics', nargs='+', default=list(UNIVERSAL_TOPICS),
                        help='v2_topic values to include (default: setbacks building_form height residential site_coverage landscaping)')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    extractor = NumericExtractor()
    conn = get_connection()

    try:
        provisions = fetch_universal_provisions(conn, args.council, tuple(args.topics), args.chapter_prefix)
        print(f"Found {len(provisions)} provisions for {args.council} in topics {args.topics}")

        if not provisions:
            print("No provisions found. Check council name and topic values.")
            return

        all_rows: list[dict] = []
        for p in provisions:
            all_rows.extend(extract_provision(p, args.council, extractor))

        # Deduplicate on (control_type, value_min, value_max) — keep first occurrence
        seen: set[tuple] = set()
        deduped: list[dict] = []
        for r in all_rows:
            key = (r['control_type'], r.get('value_min'), r.get('value_max'), r.get('unit'))
            if key not in seen:
                seen.add(key)
                deduped.append(r)

        print(f"Extracted {len(deduped)} unique control rows (from {len(all_rows)} total, after dedup)")
        n = insert_controls(conn, deduped, args.dry_run)
        print(f"{'Would insert' if args.dry_run else 'Inserted'}: {n} rows")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
