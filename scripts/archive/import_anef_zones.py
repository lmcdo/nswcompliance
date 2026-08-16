#!/usr/bin/env python3
"""
Import ANEF zones from GeoJSON into Supabase.

Usage:
    python scripts/import_anef_zones.py
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import Json

load_dotenv()


def calculate_bbox(coordinates: list) -> tuple:
    """Calculate bounding box from polygon coordinates."""
    ring = coordinates[0]  # Outer ring
    lons = [coord[0] for coord in ring]
    lats = [coord[1] for coord in ring]
    return (min(lons), max(lons), min(lats), max(lats))


def parse_airport_info(airport_str: str) -> tuple:
    """Parse airport string like 'Sydney (YSSY)' into name and code."""
    if '(' in airport_str and ')' in airport_str:
        name = airport_str.split('(')[0].strip()
        code = airport_str.split('(')[1].replace(')', '').strip()
        return name, code
    return airport_str, airport_str[:4].upper()


def main():
    # Load GeoJSON
    geojson_path = project_root / 'data' / 'anef' / 'sydney_anef_zones.geojson'

    if not geojson_path.exists():
        print(f"Error: GeoJSON file not found at {geojson_path}")
        sys.exit(1)

    with open(geojson_path, 'r') as f:
        data = json.load(f)

    print(f"Loaded {len(data['features'])} ANEF zones from GeoJSON")

    # Connect to database
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL not set in environment")
        sys.exit(1)

    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    try:
        # Check if table exists, create if not
        cur.execute("""
            CREATE TABLE IF NOT EXISTS anef_zones (
                id SERIAL PRIMARY KEY,
                airport_code VARCHAR(10) NOT NULL,
                airport_name VARCHAR(100) NOT NULL,
                anef_version VARCHAR(50) NOT NULL,
                anef_level INTEGER NOT NULL,
                zone_type VARCHAR(20),
                geometry_json JSONB NOT NULL,
                bbox_min_lon NUMERIC(10, 6),
                bbox_max_lon NUMERIC(10, 6),
                bbox_min_lat NUMERIC(10, 6),
                bbox_max_lat NUMERIC(10, 6),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Clear existing Sydney Airport data
        cur.execute("DELETE FROM anef_zones WHERE airport_code = 'YSSY'")
        deleted = cur.rowcount
        if deleted > 0:
            print(f"Cleared {deleted} existing YSSY records")

        # Insert new records
        inserted = 0
        for feature in data['features']:
            props = feature['properties']
            geom = feature['geometry']

            airport_name, airport_code = parse_airport_info(props.get('airport', 'Sydney'))
            anef_version = props.get('version', 'ANEF 2039')
            anef_level = props.get('anef_level', 0)
            zone_type = props.get('zone_type', None)

            # Calculate bounding box
            bbox = calculate_bbox(geom['coordinates'])

            cur.execute("""
                INSERT INTO anef_zones
                (airport_code, airport_name, anef_version, anef_level, zone_type,
                 geometry_json, bbox_min_lon, bbox_max_lon, bbox_min_lat, bbox_max_lat)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                airport_code,
                airport_name,
                anef_version,
                anef_level,
                zone_type,
                Json(geom),
                bbox[0], bbox[1], bbox[2], bbox[3]
            ))
            inserted += 1
            print(f"  Inserted ANEF {anef_level} zone (bbox: {bbox[0]:.3f},{bbox[2]:.3f} to {bbox[1]:.3f},{bbox[3]:.3f})")

        # Create indexes if they don't exist
        cur.execute("CREATE INDEX IF NOT EXISTS idx_anef_zones_airport ON anef_zones(airport_code)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_anef_zones_level ON anef_zones(anef_level)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_anef_zones_bbox ON anef_zones(bbox_min_lon, bbox_max_lon, bbox_min_lat, bbox_max_lat)")

        conn.commit()
        print(f"\nSuccessfully imported {inserted} ANEF zones")

        # Verify
        cur.execute("SELECT anef_level, bbox_min_lon, bbox_max_lon, bbox_min_lat, bbox_max_lat FROM anef_zones WHERE airport_code = 'YSSY' ORDER BY anef_level")
        rows = cur.fetchall()
        print("\nVerification:")
        for row in rows:
            print(f"  ANEF {row[0]}: lon [{row[1]:.3f}, {row[2]:.3f}], lat [{row[3]:.3f}, {row[4]:.3f}]")

    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    main()
