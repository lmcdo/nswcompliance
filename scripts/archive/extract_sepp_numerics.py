#!/usr/bin/env python3
"""
Extract numeric standards from existing SEPP provisions.

Uses deterministic regex patterns - same methodology as extract_sepp_housing.py.
NO LLM, NO manual entry, 100% reproducible.

Usage:
    python scripts/extract_sepp_numerics.py --dry-run   # Show what would be extracted
    python scripts/extract_sepp_numerics.py --extract   # Actually insert to database
"""

import psycopg2
import os
import re
import argparse
from typing import Optional, Dict, List
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL')

# ============================================================
# NUMERIC STANDARD EXTRACTORS
# ============================================================

def extract_height_limit(provision_text: str) -> Optional[Dict]:
    """
    Extract height limits from SEPP provisions.

    Patterns:
    - "maximum height... X metres"
    - "height must not exceed X m"
    - "X m height limit"
    """
    patterns = [
        r'maximum.*?height.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
        r'height.*?(?:must\s+)?not.*?exceed.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
        r'(?:building|structure).*?height.*?limited.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
        r'(\d+(?:\.\d+)?)\s*m(?:etres?)?\s+(?:maximum\s+)?height',
    ]

    for pattern in patterns:
        match = re.search(pattern, provision_text, re.IGNORECASE)
        if match:
            height_value = float(match.group(1))
            # Sanity check: height between 3m and 50m
            if 3.0 <= height_value <= 50.0:
                return {
                    'metric_name': 'height_max',
                    'metric_value': height_value,
                    'metric_unit': 'm',
                    'metric_operator': 'max',
                    'confidence': 1.0,
                    'matched_pattern': f'height limit pattern: {pattern[:50]}'
                }

    return None


def extract_fsr(provision_text: str) -> Optional[Dict]:
    """
    Extract FSR (Floor Space Ratio) from SEPP provisions.

    Patterns:
    - "FSR of X:1" or "FSR X:1"
    - "floor space ratio of X"
    - "minimum FSR X"
    """
    patterns = [
        r'FSR.*?(\d+(?:\.\d+)?)\s*:\s*1',
        r'floor\s+space\s+ratio.*?(\d+(?:\.\d+)?)',
        r'minimum.*?FSR.*?(\d+(?:\.\d+)?)',
        r'(\d+(?:\.\d+)?)\s*:\s*1.*?FSR',
    ]

    for pattern in patterns:
        match = re.search(pattern, provision_text, re.IGNORECASE)
        if match:
            fsr_value = float(match.group(1))
            # Sanity check: FSR between 0.1 and 10.0
            if 0.1 <= fsr_value <= 10.0:
                return {
                    'metric_name': 'fsr_min',
                    'metric_value': fsr_value,
                    'metric_unit': 'ratio',
                    'metric_operator': 'min',
                    'confidence': 1.0,
                    'matched_pattern': f'FSR pattern: {pattern[:50]}'
                }

    return None


