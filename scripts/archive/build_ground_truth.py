"""
Build SAR coherence ground truth dataset from NSW ePlanning OnlineCC records.

Pulls construction certificates for greenfield LGAs, filters to new dwelling
house builds on lots >300m², submits HyP3 jobs for 3 windows after CC date,
extracts coherence vs pre-CC baseline, writes results to CSV.

Usage:
    python scripts/build_ground_truth.py --fetch       # pull CCs, save to ground_truth/cc_records.json
    python scripts/build_ground_truth.py --submit N    # submit HyP3 jobs for first N records
    python scripts/build_ground_truth.py --process     # extract coherence from completed jobs
    python scripts/build_ground_truth.py --report      # print accuracy summary
"""
import os, sys, json, pathlib, argparse, time, zipfile, csv
from datetime import date, timedelta

os.environ.setdefault("ASF_EARTHDATA_USERNAME", "bandylala")
creds = pathlib.Path(__file__).parent / "drawdown_creds.txt"
for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
    if line.strip() and not line.startswith("#"):
        os.environ["ASF_EARTHDATA_PASSWORD"] = line.strip()
        break

import requests
import asf_search as asf
import hyp3_sdk as sdk
from hyp3_sdk import Batch
import rasterio
from rasterio.crs import CRS
from rasterio.transform import rowcol
from rasterio.warp import transform as warp_transform

OUTPUT_DIR = pathlib.Path(__file__).parent.parent / "validation_output" / "ground_truth"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CC_RECORDS_FILE = OUTPUT_DIR / "cc_records.json"
JOBS_FILE = OUTPUT_DIR / "gt_jobs.json"
RESULTS_FILE = OUTPUT_DIR / "gt_results.csv"

EPLANNING_URL = "https://api.apps1.nsw.gov.au/eplanning/data/v0/OnlineCC"

# Greenfield LGAs with high new-build turnover
TARGET_COUNCILS = [
    "BLACKTOWN CITY COUNCIL",
    "THE HILLS SHIRE COUNCIL",
    "CAMDEN COUNCIL",
    "PENRITH CITY COUNCIL",
]

# CC determination window — construction started during this period
CC_DATE_FROM = "2023-06-01"
CC_DATE_TO   = "2024-03-31"

# Minimum lot area to filter out tiny lots (weak SAR signal)
MIN_LOT_AREA_M2 = 450.0
MAX_LOT_AREA_M2 = 5000.0   # exclude rural/industrial outliers

HYPO3_USERNAME = os.environ["ASF_EARTHDATA_USERNAME"]
HYPO3_PASSWORD = os.environ["ASF_EARTHDATA_PASSWORD"]


def fetch_ccs() -> list[dict]:
    """Pull all matching CC records from ePlanning API."""
    records = []
    for council in TARGET_COUNCILS:
        print(f"\nFetching CCs for {council}...")
        page = 1
        while True:
            resp = requests.get(
                EPLANNING_URL,
                headers={
                    "Content-Type": "application/json",
                    "PageSize": "100",
                    "PageNumber": str(page),
                    "filters": json.dumps({"filters": {
                        "CouncilName": [council],
                        "DeterminationDateFrom": CC_DATE_FROM,
                        "DeterminationDateTo": CC_DATE_TO,
                        "ApplicationStatus": ["Determined"],
                    }}),
                },
                timeout=30,
            )
            data = resp.json()
            apps = data.get("Application", [])
            if not apps:
                break

            for a in apps:
                dev_types = [d["DevelopmentType"] for d in a.get("DevelopmentType", [])]
                if not any("Dwelling house" in t or "Erection of a new structure" in t for t in dev_types):
                    continue
                lot_area = a.get("LandArea") or 0
                if lot_area < MIN_LOT_AREA_M2 or lot_area > MAX_LOT_AREA_M2:
                    continue
                loc = a.get("Location", [{}])[0]
                x = loc.get("X", "")
                y = loc.get("Y", "")
                if not x or not y or x == "0" or y == "0":
                    continue
                records.append({
                    "pan": a["PlanningPortalApplicationNumber"],
                    "address": loc.get("FullAddress", ""),
                    "council": council,
                    "cc_date": a.get("DeterminationDate", "")[:10],
                    "lot_area_m2": lot_area,
                    "lat": float(y),
                    "lon": float(x),
                    "builder": a.get("BuilderLegalName", ""),
                })

            total_pages = data.get("TotalPages", 1)
            print(f"  Page {page}/{total_pages} — {len(apps)} apps, {len(records)} qualifying so far")
            if page >= total_pages:
                break
            page += 1
            time.sleep(0.5)

    print(f"\nTotal qualifying CC records: {len(records)}")
    return records


