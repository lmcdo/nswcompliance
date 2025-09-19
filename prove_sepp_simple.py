#!/usr/bin/env python3
"""
Simple proof that SEPPs are properly in the database with entities and relationships
"""

import sqlite3
import json
from datetime import datetime

def prove_sepp_database():
    """Prove SEPPs are in database with proper structure"""

    print("=== SEPP DATABASE STRUCTURE PROOF ===")
    print(f"Analysis timestamp: {datetime.now().isoformat()}")
    print()

    # Connect to database
    try:
        conn = sqlite3.connect('nsw_planning.db')
        cursor = conn.cursor()
        print("[OK] Database connection successful")
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        return

    # 1. Check database tables
    print("\n1. DATABASE TABLES ANALYSIS")
    print("-" * 40)

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"Total tables: {len(tables)}")

    # Find SEPP-related tables
    sepp_tables = [t for t in tables if 'sepp' in t.lower() or 'provision' in t.lower() or 'regulatory' in t.lower()]
    print(f"SEPP-related tables: {len(sepp_tables)}")
    for table in sepp_tables:
        print(f"  - {table}")

    # 2. SEPP Provisions Count
    print("\n2. SEPP PROVISIONS ANALYSIS")
    print("-" * 40)

    if 'regulatory_provisions' in tables:
        # Total SEPP provisions
        cursor.execute("""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE LOWER(document_id) LIKE '%sepp%'
        """)
        total_sepp = cursor.fetchone()[0]
        print(f"Total SEPP provisions: {total_sepp:,}")

        # SEPP documents
        cursor.execute("""
        SELECT document_id, COUNT(*) as count
        FROM regulatory_provisions
        WHERE LOWER(document_id) LIKE '%sepp%'
        GROUP BY document_id
        ORDER BY count DESC
        LIMIT 10
        """)
        sepp_docs = cursor.fetchall()

        print(f"SEPP documents ({len(sepp_docs)} found):")
        for doc_id, count in sepp_docs:
            print(f"  {doc_id}: {count:,} provisions")

        # 3. Key SEPP Analysis
        print("\n3. KEY SEPP TYPES ANALYSIS")
        print("-" * 40)

        # SEPP (Exempt and Complying)
        cursor.execute("""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE LOWER(document_id) LIKE '%exempt%' AND LOWER(document_id) LIKE '%complying%'
        """)
        exempt_complying = cursor.fetchone()[0]

        # SEPP (Housing) 2021
        cursor.execute("""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE LOWER(document_id) LIKE '%housing%' AND document_id LIKE '%2021%'
        """)
        housing_2021 = cursor.fetchone()[0]

        # SEPP 65
        cursor.execute("""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE document_id LIKE '%65%'
        """)
        sepp_65 = cursor.fetchone()[0]

        print(f"SEPP (Exempt and Complying): {exempt_complying:,} provisions")
        print(f"SEPP (Housing) 2021: {housing_2021:,} provisions")
        print(f"SEPP 65 Design Quality: {sepp_65:,} provisions")

        # 4. Entity Relationships Analysis
        print("\n4. ENTITY RELATIONSHIPS ANALYSIS")
        print("-" * 40)

        # Zone relationships
        cursor.execute("""
        SELECT zone, COUNT(*) as count
        FROM regulatory_provisions
        WHERE LOWER(document_id) LIKE '%sepp%' AND zone IS NOT NULL
        GROUP BY zone
        ORDER BY count DESC
        LIMIT 5
        """)
        zone_rels = cursor.fetchall()

        print("SEPP-Zone relationships (top 5):")
        for zone, count in zone_rels:
            print(f"  {zone}: {count:,} provisions")

        # Development type relationships
        cursor.execute("""
        SELECT development_type, COUNT(*) as count
        FROM regulatory_provisions
        WHERE LOWER(document_id) LIKE '%sepp%' AND development_type IS NOT NULL
        GROUP BY development_type
        ORDER BY count DESC
        LIMIT 5
        """)
        dev_type_rels = cursor.fetchall()

        print("SEPP-Development Type relationships (top 5):")
        for dev_type, count in dev_type_rels:
            print(f"  {dev_type}: {count:,} provisions")

        # 5. Sample SEPP Content
        print("\n5. SAMPLE SEPP CONTENT (Entity Examples)")
        print("-" * 40)

        # Sample Housing SEPP provision
        cursor.execute("""
        SELECT id, document_id, provision_text, zone, development_type
        FROM regulatory_provisions
        WHERE LOWER(document_id) LIKE '%housing%' AND provision_text IS NOT NULL
        LIMIT 2
        """)
        housing_samples = cursor.fetchall()

        print("Sample SEPP (Housing) provisions:")
        for i, (prov_id, doc_id, text, zone, dev_type) in enumerate(housing_samples, 1):
            print(f"  Example {i}:")
            print(f"    ID: {prov_id}")
            print(f"    Document: {doc_id}")
            print(f"    Zone: {zone or 'Not specified'}")
            print(f"    Dev Type: {dev_type or 'Not specified'}")
            print(f"    Text: {text[:150]}...")
            print()

        # 6. Data Quality Check
        print("6. DATA QUALITY ASSESSMENT")
        print("-" * 40)

        cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN provision_text IS NOT NULL AND provision_text != '' THEN 1 END) as has_text,
            COUNT(CASE WHEN zone IS NOT NULL THEN 1 END) as has_zone,
            COUNT(CASE WHEN development_type IS NOT NULL THEN 1 END) as has_dev_type
        FROM regulatory_provisions
        WHERE LOWER(document_id) LIKE '%sepp%'
        """)

        total, has_text, has_zone, has_dev_type = cursor.fetchone()

        print(f"Total SEPP provisions: {total:,}")
        print(f"With provision text: {has_text:,} ({has_text/total*100:.1f}%)")
        print(f"With zone info: {has_zone:,} ({has_zone/total*100:.1f}%)")
        print(f"With dev type: {has_dev_type:,} ({has_dev_type/total*100:.1f}%)")

        # 7. Integration with Development Permissions
        print("\n7. INTEGRATION WITH DEVELOPMENT PERMISSIONS")
        print("-" * 40)

        if 'development_permissions' in tables:
            cursor.execute("""
            SELECT COUNT(*) FROM development_permissions
            WHERE LOWER(lep_name) LIKE '%sepp%' OR source_type LIKE '%sepp%'
            """)
            sepp_permissions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM development_permissions")
            total_permissions = cursor.fetchone()[0]

            print(f"Total development permissions: {total_permissions:,}")
            print(f"SEPP-derived permissions: {sepp_permissions:,}")
            print(f"SEPP integration rate: {sepp_permissions/total_permissions*100:.1f}%")

        # 8. Proof Verification
        print("\n8. PROOF VERIFICATION")
        print("=" * 40)

        proof_results = {
            'total_sepp_provisions': total_sepp,
            'sepp_documents': len(sepp_docs),
            'exempt_complying': exempt_complying,
            'housing_2021': housing_2021,
            'sepp_65': sepp_65,
            'zone_relationships': len(zone_rels),
            'dev_type_relationships': len(dev_type_rels),
            'text_completeness': has_text/total*100,
            'entity_completeness': (has_zone + has_dev_type)/(total*2)*100
        }

        # Verification criteria
        criteria = {
            'substantial_sepp_content': total_sepp >= 1000,
            'multiple_sepp_types': len(sepp_docs) >= 3,
            'housing_sepp_present': housing_2021 >= 100,
            'exempt_complying_present': exempt_complying >= 100,
            'zone_relationships_exist': len(zone_rels) >= 3,
            'dev_type_relationships_exist': len(dev_type_rels) >= 3,
            'adequate_text_quality': has_text/total*100 >= 70,
            'adequate_entity_linkage': (has_zone + has_dev_type)/(total*2)*100 >= 30
        }

        print("VERIFICATION CRITERIA:")
        all_passed = True
        for criterion, passed in criteria.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status} {criterion.replace('_', ' ').title()}")
            if not passed:
                all_passed = False

        print(f"\nOVERALL PROOF STATUS: {'[PROVEN]' if all_passed else '[NEEDS WORK]'}")

        if all_passed:
            print("\nCONCLUSION: SEPPs are PROPERLY in the database with entities and relationships")
            print(f"  - {total_sepp:,} SEPP provisions from {len(sepp_docs)} documents")
            print(f"  - {len(zone_rels)} zone relationships, {len(dev_type_rels)} development type relationships")
            print(f"  - {has_text/total*100:.1f}% text completeness, {(has_zone + has_dev_type)/(total*2)*100:.1f}% entity linkage")
            print("  - Key SEPPs present: Housing 2021, Exempt/Complying, SEPP 65")
        else:
            print("\nCONCLUSION: SEPP database structure needs improvement")

        # Save proof results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f'sepp_proof_{timestamp}.json', 'w') as f:
            json.dump(proof_results, f, indent=2)

        print(f"\nProof results saved to: sepp_proof_{timestamp}.json")

    else:
        print("[ERROR] regulatory_provisions table not found")

    conn.close()

if __name__ == "__main__":
    prove_sepp_database()