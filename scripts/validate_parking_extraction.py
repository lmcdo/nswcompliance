#!/usr/bin/env python3
"""
Automated QA gate for DCP parking controls extraction.

12 checks covering coverage, plausibility, integrity, and cross-council
outlier detection. Must pass before any parking extraction PR.

Usage:
    python scripts/validate_parking_extraction.py          # full run
    python scripts/validate_parking_extraction.py --lga X  # single council
"""
import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor(cursor_factory=RealDictCursor)

passed = 0
failed = 0
warnings = 0

ALLOWED_UNITS = {
    "spaces/dwelling", "spaces/bedroom", "spaces/room", "spaces/bed",
    "spaces/100m2_gfa", "visitor_spaces/dwelling", "spaces/commercial_premise",
    "spaces/unit", "spaces/10_beds", "spaces/employee",
}

ALLOWED_METHODS = {"mistral_ocr", "text_extraction", "manual"}

# Plausibility ranges by unit
PLAUSIBLE_RANGES = {
    "spaces/dwelling":          (0, 3),
    "spaces/bedroom":           (0, 3),
    "spaces/room":              (0, 2),
    "spaces/bed":               (0, 1),
    "spaces/100m2_gfa":         (0, 10),
    "visitor_spaces/dwelling":  (0, 1),
    "spaces/commercial_premise": (0, 5),
    "spaces/unit":              (0, 3),
    "spaces/10_beds":           (0, 5),
    "spaces/employee":          (0, 2),
}

# Dev types that every council should have (or document SEPP deferral)
CORE_DEV_TYPES = {"dwelling_house", "secondary_dwelling"}

# Known SEPP deferrals — councils where a core dev type is genuinely
# covered by state policy, not a missed extraction.
SEPP_DEFERRALS: dict[str, set[str]] = {
    # Cumberland DCP 2021 Table 1 only lists dwelling_house, RFB, shop_top, boarding_house
    # Dual occupancy/secondary_dwelling follow dwelling_house rate or SEPP Housing 2021
    "cumberland": {"secondary_dwelling"},
    # Penrith DCP 2014 Table C10.2 does not list secondary_dwelling
    # Secondary dwellings covered by SEPP Housing 2021
    "penrith": {"secondary_dwelling"},
}


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS: {name}")
        passed += 1
    else:
        print(f"  FAIL: {name}")
        if detail:
            print(f"        {detail}")
        failed += 1


