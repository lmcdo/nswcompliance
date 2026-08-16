#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR extraction of DCP setback controls from local PDFs in data/dcps/.
Covers: dwelling_house + secondary_dwelling for 10 new LGAs.

Usage:
    python scripts/ocr_local_dcps.py --dry-run
    python scripts/ocr_local_dcps.py
    python scripts/ocr_local_dcps.py --lga hornsby --dry-run
"""
import os, sys, re, base64, argparse
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

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'dcps')

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
CTRL_VERB_RE = re.compile(
    r'\b(must|shall|is\s+to|are\s+to|minimum|maximum|not\s+exceed|no\s+more\s+than|at\s+least|required|permitted)\b',
    re.IGNORECASE,
)
OBJ_SIGNAL_RE = re.compile(
    r'^\s*(objective|intent|purpose|aim|to\s+ensure|to\s+provide|to\s+protect|to\s+minimise|to\s+avoid)',
    re.IGNORECASE | re.MULTILINE,
)
FALSE_POSITIVE_RE = re.compile(
    r'\b(tree|trees|dormer|dormer\s+window|roof\s+pitch|retaining\s+wall|fence\s+height|front\s+fence'
    r'|sight.line|skylight|from\s+the\s+sides?\s+of\s+the\s+roof|car\s+parking|parking\s+space'
    r'|driveway|letterbox|garbage\s+bin|clothes\s+line|swimming\s+pool|spa|garden\s+shed'
    r'|satellite\s+dish|antenna|air\s+conditioning|water\s+tank|solar\s+panel'
    r'|eave|eaves|gutter|guttering'
    r'|fencing\s+having|fenced\s+on|fence\s+must'
    r'|detached\s+garage|carport|outbuilding'
    r'|frontage\s+on\s+each|frontage\s+of\s+each'
    r'|outdoor\s+play|play\s+area)\b',
    re.IGNORECASE,
)

# SD section heading detection
SD_HEADING_RE = re.compile(
    r'(?:^|\n)#{1,4}\s*(?:\d+[\.\d]*\s+)?(?:secondary\s+dwell|granny\s+flat|ancillary\s+dwell)',
    re.IGNORECASE | re.MULTILINE,
)

CTRL_TYPE_MAP = {
    ('setback', 'front'):     'front_setback',
    ('setback', 'rear'):      'rear_setback',
    ('setback', 'side'):      'side_setback',
    ('setback', 'street'):    'front_setback',
    ('setback', 'boundary'):  'side_setback',
    ('setback', 'common'):    'side_setback',
    ('setback', None):        None,   # ambiguous — skip
    ('separation', None):     'separation_from_dwelling',
    ('separation_min', None): 'separation_from_dwelling',
    ('height', None):         'max_height',
    ('height', 'max'):        'max_height',
    ('site_coverage', None):  'site_coverage_max',
    ('landscaping', None):    'landscaping_min',
}

# ---------------------------------------------------------------------------
# PDF config — one entry per file
# ---------------------------------------------------------------------------
PDF_CONFIGS = {
    'blacktown': {
        'file': 'blacktown-part-c-residential.pdf',
        'lga': 'blacktown',
        'dev_types': ['dwelling_house', 'secondary_dwelling'],
        'dh_hints': ['setback', 'dwelling house', 'residential'],
        'sd_hints': ['secondary dwelling', 'granny flat'],
        'dcp_version': 'v1.0-baseline',
        'large': False,
    },
    'campbelltown': {
        'file': 'campbelltown-part3-low-medium-density.pdf',
        'lga': 'campbelltown',
        'dev_types': ['dwelling_house', 'secondary_dwelling'],
        'dh_hints': ['setback', 'dwelling house', 'low density'],
        'sd_hints': ['secondary dwelling'],
        'dcp_version': 'v1.0-baseline',
        'large': False,
    },
    'canterbury_bankstown': {
        'file': 'canterbury-bankstown.pdf',
        'lga': 'canterbury_bankstown',
        'dev_types': ['dwelling_house', 'secondary_dwelling'],
        'dh_hints': ['setback', 'dwelling house'],
        'sd_hints': ['secondary dwelling'],
        'dcp_version': 'v1.0-baseline',
        'large': False,
    },
    'cumberland': {
        'file': 'cumberland-part-b-residential.pdf',
        'lga': 'cumberland',
        'dev_types': ['dwelling_house', 'secondary_dwelling'],
        'dh_hints': ['setback', 'dwelling house', 'residential'],
        'sd_hints': ['secondary dwelling'],
        'dcp_version': 'v1.0-baseline',
        'large': False,
    },
    'hornsby': {
        'file': 'hornsby-part3-residential.pdf',
        'lga': 'hornsby',
        'dev_types': ['dwelling_house', 'secondary_dwelling'],
        'dh_hints': ['setback', 'dwelling house'],
        'sd_hints': ['secondary dwelling'],
        'dcp_version': 'v1.0-baseline',
        'large': True,
        'toc_pages': [0, 1, 2, 3, 4],
    },
    'ku_ring_gai_part5': {
        'file': 'ku-ring-gai-part5-secondary-dwellings.pdf',
        'lga': 'ku_ring_gai',
        'dev_types': ['secondary_dwelling'],
        'sd_hints': ['secondary dwelling', 'setback'],
        'dcp_version': 'v1.0-baseline',
        'large': False,
    },
    'liverpool': {
        'file': 'liverpool-part8-dwelling-houses.pdf',
        'lga': 'liverpool',
        'dev_types': ['dwelling_house'],
        'dh_hints': ['setback', 'dwelling house'],
        'dcp_version': 'v1.0-baseline',
        'large': False,
    },
    'northern_beaches': {
        'file': 'northern-beaches-warringah-dcp-2011.pdf',
        'lga': 'northern_beaches',
        'dev_types': ['dwelling_house', 'secondary_dwelling'],
        'dh_hints': ['setback', 'dwelling house', 'residential'],
        'sd_hints': ['secondary dwelling'],
        'dcp_version': 'v1.0-baseline',
        'large': True,
        'toc_pages': [0, 1, 2, 3, 4],
    },
    'parramatta': {
        'file': 'parramatta-dcp-2023.pdf',
        'lga': 'parramatta',
        'dev_types': ['dwelling_house', 'secondary_dwelling'],
        'dh_hints': ['setback', 'dwelling house', 'low density'],
        'sd_hints': ['secondary dwelling'],
        'dcp_version': 'v1.0-baseline',
        'large': True,
        'toc_pages': list(range(10)),
    },
    'penrith': {
        'file': 'penrith-part-d2-residential.pdf',
        'lga': 'penrith',
        'dev_types': ['dwelling_house', 'secondary_dwelling'],
        'dh_hints': ['setback', 'dwelling house', 'residential'],
        'sd_hints': ['secondary dwelling'],
        'dcp_version': 'v1.0-baseline',
        'large': False,
    },
    # --- Tier 1 batch (2026-05-12) ---
    'ryde': {
        'file': 'ryde-part3.3-dwelling-houses.pdf',
        'lga': 'ryde',
        'dev_types': ['dwelling_house'],
        'dh_hints': ['setback', 'dwelling house', 'dual occupancy'],
        'dcp_version': 'v1.0-baseline',
        'large': False,
    },
    'strathfield': {
        'file': 'strathfield-part-a-dwelling-houses.pdf',
        'lga': 'strathfield',
        'dev_types': ['dwelling_house'],
        'dh_hints': ['setback', 'dwelling house', 'ancillary'],
        'dcp_version': 'v1.0-baseline',
        'large': False,
    },
    'the_hills': {
        'file': 'hills-shire-part-b-section2-residential.pdf',
        'lga': 'the_hills',
        'dev_types': ['dwelling_house', 'secondary_dwelling'],
        'dh_hints': ['setback', 'dwelling', 'residential'],
        'sd_hints': ['secondary dwelling'],
        'dcp_version': 'v1.0-baseline',
        'large': False,
    },
    'camden': {
        'file': 'camden-part4-residential-dwelling-controls.pdf',
        'lga': 'camden',
        'dev_types': ['dwelling_house', 'secondary_dwelling'],
        'dh_hints': ['setback', 'dwelling house', 'residential'],
        'sd_hints': ['secondary dwelling'],
        'dcp_version': 'v1.0-baseline',
        'large': False,
    },
    'canada_bay': {
        'file': 'canada-bay-part-e-single-dwellings.pdf',
        'lga': 'canada_bay',
        'dev_types': ['dwelling_house', 'secondary_dwelling'],
        'dh_hints': ['setback', 'single dwelling', 'dual occupancy'],
        'sd_hints': ['secondary dwelling'],
        'dcp_version': 'v1.0-baseline',
        'large': False,
    },
    'burwood': {
        'file': 'burwood-part4-residential.pdf',
        'lga': 'burwood',
        'dev_types': ['dwelling_house', 'secondary_dwelling'],
        'dh_hints': ['setback', 'dwelling house', 'residential'],
        'sd_hints': ['secondary dwelling', 'dual occupancy'],
        'dcp_version': 'v1.0-baseline',
        'large': False,
    },
    'fairfield': {
        'file': 'fairfield-ch5-dwelling-houses.pdf',
        'lga': 'fairfield',
        'dev_types': ['dwelling_house', 'secondary_dwelling'],
        'dh_hints': ['setback', 'dwelling house'],
        'sd_hints': ['secondary dwelling'],
        'dcp_version': 'v1.0-baseline',
        'large': False,
    },
}

# TOC line detection: "Dwelling Houses .... 23" or "4.2 Dwelling Houses   45"
TOC_PAGE_RE = re.compile(
    r'(?P<label>(?:dwelling\s+house|secondary\s+dwell|granny\s+flat)[^\n]*?)'
    r'(?:\s*[\.·\-_]{2,}\s*|\s{3,})'
    r'(?P<page>\d{1,3})\b',
    re.IGNORECASE,
)


def pdf_to_b64_url(path):
    with open(path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    return f'data:application/pdf;base64,{b64}'


def ocr_pages(client, pdf_path, page_indices=None):
    """OCR specific pages (0-based list, or None for all). Returns page objects."""
    url = pdf_to_b64_url(pdf_path)
    kwargs = dict(
        model='mistral-ocr-latest',
        document={'type': 'document_url', 'document_url': url},
        include_image_base64=False,
    )
    if page_indices is not None:
        kwargs['pages'] = page_indices
    return client.ocr.process(**kwargs).pages


def parse_toc(toc_text):
    """Return {section_name: page_number} from OCR'd TOC text."""
    found = {}
    for m in TOC_PAGE_RE.finditer(toc_text):
        label = m.group('label').strip().lower()
        page = int(m.group('page'))
        if 'dwelling house' in label and 'dwelling_house' not in found:
            found['dwelling_house'] = page
        elif ('secondary dwell' in label or 'granny flat' in label) and 'secondary_dwelling' not in found:
            found['secondary_dwelling'] = page
    return found


