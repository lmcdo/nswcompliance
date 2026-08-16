#!/usr/bin/env python3
"""
Create comprehensive backup of regulatory_provisions after enrichment
Includes all v2 columns and metadata
"""

import json
import psycopg2
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def create_full_backup():
    """Create complete backup of regulatory_provisions"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)

    backup_file = backup_dir / f"regulatory_provisions_enriched_{timestamp}.json"

    print("=" * 70)
    print("CREATING FULL DATABASE BACKUP")
    print("=" * 70)
    print(f"\nBackup file: {backup_file}")

    conn = psycopg2.connect(os.environ['DATABASE_URL'], connect_timeout=60)
    cur = conn.cursor()

    # Set long timeout for large query
    cur.execute("SET statement_timeout = '600s'")

    try:
        # Get total count
        print("\n1. Counting provisions...")
        cur.execute("SELECT COUNT(*) FROM regulatory_provisions")
        total_count = cur.fetchone()[0]
        print(f"   Total provisions: {total_count}")

        # Get schema
        print("\n2. Fetching schema...")
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'regulatory_provisions'
            ORDER BY ordinal_position
        """)
        schema = [{"name": row[0], "type": row[1], "nullable": row[2]} for row in cur.fetchall()]
        print(f"   Columns: {len(schema)}")

        # Get enrichment statistics
        print("\n3. Gathering enrichment statistics...")
        cur.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE v2_dcp_layer IS NOT NULL) as has_layer,
                COUNT(*) FILTER (WHERE v2_topic IS NOT NULL) as has_topic,
                COUNT(*) FILTER (WHERE v2_applicable_zones IS NOT NULL) as has_zones,
                COUNT(*) FILTER (WHERE v2_applicable_dev_types IS NOT NULL) as has_dev_types,
                COUNT(*) FILTER (WHERE v2_dcp_layer = 'generic') as layer_generic,
                COUNT(*) FILTER (WHERE v2_dcp_layer = 'use_specific') as layer_use_specific,
                COUNT(*) FILTER (WHERE v2_dcp_layer = 'condition') as layer_condition,
                COUNT(*) FILTER (WHERE v2_dcp_layer = 'precinct') as layer_precinct
            FROM regulatory_provisions
        """)
        stats = cur.fetchone()

        enrichment_stats = {
            "total_provisions": stats[0],
            "has_layer": stats[1],
            "has_topic": stats[2],
            "has_zones": stats[3],
            "has_dev_types": stats[4],
            "layer_distribution": {
                "generic": stats[5],
                "use_specific": stats[6],
                "condition": stats[7],
                "precinct": stats[8]
            }
        }

        print(f"   Layer classification: {stats[1]} / {stats[0]}")
        print(f"   Topic classification: {stats[2]} / {stats[0]}")
        print(f"   Zone enrichment: {stats[3]} / {stats[0]}")
        print(f"   Dev-type enrichment: {stats[4]} / {stats[0]}")

        # Fetch all data
        print("\n4. Fetching all provision data...")
        print("   This may take a few minutes...")

        cur.execute("""
            SELECT *
            FROM regulatory_provisions
            ORDER BY id
        """)

        # Get column names
        columns = [desc[0] for desc in cur.description]

        # Fetch in batches to avoid memory issues
        batch_size = 5000
        all_data = []
        batch_num = 0

        while True:
            rows = cur.fetchmany(batch_size)
            if not rows:
                break

            batch_num += 1
            print(f"   Fetched batch {batch_num} ({len(rows)} rows)...")

            for row in rows:
                # Convert row to dict
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Convert special types
                    if isinstance(value, (list, dict)):
                        row_dict[col] = value  # Keep as is for JSON
                    elif hasattr(value, 'isoformat'):  # datetime
                        row_dict[col] = value.isoformat()
                    else:
                        row_dict[col] = value

                all_data.append(row_dict)

        print(f"   Total rows fetched: {len(all_data)}")

        # Create backup object
        backup_data = {
            "metadata": {
                "timestamp": timestamp,
                "created_at": datetime.now().isoformat(),
                "purpose": "Full backup after v2 enrichment restoration",
                "total_provisions": len(all_data),
                "database": "Supabase (aws-1-ap-southeast-2)"
            },
            "schema": schema,
            "enrichment_stats": enrichment_stats,
            "data": all_data
        }

        # Write backup
        print("\n5. Writing backup file...")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, default=str)

        file_size_mb = backup_file.stat().st_size / (1024 * 1024)
        print(f"   [OK] Backup written: {file_size_mb:.2f} MB")

        # Create metadata file
        metadata_file = backup_dir / f"regulatory_provisions_enriched_{timestamp}_metadata.txt"
        with open(metadata_file, 'w') as f:
            f.write(f"Backup Metadata\n")
            f.write(f"=" * 70 + "\n\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total provisions: {len(all_data)}\n\n")
            f.write(f"Enrichment Status:\n")
            f.write(f"  Layer classification: {enrichment_stats['has_layer']} / {enrichment_stats['total_provisions']}\n")
            f.write(f"  Topic classification: {enrichment_stats['has_topic']} / {enrichment_stats['total_provisions']}\n")
            f.write(f"  Zone enrichment: {enrichment_stats['has_zones']} / {enrichment_stats['total_provisions']}\n")
            f.write(f"  Dev-type enrichment: {enrichment_stats['has_dev_types']} / {enrichment_stats['total_provisions']}\n\n")
            f.write(f"Layer Distribution:\n")
            f.write(f"  Generic: {enrichment_stats['layer_distribution']['generic']}\n")
            f.write(f"  Use-specific: {enrichment_stats['layer_distribution']['use_specific']}\n")
            f.write(f"  Condition: {enrichment_stats['layer_distribution']['condition']}\n")
            f.write(f"  Precinct: {enrichment_stats['layer_distribution']['precinct']}\n\n")
            f.write(f"Files:\n")
            f.write(f"  Data: {backup_file.name} ({file_size_mb:.2f} MB)\n")
            f.write(f"  Metadata: {metadata_file.name}\n")

        print(f"   [OK] Metadata written: {metadata_file.name}")

        print("\n" + "=" * 70)
        print("BACKUP COMPLETE")
        print("=" * 70)
        print(f"\nBackup files:")
        print(f"  - {backup_file}")
        print(f"  - {metadata_file}")
        print(f"\nSize: {file_size_mb:.2f} MB")
        print(f"Provisions: {len(all_data)}")

        cur.close()
        conn.close()

        return str(backup_file)

    except Exception as e:
        print(f"\n[ERROR] Backup failed: {e}")
        import traceback
        traceback.print_exc()
        cur.close()
        conn.close()
        raise

if __name__ == "__main__":
    create_full_backup()
