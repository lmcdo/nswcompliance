#!/usr/bin/env python3
"""
Extract SEPP Housing 2021 Dictionary (Schedule 10) definitions.

Queries existing regulatory_provisions table for Schedule 10 (Dictionary)
provisions and extracts structured definitions.
"""

import json
import os
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict, field
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFINITIONS_OUTPUT = PROJECT_ROOT / "scripts" / "definitions" / "extracted"

# Database configuration (use Supabase connection string)
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback to local if no DATABASE_URL
if not DATABASE_URL:
    DB_CONFIG = {
        'dbname': 'nsw_planning',
        'user': 'postgres',
        'password': os.environ['DB_PASSWORD'],
        'host': 'localhost'
    }
else:
    DB_CONFIG = None


@dataclass
class Definition:
    """Represents a single definition."""
    term: str
    term_normalized: str
    definition_text: str
    source_document: str
    source_clause: str
    legislation_type: str
    lga: Optional[str]
    former_council: Optional[str]
    pdf_page: Optional[int] = None
    pdf_source_file: Optional[str] = None
    pdf_page_image_url: Optional[str] = None
    domain_tags: list = field(default_factory=list)
    extraction_confidence: float = 1.0


def normalize_term(term: str) -> str:
    """Normalize a term for matching."""
    normalized = term.lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = normalized.strip('.')
    return normalized


def infer_domain_tags(term: str, definition: str) -> list:
    """Infer domain tags based on content."""
    tags = []
    combined = (term + " " + definition).lower()

    tag_keywords = {
        'heritage': ['heritage', 'conservation', 'historic'],
        'parking': ['parking', 'car space', 'vehicle'],
        'setback': ['setback', 'boundary', 'frontage'],
        'flood': ['flood', 'inundation', 'floodplain'],
        'housing': ['dwelling', 'residential', 'habitable', 'bedroom', 'living'],
        'accessibility': ['accessible', 'disability', 'wheelchair'],
        'building': ['building', 'storey', 'floor', 'ceiling', 'wall'],
    }

    for tag, keywords in tag_keywords.items():
        if any(kw in combined for kw in keywords):
            tags.append(tag)

    return tags


def parse_schedule_10_provision(provision_text: str, ref_number: str) -> Optional[tuple]:
    """
    Parse a Schedule 10 dictionary provision into term and definition.

    Schedule 10 format varies:
    - "term means definition"
    - "(1) term means definition"
    - "term—see definition"
    """
    text = provision_text.strip()

    # Remove leading numbering like "(1)" or "1."
    text = re.sub(r'^\(\d+\)\s*', '', text)
    text = re.sub(r'^\d+\.\s*', '', text)

    # Pattern 1: "term means definition"
    match = re.match(r'^([^—–]+?)\s+means\s+(.+)', text, re.IGNORECASE | re.DOTALL)
    if match:
        term = match.group(1).strip().strip('"').strip("'")
        definition = match.group(2).strip()
        return term, definition

    # Pattern 2: "term—definition" or "term–definition"
    match = re.match(r'^([^—–]+)[—–]\s*(.+)', text, re.DOTALL)
    if match:
        term = match.group(1).strip().strip('"').strip("'")
        definition = match.group(2).strip()
        # Handle "see X" references
        if definition.lower().startswith('see '):
            definition = f"See {definition[4:]}"
        return term, definition

    # Pattern 3: "term has the same meaning as..."
    match = re.match(r'^([^—–]+?)\s+has\s+the\s+same\s+meaning\s+as\s+(.+)', text, re.IGNORECASE | re.DOTALL)
    if match:
        term = match.group(1).strip().strip('"').strip("'")
        definition = f"has the same meaning as {match.group(2).strip()}"
        return term, definition

    return None


def get_db_connection():
    """Get database connection."""
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    else:
        return psycopg2.connect(**DB_CONFIG)


def extract_sepp_housing_definitions() -> list[Definition]:
    """Extract definitions from SEPP Housing 2021 Schedule 10."""
    definitions = []

    conn = get_db_connection()
    cur = conn.cursor()

    # First check database connectivity
    cur.execute("SELECT COUNT(*) FROM regulatory_provisions")
    total = cur.fetchone()[0]
    print(f"  Total provisions in database: {total}")

    # Query for Dictionary provisions from SEPP Housing
    # The data uses document_id like: State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation
    # Note: Use %s placeholders for LIKE patterns to avoid psycopg2 escaping issues
    query = """
        SELECT
            id,
            provision_text,
            ref_number,
            pdf_page,
            pdf_page_image_url,
            document_id,
            section_header
        FROM regulatory_provisions
        WHERE document_id LIKE %s
        AND (
            section_header ILIKE %s
            OR section_header ILIKE %s
            OR provision_text ILIKE %s
        )
        ORDER BY ref_number, id;
    """
    cur.execute(query, (
        'State_Environmental_Planning_Policy_%Housing%2021%',
        '%Dictionary%',
        '%Definitions%',
        '% means %',
    ))

    rows = cur.fetchall()
    print(f"  Found {len(rows)} provisions with definitions in database")

    for row in rows:
        prov_id, provision_text, ref_number, pdf_page, pdf_image_url, document_id, section_header = row

        if not provision_text:
            continue

        # Try to parse as definition
        parsed = parse_schedule_10_provision(provision_text, ref_number or "")

        if parsed:
            term, definition_text = parsed

            # Skip if term is too short or looks like a number/reference
            if len(term) < 2 or term.isdigit():
                continue

            defn = Definition(
                term=term,
                term_normalized=normalize_term(term),
                definition_text=definition_text,
                source_document="SEPP Housing 2021",
                source_clause="Schedule 10 Dictionary",
                legislation_type="SEPP",
                lga=None,  # State-wide
                former_council=None,
                pdf_page=pdf_page,
                pdf_page_image_url=pdf_image_url,
                domain_tags=infer_domain_tags(term, definition_text),
            )
            definitions.append(defn)

    cur.close()
    conn.close()

    return definitions


def main():
    """Extract SEPP Housing 2021 definitions."""
    print("=" * 70)
    print("EXTRACT SEPP HOUSING 2021 DICTIONARY")
    print("=" * 70)
    print()

    # Create output directory
    DEFINITIONS_OUTPUT.mkdir(parents=True, exist_ok=True)

    print("Querying regulatory_provisions for Schedule 10...")
    definitions = extract_sepp_housing_definitions()

    print(f"  Extracted: {len(definitions)} definitions")

    if definitions:
        # Show samples
        print()
        print("Sample definitions:")
        for d in definitions[:3]:
            print(f"  - {d.term}: {d.definition_text[:60]}...")

    # Output to JSON
    output_path = DEFINITIONS_OUTPUT / "sepp_housing_definitions.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(
            [asdict(d) for d in definitions],
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 70)
    print(f"Total definitions extracted: {len(definitions)}")
    print(f"Output: {output_path}")
    print("=" * 70)

    return definitions


if __name__ == "__main__":
    main()
