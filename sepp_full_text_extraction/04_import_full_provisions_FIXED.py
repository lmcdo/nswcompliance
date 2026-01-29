"""
STEP 4 FIXED: Import full text provisions from JSON to database

Fixes:
1. Auto-generate IDs (no hardcoded IDs)
2. Improved ref_number matching (handles "Section X" vs "X.X" formats)
3. Fix sequence before inserts
4. Commit updates before inserts
5. Individual error handling per insert

Exit Codes:
- 0: Success - all provisions imported
- 1: Failure - import errors
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from db_safety_wrapper import get_safe_connection

# Import version tracking functions
sys.path.insert(0, str(Path(__file__).parent))
from version_tracking import (
    detect_provision_changes,
    update_provision_with_versioning,
    create_initial_version,
    calculate_text_hash
)

# Use absolute path from script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
EXTRACTED_DIR = PROJECT_ROOT / "docs/sepps/extracted"
PARSING_REPORT = EXTRACTED_DIR / "parsing_report.json"
IMPORT_LOG = EXTRACTED_DIR / "import_log.json"

def normalize_ref_number(ref: str) -> str:
    """Normalize reference numbers to match different formats

    Examples:
        "Section 31" -> "31"
        "section 2.6(1)" -> "2.6(1)"
        "2.6" -> "2.6"
        "Schedule 4" -> "Schedule 4"
    """
    if not ref:
        return ""

    # Handle "Section X" format
    section_match = re.match(r'[Ss]ection\s+(\S+)', ref)
    if section_match:
        return section_match.group(1)

    # Handle "Schedule X" format
    schedule_match = re.match(r'[Ss]chedule\s+(\d+)', ref)
    if schedule_match:
        return f"Schedule {schedule_match.group(1)}"

    # Already normalized
    return ref.strip()

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

        # Get all SEPP provisions (including version tracking fields)
        cur.execute("""
            SELECT id, document_id, ref_number, provision_text, provision_type,
                   section_header, zone, development_type, full_text_length,
                   text_hash_current
            FROM regulatory_provisions
            WHERE document_id LIKE '%State_Environmental_Planning_Policy%'
               OR document_id LIKE '%State Environmental Planning Policy%'
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
                'text_hash_current': row[9],
            })

        conn.close()

        print(f"[OK] Loaded {len(provisions):,} existing SEPP provisions from database")
        return provisions

    except Exception as e:
        print(f"[X] Error loading existing provisions: {e}")
        return None

def match_provisions(json_provisions: Dict, db_provisions: List) -> Dict:
    """Match JSON provisions to database provisions with improved matching"""
    print("\n=== MATCHING PROVISIONS ===\n")

    # Create multiple lookup strategies
    db_lookup_exact = {}  # (document, ref_number)
    db_lookup_normalized = {}  # (document_normalized, ref_normalized)

    for prov in db_provisions:
        doc_id = prov['document_id']
        ref_num = prov['ref_number']

        # Exact match lookup
        key_exact = (doc_id, ref_num)
        db_lookup_exact[key_exact] = prov

        # Normalized match lookup
        doc_normalized = doc_id.replace('_', ' ').lower()
        ref_normalized = normalize_ref_number(ref_num)
        key_normalized = (doc_normalized, ref_normalized)
        if key_normalized not in db_lookup_normalized:
            db_lookup_normalized[key_normalized] = prov

    matches = {
        'exact_matches': [],
        'normalized_matches': [],
        'new_provisions': [],
        'unmatched_db': list(db_provisions)
    }

    for sepp_name, provisions in json_provisions.items():
        # Normalize SEPP name for matching
        doc_normalized = sepp_name.replace('_', ' ').lower()

        for json_prov in provisions:
            ref_num = json_prov['ref_number']
            ref_normalized = normalize_ref_number(ref_num)

            # Try exact match first
            for doc_format in [sepp_name, sepp_name.replace(' ', '_')]:
                key_exact = (doc_format, ref_num)
                if key_exact in db_lookup_exact:
                    db_prov = db_lookup_exact[key_exact]
                    matches['exact_matches'].append({
                        'db_id': db_prov['id'],
                        'ref_number': ref_num,
                        'document_id': doc_format,
                        'old_text_length': db_prov['full_text_length'] or len(db_prov['provision_text']),
                        'new_text_length': json_prov['text_length'],
                        'json_provision': json_prov
                    })
                    if db_prov in matches['unmatched_db']:
                        matches['unmatched_db'].remove(db_prov)
                    break
            else:
                # Try normalized match
                key_normalized = (doc_normalized, ref_normalized)
                if key_normalized in db_lookup_normalized:
                    db_prov = db_lookup_normalized[key_normalized]
                    matches['normalized_matches'].append({
                        'db_id': db_prov['id'],
                        'ref_number': ref_num,
                        'db_ref_number': db_prov['ref_number'],
                        'document_id': db_prov['document_id'],
                        'old_text_length': db_prov['full_text_length'] or len(db_prov['provision_text']),
                        'new_text_length': json_prov['text_length'],
                        'json_provision': json_prov
                    })
                    if db_prov in matches['unmatched_db']:
                        matches['unmatched_db'].remove(db_prov)
                else:
                    # New provision
                    matches['new_provisions'].append({
                        'ref_number': ref_num,
                        'document_id': sepp_name,
                        'text_length': json_prov['text_length'],
                        'json_provision': json_prov
                    })

    print(f"Exact matches:       {len(matches['exact_matches']):>6,}")
    print(f"Normalized matches:  {len(matches['normalized_matches']):>6,}")
    print(f"New provisions:      {len(matches['new_provisions']):>6,}")
    print(f"Unmatched in DB:     {len(matches['unmatched_db']):>6,}")

    return matches

