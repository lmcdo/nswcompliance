"""Quick scene availability check for 3 placeholder validation sites."""
import asf_search as asf

SITES = [
    {
        "name": "parramatta_test",
        "bbox": "POLYGON((151.000 -33.820, 151.004 -33.820, 151.004 -33.816, 151.000 -33.816, 151.000 -33.820))",
        "start": "2023-08-15",
        "end": "2023-09-30",
        "cc_date": "2023-09-15",
    },
    {
        "name": "hills_district_test",
        "bbox": "POLYGON((150.990 -33.730, 150.994 -33.730, 150.994 -33.726, 150.990 -33.726, 150.990 -33.730))",
        "start": "2023-05-20",
        "end": "2023-07-05",
        "cc_date": "2023-06-20",
    },
    {
        "name": "inner_west_test",
        "bbox": "POLYGON((151.148 -33.896, 151.152 -33.896, 151.152 -33.892, 151.148 -33.892, 151.148 -33.896))",
        "start": "2023-10-10",
        "end": "2023-11-25",
        "cc_date": "2023-11-10",
    },
]


def find_pair(site):
    results = asf.search(
        platform=asf.PLATFORM.SENTINEL1,
        processingLevel=asf.PRODUCT_TYPE.SLC,
        intersectsWith=site["bbox"],
        start=site["start"],
        end=site["end"],
    )

    results_sorted = sorted(results, key=lambda r: r.properties.get("startTime", ""))

    # Group by orbit
    orbit_groups = {}
    for r in results_sorted:
        orbit = str(r.properties.get("pathNumber", ""))
        orbit_groups.setdefault(orbit, []).append(r)

    print(f"\n--- {site['name']} ({len(results)} scenes total) ---")
    for orbit, scenes in sorted(orbit_groups.items(), key=lambda x: -len(x[1])):
        print(f"  Orbit {orbit}: {len(scenes)} scenes")
        for s in scenes[:3]:
            p = s.properties
            print(f"    {p['sceneName']}  date={p['startTime'][:10]}")

    # Primary orbit
    if not orbit_groups:
        print("  ERROR: no scenes found")
        return None

    primary_orbit = max(orbit_groups, key=lambda k: len(orbit_groups[k]))
    candidates = orbit_groups[primary_orbit]

    # Find before/after pair
    cc = site["cc_date"]
    before = after = None
    for s in candidates:
        d = s.properties["startTime"][:10]
        if d <= cc:
            before = s
        elif before is not None and after is None:
            after = s
            break

    if before is None or after is None:
        if len(candidates) >= 2:
            before, after = candidates[0], candidates[1]
            print(f"  Fallback pair (could not bracket {cc})")
        else:
            print(f"  ERROR: not enough scenes on orbit {primary_orbit}")
            return None

    db = before.properties["startTime"][:10]
    da = after.properties["startTime"][:10]
    sb = before.properties["sceneName"]
    sa = after.properties["sceneName"]
    print(f"  SELECTED PAIR: {db} -> {da}")
    print(f"    before: {sb}")
    print(f"    after:  {sa}")
    return sb, sa, db, da


for site in SITES:
    find_pair(site)

print("\nDone.")
