#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mistral OCR 3 setback extractor for DCP chapters with garbled/table text.

Usage:
    python scripts/mistral_ocr_setback_extract.py --council leichhardt --dry-run
    python scripts/mistral_ocr_setback_extract.py --council ashfield --dry-run
    python scripts/mistral_ocr_setback_extract.py --council leichhardt
    python scripts/mistral_ocr_setback_extract.py --council ashfield
    python scripts/mistral_ocr_setback_extract.py --council all
"""
import os, sys, re, argparse, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral

load_dotenv()

from enrichment.extractors.numeric_extractor import NumericExtractor

# ---------------------------------------------------------------------------
# Target chapters — public R2 URLs + page hints for context
# ---------------------------------------------------------------------------
TARGETS = {
    'leichhardt': {
        'chapters': [
            {
                'chapter_key': 'part-c-s3-residential',
                'url': 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/source-pdfs/dcps/leichhardt/v1.1-2026-03-02/part-c-s3-residential.pdf',
                'pages': None,  # all 34 pages
                'section_hint': 'Secondary Dwellings',
            },
        ],
        'dev_type': 'secondary_dwelling',
        'applicability': 'universal_residential',  # not SD-specific in Leichhardt DCP
    },
    'ashfield': {
        'chapters': [
            {
                'chapter_key': 'chapter-f-dev-category',
                'url': 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/source-pdfs/dcps/ashfield/v1.1-2026-03-02/chapter-f-dev-category.pdf',
                'pages': '1-40',  # SD section is in F-Part1, ~pages 14-30 but process first 40 to be safe
                'section_hint': 'Secondary Dwellings',
            },
        ],
        'dev_type': 'secondary_dwelling',
        'applicability': 'secondary_dwelling_specific',
    },
}

# ---------------------------------------------------------------------------
# Control type mapping — same logic as other extractors
# ---------------------------------------------------------------------------
CONTROL_TYPE_MAP = {
    ('setback', 'front'):    'front_setback',
    ('setback', 'rear'):     'rear_setback',
    ('setback', 'side'):     'side_setback',
    ('setback', 'street'):   'front_setback',
    ('setback', 'boundary'): 'side_setback',
    ('separation', None):    'separation_from_dwelling',
    ('separation_min', None): 'separation_from_dwelling',
    ('height', None):        'max_height',
    ('height', 'max'):       'max_height',
    ('site_coverage', None): 'site_coverage',
    ('landscaping', None):   'landscaping',
}

SD_SECTION_RE = re.compile(
    r'secondary\s+dwell',
    re.IGNORECASE,
)

NUMERIC_SETBACK_TYPES = {'setback', 'separation', 'separation_min', 'height', 'site_coverage', 'landscaping'}

CONTROL_VERB_RE = re.compile(
    r'\b(must|shall|is\s+to|are\s+to|minimum|maximum|not\s+exceed|no\s+more\s+than|at\s+least)\b',
    re.IGNORECASE,
)

OBJECTIVE_SIGNAL_RE = re.compile(
    r'\b(objective|intent|purpose|aim|goal|ensure|encourage|promote|protect|maintain|support)\b',
    re.IGNORECASE,
)


def map_control_type(value_type: str, context: str | None) -> str | None:
    key = (value_type, context)
    if key in CONTROL_TYPE_MAP:
        return CONTROL_TYPE_MAP[key]
    # Try without context
    key2 = (value_type, None)
    if key2 in CONTROL_TYPE_MAP:
        return CONTROL_TYPE_MAP[key2]
    return None


def is_likely_objective(text: str) -> bool:
    """Heuristic: more objective signals than control verbs → likely narrative."""
    obj_hits = len(OBJECTIVE_SIGNAL_RE.findall(text[:500]))
    ctrl_hits = len(CONTROL_VERB_RE.findall(text[:500]))
    return obj_hits > ctrl_hits and ctrl_hits == 0


def ocr_pdf(client: Mistral, url: str, pages: str | None) -> list[dict]:
    """Run Mistral OCR on a PDF URL. Returns list of {page_num, markdown} dicts."""
    kwargs = {
        'model': 'mistral-ocr-latest',
        'document': {
            'type': 'document_url',
            'document_url': url,
        },
        'include_image_base64': False,
    }
    if pages:
        # Mistral OCR accepts pages as list of ints
        start, end = pages.split('-')
        kwargs['pages'] = list(range(int(start) - 1, int(end)))  # 0-indexed

    response = client.ocr.process(**kwargs)
    return response.pages


def extract_from_ocr_pages(pages: list, section_hint: str) -> list[dict]:
    """
    Find secondary dwelling section in OCR output and extract setback controls.
    Returns list of candidate dicts.
    """
    extractor = NumericExtractor()
    candidates = []

    # Concatenate pages into one text with page markers
    full_text = '\n'.join(f'[PAGE {p.index + 1}]\n{p.markdown}' for p in pages)

    # Find the secondary dwelling section
    match = SD_SECTION_RE.search(full_text)
    if not match:
        print(f"  WARNING: '{section_hint}' section not found in OCR output")
        # Try processing the whole text anyway
        section_text = full_text
        section_start_page = 1
    else:
        section_text = full_text[match.start():]
        # Determine start page from preceding [PAGE N] marker
        preceding = full_text[:match.start()]
        page_markers = re.findall(r'\[PAGE (\d+)\]', preceding)
        section_start_page = int(page_markers[-1]) if page_markers else 1
        print(f"  Found '{section_hint}' section at page ~{section_start_page}, offset {match.start()}")

    # Split into paragraphs / clauses for per-clause analysis
    # Split on double newlines or heading patterns
    clauses = re.split(r'\n{2,}|(?=#{1,4}\s)', section_text)

    for clause in clauses:
        clause = clause.strip()
        if not clause or len(clause) < 15:
            continue
        if is_likely_objective(clause):
            continue

        result = extractor.extract(clause)
        values = [v for v in result.get('values', [])
                  if v.get('value_type') in NUMERIC_SETBACK_TYPES]
        if not values:
            continue

        # Skip if no control verb present
        if not CONTROL_VERB_RE.search(clause[:400]):
            continue

        for v in values:
            ct = map_control_type(v.get('value_type'), v.get('context'))
            if ct is None:
                ct = 'unknown'

            candidates.append({
                'control_type': ct,
                'value_min': v.get('value_exact') or v.get('value_min'),
                'value_max': v.get('value_max'),
                'unit': v.get('unit', 'm'),
                'condition': v.get('condition'),
                'source_text': clause[:500],
                'raw_value': v,
            })

    return candidates


def insert_rows(conn, lga: str, dev_type: str, applicability: str,
                section_ref: str, rows: list[dict], dry_run: bool) -> int:
    cur = conn.cursor(cursor_factory=RealDictCursor)
    inserted = 0

    for row in rows:
        # Check for duplicate
        cur.execute("""
            SELECT id FROM dcp_setback_controls
            WHERE lga = %s AND dev_type = %s AND control_type = %s
              AND COALESCE(condition, '') = COALESCE(%s, '')
              AND COALESCE(value_min::text, '') = COALESCE(%s::text, '')
              AND COALESCE(value_max::text, '') = COALESCE(%s::text, '')
        """, (lga, dev_type, row['control_type'],
              row['condition'], row['value_min'], row['value_max']))
        if cur.fetchone():
            print(f"    SKIP (dup): {row['control_type']} {row['value_min']}{row['unit']}")
            continue

        if dry_run:
            print(f"    DRY-RUN INSERT: lga={lga} control={row['control_type']} "
                  f"min={row['value_min']} max={row['value_max']} unit={row['unit']} "
                  f"cond={row['condition']}")
            print(f"      text: {row['source_text'][:120]}")
        else:
            cur.execute("""
                INSERT INTO dcp_setback_controls
                  (lga, dev_type, control_type, value_min, value_max, unit,
                   condition, applicability, source_text, section_ref)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (lga, dev_type, row['control_type'],
                  row['value_min'], row['value_max'], row['unit'],
                  row['condition'], applicability,
                  row['source_text'], section_ref))
            inserted += 1
            print(f"    INSERTED: {row['control_type']} {row['value_min']}{row['unit']}"
                  f" (cond={row['condition']})")

    if not dry_run:
        conn.commit()
    return inserted


