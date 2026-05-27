#!/usr/bin/env python3
"""
Intelligence Brief — Pre-Implementation Validation Spike

Validates 3 assumptions before Stage 1 schema design:
  1. Compound constraint rules (heritage+flood, heritage+bushfire, TOD+heritage)
  2. Strata classification heuristic (apartment vs development vs Torrens)
  3. LGA boundary detection accuracy (detect_former_council)

Calls all pipeline functions per address, evaluates rules, outputs JSON report.

Requires: DATABASE_URL env var, network access to Planning Portal + VG APIs.
Shadow included by default (calls Railway service ~17s/address). Skip with --no-shadow.

Usage:
  python scripts/intelligence_brief_spike.py              # full run including shadow
  python scripts/intelligence_brief_spike.py --no-shadow   # skip shadow (faster)
"""

import io
import json
import os
import sys
import time
from datetime import date

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load env — try worktree root first, then main repo root
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_root, ".env"))
# Fallback: if running from worktree, main repo .env may be elsewhere
if not os.getenv("DATABASE_URL"):
    _main_root = os.path.abspath(os.path.join(_root, "..", "..", "..", "..", ".."))
    load_dotenv(os.path.join(_main_root, ".env"), override=True)

import psycopg2

from scripts.generate_conveyancing_report import (
    detect_former_council,
    detect_strata,
    get_raw_controls,
    get_shadow_risk,
    get_unique_overlays,
    get_valuation,
    parse_controls,
    resolve_address,
)
from scripts.conveyancing_db import (
    fetch_dcp_setbacks,
    fetch_heritage_postgis,
    fetch_lep_clauses,
    fetch_nearby_das,
)


# ---------------------------------------------------------------------------
# Test addresses — chosen because ground truth is known
# ---------------------------------------------------------------------------
TEST_ADDRESSES = [
    # 1-3: Heritage HCA + flood (Inner West — known flood + heritage areas)
    {
        "address": "10 Hollands Avenue, Marrickville NSW 2204",
        "type": "heritage_flood",
        "expect": "heritage HCA + flood overlay both present",
    },
    {
        "address": "5 River Street, Marrickville NSW 2204",
        "type": "heritage_flood",
        "expect": "near Cooks River, flood + possible heritage",
    },
    {
        "address": "21 Illawarra Road, Marrickville NSW 2204",
        "type": "heritage_flood",
        "expect": "Marrickville heritage area near flood zone",
    },
    # 4-5: Heritage + bushfire (Blue Mountains / Ku-ring-gai)
    {
        "address": "1 Station Street, Katoomba NSW 2780",
        "type": "heritage_bushfire",
        "expect": "heritage item in bushfire-prone area",
    },
    {
        "address": "15 Fox Valley Road, Wahroonga NSW 2076",
        "type": "heritage_bushfire",
        "expect": "Ku-ring-gai heritage + bushfire prone land",
    },
    # 6: TOD + heritage (near major station + heritage)
    {
        "address": "8 Marion Street, Leichhardt NSW 2040",
        "type": "tod_heritage",
        "expect": "near Leichhardt station, heritage area",
    },
    # 7-8: Boundary suburbs (Inner West merger — Stanmore, Dulwich Hill)
    {
        "address": "100 Stanmore Road, Stanmore NSW 2048",
        "type": "boundary_lga",
        "expect": "Marrickville former council",
    },
    {
        "address": "15 Marrickville Road, Dulwich Hill NSW 2203",
        "type": "boundary_lga",
        "expect": "Marrickville former council",
    },
    # 9: Strata apartment (high-rise)
    {
        "address": "5/1 Treacy Street, Hurstville NSW 2220",
        "type": "strata_apartment",
        "expect": "strata confirmed, is_apartment = True",
    },
    # 10: Strata townhouse (own lot — should NOT be apartment)
    {
        "address": "3/22 Carlton Crescent, Summer Hill NSW 2130",
        "type": "strata_townhouse",
        "expect": "strata but NOT apartment (small lot, low unit count)",
    },
    # 11: Community title
    {
        "address": "2/45 Alt Street, Ashfield NSW 2131",
        "type": "community_title",
        "expect": "may be community title (CP not SP)",
    },
    # 12: R3 lot with dwelling house — zone allows higher density
    {
        "address": "35 Denison Road, Dulwich Hill NSW 2203",
        "type": "zone_advisory",
        "expect": "R3 zone permits medium density but has single dwelling",
    },
    # 13: Marginal lot size (~450m²)
    {
        "address": "22 Pile Street, Marrickville NSW 2204",
        "type": "marginal_lot",
        "expect": "lot area near SEPP 450m² threshold",
    },
    # 14: Known DA area — should have nearby DAs
    {
        "address": "88 Marrickville Road, Marrickville NSW 2204",
        "type": "da_shadow",
        "expect": "recent DAs within 200m",
    },
    # 15: Rural lot (no DCP coverage expected)
    {
        "address": "123 Bells Line of Road, Kurrajong Heights NSW 2758",
        "type": "rural_no_dcp",
        "expect": "no DCP setbacks available",
    },
    # 16-17: Inner West with full DCP — happy path
    {
        "address": "15 Petersham Road, Marrickville NSW 2204",
        "type": "happy_path",
        "expect": "full data available: zone, height, FSR, heritage, DCP",
    },
    {
        "address": "42 Norton Street, Leichhardt NSW 2040",
        "type": "happy_path",
        "expect": "full data available — Leichhardt DCP",
    },
    # 18: Multi-overlay area (Hawkesbury — known flood + bushfire)
    {
        "address": "1 George Street, Windsor NSW 2756",
        "type": "multi_overlay",
        "expect": "flood + possibly bushfire, multiple overlays",
    },
    # 19: Clean lot — nothing should fire
    {
        "address": "50 Pitt Street, Sydney NSW 2000",
        "type": "clean_lot",
        "expect": "CBD — no heritage HCA, no flood, no bushfire",
    },
    # 20: Recently rezoned area
    {
        "address": "10 Parramatta Road, Granville NSW 2142",
        "type": "recently_rezoned",
        "expect": "may show zone change from recent LEP amendment",
    },
]


