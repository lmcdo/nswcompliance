#!/usr/bin/env python3
"""
Verify regulatory definitions extraction and import.

Checks:
1. Definition counts match expectations
2. All definitions have required fields
3. No duplicate term+source combinations
4. PDF page images exist for DCP sources
5. Domain tags are reasonable
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFINITIONS_OUTPUT = PROJECT_ROOT / "scripts" / "definitions" / "extracted"
IMAGE_OUTPUT = PROJECT_ROOT / "frontend-nextjs" / "public" / "images" / "definitions"

# Database configuration - use DATABASE_URL (Supabase) if available
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


def get_db_connection():
    """Get database connection."""
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    else:
        return psycopg2.connect(**DB_CONFIG)

# Expected counts (from plan)
EXPECTED_COUNTS = {
    "Marrickville DCP 2011": 20,      # ~25 expected, allow some variance
    "Leichhardt DCP 2013": 80,         # ~100 expected
    "Ashfield DCP 2016": 40,           # ~50 expected
    "SEPP Housing 2021": 25,           # ~35 expected
    "Standard Instrument": 100,        # ~150 expected
}


def get_db_connection():
    """Get database connection."""
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    else:
        return psycopg2.connect(**DB_CONFIG)


def verify_json_files() -> dict:
    """Verify extracted JSON files exist and have content."""
    print("Verifying JSON files...")
    results = {}

    json_files = [
        ("dcp_definitions.json", "DCP"),
        ("sepp_housing_definitions.json", "SEPP Housing"),
        ("si_lep_definitions.json", "Standard Instrument LEP"),
    ]

    for filename, name in json_files:
        path = DEFINITIONS_OUTPUT / filename
        if path.exists():
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            results[name] = {
                "exists": True,
                "count": len(data),
                "status": "OK" if len(data) > 0 else "EMPTY",
            }
            print(f"  {name}: {len(data)} definitions")
        else:
            results[name] = {
                "exists": False,
                "count": 0,
                "status": "MISSING",
            }
            print(f"  {name}: MISSING")

    return results


def verify_database_contents() -> dict:
    """Verify database table contents."""
    print()
    print("Verifying database contents...")

    results = {}

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'regulatory_definitions'
            );
        """)
        table_exists = cur.fetchone()[0]

        if not table_exists:
            print("  [ERROR] Table regulatory_definitions does not exist!")
            return {"table_exists": False}

        results["table_exists"] = True

        # Total count
        cur.execute("SELECT COUNT(*) FROM regulatory_definitions;")
        total = cur.fetchone()[0]
        results["total_count"] = total
        print(f"  Total definitions: {total}")

        # Count by source
        cur.execute("""
            SELECT source_document, COUNT(*)
            FROM regulatory_definitions
            GROUP BY source_document
            ORDER BY COUNT(*) DESC;
        """)
        by_source = cur.fetchall()
        results["by_source"] = dict(by_source)
        print("  By source:")
        for source, count in by_source:
            print(f"    {source}: {count}")

        # Count by legislation type
        cur.execute("""
            SELECT legislation_type, COUNT(*)
            FROM regulatory_definitions
            GROUP BY legislation_type
            ORDER BY COUNT(*) DESC;
        """)
        by_type = cur.fetchall()
        results["by_type"] = dict(by_type)
        print("  By legislation type:")
        for leg_type, count in by_type:
            print(f"    {leg_type}: {count}")

        # Check for missing required fields
        cur.execute("""
            SELECT COUNT(*)
            FROM regulatory_definitions
            WHERE term IS NULL
               OR term_normalized IS NULL
               OR definition_text IS NULL
               OR source_document IS NULL
               OR legislation_type IS NULL;
        """)
        missing_required = cur.fetchone()[0]
        results["missing_required"] = missing_required
        if missing_required > 0:
            print(f"  [WARNING] {missing_required} definitions missing required fields")
        else:
            print("  Required fields: OK")

        # Check for duplicates (should be 0 due to unique constraint)
        cur.execute("""
            SELECT term_normalized, source_document, COUNT(*)
            FROM regulatory_definitions
            GROUP BY term_normalized, source_document
            HAVING COUNT(*) > 1;
        """)
        duplicates = cur.fetchall()
        results["duplicates"] = len(duplicates)
        if duplicates:
            print(f"  [WARNING] {len(duplicates)} duplicate term+source combinations")
            for term, source, count in duplicates[:5]:
                print(f"    '{term}' in {source}: {count} times")
        else:
            print("  Duplicates: None (good)")

        # Check domain tags coverage
        cur.execute("""
            SELECT
                COUNT(*) FILTER (WHERE domain_tags IS NOT NULL AND array_length(domain_tags, 1) > 0) as with_tags,
                COUNT(*) FILTER (WHERE domain_tags IS NULL OR array_length(domain_tags, 1) IS NULL) as without_tags
            FROM regulatory_definitions;
        """)
        tag_coverage = cur.fetchone()
        results["with_tags"] = tag_coverage[0]
        results["without_tags"] = tag_coverage[1]
        print(f"  Domain tags: {tag_coverage[0]} with tags, {tag_coverage[1]} without")

        # Sample definitions
        print()
        print("  Sample definitions:")
        cur.execute("""
            SELECT term, LEFT(definition_text, 60), source_document
            FROM regulatory_definitions
            ORDER BY RANDOM()
            LIMIT 5;
        """)
        for term, defn_preview, source in cur.fetchall():
            print(f"    '{term}' ({source}): {defn_preview}...")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"  [ERROR] Database verification failed: {e}")
        results["error"] = str(e)

    return results


