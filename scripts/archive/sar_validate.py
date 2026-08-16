"""
SAR signal validation using the existing NSW Planning Portal address lookup.
Resolves address -> propId -> lot polygon -> centroid -> ASF scene search -> HyP3 job.

Usage:
    python scripts/sar_validate.py "21 Martens Circuit, Kellyville NSW 2155" 2023-01-01 2023-12-31
    python scripts/sar_validate.py "ADDRESS" START_DATE END_DATE [--submit]
"""
import asyncio, sys, os, json, pathlib
os.environ.setdefault("ASF_EARTHDATA_USERNAME", "bandylala")
creds = pathlib.Path(__file__).parent / "drawdown_creds.txt"
for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
    if line.strip() and not line.startswith("#"):
        os.environ["ASF_EARTHDATA_PASSWORD"] = line.strip()
        break

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from services.nsw_planning_api import NSWPlanningAPI
import asf_search as asf

ADDRESS    = sys.argv[1] if len(sys.argv) > 1 else "21 Martens Circuit, Kellyville NSW 2155"
START_DATE = sys.argv[2] if len(sys.argv) > 2 else "2022-07-01"
END_DATE   = sys.argv[3] if len(sys.argv) > 3 else "2023-06-30"
SUBMIT     = "--submit" in sys.argv

OUTPUT_DIR = pathlib.Path(__file__).parent.parent / "validation_output"
OUTPUT_DIR.mkdir(exist_ok=True)


async def resolve_address(address: str):
    async with NSWPlanningAPI() as api:
        results = await api.lookup_property_id(address)
        if not results:
            raise SystemExit(f"Address not found: {address}")

        prop = results[0]
        prop_id = prop.get("propId")
        print(f"  propId: {prop_id}")
        print(f"  Matched address: {prop.get('address')}")

        lot_data = await api.get_lot_data(prop_id)
        if not lot_data:
            raise SystemExit(f"No lot data for propId {prop_id}")

        lot = lot_data[0]
        # Lot data returns geometry in GDA94 / MGA Zone 56 (EPSG:28356) — need WGS84
        # The NSW API returns centroid as part of the feature
        print(f"  Lot data keys: {list(lot.keys())}")
        return prop_id, lot


def web_mercator_to_wgs84(x, y):
    """Convert EPSG:3857 to WGS84 lat/lon."""
    import math
    lon = x / 20037508.34 * 180.0
    lat = math.degrees(2 * math.atan(math.exp(y / 20037508.34 * math.pi)) - math.pi / 2)
    return lat, lon