def evaluate_compound_constraints(controls: dict, overlays: list, heritage_postgis: dict) -> list:
    """Evaluate compound constraint rules against real data."""
    fired = []

    has_heritage_hca = bool(controls.get("heritage_hca"))
    has_heritage_item = bool(controls.get("heritage_items"))
    has_flood_epi = controls.get("flood_epi", False)
    has_tod = controls.get("tod_area", False)

    # Check PostGIS overlays for flood/bushfire
    overlay_types = {o.get("layer_type") for o in overlays}
    has_flood_postgis = "flood" in overlay_types
    has_bushfire = "bushfire" in overlay_types

    # Heritage (HCA or item) + Flood
    if (has_heritage_hca or has_heritage_item) and (has_flood_epi or has_flood_postgis):
        fired.append({
            "rule": "heritage_flood",
            "note": "Heritage item/HCA + flood zone — demolition constraints conflict with flood resilience requirements",
            "heritage_source": "portal_hca" if has_heritage_hca else "portal_item",
            "flood_source": "epi" if has_flood_epi else "postgis",
        })

    # Heritage + Bushfire (10/50 clearing rule)
    if (has_heritage_hca or has_heritage_item) and has_bushfire:
        fired.append({
            "rule": "heritage_bushfire_1050",
            "note": "Heritage item/HCA + bushfire prone land — 10/50 vegetation clearing may conflict with heritage tree protections",
            "heritage_source": "portal",
        })

    # TOD + Heritage
    if has_tod and (has_heritage_hca or has_heritage_item):
        fired.append({
            "rule": "tod_heritage_density",
            "note": "TOD density uplift vs heritage conservation — height/density bonuses may be constrained by heritage controls",
        })

    # Heritage PostGIS items (DB-sourced heritage near property)
    if heritage_postgis.get("has_heritage") and not has_heritage_item:
        fired.append({
            "rule": "heritage_postgis_only",
            "note": "Heritage detected in PostGIS but NOT in portal controls — possible gap in portal data",
        })

    # Flood + bushfire compound
    if (has_flood_epi or has_flood_postgis) and has_bushfire:
        fired.append({
            "rule": "flood_bushfire_compound",
            "note": "Flood + bushfire prone — dual natural hazard, significant insurance and compliance implications",
        })

    return fired


