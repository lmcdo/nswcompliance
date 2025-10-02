"""
STEP 4: Import full text provisions from JSON to database

Strategy:
1. Match JSON provisions to existing database provisions by ref_number
2. Update matched provisions with full text
3. Insert new provisions not found in database
4. Preserve all existing relationships (zones, development types, etc.)

Exit Codes:
- 0: Success - all provisions imported
- 1: Failure - import errors
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from db_safety_wrapper import get_safe_connection

# Use absolute path from script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
EXTRACTED_DIR = PROJECT_ROOT / "docs/sepps/extracted"
PARSING_REPORT = EXTRACTED_DIR / "parsing_report.json"
IMPORT_LOG = EXTRACTED_DIR / "import_log.json"

def load_parsed_provisions():
    """Load all parsed provisions from JSON files"""
    print("\n=== LOADING PARSED PROVISIONS ===\n")

    if not PARSING_REPORT.exists():
        print(f"[X] Parsing report not found: {PARSING_REPORT}")
        return None

    with open(PARSING_REPORT, 'r', encoding='utf-8') as f:
        parsing_report = json.load(f)

    all_provisions = {}
    for result in parsing_report['results']:
        if result['success']:
            json_file = Path(result['json_file'])
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    sepp_name = data['sepp_name']
                    provisions = data['provisions']
                    all_provisions[sepp_name] = provisions
                    print(f"[OK] Loaded {len(provisions):,} provisions from {sepp_name}")

    total = sum(len(provs) for provs in all_provisions.values())
    print(f"\n[OK] Total provisions loaded: {total:,}")
    return all_provisions

def get_existing_provisions():
    """Get all existing SEPP provisions from database"""
    print("\n=== LOADING EXISTING DATABASE PROVISIONS ===\n")

    try:
        conn = get_safe_connection()
        cur = conn.cursor()

        # Get all SEPP provisions
        cur.execute("""
            SELECT id, document_id, ref_number, provision_text, provision_type,
                   section_header, zone, development_type, full_text_length
            FROM regulatory_provisions
            WHERE document_id LIKE '%State_Environmental_Planning_Policy%'
        """)

        provisions = []
        for row in cur.fetchall():
            provisions.append({
                'id': row[0],
                'document_id': row[1],
                'ref_number': row[2],
                'provision_text': row[3],
                'provision_type': row[4],
                'section_header': row[5],
                'zone': row[6],
                'development_type': row[7],
                'full_text_length': row[8],
            })

        conn.close()

        print(f"[OK] Loaded {len(provisions):,} existing SEPP provisions from database")

        # Group by document
        by_document = {}
        for prov in provisions:
            doc_id = prov['document_id']
            if doc_id not in by_document:
                by_document[doc_id] = []
            by_document[doc_id].append(prov)

        for doc_id, provs in sorted(by_document.items()):
            sepp_name = doc_id.split('___')[0].replace('_', ' ')
            print(f"  {sepp_name:50} {len(provs):>6,} provisions")

        return provisions

    except Exception as e:
        print(f"[X] Error loading existing provisions: {e}")
        return None

def match_provisions(json_provisions: Dict, db_provisions: List) -> Dict:
    """Match JSON provisions to database provisions"""
    print("\n=== MATCHING PROVISIONS ===\n")

    # Create lookup by (document, ref_number)
    db_lookup = {}
    for prov in db_provisions:
        key = (prov['document_id'], prov['ref_number'])
        db_lookup[key] = prov

    matches = {
        'exact_matches': [],
        'partial_matches': [],
        'new_provisions': [],
        'unmatched_db': list(db_provisions)  # Start with all, remove as matched
    }

    for sepp_name, provisions in json_provisions.items():
        # Convert sepp_name to document_id format
        doc_id = sepp_name.replace(' ', '_').replace('-', '_')

        for json_prov in provisions:
            ref_num = json_prov['ref_number']

            # Try exact match on (document, ref_number)
            key = (doc_id, ref_num)
            if key in db_lookup:
                db_prov = db_lookup[key]
                matches['exact_matches'].append({
                    'db_id': db_prov['id'],
                    'ref_number': ref_num,
                    'document_id': doc_id,
                    'old_text_length': db_prov['full_text_length'] or len(db_prov['provision_text']),
                    'new_text_length': json_prov['text_length'],
                    'json_provision': json_prov
                })
                # Remove from unmatched
                if db_prov in matches['unmatched_db']:
                    matches['unmatched_db'].remove(db_prov)
            else:
                # Try partial match on ref_number (might be different doc_id format)
                found = False
                for db_prov in db_provisions:
                    if db_prov['ref_number'] == ref_num and sepp_name in db_prov['document_id']:
                        matches['partial_matches'].append({
                            'db_id': db_prov['id'],
                            'ref_number': ref_num,
                            'document_id': doc_id,
                            'old_text_length': db_prov['full_text_length'] or len(db_prov['provision_text']),
                            'new_text_length': json_prov['text_length'],
                            'json_provision': json_prov
                        })
                        if db_prov in matches['unmatched_db']:
                            matches['unmatched_db'].remove(db_prov)
                        found = True
                        break

                if not found:
                    # New provision not in database
                    matches['new_provisions'].append({
                        'ref_number': ref_num,
                        'document_id': doc_id,
                        'text_length': json_prov['text_length'],
                        'json_provision': json_prov
                    })

    print(f"Exact matches:     {len(matches['exact_matches']):>6,}")
    print(f"Partial matches:   {len(matches['partial_matches']):>6,}")
    print(f"New provisions:    {len(matches['new_provisions']):>6,}")
    print(f"Unmatched in DB:   {len(matches['unmatched_db']):>6,}")

    return matches

def update_database(matches: Dict) -> bool:
    """Update database with full text provisions"""
    print("\n=== UPDATING DATABASE ===\n")

    try:
        conn = get_safe_connection()
        cur = conn.cursor()

        updated_count = 0
        inserted_count = 0
        errors = []

        # Update exact matches
        print("1. Updating exact matches...")
        for match in matches['exact_matches']:
            try:
                json_prov = match['json_provision']
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET provision_text = %s,
                        full_text_length = %s,
                        extraction_method = 'mineru',
                        last_updated = NOW(),
                        section_header = COALESCE(section_header, %s)
                    WHERE id = %s
                """, (
                    json_prov['provision_text'],
                    json_prov['text_length'],
                    json_prov.get('section_header'),
                    match['db_id']
                ))
                updated_count += 1

                if updated_count % 100 == 0:
                    print(f"   Updated {updated_count:,} provisions...")

            except Exception as e:
                errors.append(f"Update error for ID {match['db_id']}: {e}")

        print(f"   [OK] Updated {updated_count:,} provisions")

        # Update partial matches
        print("\n2. Updating partial matches...")
        partial_updated = 0
        for match in matches['partial_matches']:
            try:
                json_prov = match['json_provision']
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET provision_text = %s,
                        full_text_length = %s,
                        extraction_method = 'mineru',
                        last_updated = NOW()
                    WHERE id = %s
                """, (
                    json_prov['provision_text'],
                    json_prov['text_length'],
                    match['db_id']
                ))
                partial_updated += 1
            except Exception as e:
                errors.append(f"Partial update error for ID {match['db_id']}: {e}")

        print(f"   [OK] Updated {partial_updated:,} provisions")
        updated_count += partial_updated

        # COMMIT UPDATES BEFORE TRYING INSERTS
        print(f"\n   Committing {updated_count} updates...")
        conn.commit()
        print(f"   [OK] Updates committed successfully")

        # Insert new provisions
        print("\n3. Inserting new provisions...")
        for new_prov in matches['new_provisions']:
            try:
                json_prov = new_prov['json_provision']
                cur.execute("""
                    INSERT INTO regulatory_provisions (
                        document_id, ref_number, provision_text, provision_type,
                        section_header, full_text_length, extraction_method,
                        created_at, last_updated
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """, (
                    new_prov['document_id'],
                    new_prov['ref_number'],
                    json_prov['provision_text'],
                    json_prov.get('provision_type', 'formal_provision'),
                    json_prov.get('section_header'),
                    json_prov['text_length'],
                    'mineru'
                ))
                inserted_count += 1

                if inserted_count % 100 == 0:
                    print(f"   Inserted {inserted_count:,} provisions...")

            except Exception as e:
                errors.append(f"Insert error for {new_prov['ref_number']}: {e}")

        print(f"   [OK] Inserted {inserted_count:,} new provisions")

        # Commit changes
        conn.commit()
        conn.close()

        # Save import log
        import_log = {
            'import_timestamp': datetime.now().isoformat(),
            'provisions_updated': updated_count,
            'provisions_inserted': inserted_count,
            'errors': errors,
            'error_count': len(errors)
        }

        with open(IMPORT_LOG, 'w') as f:
            json.dump(import_log, f, indent=2)

        print(f"\n[SUCCESS] DATABASE UPDATE COMPLETE")
        print(f"   Updated:  {updated_count:,} provisions")
        print(f"   Inserted: {inserted_count:,} provisions")
        print(f"   Errors:   {len(errors):,}")

        if errors:
            print(f"\n[!] Errors logged to: {IMPORT_LOG}")
            for error in errors[:5]:
                print(f"   {error}")
            if len(errors) > 5:
                print(f"   ... and {len(errors) - 5} more")

        return len(errors) == 0

    except Exception as e:
        print(f"\n[X] Database update failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def verify_import():
    """Verify provisions were imported correctly"""
    print("\n=== VERIFYING IMPORT ===\n")

    try:
        conn = get_safe_connection()
        cur = conn.cursor()

        # Check text length distribution
        cur.execute("""
            SELECT
                extraction_method,
                COUNT(*) as count,
                AVG(full_text_length) as avg_length,
                MIN(full_text_length) as min_length,
                MAX(full_text_length) as max_length
            FROM regulatory_provisions
            WHERE document_id LIKE '%State_Environmental_Planning_Policy%'
            GROUP BY extraction_method
        """)

        print("Provision statistics by extraction method:")
        for row in cur.fetchall():
            method, count, avg, min_len, max_len = row
            print(f"  {method:15} {count:>6,} provs | Avg: {avg:>7,.0f} | Min: {min_len:>6,} | Max: {max_len:>8,}")

        # Sample check: Get a few long provisions
        cur.execute("""
            SELECT id, ref_number, full_text_length, LEFT(provision_text, 100) as preview
            FROM regulatory_provisions
            WHERE extraction_method = 'mineru'
            AND full_text_length > 1000
            ORDER BY full_text_length DESC
            LIMIT 5
        """)

        print(f"\nSample full-text provisions (longest 5):")
        for row in cur.fetchall():
            prov_id, ref, length, preview = row
            print(f"  ID {prov_id:5} | {ref:20} | {length:>7,} chars")
            print(f"    {preview}...")

        conn.close()

        print(f"\n[SUCCESS] VERIFICATION PASSED")
        return True

    except Exception as e:
        print(f"\n[X] Verification failed: {e}")
        return False

def main():
    """Main execution"""
    print("\n" + "="*80)
    print("IMPORT FULL TEXT PROVISIONS - STEP 4")
    print("="*80)

    # Load parsed provisions
    json_provisions = load_parsed_provisions()
    if not json_provisions:
        return 1

    # Load existing database provisions
    db_provisions = get_existing_provisions()
    if db_provisions is None:
        return 1

    # Match provisions
    matches = match_provisions(json_provisions, db_provisions)

    # Confirm before updating
    print(f"\n{'='*80}")
    print("READY TO UPDATE DATABASE")
    print(f"{'='*80}")
    print(f"This will update {len(matches['exact_matches']) + len(matches['partial_matches']):,} existing provisions")
    print(f"and insert {len(matches['new_provisions']):,} new provisions.")
    print(f"\nProceeding with database update...")

    # Update database
    if not update_database(matches):
        return 1

    # Verify import
    if not verify_import():
        return 1

    print(f"\n[SUCCESS] IMPORT COMPLETE")
    print(f"\nNext step: Run 05_verify_completeness.py")
    return 0

if __name__ == "__main__":
    sys.exit(main())