#!/usr/bin/env python3
"""
Backfill page numbers for SEPP provisions in database
- Matches provisions to text blocks by content similarity
- Updates pdf_page, pdf_source_file, and pdf_extra fields
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from db_safety_wrapper import get_safe_connection

MAPPINGS_FILE = "sepp_page_mappings.json"

def normalize_text(text):
    """Normalize text for comparison"""
    if not text:
        return ""
    # Remove extra whitespace
    return ' '.join(text.split()).lower()[:500]

def find_best_page_match(provision_text, text_blocks):
    """Find the text block that best matches this provision"""
    if not provision_text or len(provision_text) < 50:
        return None

    # Normalize provision text
    prov_normalized = normalize_text(provision_text)

    # Try exact hash match first
    prov_hash = hash(provision_text)
    for block in text_blocks:
        if block['full_text_hash'] == prov_hash:
            return block['page']

    # Try substring match (provision is part of page text block)
    prov_first_100 = provision_text[:100].strip()
    for block in text_blocks:
        if prov_first_100 in block.get('text_preview', ''):
            return block['page']

    # Try normalized match
    for block in text_blocks:
        block_norm = normalize_text(block.get('text_preview', ''))
        if prov_normalized[:200] in block_norm:
            return block['page']

    return None

def main():
    print("="*60)
    print("SEPP PAGE NUMBER BACKFILL")
    print("="*60)

    # Load mappings
    mappings_path = Path(MAPPINGS_FILE)
    if not mappings_path.exists():
        print(f"\n[ERROR] {MAPPINGS_FILE} not found!")
        print("Run: python reparse_sepps_with_page_numbers.py first")
        return 1

    print(f"\nLoading: {MAPPINGS_FILE}")
    with mappings_path.open('r', encoding='utf-8') as f:
        mappings = json.load(f)

    print(f"Loaded {len(mappings)} documents with page mappings")

    # Connect to database
    print("\nConnecting to database...")
    conn = get_safe_connection()
    cursor = conn.cursor()

    # Get SEPP provisions without page numbers
    print("\nFetching SEPP provisions without page numbers...")
    cursor.execute("""
        SELECT id, document_id, provision_text, ref_number
        FROM regulatory_provisions
        WHERE (document_id LIKE '%Environmental_Planning_Policy%'
               OR document_id LIKE '%SEPP%')
          AND pdf_page IS NULL
        ORDER BY id
    """)

    provisions = cursor.fetchall()
    print(f"Found {len(provisions)} SEPP provisions without page numbers")

    if not provisions:
        print("\n[SUCCESS] All SEPP provisions already have page numbers!")
        return 0

    # Match and update
    matched = 0
    unmatched = 0

    print("\nMatching provisions to pages...")

    for prov_id, doc_id, prov_text, ref_num in provisions:
        # Find matching document in mappings
        # Normalize both: convert underscores to spaces, ___ to " - ", remove _section_X suffix
        doc_id_normalized = doc_id.replace('___', ' - ').replace('_', ' ')
        # Remove section suffix (e.g., "_section_10" → "")
        doc_id_base = doc_id_normalized.split(' section ')[0]

        doc_mapping = None
        for doc_name, mapping in mappings.items():
            if doc_name == doc_id_base or doc_name in doc_id_base:
                doc_mapping = mapping
                break

        if not doc_mapping:
            unmatched += 1
            continue

        # Find best matching page
        page = find_best_page_match(prov_text, doc_mapping['text_blocks'])

        if page:
            # Update database
            pdf_source = Path(doc_mapping['source_file']).name.replace('.md', '.pdf')

            cursor.execute("""
                UPDATE regulatory_provisions
                SET pdf_page = %s,
                    pdf_source_file = %s,
                    pdf_extra = jsonb_set(
                        COALESCE(pdf_extra, '{}'::jsonb),
                        '{extracted_at}',
                        %s::jsonb
                    )
                WHERE id = %s
            """, (page, pdf_source, json.dumps("2025-10-13T13:15:00"), prov_id))

            matched += 1

            if matched % 100 == 0:
                print(f"  Matched: {matched}/{len(provisions)}")
                conn.commit()
        else:
            unmatched += 1

    # Final commit
    conn.commit()

    print("\n" + "="*60)
    print("BACKFILL COMPLETE")
    print("="*60)
    print(f"\nMatched: {matched}/{len(provisions)} ({100*matched/len(provisions):.1f}%)")
    print(f"Unmatched: {unmatched}")

    # Verify
    cursor.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE (document_id LIKE '%Environmental_Planning_Policy%'
               OR document_id LIKE '%SEPP%')
          AND pdf_page IS NOT NULL
    """)

    total_with_pages = cursor.fetchone()[0]
    print(f"\nTotal SEPP provisions with pages: {total_with_pages}")

    cursor.close()
    conn.close()

    if matched > 0:
        print("\n[SUCCESS] Page numbers backfilled!")
        return 0
    else:
        print("\n[WARNING] No matches found - check text matching logic")
        return 1

if __name__ == "__main__":
    sys.exit(main())