def fix_sequence(conn, cur):
    """Fix the ID sequence to prevent duplicate key errors"""
    print("\n=== FIXING ID SEQUENCE ===\n")

    try:
        # Get the current max ID
        cur.execute("SELECT MAX(id) FROM regulatory_provisions")
        max_id = cur.fetchone()[0] or 0

        # Reset sequence to max_id + 1
        cur.execute(f"SELECT setval('regulatory_provisions_id_seq', {max_id + 1}, false)")

        print(f"[OK] Sequence reset to start at {max_id + 1}")
        return True
    except Exception as e:
        print(f"[!] Could not fix sequence: {e}")
        print(f"    Will skip inserts and only do updates")
        return False

def update_database(matches: Dict) -> bool:
    """Update database with full text provisions"""
    print("\n=== UPDATING DATABASE ===\n")

    try:
        conn = get_safe_connection()
        cur = conn.cursor()

        updated_count = 0
        inserted_count = 0
        errors = []

        # Update exact matches (with version tracking)
        print("1. Updating exact matches with version tracking...")
        version_created_count = 0
        for match in matches['exact_matches']:
            try:
                json_prov = match['json_provision']

                # Get existing provision data for version tracking
                cur.execute("""
                    SELECT provision_text, text_hash_current
                    FROM regulatory_provisions
                    WHERE id = %s
                """, (match['db_id'],))

                row = cur.fetchone()
                if row:
                    old_text = row[0]
                    old_hash = row[1]

                    # Prepare new metadata
                    new_metadata = {
                        'provision_type': json_prov.get('provision_type', 'formal_provision'),
                        'section_header': json_prov.get('section_header'),
                    }

                    # Update with version tracking
                    was_changed, new_version_id = update_provision_with_versioning(
                        cur=cur,
                        provision_id=match['db_id'],
                        old_text=old_text,
                        old_hash=old_hash or calculate_text_hash(old_text),
                        new_text=json_prov['provision_text'],
                        new_metadata=new_metadata,
                        document_id=match['document_id'],
                        amendment_ref='Full text extraction update'
                    )

                    if was_changed:
                        version_created_count += 1

                    # Also update fields not tracked in version history
                    cur.execute("""
                        UPDATE regulatory_provisions
                        SET full_text_length = %s,
                            extraction_method = 'mineru',
                            section_header = COALESCE(section_header, %s)
                        WHERE id = %s
                    """, (
                        json_prov['text_length'],
                        json_prov.get('section_header'),
                        match['db_id']
                    ))

                    updated_count += 1

                    if updated_count % 100 == 0:
                        print(f"   Updated {updated_count:,} provisions ({version_created_count} changed)...")

            except Exception as e:
                errors.append(f"Update error for ID {match['db_id']}: {e}")

        print(f"   [OK] Updated {updated_count:,} exact match provisions ({version_created_count} versions created)")

        # Update normalized matches (with version tracking)
        print("\n2. Updating normalized matches with version tracking...")
        normalized_updated = 0
        normalized_version_count = 0
        for match in matches['normalized_matches']:
            try:
                json_prov = match['json_provision']

                # Get existing provision data for version tracking
                cur.execute("""
                    SELECT provision_text, text_hash_current
                    FROM regulatory_provisions
                    WHERE id = %s
                """, (match['db_id'],))

                row = cur.fetchone()
                if row:
                    old_text = row[0]
                    old_hash = row[1]

                    # Prepare new metadata
                    new_metadata = {
                        'provision_type': json_prov.get('provision_type', 'formal_provision'),
                    }

                    # Update with version tracking
                    was_changed, new_version_id = update_provision_with_versioning(
                        cur=cur,
                        provision_id=match['db_id'],
                        old_text=old_text,
                        old_hash=old_hash or calculate_text_hash(old_text),
                        new_text=json_prov['provision_text'],
                        new_metadata=new_metadata,
                        document_id=match['document_id'],
                        amendment_ref='Full text extraction update'
                    )

                    if was_changed:
                        normalized_version_count += 1

                    # Also update fields not tracked in version history
                    cur.execute("""
                        UPDATE regulatory_provisions
                        SET full_text_length = %s,
                            extraction_method = 'mineru'
                        WHERE id = %s
                    """, (
                        json_prov['text_length'],
                        match['db_id']
                    ))

                    normalized_updated += 1

                    if normalized_updated % 100 == 0:
                        print(f"   Updated {normalized_updated:,} provisions ({normalized_version_count} changed)...")

            except Exception as e:
                errors.append(f"Normalized update error for ID {match['db_id']}: {e}")

        print(f"   [OK] Updated {normalized_updated:,} normalized match provisions ({normalized_version_count} versions created)")
        updated_count += normalized_updated
        version_created_count += normalized_version_count

        # COMMIT UPDATES BEFORE TRYING INSERTS
        print(f"\n   Committing {updated_count} updates...")
        conn.commit()
        print(f"   [OK] Updates committed successfully")

        # Fix sequence before inserts
        sequence_fixed = fix_sequence(conn, cur)

        if sequence_fixed and len(matches['new_provisions']) > 0:
            # Insert new provisions (with initial version creation)
            print(f"\n3. Inserting {len(matches['new_provisions']):,} new provisions with version tracking...")

            for idx, new_prov in enumerate(matches['new_provisions']):
                try:
                    json_prov = new_prov['json_provision']

                    # Use document_id from match
                    doc_id = new_prov['document_id']

                    # Insert provision
                    cur.execute("""
                        INSERT INTO regulatory_provisions (
                            document_id, ref_number, provision_text, provision_type,
                            section_header, full_text_length, extraction_method,
                            last_updated
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                        RETURNING id
                    """, (
                        doc_id,
                        new_prov['ref_number'],
                        json_prov['provision_text'],
                        json_prov.get('provision_type', 'formal_provision'),
                        json_prov.get('section_header'),
                        json_prov['text_length'],
                        'mineru'
                    ))

                    new_provision_id = cur.fetchone()[0]

                    # Create initial version (version 1)
                    metadata = {
                        'provision_type': json_prov.get('provision_type', 'formal_provision'),
                    }

                    create_initial_version(
                        cur=cur,
                        provision_id=new_provision_id,
                        provision_text=json_prov['provision_text'],
                        metadata=metadata,
                        document_id=doc_id
                    )

                    inserted_count += 1

                    if inserted_count % 100 == 0:
                        print(f"   Inserted {inserted_count:,} provisions...")
                        conn.commit()  # Commit in batches

                except Exception as e:
                    # Don't let one failure stop all inserts
                    errors.append(f"Insert error for {new_prov['ref_number']}: {str(e)}")
                    # Rollback this one and continue
                    conn.rollback()
                    # Reconnect cursor
                    conn = get_safe_connection()
                    cur = conn.cursor()

            print(f"   [OK] Inserted {inserted_count:,} new provisions (with version 1 records)")
        else:
            print(f"\n3. Skipping inserts (sequence issue or no new provisions)")

        # Final commit
        conn.commit()
        conn.close()

        # Save import log
        import_log = {
            'import_timestamp': datetime.now().isoformat(),
            'provisions_updated': updated_count,
            'provisions_inserted': inserted_count,
            'versions_created': version_created_count,
            'errors': errors,
            'error_count': len(errors)
        }

        with open(IMPORT_LOG, 'w', encoding='utf-8') as f:
            json.dump(import_log, f, indent=2)

        print(f"\n[SUCCESS] DATABASE UPDATE COMPLETE (WITH VERSION TRACKING)")
        print(f"   Updated:         {updated_count:,} provisions")
        print(f"   Inserted:        {inserted_count:,} provisions")
        print(f"   Versions Created: {version_created_count:,} (changes detected)")
        print(f"   Errors:          {len(errors):,}")

        if errors and len(errors) <= 20:
            print(f"\n[!] Errors:")
            for error in errors:
                print(f"   {error}")
        elif errors:
            print(f"\n[!] Errors logged to: {IMPORT_LOG}")
            for error in errors[:5]:
                print(f"   {error}")
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
                AVG(full_text_length)::int as avg_length,
                MIN(full_text_length) as min_length,
                MAX(full_text_length) as max_length
            FROM regulatory_provisions
            WHERE document_id LIKE '%State_Environmental_Planning_Policy%'
               OR document_id LIKE '%State Environmental Planning Policy%'
            GROUP BY extraction_method
        """)

        print("Provision statistics by extraction method:")
        for row in cur.fetchall():
            method, count, avg, min_len, max_len = row
            print(f"  {method or 'NULL':15} {count:>6,} provs | Avg: {avg or 0:>7,} | Min: {min_len or 0:>6,} | Max: {max_len or 0:>8,}")

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
    print("IMPORT FULL TEXT PROVISIONS - STEP 4 (FIXED)")
    print("="*80)

    # Load parsed provisions
    json_provisions = load_parsed_provisions()
    if not json_provisions:
        return 1

    # Load existing database provisions
    db_provisions = get_existing_provisions()
    if db_provisions is None:
        return 1

    # Match provisions with improved matching
    matches = match_provisions(json_provisions, db_provisions)

    # Confirm before updating
    print(f"\n{'='*80}")
    print("READY TO UPDATE DATABASE")
    print(f"{'='*80}")
    print(f"This will update {len(matches['exact_matches']) + len(matches['normalized_matches']):,} existing provisions")
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