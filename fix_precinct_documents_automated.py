"""
AUTOMATED FIX: Create documents table entries for precinct provisions
SAFE: Uses db_safety_wrapper and transactions
"""
import os
import json
from datetime import date
from dotenv import load_dotenv
from db_safety_wrapper import get_safe_connection

load_dotenv()

def extract_precinct_metadata(safe_conn):
    """Extract metadata from regulatory_provisions for all precinct documents"""
    cur = safe_conn.cursor()

    print("\nSTEP 1: Extracting metadata from regulatory_provisions...")

    # Get all unique precinct document_ids from dcp_precinct_provisions
    cur.execute("""
        SELECT DISTINCT document_id
        FROM dcp_precinct_provisions
        ORDER BY document_id
    """)
    precinct_doc_ids = [row[0] for row in cur.fetchall()]
    print(f"  Found {len(precinct_doc_ids)} unique precinct documents")

    # For each document_id, extract metadata from regulatory_provisions
    documents_to_create = []

    for doc_id in precinct_doc_ids:
        cur.execute("""
            SELECT
                document_id,
                pdf_source_file,
                MIN(pdf_page) as first_page,
                MAX(pdf_page) as last_page,
                COUNT(*) as provision_count,
                MAX(last_updated) as last_updated
            FROM regulatory_provisions
            WHERE document_id = %s
            GROUP BY document_id, pdf_source_file
        """, (doc_id,))

        result = cur.fetchone()
        if result:
            doc_data = {
                'id': result[0],
                'pdf_name': result[1],
                'pdf_source_file': result[1],
                'first_page': result[2],
                'last_page': result[3],
                'provision_count': result[4],
                'last_updated': result[5]
            }

            # Determine document_area from document_id
            if 'Marrickville' in doc_id:
                doc_data['document_area'] = 'Marrickville'
                doc_data['regulation_year'] = 2011
            elif 'Leichhardt' in doc_id:
                doc_data['document_area'] = 'Leichhardt'
                doc_data['regulation_year'] = 2013
            elif 'Ashfield' in doc_id:
                doc_data['document_area'] = 'Ashfield'
                doc_data['regulation_year'] = 2009
            else:
                doc_data['document_area'] = 'Inner West'
                doc_data['regulation_year'] = None

            # Extract amendment info if present
            if 'Amdt' in doc_id:
                parts = doc_id.split('Amdt')
                if len(parts) > 1:
                    amdt_part = parts[1].strip('_').split('_')[0]
                    doc_data['amendment_reference'] = f'Amdt {amdt_part}'

            documents_to_create.append(doc_data)

    print(f"  Extracted metadata for {len(documents_to_create)} documents")
    return documents_to_create

def create_document_entries(safe_conn, documents_to_create):
    """Create documents table entries using transaction"""
    cur = safe_conn.cursor()

    print("\nSTEP 2: Creating documents table entries...")
    print(f"  Will create {len(documents_to_create)} entries")

    created_count = 0
    skipped_count = 0

    for doc_data in documents_to_create:
        # Check if document already exists
        cur.execute("SELECT id FROM documents WHERE id = %s", (doc_data['id'],))
        if cur.fetchone():
            print(f"  SKIP: {doc_data['id']} (already exists)")
            skipped_count += 1
            continue

        # Insert document entry
        cur.execute("""
            INSERT INTO documents (
                id,
                pdf_name,
                document_type,
                document_area,
                regulation_year,
                amendment_reference,
                last_verified_date,
                version_status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            doc_data['id'],
            doc_data.get('pdf_name'),
            'DCP',
            doc_data.get('document_area'),
            doc_data.get('regulation_year'),
            doc_data.get('amendment_reference'),
            date.today(),
            'verified'
        ))

        created_count += 1
        print(f"  CREATE: {doc_data['id']}")

    print(f"\n  Created: {created_count}")
    print(f"  Skipped (already exist): {skipped_count}")

    return created_count

def verify_linkage(safe_conn):
    """Verify that all precinct provisions now have valid document entries"""
    cur = safe_conn.cursor()

    print("\nSTEP 3: Verifying document linkage...")

    # Check how many precinct provisions now have valid documents entries
    cur.execute("""
        SELECT
            COUNT(DISTINCT dpp.document_id) as total_docs,
            COUNT(DISTINCT d.id) as linked_docs
        FROM dcp_precinct_provisions dpp
        LEFT JOIN documents d ON d.id = dpp.document_id
    """)
    total_docs, linked_docs = cur.fetchone()

    print(f"  Total precinct documents: {total_docs}")
    print(f"  Linked to documents table: {linked_docs}")

    if total_docs == linked_docs:
        print("  SUCCESS: All precinct documents now have documents table entries")
        return True
    else:
        print(f"  WARNING: {total_docs - linked_docs} documents still missing")

        # Show which ones are missing
        cur.execute("""
            SELECT DISTINCT dpp.document_id
            FROM dcp_precinct_provisions dpp
            LEFT JOIN documents d ON d.id = dpp.document_id
            WHERE d.id IS NULL
        """)
        missing = cur.fetchall()
        print(f"\n  Missing documents:")
        for row in missing:
            print(f"    - {row[0]}")

        return False

def main():
    """Main execution with transaction safety"""
    print("=" * 80)
    print("AUTOMATED FIX: Precinct Documents Table Entries")
    print("=" * 80)

    # Create backup first (handled by db_safety_wrapper)
    with get_safe_connection(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        port=int(os.getenv('DB_PORT', 5432))
    ) as safe_conn:

        try:
            # Extract metadata
            documents_to_create = extract_precinct_metadata(safe_conn)

            # Save metadata for review
            with open('precinct_documents_to_create.json', 'w') as f:
                json.dump(documents_to_create, f, indent=2, default=str)
            print("\n  Metadata saved to: precinct_documents_to_create.json")

            # Create document entries (in transaction)
            created_count = create_document_entries(safe_conn, documents_to_create)

            # Commit transaction
            safe_conn.commit()
            print("\n  Transaction committed")

            # Verify
            success = verify_linkage(safe_conn)

            print("\n" + "=" * 80)
            if success:
                print("STATUS: COMPLETE - All precinct documents linked successfully")
                print("NEXT: Run comprehensive verification")
            else:
                print("STATUS: PARTIAL - Some documents still missing")
                print("NEXT: Review missing documents and re-run if needed")
            print("=" * 80)

            return success

        except Exception as e:
            print(f"\nERROR: {str(e)}")
            print("Rolling back transaction...")
            safe_conn.rollback()
            print("Transaction rolled back")
            return False

if __name__ == "__main__":
    main()