def run_council(council: str, target: dict, dry_run: bool,
                client: Mistral, conn) -> None:
    lga = council
    print(f"\n{'='*60}")
    print(f"Council: {council.upper()}  dev_type={target['dev_type']}  dry_run={dry_run}")
    print(f"{'='*60}")

    for chapter in target['chapters']:
        print(f"\nChapter: {chapter['chapter_key']}  pages={chapter['pages'] or 'all'}")
        print(f"  OCR-ing: {chapter['url'][:80]}...")

        try:
            pages = ocr_pdf(client, chapter['url'], chapter['pages'])
        except Exception as e:
            print(f"  ERROR during OCR: {e}")
            continue

        print(f"  OCR complete: {len(pages)} pages returned")

        candidates = extract_from_ocr_pages(pages, chapter['section_hint'])
        print(f"  Candidates found: {len(candidates)}")

        if not candidates:
            print("  No setback controls extracted.")
            continue

        # Show all candidates for review
        for i, c in enumerate(candidates):
            print(f"\n  [{i+1}] control={c['control_type']}  min={c['value_min']}  "
                  f"max={c['value_max']}  unit={c['unit']}  cond={c['condition']}")
            print(f"       text: {c['source_text'][:200]}")

        n = insert_rows(conn, lga, target['dev_type'], target['applicability'],
                        chapter['chapter_key'], candidates, dry_run)
        print(f"\n  {'DRY-RUN' if dry_run else 'Inserted'}: {n} rows for {chapter['chapter_key']}")


def main():
    parser = argparse.ArgumentParser(description='Mistral OCR setback extractor')
    parser.add_argument('--council', required=True,
                        help='leichhardt | ashfield | all')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print candidates without inserting')
    args = parser.parse_args()

    api_key = os.environ.get('MISTRAL_API_KEY')
    if not api_key:
        print("ERROR: MISTRAL_API_KEY not set in environment")
        sys.exit(1)

    client = Mistral(api_key=api_key)
    conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])

    councils = list(TARGETS.keys()) if args.council == 'all' else [args.council]
    for council in councils:
        if council not in TARGETS:
            print(f"Unknown council: {council}. Options: {list(TARGETS.keys())}")
            continue
        run_council(council, TARGETS[council], args.dry_run, client, conn)

    conn.close()
    print("\nDone.")


if __name__ == '__main__':
    main()
