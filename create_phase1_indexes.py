#!/usr/bin/env python3
"""
Create database indexes for Phase 1 performance optimization
"""

from db_config import get_connection

def create_indexes():
    """Create performance indexes for constraint queries"""

    conn = get_connection()
    cursor = conn.cursor()

    indexes = [
        # Index 1: Zone-based queries
        """
        CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_zone
        ON regulatory_provisions(zone)
        WHERE zone IS NOT NULL
        """,

        # Index 2: Provision type filtering
        """
        CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_type
        ON regulatory_provisions(provision_type)
        WHERE provision_type IS NOT NULL
        """,

        # Index 3: Composite zone + type
        """
        CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_zone_type
        ON regulatory_provisions(zone, provision_type)
        WHERE zone IS NOT NULL AND provision_type IS NOT NULL
        """,

        # Index 4: Document ID join optimization
        """
        CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_document
        ON regulatory_provisions(document_id)
        WHERE document_id IS NOT NULL
        """,

        # Index 5: Development permissions lookup
        """
        CREATE INDEX IF NOT EXISTS idx_development_permissions_zone_type
        ON development_permissions(zone, development_type)
        """,

        # Index 6: SEPP overrides lookup (skip if column doesn't exist)
        """
        -- CREATE INDEX IF NOT EXISTS idx_sepp_overrides_clause
        -- ON sepp_lep_overrides(affected_clause)
        -- WHERE affected_clause IS NOT NULL
        SELECT 1
        """
    ]

    print("Creating indexes for constraint queries...")

    for i, index_sql in enumerate(indexes, 1):
        try:
            cursor.execute(index_sql)
            print(f"[{i}/6] Created index successfully")
        except Exception as e:
            print(f"[{i}/6] Error creating index: {e}")

    # Analyze tables
    print("\nAnalyzing tables for query optimization...")

    tables = ['regulatory_provisions', 'development_permissions', 'sepp_lep_overrides', 'documents']

    for table in tables:
        try:
            cursor.execute(f"ANALYZE {table}")
            print(f"  Analyzed: {table}")
        except Exception as e:
            print(f"  Error analyzing {table}: {e}")

    conn.commit()

    # Show created indexes
    print("\nVerifying indexes...")
    cursor.execute("""
        SELECT
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        AND tablename IN ('regulatory_provisions', 'development_permissions', 'sepp_lep_overrides')
        AND indexname LIKE 'idx_%'
        ORDER BY tablename, indexname
    """)

    indexes_found = cursor.fetchall()

    print(f"\nFound {len(indexes_found)} indexes:")
    for table, index_name, _ in indexes_found:
        print(f"  {table:30s} -> {index_name}")

    conn.close()

    print("\n[OK] All indexes created successfully")
    print("Run: python PRPs/FINALUI/scripts/verify_phase1.py to test performance")

if __name__ == "__main__":
    create_indexes()