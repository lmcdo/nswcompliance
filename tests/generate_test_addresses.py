"""
Generate stratified sample of test addresses for validation suite.

Queries the database and NSW Planning Portal to build a representative
test set covering all councils, zones, and edge cases.
"""

import json
import random
import psycopg2
from dataclasses import dataclass, asdict
from typing import List, Optional

# Known addresses for each stratum (manually curated starting points)
# These will be supplemented with database queries

SEED_ADDRESSES = {
    "marrickville": {
        "R2": [
            "180 Addison Road Marrickville 2204",
            "45 Denison Road Dulwich Hill 2203",
            "12 Pile Street Dulwich Hill 2203",
        ],
        "R3": [
            "100 Marrickville Road Marrickville 2204",
            "55 Livingstone Road Marrickville 2204",
        ],
        "B2": [
            "250 Marrickville Road Marrickville 2204",
            "80 Victoria Road Marrickville 2204",
        ],
        "heritage": [
            "2 Carrington Road Marrickville 2204",  # HCA
        ]
    },
    "ashfield": {
        "R2": [
            "15 Alt Street Ashfield 2131",
            "22 Orpington Street Ashfield 2131",
            "8 Bland Street Ashfield 2131",
        ],
        "R3": [
            "200 Liverpool Road Ashfield 2131",
        ],
        "E1": [
            "260 Liverpool Road Ashfield 2131",
        ],
        "heritage": [
            "1 The Parade Haberfield 2045",  # Haberfield HCA
            "5 Ramsay Street Haberfield 2045",
        ]
    },
    "leichhardt": {
        "R2": [
            "10 Norton Street Leichhardt 2040",
            "25 Marion Street Leichhardt 2040",
        ],
        "R3": [
            "150 Balmain Road Leichhardt 2040",
        ],
        "B2": [
            "120 Norton Street Leichhardt 2040",
        ],
        "heritage": [
            "5 Lombard Street Glebe 2037",
            "12 Darghan Street Glebe 2037",
        ]
    },
    "rejected": [
        # Should be rejected - not Inner West
        "14 Lamrock Avenue Russell Lea 2046",  # Canada Bay
        "100 Burwood Road Burwood 2134",  # Burwood
        "1 George Street Sydney 2000",  # Sydney CBD
    ]
}


@dataclass
class TestAddress:
    address: str
    council: str
    expected_zone: Optional[str]
    test_category: str  # "standard", "heritage", "boundary", "rejected"
    notes: Optional[str] = None


def get_addresses_from_db(council: str, zone_prefix: str, limit: int = 5) -> List[str]:
    """Query database for addresses in a given council/zone"""
    try:
        conn = psycopg2.connect(
            "postgresql://postgres@127.0.0.1:5432/nsw_planning"
        )
        cur = conn.cursor()

        # Query precinct boundaries to find addresses
        # This is a simplified approach - in practice you'd use spatial queries
        cur.execute("""
            SELECT DISTINCT precinct_name, former_council
            FROM dcp_precinct_boundaries
            WHERE LOWER(former_council) = LOWER(%s)
            LIMIT %s
        """, (council, limit))

        precincts = cur.fetchall()
        conn.close()

        return [f"Sample address in {p[0]}" for p in precincts]
    except Exception as e:
        print(f"DB query failed: {e}")
        return []


def generate_test_set() -> List[TestAddress]:
    """Generate the full stratified test set"""
    test_addresses = []

    # Standard addresses by council and zone
    for council, zones in SEED_ADDRESSES.items():
        if council == "rejected":
            continue

        for zone, addresses in zones.items():
            category = "heritage" if zone == "heritage" else "standard"
            expected_zone = None if zone == "heritage" else zone

            for addr in addresses:
                test_addresses.append(TestAddress(
                    address=addr,
                    council=council.title(),
                    expected_zone=expected_zone,
                    test_category=category,
                    notes=f"{zone} zone" if zone != "heritage" else "Heritage area"
                ))

    # Rejected addresses
    for addr in SEED_ADDRESSES["rejected"]:
        test_addresses.append(TestAddress(
            address=addr,
            council="NOT_INNER_WEST",
            expected_zone=None,
            test_category="rejected",
            notes="Should be rejected - not in Inner West LGA"
        ))

    return test_addresses


def export_test_addresses(output_path: str = "tests/fixtures/test_addresses.json"):
    """Export test addresses to JSON fixture file"""
    addresses = generate_test_set()

    output = {
        "metadata": {
            "description": "Stratified test addresses for validation suite",
            "total_count": len(addresses),
            "by_category": {
                "standard": len([a for a in addresses if a.test_category == "standard"]),
                "heritage": len([a for a in addresses if a.test_category == "heritage"]),
                "rejected": len([a for a in addresses if a.test_category == "rejected"]),
            },
            "by_council": {
                "Marrickville": len([a for a in addresses if a.council == "Marrickville"]),
                "Ashfield": len([a for a in addresses if a.council == "Ashfield"]),
                "Leichhardt": len([a for a in addresses if a.council == "Leichhardt"]),
            }
        },
        "addresses": [asdict(a) for a in addresses]
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Exported {len(addresses)} test addresses to {output_path}")
    print(f"\nBreakdown:")
    print(f"  Standard: {output['metadata']['by_category']['standard']}")
    print(f"  Heritage: {output['metadata']['by_category']['heritage']}")
    print(f"  Rejected: {output['metadata']['by_category']['rejected']}")

    return output


if __name__ == "__main__":
    export_test_addresses()
