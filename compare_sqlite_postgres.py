#!/usr/bin/env python3
"""
Compare SQLite and PostgreSQL databases to understand data differences
"""

import sqlite3
import psycopg2
from pathlib import Path

def analyze_sqlite_db(db_path):
    """Analyze a SQLite database"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    stats = {}
    
    # Get all tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cur.fetchall()]
    stats['tables'] = tables
    stats['table_count'] = len(tables)
    
    # Check for regulatory_provisions table
    if 'regulatory_provisions' in tables:
        cur.execute("SELECT COUNT(*) FROM regulatory_provisions")
        stats['regulatory_provisions_count'] = cur.fetchone()[0]
        
        # Check for numeric values
        cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE numeric_value IS NOT NULL")
        stats['regulatory_provisions_numeric'] = cur.fetchone()[0]
        
        # Get zones
        cur.execute("SELECT COUNT(DISTINCT zone) FROM regulatory_provisions WHERE zone IS NOT NULL")
        stats['unique_zones'] = cur.fetchone()[0]
        
        # Sample zones with numeric data
        cur.execute("""
            SELECT zone, COUNT(*) as total, 
                   COUNT(CASE WHEN numeric_value IS NOT NULL THEN 1 END) as numeric
            FROM regulatory_provisions 
            WHERE zone IS NOT NULL
            GROUP BY zone
            ORDER BY numeric DESC
            LIMIT 10
        """)
        stats['top_zones'] = cur.fetchall()
    
    # Check for quantitative_standards table
    if 'quantitative_standards' in tables:
        cur.execute("SELECT COUNT(*) FROM quantitative_standards")
        stats['quantitative_standards_count'] = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(DISTINCT context) FROM quantitative_standards")
        stats['unique_contexts'] = cur.fetchone()[0]
    
    conn.close()
    return stats

def analyze_postgres_db():
    """Analyze PostgreSQL database"""
    conn = psycopg2.connect(
        host='localhost',
        database='nsw_planning',
        user='postgres',
        password='postgres'
    )
    cur = conn.cursor()
    
    stats = {}
    
    # Check public schema
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    public_tables = [row[0] for row in cur.fetchall()]
    stats['public_tables'] = public_tables
    
    # Check authoritative schema
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'authoritative'
    """)
    auth_tables = [row[0] for row in cur.fetchall()]
    stats['authoritative_tables'] = auth_tables
    
    # Check authoritative.planning_provisions
    cur.execute("SELECT COUNT(*) FROM authoritative.planning_provisions")
    stats['auth_provisions_count'] = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM authoritative.planning_provisions WHERE numeric_value IS NOT NULL")
    stats['auth_provisions_numeric'] = cur.fetchone()[0]
    
    # Check zones in authoritative
    cur.execute("""
        WITH zones AS (
            SELECT UNNEST(applicable_zones) as zone
            FROM authoritative.planning_provisions
            WHERE applicable_zones IS NOT NULL
        )
        SELECT COUNT(DISTINCT zone) FROM zones
    """)
    stats['auth_unique_zones'] = cur.fetchone()[0]
    
    # Check public.regulatory_provisions if exists
    if 'regulatory_provisions' in public_tables:
        cur.execute("SELECT COUNT(*) FROM public.regulatory_provisions")
        stats['public_provisions_count'] = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM public.regulatory_provisions WHERE numeric_value IS NOT NULL")
        stats['public_provisions_numeric'] = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(DISTINCT zone) FROM public.regulatory_provisions WHERE zone IS NOT NULL")
        stats['public_unique_zones'] = cur.fetchone()[0]
        
        # Top zones in public schema
        cur.execute("""
            SELECT zone, COUNT(*) as total,
                   COUNT(CASE WHEN numeric_value IS NOT NULL THEN 1 END) as numeric
            FROM public.regulatory_provisions
            WHERE zone IS NOT NULL
            GROUP BY zone
            ORDER BY numeric DESC
            LIMIT 10
        """)
        stats['public_top_zones'] = cur.fetchall()
    
    conn.close()
    return stats

# Main comparison
print("=" * 80)
print("SQLITE vs POSTGRESQL DATABASE COMPARISON")
print("=" * 80)

# Analyze main SQLite database
print("\n=== SQLITE DATABASE (nsw_planning.db) ===\n")
sqlite_stats = analyze_sqlite_db('nsw_planning.db')

