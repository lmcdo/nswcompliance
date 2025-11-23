#!/usr/bin/env python3
"""
Compare local PostgreSQL database with Supabase production database.
Used to check sync status before deployments.
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor

def get_local_connection():
    """Connect to local PostgreSQL database."""
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=os.getenv('PGPORT', '5432'),
        database=os.getenv('PGDATABASE', 'nsw_planning'),
        user=os.getenv('PGUSER', 'postgres'),
        password=os.getenv('PGPASSWORD', 'postgres')
    )

def get_supabase_connection():
    """Connect to Supabase production database."""
    url = os.getenv('SUPABASE_DB_URL')
    if not url:
        print("ERROR: SUPABASE_DB_URL not set in .env")
        print("Add this to your .env file:")
        print("SUPABASE_DB_URL=postgresql://postgres.xxx:PASSWORD@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres")
        sys.exit(1)
    return psycopg2.connect(url)

def count_provisions(conn, label):
    """Count provisions with different filters."""
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Total provisions
    cur.execute("SELECT COUNT(*) as cnt FROM regulatory_provisions")
    total = cur.fetchone()['cnt']

    # Check if v2_ columns exist
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'regulatory_provisions' AND column_name = 'v2_is_actionable'
    """)
    has_v2_columns = cur.fetchone() is not None

    v2_actionable = 0
    v2_by_layer = {}

    if has_v2_columns:
        cur.execute("SELECT COUNT(*) as cnt FROM regulatory_provisions WHERE v2_is_actionable = true")
        v2_actionable = cur.fetchone()['cnt']

        cur.execute("""
            SELECT v2_dcp_layer, COUNT(*) as cnt
            FROM regulatory_provisions
            WHERE v2_is_actionable = true
            GROUP BY v2_dcp_layer
        """)
        for row in cur.fetchall():
            v2_by_layer[row['v2_dcp_layer'] or 'NULL'] = row['cnt']

    return {
        'label': label,
        'total': total,
        'has_v2_columns': has_v2_columns,
        'v2_actionable': v2_actionable,
        'v2_by_layer': v2_by_layer
    }

def main():
    print("=" * 60)
    print("LOCAL vs SUPABASE DATABASE COMPARISON")
    print("=" * 60)

    # Connect to local
    print("\n1. Connecting to LOCAL database...")
    try:
        local_conn = get_local_connection()
        local_stats = count_provisions(local_conn, "LOCAL")
        local_conn.close()
        print(f"   Connected successfully")
    except Exception as e:
        print(f"   ERROR: {e}")
        local_stats = None

    # Connect to Supabase
    print("\n2. Connecting to SUPABASE database...")
    try:
        supa_conn = get_supabase_connection()
        supa_stats = count_provisions(supa_conn, "SUPABASE")
        supa_conn.close()
        print(f"   Connected successfully")
    except Exception as e:
        print(f"   ERROR: {e}")
        supa_stats = None

    # Compare
    print("\n" + "=" * 60)
    print("COMPARISON RESULTS")
    print("=" * 60)

    if local_stats and supa_stats:
        print(f"\n{'Metric':<30} {'LOCAL':>12} {'SUPABASE':>12} {'MATCH':>8}")
        print("-" * 62)

        # Total provisions
        match = "YES" if local_stats['total'] == supa_stats['total'] else "NO"
        print(f"{'Total provisions':<30} {local_stats['total']:>12} {supa_stats['total']:>12} {match:>8}")

        # v2 columns exist
        local_v2 = "Yes" if local_stats['has_v2_columns'] else "No"
        supa_v2 = "Yes" if supa_stats['has_v2_columns'] else "No"
        match = "YES" if local_stats['has_v2_columns'] == supa_stats['has_v2_columns'] else "NO"
        print(f"{'Has v2_ columns':<30} {local_v2:>12} {supa_v2:>12} {match:>8}")

        # v2 actionable count
        match = "YES" if local_stats['v2_actionable'] == supa_stats['v2_actionable'] else "NO"
        print(f"{'v2_is_actionable = true':<30} {local_stats['v2_actionable']:>12} {supa_stats['v2_actionable']:>12} {match:>8}")

        # By layer
        if local_stats['v2_by_layer'] or supa_stats['v2_by_layer']:
            print("\nBy v2_dcp_layer:")
            all_layers = set(local_stats['v2_by_layer'].keys()) | set(supa_stats['v2_by_layer'].keys())
            for layer in sorted(all_layers):
                local_cnt = local_stats['v2_by_layer'].get(layer, 0)
                supa_cnt = supa_stats['v2_by_layer'].get(layer, 0)
                match = "YES" if local_cnt == supa_cnt else "NO"
                print(f"  {layer:<28} {local_cnt:>12} {supa_cnt:>12} {match:>8}")

        # Summary
        print("\n" + "=" * 60)
        if local_stats['v2_actionable'] > supa_stats['v2_actionable']:
            diff = local_stats['v2_actionable'] - supa_stats['v2_actionable']
            print(f"ACTION NEEDED: Local has {diff} more v2_ enriched provisions")
            print("Run: python scripts/sync_v2_to_supabase.py")
        elif local_stats['v2_actionable'] < supa_stats['v2_actionable']:
            diff = supa_stats['v2_actionable'] - local_stats['v2_actionable']
            print(f"WARNING: Supabase has {diff} more v2_ enriched provisions than local")
        else:
            print("DATABASES IN SYNC (v2_ columns match)")

        if not supa_stats['has_v2_columns']:
            print("\nACTION NEEDED: Run migration on Supabase first:")
            print("psql $SUPABASE_DB_URL -f migrations/001_add_v2_columns.sql")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