def pages_to_text(pages):
    return '\n'.join(f'[PAGE {p.index + 1}]\n{p.markdown}' for p in pages)


def split_dh_sd(full_text):
    """Split text at first SD heading. Returns (dh_text, sd_text)."""
    m = SD_HEADING_RE.search(full_text)
    if m:
        return full_text[:m.start()], full_text[m.start():]
    return full_text, ''


def extract_candidates(text, hints):
    """Find setback controls in text, anchored to the first hint match."""
    best_offset = None
    for hint in hints:
        m = re.search(re.escape(hint), text, re.IGNORECASE)
        if m and (best_offset is None or m.start() < best_offset):
            best_offset = m.start()

    section = text[best_offset:] if best_offset else text
    clauses = re.split(r'\n{2,}|(?=#{1,4}\s)', section)
    out = []

    for clause in clauses:
        clause = clause.strip()
        if not clause or len(clause) < 20:
            continue
        if OBJ_SIGNAL_RE.match(clause) and not CTRL_VERB_RE.search(clause):
            continue
        if not CTRL_VERB_RE.search(clause[:400]):
            continue
        if FALSE_POSITIVE_RE.search(clause[:400]):
            continue

        result = extractor.extract(clause)
        vals = [v for v in result.get('values', []) if v.get('value_type') in NUMERIC_TYPES]
        for v in vals:
            vtype = v.get('value_type')
            ctx = v.get('context')
            ct = CTRL_TYPE_MAP.get((vtype, ctx)) or CTRL_TYPE_MAP.get((vtype, None))
            if ct is None:
                continue
            out.append({
                'control_type': ct,
                'value_min': v.get('value_exact') or v.get('value_min'),
                'value_max': v.get('value_max'),
                'unit': v.get('unit', 'm'),
                'condition': v.get('condition'),
                'source_text': clause[:400],
            })

    return out


