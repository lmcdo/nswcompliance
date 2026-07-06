#!/usr/bin/env python3
"""Capture golden fixtures from the REAL services for the brief's S2/S3 harness.

prior-art-checked: new capture tool; complements brief_contract_drift.py (which
CHECKS captured output against contracts) — this produces the captured output.
No existing script runs the brief's upstream services and persists their raw
emissions as fixtures.

Runs each service the brief consumes (live network + production DB, read-only)
against the verified demo addresses and writes the raw output — exactly what
the brief's boundary sees — to tests/fixtures/brief_golden/<service>.json.
The fixture tests then feed these REAL shapes into the S2 contracts and the
``_build_*`` layers, replacing self-confirming mocks (a mock that returns the
keys the brief expects can never catch a service rename; a captured real
output can).

Coverage note (honest limit): flood_truth / terrain / bushfire need native
raster deps (rasterio/whitebox) not present on the dev box — their contracts
were locked from the 2026-06-22 live capture (#597/#598) and stay covered by
the live drift check. This script captures the six Slice-0 services:
vg comparables, vg sales, strata (cadastre + StrataHub), housing SEPP
eligibility, LEP land-use rows, climate risk.

Usage:  python scripts/capture_brief_golden_fixtures.py [--only service,...]
Read-only: SELECTs and GET queries only; never writes to the database.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "services"))  # bushfire_prescreen imports bare `audit_trail`

from dotenv import find_dotenv, load_dotenv

load_dotenv(REPO / ".env")
if not os.getenv("DATABASE_URL"):
    # A git worktree doesn't carry the untracked .env — fall back to the main
    # checkout's (find_dotenv walks up from the current working directory).
    load_dotenv(find_dotenv(usecwd=True))

OUT_DIR = REPO / "tests" / "fixtures" / "brief_golden"

# Verified demo addresses (memory/project-verified-demo-addresses; plan §Demo).
CONCORD = {"address": "14 Stanley Street, Concord", "prop_id": 1456609,
           "lat": -33.86382, "lng": 151.10586, "zone": "R3"}
HURSTVILLE = {"address": "5/1 Treacy Street, Hurstville", "prop_id": 4241915}
# Regional worst-case profile: R3 in a non-DCP-onboarded council, big irregular
# lot (polygon fills 59.4% of its OBB → frontage unmeasurable → width-gated
# forms UNCONFIRMED), no LEP height/FSR. The metro fixtures never exercised
# these fallbacks together — that's how the 2026-07-05 Bowral brief shipped a
# contradictory SEPP card unnoticed.
BOWRAL = {"address": "38 Park Road, Bowral", "prop_id": 1119594, "zone": "R3"}


def _write(name: str, inputs: dict, output) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.json"
    envelope = {
        "service": name,
        "captured_at": date.today().isoformat(),
        "inputs": inputs,
        "output": output,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(envelope, fh, indent=2, default=str)
        fh.write("\n")
    size_kb = path.stat().st_size / 1024
    print(f"  wrote {path.relative_to(REPO)} ({size_kb:.1f} KB)")


def capture_vg_comparables() -> None:
    from services.vg_comparables import get_comparable_values

    # Lot area for the subject comes from the live valuation the brief uses.
    from generate_conveyancing_report import get_valuation

    val = get_valuation(CONCORD["prop_id"])
    lot_area = val.get("lot_area_m2") or 550.0
    result = get_comparable_values(
        CONCORD["lng"], CONCORD["lat"], CONCORD["zone"], lot_area_m2=lot_area,
        subject_propid=CONCORD["prop_id"],
    )
    _write("vg_comparables", {**CONCORD, "lot_area_m2": lot_area}, result.model_dump())


def capture_vg_sales() -> None:
    from services.vg_comparables import get_recent_sales

    sales = get_recent_sales(CONCORD["lng"], CONCORD["lat"])
    _write("vg_sales", CONCORD, [s.model_dump() for s in sales])


def capture_strata() -> None:
    from generate_conveyancing_report import detect_strata

    # Coordinates from the verified prop_id's cadastral polygon centroid (the
    # text resolver fail-closes on unit-style addresses — GATE-0 — but the real
    # brief flow supplies pin coordinates, which this reproduces).
    from services.lot_dimensions import fetch_lot_geometry
    from services.vg_comparables import _webmercator_to_wgs84

    geom = fetch_lot_geometry(str(HURSTVILLE["prop_id"]))
    ring = geom["rings"][0]
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    lat, lng = _webmercator_to_wgs84(cx, cy)
    raw = detect_strata(HURSTVILLE["address"], lat, lng)

    # StrataHub enrichment — the same call _fetch_strata makes.
    from services.strata_lookup import query_strata_at_point

    sh = query_strata_at_point(lng, lat)
    _write("strata_cadastre", {**HURSTVILLE, "lat": lat, "lng": lng}, raw)
    _write("strata_hub", {"lat": lat, "lng": lng},
           sh.model_dump() if sh is not None else None)


def capture_housing_sepp() -> None:
    from services.housing_sepp_eligibility import evaluate_eligibility
    from dataclasses import asdict

    from generate_conveyancing_report import get_valuation

    val = get_valuation(CONCORD["prop_id"])
    lot_area = val.get("lot_area_m2")
    results = evaluate_eligibility(
        CONCORD["zone"], lot_area, None, CONCORD["lat"], CONCORD["lng"],
    )
    _write("housing_sepp_eligibility",
           {**CONCORD, "lot_area_m2": lot_area},
           [asdict(r) for r in results])


def capture_housing_sepp_bowral() -> None:
    """Eligibility with a REAL unmeasurable lot width — the brief's exact
    Bowral inputs (width from the live cadastral polygon, None when irregular),
    so the data-gap-vs-failed-standard distinction is locked by a real shape."""
    from dataclasses import asdict

    from generate_conveyancing_report import get_valuation
    from services.housing_sepp_eligibility import evaluate_eligibility
    from services.lot_dimensions import calculate_lot_dimensions, fetch_lot_geometry
    from services.vg_comparables import _webmercator_to_wgs84

    geom = fetch_lot_geometry(str(BOWRAL["prop_id"]))
    dims = calculate_lot_dimensions(geom)
    ring = geom["rings"][0]
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    lat, lng = _webmercator_to_wgs84(cx, cy)
    val = get_valuation(BOWRAL["prop_id"])
    lot_area = val.get("lot_area_m2")
    width = dims.frontage_m if dims else None
    results = evaluate_eligibility(BOWRAL["zone"], lot_area, width, lat, lng)
    _write("housing_sepp_eligibility_bowral",
           {**BOWRAL, "lat": lat, "lng": lng, "lot_area_m2": lot_area,
            "lot_width_m": width,
            "lot_irregular": dims.irregular if dims else None},
           [asdict(r) for r in results])


def capture_lep_land_use() -> None:
    import psycopg2

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        # prior-art-checked: development_permissions_db.py queries the OLDER
        # regulatory_provisions table; the brief's _permitted_engine_forms
        # consumes lep_land_use_table — this capture mirrors THAT seam exactly.
        # DISTINCT permissibility first so the fixture covers the value
        # vocabulary (real data: permitted/prohibited/exempt/…), then a row spread.
        cur.execute(
            "SELECT DISTINCT permissibility FROM lep_land_use_table WHERE zone = %s",
            (CONCORD["zone"],),
        )
        vocab = sorted(r[0] for r in cur.fetchall())
        cur.execute(
            "SELECT lga, zone, development_type, permissibility "
            "FROM lep_land_use_table WHERE zone = %s "
            "ORDER BY permissibility, lga, development_type LIMIT 60",
            (CONCORD["zone"],),
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        conn.close()
    _write("lep_land_use_rows", {"zone": CONCORD["zone"], "limit": 60},
           {"permissibility_vocab": vocab, "rows": rows})


def capture_climate() -> None:
    """Capture through the brief's ACTUAL fetch seam (_fetch_climate_risk),
    which attaches the NARCLIM projection summary - not the bare to_dict."""
    import services.intelligence_brief as ib

    _write("climate_risk", CONCORD, ib._fetch_climate_risk(CONCORD["lat"], CONCORD["lng"]))


def capture_env_overlays() -> None:
    """get_unique_overlays real run — overlays hit + coverage + measured
    nearest-feature distances (proximity_m), the Slice-2 distance source."""
    from generate_conveyancing_report import get_unique_overlays

    overlays, covered, proximity = get_unique_overlays(CONCORD["lat"], CONCORD["lng"])
    _write("env_overlays", CONCORD, {
        "overlays": overlays,
        "covered_layers": sorted(covered),
        "proximity_m": proximity,
    })


def capture_da_outcomes() -> None:
    """Real DA tracking outcomes near Concord + LGA determination counts —
    through the brief's fetch seam (post-fix; was a silent zero)."""
    import services.intelligence_brief as ib

    _write("da_outcomes", CONCORD, ib._fetch_da_outcomes(CONCORD["lng"], CONCORD["lat"]))
    _write("da_refusal_stats", {"lga": "CANADA BAY"}, ib._fetch_refusal_stats("CANADA BAY"))


CAPTURES = {
    "vg_comparables": capture_vg_comparables,
    "vg_sales": capture_vg_sales,
    "strata": capture_strata,
    "housing_sepp": capture_housing_sepp,
    "housing_sepp_bowral": capture_housing_sepp_bowral,
    "lep_land_use": capture_lep_land_use,
    "climate": capture_climate,
    "env_overlays": capture_env_overlays,
    "da_outcomes": capture_da_outcomes,
}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="comma-separated subset of: " + ",".join(CAPTURES))
    args = parser.parse_args(argv[1:])
    names = args.only.split(",") if args.only else list(CAPTURES)

    failures = []
    for name in names:
        print(f"capturing {name} ...")
        try:
            CAPTURES[name]()
        except Exception as e:  # a capture failure must be VISIBLE, never an empty fixture
            failures.append((name, f"{type(e).__name__}: {e}"))
            print(f"  FAILED: {type(e).__name__}: {e}")
    if failures:
        print(f"\n{len(failures)}/{len(names)} captures failed — fixtures NOT written for those.")
        return 1
    print(f"\nAll {len(names)} captures written to {OUT_DIR.relative_to(REPO)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
