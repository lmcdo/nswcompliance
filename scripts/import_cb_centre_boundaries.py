#!/usr/bin/env python3
"""Load the three Canterbury-Bankstown centre outlines into dcp_precinct_boundaries.

prior-art-checked: modelled on import_parramatta_part8_boundaries.py (upsert on the
(precinct_id, lga) unique key, former_council set, proof-after-write). The geometry is built
and documented by scripts/build_cb_centre_boundaries.py; this only loads the committed file.

KEYS (each one load-bearing, measured 2026-10-11)
  lga             'Canterbury-Bankstown' -- precinct-service matches LOWER(lga) against the
                  Planning Portal's 'CANTERBURY-BANKSTOWN'.
  former_council  'Canterbury-Bankstown' -- NOT NULL on purpose: a NULL falls back to
                  PRECINCT_ID_PATTERNS, whose default is 'Marrickville', and '6.2' would also
                  match the City of Sydney pattern. councilKey() turns this into
                  'canterbury_bankstown', the rules' source_council.
  precinct_id     the DCP chapter number ('6.2', '7.5', '7.6'), the same value
                  derive_precinct_keys.py writes onto the chapters' rules.

Usage:
    python scripts/import_cb_centre_boundaries.py            # dry-run: prints what it would write
    python scripts/import_cb_centre_boundaries.py --commit   # backup, upsert, prove
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "data" / "canterbury_bankstown_precincts" / "centres.geojson"
BACKUP_DIR = REPO / "data" / "db_rollback_backups"

LGA = "Canterbury-Bankstown"
FORMER_COUNCIL = "Canterbury-Bankstown"
EXPECTED_IDS = {"6.2", "7.5", "7.6"}
#: Other files (--src) carry their own ids: the 7.2 raster centres are 7.2.2-7.2.13 + the union '7.2'
#: (scripts/fit_cb_raster_centres.py). Their ids are checked against the file's own config, not this set.
RASTER_IDS = {"centres_7_2.geojson": {"7.2", *(f"7.2.{n}" for n in range(2, 14))}}
#: Site files: any subset of these ids (refused sites are simply absent; there is no union).
SITE_IDS = {"site_plans_8_3.geojson": {"8.3.5", "8.3.7", "8.3.8"}, "site_plans_11_4.geojson": {"11.4"},
            "lep_area1_7_4.geojson": {"7.4"},  # 7.4: the LEP's own Area 1 polygons (69 centres, one union)
            "lep_riverwood_11_14.geojson": {"11.14"}}  # 11.14: the LEP's FSR 2.2 polygon of the 2024 Riverwood amendment
#: Former-council halves (ABS ASGS 2015, scripts/build in the file's own 'source'). They tile the whole LGA, so the
#: audit addresses must each land in EXACTLY ONE of them instead of in no precinct.
FORMER_IDS = {"former_councils_abs2015.geojson": {"C-B former Bankstown", "C-B former Canterbury"}}
#: The Planning Portal's state outline is the council's legal map layer (1.0). A figure fitted to
#: the cadastre is positionally ~4 m, and doubtful lots were kept, so it is recorded lower.
CONFIDENCE = {"cadastre_lot_plan": 0.95, "nsw_planning_local_provisions": 1.0, "nsw_planning_epi_layer": 1.0, "dcp_figure_georeferenced_to_cadastre": 0.9,
              "dcp_raster_map_fitted_to_road_centrelines": 0.85, "dcp_site_plan_shape_fitted_to_cadastre": 0.85,
              "abs_asgs_2015_former_lga": 0.95}
CB_ENVELOPE = (150.95, -33.99, 151.18, -33.85)

#: Lot points (ST_PointOnSurface of nsw_cadastre_lots, 2026-10-11) of the served-answer audit's
#: three Canterbury-Bankstown addresses. None is in a centre; each must stay in no precinct.
OUTSIDE_ALL = {
    "44 Hood Ave Earlwood (11//DP13148)": (151.116551, -33.929486),
    "44 Lawford St Greenacre (3//DP35333)": (151.061015, -33.889200),
    "5-9 Clack Rd Chester Hill (671//DP1158597)": (150.990406, -33.870217),
}

#: Another council's fitted outlines load through the same proof with that council's own facts (--council).
#: Warringah G9 (2026-10-20): the box around Northern Beaches, addresses that must stay outside (the hospital the
#: figure's line skirts, a house on the far side of Karingal Crescent, Cromer), and points that must fall inside
#: (the central block and two addresses inside the figure's line).
PROFILES = {
    "northern_beaches": {
        "lga": "Northern Beaches", "former_council": "Northern Beaches",
        "envelope": (151.15, -33.82, 151.35, -33.57),
        # Each outline file names its ids and its own anchors. Lot points are ST_PointOnSurface of nsw_cadastre_lots;
        # addresses are NSW address register points.
        "files": {
            "centres_g9.geojson": {
                "ids": {"G9 Frenchs Forest Town Centre"},
                "outside": {
                    "Northern Beaches Hospital (1//DP1247544)": (151.232883, -33.751053),
                    "74 Karingal Cres Frenchs Forest (south side)": (151.230758, -33.753158),
                    "10 Campbell Ave Cromer": (151.287220, -33.744429),
                },
                "inside": {
                    "central block (99//DP1241021)": (151.229781, -33.750295),
                    "1 Gladys Ave Frenchs Forest": (151.232218, -33.748933),
                    "5 Hilmer St Frenchs Forest": (151.232180, -33.752803),
                },
            },
            # G7 Evergreen = DP270829 lots 1-35 (the estate's Lot 101 subdivided), loaded on the user's decision
            # (2026-10-20) without a figure match: Figure 1 has no streets to fit.
            "centres_g7.geojson": {
                "ids": {"G7 Evergreen"},
                "outside": {
                    "10 Campbell Ave Cromer": (151.287220, -33.744429),
                    "Northern Beaches Hospital (1//DP1247544)": (151.232883, -33.751053),
                },
                "inside": {"20 Evergreen Drive Cromer": (151.286697, -33.742673)},
            },
        },
    },
}

LOOKUP_SQL = """SELECT precinct_id FROM dcp_precinct_boundaries
                 WHERE ST_Contains(boundary, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                   AND LOWER(lga) = LOWER(%s)"""


def load_rows(src: Path = SRC, profile: dict | None = None) -> list[dict]:
    fc = json.loads(src.read_text(encoding="utf-8"))
    rows = []
    for f in fc["features"]:
        p = f["properties"]
        rows.append({
            "precinct_id": p["precinct_id"], "precinct_name": p["precinct_name"],
            "geom": json.dumps(f["geometry"]), "area_sqm": p["area_sqm"], "perimeter_m": p["perimeter_m"],
            "extraction_method": p["method"], "confidence_score": CONFIDENCE[p["method"]],
            "source_document": p["source"], "boundary_description": p["quote"],
        })
    ids = {r["precinct_id"] for r in rows}
    if profile is not None:  # another council: the file must hold exactly the ids its profile names
        expected = (profile["files"].get(src.name) or {}).get("ids")
        if expected is None or ids != expected:
            raise SystemExit(f"[ABORT] {src.name} holds {sorted(ids)}, expected {sorted(expected or [])}")
        return rows
    expected = RASTER_IDS.get(src.name, EXPECTED_IDS)
    # A raster file may lack centres the fit REFUSED (their rules stay unkeyed); it may never hold an unknown id,
    # and it must hold the chapter's union.
    if src.name in FORMER_IDS:
        expected = FORMER_IDS[src.name]
        ok = ids == expected
    elif src.name in SITE_IDS:
        expected = SITE_IDS[src.name]
        ok = bool(ids) and ids <= expected
    else:
        ok = ids <= expected and min(expected, key=len) in ids if src.name in RASTER_IDS else ids == expected
    if not ok:
        raise SystemExit(f"[ABORT] {src.name} holds {sorted(ids)}, expected {sorted(expected)}")
    return rows


def connect():
    import psycopg2
    from dotenv import dotenv_values
    import os
    url = os.environ.get("DATABASE_URL")
    for d in [REPO, *REPO.parents]:
        if url:
            break
        if (d / ".env").exists():
            url = dotenv_values(d / ".env").get("DATABASE_URL")
    if not url:
        raise SystemExit("[ABORT] DATABASE_URL not found")
    return psycopg2.connect(url, connect_timeout=15, options="-c statement_timeout=30000")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--src", default=str(SRC), help="another outline file in the same shape")
    ap.add_argument("--council", choices=sorted(PROFILES), help="load another council's outlines with its own proof")
    a = ap.parse_args()
    profile = PROFILES[a.council] if a.council else None
    rows = load_rows(Path(a.src), profile)
    for r in rows:
        print(f"  {r['precinct_id']:<4} {r['precinct_name']:<30} {r['area_sqm'] / 1e4:7.1f} ha  "
              f"{r['extraction_method']} ({r['confidence_score']})")
    conn = connect()
    try:
        return _load(conn, rows, a.commit, former=Path(a.src).name in FORMER_IDS, profile=profile,
                     src_name=Path(a.src).name)
    finally:
        conn.close()


def _load(conn, rows: list[dict], commit: bool, former: bool = False, profile: dict | None = None,
          src_name: str = "") -> int:
    lga = profile["lga"] if profile else LGA
    fc = profile["former_council"] if profile else FORMER_COUNCIL
    envelope = profile["envelope"] if profile else CB_ENVELOPE
    per_file = (profile["files"].get(src_name) or {}) if profile else {}
    outside = (per_file.get("outside") or {}) if profile else OUTSIDE_ALL
    # prior-art-checked: closing this script's own connection; no new data source is added.
    cur = conn.cursor()
    cur.execute("SELECT current_database()")
    print(f"database: {cur.fetchone()[0]}")
    cur.execute("""SELECT id, precinct_id, precinct_name, lga, former_council, extraction_method,
                          confidence_score, source_document, boundary_description,
                          ST_AsGeoJSON(boundary) FROM dcp_precinct_boundaries WHERE LOWER(lga) = LOWER(%s)""",
                (lga,))
    existing = cur.fetchall()
    print(f"existing {lga} rows: {len(existing)}")
    if not commit:
        print("dry-run: nothing written (pass --commit)")
        return 0

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    bpath = BACKUP_DIR / f"{'cb' if not profile else lga.lower().replace(' ', '_')}_precinct_boundaries_before_{datetime.now(timezone.utc):%Y-%m-%dT%H%M%S}.json"
    bpath.write_text(json.dumps([list(map(str, r)) for r in existing], indent=1), encoding="utf-8")
    print(f"backup: {bpath} ({len(existing)} rows)")

    for r in rows:
        cur.execute("""
            INSERT INTO dcp_precinct_boundaries
                (precinct_id, precinct_name, lga, former_council, boundary, centroid,
                 source_document, extraction_method, confidence_score, boundary_description,
                 area_sqm, perimeter_m, created_at, updated_at)
            VALUES (%(precinct_id)s, %(precinct_name)s, %(lga)s, %(fc)s,
                    ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326)),
                    ST_PointOnSurface(ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326)),
                    %(source_document)s, %(extraction_method)s, %(confidence_score)s,
                    %(boundary_description)s, %(area_sqm)s, %(perimeter_m)s, now(), now())
            ON CONFLICT (precinct_id, lga) DO UPDATE SET
                precinct_name = EXCLUDED.precinct_name, former_council = EXCLUDED.former_council,
                boundary = EXCLUDED.boundary, centroid = EXCLUDED.centroid,
                source_document = EXCLUDED.source_document,
                extraction_method = EXCLUDED.extraction_method,
                confidence_score = EXCLUDED.confidence_score,
                boundary_description = EXCLUDED.boundary_description,
                area_sqm = EXCLUDED.area_sqm, perimeter_m = EXCLUDED.perimeter_m, updated_at = now()
        """, {**r, "lga": lga, "fc": fc})

    # Proof, inside the transaction: placed on Earth correctly, found by the SAME lookup the
    # site runs, and the audit addresses still in no precinct. The test point is ST_PointOnSurface,
    # not the stored centroid: trigger update_precinct_geometry_stats sets centroid = ST_Centroid,
    # which for a multi-part outline (the 7.2 centres) can lie between the parts.
    problems = []
    cur.execute("""SELECT precinct_id, ST_XMin(boundary), ST_YMin(boundary), ST_XMax(boundary),
                          ST_YMax(boundary), ST_X(ST_PointOnSurface(boundary)), ST_Y(ST_PointOnSurface(boundary))
                     FROM dcp_precinct_boundaries WHERE lga = %s AND precinct_id = ANY(%s)""",
                (lga, [r["precinct_id"] for r in rows]))
    got = cur.fetchall()
    if {g[0] for g in got} != {r["precinct_id"] for r in rows}:
        problems.append(f"rows after write: {sorted(g[0] for g in got)}")
    x0, y0, x1, y1 = envelope
    for pid, a0, b0, a1, b1, cx, cy in got:
        if not (x0 <= a0 and a1 <= x1 and y0 <= b0 and b1 <= y1):
            problems.append(f"{pid} outside the {lga} envelope")
        cur.execute(LOOKUP_SQL, (cx, cy, lga))
        if pid not in {r[0] for r in cur.fetchall()}:
            problems.append(f"{pid}: a point inside it is not found by the site's lookup")
    for label, (x, y) in (per_file.get("inside") or {}).items():
        cur.execute(LOOKUP_SQL, (x, y, lga))
        hit = [r[0] for r in cur.fetchall()]
        print(f"  lookup {label}: {hit or 'no precinct'}")
        if not set(hit) & {r["precinct_id"] for r in rows}:
            problems.append(f"{label} should be inside the new outline, resolves to {hit}")
    for label, (x, y) in outside.items():
        cur.execute(LOOKUP_SQL, (x, y, lga))
        hit = [r[0] for r in cur.fetchall()]
        print(f"  lookup {label}: {hit or 'no precinct'}")
        if former:
            halves = [h for h in hit if h.startswith("C-B former ")]
            if len(halves) != 1 or len(hit) != 1:
                problems.append(f"{label} resolves to {hit}; expected exactly one former council")
        else:
            # The former-council halves tile the whole LGA, so every address is in one; only a CENTRE/site hit is wrong.
            hit = [h for h in hit if not h.startswith("C-B former ")]
            if hit:
                problems.append(f"{label} now resolves to {hit}")
    if problems:
        conn.rollback()
        print("[ROLLED BACK]\n  " + "\n  ".join(problems))
        return 1
    conn.commit()
    print(f"committed {len(rows)} rows; every check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
