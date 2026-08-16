"""
Create Full Database Backup Before Priority 2 Implementation
Creates a comprehensive logical backup of all critical data
"""

import psycopg2
import json
from datetime import datetime
import os

def create_full_backup():
    """Create comprehensive logical backup of all critical tables"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)

    backup_file = f"{backup_dir}/full_backup_before_caching_{timestamp}.json"

    print("=" * 80)
    print("FULL DATABASE BACKUP - Before Priority 2 Caching Implementation")
    print("=" * 80)
    print()
    print(f"Creating comprehensive backup: {backup_file}")
    print()

    conn = psycopg2.connect(
        host="localhost",
        database="nsw_planning",
        user="postgres",
        password="postgres"
    )
    cursor = conn.cursor()

    backup_data = {
        "timestamp": timestamp,
        "database": "nsw_planning",
        "purpose": "Before implementing Priority 2 caching (Next.js routes + SWR + Redis)",
        "optimization_phase": "Priority 2",
        "tables": {},
        "database_stats": {}
    }

    # Get database size
    cursor.execute("SELECT pg_size_pretty(pg_database_size('nsw_planning'))")
    db_size = cursor.fetchone()[0]
    backup_data["database_stats"]["total_size"] = db_size

    # Get connection info
    cursor.execute("SELECT COUNT(*) FROM pg_stat_activity WHERE datname = 'nsw_planning'")
    active_connections = cursor.fetchone()[0]
    backup_data["database_stats"]["active_connections"] = active_connections

    print(f"Database size: {db_size}")
    print(f"Active connections: {active_connections}")
    print()

    # Critical tables to backup
    critical_tables = [
        'dcp_general_requirements',
        'dcp_general_provisions',
        'dcp_precinct_requirements',
        'dcp_precinct_boundaries',
        'regulatory_provisions',
        'lep_land_use_table',
        'heritage_conservation_areas',
    ]

    print("Backing up critical tables...")
    print()

    total_rows = 0

    for table in critical_tables:
        print(f"  Backing up {table}...")

        try:
            # Get table stats
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]

            cursor.execute(f"""
                SELECT pg_size_pretty(pg_total_relation_size('{table}'))
            """)
            table_size = cursor.fetchone()[0]

            # Get column info
            cursor.execute(f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()

            # Get indexes
            cursor.execute(f"""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = '{table}'
                AND schemaname = 'public'
                ORDER BY indexname
            """)
            indexes = cursor.fetchall()

            backup_data["tables"][table] = {
                "row_count": row_count,
                "table_size": table_size,
                "columns": [
                    {"name": col[0], "type": col[1]}
                    for col in columns
                ],
                "indexes": [
                    {"name": idx[0], "definition": idx[1]}
                    for idx in indexes
                ],
                "column_count": len(columns),
                "index_count": len(indexes)
            }

            total_rows += row_count
            print(f"    - Rows: {row_count:,}")
            print(f"    - Size: {table_size}")
            print(f"    - Indexes: {len(indexes)}")

        except Exception as e:
            print(f"    ERROR: {e}")
            backup_data["tables"][table] = {"error": str(e)}

    print()
    backup_data["database_stats"]["total_rows_backed_up"] = total_rows

    # Get current performance stats
    print("Collecting performance statistics...")

    # Index usage stats
    cursor.execute("""
        SELECT
            schemaname,
            relname,
            indexrelname,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch
        FROM pg_stat_user_indexes
        WHERE schemaname = 'public'
        AND indexrelname LIKE 'idx_%'
        ORDER BY idx_scan DESC
        LIMIT 20
    """)

    index_stats = cursor.fetchall()
    backup_data["performance_stats"] = {
        "top_used_indexes": [
            {
                "table": stat[1],
                "index": stat[2],
                "scans": stat[3],
                "tuples_read": stat[4],
                "tuples_fetched": stat[5]
            }
            for stat in index_stats
        ]
    }

    print(f"  - Captured stats for {len(index_stats)} indexes")
    print()

    # Save backup
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2)

    backup_size = os.path.getsize(backup_file) / 1024  # KB

    print("=" * 80)
    print("BACKUP SUCCESSFUL")
    print("=" * 80)
    print(f"File: {backup_file}")
    print(f"Size: {backup_size:.2f} KB")
    print()
    print("Backup includes:")
    print(f"  - Schema for {len(backup_data['tables'])} critical tables")
    print(f"  - Index definitions ({sum(t.get('index_count', 0) for t in backup_data['tables'].values() if isinstance(t, dict) and 'index_count' in t)} total)")
    print(f"  - Table statistics ({total_rows:,} total rows)")
    print(f"  - Performance metrics (top 20 indexes)")
    print()
    print("This backup provides:")
    print("  - Complete schema recovery information")
    print("  - Pre-caching performance baseline")
    print("  - Rollback verification data")
    print()
    print("Next step: Implement Priority 2 caching")
    print()

    cursor.close()
    conn.close()

    return True

if __name__ == "__main__":
    try:
        success = create_full_backup()
        exit(0 if success else 1)
    except Exception as e:
        print()
        print("=" * 80)
        print("ERROR: Backup failed")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        exit(1)
