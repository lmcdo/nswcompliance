"""
Scan Ashfield provisions by page to identify Part boundaries.
Look for mentions of "Part X" in provision text to map page ranges.
"""

import os
import psycopg2
import re
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('PGHOST'),
        database=os.getenv('PGDATABASE'),
        user=os.getenv('PGUSER'),
        password=os.getenv('PGPASSWORD'),
        port=os.getenv('PGPORT')
    )

def identify_boundaries():
    """Identify Part boundaries by scanning provision text."""
    conn = get_db_connection()
    cur = conn.cursor()

    print("=" * 80)
    print("IDENTIFYING ASHFIELD PART BOUNDARIES")
    print("=" * 80)

    # Get all provisions ordered by page
    cur.execute("""
        SELECT id, pdf_page, provision_text
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
        ORDER BY pdf_page, id;
    """)

    provisions = cur.fetchall()
    print(f"\nTotal provisions: {len(provisions)}")
    print(f"Page range: {provisions[0][1]} - {provisions[-1][1]}")

    # Look for Part mentions
    print("\n" + "=" * 80)
    print("SCANNING FOR PART MENTIONS")
    print("=" * 80)

    part_mentions = defaultdict(list)

    # Known Part names from boundaries table
    part_names = {
        'Part 1': ['Ashfield Town Centre', 'Town Centre'],
        'Part 2': ['Ashfield East'],
        'Part 3': ['Ashfield West'],
        'Part 4': ['Croydon Urban Village', 'Croydon'],
        'Part 6': ['Enterprise Zone', 'Parramatta Road', 'Parramatta Rd Corridor'],
        'Part 7': ['Hurlstone Park', 'B6.*Hurlstone'],
        'Part 8': ['Summer Hill Urban Village', 'SummerHill Urban Village'],
        'Part 9': ['Summer Hill Flour Mill', 'Flour Mill'],
        'Part 10': ['Edwards Street', 'B4.*Edwards'],
        'Part 12': ['55.*Smith', 'Smith Street.*Summer Hill'],
        'Part 13': ['120C.*Canterbury', 'Old Canterbury Road'],
    }

    for id, page, text in provisions:
        text_lower = text.lower() if text else ""

        # Check for explicit "Part X" mentions
        explicit_match = re.search(r'part\s+(\d+)', text_lower)
        if explicit_match:
            part_num = explicit_match.group(1)
            part_mentions[f'Part {part_num}'].append((page, id, text[:100]))

        # Check for Part name mentions
        for part, keywords in part_names.items():
            for keyword in keywords:
                if re.search(keyword.lower(), text_lower):
                    part_mentions[part].append((page, id, text[:100]))
                    break

    # Print findings
    print("\nPart mentions found:")
    for part in sorted(part_mentions.keys(), key=lambda x: int(re.search(r'\d+', x).group())):
        mentions = part_mentions[part]
        if mentions:
            pages = [m[0] for m in mentions]
            print(f"\n{part} ({len(mentions)} mentions):")
            print(f"  Page range: {min(pages)} - {max(pages)}")
            print(f"  First mention (page {mentions[0][0]}): {mentions[0][2]}...")
            if len(mentions) > 1:
                print(f"  Last mention (page {mentions[-1][0]}): {mentions[-1][2]}...")

    # Estimate boundaries
    print("\n" + "=" * 80)
    print("ESTIMATED PART BOUNDARIES (based on mentions)")
    print("=" * 80)

    boundaries = {}
    for part, mentions in sorted(part_mentions.items(), key=lambda x: int(re.search(r'\d+', x[0]).group())):
        if mentions:
            pages = [m[0] for m in mentions]
            min_page = min(pages)
            max_page = max(pages)
            boundaries[part] = (min_page, max_page)
            print(f"{part}: Pages {min_page:3d} - {max_page:3d} ({len(mentions):2d} provisions)")

    # Show provision distribution by page ranges
    print("\n" + "=" * 80)
    print("PROVISION DISTRIBUTION BY PAGE")
    print("=" * 80)

    page_groups = defaultdict(list)
    for id, page, text in provisions:
        page_groups[page].append((id, text[:80] if text else "None"))

    print(f"\nShowing pages with provisions (sample every 10 pages):")
    for page in sorted(page_groups.keys()):
        if page % 10 == 0 or page in [min(page_groups.keys()), max(page_groups.keys())]:
            provs = page_groups[page]
            print(f"\nPage {page} ({len(provs)} provisions):")
            for id, text in provs[:2]:  # First 2 per page
                print(f"  ID {id}: {text}...")

    # Suggest manual boundary review points
    print("\n" + "=" * 80)
    print("RECOMMENDED BOUNDARY REVIEW")
    print("=" * 80)
    print("\nBased on mentions, suggested Part boundaries:")

    suggested = {
        'Part 1': (4, 30),
        'Part 2': (31, 58),
        'Part 3': (59, 72),
        'Part 4': (73, 107),
        'Part 6': (108, 152),
        'Part 7': (153, 169),
        'Part 8': (170, 181),
        'Part 9': (182, 192),
        'Part 10': (193, 194),
        'Part 12': (195, 196),
        'Part 13': (197, 197),
    }

    for part, (start, end) in suggested.items():
        actual = boundaries.get(part)
        if actual:
            print(f"{part}: Suggested {start:3d}-{end:3d}, Actual {actual[0]:3d}-{actual[1]:3d}")
        else:
            print(f"{part}: Suggested {start:3d}-{end:3d}, NO MENTIONS FOUND")

    cur.close()
    conn.close()

    return boundaries

if __name__ == '__main__':
    identify_boundaries()
