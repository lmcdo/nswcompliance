#!/usr/bin/env python3
"""Check for SEPP/LEP data in existing tables"""

import sqlite3

def check_sepp_lep_data():
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()

    print("=== SEPP/LEP DATA ANALYSIS ===")

    # Check documents table for SEPP/LEP sources
    cursor.execute("SELECT COUNT(*) FROM documents WHERE document_name LIKE '%SEPP%' OR document_name LIKE '%LEP%'")
    sepp_lep_docs = cursor.fetchone()[0]
    print(f"SEPP/LEP documents: {sepp_lep_docs:,}")

    if sepp_lep_docs > 0:
        cursor.execute("SELECT DISTINCT document_name FROM documents WHERE document_name LIKE '%SEPP%' OR document_name LIKE '%LEP%' LIMIT 10")
        docs = [row[0] for row in cursor.fetchall()]
        print("Sample documents:")
        for doc in docs:
            print(f"  - {doc}")

    # Check regulatory_provisions by document source
    cursor.execute("""
        SELECT COUNT(*) FROM regulatory_provisions rp
        JOIN documents d ON rp.document_id = d.id
        WHERE d.document_name LIKE '%SEPP%' OR d.document_name LIKE '%LEP%'
    """)
    sepp_lep_provisions = cursor.fetchone()[0]
    print(f"SEPP/LEP provisions (via documents): {sepp_lep_provisions:,}")

    # Sample provision types
    cursor.execute("SELECT DISTINCT provision_type FROM regulatory_provisions LIMIT 10")
    types = [row[0] for row in cursor.fetchall()]
    print(f"Provision types: {types}")

    # Check contextual_guidance
    cursor.execute("SELECT COUNT(*) FROM contextual_guidance")
    guidance_count = cursor.fetchone()[0]
    print(f"Contextual guidance records: {guidance_count:,}")

    # Check all table counts
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"\n=== ALL TABLE COUNTS ===")
    for table in tables:
        if table != 'sqlite_sequence':
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{table}: {count:,}")

    conn.close()

if __name__ == "__main__":
    check_sepp_lep_data()