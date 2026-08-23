#!/usr/bin/env python3
"""
Import all extracted definitions into the regulatory_definitions table.

This orchestrator:
1. Loads extracted definitions from JSON files
2. Normalizes and deduplicates
3. Links PDF page images
4. Imports to Supabase database
"""

import json
import os
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_batch

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
        'password': os.environ['DB_PASSWORD'],
        'host': 'localhost'
    }
else:
    DB_CONFIG = None

# R2 CDN base URL
R2_CDN_BASE = "https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev"

# PDF image prefixes by source
PDF_IMAGE_PREFIXES = {
    "Marrickville DCP 2011": "marrickville_dcp_definitions",
    "Leichhardt DCP 2013": "leichhardt_dcp_definitions",
    "Ashfield DCP 2016": "ashfield_dcp_definitions",
}


def get_db_connection():
    """Get database connection."""
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    else:
        return psycopg2.connect(**DB_CONFIG)


def load_definitions_from_json(json_path: Path) -> list[dict]:
    """Load definitions from a JSON file."""
    if not json_path.exists():
        print(f"  [SKIP] File not found: {json_path}")
        return []

    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_summary(definition_text: str, max_length: int = 500) -> Optional[str]:
    """
    Generate a short summary of a definition.

    For now, just truncate long definitions. In future, could use LLM.
    """
    if len(definition_text) <= max_length:
        return None  # No summary needed

    # Find a good break point
    truncated = definition_text[:max_length]

    # Try to break at sentence boundary
    last_period = truncated.rfind('.')
    if last_period > max_length * 0.7:
        return truncated[:last_period + 1]

    # Otherwise break at word boundary
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:
        return truncated[:last_space] + "..."

    return truncated + "..."


def get_pdf_page_image_url(source_document: str, page_num: Optional[int]) -> Optional[str]:
    """Get the CDN URL for a PDF page image."""
    if not page_num:
        return None

    prefix = PDF_IMAGE_PREFIXES.get(source_document)
    if not prefix:
        return None

    return f"{R2_CDN_BASE}/pdf-pages/definitions/{prefix}_page_{page_num}.png"


def deduplicate_definitions(definitions: list[dict]) -> list[dict]:
    """
    Remove duplicates based on (term_normalized, source_document).

    Keep the one with higher confidence or longer definition.
    """
    seen = {}

    for defn in definitions:
        key = (defn['term_normalized'], defn['source_document'])

        if key in seen:
            existing = seen[key]
            # Keep the one with higher confidence
            if defn.get('extraction_confidence', 1.0) > existing.get('extraction_confidence', 1.0):
                seen[key] = defn
            # Or longer definition if same confidence
            elif len(defn['definition_text']) > len(existing['definition_text']):
                seen[key] = defn
        else:
            seen[key] = defn

    return list(seen.values())