async def main():
    print(f"Address: {ADDRESS}")
    print(f"Search window: {START_DATE} to {END_DATE}")
    print()

    # Step 1: Resolve address
    print("Step 1: Resolve address via NSW Planning Portal...")
    prop_id, lot = await resolve_address(ADDRESS)

    # Step 2: Convert lot polygon to WGS84, compute centroid + bbox
    rings = lot["geometry"]["rings"][0]
    coords_wgs84 = [web_mercator_to_wgs84(x, y) for x, y in rings]
    lats = [c[0] for c in coords_wgs84]
    lons = [c[1] for c in coords_wgs84]
    centroid_lat = sum(lats) / len(lats)
    centroid_lon = sum(lons) / len(lons)
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    # Add 50m buffer to bbox
    buf = 0.0005
    bbox_wkt = (
        f"POLYGON(({min_lon-buf} {min_lat-buf}, {max_lon+buf} {min_lat-buf}, "
        f"{max_lon+buf} {max_lat+buf}, {min_lon-buf} {max_lat+buf}, {min_lon-buf} {min_lat-buf}))"
    )

    print(f"  Centroid (WGS84): {centroid_lat:.6f}, {centroid_lon:.6f}")
    print(f"  Lot bbox: [{min_lon:.6f}, {min_lat:.6f}, {max_lon:.6f}, {max_lat:.6f}]")
    print(f"  BBox WKT: {bbox_wkt}")

    # Step 3: ASF scene search
    print(f"\nStep 2: ASF scene search ({START_DATE} to {END_DATE})...")
    results = asf.search(
        platform=asf.PLATFORM.SENTINEL1,
        processingLevel=asf.PRODUCT_TYPE.SLC,
        intersectsWith=bbox_wkt,
        start=START_DATE,
        end=END_DATE,
    )

    # Group by orbit
    orbit_groups = {}
    for r in results:
        orbit = str(r.properties.get("pathNumber", ""))
        orbit_groups.setdefault(orbit, []).append(r)

    print(f"  {len(results)} scenes across {len(orbit_groups)} orbits")
    for orbit, scenes in sorted(orbit_groups.items(), key=lambda x: -len(x[1])):
        scenes = sorted(scenes, key=lambda r: r.properties["startTime"])
        print(f"  Orbit {orbit}: {len(scenes)} scenes")
        for s in scenes[:4]:
            p = s.properties
            print(f"    {p['sceneName']}  {p['startTime'][:10]}  t={p['startTime'][11:16]}")

    # Step 4: Find 12-day matched pairs on orbit 9
    orbit9 = sorted(
        [r for r in results if str(r.properties.get("pathNumber")) == "9"
         and r.properties["startTime"][11:14] == "08:"],
        key=lambda r: r.properties["startTime"]
    )
    print(f"\n  Orbit-9 (08:xx) scenes: {len(orbit9)}")

    from datetime import date as ddate
    pairs = []
    for i in range(len(orbit9) - 1):
        a, b = orbit9[i], orbit9[i+1]
        da = a.properties["startTime"][:10]
        db = b.properties["startTime"][:10]
        gap = (ddate.fromisoformat(db) - ddate.fromisoformat(da)).days
        if 10 <= gap <= 14:
            pairs.append((a, b, da, db))

    print(f"  Valid 12-day pairs: {len(pairs)}")
    for a, b, da, db in pairs[:6]:
        print(f"    {da} -> {db}")

    if not pairs:
        print("  No valid pairs. Try wider date range.")
        return

    # Save info
    info = {
        "address": ADDRESS,
        "prop_id": prop_id,
        "centroid_lat": centroid_lat,
        "centroid_lon": centroid_lon,
        "bbox_wkt": bbox_wkt,
        "search_window": f"{START_DATE} to {END_DATE}",
        "pairs": [[da, db, a.properties["sceneName"], b.properties["sceneName"]]
                  for a, b, da, db in pairs],
    }
    out = OUTPUT_DIR / "sar_validate_info.json"
    out.write_text(json.dumps(info, indent=2))
    print(f"\n  Saved to {out}")
    print(f"\nTo submit jobs, add --submit flag or run submit_kellyville_job.py with these pairs.")

    if SUBMIT:
        import hyp3_sdk as sdk
        hyp3 = sdk.HyP3(
            username=os.environ["ASF_EARTHDATA_USERNAME"],
            password=os.environ["ASF_EARTHDATA_PASSWORD"]
        )
        submitted = []
        # Submit first 3 pairs
        for a, b, da, db in pairs[:3]:
            job_name = f"val-{da}-{db}"[:30]
            print(f"\n  Submitting {job_name}...")
            try:
                job = hyp3.submit_insar_job(
                    granule1=a.properties["sceneName"],
                    granule2=b.properties["sceneName"],
                    name=job_name,
                    looks="10x2",
                    apply_water_mask=False,
                    include_dem=False,
                    include_wrapped_phase=False,
                )
                jid = str(job.jobs[0].job_id)
                print(f"  Job ID: {jid}")
                submitted.append({"job_id": jid, "dates": f"{da}->{db}",
                                   "centroid_lat": centroid_lat, "centroid_lon": centroid_lon})
            except Exception as e:
                print(f"  ERROR: {e}")

        jobs_out = OUTPUT_DIR / "submitted_jobs.json"
        existing = json.loads(jobs_out.read_text()) if jobs_out.exists() else []
        jobs_out.write_text(json.dumps(existing + submitted, indent=2))
        print(f"\n  Jobs saved to {jobs_out}")
        print(f"  Credits remaining: {hyp3.check_credits()}")


asyncio.run(main())
