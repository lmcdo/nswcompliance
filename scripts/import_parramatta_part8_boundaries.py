#!/usr/bin/env python3
"""City of Parramatta DCP 2023 Part 8 — import council-supplied precinct boundaries.

prior-art-checked: no shapefile->dcp_precinct_boundaries importer exists for
Parramatta. Four sweeps on origin/main d1034243:
  (1) DB — dcp_precinct_boundaries holds 274 rows, of which 13 are
      'City of Parramatta': twelve Part 7.10 heritage areas
      (extraction_method='eplanning_epi_heritage') and one Part 9 city centre
      ('council_agol_lep2023'). No Part 8 geometry of any kind.
  (2) scripts/ — import_krg_local_centre_boundaries.py reads a QGIS GeoPackage
      of HAND-DIGITISED Ku-ring-gai polygons; harvest_council_dcp_boundaries.py
      pulls from public ArcGIS REST. Neither reads a council-supplied shapefile,
      and neither reprojects. This borrows their upsert shape and adds both.
  (3) services/ — arcgis_client is for REST fetches, not files.
  (4) plans/memory — the 2026-07-29 rollout decision puts Woollahra and
      Parramatta at the front of the queue precisely because they hold
      provision text and lack BOUNDARIES. This is that missing half.

PROVENANCE
----------
Shapefile supplied by David Hewetson, GIS Analyst, City of Parramatta, by email
2026-08-18, answering a data request of 2026-07-29. His words: "this data may be
subject to future amendments and is correct as at today." No licence or
attribution condition was stated. That currency statement is recorded on every
row rather than remembered, because a boundary with no as-at date cannot be
audited later.

This is the first boundary set in the table that came from a council's own GIS
rather than being traced or approximated, so extraction_method distinguishes it.

WHAT IT UNLOCKS (measured, not asserted)
----------------------------------------
All 38 distinct Part 8 `v2_precinct_id` values on current Parramatta provisions
match a polygon here — 35 exactly, 3 by prefix where the provision is keyed one
level coarser than the map (e.g. provisions at 8.1.1, polygons at 8.1.1.1..8).
That takes 290 provision rows from "no geometry at all" to locatable.

17 of the 74 refs have no provision yet — the sixteen 8.5.13.* specific sites
and 8.3.10. That is a gap in the TEXT extraction, not in this data.

THREE TRAPS IN THE SOURCE DATA, ALL MEASURED
--------------------------------------------
1. CRS. The shapefile is EPSG:28356 (GDA94 / MGA Zone 56), in METRES. The
   boundary column is EPSG:4326. Loading the eastings straight in would put
   Parramatta off the coast of Africa. Reprojection is mandatory.

   The upside: 28356 is the correct projected CRS for Sydney, so area and
   perimeter are computed from the ORIGINAL geometry BEFORE reprojection and are
   exact rather than estimated. Computing area from 4326 degrees is what made
   lot areas ~45% too large once already.

2. PART_REF is NOT unique. 76 features carry 74 distinct refs: "Part 8.3.2" is
   shared by three separately mapped Harris Park Special Areas (Area of National
   Significance / Football Estate / Harris Park River Area). The parenthetical is
   part of the citation identity, not decoration, so those three get suffixed ids
   that still prefix-match "8.3.2".

3. Two of the 76 geometries are invalid (self-intersection). They are repaired
   with make_valid and the repair is CHECKED: a fix that silently moves a
   boundary is worse than a load failure, so any area change beyond a small
   tolerance aborts the run.

IDS
---
precinct_id follows the convention already in the table AND on the provisions:
the bare DCP part number with no "Part " prefix ("7.10.1", "9", "8.2.6"), so
Part 8 rows become "8.1.1.1", "8.2.1" and so on. Nothing in 8.* collides with
the existing 7.10.* and 9.

Usage:
    ./venv_linux/Scripts/python.exe scripts/import_parramatta_part8_boundaries.py            # dry-run
    ./venv_linux/Scripts/python.exe scripts/import_parramatta_part8_boundaries.py --commit   # writes
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

LGA = "City of Parramatta"          # DB vocabulary; the shapefile says "PARRAMATTA"
SOURCE_EPSG = 28356                 # GDA94 / MGA Zone 56 — the shapefile's own CRS
TARGET_EPSG = 4326                  # what dcp_precinct_boundaries stores
EXTRACTION_METHOD = "council_supplied_shapefile"

#: NOT cosmetic, and NOT NULL. frontend-nextjs/lib/precinct-service.ts resolves a
#: boundary's council from this column first, and falls back to
#: PRECINCT_ID_PATTERNS only when it is NULL — a fallback whose final default is
#: 'Marrickville'. Parramatta's only patterns are /^parra/i and /^p_/i, so a
#: dotted id like "8.1.1.1" matches nothing and every one of these 76 precincts
#: would be attributed to Marrickville in the UI. The 13 rows loaded 2026-07-29
#: set 'Parramatta' for exactly this reason; the first version of this script
#: copied NULL from the Ku-ring-gai importer, which gets away with it because
#: KRG ids DO match a pattern (/^14[A-O](_T\d)?$/i).
FORMER_COUNCIL = "Parramatta"

#: Supplied by the council's GIS team rather than traced from a PDF or inferred
#: from an adjacent LEP layer, so the geometry IS the council's own. 1.0 refers
#: to positional fidelity, NOT to whether the plan is still current — that is
#: what the as-at date in source_document is for.
CONFIDENCE = 1.0

SUPPLIED_ON = "2026-08-18"
SUPPLIED_BY = "David Hewetson, GIS Analyst, City of Parramatta"

#: The three areas sharing "Part 8.3.2". Suffixes keep a LIKE '8.3.2%' lookup
#: working while making each row individually addressable.
SHARED_REF_SUFFIX = {
    "Area of National Significance": "national-significance",
    "Football Estate": "football-estate",
    "Harris Park River Area": "river-area",
}

#: A repaired polygon whose area moves by more than this has been reshaped, not
#: repaired, and must be looked at by a human instead of loaded.
MAX_REPAIR_AREA_DRIFT = 0.001   # 0.1%

#: Parramatta LGA sits comfortably inside this envelope. Used after the write to
#: prove the geometry landed in the right place on Earth, not merely that rows
#: exist — the failure mode of a botched reprojection is a full table of
#: plausible-looking rows pointing at the wrong continent.
PARRAMATTA_ENVELOPE = (150.85, -33.90, 151.15, -33.72)


def strip_part_prefix(part_ref: str) -> str:
    """'Part 8.1.1.1' -> '8.1.1.1', matching the ids already in the table."""
    return re.sub(r"^\s*Part\s+", "", part_ref or "", flags=re.I).strip()


def build_precinct_id(part_ref: str, part_name: str, shared_refs: set[str]) -> str:
    """The DCP part number, suffixed only where one ref maps several areas."""
    base = strip_part_prefix(part_ref)
    if part_ref not in shared_refs:
        return base
    for marker, suffix in SHARED_REF_SUFFIX.items():
        if marker.lower() in (part_name or "").lower():
            return f"{base}-{suffix}"
    # Never invent a silent fallback id: an unrecognised sub-area means the
    # source gained a row this script has not been told about.
    raise SystemExit(
        f"[ABORT] {part_ref} is shared by several areas and "
        f"{part_name!r} matches no known sub-area. Add it to SHARED_REF_SUFFIX."
    )


def source_document(part_ref: str, amendment, commenced) -> str:
    """One string carrying the citation, the amendment, and the as-at date."""
    bits = [f"Parramatta DCP 2023 {part_ref}"]
    if amendment:
        bits.append(str(amendment))
    if commenced is not None:
        bits.append(f"commenced {str(commenced)[:10]}")
    bits.append(
        f"<- council GIS shapefile dcp2023_part8, supplied {SUPPLIED_ON} by {SUPPLIED_BY}"
    )
    bits.append(
        "council advises data may be subject to future amendments and was "
        "correct as at the supply date"
    )
    return " | ".join(bits)


def load_features(shp_path: Path) -> list[dict]:
    """Read, validate, measure in metres, then reproject. The order matters."""
    import geopandas as gpd
    from shapely.validation import make_valid

    g = gpd.read_file(shp_path)
    if g.crs is None or g.crs.to_epsg() != SOURCE_EPSG:
        raise SystemExit(
            f"[ABORT] expected EPSG:{SOURCE_EPSG}, got {g.crs}. "
            "Both the area figures and the reprojection depend on this."
        )

    invalid = ~g.geometry.is_valid
    if invalid.any():
        print(f"[repair] {int(invalid.sum())} invalid geometries — repairing and checking")
        for idx in g.index[invalid]:
            before = g.at[idx, "geometry"]
            after = make_valid(before)
            # Compared in the SOURCE crs, where area is in real square metres.
            a0, a1 = before.buffer(0).area, after.area
            drift = abs(a1 - a0) / a0 if a0 else 0.0
            ref = g.at[idx, "PART_REF"]
            if drift > MAX_REPAIR_AREA_DRIFT:
                raise SystemExit(
                    f"[ABORT] repairing {ref} moved its area by {drift:.2%} "
                    f"({a0:.0f} -> {a1:.0f} m2). That is a reshape, not a repair."
                )
            print(f"    {ref}: repaired, area drift {drift:.4%}")
            g.at[idx, "geometry"] = after

    # Measure BEFORE reprojecting: 28356 is metres, 4326 is degrees.
    g["_area_sqm"] = g.geometry.area
    g["_perimeter_m"] = g.geometry.length

    shared = {r for r in g["PART_REF"] if (g["PART_REF"] == r).sum() > 1}
    if shared:
        print(f"[keys] refs mapping several areas: {sorted(shared)}")

    g = g.to_crs(epsg=TARGET_EPSG)

    rows = []
    for _, f in g.iterrows():
        rows.append({
            "precinct_id": build_precinct_id(f["PART_REF"], f["PART_NAME"], shared),
            "precinct_name": f["PART_NAME"],
            "geom": json.dumps(f.geometry.__geo_interface__),
            "source_document": source_document(f["PART_REF"], f["AMENDMENT"], f["COMMENCED"]),
            "area_sqm": float(f["_area_sqm"]),
            "perimeter_m": float(f["_perimeter_m"]),
            "status": f["STATUS"],
        })
    return rows


def find_env() -> Path:
    """Locate the repo-root .env, including when running from a git worktree.

    .env is gitignored, so it exists ONLY in the main working tree. A worktree
    under .claude/worktrees/<name>/ has none, and without this the PG* vars are
    absent, db_config falls back to its localhost defaults, and the failure
    surfaces as "server does not support SSL" — which reads like a TLS problem
    and is really a missing-credentials problem. Fail loudly instead.
    """
    local = REPO / ".env"
    if local.exists():
        return local
    for parent in REPO.parents:
        candidate = parent / ".env"
        if candidate.exists() and (parent / "services" / "db_config.py").exists():
            return candidate
    raise SystemExit(
        "[ABORT] no .env found. Credentials live in the main working tree's "
        "repo-root .env, which is gitignored and absent from worktrees."
    )


def connect():
    from dotenv import load_dotenv
    load_dotenv(find_env())
    for pg, db in (("PGHOST", "DB_HOST"), ("PGUSER", "DB_USER"), ("PGPASSWORD", "DB_PASSWORD"),
                   ("PGDATABASE", "DB_NAME"), ("PGPORT", "DB_PORT")):
        if os.getenv(pg):
            os.environ[db] = os.environ[pg]
    if not os.getenv("DB_HOST"):
        raise SystemExit(
            "[ABORT] DB_HOST unset after loading .env. Refusing to fall back to "
            "localhost, which would silently target the wrong database."
        )
    os.environ.setdefault("PGSSLMODE", "require")
    sys.path.insert(0, str(REPO / "services"))
    from db_config import get_connection
    return get_connection()


UPSERT = """
INSERT INTO dcp_precinct_boundaries (
    precinct_id, precinct_name, lga, former_council,
    boundary, centroid,
    source_document, extraction_method, confidence_score,
    area_sqm, perimeter_m
) VALUES (
    %(precinct_id)s, %(precinct_name)s, %(lga)s, %(former_council)s,
    -- ST_Force2D is load-bearing: the shapefile's polygons carry a Z ordinate
    -- (all zero), and the column is 2D, so without it every insert fails with
    -- "Geometry has Z dimension but column does not". Dropping Z loses nothing
    -- here — these are planning boundaries, not terrain.
    ST_Multi(ST_Force2D(ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326))),
    ST_Centroid(ST_Force2D(ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326))),
    %(source_document)s, %(extraction_method)s, %(confidence_score)s,
    %(area_sqm)s, %(perimeter_m)s
)
ON CONFLICT (precinct_id, lga) DO UPDATE SET
    precinct_name     = EXCLUDED.precinct_name,
    former_council    = EXCLUDED.former_council,
    boundary          = EXCLUDED.boundary,
    centroid          = EXCLUDED.centroid,
    source_document   = EXCLUDED.source_document,
    extraction_method = EXCLUDED.extraction_method,
    confidence_score  = EXCLUDED.confidence_score,
    area_sqm          = EXCLUDED.area_sqm,
    perimeter_m       = EXCLUDED.perimeter_m,
    updated_at        = NOW()
