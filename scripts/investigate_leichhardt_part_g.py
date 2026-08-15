"""
Investigate Leichhardt "Part G Section 1-12" document provisions.
Find patterns to map the 447 provisions to specific precincts.
"""

import os
import psycopg2
import re
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')

def get_db_connection():
    """Create database connection using environment variables."""
    return psycopg2.connect(
        host=os.getenv('PGHOST'),
        database=os.getenv('PGDATABASE'),
        user=os.getenv('PGUSER'),
        password=os.getenv('PGPASSWORD'),
        port=os.getenv('PGPORT')
    )

# Leichhardt precinct names from boundaries table
LEICHHARDT_PRECINCTS = {
    'C2.2.1.1': 'Young Street',
    'C2.2.1.2': 'Annandale Street',
    'C2.2.1.3': 'Johnston Street',
    'C2.2.1.4': 'Booth Street',
    'C2.2.1.5': 'Trafalgar Street',
    'C2.2.1.6': 'Nelson Street',
    'C2.2.1.7': 'Parramatta Road Commercial',
    'C2.2.1.8': 'Camperdown',
    'C2.2.2.1': 'Darling Street',
    'C2.2.2.2': 'Balmain East',
    'C2.2.2.3': 'Gladstone Park',
    'C2.2.2.4': "The Valley 'Balmain'",
    'C2.2.2.5': 'Mort Bay',
    'C2.2.2.6': 'Birchgrove',
    'C2.2.3.1': 'Excelsior Estate',
    'C2.2.3.2': 'West Leichhardt',
    'C2.2.3.3': 'Piperston',
    'C2.2.3.4': 'Helsarmel',
    'C2.2.3.5': 'Leichhardt Commercial',
    'C2.2.4.1': 'Catherine Street',
    'C2.2.4.2': 'Nanny Goat Hill',
    'C2.2.4.3': 'Leichhardt Park',
    'C2.2.4.4': 'Iron Cove Parklands',
    'C2.2.5.1': "The Valley 'Rozelle'",
    'C2.2.5.2': 'Easton Park',
    'C2.2.5.3': 'Callan Park',
    'C2.2.5.4': 'Iron Cove',
    'C2.2.5.5': 'Rozelle Commercial',
    'C2.2.5.6': 'Robert Street Industrial',
}

def investigate():
    """Investigate Part G Section 1-12 provisions."""
    conn = get_db_connection()
    cur = conn.cursor()

    print("=" * 80)
    print("INVESTIGATING LEICHHARDT PART G SECTION 1-12 PROVISIONS")
    print("=" * 80)

    # Get all provisions from this document
    cur.execute("""
        SELECT id, v2_dcp_part, provision_text, pdf_page
        FROM regulatory_provisions
        WHERE document_id = 'Leichhardt DCP 2013 - 12 - Part G Section 1-12 - Amdt 19 - Nov 2023'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
        ORDER BY pdf_page, id;
    """)

    provisions = cur.fetchall()
    print(f"\nTotal provisions: {len(provisions)}")

    if not provisions:
        print("No provisions found!")
        return

    # Get page range
    pages = [p[3] for p in provisions if p[3] is not None]
    if pages:
        print(f"Page range: {min(pages)} - {max(pages)}")
    else:
        print("Page range: No pdf_page data available")

    # Try to find neighbourhood names in text
    print("\n" + "=" * 80)
    print("SEARCHING FOR PRECINCT NAMES IN PROVISION TEXT")
    print("=" * 80)

    matches = {precinct_id: [] for precinct_id in LEICHHARDT_PRECINCTS.keys()}
    unmatched = []

    for id, part, text, pdf_page in provisions:
        text_lower = text.lower() if text else ""
        matched = False

        for precinct_id, name in LEICHHARDT_PRECINCTS.items():
            # Try exact name match
            if name.lower() in text_lower:
                matches[precinct_id].append((id, pdf_page, text[:100]))
                matched = True
                break

            # Try partial matches (e.g., "Young Street" matches "Young St")
            name_words = name.lower().split()
            if len(name_words) >= 2:
                # Match first word (e.g., "Young" from "Young Street")
                if name_words[0] in text_lower and len(name_words[0]) > 4:
                    matches[precinct_id].append((id, pdf_page, text[:100]))
                    matched = True
                    break

        if not matched:
            unmatched.append((id, pdf_page, text[:100] if text else "None"))

    # Print results
    print("\nProvisions matched by text content:")
    total_matched = 0
    for precinct_id in sorted(matches.keys()):
        if matches[precinct_id]:
            count = len(matches[precinct_id])
            total_matched += count
            name = LEICHHARDT_PRECINCTS[precinct_id]
            print(f"\n{precinct_id} ({name}): {count} provisions")
            # Show first 2 samples
            for id, page, text in matches[precinct_id][:2]:
                print(f"  ID {id} (page {page}): {text}...")

    print(f"\n\nTotal matched: {total_matched}/{len(provisions)} ({total_matched/len(provisions)*100:.1f}%)")
    print(f"Unmatched: {len(unmatched)} provisions")

    if unmatched:
        print("\nFirst 10 unmatched provisions:")
        for id, page, text in unmatched[:10]:
            print(f"  ID {id} (page {page}): {text}...")

    # Analyze page distribution
    print("\n" + "=" * 80)
    print("ANALYZING PAGE DISTRIBUTION")
    print("=" * 80)

    print("\nProvisions by page (first 50 pages):")
    page_groups = {}
    for id, part, text, pdf_page in provisions:
        if pdf_page not in page_groups:
            page_groups[pdf_page] = []
        page_groups[pdf_page].append((id, text[:80] if text else "None"))

    for page in sorted(page_groups.keys())[:50]:
        provs = page_groups[page]
        print(f"\nPage {page} ({len(provs)} provisions):")
        for id, text in provs[:2]:  # First 2 per page
            print(f"  ID {id}: {text}...")

    cur.close()
    conn.close()

if __name__ == '__main__':
    investigate()