def find_orbit9_pairs(lat: float, lon: float, cc_date: str, n_pairs: int = 3) -> list[tuple]:
    """Find orbit-9 12-day pairs starting from cc_date."""
    buf = 0.0005
    bbox_wkt = (
        f"POLYGON(({lon-buf} {lat-buf}, {lon+buf} {lat-buf}, "
        f"{lon+buf} {lat+buf}, {lon-buf} {lat+buf}, {lon-buf} {lat-buf}))"
    )
    # Search 6 months after CC date for post-construction windows
    start = cc_date
    end_dt = date.fromisoformat(cc_date) + timedelta(days=180)
    end = end_dt.isoformat()

    try:
        results = asf.search(
            platform=asf.PLATFORM.SENTINEL1,
            processingLevel=asf.PRODUCT_TYPE.SLC,
            intersectsWith=bbox_wkt,
            start=start,
            end=end,
        )
    except Exception as e:
        print(f"    ASF search error: {e}")
        return []

    orbit9 = sorted(
        [r for r in results
         if str(r.properties.get("pathNumber")) == "9"
         and r.properties["startTime"][11:14] == "08:"],
        key=lambda r: r.properties["startTime"]
    )

    pairs = []
    for i in range(len(orbit9) - 1):
        a, b = orbit9[i], orbit9[i + 1]
        da = a.properties["startTime"][:10]
        db = b.properties["startTime"][:10]
        gap = (date.fromisoformat(db) - date.fromisoformat(da)).days
        if 10 <= gap <= 14:
            pairs.append((a.properties["sceneName"], b.properties["sceneName"], da, db))
        if len(pairs) >= n_pairs:
            break

    return pairs


def find_pre_cc_pairs(lat: float, lon: float, cc_date: str, n_pairs: int = 2) -> list[tuple]:
    """Find orbit-9 12-day pairs in the 6 months BEFORE cc_date (baseline)."""
    buf = 0.0005
    bbox_wkt = (
        f"POLYGON(({lon-buf} {lat-buf}, {lon+buf} {lat-buf}, "
        f"{lon+buf} {lat+buf}, {lon-buf} {lat+buf}, {lon-buf} {lat-buf}))"
    )
    end = cc_date
    start_dt = date.fromisoformat(cc_date) - timedelta(days=180)
    start = start_dt.isoformat()

    try:
        results = asf.search(
            platform=asf.PLATFORM.SENTINEL1,
            processingLevel=asf.PRODUCT_TYPE.SLC,
            intersectsWith=bbox_wkt,
            start=start,
            end=end,
        )
    except Exception as e:
        print(f"    ASF baseline search error: {e}")
        return []

    orbit9 = sorted(
        [r for r in results
         if str(r.properties.get("pathNumber")) == "9"
         and r.properties["startTime"][11:14] == "08:"],
        key=lambda r: r.properties["startTime"]
    )

    pairs = []
    for i in range(len(orbit9) - 1):
        a, b = orbit9[i], orbit9[i + 1]
        da = a.properties["startTime"][:10]
        db = b.properties["startTime"][:10]
        gap = (date.fromisoformat(db) - date.fromisoformat(da)).days
        if 10 <= gap <= 14:
            pairs.append((a.properties["sceneName"], b.properties["sceneName"], da, db))
        if len(pairs) >= n_pairs:
            break

    return pairs


