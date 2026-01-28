#!/usr/bin/env python3
"""
Extract provisions from documents table and insert into regulatory_provisions.

This script:
1. Reads the current SEPP Housing full_text from documents table (we've verified it's Dec 2025)
2. Extracts the 7 affected clauses (§15C, §42, §61, §64, §74, §87, §90)
3. Extracts the 3 definitions (complete versions, not truncated)
4. Inserts them as new rows in regulatory_provisions with proper metadata

DRY RUN by default - use --update to actually insert.
"""
import sys, re, hashlib
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
import psycopg2, os, argparse
from dotenv import load_dotenv
load_dotenv()

# Clauses changed by EPIs 512/597/647/684
AFFECTED_CLAUSES = {
    '15C': 'Group homes — development to which division applies',
    '42': 'Complying development — group homes division applicability',
    '61': 'Development in prescribed zones — group homes',
    '64': 'Complying development — group homes standards',
    '74': 'Non-discretionary development standards (parking rates)',
    '87': 'Additional floor space ratios — seniors housing',
    '90': 'Subdivision'
}

AFFECTED_DEFINITIONS = [
    'low and mid rise housing area',
    'low and mid rise housing inner area',
    'low and mid rise housing outer area'
]

def extract_clause(full_text: str, clause_num: str) -> str:
    """Extract a clause from the full text."""
    escaped = re.escape(clause_num)
    # Match: clause number + spaces + uppercase title through to next clause
    pattern = rf'^\s*{escaped}\s+[A-Z].*?(?=^\s*\d+[A-Z]?\s+[A-Z]|\Z)'
    match = re.search(pattern, full_text, re.MULTILINE | re.DOTALL)
    if match:
        return match.group(0).strip()
    return ''

def extract_definition(full_text: str, term: str) -> str:
    """Extract a definition from the full text."""
    escaped = re.escape(term)
    # Match: term + "means" through to next definition or map reference
    pattern = rf'^\s*{escaped}\s+means.*?(?=^\s*[a-z].*\s+means|\n\s*[A-Z][^—]*Map|\Z)'
    match = re.search(pattern, full_text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(0).strip()
    return ''

def main():
    parser = argparse.ArgumentParser(description='Extract provisions from documents table')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be inserted without changing DB')
    parser.add_argument('--update', action='store_true', help='Actually insert provisions')
    args = parser.parse_args()

    if not args.dry_run and not args.update:
        print("Specify --dry-run or --update")
        return

    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()

    # Step 1: Get the current full_text from documents table
    print("Fetching SEPP Housing from documents table...")
    cur.execute("""
    SELECT full_text FROM documents
    WHERE id = 'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation'
    """)
    row = cur.fetchone()
    if not row:
        print("ERROR: Document not found")
        return

    full_text = row[0]
    print(f"  ✓ Retrieved {len(full_text)} chars")

    # Step 2: Extract clauses
    print("\nExtracting clauses...")
    clause_texts = {}
    for clause_num, description in AFFECTED_CLAUSES.items():
        extracted = extract_clause(full_text, clause_num)
        if extracted:
            clause_texts[clause_num] = extracted
            print(f"  ✓ §{clause_num}: {len(extracted)} chars")
        else:
            print(f"  ✗ §{clause_num}: NOT FOUND")

    # Step 3: Extract definitions
    print("\nExtracting definitions...")
    definition_texts = {}
    for term in AFFECTED_DEFINITIONS:
        extracted = extract_definition(full_text, term)
        if extracted:
            definition_texts[term] = extracted
            print(f"  ✓ '{term}': {len(extracted)} chars")
        else:
            print(f"  ✗ '{term}': NOT FOUND")

    # Step 4: Check what exists in regulatory_provisions
    print("\nChecking existing provisions...")
    clause_nums = list(AFFECTED_CLAUSES.keys())
    placeholders_clauses = ','.join(['%s'] * len(clause_nums))

    cur.execute(f"""
    SELECT ref_number, COUNT(*)
    FROM regulatory_provisions
    WHERE document_id LIKE '%%Housing%%2021%%'
      AND ref_number IN ({placeholders_clauses})
    GROUP BY ref_number
    """, clause_nums)

    existing = {row[0]: row[1] for row in cur.fetchall()}
    print(f"  Found {len(existing)} existing clause ref_numbers")
    for ref, count in existing.items():
        print(f"    {ref}: {count} rows")

    # Check for existing definitions separately
    print(f"  Checking definitions...")
    for term in AFFECTED_DEFINITIONS:
        cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE document_id LIKE '%%Housing%%2021%%'
          AND provision_text LIKE %s
        """, (f'{term} means%',))
        count = cur.fetchone()[0]
        if count > 0:
            print(f"    '{term}': {count} rows exist")

    # Step 5: Prepare insertions (clauses as new provisions, definitions as updates)
    to_insert = []
    to_update = []

    for clause_num, text in clause_texts.items():
        if clause_num not in existing:
            to_insert.append({
                'ref_number': clause_num,
                'provision_text': text,
                'section_header': AFFECTED_CLAUSES[clause_num],
                'provision_type': None,  # Most SEPP provisions have NULL type
                'display_priority': 6,  # Same as existing SEPP provisions
                'zone': 'R1',  # Default for SEPP provisions
                'text_hash': hashlib.md5(text.encode()).hexdigest()
            })

    # For definitions: update existing truncated rows
    for term, text in definition_texts.items():
        cur.execute(
            "SELECT id, ref_number, LENGTH(provision_text) as old_len "
            "FROM regulatory_provisions "
            "WHERE document_id LIKE '%%Housing%%2021%%' "
            "  AND provision_text LIKE %s",
            (f'{term} means%',)
        )
        for row in cur.fetchall():
            if row[2] < len(text):  # Only update if current text is shorter (truncated)
                to_update.append({
                    'id': row[0],
                    'ref_number': row[1],
                    'old_len': row[2],
                    'new_text': text,
                    'new_hash': hashlib.md5(text.encode()).hexdigest()
                })

    print(f"\n{'='*70}")
    print(f"Summary: {len(to_insert)} provisions to insert, {len(to_update)} to update")
    print(f"{'='*70}")

    if args.dry_run:
        print("\nDRY RUN - would insert:")
        for item in to_insert:
            print(f"  §{item['ref_number']}: {item['section_header']} ({len(item['provision_text'])} chars)")

        print("\nDRY RUN - would update:")
        for item in to_update:
            print(f"  [{item['ref_number']}] ID {item['id']}: {item['old_len']} → {len(item['new_text'])} chars")

    if args.update:
        print("\nInserting provisions...")
        for item in to_insert:
            cur.execute("""
            INSERT INTO regulatory_provisions
                (document_id, ref_number, provision_text, section_header, provision_type,
                 display_priority, zone, text_hash, is_current, extraction_method)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true, 'manual_Dec2025_update')
            """, (
                'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation',
                item['ref_number'],
                item['provision_text'],
                item['section_header'],
                item['provision_type'],
                item['display_priority'],
                item['zone'],
                item['text_hash']
            ))
            print(f"  ✓ Inserted §{item['ref_number']}")

        print("\nUpdating truncated definitions...")
        for item in to_update:
            cur.execute("""
            UPDATE regulatory_provisions
            SET provision_text = %s,
                text_hash = %s,
                last_updated = CURRENT_TIMESTAMP,
                extraction_method = 'manual_Dec2025_update'
            WHERE id = %s
            """, (item['new_text'], item['new_hash'], item['id']))
            print(f"  ✓ Updated ID {item['id']} (ref {item['ref_number']})")

        conn.commit()
        print(f"\n✓ Changes committed to database")

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
