"""
Extract Precinct Boundaries from NSW Planning Portal API

This script attempts to extract precinct boundaries using multiple strategies:
1. NSW Planning Portal API (check for precinct layers)
2. Approximate boundaries from known addresses within each precinct
3. Manual entry of boundary coordinates from DCP maps

For now, we'll start with strategy 2 (approximate boundaries) as a quick start,
then enhance with manual digitization of precise boundaries from DCP PDFs.
"""

import psycopg2
import requests
import json
from shapely.geometry import Point, Polygon, MultiPoint
from shapely import wkt
import time

# Database connection
conn = psycopg2.connect(
    dbname='nsw_planning',
    user='postgres',
    password='Duffysql1!',
    host='localhost',
    port='5432'
)
cur = conn.cursor()

# NSW Planning Portal API base URL
PLANNING_PORTAL_API = "https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi"


def get_property_coordinates(address):
    """Get coordinates for an address from NSW Planning Portal"""
    try:
        url = f"{PLANNING_PORTAL_API}/address"
        params = {'a': address, 'noOfRecords': 1}

        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            print(f"  API error for {address}: {response.status_code}")
            return None

        data = response.json()
        if not data or len(data) == 0:
            print(f"  No results for {address}")
            return None

        prop = data[0]
        prop_id = prop.get('propId')

        # Get geometry
        geom_url = f"https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer/5/query"
        geom_params = {
            'where': f'propid={prop_id}',
            'outFields': 'propid,address',
            'f': 'json'
        }

        geom_response = requests.get(geom_url, params=geom_params, timeout=10)
        if geom_response.status_code != 200:
            print(f"  Geometry API error: {geom_response.status_code}")
            return None

        geom_data = geom_response.json()
        if not geom_data.get('features') or len(geom_data['features']) == 0:
            print(f"  No geometry for {address}")
            return None

        # Extract first ring point (centroid approximation)
        rings = geom_data['features'][0]['geometry']['rings']
        if not rings or not rings[0]:
            return None

        # Get centroid of property polygon
        coords = rings[0]
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        centroid_x = sum(xs) / len(xs)
        centroid_y = sum(ys) / len(ys)

        # Convert from MGA94 Zone 56 (EPSG:7856) to WGS84 (EPSG:4326)
        # Approximate conversion (for more accuracy, use pyproj)
        # MGA to lat/lon rough conversion
        lon = (centroid_x - 500000) / 111320 + 147
        lat = centroid_y / 111320 - 33

        print(f"  OK: {address}: ({lon:.6f}, {lat:.6f})")
        return (lon, lat)

    except Exception as e:
        print(f"  Error getting coordinates for {address}: {e}")
        return None

    time.sleep(0.5)  # Rate limiting


def create_approximate_boundary(sample_addresses, precinct_id, precinct_name, lga):
    """
    Create approximate precinct boundary from sample addresses
    Uses convex hull of known addresses within the precinct
    """
    print(f"\n[*] Creating boundary for {precinct_id}: {precinct_name}")

    coords = []
    for address in sample_addresses:
        coord = get_property_coordinates(address)
        if coord:
            coords.append(coord)

    if len(coords) < 3:
        print(f"  ERROR: Not enough coordinates ({len(coords)}) to create boundary")
        return None

    # Create convex hull
    points = MultiPoint(coords)
    boundary = points.convex_hull

    # Buffer slightly to ensure all points are inside
    # 0.002 degrees ≈ 200 meters
    boundary = boundary.buffer(0.002)

    # Convert to WKT for PostgreSQL
    boundary_wkt = boundary.wkt

    print(f"  OK: Created boundary from {len(coords)} points")

    return boundary_wkt