def submit_jobs(records: list[dict], n: int):
    """Submit HyP3 jobs for first n records, sorted by lot size descending."""
    hyp3 = sdk.HyP3(username=HYPO3_USERNAME, password=HYPO3_PASSWORD)
    existing = json.loads(JOBS_FILE.read_text()) if JOBS_FILE.exists() else []
    existing_pans = {j["pan"] for j in existing}

    # Prioritise large lots — stronger SAR signal, higher detection probability
    records = sorted(records, key=lambda r: r.get("lot_area_m2", 0), reverse=True)

    new_jobs = []
    for rec in records[:n]:
        pan = rec["pan"]
        if pan in existing_pans:
            print(f"  {pan}: already submitted, skipping")
            continue

        print(f"\n{pan} — {rec['address']}")
        print(f"  CC date: {rec['cc_date']}, lot: {rec['lot_area_m2']}m2")

        # Pre-construction baseline pairs
        pre_pairs = find_pre_cc_pairs(rec["lat"], rec["lon"], rec["cc_date"], n_pairs=2)
        # Post-construction pairs
        post_pairs = find_orbit9_pairs(rec["lat"], rec["lon"], rec["cc_date"], n_pairs=3)

        if not post_pairs:
            print(f"  No orbit-9 pairs found, skipping")
            continue

        print(f"  Pre-CC pairs: {len(pre_pairs)}, Post-CC pairs: {len(post_pairs)}")

        job_entry = {
            "pan": pan,
            "address": rec["address"],
            "lat": rec["lat"],
            "lon": rec["lon"],
            "cc_date": rec["cc_date"],
            "lot_area_m2": rec["lot_area_m2"],
            "pre_jobs": [],
            "post_jobs": [],
        }

        for s1, s2, da, db in pre_pairs:
            name = f"gt-pre-{pan[-6:]}-{da}"[:30]
            try:
                job = hyp3.submit_insar_job(
                    granule1=s1, granule2=s2, name=name,
                    looks="10x2", apply_water_mask=False,
                    include_dem=False, include_wrapped_phase=False,
                )
                jid = str(job.jobs[0].job_id)
                job_entry["pre_jobs"].append({"job_id": jid, "dates": f"{da}->{db}"})
                print(f"  Pre  {da}->{db}: {jid}")
            except Exception as e:
                print(f"  Pre job error: {e}")

        for s1, s2, da, db in post_pairs:
            name = f"gt-pst-{pan[-6:]}-{da}"[:30]
            try:
                job = hyp3.submit_insar_job(
                    granule1=s1, granule2=s2, name=name,
                    looks="10x2", apply_water_mask=False,
                    include_dem=False, include_wrapped_phase=False,
                )
                jid = str(job.jobs[0].job_id)
                job_entry["post_jobs"].append({"job_id": jid, "dates": f"{da}->{db}"})
                print(f"  Post {da}->{db}: {jid}")
            except Exception as e:
                print(f"  Post job error: {e}")

        new_jobs.append(job_entry)
        time.sleep(1)

    all_jobs = existing + new_jobs
    JOBS_FILE.write_text(json.dumps(all_jobs, indent=2))
    print(f"\nSaved {len(all_jobs)} records to {JOBS_FILE}")
    print(f"Credits remaining: {hyp3.check_credits()}")


def extract_coherence(job_id: str, lat: float, lon: float, hyp3) -> float | None:
    """Download job, extract 3x3 window coherence at centroid. Returns None on error."""
    job_dir = OUTPUT_DIR / "jobs" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    j = hyp3.get_job_by_id(job_id)
    if j.status_code != "SUCCEEDED":
        return None

    zip_files = list(job_dir.glob("*.zip"))
    if not zip_files:
        Batch([j]).download_files(location=str(job_dir))
        zip_files = list(job_dir.glob("*.zip"))

    corr_files = list(job_dir.rglob("*_corr.tif"))
    if not corr_files and zip_files:
        with zipfile.ZipFile(zip_files[0]) as zf:
            zf.extractall(str(job_dir))
        corr_files = list(job_dir.rglob("*_corr.tif"))

    if not corr_files:
        return None

    try:
        with rasterio.open(str(corr_files[0])) as src:
            data = src.read(1)
            xs, ys = warp_transform(CRS.from_epsg(4326), src.crs, [lon], [lat])
            row, col = rowcol(src.transform, xs[0], ys[0])
            h, w = data.shape
            if 0 <= row < h and 0 <= col < w:
                r0, r1 = max(0, row - 1), min(h, row + 2)
                c0, c1 = max(0, col - 1), min(w, col + 2)
                return float(data[r0:r1, c0:c1].mean())
    except Exception as e:
        print(f"    rasterio error: {e}")
    return None


