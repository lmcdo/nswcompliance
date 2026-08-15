#!/usr/bin/env python3
"""
Extract exclusion triggers from existing SEPP provisions.

Uses deterministic regex patterns - same methodology as extract_sepp_housing.py.
NO LLM, NO manual entry, 100% reproducible.

Usage:
    python scripts/extract_sepp_exclusions.py --dry-run   # Show what would be extracted
    python scripts/extract_sepp_exclusions.py --extract   # Actually insert to database
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
# EXCLUSION PATTERN EXTRACTORS
# ============================================================

def extract_heritage_exclusion(provision_text: str) -> Optional[Dict]:
    """
    Detect heritage exclusions via keyword patterns.

    Patterns:
    - "heritage item" + prohibition keywords
    - "heritage conservation area" + prohibition
    - "draft heritage" + prohibition
    """
    # Check for heritage keywords
    heritage_match = re.search(
        r'heritage\s+(?:item|conservation\s+area)|'
        r'draft\s+heritage|'
        r'state\s+heritage\s+register',
        provision_text,
        re.IGNORECASE
    )

    if not heritage_match:
        return None

    # Check for prohibition/exclusion keywords
    exclusion_match = re.search(
        r'prohibit(?:ed)?|'
        r'excluded?|'
        r'must\s+not|'
        r'cannot|'
        r'does\s+not\s+apply|'
        r'not\s+permitted',
        provision_text,
        re.IGNORECASE
    )

    if exclusion_match:
        return {
            'exclusion_type': 'heritage',
            'applies_to': 'all',
            'confidence': 1.0,
            'matched_pattern': 'heritage + prohibition keywords'
        }

    return None


def extract_flood_exclusion(provision_text: str) -> Optional[Dict]:
    """
    Detect flood exclusions.

    Patterns:
    - "flood planning area" + exclusion
    - "flood control lot" + prohibition
    - "PMF" (Probable Maximum Flood)
    """
    flood_match = re.search(
        r'flood\s+(?:planning|control|prone)|'
        r'PMF|'
        r'probable\s+maximum\s+flood|'
        r'floodplain',
        provision_text,
        re.IGNORECASE
    )

    if not flood_match:
        return None

    # Check for exclusion keywords
    exclusion_match = re.search(
        r'must\s+not\s+be\s+carried\s+out|'
        r'excluded?|'
        r'prohibit(?:ed)?|'
        r'does\s+not\s+apply',
        provision_text,
        re.IGNORECASE
    )

    if exclusion_match:
        return {
            'exclusion_type': 'flood_planning_area',
            'applies_to': 'all',
            'confidence': 1.0,
            'matched_pattern': 'flood + exclusion keywords'
        }

    return None


def extract_bushfire_exclusion(provision_text: str) -> Optional[Dict]:
    """
    Detect bushfire exclusions.

    Patterns:
    - "bushfire prone land"
    - "BAL-12.5" or "BAL 12.5"
    """
    bushfire_match = re.search(
        r'bushfire\s+prone|'
        r'BAL-?\d+|'
        r'bush\s+fire\s+prone',
        provision_text,
        re.IGNORECASE
    )

    if not bushfire_match:
        return None

    # Bushfire prone land is typically an automatic exclusion
    # or requires specific assessment
    exclusion_match = re.search(
        r'excluded?|'
        r'must\s+not|'
        r'prohibit(?:ed)?|'
        r'does\s+not\s+apply',
        provision_text,
        re.IGNORECASE
    )

    if exclusion_match:
        return {
            'exclusion_type': 'bushfire_prone',
            'applies_to': 'all',
            'confidence': 1.0,
            'matched_pattern': 'bushfire + exclusion keywords'
        }

    return None


def extract_acid_sulfate_exclusion(provision_text: str) -> Optional[Dict]:
    """
    Detect acid sulfate soil exclusions.

    Patterns:
    - "acid sulfate soils"
    - "ASS"
    """
    ass_match = re.search(
        r'acid\s+sul(?:ph|f)ate\s+soils?|'
        r'\bASS\b',
        provision_text,
        re.IGNORECASE
    )

    if ass_match:
        return {
            'exclusion_type': 'acid_sulfate_soils',
            'applies_to': 'all',
            'confidence': 1.0,
            'matched_pattern': 'acid sulfate soils keyword'
        }

    return None


def extract_aircraft_noise_exclusion(provision_text: str) -> Optional[Dict]:
    """
    Detect aircraft noise exclusions.

    Patterns:
    - "25 ANEF" or "20 ANEF"
    - "aircraft noise"
    """
    aircraft_match = re.search(
        r'(?:25|20)\s+ANEF|'
        r'aircraft\s+noise|'
        r'ANEF\s+contour',
        provision_text,
        re.IGNORECASE
    )

    if aircraft_match:
        return {
            'exclusion_type': 'aircraft_noise',
            'applies_to': 'all',
            'confidence': 1.0,
            'matched_pattern': 'ANEF/aircraft noise keyword'
        }

    return None


def extract_threatened_species_exclusion(provision_text: str) -> Optional[Dict]:
    """
    Detect threatened species/biodiversity exclusions.

    Patterns:
    - "threatened species"
    - "critical habitat"
    - "endangered ecological community"
    """
    species_match = re.search(
        r'threatened\s+species|'
        r'critical\s+habitat|'
        r'endangered\s+ecological\s+communit|'
        r'biodiversity.*threshold',
        provision_text,
        re.IGNORECASE
    )

    if not species_match:
        return None

    exclusion_match = re.search(
        r'excluded?|'
        r'must\s+not|'
        r'prohibit(?:ed)?',
        provision_text,
        re.IGNORECASE
    )

    if exclusion_match:
        return {
            'exclusion_type': 'threatened_species',
            'applies_to': 'all',
            'confidence': 1.0,
            'matched_pattern': 'threatened species + exclusion'
        }

    return None


def extract_coastal_exclusion(provision_text: str) -> Optional[Dict]:
    """
    Detect coastal erosion/management exclusions.

    Patterns:
    - "coastal erosion"
    - "coastal management"
    - "foreshore area"
    """
    coastal_match = re.search(
        r'coastal\s+(?:erosion|management)|'
        r'foreshore\s+area|'
        r'coastal\s+zone',
        provision_text,
        re.IGNORECASE
    )

    if coastal_match:
        return {
            'exclusion_type': 'coastal_erosion',
            'applies_to': 'all',
            'confidence': 1.0,
            'matched_pattern': 'coastal keyword'
        }

    return None


def extract_unsewered_exclusion(provision_text: str) -> Optional[Dict]:
    """
    Detect unsewered land exclusions.

    Patterns:
    - "unsewered land"
    - "not connected to sewer"
    """
    unsewered_match = re.search(
        r'unsewered|'
        r'not\s+connected\s+to.*sewer|'
        r'without.*sewer\s+(?:connection|main)',
        provision_text,
        re.IGNORECASE
    )

    if unsewered_match:
        return {
            'exclusion_type': 'unsewered',
            'applies_to': 'all',
            'confidence': 1.0,
            'matched_pattern': 'unsewered keyword'
        }

    return None


def extract_protected_area_exclusion(provision_text: str) -> Optional[Dict]:
    """
    Detect protected area exclusions.

    Patterns:
    - "conservation zone"
    - "national park"
    - "protected area"
    """
    protected_match = re.search(
        r'conservation\s+zone|'
        r'national\s+park|'
        r'protected\s+area|'
        r'reserve',
        provision_text,
        re.IGNORECASE
    )

    if not protected_match:
        return None

    exclusion_match = re.search(
        r'excluded?|'
        r'prohibit(?:ed)?|'
        r'must\s+not',
        provision_text,
        re.IGNORECASE
    )

    if exclusion_match:
        return {
            'exclusion_type': 'protected_area',
            'applies_to': 'all',
            'confidence': 1.0,
            'matched_pattern': 'protected area + exclusion'
        }

    return None


def extract_reserved_land_exclusion(provision_text: str) -> Optional[Dict]:
    """
    Detect reserved for public purpose exclusions.

    Patterns:
    - "reserved for public purpose"
    - "public infrastructure"
    """
    reserved_match = re.search(
        r'reserved\s+for\s+public\s+purpose|'
        r'public\s+infrastructure|'
        r'earmarked.*public',
        provision_text,
        re.IGNORECASE
    )

    if reserved_match:
        return {
            'exclusion_type': 'reserved_public_purpose',
            'applies_to': 'all',
            'confidence': 1.0,
            'matched_pattern': 'reserved for public purpose'
        }

    return None


# ============================================================
# MAIN EXTRACTION LOGIC
# ============================================================

def extract_all_exclusions(provision_text: str) -> List[Dict]:
    """
    Run all exclusion extractors on a provision.

    Returns:
        List of extracted exclusions (may be empty or contain multiple)
    """
    extractors = [
        extract_heritage_exclusion,
        extract_flood_exclusion,
        extract_bushfire_exclusion,
        extract_acid_sulfate_exclusion,
        extract_aircraft_noise_exclusion,
        extract_threatened_species_exclusion,
        extract_coastal_exclusion,
        extract_unsewered_exclusion,
        extract_protected_area_exclusion,
        extract_reserved_land_exclusion
    ]

    exclusions = []
    for extractor in extractors:
        result = extractor(provision_text)
        if result:
            exclusions.append(result)

    return exclusions


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL)


def fetch_candidate_provisions():
    """
    Fetch SEPP provisions that likely contain exclusion triggers.

    Uses keyword filtering to reduce search space.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Query provisions with exclusion-related keywords
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
          AND (
            provision_text ILIKE '%heritage%item%' OR
            provision_text ILIKE '%heritage%conservation%area%' OR
            provision_text ILIKE '%flood%' OR
            provision_text ILIKE '%bushfire%prone%' OR
            provision_text ILIKE '%acid sulfate%' OR
            provision_text ILIKE '%ANEF%' OR
            provision_text ILIKE '%aircraft%noise%' OR
            provision_text ILIKE '%threatened%species%' OR
            provision_text ILIKE '%coastal%erosion%' OR
            provision_text ILIKE '%unsewered%' OR
            provision_text ILIKE '%protected%area%' OR
            provision_text ILIKE '%reserved%public%' OR
            provision_text ILIKE '%excluded%' OR
            provision_text ILIKE '%must not%' OR
            provision_text ILIKE '%prohibited%'
          )
        ORDER BY d.pdf_name, rp.pdf_page, rp.id
    """

    cur.execute(query)
    provisions = cur.fetchall()

    cur.close()
    conn.close()

    return provisions


def insert_exclusion(provision_id: int, exclusion: Dict, pdf_page: int,
                    provision_text: str, document_name: str):
    """Insert extracted exclusion into database."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO sepp_structured_requirements (
            provision_id,
            requirement_category,
            is_exclusion_trigger,
            exclusion_type,
            applies_to,
            source_pdf_page,
            source_provision_text,
            extraction_confidence,
            source_clause
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (
        provision_id,
        'exclusion',
        True,
        exclusion['exclusion_type'],
        exclusion['applies_to'],
        pdf_page,
        provision_text[:500],  # First 500 chars for reference
        exclusion['confidence'],
        f"{document_name} - Page {pdf_page}"
    ))

    conn.commit()
    cur.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Extract SEPP exclusion triggers')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be extracted without inserting')
    parser.add_argument('--extract', action='store_true',
                       help='Actually extract and insert to database')

    args = parser.parse_args()

    if not args.dry_run and not args.extract:
        print("ERROR: Specify --dry-run or --extract")
        return

    print("=" * 70)
    print("SEPP EXCLUSION TRIGGER EXTRACTION")
    print("=" * 70)
    print()

    # Fetch candidate provisions
    print("Fetching candidate provisions from database...")
    provisions = fetch_candidate_provisions()
    print(f"Found {len(provisions)} candidate provisions")
    print()

    # Extract exclusions
    print("Running deterministic exclusion extractors...")
    print()

    extracted_count = 0
    exclusion_types = {}

    for prov_id, prov_text, pdf_page, doc_name, topic in provisions:
        exclusions = extract_all_exclusions(prov_text)

        if exclusions:
            for exclusion in exclusions:
                exclusion_type = exclusion['exclusion_type']
                exclusion_types[exclusion_type] = exclusion_types.get(exclusion_type, 0) + 1

                print(f"[{extracted_count + 1}] Provision ID {prov_id} (Page {pdf_page})")
                print(f"    Type: {exclusion_type}")
                print(f"    Topic: {topic or 'NULL'}")
                print(f"    Pattern: {exclusion['matched_pattern']}")
                print(f"    Text: {prov_text[:100].replace(chr(10), ' ')}...")
                print()

                if args.extract:
                    insert_exclusion(prov_id, exclusion, pdf_page, prov_text, doc_name)

                extracted_count += 1

    print("=" * 70)
    print("EXTRACTION SUMMARY")
    print("=" * 70)
    print(f"Total exclusions extracted: {extracted_count}")
    print()
    print("By type:")
    for exc_type, count in sorted(exclusion_types.items()):
        print(f"  {exc_type}: {count}")
    print()

    if args.dry_run:
        print("DRY RUN - No data inserted")
    else:
        print(f"Inserted {extracted_count} exclusion triggers to database")
    print()


if __name__ == '__main__':
    main()
