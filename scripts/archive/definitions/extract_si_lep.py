#!/usr/bin/env python3
"""
Extract Standard Instrument LEP Dictionary definitions.

The Standard Instrument (Local Environmental Plans) Order 2006 defines
standard terms used across all NSW LEPs. We extract these from the
Inner West LEP 2022 provisions which use the standard dictionary.

This approach uses the database (which has the Inner West LEP 2022
provisions already extracted) rather than web scraping.
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

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DB_CONFIG = {
        'dbname': 'nsw_planning',
        'user': 'postgres',
        'password': 'Sturt1802!',
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


def get_db_connection():
    """Get database connection."""
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    else:
        return psycopg2.connect(**DB_CONFIG)


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
        'heritage': ['heritage', 'conservation', 'historic', 'aboriginal'],
        'parking': ['parking', 'car space', 'vehicle', 'motor'],
        'setback': ['setback', 'boundary', 'frontage'],
        'flood': ['flood', 'inundation', 'floodplain', 'coastal'],
        'housing': ['dwelling', 'residential', 'habitable', 'bedroom', 'living', 'apartment'],
        'accessibility': ['accessible', 'disability', 'wheelchair'],
        'building': ['building', 'storey', 'floor', 'ceiling', 'wall', 'structure'],
        'commercial': ['commercial', 'retail', 'shop', 'business', 'office'],
        'industrial': ['industrial', 'warehouse', 'factory', 'manufacturing'],
        'rural': ['rural', 'agricultural', 'farm', 'primary production'],
        'environmental': ['environment', 'ecological', 'conservation', 'wetland', 'waterway'],
        'infrastructure': ['infrastructure', 'road', 'railway', 'utility', 'drainage'],
    }

    for tag, keywords in tag_keywords.items():
        if any(kw in combined for kw in keywords):
            tags.append(tag)

    return tags


def parse_definition_provision(provision_text: str) -> Optional[tuple]:
    """
    Parse a provision containing a definition.

    Standard Instrument format: "term means definition"
    """
    text = provision_text.strip()

    # Skip very short provisions
    if len(text) < 15:
        return None

    # Pattern 1: "term means definition"
    match = re.match(r'^([a-zA-Z][a-zA-Z\s\-]+?)\s+means\s+(.+)', text, re.IGNORECASE | re.DOTALL)
    if match:
        term = match.group(1).strip()
        definition = match.group(2).strip()

        # Skip if term is too long (probably not a definition)
        if len(term) > 60:
            return None

        return term, definition

    # Pattern 2: "term—see definition" or cross-reference
    match = re.match(r'^([a-zA-Z][a-zA-Z\s\-]+?)[—–]\s*see\s+(.+)', text, re.IGNORECASE | re.DOTALL)
    if match:
        term = match.group(1).strip()
        definition = f"see {match.group(2).strip()}"
        if len(term) > 60:
            return None
        return term, definition

    return None


def extract_si_lep_definitions() -> list[Definition]:
    """Extract Standard Instrument LEP definitions from Inner West LEP 2022."""
    definitions = []

    conn = get_db_connection()
    cur = conn.cursor()

    # Query for definition provisions from Inner West LEP 2022
    # These use the Standard Instrument dictionary
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
        AND provision_text ILIKE %s
        ORDER BY provision_text;
    """
    cur.execute(query, (
        'Inner_West_Local_Environmental_Plan_2022%',
        '% means %',
    ))

    rows = cur.fetchall()
    print(f"  Found {len(rows)} provisions with definitions in Inner West LEP 2022")

    seen_terms = set()  # Track unique terms

    for row in rows:
        prov_id, provision_text, ref_number, pdf_page, pdf_image_url, document_id, section_header = row

        if not provision_text:
            continue

        # Try to parse as definition
        parsed = parse_definition_provision(provision_text)

        if parsed:
            term, definition_text = parsed

            # Normalize term for deduplication
            term_norm = normalize_term(term)

            # Skip duplicates and very short terms
            if term_norm in seen_terms or len(term_norm) < 3:
                continue

            seen_terms.add(term_norm)

            defn = Definition(
                term=term,
                term_normalized=term_norm,
                definition_text=definition_text,
                source_document="Inner West LEP 2022 (Standard Instrument)",
                source_clause="Dictionary",
                legislation_type="SI_LEP",
                lga="Inner West",
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
    """Extract Standard Instrument LEP definitions."""
    print("=" * 70)
    print("EXTRACT STANDARD INSTRUMENT LEP DICTIONARY")
    print("=" * 70)
    print()

    # Create output directory
    DEFINITIONS_OUTPUT.mkdir(parents=True, exist_ok=True)

    print("Querying Inner West LEP 2022 for Standard Instrument definitions...")
    definitions = extract_si_lep_definitions()

    print(f"  Extracted: {len(definitions)} unique definitions")

    if definitions:
        # Show samples
        print()
        print("Sample definitions:")
        for d in definitions[:5]:
            print(f"  - {d.term}: {d.definition_text[:60]}...")

    # Output to JSON
    output_path = DEFINITIONS_OUTPUT / "si_lep_definitions.json"
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

