#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Systematic OCR extraction of residential setback controls for all 6 Tier 1 councils.
Targets: dwelling_house + secondary_dwelling controls (front, side, rear, height, site_coverage).

Usage:
    python scripts/ocr_extract_all_residential_setbacks.py --dry-run
    python scripts/ocr_extract_all_residential_setbacks.py
    python scripts/ocr_extract_all_residential_setbacks.py --council marrickville --dry-run
"""
import os, sys, re, argparse, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()

try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral

from enrichment.extractors.numeric_extractor import NumericExtractor

extractor = NumericExtractor()
NUMERIC_TYPES = {'setback', 'separation', 'separation_min', 'height', 'site_coverage', 'landscaping'}

CTRL_VERB_RE = re.compile(
    r'\b(must|shall|is\s+to|are\s+to|minimum|maximum|not\s+exceed|no\s+more\s+than|at\s+least|required|permitted)\b',
    re.IGNORECASE,
)
OBJ_SIGNAL_RE = re.compile(
    r'^\s*(objective|intent|purpose|aim|to\s+ensure|to\s+provide|to\s+protect|to\s+minimise|to\s+avoid)',
    re.IGNORECASE | re.MULTILINE,
)
# Clauses that look like setback controls but are actually about non-building elements
FALSE_POSITIVE_RE = re.compile(
    r'\b(tree|trees|dormer|dormer\s+window|roof\s+pitch|retaining\s+wall|front\s+fence|fence\s+height'
    r'|sight.line|skylight|from\s+the\s+sides?\s+of\s+the\s+roof)\b',
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Direct-insert records (no OCR needed — already read from prior OCR sessions)
# ---------------------------------------------------------------------------
DIRECT_INSERTS = [
    # Ashfield DS4 — dwelling house side setback (from pages 8-9 OCR, session prior)
    dict(lga='ashfield', dev_type='dwelling_house', control_type='side_setback',
         value_min=0.9, value_max=None, unit='m', condition=None,
         applicability='universal_residential',
         source_text='DS4.3 Generally, Council requires a minimum side setback of 900mm for houses. DS4.4 The minimum side setback is 900mm for the entire length of the building.',
         section_ref='chapter-f-dev-category/DS4.3-DS4.4',
         dcp_version='v1.1-2026-03-02', extraction_method='mistral_ocr'),
    dict(lga='ashfield', dev_type='dwelling_house', control_type='side_setback',
         value_min=0.45, value_max=None, unit='m', condition='outbuildings (garages, sheds)',
         applicability='universal_residential',
         source_text='DS4.5 The minimum side setback for outbuildings, including garages and sheds, where not located between the main building and side boundary is 450mm.',
         section_ref='chapter-f-dev-category/DS4.5',
         dcp_version='v1.1-2026-03-02', extraction_method='mistral_ocr'),

    # Woollahra B3.2 Figure 5A — dwelling_house side setback (lot-width dependent)
    dict(lga='woollahra', dev_type='dwelling_house', control_type='side_setback',
         value_min=0.9, value_max=None, unit='m',
         condition='site width < 9m (Figure 5A; lot-width dependent: 9-11m→1.1m; 11-13m→1.3m; 13-15m→1.5m; 15-17m→1.9m; 17-19m→2.3m; 19-21m→2.7m; 21-23m→3.1m; 23-25m→3.4m; 25-30m→3.75m; 30m+→4.5m)',
         applicability='universal_residential',
         source_text='B3.2.3 C1: minimum side setback for dwelling houses, semi-detached dwellings and dual occupancies is Figure 5A. Min 0.9m for site width < 9.0m.',
         section_ref='chapter-b3-general-development/B3.2.3_Figure5A',
         dcp_version='v1.0-baseline', extraction_method='mistral_ocr'),

    # Woollahra B3.2 Figure 5A — secondary_dwelling inherits same envelope
    dict(lga='woollahra', dev_type='secondary_dwelling', control_type='side_setback',
         value_min=0.9, value_max=None, unit='m',
         condition='site width < 9m; SD must be within dwelling house building envelope (B3.8 s3.8.2 C1) — Figure 5A applies',
         applicability='universal_residential',
         source_text='B3.8 s3.8.2 C1: secondary dwelling located within building envelope. Building envelope for dwelling house lot defined by Figure 5A setbacks (B3.2.3 C1).',
         section_ref='chapter-b3-general-development/B3.8-s3.8.2-C1+B3.2.3_Figure5A',
         dcp_version='v1.0-baseline', extraction_method='mistral_ocr'),

    # Woollahra B3.2 rear setback — formula-based 25%
    dict(lga='woollahra', dev_type='dwelling_house', control_type='rear_setback',
         value_min=25, value_max=None, unit='%',
         condition='of average side boundary depth: (side_A + side_B) / 2 × 25%',
         applicability='universal_residential',
         source_text='B3.2.4 C1: minimum rear setback = 25% of average of the two side boundary dimensions measured perpendicular to the rear boundary.',
         section_ref='chapter-b3-general-development/B3.2.4_Figure6',
         dcp_version='v1.0-baseline', extraction_method='mistral_ocr'),

    # Woollahra — SD inherits same rear setback formula
    dict(lga='woollahra', dev_type='secondary_dwelling', control_type='rear_setback',
         value_min=25, value_max=None, unit='%',
         condition='of average side boundary depth; SD within building envelope (B3.8 s3.8.2 C1)',
         applicability='universal_residential',
         source_text='B3.2.4 C1: rear setback = 25% of average side boundary depth. SD must be within the building envelope per B3.8 s3.8.2 C1.',
         section_ref='chapter-b3-general-development/B3.2.4+B3.8-s3.8.2',
         dcp_version='v1.0-baseline', extraction_method='mistral_ocr'),

    # Woollahra B3.2 Figure 5B — any other use (commercial/institutional on residential lots)
    dict(lga='woollahra', dev_type='other_residential', control_type='side_setback',
         value_min=1.5, value_max=None, unit='m',
         condition='site width < 18m (Figure 5B; varies: 18-21m→2.0m; 21-28m→2.5m; 28-35m→3.0m; 35m+→3.5m)',
         applicability='universal_residential',
         source_text='B3.2.3 C4: any other land use not addressed in C1-C3 → Figure 5B. Min 1.5m for site width < 18.0m.',
         section_ref='chapter-b3-general-development/B3.2.3_Figure5B',
         dcp_version='v1.0-baseline', extraction_method='mistral_ocr'),
]

# ---------------------------------------------------------------------------
# OCR targets
# ---------------------------------------------------------------------------
OCR_TARGETS = {
    'marrickville': {
        'url': 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/source-pdfs/dcps/marrickville/v1.1-2026-03-02/part4-s1-low-density.pdf',
        'pages': '1-55',
        'chapter_key': 'part4-s1-low-density',
        'dcp_version': 'v1.1-2026-03-02',
        'dev_types': ['dwelling_house', 'secondary_dwelling'],
        'section_hints': {
            'dwelling_house': ['C10', 'dwelling house', 'setback', '4 low density'],
            'secondary_dwelling': ['C11', 'secondary dwelling'],
        },
    },
    'ku_ring_gai_dwelling': {
        'url': 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/source-pdfs/dcps/ku_ring_gai/v1.0-baseline/section-a-part-4-dwelling-houses.pdf',
        'pages': '1-38',
        'chapter_key': 'section-a-part-4-dwelling-houses',
        'dcp_version': 'v1.0-baseline',
        'dev_types': ['dwelling_house'],
        'section_hints': {'dwelling_house': ['4A.2', 'building setback', 'dwelling house']},
    },
    'ku_ring_gai_sd': {
        'url': 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/source-pdfs/dcps/ku_ring_gai/v1.0-baseline/section-a-part-4-1-secondary-dwellings.pdf',
        'pages': '1-24',
        'chapter_key': 'section-a-part-4-1-secondary-dwellings',
        'dcp_version': 'v1.0-baseline',
        'dev_types': ['secondary_dwelling'],
        'section_hints': {'secondary_dwelling': ['4.1A', 'secondary dwelling', 'setback']},
    },
    'leichhardt': {
        'url': 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/source-pdfs/dcps/leichhardt/v1.1-2026-03-02/part-c-s3-residential.pdf',
        'pages': '1-34',
        'chapter_key': 'part-c-s3-residential',
        'dcp_version': 'v1.1-2026-03-02',
        'dev_types': ['dwelling_house', 'secondary_dwelling'],
        'section_hints': {
            'dwelling_house': ['setback', 'building line', 'C3.'],
            'secondary_dwelling': ['secondary dwelling'],
        },
    },
}

SETBACK_PAGE_RE = re.compile(
    r'(setback|rear\s+boundary|side\s+boundary|front\s+boundary|building\s+line|height\s+limit|site\s+coverage)',
    re.IGNORECASE,
)


def ocr_pdf(client, url, pages_str):
    if pages_str:
        start, end = pages_str.split('-')
        page_list = list(range(int(start) - 1, int(end)))
    else:
        page_list = None

    kwargs = dict(
        model='mistral-ocr-latest',
        document={'type': 'document_url', 'document_url': url},
        include_image_base64=False,
    )
    if page_list:
        kwargs['pages'] = page_list

    return client.ocr.process(**kwargs).pages


def extract_candidates(pages, section_hints):
    """Extract setback-relevant clauses from OCR pages."""
    full_text = '\n'.join(f'[PAGE {p.index + 1}]\n{p.markdown}' for p in pages)

    # Find the most relevant section start
    best_offset = None
    for hint in section_hints:
        m = re.search(re.escape(hint), full_text, re.IGNORECASE)
        if m:
            if best_offset is None or m.start() < best_offset:
                best_offset = m.start()

    section_text = full_text[best_offset:] if best_offset else full_text

    # Split into clauses (paragraphs + table cells)
    clauses = re.split(r'\n{2,}|(?=#{1,4}\s)', section_text)
    candidates = []

    for clause in clauses:
        clause = clause.strip()
        if not clause or len(clause) < 20:
            continue
        # Skip pure objective paragraphs
        if OBJ_SIGNAL_RE.match(clause) and not CTRL_VERB_RE.search(clause):
            continue
        if not CTRL_VERB_RE.search(clause[:400]):
            continue
        # Skip clauses that are clearly about trees, fences, dormers etc.
        if FALSE_POSITIVE_RE.search(clause[:400]):
            continue

        result = extractor.extract(clause)
        vals = [v for v in result.get('values', []) if v.get('value_type') in NUMERIC_TYPES]
        if not vals:
            continue

        for v in vals:
            ct = _map_control_type(v.get('value_type'), v.get('context'))
            if ct is None:
                continue
            candidates.append({
                'control_type': ct,
                'value_min': v.get('value_exact') or v.get('value_min'),
                'value_max': v.get('value_max'),
                'unit': v.get('unit', 'm'),
                'condition': v.get('condition'),
                'source_text': clause[:400],
                'raw': v,
            })

    return candidates


CTRL_TYPE_MAP = {
    ('setback', 'front'):    'front_setback',
    ('setback', 'rear'):     'rear_setback',
    ('setback', 'side'):     'side_setback',
    ('setback', 'street'):   'front_setback',
    ('setback', 'boundary'): 'side_setback',
    ('setback', 'common'):   'side_setback',
    ('setback', None):        None,  # ambiguous — don't guess
    ('separation', None):    'separation_from_dwelling',
    ('separation_min', None): 'separation_from_dwelling',
    ('height', None):        'max_height',
    ('height', 'max'):       'max_height',
    ('site_coverage', None): 'site_coverage_max',
    ('landscaping', None):   'landscaping_min',
}


def _map_control_type(value_type, context):
    key = (value_type, context)
    if key in CTRL_TYPE_MAP:
        return CTRL_TYPE_MAP[key]
    return CTRL_TYPE_MAP.get((value_type, None))


def do_insert(conn, lga, dev_type, applicability, chapter_key, dcp_version,
              extraction_method, rows, dry_run):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    inserted = 0
    for row in rows:
        cur.execute("""
            SELECT id FROM dcp_setback_controls
            WHERE lga = %s AND dev_type = %s AND control_type = %s
              AND COALESCE(condition,'') = COALESCE(%s,'')
              AND COALESCE(value_min::text,'') = COALESCE(%s::text,'')
        """, (lga, dev_type, row['control_type'], row.get('condition'), row.get('value_min')))
        if cur.fetchone():
            print(f"    SKIP dup: {row['control_type']} {row.get('value_min')}")
            continue

        if dry_run:
            print(f"    DRY-RUN: {lga} {dev_type} {row['control_type']} "
                  f"min={row.get('value_min')} max={row.get('value_max')} "
                  f"unit={row.get('unit')} cond={row.get('condition')}")
            print(f"      {row.get('source_text','')[:100]}")
        else:
            cur.execute("""
                INSERT INTO dcp_setback_controls
                  (lga, dev_type, control_type, value_min, value_max, unit,
                   condition, applicability, source_text, section_ref,
                   dcp_version, is_current, extraction_method)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,%s)
            """, (lga, dev_type, row['control_type'],
                  row.get('value_min'), row.get('value_max'), row.get('unit'),
                  row.get('condition'), applicability,
                  row.get('source_text'), row.get('section_ref') or chapter_key,
                  dcp_version, extraction_method))
            inserted += 1
            print(f"    INSERTED: {row['control_type']} min={row.get('value_min')} cond={row.get('condition')}")

    if not dry_run:
        conn.commit()
    return inserted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--council', default='all',
                        help='all | marrickville | ku_ring_gai | leichhardt | woollahra | ashfield')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    client = Mistral(api_key=os.environ['MISTRAL_API_KEY'])
    conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])

    # --- Direct inserts (no OCR) ---
    print("\n=== DIRECT INSERTS (Ashfield DS4 + Woollahra B3.2) ===")
    for rec in DIRECT_INSERTS:
        lga = rec['lga']
        if args.council != 'all' and lga != args.council:
            continue
        cur = conn.cursor()
        cur.execute("""
            SELECT id FROM dcp_setback_controls
            WHERE lga = %s AND dev_type = %s AND control_type = %s
              AND COALESCE(condition,'') = COALESCE(%s,'')
              AND COALESCE(value_min::text,'') = COALESCE(%s::text,'')
        """, (rec['lga'], rec['dev_type'], rec['control_type'],
              rec.get('condition'), rec.get('value_min')))
        if cur.fetchone():
            print(f"  SKIP dup: {lga} {rec['dev_type']} {rec['control_type']}")
            continue
        if args.dry_run:
            print(f"  DRY-RUN: {lga} {rec['dev_type']} {rec['control_type']} "
                  f"min={rec.get('value_min')} unit={rec.get('unit')}")
        else:
            cur.execute("""
                INSERT INTO dcp_setback_controls
                  (lga, dev_type, control_type, value_min, value_max, unit,
                   condition, applicability, source_text, section_ref,
                   dcp_version, is_current, extraction_method)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,%s)
            """, (rec['lga'], rec['dev_type'], rec['control_type'],
                  rec.get('value_min'), rec.get('value_max'), rec.get('unit'),
                  rec.get('condition'), rec['applicability'],
                  rec['source_text'], rec['section_ref'],
                  rec['dcp_version'], rec['extraction_method']))
            print(f"  INSERTED: {lga} {rec['dev_type']} {rec['control_type']} "
                  f"min={rec.get('value_min')} unit={rec.get('unit')}")
    if not args.dry_run:
        conn.commit()

    # --- OCR targets ---
    for target_key, cfg in OCR_TARGETS.items():
        council = target_key.split('_')[0] if '_' in target_key else target_key
        # Normalise: ku_ring_gai_dwelling → ku_ring_gai
        council_norm = re.sub(r'_(dwelling|sd)$', '', target_key)

        if args.council != 'all' and council_norm != args.council:
            continue

        print(f"\n{'='*60}")
        print(f"OCR: {target_key}  pages={cfg['pages']}")
        print('='*60)

        try:
            pages = ocr_pdf(client, cfg['url'], cfg['pages'])
        except Exception as e:
            print(f"  OCR ERROR: {e}")
            continue
        print(f"  OCR complete: {len(pages)} pages")

        for dev_type in cfg['dev_types']:
            hints = cfg['section_hints'].get(dev_type, [])
            candidates = extract_candidates(pages, hints)
            print(f"\n  dev_type={dev_type}  candidates={len(candidates)}")

            if not candidates:
                print("  No setback controls extracted from OCR.")
                continue

            for i, c in enumerate(candidates):
                print(f"\n  [{i+1}] {c['control_type']}  min={c['value_min']}  "
                      f"max={c['value_max']}  unit={c['unit']}  cond={c['condition']}")
                print(f"       {c['source_text'][:160]}")

            # separation_from_dwelling is always an SD control (SD ↔ main dwelling gap)
            # — never meaningful as a dwelling_house standalone control
            if dev_type == 'dwelling_house':
                candidates = [c for c in candidates
                              if c['control_type'] != 'separation_from_dwelling']

            # Patch known missing conditions that the extractor couldn't parse
            if target_key == 'ku_ring_gai_dwelling' and dev_type == 'dwelling_house':
                for c in candidates:
                    if c['control_type'] == 'rear_setback' and c['value_min'] == 12.0:
                        c['condition'] = 'site depth > 48m (sites ≤ 48m deep: see 4A.2 for applicable rear setback)'

            applicability = ('secondary_dwelling_specific'
                             if dev_type == 'secondary_dwelling'
                             else 'universal_residential')

            do_insert(conn, council_norm, dev_type, applicability,
                      cfg['chapter_key'], cfg['dcp_version'],
                      'mistral_ocr', candidates, args.dry_run)

    conn.close()
    print("\nDone.")


if __name__ == '__main__':
    main()