PLAUSIBLE_RANGES = {
    'front_setback':  (2.0, 15.0),
    'side_setback':   (0.5, 6.0),
    'rear_setback':   (1.0, 15.0),   # 15m is very generous for outer-suburb large lots
    'max_height':     (2.4, 15.0),
    'site_coverage_max': (20.0, 80.0),
    'landscaping_min': (10.0, 60.0),
    'separation_from_dwelling': (1.0, 15.0),
}

# Control types that must have a non-empty unit
UNIT_REQUIRED = {'front_setback', 'side_setback', 'rear_setback', 'max_height', 'separation_from_dwelling'}


def in_range(control_type, value_min):
    if value_min is None:
        return True
    lo, hi = PLAUSIBLE_RANGES.get(control_type, (0, 999))
    try:
        return lo <= float(value_min) <= hi
    except (TypeError, ValueError):
        return True


def dedup(candidates):
    seen = set()
    out = []
    for c in candidates:
        ct = c['control_type']
        if not in_range(ct, c.get('value_min')):
            continue
        # Skip if unit is missing for types where it's required
        if ct in UNIT_REQUIRED and not (c.get('unit') or '').strip():
            continue
        key = (ct, str(c.get('value_min')), c.get('condition') or '')
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def try_insert(cur, lga, dev_type, c, applicability, section_ref, dcp_version, dry_run):
    cur.execute(
        "SELECT id FROM dcp_setback_controls "
        "WHERE lga=%s AND dev_type=%s AND control_type=%s "
        "AND COALESCE(condition,'')=COALESCE(%s,'') "
        "AND COALESCE(value_min::text,'')=COALESCE(%s::text,'')",
        (lga, dev_type, c['control_type'], c.get('condition'), c.get('value_min')),
    )
    if cur.fetchone():
        return 'dup'
    if dry_run:
        return 'dry'
    cur.execute(
        "INSERT INTO dcp_setback_controls "
        "(lga,dev_type,control_type,value_min,value_max,unit,condition,"
        "applicability,source_text,section_ref,dcp_version,is_current,extraction_method) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,%s)",
        (lga, dev_type, c['control_type'], c.get('value_min'), c.get('value_max'),
         c.get('unit', 'm'), c.get('condition'), applicability,
         c['source_text'], section_ref, dcp_version, 'mistral_ocr'),
    )
    return 'inserted'