print(f"Tables: {sqlite_stats['table_count']}")
if 'regulatory_provisions_count' in sqlite_stats:
    print(f"Regulatory Provisions: {sqlite_stats['regulatory_provisions_count']:,}")
    print(f"With Numeric Values: {sqlite_stats['regulatory_provisions_numeric']:,}")
    print(f"Unique Zones: {sqlite_stats['unique_zones']}")
    
    print("\nTop Zones by Numeric Data (SQLite):")
    for zone, total, numeric in sqlite_stats['top_zones']:
        percent = (numeric/total * 100) if total > 0 else 0
        print(f"  {zone:10} Total: {total:4} Numeric: {numeric:4} ({percent:.1f}%)")

if 'quantitative_standards_count' in sqlite_stats:
    print(f"\nQuantitative Standards: {sqlite_stats['quantitative_standards_count']:,}")
    print(f"Unique Contexts: {sqlite_stats['unique_contexts']}")

# Analyze PostgreSQL database
print("\n=== POSTGRESQL DATABASE ===\n")
pg_stats = analyze_postgres_db()

print(f"Public Schema Tables: {len(pg_stats['public_tables'])}")
print(f"Authoritative Schema Tables: {len(pg_stats['authoritative_tables'])}")

print("\nAuthoritative Schema:")
print(f"  Planning Provisions: {pg_stats['auth_provisions_count']:,}")
print(f"  With Numeric Values: {pg_stats['auth_provisions_numeric']:,}")
print(f"  Unique Zones: {pg_stats['auth_unique_zones']}")

if 'public_provisions_count' in pg_stats:
    print("\nPublic Schema:")
    print(f"  Regulatory Provisions: {pg_stats['public_provisions_count']:,}")
    print(f"  With Numeric Values: {pg_stats['public_provisions_numeric']:,}")
    print(f"  Unique Zones: {pg_stats['public_unique_zones']}")
    
    if 'public_top_zones' in pg_stats:
        print("\nTop Zones by Numeric Data (PostgreSQL Public):")
        for zone, total, numeric in pg_stats['public_top_zones']:
            percent = (numeric/total * 100) if total > 0 else 0
            print(f"  {zone:10} Total: {total:4} Numeric: {numeric:4} ({percent:.1f}%)")

# Comparison Summary
print("\n" + "=" * 80)
print("COMPARISON SUMMARY")
print("=" * 80)

if 'regulatory_provisions_count' in sqlite_stats:
    sqlite_total = sqlite_stats['regulatory_provisions_count']
    sqlite_numeric = sqlite_stats['regulatory_provisions_numeric']
else:
    sqlite_total = 0
    sqlite_numeric = 0

if 'public_provisions_count' in pg_stats:
    pg_public_total = pg_stats['public_provisions_count']
    pg_public_numeric = pg_stats['public_provisions_numeric']
else:
    pg_public_total = 0
    pg_public_numeric = 0

pg_auth_total = pg_stats['auth_provisions_count']
pg_auth_numeric = pg_stats['auth_provisions_numeric']

print(f"\nProvision Counts:")
print(f"  SQLite:                     {sqlite_total:,} total, {sqlite_numeric:,} numeric")
print(f"  PostgreSQL (public):        {pg_public_total:,} total, {pg_public_numeric:,} numeric")
print(f"  PostgreSQL (authoritative): {pg_auth_total:,} total, {pg_auth_numeric:,} numeric")

print(f"\nData Loss Analysis:")
if sqlite_total > 0:
    if pg_public_total > 0:
        public_loss = ((sqlite_total - pg_public_total) / sqlite_total) * 100
        print(f"  SQLite → PG Public: {public_loss:+.1f}% provisions")
    
    auth_loss = ((sqlite_total - pg_auth_total) / sqlite_total) * 100
    print(f"  SQLite → PG Authoritative: {auth_loss:+.1f}% provisions")
    
    if sqlite_numeric > 0:
        numeric_loss = ((sqlite_numeric - pg_auth_numeric) / sqlite_numeric) * 100
        print(f"  Numeric Data Loss: {numeric_loss:+.1f}%")

# Check the backup database too
print("\n=== BACKUP SQLITE DATABASE ===\n")
backup_db = 'nsw_planning_prp_k1_backup.db'
if Path(backup_db).exists():
    backup_stats = analyze_sqlite_db(backup_db)
    if 'regulatory_provisions_count' in backup_stats:
        print(f"Backup Regulatory Provisions: {backup_stats['regulatory_provisions_count']:,}")
        print(f"Backup Numeric Values: {backup_stats['regulatory_provisions_numeric']:,}")
        print(f"Backup Unique Zones: {backup_stats['unique_zones']}")