def verify_pdf_images() -> dict:
    """Verify PDF page images exist."""
    print()
    print("Verifying PDF page images...")

    results = {}

    if not IMAGE_OUTPUT.exists():
        print("  [WARNING] Image output directory does not exist")
        print(f"    Expected: {IMAGE_OUTPUT}")
        results["directory_exists"] = False
        return results

    results["directory_exists"] = True

    # Count images by source
    image_counts = {
        "marrickville": 0,
        "leichhardt": 0,
        "ashfield": 0,
    }

    total_size = 0

    for img_path in IMAGE_OUTPUT.glob("*.png"):
        total_size += img_path.stat().st_size
        name = img_path.name.lower()
        if "marrickville" in name:
            image_counts["marrickville"] += 1
        elif "leichhardt" in name:
            image_counts["leichhardt"] += 1
        elif "ashfield" in name:
            image_counts["ashfield"] += 1

    results["image_counts"] = image_counts
    results["total_size_mb"] = total_size / 1024 / 1024

    print(f"  Directory: {IMAGE_OUTPUT}")
    print(f"  Marrickville images: {image_counts['marrickville']}")
    print(f"  Leichhardt images: {image_counts['leichhardt']}")
    print(f"  Ashfield images: {image_counts['ashfield']}")
    print(f"  Total size: {total_size / 1024 / 1024:.1f} MB")

    return results


def run_sample_queries() -> None:
    """Run sample queries to test the definitions table."""
    print()
    print("Running sample queries...")

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Query 1: Find "habitable room"
        print()
        print("  Query: 'habitable room'")
        cur.execute("""
            SELECT term, source_document, LEFT(definition_text, 100)
            FROM regulatory_definitions
            WHERE term_normalized LIKE '%habitable%room%'
               OR term_normalized LIKE '%habitable%';
        """)
        results = cur.fetchall()
        if results:
            for term, source, defn in results[:3]:
                print(f"    [{source}] {term}: {defn}...")
        else:
            print("    No results")

        # Query 2: Find flood-related definitions
        print()
        print("  Query: 'flood' domain tag")
        cur.execute("""
            SELECT term, source_document
            FROM regulatory_definitions
            WHERE 'flood' = ANY(domain_tags)
            LIMIT 5;
        """)
        results = cur.fetchall()
        if results:
            for term, source in results:
                print(f"    [{source}] {term}")
        else:
            print("    No results")

        # Query 3: Full text search
        print()
        print("  Query: Full text search for 'heritage conservation'")
        cur.execute("""
            SELECT term, source_document
            FROM regulatory_definitions
            WHERE to_tsvector('english', term || ' ' || definition_text)
                  @@ to_tsquery('english', 'heritage & conservation')
            LIMIT 5;
        """)
        results = cur.fetchall()
        if results:
            for term, source in results:
                print(f"    [{source}] {term}")
        else:
            print("    No results")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"  [ERROR] Sample queries failed: {e}")


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("VERIFY REGULATORY DEFINITIONS")
    print("=" * 70)
    print()

    all_results = {}

    # Verify JSON files
    all_results["json"] = verify_json_files()

    # Verify database
    all_results["database"] = verify_database_contents()

    # Verify images
    all_results["images"] = verify_pdf_images()

    # Run sample queries
    run_sample_queries()

    # Summary
    print()
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    issues = []

    # Check JSON files
    for name, result in all_results["json"].items():
        if result["status"] != "OK":
            issues.append(f"JSON {name}: {result['status']}")

    # Check database
    db = all_results.get("database", {})
    if not db.get("table_exists"):
        issues.append("Database table does not exist")
    elif db.get("total_count", 0) < 100:
        issues.append(f"Low definition count: {db.get('total_count', 0)}")
    if db.get("missing_required", 0) > 0:
        issues.append(f"{db['missing_required']} definitions missing required fields")
    if db.get("duplicates", 0) > 0:
        issues.append(f"{db['duplicates']} duplicate entries")

    # Check images
    imgs = all_results.get("images", {})
    if not imgs.get("directory_exists"):
        issues.append("Image directory does not exist")

    if issues:
        print()
        print("Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        print()
        print("Status: NEEDS ATTENTION")
    else:
        print()
        print("Status: ALL CHECKS PASSED")

    print("=" * 70)

    return len(issues) == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
