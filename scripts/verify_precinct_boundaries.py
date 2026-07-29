#!/usr/bin/env python3
"""
Precinct Boundary Verification — dcp_precinct_boundaries health check
======================================================================
Run before and after any import to confirm nothing is broken.

Checks:
  1. Geometry type — all must be MULTIPOLYGON
  2. Invalid geometries — ST_IsValid failures (self-intersections etc.)
  3. Point-in-polygon self-test — centroid of each precinct should be inside it
     (exceptions flagged separately for known elongated precincts)
  4. LGA name consistency — detects case variants and trailing spaces
  5. Known address spot checks — real coords that must hit specific precincts
  6. Coverage summary — count by LGA

Exit code 0 = all checks pass (warnings allowed)
Exit code 1 = failures detected

Usage:
    python3 scripts/verify_precinct_boundaries.py
    python3 scripts/verify_precinct_boundaries.py --lga "City of Sydney"
    python3 scripts/verify_precinct_boundaries.py --verbose
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"]

# Known good test points: (lon, lat, expected_precinct_id, label)
# Add new entries here when onboarding each new LGA.
KNOWN_POINTS = [
    # Inner West — Marrickville precincts
    (151.14752, -33.89172, "1_",   "Lewisham North (Marrickville)"),
    (151.13851, -33.89811, "10_",  "Dulwich Hill North (Marrickville)"),
    (151.15822, -33.90381, "13_",  "Henson Park (Marrickville)"),
    (151.17598, -33.90368, "14_",  "Camdenville (Marrickville)"),
    # Inner West — Leichhardt precincts (add real coords once confirmed)
    # Inner West — Ashfield precincts (add real coords once confirmed)
    # City of Sydney — coords geocoded via SIX Address_Location 2026-07-29;
    # each point also sits inside its locality sub-area / specific-area polygons
    # (multi-membership listed in the label; the check asserts membership only).
    (151.2067248368, -33.9048022299, "6.3.3", "904 Bourke St Zetland (also 2.5.8, 5.2)"),
    (151.2117495867, -33.8659150961, "6.3.24", "2 Chifley Sq Sydney (also 2.1.12, 5.1)"),
    (151.1890328271, -33.9074964885, "6.2.4", "18 Huntley St Alexandria (also 2.7.11)"),
    # Ku-ring-gai (add once Part 14 provisions are extracted)
    # Waverley DCP 2022 Part E — coords geocoded via NSW Planning Portal lot
    # centroids 2026-07-28; expectations from adopted DCP figures (E1 Fig 1,
    # E2 Fig 42). 113 Macpherson St is inside BOTH E5 and the E3 village
    # centre; the script checks membership, so E5 is listed as expected.
    (151.25275, -33.89091, "E1", "500 Oxford St Bondi Junction — Westfield (Waverley)"),
    (151.27483, -33.88977, "E2", "178 Campbell Pde Bondi Beach (Waverley)"),
    (151.26251, -33.90627, "E5", "113 Macpherson St Bronte (Waverley)"),
    # E7 = union of the cadastre block bound by Birrell/Carrington/Church/Bronte
    # (the DCP's own text definition, p390); probe point is block interior.
    (151.25220, -33.89720, "E7", "Edina Estate block interior (Waverley)"),
]

# Known exceptions: precincts where centroid legitimately falls outside boundary
# (elongated commercial corridors, L-shaped precincts etc.)
CENTROID_EXCEPTIONS = {
    "35_",       # Parramatta Rd Commercial Precinct — long linear corridor
    "37_",       # King St and Enmore Rd Commercial Precinct — long linear corridor
    "C2.2.2.1",  # Darling Street Distinctive Neighbourhood — complex shape
    "14O",       # Pymble Golf Club — 3 non-contiguous lots, centroid falls in gap
    "E2",        # Waverley Bondi Beachfront — 5 separate strips around the beach
    "E3",        # Waverley Local Village Centres — 94 scattered polygons LGA-wide
    "E4",        # Waverley Special Character Areas — 3 separate areas
    "2.13.9",    # CoS Redfern Street and Redfern Park — L-shaped corridor + park
}


def run_checks(cur, lga_filter: str | None, verbose: bool) -> tuple[int, int]:
    """Returns (failures, warnings)."""
    failures = 0
    warnings = 0

    # ── 1. Column type ────────────────────────────────────────────────────────
    cur.execute("""
        SELECT type FROM geometry_columns
        WHERE f_table_name = 'dcp_precinct_boundaries'
          AND f_geometry_column = 'boundary'
    """)
    row = cur.fetchone()
    col_type = row[0] if row else "UNKNOWN"
    if col_type != "MULTIPOLYGON":
        print(f"[FAIL] boundary column type is {col_type}, expected MULTIPOLYGON")
        failures += 1
    else:
        print(f"[OK]  boundary column type: {col_type}")

    # ── 2. Coverage summary ───────────────────────────────────────────────────
    cur.execute("SELECT lga, COUNT(*) FROM dcp_precinct_boundaries GROUP BY lga ORDER BY lga")
    rows = cur.fetchall()
    print(f"\nCoverage ({sum(r[1] for r in rows)} total rows):")
    for lga, count in rows:
        print(f"  {repr(lga)}: {count}")

    # ── 3. LGA name inconsistencies ───────────────────────────────────────────
    cur.execute("SELECT DISTINCT lga FROM dcp_precinct_boundaries ORDER BY lga")
    lgas = [r[0] for r in cur.fetchall()]
    lga_normalised = [l.strip().upper() for l in lgas]
    seen: dict[str, list[str]] = {}
    for orig, norm in zip(lgas, lga_normalised):
        seen.setdefault(norm, []).append(orig)
    inconsistent = {k: v for k, v in seen.items() if len(v) > 1}
    if inconsistent:
        for norm, variants in inconsistent.items():
            print(f"[WARN] LGA name inconsistency for '{norm}': {variants}")
            warnings += 1
    else:
        print("[OK]  LGA names consistent")

    # ── 4. Invalid geometries ─────────────────────────────────────────────────
    where = "WHERE NOT ST_IsValid(boundary)"
    params = []
    if lga_filter:
        where += " AND LOWER(TRIM(lga)) = LOWER(%s)"
        params.append(lga_filter)
    cur.execute(f"SELECT precinct_id, precinct_name, lga, ST_IsValidReason(boundary) FROM dcp_precinct_boundaries {where}", params)
    invalid = cur.fetchall()
    if invalid:
        print(f"\n[WARN] {len(invalid)} invalid geometry(s):")
        for r in invalid:
            print(f"  {r[0]} | {r[1]} | {r[2]} | {r[3]}")
        warnings += len(invalid)
    else:
        print("[OK]  All geometries valid")

    # ── 5. Geometry type consistency ─────────────────────────────────────────
    cur.execute("SELECT ST_GeometryType(boundary), COUNT(*) FROM dcp_precinct_boundaries GROUP BY 1")
    type_rows = cur.fetchall()
    non_multi = [(t, c) for t, c in type_rows if t != "ST_MultiPolygon"]
    if non_multi:
        for t, c in non_multi:
            print(f"[FAIL] {c} row(s) with type {t} — expected ST_MultiPolygon")
            failures += 1
    else:
        print("[OK]  All rows are ST_MultiPolygon")

    # ── 6. Centroid self-test ─────────────────────────────────────────────────
    where2 = "WHERE NOT ST_Contains(boundary, ST_Centroid(boundary))"
    params2 = []
    if lga_filter:
        where2 += " AND LOWER(TRIM(lga)) = LOWER(%s)"
        params2.append(lga_filter)
    cur.execute(f"SELECT precinct_id, precinct_name, lga FROM dcp_precinct_boundaries {where2}", params2)
    centroid_fails = [(r[0], r[1], r[2]) for r in cur.fetchall() if r[0] not in CENTROID_EXCEPTIONS]
    known_exceptions = [(r[0], r[1], r[2]) for r in cur.fetchall() if r[0] in CENTROID_EXCEPTIONS] if not params2 else []
    if centroid_fails:
        print(f"\n[WARN] {len(centroid_fails)} precinct(s) where centroid falls outside boundary:")
        for pid, name, lga in centroid_fails:
            print(f"  {pid} | {name} | {lga}")
        warnings += len(centroid_fails)
    else:
        print(f"[OK]  Centroid-in-boundary self-test passed")

    if verbose and CENTROID_EXCEPTIONS:
        print(f"       Known exceptions (not flagged): {sorted(CENTROID_EXCEPTIONS)}")

    # ── 7. Known address spot checks ─────────────────────────────────────────
    print(f"\nKnown address spot checks ({len(KNOWN_POINTS)} total):")
    spot_failures = 0
    for lon, lat, expected_id, label in KNOWN_POINTS:
        cur.execute("""
            SELECT precinct_id, precinct_name
            FROM dcp_precinct_boundaries
            WHERE ST_Contains(boundary, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
        """, (lon, lat))
        results = cur.fetchall()
        hit_ids = [r[0] for r in results]
        if expected_id in hit_ids:
            if verbose:
                print(f"  [OK]  {label}: {hit_ids}")
        else:
            print(f"  [FAIL] {label}: expected {expected_id}, got {hit_ids}")
            spot_failures += 1
            failures += 1
    if spot_failures == 0:
        print(f"  All {len(KNOWN_POINTS)} spot checks passed")

    return failures, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify precinct boundary table health")
    parser.add_argument("--lga", help="Filter checks to a specific LGA")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("=" * 60)
    print("Precinct Boundary Verification")
    if args.lga:
        print(f"Filtered to LGA: {args.lga}")
    print("=" * 60)

    failures, warnings = run_checks(cur, args.lga, args.verbose)

    print(f"\n{'=' * 60}")
    print(f"Result: {failures} failure(s), {warnings} warning(s)")
    if failures:
        print("FAIL — address issues before importing or using in production")
    elif warnings:
        print("PASS with warnings — review warnings above")
    else:
        print("PASS")

    cur.close()
    conn.close()
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