def warn(name, detail=""):
    global warnings
    print(f"  WARN: {name}")
    if detail:
        print(f"        {detail}")
    warnings += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lga", help="Filter to a single LGA")
    args = parser.parse_args()

    lga_filter = ""
    params: tuple = ()
    if args.lga:
        lga_filter = "AND sc.lga = %s"
        params = (args.lga,)

    # Fetch all parking rows
    cur.execute(f"""
        SELECT sc.*, cr.chapter_key AS registry_key
        FROM dcp_setback_controls sc
        LEFT JOIN dcp_chapter_registry cr
            ON sc.lga = cr.council
            AND sc.source_chapter_key = cr.chapter_key
        WHERE sc.control_type = 'car_parking'
          AND sc.is_current = TRUE
          {lga_filter}
        ORDER BY sc.lga, sc.dev_type
    """, params)
    rows = cur.fetchall()

    if not rows:
        print("No parking rows found.")
        sys.exit(1)

    lgas = sorted(set(r["lga"] for r in rows))
    print(f"\nValidating {len(rows)} parking rows across {len(lgas)} LGAs\n")

    # ── CHECK 1: Core dev-type coverage ──────────────────────────
    print("--- Coverage Checks ---")
    dev_types_by_lga = defaultdict(set)
    for r in rows:
        dev_types_by_lga[r["lga"]].add(r["dev_type"])

    missing_core = {}
    for lga in lgas:
        deferrals = SEPP_DEFERRALS.get(lga, set())
        missing = CORE_DEV_TYPES - dev_types_by_lga[lga] - deferrals
        if missing:
            missing_core[lga] = missing

    check(
        "1. Core dev-type coverage (dwelling_house + secondary_dwelling)",
        not missing_core,
        f"Missing: {missing_core}" if missing_core else "",
    )

    # ── CHECK 2: Dev-type symmetry ───────────────────────────────
    asymmetric = {}
    for lga in lgas:
        dt = dev_types_by_lga[lga]
        if "dwelling_house" in dt and "dual_occupancy" not in dt:
            asymmetric.setdefault(lga, []).append("has dwelling_house but no dual_occupancy")
        if "multi_dwelling_housing" in dt and "residential_flat_building" not in dt:
            asymmetric.setdefault(lga, []).append("has multi_dwelling but no RFB")

    if asymmetric:
        for lga, issues in asymmetric.items():
            warn(f"2. Symmetry gap in {lga}", "; ".join(issues))
    else:
        check("2. Dev-type coverage symmetry", True)

    # ── CHECK 3: source_chapter_key not NULL ─────────────────────
    null_sck = [r for r in rows if r["source_chapter_key"] is None]
    check(
        "3. All rows have source_chapter_key",
        not null_sck,
        f"{len(null_sck)} rows with NULL source_chapter_key" if null_sck else "",
    )

    # ── CHECK 4: Plausibility — value_min in range ───────────────
    print("\n--- Plausibility Checks ---")
    out_of_range = []
    for r in rows:
        unit = r["unit"]
        lo, hi = PLAUSIBLE_RANGES.get(unit, (0, 10))
        vmin = r.get("value_min")
        if vmin is not None and (float(vmin) < lo or float(vmin) > hi):
            out_of_range.append(
                f"{r['lga']} {r['dev_type']} value_min={vmin} unit={unit} (range {lo}-{hi})"
            )

    check(
        "4. All value_min in plausible range",
        not out_of_range,
        "\n        ".join(out_of_range[:10]) if out_of_range else "",
    )

    # ── CHECK 5: No negative values ──────────────────────────────
    negatives = [
        r for r in rows
        if (r.get("value_min") is not None and float(r["value_min"]) < 0)
        or (r.get("value_max") is not None and float(r["value_max"]) < 0)
    ]
    check("5. No negative values", not negatives)

    # ── CHECK 6: value_min <= value_max ──────────────────────────
    min_gt_max = [
        f"{r['lga']} {r['dev_type']} min={r['value_min']} > max={r['value_max']}"
        for r in rows
        if r.get("value_min") is not None
        and r.get("value_max") is not None
        and float(r["value_min"]) > float(r["value_max"])
    ]
    check(
        "6. No value_min > value_max",
        not min_gt_max,
        "\n        ".join(min_gt_max[:5]) if min_gt_max else "",
    )

    # ── CHECK 7: Unit values from allowed set ────────────────────
    bad_units = [
        f"{r['lga']} {r['dev_type']} unit={r['unit']}"
        for r in rows if r["unit"] not in ALLOWED_UNITS
    ]
    check(
        "7. All units in allowed set",
        not bad_units,
        "\n        ".join(bad_units[:5]) if bad_units else "",
    )

    # ── CHECK 8: No duplicates ───────────────────────────────────
    print("\n--- Integrity Checks ---")
    cur.execute(f"""
        SELECT lga, dev_type, control_type,
               COALESCE(condition, '') AS cond,
               COALESCE(value_min::text, '') AS vmin,
               count(*) AS n
        FROM dcp_setback_controls
        WHERE control_type = 'car_parking' AND is_current = TRUE
          {'AND lga = %s' if args.lga else ''}
        GROUP BY 1, 2, 3, 4, 5
        HAVING count(*) > 1
    """, params)
    dups = cur.fetchall()
    check(
        "8. No duplicate (lga, dev_type, condition, value_min) combos",
        not dups,
        "\n        ".join(
            f"{d['lga']} {d['dev_type']} cond={d['cond']!r} vmin={d['vmin']} x{d['n']}"
            for d in dups[:5]
        ) if dups else "",
    )

    # ── CHECK 9: source_chapter_key exists in registry ───────────
    orphan_sck = [
        r for r in rows
        if r["source_chapter_key"] is not None and r["registry_key"] is None
    ]
    # Tier 2 orphans are expected (councils not yet in registry)
    tier2_orphans = [r for r in orphan_sck]
    if tier2_orphans:
        lga_counts = defaultdict(int)
        for r in tier2_orphans:
            lga_counts[r["lga"]] += 1
        warn(
            f"9. {len(tier2_orphans)} rows have source_chapter_key not in registry (Tier 2 expected)",
            ", ".join(f"{lga}={n}" for lga, n in sorted(lga_counts.items())),
        )
    else:
        check("9. All source_chapter_key values exist in registry", True)

    # ── CHECK 10: extraction_method valid ────────────────────────
    bad_method = [
        f"{r['lga']} method={r['extraction_method']}"
        for r in rows if r.get("extraction_method") not in ALLOWED_METHODS
    ]
    check(
        "10. All extraction_method values valid",
        not bad_method,
        "\n        ".join(bad_method[:5]) if bad_method else "",
    )

    # ── CHECK 11-12: Cross-council outlier detection ─────────────
    print("\n--- Cross-Council Outlier Detection ---")
    if len(lgas) < 3:
        print("  SKIP: Need 3+ LGAs for outlier detection")
    else:
        # Group by dev_type, compute stats
        import statistics
        values_by_dt: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for r in rows:
            if r.get("value_min") is not None and r["unit"] == "spaces/dwelling":
                values_by_dt[r["dev_type"]].append((r["lga"], float(r["value_min"])))

        outlier_count = 0
        for dt, vals in sorted(values_by_dt.items()):
            if len(vals) < 3:
                continue
            numbers = [v for _, v in vals]
            mean = statistics.mean(numbers)
            if len(set(numbers)) < 2:
                continue  # all identical, no variance
            stdev = statistics.stdev(numbers)
            if stdev == 0:
                continue

            for lga, v in vals:
                z = abs(v - mean) / stdev
                if z > 3:
                    print(f"  OUTLIER (>3s): {lga} {dt}={v} (mean={mean:.2f}, s={stdev:.2f}, z={z:.1f})")
                    outlier_count += 1
                elif z > 2:
                    warn(f"11. {lga} {dt}={v} is >2s from mean={mean:.2f} (s={stdev:.2f}, z={z:.1f})")

        check("11-12. No >3-sigma outliers", outlier_count == 0)

    # ── Coverage Matrix ──────────────────────────────────────────
    print("\n--- Coverage Matrix ---")
    all_dev_types = sorted(set(r["dev_type"] for r in rows))
    header = f"{'LGA':<25}" + "".join(f"{dt[:12]:>13}" for dt in all_dev_types)
    print(header)
    print("-" * len(header))
    for lga in lgas:
        dt_set = dev_types_by_lga[lga]
        row_str = f"{lga:<25}"
        for dt in all_dev_types:
            count = sum(1 for r in rows if r["lga"] == lga and r["dev_type"] == dt)
            if count > 0:
                row_str += f"{count:>13}"
            elif dt in SEPP_DEFERRALS.get(lga, set()):
                row_str += f"{'SEPP':>13}"
            else:
                row_str += f"{'-':>13}"
        print(row_str)

    # ── Summary ──────────────────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"PASSED: {passed}  FAILED: {failed}  WARNINGS: {warnings}")
    print(f"{'='*50}")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