# Sample addresses for each precinct (for approximate boundary creation)
# These are known addresses within each precinct - the more, the better
PRECINCT_SAMPLE_ADDRESSES = {
    '10_': {
        'name': 'Dulwich Hill North',
        'lga': 'INNER WEST',
        'former_council': 'Marrickville',
        'addresses': [
            '20 Pile Street Dulwich Hill 2203',
            '50 Gordon Street Dulwich Hill 2203',
            '30 Constitution Road Dulwich Hill 2203',
            '10 Dulwich Grove Dulwich Hill 2203',
        ]
    },
    '18_': {
        'name': 'Dulwich Hill Station North',
        'lga': 'INNER WEST',
        'former_council': 'Marrickville',
        'addresses': [
            '15 Railway Parade Dulwich Hill 2203',
            '25 Kingsland Road Dulwich Hill 2203',
            '10 Ewart Street Dulwich Hill 2203',
        ]
    },
    '22_': {
        'name': 'Dulwich Hill Station South Precinct 22',
        'lga': 'INNER WEST',
        'former_council': 'Marrickville',
        'addresses': [
            '50 Wardell Road Dulwich Hill 2203',
            '30 Terry Street Dulwich Hill 2203',
            '40 Victoria Road Dulwich Hill 2203',
        ]
    },
    '9_29': {
        'name': 'South Western Marrickville',
        'lga': 'INNER WEST',
        'former_council': 'Marrickville',
        'addresses': [
            '170 Illawarra Road Marrickville 2204',
            '22 Illawarra Road Marrickville 2204',
            '50 Harnett Avenue Marrickville 2204',
            '60 Hill Street Marrickville 2204',
        ]
    },
    '9_30': {
        'name': 'The Warren',
        'lga': 'INNER WEST',
        'former_council': 'Marrickville',
        'addresses': [
            '330 Illawarra Road Marrickville 2204',
            '350 Illawarra Road Marrickville 2204',
            '20 Warren Road Marrickville 2204',
            '30 Carrington Road Marrickville 2204',
            '40 Renwick Street Marrickville 2204',
        ]
    },
    '9_47': {
        'name': 'Addison Road Area',
        'lga': 'INNER WEST',
        'former_council': 'Marrickville',
        'addresses': [
            '180 Addison Road Marrickville 2204',
            '150 Addison Road Marrickville 2204',
            '200 Addison Road Marrickville 2204',
            '50 Fitzroy Street Marrickville 2204',
            '100 Sydenham Road Marrickville 2204',
        ]
    },
    '9_37': {
        'name': 'King Street and Enmore Road Commercial',
        'lga': 'INNER WEST',
        'former_council': 'Marrickville',
        'addresses': [
            '234 King Street Newtown 2042',
            '200 King Street Newtown 2042',
            '250 King Street Newtown 2042',
            '100 Enmore Road Newtown 2042',
            '120 Enmore Road Newtown 2042',
        ]
    },
}


def insert_precinct_boundary(precinct_id, precinct_name, lga, former_council, boundary_wkt, confidence_score, extraction_method):
    """Insert precinct boundary into database"""
    try:
        cur.execute("""
            INSERT INTO dcp_precinct_boundaries
            (precinct_id, precinct_name, lga, former_council, boundary, confidence_score, extraction_method)
            VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s, %s)
            ON CONFLICT (precinct_id, lga) DO UPDATE
            SET boundary = ST_GeomFromText(%s, 4326),
                confidence_score = %s,
                extraction_method = %s,
                updated_at = NOW()
        """, (
            precinct_id, precinct_name, lga, former_council, boundary_wkt,
            confidence_score, extraction_method,
            boundary_wkt, confidence_score, extraction_method
        ))
        conn.commit()
        print(f"  OK: Inserted into database (confidence: {confidence_score})")
        return True
    except Exception as e:
        print(f"  ERROR: Database error: {e}")
        conn.rollback()
        return False


def main():
    print("=== Precinct Boundary Extraction ===\n")

    # Check if PostGIS is installed
    try:
        cur.execute("SELECT PostGIS_Version()")
        version = cur.fetchone()[0]
        print(f"SUCCESS: PostGIS version: {version}\n")
    except Exception as e:
        print(f"ERROR: PostGIS not installed: {e}")
        print("Please run: python install_postgis.py")
        return

    # Check if table exists
    try:
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'dcp_precinct_boundaries'
            )
        """)
        table_exists = cur.fetchone()[0]
        if not table_exists:
            print("✗ Table dcp_precinct_boundaries does not exist")
            print("Please run: psql -d nsw_planning -f migrations/create_precinct_boundaries_postgis.sql")
            return
        print("SUCCESS: Table dcp_precinct_boundaries exists\n")
    except Exception as e:
        print(f"ERROR: Error checking table: {e}")
        return

    # Extract boundaries for each precinct
    print("Extracting precinct boundaries from sample addresses...\n")

    success_count = 0
    fail_count = 0

    for precinct_id, precinct_data in PRECINCT_SAMPLE_ADDRESSES.items():
        boundary_wkt = create_approximate_boundary(
            precinct_data['addresses'],
            precinct_id,
            precinct_data['name'],
            precinct_data['lga']
        )

        if boundary_wkt:
            if insert_precinct_boundary(
                precinct_id,
                precinct_data['name'],
                precinct_data['lga'],
                precinct_data.get('former_council'),
                boundary_wkt,
                confidence_score=0.6,  # Approximate boundaries have lower confidence
                extraction_method='approximated_from_addresses'
            ):
                success_count += 1
            else:
                fail_count += 1
        else:
            fail_count += 1

    # Summary
    print(f"\n=== Summary ===")
    print(f"SUCCESS: Created {success_count} precincts")
    print(f"FAILED: {fail_count} precincts")

    # Show what's in the database
    cur.execute("""
        SELECT precinct_id, precinct_name, lga, confidence_score,
               ROUND(area_sqm::numeric, 0) as area_sqm
        FROM dcp_precinct_boundaries
        ORDER BY precinct_id
    """)

    print(f"\n=== Precinct Boundaries in Database ===")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} ({row[2]}) - {row[4]} sqm (confidence: {row[3]})")

    cur.close()
    conn.close()

    print("\nSUCCESS: Extraction complete!")
    print("\nNext steps:")
    print("1. Test precinct matching: python test_precinct_matching.py")
    print("2. Update precinct-service.ts to use PostGIS queries")
    print("3. (Optional) Manually digitize more accurate boundaries from DCP maps")


if __name__ == "__main__":
    main()