def classify_strata(strata_info: dict, valuation: dict) -> str:
    """
    Classify strata properties using sp_lot_count from the Cadastre API.

    The NSW Cadastre returns individual SP/CP lot features for every lot
    in a strata plan. sp_lot_count is the actual registered lot count
    for the plan — not an approximation.

    Classification:
      >6 lots on the same plan  → apartment (high-density block)
      2-6 lots                  → development (townhouse/villa — GF potential)
      1 lot or no count         → strata_unknown (can't determine from lot count alone)
    """
    if not strata_info.get("is_strata"):
        return "not_strata"

    sp_lot_count = strata_info.get("sp_lot_count")
    if sp_lot_count is None:
        return "strata_unknown"

    if sp_lot_count > 6:
        return "apartment"
    elif sp_lot_count >= 2:
        return "development"  # townhouse/villa — can do GF etc.
    else:
        return "strata_unknown"  # single lot edge case


def run_spike(include_shadow: bool = True):
    """Run all pipeline functions against 20 test addresses."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    if not include_shadow:
        print("Shadow: SKIPPED (--no-shadow)")
    else:
        print("Shadow: ENABLED (Railway service)")

    results = []
    errors = []

    for i, test in enumerate(TEST_ADDRESSES, 1):
        addr = test["address"]
        print(f"\n[{i:2d}/20] {addr}")
        print(f"        Type: {test['type']} — Expect: {test['expect']}")

        entry = {
            "index": i,
            "address": addr,
            "test_type": test["type"],
            "expected": test["expect"],
            "raw_data": {},
            "compound_constraints_fired": [],
            "strata_classification": None,
            "lga_slug": None,
            "issues": [],
            "timing_s": {},
        }

        try:
            # 1. Resolve address
            t0 = time.time()
            prop_id, lat, lng, lot_wkt = resolve_address(addr)
            entry["timing_s"]["resolve"] = round(time.time() - t0, 2)
            entry["raw_data"]["prop_id"] = prop_id
            entry["raw_data"]["lat"] = lat
            entry["raw_data"]["lng"] = lng
            entry["raw_data"]["has_lot_wkt"] = lot_wkt is not None
            print(f"        propId={prop_id}, lat={lat}, lng={lng}")

            if not prop_id:
                entry["issues"].append("FAILED: could not resolve address")
                results.append(entry)
                continue

            # 2. Controls
            t0 = time.time()
            raw_controls = get_raw_controls(prop_id)
            controls = parse_controls(raw_controls)
            entry["timing_s"]["controls"] = round(time.time() - t0, 2)
            entry["raw_data"]["controls"] = {
                "zone": controls.get("zone"),
                "zone_full": controls.get("zone_full"),
                "zone_epi": controls.get("zone_epi"),
                "height": controls.get("height"),
                "fsr": controls.get("fsr"),
                "heritage_items": controls.get("heritage_items", []),
                "heritage_hca": controls.get("heritage_hca", []),
                "tod_area": controls.get("tod_area"),
                "flood_epi": controls.get("flood_epi"),
                "housing_sepp": controls.get("housing_sepp"),
            }
            print(f"        zone={controls.get('zone')} height={controls.get('height')} fsr={controls.get('fsr')}")

            # 3. Valuation
            t0 = time.time()
            valuation = get_valuation(prop_id)
            entry["timing_s"]["valuation"] = round(time.time() - t0, 2)
            entry["raw_data"]["valuation"] = valuation
            print(f"        lot_area={valuation.get('lot_area_m2')}m² land_value=${valuation.get('land_value')}")

            # 4. Strata detection
            t0 = time.time()
            strata = detect_strata(addr, lat, lng)
            entry["timing_s"]["strata"] = round(time.time() - t0, 2)
            entry["raw_data"]["strata"] = strata
            entry["strata_classification"] = classify_strata(strata, valuation)
            print(f"        strata={strata.get('is_strata')} source={strata.get('source')} => {entry['strata_classification']}")

            # 5. LGA / former council detection
            t0 = time.time()
            zone_epi = controls.get("zone_epi") or ""
            lga_slug = detect_former_council(addr, zone_epi)
            entry["timing_s"]["lga"] = round(time.time() - t0, 2)
            entry["lga_slug"] = lga_slug
            print(f"        lga_slug={lga_slug}")

            # 6. PostGIS overlays
            t0 = time.time()
            overlays, overlay_types, proximity_m = get_unique_overlays(lat, lng, lot_wkt)
            entry["timing_s"]["overlays"] = round(time.time() - t0, 2)
            entry["raw_data"]["overlay_types"] = sorted(overlay_types)
            entry["raw_data"]["overlay_count"] = len(overlays)
            entry["raw_data"]["proximity_m"] = {k: round(v, 1) for k, v in proximity_m.items()} if proximity_m else {}
            print(f"        overlays={sorted(overlay_types)} ({len(overlays)} features)")

            # 7. DB queries (heritage, LEP, DCP, DAs)
            conn = None
            heritage_postgis = {"hca": [], "items": [], "has_heritage": False, "raw": []}
            lep_clauses = []
            dcp_setbacks = None
            nearby_das = []

            try:
                conn = psycopg2.connect(db_url)

                t0 = time.time()
                heritage_postgis = fetch_heritage_postgis(conn, lat, lng, lot_wkt)
                entry["timing_s"]["heritage_db"] = round(time.time() - t0, 2)
                entry["raw_data"]["heritage_postgis"] = {
                    "has_heritage": heritage_postgis.get("has_heritage"),
                    "hca_count": len(heritage_postgis.get("hca") or []),
                    "item_count": len(heritage_postgis.get("items") or []),
                }

                t0 = time.time()
                key_sites = controls.get("key_sites_clause")
                epi_name = controls.get("zone_epi")
                lep_clauses = fetch_lep_clauses(conn, key_sites, epi_name)
                entry["timing_s"]["lep_db"] = round(time.time() - t0, 2)
                entry["raw_data"]["lep_clause_count"] = len(lep_clauses)

                t0 = time.time()
                zone_code = controls.get("zone")
                dcp_setbacks = fetch_dcp_setbacks(conn, lga_slug, zone_code)
                entry["timing_s"]["dcp_db"] = round(time.time() - t0, 2)
                entry["raw_data"]["has_dcp_setbacks"] = dcp_setbacks is not None
                if dcp_setbacks:
                    entry["raw_data"]["dcp_setback_keys"] = sorted(dcp_setbacks.keys()) if isinstance(dcp_setbacks, dict) else "non-dict"

                t0 = time.time()
                council_name = None
                if "inner west" in (zone_epi or "").lower():
                    council_name = "Inner West Council"
                nearby_das = fetch_nearby_das(conn, lat, lng, council_name)
                entry["timing_s"]["das_db"] = round(time.time() - t0, 2)
                entry["raw_data"]["nearby_da_count"] = len(nearby_das)
                if nearby_das:
                    entry["raw_data"]["nearest_da"] = {
                        "number": nearby_das[0].get("number"),
                        "distance_m": nearby_das[0].get("distance_m"),
                        "status": nearby_das[0].get("status"),
                    }
                print(f"        DAs={len(nearby_das)} heritage_db={heritage_postgis.get('has_heritage')} dcp={'yes' if dcp_setbacks else 'no'}")

            except Exception as e:
                entry["issues"].append(f"DB error: {e}")
                print(f"        DB ERROR: {e}")
            finally:
                if conn:
                    conn.close()

            # 8. Shadow risk (optional)
            if include_shadow:
                t0 = time.time()
                height_m = None
                raw_h = controls.get("height")
                if raw_h:
                    import re
                    m = re.search(r"(\d+(?:\.\d+)?)", str(raw_h))
                    if m:
                        height_m = float(m.group(1))
                shadow_result = get_shadow_risk(addr, prop_id, lat, lng, height_m)
                entry["timing_s"]["shadow"] = round(time.time() - t0, 2)
                if shadow_result:
                    entry["raw_data"]["shadow"] = {
                        "has_result": True,
                        "keys": sorted(shadow_result.keys()) if isinstance(shadow_result, dict) else [],
                    }
                    print(f"        shadow=YES ({entry['timing_s']['shadow']}s)")
                else:
                    entry["raw_data"]["shadow"] = {"has_result": False}
                    print(f"        shadow=None ({entry['timing_s']['shadow']}s)")

            # 10. Evaluate compound constraints
            entry["compound_constraints_fired"] = evaluate_compound_constraints(
                controls, overlays, heritage_postgis
            )
            if entry["compound_constraints_fired"]:
                rules = [c["rule"] for c in entry["compound_constraints_fired"]]
                print(f"        COMPOUND: {rules}")

            # 11. Check for issues
            # Strata misclassification check
            if test["type"] == "strata_townhouse" and entry["strata_classification"] == "apartment":
                entry["issues"].append(
                    f"STRATA MISCLASSIFICATION: classified as apartment but expected townhouse/development "
                    f"(lot_area={valuation.get('lot_area_m2')})"
                )
            if test["type"] == "strata_apartment" and entry["strata_classification"] != "apartment":
                entry["issues"].append(
                    f"STRATA MISCLASSIFICATION: classified as {entry['strata_classification']} but expected apartment "
                    f"(lot_area={valuation.get('lot_area_m2')})"
                )

            # LGA boundary check
            if test["type"] == "boundary_lga" and not lga_slug:
                entry["issues"].append("LGA DETECTION FAILED: detect_former_council returned None")

            # Rural DCP check
            if test["type"] == "rural_no_dcp" and dcp_setbacks:
                entry["issues"].append("UNEXPECTED: rural lot returned DCP setbacks")

            # DA presence check
            if test["type"] == "da_shadow" and not nearby_das:
                entry["issues"].append("NO NEARBY DAs: expected DAs within 200m")

        except Exception as e:
            entry["issues"].append(f"FATAL: {e}")
            print(f"        FATAL ERROR: {e}")
            import traceback
            traceback.print_exc()

        results.append(entry)

        # Rate limit — Planning Portal returns 429 if too fast
        time.sleep(3.0)

    return results


def print_summary(results: list):
    """Print analysis summary."""
    print("\n" + "=" * 80)
    print("SPIKE RESULTS SUMMARY")
    print("=" * 80)

    # Compound constraints
    print("\n--- Compound Constraints ---")
    for r in results:
        if r["compound_constraints_fired"]:
            rules = [c["rule"] for c in r["compound_constraints_fired"]]
            print(f"  [{r['index']:2d}] {r['address'][:50]:50s} => {rules}")
    no_compound = [r for r in results if not r["compound_constraints_fired"]]
    print(f"  ({len(no_compound)} addresses had no compound constraints)")

    # Strata classification
    print("\n--- Strata Classification ---")
    for r in results:
        if r["test_type"] in ("strata_apartment", "strata_townhouse", "community_title"):
            strata = r["raw_data"].get("strata", {})
            lot = r["raw_data"].get("valuation", {}).get("lot_area_m2")
            print(f"  [{r['index']:2d}] {r['address'][:50]:50s}")
            print(f"       is_strata={strata.get('is_strata')} source={strata.get('source')} "
                  f"lot={lot}m² => {r['strata_classification']}")

    # LGA detection
    print("\n--- LGA Detection ---")
    for r in results:
        if r["test_type"] == "boundary_lga" or r.get("lga_slug"):
            print(f"  [{r['index']:2d}] {r['address'][:50]:50s} => slug={r['lga_slug']}")

    # Issues
    issues = [r for r in results if r["issues"]]
    print(f"\n--- Issues ({len(issues)} addresses) ---")
    for r in issues:
        print(f"  [{r['index']:2d}] {r['address'][:50]:50s}")
        for issue in r["issues"]:
            print(f"       ⚠ {issue}")

    # Timing
    print("\n--- Timing (seconds) ---")
    total_times = {}
    for r in results:
        for k, v in (r.get("timing_s") or {}).items():
            total_times.setdefault(k, []).append(v)
    for k in sorted(total_times):
        vals = total_times[k]
        print(f"  {k:15s}: avg={sum(vals)/len(vals):.2f}  max={max(vals):.2f}  total={sum(vals):.2f}")


if __name__ == "__main__":
    no_shadow = "--no-shadow" in sys.argv
    print(f"Intelligence Brief Spike — {date.today()}")
    print(f"Testing {len(TEST_ADDRESSES)} addresses\n")

    results = run_spike(include_shadow=not no_shadow)
    print_summary(results)

    # Save full JSON
    out_path = os.path.join(_root, "docs", "intelligence-brief")
    os.makedirs(out_path, exist_ok=True)
    out_file = os.path.join(out_path, "spike-results.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nFull results saved to {out_file}")
