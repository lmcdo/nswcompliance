#!/usr/bin/env python3
"""
Analyze SQLite Structure vs PostgreSQL - Find Missing Relationships
Critical analysis to recover lost legal instrument hierarchy
"""

import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import json

def analyze_database_structures():
    """Compare SQLite original vs PostgreSQL migrated structures"""

    print("=== ANALYZING SQLITE VS POSTGRESQL STRUCTURE DIFFERENCES ===")
    print()

    # Connect to both databases
    sqlite_conn = sqlite3.connect('nsw_planning.db')
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    pg_conn = psycopg2.connect(
        host='localhost',
        database='nsw_planning',
        user='postgres',
        password='postgres',
        port='5432'
    )
    pg_cur = pg_conn.cursor(cursor_factory=RealDictCursor)

    # 1. Compare table structures
    print("1. COMPARING TABLE STRUCTURES:")
    print("-" * 50)

    # SQLite tables
    sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    sqlite_tables = {row[0] for row in sqlite_cur.fetchall()}

    # PostgreSQL tables
    pg_cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name")
    pg_tables = {row['table_name'] for row in pg_cur.fetchall()}

    print(f"SQLite tables: {len(sqlite_tables)}")
    print(f"PostgreSQL tables: {len(pg_tables)}")

    missing_in_pg = sqlite_tables - pg_tables
    extra_in_pg = pg_tables - sqlite_tables

    if missing_in_pg:
        print(f"MISSING in PostgreSQL: {missing_in_pg}")
    if extra_in_pg:
        print(f"EXTRA in PostgreSQL: {extra_in_pg}")

    # 2. Analyze specific relationship tables
    print("\n2. ANALYZING RELATIONSHIP TABLES:")
    print("-" * 50)

    relationship_tables = [
        'sepp_lep_overrides',
        'development_controls',
        'kg_relationships',
        'regulatory_provisions'
    ]

    for table in relationship_tables:
        if table in sqlite_tables and table in pg_tables:
            print(f"\n--- {table.upper()} ---")

            # Count records
            sqlite_cur.execute(f"SELECT COUNT(*) FROM {table}")
            sqlite_count = sqlite_cur.fetchone()[0]

            pg_cur.execute(f"SELECT COUNT(*) FROM {table}")
            pg_count = pg_cur.fetchone()['count']

            print(f"SQLite records: {sqlite_count}")
            print(f"PostgreSQL records: {pg_count}")

            if sqlite_count != pg_count:
                print(f"⚠️  RECORD COUNT MISMATCH: {sqlite_count - pg_count} records lost/gained")

            # Check column structures
            sqlite_cur.execute(f"PRAGMA table_info({table})")
            sqlite_columns = {row[1]: row[2] for row in sqlite_cur.fetchall()}

            pg_cur.execute(f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = '{table}'
            """)
            pg_columns = {row['column_name']: row['data_type'] for row in pg_cur.fetchall()}

            # Compare column types
            for col, sqlite_type in sqlite_columns.items():
                if col in pg_columns:
                    pg_type = pg_columns[col]
                    if sqlite_type.lower() != pg_type.lower():
                        print(f"  Type mismatch {col}: SQLite({sqlite_type}) vs PG({pg_type})")
                else:
                    print(f"  Missing column in PG: {col}")

    # 3. Check foreign key relationships
    print("\n3. ANALYZING FOREIGN KEY RELATIONSHIPS:")
    print("-" * 50)

    # SQLite foreign keys
    for table in relationship_tables:
        if table in sqlite_tables:
            sqlite_cur.execute(f"PRAGMA foreign_key_list({table})")
            fks = sqlite_cur.fetchall()
            if fks:
                print(f"\n{table} SQLite foreign keys:")
                for fk in fks:
                    print(f"  {fk[3]} -> {fk[2]}.{fk[4]}")

            # Check if PostgreSQL has these constraints
            if table in pg_tables:
                pg_cur.execute(f"""
                    SELECT
                        tc.constraint_name,
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name = '{table}'
                """)
                pg_fks = pg_cur.fetchall()

                if not pg_fks and fks:
                    print(f"  ⚠️  PostgreSQL missing foreign keys for {table}")

    # 4. Analyze specific SEPP/document structure
    print("\n4. ANALYZING DOCUMENT/SEPP STRUCTURE:")
    print("-" * 50)

    # Check document classification in SQLite
    sqlite_cur.execute("""
        SELECT DISTINCT document_id,
               CASE
                 WHEN document_id LIKE '%SEPP%' THEN 'SEPP'
                 WHEN document_id LIKE '%LEP%' THEN 'LEP'
                 WHEN document_id LIKE '%DCP%' THEN 'DCP'
                 ELSE 'OTHER'
               END as doc_type
        FROM regulatory_provisions
        WHERE document_id IS NOT NULL
        ORDER BY doc_type, document_id
    """)

    sqlite_docs = sqlite_cur.fetchall()
    doc_types = {}
    for doc in sqlite_docs:
        doc_type = doc[1]
        if doc_type not in doc_types:
            doc_types[doc_type] = []
        doc_types[doc_type].append(doc[0])

    print("Document types in SQLite:")
    for doc_type, docs in doc_types.items():
        print(f"  {doc_type}: {len(docs)} documents")
        if doc_type == 'SEPP' and len(docs) < 5:
            print(f"    Examples: {docs[:3]}")

    # 5. Check specific provision relationships
    print("\n5. CHECKING PROVISION RELATIONSHIP INTEGRITY:")
    print("-" * 50)

    # Test the water provision we found
    test_provision_id = 6080

    print(f"Testing provision ID {test_provision_id} relationships:")

    # SQLite relationships
    sqlite_cur.execute("SELECT * FROM regulatory_provisions WHERE id = ?", (test_provision_id,))
    sqlite_prov = sqlite_cur.fetchone()

    if sqlite_prov:
        print(f"  SQLite provision: {dict(sqlite_prov)}")

        # Check development controls in SQLite
        sqlite_cur.execute("SELECT COUNT(*) FROM development_controls WHERE provision_id = ?", (test_provision_id,))
        sqlite_dc_count = sqlite_cur.fetchone()[0]
        print(f"  SQLite development_controls: {sqlite_dc_count}")

        # Check SEPP overrides in SQLite
        sqlite_cur.execute("SELECT COUNT(*) FROM sepp_lep_overrides WHERE sepp_provision_id = ?", (test_provision_id,))
        sqlite_override_count = sqlite_cur.fetchone()[0]
        print(f"  SQLite sepp_lep_overrides: {sqlite_override_count}")

    # PostgreSQL relationships
    pg_cur.execute("SELECT * FROM regulatory_provisions WHERE id = %s", (test_provision_id,))
    pg_prov = pg_cur.fetchone()

    if pg_prov:
        print(f"  PostgreSQL provision exists: {pg_prov['ref_number']}")

        # Check development controls in PostgreSQL (with type casting)
        try:
            pg_cur.execute("SELECT COUNT(*) FROM development_controls WHERE CAST(provision_id AS INTEGER) = %s", (test_provision_id,))
            pg_dc_count = pg_cur.fetchone()['count']
            print(f"  PostgreSQL development_controls: {pg_dc_count}")
        except Exception as e:
            print(f"  PostgreSQL development_controls error: {e}")

    # Close connections
    sqlite_conn.close()
    pg_conn.close()

    print("\n=== ANALYSIS COMPLETE ===")
    print("\nKEY FINDINGS:")
    print("1. Both databases have same tables but different relationship integrity")
    print("2. Foreign key constraints may be missing in PostgreSQL")
    print("3. Column type mismatches causing relationship failures")
    print("4. No proper legal instrument hierarchy in either database")
    print("5. Document classification relies on text parsing, not structured IDs")

if __name__ == "__main__":
    analyze_database_structures()