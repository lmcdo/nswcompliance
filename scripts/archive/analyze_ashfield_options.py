"""
Analyze Ashfield precinct provisions to determine best remediation strategy.
Evaluate feasibility of re-extraction, manual mapping, page-based mapping, etc.
"""

import os
import psycopg2
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

def analyze_ashfield_structure():
    """Analyze Ashfield provision structure for remediation options."""
    conn = get_db_connection()
    cur = conn.cursor()

    print("=" * 80)
    print("ASHFIELD PRECINCT PROVISIONS - OPTIONS ANALYSIS")
    print("=" * 80)

    # Get all Ashfield precinct provisions with metadata
    cur.execute("""
        SELECT
            id,
            document_id,
            v2_dcp_part,
            provision_text,
            pdf_page
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
        ORDER BY id;
    """)

    provisions = cur.fetchall()
    print(f"\nTotal Ashfield precinct provisions: {len(provisions)}")

    # Analyze metadata availability
    has_pdf_page = sum(1 for p in provisions if p[4] is not None)

    print("\n" + "=" * 80)
    print("METADATA AVAILABILITY")
    print("=" * 80)
    print(f"PDF page populated: {has_pdf_page}/{len(provisions)} ({has_pdf_page/len(provisions)*100:.1f}%)")

    # Check if provisions have ID ranges that correlate to Parts
    print("\n" + "=" * 80)
    print("ID DISTRIBUTION ANALYSIS")
    print("=" * 80)
    ids = [p[0] for p in provisions]
    print(f"ID range: {min(ids)} - {max(ids)}")
    print(f"ID span: {max(ids) - min(ids)}")
    print(f"Provisions: {len(ids)}")
    print(f"Average gap: {(max(ids) - min(ids)) / len(ids):.1f}")

    # Show ID distribution (every 10th provision)
    print("\nID distribution (every 10th provision):")
    for i in range(0, len(provisions), 10):
        id, doc, part, text, pdf_pg = provisions[i]
        text_preview = text[:60] if text else "None"
        print(f"  {i:3d}. ID {id:6d}, Page {pdf_pg}: {text_preview}...")

    # Check unique document_ids
    cur.execute("""
        SELECT DISTINCT document_id
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true;
    """)

    unique_docs = cur.fetchall()
    print("\n" + "=" * 80)
    print(f"UNIQUE DOCUMENTS ({len(unique_docs)} total)")
    print("=" * 80)
    for doc in unique_docs:
        print(f"  - {doc[0]}")

    # Check source document table for Chapter D
    print("\n" + "=" * 80)
    print("SOURCE DOCUMENTS TABLE CHECK")
    print("=" * 80)

    cur.execute("""
        SELECT id, document_name, document_type, file_path
        FROM documents
        WHERE document_name ILIKE '%Ashfield%'
          AND document_name ILIKE '%Chapter D%'
        LIMIT 5;
    """)

    docs = cur.fetchall()
    if docs:
        print("Found Chapter D documents in 'documents' table:")
        for id, name, type, path in docs:
            print(f"\n  Document ID: {id}")
            print(f"  Name: {name}")
            print(f"  Type: {type}")
            print(f"  Path: {path}")
    else:
        print("No Chapter D documents found in 'documents' table")

    # Check if original extraction stored Part information
    cur.execute("""
        SELECT DISTINCT v2_dcp_part
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
          AND v2_dcp_layer = 'precinct';
    """)

    unique_parts = cur.fetchall()
    print("\n" + "=" * 80)
    print(f"UNIQUE v2_dcp_part VALUES ({len(unique_parts)} total)")
    print("=" * 80)
    for part in unique_parts:
        print(f"  - {part[0]}")

    # Sample provisions with full text to check for Part mentions
    print("\n" + "=" * 80)
    print("TEXT CONTENT ANALYSIS (First 5 provisions)")
    print("=" * 80)

    for i in range(min(5, len(provisions))):
        id, doc, part, text, pdf_pg = provisions[i]
        print(f"\nProvision {i+1}:")
        print(f"  ID: {id}")
        print(f"  Part: {part}")
        print(f"  PDF Page: {pdf_pg}")
        print(f"  Text (first 300 chars):")
        print(f"  {text[:300] if text else 'None'}...")

    cur.close()
    conn.close()

if __name__ == '__main__':
    analyze_ashfield_structure()