def process_results():
    """Extract coherence for all completed jobs, write CSV."""
    if not JOBS_FILE.exists():
        print("No jobs file. Run --submit first.")
        return

    hyp3 = sdk.HyP3(username=HYPO3_USERNAME, password=HYPO3_PASSWORD)
    job_records = json.loads(JOBS_FILE.read_text())

    rows = []
    for rec in job_records:
        pan = rec["pan"]
        lat, lon = rec["lat"], rec["lon"]
        print(f"\n{pan} — {rec['address']}")

        pre_vals = []
        for j in rec["pre_jobs"]:
            val = extract_coherence(j["job_id"], lat, lon, hyp3)
            if val is not None:
                pre_vals.append(val)
                print(f"  Pre  {j['dates']}: {val:.4f}")

        post_vals = []
        for j in rec["post_jobs"]:
            val = extract_coherence(j["job_id"], lat, lon, hyp3)
            if val is not None:
                post_vals.append(val)
                print(f"  Post {j['dates']}: {val:.4f}")

        if not pre_vals or not post_vals:
            print(f"  Skipping — insufficient data")
            continue

        baseline = sum(pre_vals) / len(pre_vals)
        min_post = min(post_vals)
        drop = baseline - min_post
        # Signal detected if any post window drops >4% below pre-CC baseline
        signal = drop > 0.04

        rows.append({
            "pan": pan,
            "address": rec["address"],
            "cc_date": rec["cc_date"],
            "lot_area_m2": rec["lot_area_m2"],
            "lat": lat,
            "lon": lon,
            "pre_baseline": round(baseline, 4),
            "min_post_coherence": round(min_post, 4),
            "drop": round(drop, 4),
            "signal_detected": signal,
            "pre_windows": len(pre_vals),
            "post_windows": len(post_vals),
        })
        print(f"  Baseline: {baseline:.4f}, Min post: {min_post:.4f}, Drop: {drop:.4f}, Signal: {signal}")

    if not rows:
        print("No results to write.")
        return

    with open(RESULTS_FILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {RESULTS_FILE}")


def report():
    """Print accuracy summary from results CSV."""
    if not RESULTS_FILE.exists():
        print("No results file. Run --process first.")
        return

    rows = list(csv.DictReader(open(RESULTS_FILE)))
    n = len(rows)
    detected = sum(1 for r in rows if r["signal_detected"] == "True")
    not_detected = n - detected
    avg_drop = sum(float(r["drop"]) for r in rows) / n if n else 0

    print(f"\n{'='*50}")
    print(f"GROUND TRUTH RESULTS — n={n}")
    print(f"{'='*50}")
    print(f"Signal detected:     {detected}/{n} ({100*detected/n:.1f}%)")
    print(f"Not detected:        {not_detected}/{n} ({100*not_detected/n:.1f}%)")
    print(f"Avg coherence drop:  {avg_drop:.4f}")
    print()

    # Breakdown by lot size
    small = [r for r in rows if float(r["lot_area_m2"]) < 500]
    large = [r for r in rows if float(r["lot_area_m2"]) >= 500]
    if small:
        s_det = sum(1 for r in small if r["signal_detected"] == "True")
        print(f"Lots <500m2:  {s_det}/{len(small)} detected ({100*s_det/len(small):.1f}%)")
    if large:
        l_det = sum(1 for r in large if r["signal_detected"] == "True")
        print(f"Lots >=500m2: {l_det}/{len(large)} detected ({100*l_det/len(large):.1f}%)")

    # Worst performers (no signal despite CC)
    missed = [r for r in rows if r["signal_detected"] == "False"]
    if missed:
        print(f"\nMissed ({len(missed)}):")
        for r in missed[:5]:
            print(f"  {r['pan']} {r['address']} lot={r['lot_area_m2']}m2 drop={r['drop']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch",   action="store_true", help="Pull CC records from ePlanning")
    parser.add_argument("--submit",  type=int, metavar="N", help="Submit HyP3 jobs for first N records")
    parser.add_argument("--process", action="store_true", help="Extract coherence from completed jobs")
    parser.add_argument("--report",  action="store_true", help="Print accuracy summary")
    args = parser.parse_args()

    if args.fetch:
        records = fetch_ccs()
        CC_RECORDS_FILE.write_text(json.dumps(records, indent=2))
        print(f"Saved {len(records)} records to {CC_RECORDS_FILE}")

    elif args.submit is not None:
        if not CC_RECORDS_FILE.exists():
            print("No CC records. Run --fetch first.")
            sys.exit(1)
        records = json.loads(CC_RECORDS_FILE.read_text())
        submit_jobs(records, args.submit)

    elif args.process:
        process_results()

    elif args.report:
        report()

    else:
        parser.print_help()
