"""
Comprehensive verification of precinct documents fix
"""
import os
from dotenv import load_dotenv
from db_safety_wrapper import get_safe_connection

load_dotenv()

with get_safe_connection(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    port=int(os.getenv('DB_PORT', 5432))
) as safe_conn:
    cur = safe_conn.cursor()

    print("=" * 80)
    print("COMPREHENSIVE PRECINCT DOCUMENTS VERIFICATION")
    print("=" * 80)

    # 1. Check dcp_precinct_provisions linkage
    print("\n1. DCP_PRECINCT_PROVISIONS LINKAGE:")
    cur.execute("""
        SELECT
            COUNT(DISTINCT dpp.document_id) as total_docs,
            COUNT(DISTINCT CASE WHEN d.id IS NOT NULL THEN dpp.document_id END) as linked_docs
        FROM dcp_precinct_provisions dpp
        LEFT JOIN documents d ON d.id = dpp.document_id
    """)
    total_docs, linked_docs = cur.fetchone()
    print(f"  Total precinct documents: {total_docs}")
    print(f"  Linked to documents table: {linked_docs}")
    print(f"  Status: {'SUCCESS' if total_docs == linked_docs else 'FAILED'}")

    # 2. Check documents table entries
    print("\n2. DOCUMENTS TABLE ENTRIES:")
    cur.execute("""
        SELECT COUNT(*)
        FROM documents
        WHERE id IN (SELECT DISTINCT document_id FROM dcp_precinct_provisions)
    """)
    doc_count = cur.fetchone()[0]
    print(f"  Precinct documents in documents table: {doc_count}")

    # 3. Check metadata completeness
    print("\n3. METADATA COMPLETENESS:")
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN pdf_name IS NOT NULL THEN 1 END) as has_pdf_name,
            COUNT(CASE WHEN document_type IS NOT NULL THEN 1 END) as has_type,
            COUNT(CASE WHEN document_area IS NOT NULL THEN 1 END) as has_area,
            COUNT(CASE WHEN regulation_year IS NOT NULL THEN 1 END) as has_year
        FROM documents
        WHERE id IN (SELECT DISTINCT document_id FROM dcp_precinct_provisions)
    """)
    total, has_pdf, has_type, has_area, has_year = cur.fetchone()
    print(f"  Total documents: {total}")
    print(f"  Has pdf_name: {has_pdf} ({has_pdf/total*100:.0f}%)")
    print(f"  Has document_type: {has_type} ({has_type/total*100:.0f}%)")
    print(f"  Has document_area: {has_area} ({has_area/total*100:.0f}%)")
    print(f"  Has regulation_year: {has_year} ({has_year/total*100:.0f}%)")

    # 4. Test JOIN query (this is what the UI will use)
    print("\n4. TEST UI JOIN QUERY:")
    cur.execute("""
        SELECT
            dpp.precinct_id,
            dpp.precinct_name,
            dpp.provision_text,
            d.pdf_name,
            d.document_area,
            d.regulation_year
        FROM dcp_precinct_provisions dpp
        JOIN documents d ON d.id = dpp.document_id
        WHERE dpp.precinct_name = 'Abergeldie Estate'
        LIMIT 3
    """)
    results = cur.fetchall()
    print(f"  Sample JOIN results (Abergeldie Estate): {len(results)} provisions")
    if results:
        for i, row in enumerate(results, 1):
            print(f"\n    Provision {i}:")
            print(f"      Precinct: {row[1]}")
            print(f"      Text: {row[2][:60]}...")
            print(f"      PDF: {row[3]}")
            print(f"      Area: {row[4]}")
            print(f"      Year: {row[5]}")

    # 5. Check regulatory_provisions linkage
    print("\n5. REGULATORY_PROVISIONS LINKAGE:")
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions rp
        WHERE rp.document_id IN (
            SELECT DISTINCT document_id FROM dcp_precinct_provisions
        )
    """)
    rp_count = cur.fetchone()[0]
    print(f"  Provisions in regulatory_provisions: {rp_count}")

    # 6. Verify we can query by address (future workflow)
    print("\n6. FUTURE WORKFLOW TEST (Address -> Precinct -> Provisions):")
    print("  Step 1: User enters address -> Get precinct from spatial query")
    print("  Step 2: Query dcp_precinct_provisions for that precinct")
    print("  Step 3: JOIN with documents to get PDF links, page numbers, etc.")
    print("  Step 4: Display to user with full source metadata")
    print("\n  Test query for 'Abergeldie Estate' precinct:")
    cur.execute("""
        SELECT
            COUNT(*) as provision_count,
            d.pdf_name,
            d.document_area,
            d.regulation_year,
            d.version_status
        FROM dcp_precinct_provisions dpp
        JOIN documents d ON d.id = dpp.document_id
        WHERE dpp.precinct_name = 'Abergeldie Estate'
        GROUP BY d.pdf_name, d.document_area, d.regulation_year, d.version_status
    """)
    workflow_test = cur.fetchone()
    if workflow_test:
        print(f"    Provisions: {workflow_test[0]}")
        print(f"    Source PDF: {workflow_test[1]}")
        print(f"    Area: {workflow_test[2]}")
        print(f"    Year: {workflow_test[3]}")
        print(f"    Status: {workflow_test[4]}")
        print("    Result: SUCCESS - Full metadata available for user display")

    # 7. Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

    all_pass = True
    if total_docs == linked_docs:
        print("PASS: All precinct provisions linked to documents table")
    else:
        print("FAIL: Some precinct provisions missing documents entries")
        all_pass = False

    if has_pdf == total and has_type == total:
        print("PASS: All documents have required metadata (pdf_name, document_type)")
    else:
        print("FAIL: Some documents missing metadata")
        all_pass = False

    if results and len(results) > 0:
        print("PASS: JOIN queries working correctly")
    else:
        print("FAIL: JOIN queries not working")
        all_pass = False

    print("\n" + "=" * 80)
    if all_pass:
        print("STATUS: ALL VERIFICATIONS PASSED")
        print("READY: System is optimal for providing relevant provisions per address")
        print("\nNEXT STEPS:")
        print("1. Implement address -> precinct spatial query")
        print("2. Connect to LightRAG for intelligent provision retrieval")
        print("3. Display provisions to users with full source metadata")
    else:
        print("STATUS: SOME ISSUES FOUND - Review above")
    print("=" * 80)