"""


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Import Parramatta DCP 2023 Part 8 precinct boundaries"
    )
    ap.add_argument(
        "--shapefile",
        default=r"C:\Users\lawre\Downloads\dcp2023_part8.shp\dcp2023_part8.shp",
    )
    ap.add_argument("--commit", action="store_true", help="write to the database (default: dry-run)")
    args = ap.parse_args()

    shp = Path(args.shapefile)
    if not shp.exists():
        raise SystemExit(f"[ABORT] shapefile not found: {shp}")

    rows = load_features(shp)
    print(f"\n[read] {len(rows)} features from {shp.name}")

    non_current = [r for r in rows if r["status"] != "CURRENT"]
    if non_current:
        print(f"[warn] {len(non_current)} features are not CURRENT: "
              f"{[r['precinct_id'] for r in non_current]}")

    ids = [r["precinct_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise SystemExit("[ABORT] precinct_id collision within the shapefile itself")

    conn = connect()
    cur = conn.cursor()
    cur.execute("SET statement_timeout='60s'")

    cur.execute(
        "SELECT precinct_id FROM dcp_precinct_boundaries WHERE lga = %s AND precinct_id = ANY(%s)",
        (LGA, ids),
    )
    clash = sorted(r[0] for r in cur.fetchall())
    print(f"[check] {len(clash)} of {len(ids)} ids already exist for {LGA} "
          f"(these would be UPDATED, not duplicated): {clash or 'none'}")

    cur.execute("SELECT count(*) FROM dcp_precinct_boundaries WHERE lga = %s", (LGA,))
    before_lga = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM dcp_precinct_boundaries")
    before_all = cur.fetchone()[0]
    print(f"[before] {LGA}: {before_lga} rows | table total: {before_all}")

    if not args.commit:
        print("\n[dry-run] nothing written. First five rows that would be inserted:\n")
        for r in rows[:5]:
            print(f"  {r['precinct_id']:22s} {r['precinct_name'][:60]}")
            print(f"      area {r['area_sqm']:,.0f} m2   perimeter {r['perimeter_m']:,.0f} m")
        print(f"  ... and {len(rows) - 5} more")
        print(f"\n[dry-run] would take {LGA} from {before_lga} to "
              f"{before_lga + len(ids) - len(clash)} rows. Re-run with --commit.")
        conn.close()
        return

    for r in rows:
        cur.execute(UPSERT, {
            **r,
            "lga": LGA,
            "former_council": FORMER_COUNCIL,
            "extraction_method": EXTRACTION_METHOD,
            "confidence_score": CONFIDENCE,
        })
    conn.commit()

    cur.execute("SELECT count(*) FROM dcp_precinct_boundaries WHERE lga = %s", (LGA,))
    after_lga = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM dcp_precinct_boundaries")
    after_all = cur.fetchone()[0]
    print(f"[after]  {LGA}: {after_lga} rows (+{after_lga - before_lga}) | "
          f"table total: {after_all} (+{after_all - before_all})")

    x0, y0, x1, y1 = PARRAMATTA_ENVELOPE
    cur.execute("""
        SELECT count(*) FROM dcp_precinct_boundaries
        WHERE lga = %s AND extraction_method = %s
          AND NOT ST_Within(centroid, ST_MakeEnvelope(%s, %s, %s, %s, 4326))
    """, (LGA, EXTRACTION_METHOD, x0, y0, x1, y1))
    stray = cur.fetchone()[0]
    if stray:
        print(f"[FAIL] {stray} imported centroids fall outside the Parramatta envelope — "
              "the reprojection is wrong. Roll back.")
        conn.close()
        sys.exit(1)
    print(f"[verify] all {len(ids)} imported centroids fall inside the Parramatta envelope")
    conn.close()


if __name__ == "__main__":
    main()
