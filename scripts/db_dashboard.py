#!/usr/bin/env python3
"""Quick database dashboard."""

import psycopg2
from datetime import datetime

def dashboard():
    conn = psycopg2.connect(
        host="localhost",
        database="nsw_planning",
        user="postgres",
        password="postgres"
    )
    cur = conn.cursor()

    print(f"\n{'='*60}")
    print(f"DATABASE DASHBOARD - {datetime.now()}")
    print(f"{'='*60}\n")

    # Table sizes
    cur.execute("""
        SELECT
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        LIMIT 5;
    """)

    print("LARGEST TABLES:")
    for table, size in cur.fetchall():
        print(f"   {table:40s} {size}")

    # Statistics age
    cur.execute("""
        SELECT
            relname,
            last_analyze,
            NOW() - last_analyze as age
        FROM pg_stat_user_tables
        WHERE schemaname = 'public'
          AND relname IN ('documents', 'regulatory_provisions')
        ORDER BY relname;
    """)

    print("\nSTATISTICS AGE:")
    for table, last_analyze, age in cur.fetchall():
        if last_analyze:
            print(f"   {table:40s} {age}")
        else:
            print(f"   {table:40s} NEVER ANALYZED [ERROR]")

    # Row counts
    cur.execute("""
        SELECT
            'documents' as table, COUNT(*) as count FROM documents
        UNION ALL
        SELECT
            'regulatory_provisions', COUNT(*) FROM regulatory_provisions
        UNION ALL
        SELECT
            'development_controls', COUNT(*) FROM development_controls;
    """)

    print("\nROW COUNTS:")
    for table, count in cur.fetchall():
        print(f"   {table:40s} {count:,}")

    # Connections
    cur.execute("""
        SELECT
            state,
            COUNT(*) as count
        FROM pg_stat_activity
        WHERE datname = 'nsw_planning'
        GROUP BY state;
    """)

    print("\nCONNECTIONS:")
    for state, count in cur.fetchall():
        print(f"   {state:40s} {count}")

    # Autovacuum status
    cur.execute("""
        SELECT
            relname,
            last_vacuum,
            last_autovacuum,
            last_analyze,
            last_autoanalyze
        FROM pg_stat_user_tables
        WHERE schemaname = 'public'
          AND relname IN ('documents', 'regulatory_provisions')
        ORDER BY relname;
    """)

    print("\nAUTOVACUUM STATUS:")
    for table, vac, auto_vac, ana, auto_ana in cur.fetchall():
        print(f"   {table}:")
        print(f"      Last vacuum: {vac or 'NEVER'}")
        print(f"      Last autovacuum: {auto_vac or 'NEVER'}")
        print(f"      Last analyze: {ana or 'NEVER'}")
        print(f"      Last autoanalyze: {auto_ana or 'NEVER'}")

    print(f"\n{'='*60}\n")

    cur.close()
    conn.close()

if __name__ == "__main__":
    dashboard()
