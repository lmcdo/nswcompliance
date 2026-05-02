"""
E2E validation matrix for flood_truth.py spatial_overlays data.

Tests known addresses against the live DB to confirm:
  - In-FPA addresses return ses_in_flood_planning_area=True
  - Out-of-FPA addresses in covered LGAs return False
  - LGAs with no data return None (unavailable signal)
  - ses_flood_class is a canonical display string (not snake_case)

Usage:
  cd <repo_root>
  source venv_linux/bin/activate
  python scripts/validate_flood_e2e.py

Exit code 0 = all assertions passed.
Exit code 1 = one or more assertions failed.
"""
import os
import sys
import json
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Load from the nearest .env.local (repo root when run from there)
load_dotenv(".env.local")

DB_URL = os.environ["DATABASE_URL"]


def _get_conn():
    return psycopg2.connect(DB_URL)


def _query(lat: float, lng: float) -> dict:
    """Reproduce _query_ses_flood_study() logic directly against the DB."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT COUNT(*) AS n FROM spatial_overlays WHERE layer_type = 'flood'"
            )
            if cur.fetchone()["n"] == 0:
                return {
                    "ses_in_flood_planning_area": None,
                    "ses_flood_class": None,
                    "ses_study_name": None,
                    "ses_study_lga": None,
                }
            cur.execute(
                """
                SELECT instrument_key, lga_name, value
                FROM spatial_overlays
                WHERE layer_type = 'flood'
                  AND ST_Intersects(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                ORDER BY currency_date DESC
                LIMIT 1
                """,
                (lng, lat),
            )
            row = cur.fetchone()
        if row:
            return {
                "ses_in_flood_planning_area": True,
                "ses_flood_class": row["value"],
                "ses_study_name": row["instrument_key"],
                "ses_study_lga": row["lga_name"],
            }
        # Check if LGA has any flood coverage at all (confirm False is meaningful)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS n
                FROM spatial_overlays
                WHERE layer_type = 'flood'
                  AND ST_DWithin(
                      geom,
                      ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                      0.5
                  )
                """,
                (lng, lat),
            )
            nearby = cur.fetchone()["n"]
        return {
            "ses_in_flood_planning_area": False,
            "ses_flood_class": None,
            "ses_study_name": None,
            "ses_study_lga": None,
            "_nearby_polygons": nearby,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Test matrix
# Each entry: (description, lat, lng, expected_in_fpa, expected_class_contains)
# expected_in_fpa: True | False | None
# expected_class_contains: substring that must appear in ses_flood_class (or None to skip)
# ---------------------------------------------------------------------------
TESTS = [
    # Hawkesbury — FPA shapefile (hawkesbury_fpa)
    (
        "Hawkesbury — Windsor town centre (known IN FPA)",
        -33.6134, 150.8130,
        True, "Flood Planning Area",
    ),
    (
        "Hawkesbury — Pitt Town (known IN FPA)",
        -33.5800, 150.8370,
        True, "Flood Planning Area",
    ),
    (
        "Hawkesbury — Richmond (on higher ground, should be outside FPA)",
        -33.5983, 150.7517,
        False, None,
    ),

    # Tweed — FeatureServer (tweed_flood: 1%AEP)
    (
        "Tweed — Murwillumbah low-lying area (known flood-prone)",
        -28.3275, 153.3985,
        True, "1%",
    ),
    (
        "Tweed — Tweed Heads hill area (should be outside)",
        -28.1728, 153.5455,
        False, None,
    ),

    # Byron — FPA FeatureServer (byron_fpa)
    (
        "Byron — Brunswick Heads low ground (floodplain)",
        -28.5430, 153.5422,
        True, "Flood Planning Area",
    ),

    # Port Macquarie-Hastings — FeatureServer (pmhc_flood)
    (
        "Port Macquarie — Camden Haven low area (known flood-prone)",
        -31.6470, 152.8310,
        True, "Flood Planning Area",
    ),

    # Lismore — EPI FeatureServer (lismore_epi_flood)
    (
        "Lismore — CBD area (known flood history)",
        -28.8144, 153.2760,
        True, "Flood Planning Area",
    ),

    # Ballina — EPI FeatureServer (ballina_epi_flood)
    (
        "Ballina — East Ballina low ground",
        -28.8705, 153.5750,
        True, "Flood Planning Area",
    ),

    # No-data LGA — should return None (unavailable)
    # Parramatta has no flood data ingested yet
    (
        "Parramatta — LGA with no flood coverage (expect None)",
        -33.8150, 151.0011,
        None, None,
    ),
]

# Raw DB values that are not yet normalised (snake_case) — these should NOT appear
SNAKE_CASE_VALUES = {"flood_planning_area", "design_flood"}


def run():
    passed = 0
    failed = 0

    print(f"\n{'='*70}")
    print("Flood E2E Validation Matrix")
    print(f"{'='*70}\n")

    for desc, lat, lng, exp_in_fpa, exp_class_substr in TESTS:
        result = _query(lat, lng)
        in_fpa = result["ses_in_flood_planning_area"]
        flood_class = result["ses_flood_class"]

        errors = []

        if in_fpa != exp_in_fpa:
            errors.append(
                f"ses_in_flood_planning_area: expected={exp_in_fpa}, got={in_fpa}"
            )

        if exp_class_substr and flood_class and exp_class_substr.lower() not in flood_class.lower():
            errors.append(
                f"ses_flood_class '{flood_class}' does not contain '{exp_class_substr}'"
            )

        if flood_class and flood_class in SNAKE_CASE_VALUES:
            errors.append(
                f"ses_flood_class '{flood_class}' is still snake_case — normalisation not applied"
            )

        if errors:
            failed += 1
            print(f"  FAIL  {desc}")
            for e in errors:
                print(f"        -> {e}")
            print(f"        raw result: {json.dumps(dict(result), default=str)}")
        else:
            passed += 1
            extra = f" [{flood_class}]" if flood_class else ""
            nearby = result.get("_nearby_polygons", "")
            nearby_note = f" (nearby polygons within 0.5°: {nearby})" if nearby != "" else ""
            print(f"  PASS  {desc}{extra}{nearby_note}")

    print(f"\n{'='*70}")
    print(f"Results: {passed} passed, {failed} failed out of {len(TESTS)} tests")
    print(f"{'='*70}\n")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    run()