def process_lga(client, conn, key, cfg, dry_run):
    lga = cfg['lga']
    path = os.path.join(DATA_DIR, cfg['file'])
    if not os.path.exists(path):
        print(f'  FILE NOT FOUND: {path}')
        return {}

    mb = os.path.getsize(path) / 1_000_000
    print(f'  {cfg["file"]} ({mb:.1f} MB)')

    # Mistral OCR hard limit: 1000 pages. Very large DCPs (full instrument) need
    # specific chapter PDFs — skip with a clear note.
    if mb > 40:
        print(f'  SKIP: File exceeds 40MB ({mb:.0f}MB). Mistral limit is 1000 pages.')
        print('  Action needed: Download specific residential chapter PDF.')
        return {}

    cur = conn.cursor(cursor_factory=RealDictCursor)
    counts = {'inserted': 0, 'dup': 0, 'dry': 0}

    # For large files: TOC scan to get targeted page ranges
    dh_page_range = None
    sd_page_range = None

    if cfg.get('large'):
        # Check for explicit page overrides first (bypasses TOC scan)
        if cfg.get('dh_pages_override'):
            dh_page_range = cfg['dh_pages_override']
            print(f'  [LARGE] Using DH page override: pages {dh_page_range[0]}-{dh_page_range[-1]}')
        if cfg.get('sd_pages_override'):
            sd_page_range = cfg['sd_pages_override']
            print(f'  [LARGE] Using SD page override: pages {sd_page_range[0]}-{sd_page_range[-1]}')

        if not dh_page_range:
            print('  [LARGE] Scanning TOC...')
            toc_pages = ocr_pages(client, path, cfg.get('toc_pages', list(range(5))))
            toc_text = pages_to_text(toc_pages)
            toc_info = parse_toc(toc_text)
            print(f'  TOC: {toc_info}')

            if toc_info.get('dwelling_house'):
                pg = toc_info['dwelling_house'] - 1   # 0-based
                dh_page_range = list(range(max(0, pg), pg + 50))

            if not sd_page_range and toc_info.get('secondary_dwelling'):
                pg = toc_info['secondary_dwelling'] - 1
                sd_page_range = list(range(max(0, pg), pg + 40))

            if not dh_page_range:
                print('  WARNING: no DH section found in TOC, using pages 0-59')
                dh_page_range = list(range(60))

    # OCR the relevant section (one OCR pass for DH, one for SD if separate)
    if not cfg.get('large') or not sd_page_range or dh_page_range == sd_page_range:
        # Single pass — split the result at the SD heading
        print('  OCR-ing full section...')
        pages = ocr_pages(client, path, dh_page_range)
        full_text = pages_to_text(pages)
        print(f'  {len(pages)} pages, {len(full_text):,} chars')
        dh_text, sd_text = split_dh_sd(full_text)
        sections = {'dwelling_house': dh_text if dh_text.strip() else full_text}
        if sd_text.strip():
            sections['secondary_dwelling'] = sd_text
        else:
            print('  NOTE: No SD heading found in text — SD section skipped (may inherit DH controls)')
    else:
        # Large file: separate OCR passes for DH and SD sections
        sections = {}
        if 'dwelling_house' in cfg['dev_types']:
            print('  OCR-ing DH section...')
            dh_pages = ocr_pages(client, path, dh_page_range)
            dh_full = pages_to_text(dh_pages)
            dh_text, _ = split_dh_sd(dh_full)
            sections['dwelling_house'] = dh_text
            print(f'  DH: {len(dh_pages)} pages')

        if 'secondary_dwelling' in cfg['dev_types']:
            sd_range = sd_page_range
            print('  OCR-ing SD section...')
            sd_pages = ocr_pages(client, path, sd_range)
            sd_full = pages_to_text(sd_pages)
            _, sd_text = split_dh_sd(sd_full)
            if sd_text.strip():
                sections['secondary_dwelling'] = sd_text
            else:
                sections['secondary_dwelling'] = sd_full  # use full SD range text
            print(f'  SD: {len(sd_pages)} pages')

    # Extract and insert
    for dev_type in cfg['dev_types']:
        hints = cfg.get('dh_hints' if dev_type == 'dwelling_house' else 'sd_hints', ['setback'])
        work_text = sections.get(dev_type, '')

        if not work_text.strip():
            print(f'\n  [{dev_type}] No section text found.')
            continue

        candidates = extract_candidates(work_text, hints)
        candidates = dedup(candidates)

        # Separation controls only make sense for SD (SD-to-main-dwelling gap)
        if dev_type == 'dwelling_house':
            candidates = [c for c in candidates if c['control_type'] != 'separation_from_dwelling']

        applicability = ('secondary_dwelling_specific' if dev_type == 'secondary_dwelling'
                         else 'universal_residential')
        section_ref = f'{cfg["file"]}#{dev_type}'

        print(f'\n  [{dev_type}] {len(candidates)} candidates')
        for c in candidates:
            cond_s = (c.get('condition') or '')[:55]
            print(f'    {c["control_type"]:25} {str(c.get("value_min") or ""):>6} {c.get("unit","m"):3}  {cond_s}')
            print(f'      {c["source_text"][:110]}')

            result = try_insert(cur, lga, dev_type, c, applicability,
                                section_ref, cfg['dcp_version'], dry_run)
            counts[result] += 1
            print(f'    -> {result}')

    if not dry_run:
        conn.commit()

    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lga', default='all')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    client = Mistral(api_key=os.environ['MISTRAL_API_KEY'])
    conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
    total = {'inserted': 0, 'dup': 0, 'dry': 0}

    for key, cfg in PDF_CONFIGS.items():
        if args.lga != 'all' and cfg['lga'] != args.lga and key != args.lga:
            continue
        print(f'\n{"="*60}')
        print(f'LGA: {cfg["lga"]}  ({key})')
        print('='*60)
        counts = process_lga(client, conn, key, cfg, args.dry_run)
        for k in total:
            total[k] += counts.get(k, 0)

    print(f'\n{"="*60}')
    print(f'TOTAL: inserted={total["inserted"]}  dup={total["dup"]}  dry={total["dry"]}')
    conn.close()


if __name__ == '__main__':
    main()