def extract_setback(provision_text: str) -> List[Dict]:
    """
    Extract setbacks from SEPP provisions.

    Returns list (can extract front, side, and rear from same provision).

    Patterns:
    - "front setback... X metres"
    - "side setback of X m"
    - "rear setback X m"
    """
    results = []

    # Front setback
    front_patterns = [
        r'(?:front|primary|street).*?setback.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
        r'setback.*?(?:from|to).*?(?:front|street|primary).*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
    ]
    for pattern in front_patterns:
        match = re.search(pattern, provision_text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            if 0.5 <= value <= 20.0:  # Sanity check
                results.append({
                    'metric_name': 'setback_front_min',
                    'metric_value': value,
                    'metric_unit': 'm',
                    'metric_operator': 'min',
                    'confidence': 1.0,
                    'matched_pattern': 'front setback pattern'
                })
                break

    # Side setback
    side_patterns = [
        r'side.*?setback.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
        r'setback.*?(?:from|to).*?side.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
        r'lateral.*?setback.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
    ]
    for pattern in side_patterns:
        match = re.search(pattern, provision_text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            # Check if it's in mm and convert
            if 'mm' in match.group(0).lower():
                value = value / 1000
            if 0.3 <= value <= 10.0:  # Sanity check
                results.append({
                    'metric_name': 'setback_side_min',
                    'metric_value': value,
                    'metric_unit': 'm',
                    'metric_operator': 'min',
                    'confidence': 1.0,
                    'matched_pattern': 'side setback pattern'
                })
                break

    # Rear setback
    rear_patterns = [
        r'rear.*?setback.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
        r'setback.*?(?:from|to).*?rear.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
    ]
    for pattern in rear_patterns:
        match = re.search(pattern, provision_text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            if 0.5 <= value <= 20.0:  # Sanity check
                results.append({
                    'metric_name': 'setback_rear_min',
                    'metric_value': value,
                    'metric_unit': 'm',
                    'metric_operator': 'min',
                    'confidence': 1.0,
                    'matched_pattern': 'rear setback pattern'
                })
                break

    return results


def extract_deep_soil(provision_text: str) -> Optional[Dict]:
    """
    Extract deep soil percentage.

    Patterns:
    - "deep soil... X%"
    - "minimum deep soil zone X percent"
    """
    patterns = [
        r'deep\s+soil.*?(\d+(?:\.\d+)?)\s*%',
        r'deep\s+soil.*?(\d+(?:\.\d+)?)\s*percent',
        r'(\d+(?:\.\d+)?)\s*%.*?deep\s+soil',
    ]

    for pattern in patterns:
        match = re.search(pattern, provision_text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            # Sanity check: 5% to 50%
            if 5.0 <= value <= 50.0:
                return {
                    'metric_name': 'deep_soil_percent_min',
                    'metric_value': value,
                    'metric_unit': 'percent',
                    'metric_operator': 'min',
                    'confidence': 1.0,
                    'matched_pattern': 'deep soil pattern'
                }

    return None


def extract_tree_canopy(provision_text: str) -> Optional[Dict]:
    """
    Extract tree canopy percentage.

    Patterns:
    - "tree canopy cover... X%"
    - "canopy coverage X percent"
    """
    patterns = [
        r'tree\s+canopy.*?(\d+(?:\.\d+)?)\s*%',
        r'canopy\s+cover(?:age)?.*?(\d+(?:\.\d+)?)\s*%',
        r'(\d+(?:\.\d+)?)\s*%.*?tree\s+canopy',
    ]

    for pattern in patterns:
        match = re.search(pattern, provision_text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            # Sanity check: 10% to 50%
            if 10.0 <= value <= 50.0:
                return {
                    'metric_name': 'tree_canopy_percent_min',
                    'metric_value': value,
                    'metric_unit': 'percent',
                    'metric_operator': 'min',
                    'confidence': 1.0,
                    'matched_pattern': 'tree canopy pattern'
                }

    return None


def extract_lot_size(provision_text: str) -> Optional[Dict]:
    """
    Extract minimum lot size requirements.

    Patterns:
    - "minimum lot size... X m2"
    - "lot area of at least X sqm"
    """
    patterns = [
        r'minimum.*?lot\s+(?:size|area).*?(\d+(?:,\d+)?)\s*(?:m2|sqm|square\s+metres?)',
        r'lot.*?(?:size|area).*?(?:at\s+least|minimum).*?(\d+(?:,\d+)?)\s*(?:m2|sqm)',
    ]

    for pattern in patterns:
        match = re.search(pattern, provision_text, re.IGNORECASE)
        if match:
            # Remove commas from number
            value_str = match.group(1).replace(',', '')
            value = float(value_str)
            # Sanity check: 200 to 2000 sqm
            if 200.0 <= value <= 2000.0:
                return {
                    'metric_name': 'lot_size_min',
                    'metric_value': value,
                    'metric_unit': 'sqm',
                    'metric_operator': 'min',
                    'confidence': 1.0,
                    'matched_pattern': 'lot size pattern'
                }

    return None


# ============================================================
# MAIN EXTRACTION LOGIC
# ============================================================

def extract_all_numerics(provision_text: str) -> List[Dict]:
    """
    Run all numeric extractors on a provision.

    Returns:
        List of extracted numerics (may be empty or contain multiple)
    """
    numerics = []

    # Single-value extractors
    height = extract_height_limit(provision_text)
    if height:
        numerics.append(height)

    fsr = extract_fsr(provision_text)
    if fsr:
        numerics.append(fsr)

    deep_soil = extract_deep_soil(provision_text)
    if deep_soil:
        numerics.append(deep_soil)

    tree_canopy = extract_tree_canopy(provision_text)
    if tree_canopy:
        numerics.append(tree_canopy)

    lot_size = extract_lot_size(provision_text)
    if lot_size:
        numerics.append(lot_size)

    # Multi-value extractor
    setbacks = extract_setback(provision_text)
    numerics.extend(setbacks)

    return numerics


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL)


def fetch_candidate_provisions():
    """
    Fetch SEPP provisions that likely contain numeric standards.

    Uses keyword filtering and regex for numeric content.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Query provisions with numeric content
    query = """
        SELECT
            rp.id,
            rp.provision_text,
            rp.pdf_page,
            d.pdf_name,
            rp.v2_topic
        FROM regulatory_provisions rp
        JOIN documents d ON rp.document_id = d.id
        WHERE d.document_type = 'SEPP'
          AND rp.v2_is_actionable = true
          AND rp.provision_text IS NOT NULL
          AND rp.provision_text ~ '\d+(?:\.\d+)?\s*(?:m|%|metres?|percent|sqm|m2)'
          AND (
            provision_text ILIKE '%height%' OR
            provision_text ILIKE '%FSR%' OR
            provision_text ILIKE '%floor space ratio%' OR
            provision_text ILIKE '%setback%' OR
            provision_text ILIKE '%deep soil%' OR
            provision_text ILIKE '%tree canopy%' OR
            provision_text ILIKE '%lot size%' OR
            provision_text ILIKE '%lot area%'
          )
        ORDER BY d.pdf_name, rp.pdf_page, rp.id
    """

    cur.execute(query)
    provisions = cur.fetchall()

    cur.close()
    conn.close()

    return provisions


def insert_numeric(provision_id: int, numeric: Dict, pdf_page: int,
                   provision_text: str, document_name: str):
    """Insert extracted numeric standard into database."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO sepp_structured_requirements (
            provision_id,
            requirement_category,
            metric_name,
            metric_value,
            metric_unit,
            metric_operator,
            applies_to,
            source_pdf_page,
            source_provision_text,
            extraction_confidence,
            source_clause
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (
        provision_id,
        'numeric_standard',
        numeric['metric_name'],
        numeric['metric_value'],
        numeric['metric_unit'],
        numeric['metric_operator'],
        'all',  # Default applies_to
        pdf_page,
        provision_text[:500],  # First 500 chars for reference
        numeric['confidence'],
        f"{document_name} - Page {pdf_page}"
    ))

    conn.commit()
    cur.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Extract SEPP numeric standards')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be extracted without inserting')
    parser.add_argument('--extract', action='store_true',
                       help='Actually extract and insert to database')

    args = parser.parse_args()

    if not args.dry_run and not args.extract:
        print("ERROR: Specify --dry-run or --extract")
        return

    print("=" * 70)
    print("SEPP NUMERIC STANDARDS EXTRACTION")
    print("=" * 70)
    print()

    # Fetch candidate provisions
    print("Fetching candidate provisions from database...")
    provisions = fetch_candidate_provisions()
    print(f"Found {len(provisions)} candidate provisions")
    print()

    # Extract numerics
    print("Running deterministic numeric extractors...")
    print()

    extracted_count = 0
    numeric_types = {}

    for prov_id, prov_text, pdf_page, doc_name, topic in provisions:
        numerics = extract_all_numerics(prov_text)

        if numerics:
            for numeric in numerics:
                metric_name = numeric['metric_name']
                numeric_types[metric_name] = numeric_types.get(metric_name, 0) + 1

                print(f"[{extracted_count + 1}] Provision ID {prov_id} (Page {pdf_page})")
                print(f"    Metric: {metric_name}")
                print(f"    Value: {numeric['metric_value']} {numeric['metric_unit']}")
                print(f"    Operator: {numeric['metric_operator']}")
                print(f"    Topic: {topic or 'NULL'}")
                print(f"    Text: {prov_text[:100].replace(chr(10), ' ')}...")
                print()

                if args.extract:
                    insert_numeric(prov_id, numeric, pdf_page, prov_text, doc_name)

                extracted_count += 1

    print("=" * 70)
    print("EXTRACTION SUMMARY")
    print("=" * 70)
    print(f"Total numeric standards extracted: {extracted_count}")
    print()
    print("By metric:")
    for metric, count in sorted(numeric_types.items()):
        print(f"  {metric}: {count}")
    print()

    if args.dry_run:
        print("DRY RUN - No data inserted")
    else:
        print(f"Inserted {extracted_count} numeric standards to database")
    print()


if __name__ == '__main__':
    main()