def import_to_database(definitions: list[dict], dry_run: bool = False) -> tuple[int, int]:
    """
    Import definitions to the database.

    Returns:
        Tuple of (inserted_count, skipped_count)
    """
    if dry_run:
        print("  [DRY RUN] Would import definitions to database")
        return len(definitions), 0

    conn = get_db_connection()
    conn.autocommit = False  # Use explicit transactions
    cur = conn.cursor()

    # Prepare insert statement with ON CONFLICT
    insert_sql = """
        INSERT INTO regulatory_definitions (
            term,
            term_normalized,
            definition_text,
            definition_summary,
            source_document,
            source_clause,
            legislation_type,
            lga,
            former_council,
            pdf_page,
            pdf_source_file,
            pdf_page_image_url,
            domain_tags,
            extraction_confidence,
            manual_verified
        ) VALUES (
            %(term)s,
            %(term_normalized)s,
            %(definition_text)s,
            %(definition_summary)s,
            %(source_document)s,
            %(source_clause)s,
            %(legislation_type)s,
            %(lga)s,
            %(former_council)s,
            %(pdf_page)s,
            %(pdf_source_file)s,
            %(pdf_page_image_url)s,
            %(domain_tags)s,
            %(extraction_confidence)s,
            %(manual_verified)s
        )
        ON CONFLICT (term_normalized, source_document)
        DO UPDATE SET
            term = EXCLUDED.term,
            definition_text = EXCLUDED.definition_text,
            definition_summary = EXCLUDED.definition_summary,
            source_clause = EXCLUDED.source_clause,
            pdf_page = EXCLUDED.pdf_page,
            pdf_page_image_url = EXCLUDED.pdf_page_image_url,
            domain_tags = EXCLUDED.domain_tags,
            extraction_confidence = EXCLUDED.extraction_confidence,
            updated_at = NOW()
    """

    inserted = 0
    skipped = 0
    errors = []

    for defn in definitions:
        try:
            # Prepare record
            record = {
                'term': defn['term'],
                'term_normalized': defn['term_normalized'],
                'definition_text': defn['definition_text'],
                'definition_summary': generate_summary(defn['definition_text']),
                'source_document': defn['source_document'],
                'source_clause': defn.get('source_clause'),
                'legislation_type': defn['legislation_type'],
                'lga': defn.get('lga'),
                'former_council': defn.get('former_council'),
                'pdf_page': defn.get('pdf_page'),
                'pdf_source_file': defn.get('pdf_source_file'),
                'pdf_page_image_url': defn.get('pdf_page_image_url') or get_pdf_page_image_url(
                    defn['source_document'], defn.get('pdf_page')
                ),
                'domain_tags': defn.get('domain_tags', []),
                'extraction_confidence': defn.get('extraction_confidence', 1.0),
                'manual_verified': False,
            }

            cur.execute(insert_sql, record)
            inserted += 1

            # Commit every 50 records
            if inserted % 50 == 0:
                conn.commit()
                print(f"    Imported {inserted} definitions...")

        except Exception as e:
            # Rollback the failed transaction and continue
            conn.rollback()
            errors.append(f"{defn['term']}: {e}")
            skipped += 1

    # Final commit
    conn.commit()

    cur.close()
    conn.close()

    # Print errors at the end (not all of them, just first 5)
    if errors:
        print(f"    First {min(5, len(errors))} errors:")
        for err in errors[:5]:
            print(f"      {err}")

    return inserted, skipped


def main(dry_run: bool = False):
    """Import all definitions to database."""
    print("=" * 70)
    print("IMPORT REGULATORY DEFINITIONS")
    print("=" * 70)
    print()

    if dry_run:
        print("[DRY RUN MODE - No database changes will be made]")
        print()

    all_definitions = []

    # Load DCP definitions
    print("Loading DCP definitions...")
    dcp_defs = load_definitions_from_json(DEFINITIONS_OUTPUT / "dcp_definitions.json")
    print(f"  Loaded: {len(dcp_defs)} definitions")
    all_definitions.extend(dcp_defs)

    # Load SEPP Housing definitions
    print("Loading SEPP Housing definitions...")
    sepp_defs = load_definitions_from_json(DEFINITIONS_OUTPUT / "sepp_housing_definitions.json")
    print(f"  Loaded: {len(sepp_defs)} definitions")
    all_definitions.extend(sepp_defs)

    # Load Standard Instrument LEP definitions
    print("Loading Standard Instrument LEP definitions...")
    si_lep_defs = load_definitions_from_json(DEFINITIONS_OUTPUT / "si_lep_definitions.json")
    print(f"  Loaded: {len(si_lep_defs)} definitions")
    all_definitions.extend(si_lep_defs)

    print()
    print(f"Total loaded: {len(all_definitions)}")

    # Deduplicate
    print("Deduplicating...")
    unique_definitions = deduplicate_definitions(all_definitions)
    print(f"  Unique definitions: {len(unique_definitions)}")

    # Import to database
    print()
    print("Importing to database...")
    inserted, skipped = import_to_database(unique_definitions, dry_run=dry_run)
    print(f"  Inserted/Updated: {inserted}")
    print(f"  Skipped (errors): {skipped}")

    print()
    print("=" * 70)
    print("COMPLETE")
    print("=" * 70)

    # Summary by source
    print()
    print("By source:")
    by_source = {}
    for d in unique_definitions:
        key = d['source_document']
        by_source[key] = by_source.get(key, 0) + 1
    for source, count in sorted(by_source.items()):
        print(f"  {source}: {count}")

    # Summary by legislation type
    print()
    print("By legislation type:")
    by_type = {}
    for d in unique_definitions:
        key = d['legislation_type']
        by_type[key] = by_type.get(key, 0) + 1
    for leg_type, count in sorted(by_type.items()):
        print(f"  {leg_type}: {count}")


if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv

    main(dry_run=dry_run)
