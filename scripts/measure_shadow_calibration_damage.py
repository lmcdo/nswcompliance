#!/usr/bin/env python3
# prior-art-checked: reuse not viable because the sibling measurement scripts
# each read a different corpus for a different defect —
# measure_granny_confidence_states.py reads granny_flat rows for badge states,
# measure_control_quote_gap.py and measure_control_type_mismatch.py read
# dcp_setback_controls. None touches property_reports WHERE product='shadow',
# and none computes solar geometry. Same PATTERN (measure-only, print, never
# write), new corpus.
"""Measure the shadow calibration damage in stored reports. READ-ONLY.

Answers, with numbers rather than adjectives:
  1. How many of the stored shadow reports carry the daylight-saving defect,
     and how wrong is the December scenario as a result?
  2. How many carry a surface-change claim, and what evidence sits behind it?
  3. How many serve a physically impossible shadow reach?

WHY MEASURE-ONLY. Repairing stored reports is a separate authorised pass. This
script opens the connection with ``set_session(readonly=True)`` so the server
itself rejects a write, and issues no UPDATE/INSERT/DELETE. Run it, read the
counts, decide separately.

Usage:
    DATABASE_URL=... python scripts/measure_shadow_calibration_damage.py

Exit codes:
    0  measurement completed
    2  DATABASE_URL missing, or the corpus could not be read — never treated as
       "no damage", because "could not measure" and "nothing wrong" must not
       look the same.
"""
from __future__ import annotations

import math
import os
import sys
from collections import Counter
from datetime import datetime, timezone

# Every scenario's LOCAL wall-clock time, matching services/shadow_model.py.
SCENARIOS = {
    "jun21_9am": (6, 21, 9),
    "jun21_12pm": (6, 21, 12),
    "jun21_3pm": (6, 21, 15),
    "sep21_12pm": (9, 21, 12),
    "dec21_12pm": (12, 21, 12),
}
SCENARIO_YEAR = 2025

# The retired constants, as stored in every report written before this change.
RETIRED_DIRECTION_DEG = {
    "jun21_9am": 222.6, "jun21_12pm": 179.2, "jun21_3pm": 136.3,
    "sep21_12pm": 175.0, "dec21_12pm": 183.0,
}

# The UTC hour each scenario was ACTUALLY modelled at before the fix. December
# is the defect: 02:00 UTC is 13:00 AEDT, and the report labelled it 12:00.
OLD_HOUR_UTC = {
    "jun21_9am": 23, "jun21_12pm": 2, "jun21_3pm": 5,
    "sep21_12pm": 2, "dec21_12pm": 2,
}

REACH_CEILING_TOLERANCE = 1.25


def _fail(message: str) -> None:
    print(f"MEASUREMENT FAILED: {message}")
    print("  Not reporting zero damage — an unread corpus is not a clean one.")
    sys.exit(2)


def _angular_difference(a: float, b: float) -> float:
    return (a - b + 180.0) % 360.0 - 180.0


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        _fail("DATABASE_URL is not set")

    try:
        import psycopg2
        import psycopg2.extras
        from suncalc import get_position
        from zoneinfo import ZoneInfo
    except ImportError as e:
        _fail(f"missing dependency: {e}")

    nsw = ZoneInfo("Australia/Sydney")

    def instants(key):
        """(fixed_utc, old_utc) for a scenario — what it models now vs before."""
        month, day, hour = SCENARIOS[key]
        fixed = datetime(SCENARIO_YEAR, month, day, hour, 0, tzinfo=nsw).astimezone(timezone.utc)
        old = datetime(SCENARIO_YEAR, month, day, OLD_HOUR_UTC[key], 0, tzinfo=timezone.utc)
        if key == "jun21_9am":
            old = datetime(SCENARIO_YEAR, 6, 20, 23, 0, tzinfo=timezone.utc)
        return fixed, old

    def sun(dt, lat, lng):
        p = get_position(dt, lng, lat)      # suncalc takes lng FIRST
        return math.degrees(p["altitude"]), math.degrees(p["azimuth"]) % 360.0

    try:
        conn = psycopg2.connect(dsn, connect_timeout=30)
        conn.set_session(readonly=True, autocommit=True)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT p.id, p.lat, p.lng, p.run_date,
                   (p.outputs ->> 'height_m')::numeric        AS height_m,
                   p.outputs ->> 'construction_change_score'  AS change_score,
                   p.outputs ->> 'construction_change_note'   AS change_note,
                   p.outputs ->> 'construction_change_detected' AS change_detected,
                   p.outputs -> 'scenarios'                   AS scenarios
            FROM property_reports p
            WHERE p.product = 'shadow'
        """)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        _fail(f"could not read property_reports: {e}")

    if not rows:
        _fail("no shadow reports found — expected a non-empty corpus")

    print("=" * 88)
    print(f"STORED SHADOW REPORTS: {len(rows)}")
    dates = sorted(r["run_date"] for r in rows if r["run_date"])
    if dates:
        print(f"run_date range: {dates[0]} .. {dates[-1]}")
    print("=" * 88)

    # ---------------------------------------------------------------- defect 1
    print("\n[1] DAYLIGHT SAVING — the December scenario modelled at 13:00 AEDT, labelled 12:00")
    dec_fixed, dec_old = instants("dec21_12pm")
    print(f"    modelled instant: {dec_old.isoformat()} = "
          f"{dec_old.astimezone(nsw):%H:%M} {dec_old.astimezone(nsw).tzname()}")
    print(f"    labelled instant: {dec_fixed.isoformat()} = "
          f"{dec_fixed.astimezone(nsw):%H:%M} {dec_fixed.astimezone(nsw).tzname()}")

    carries_dec = 0
    bearing_shifts, altitude_shifts, length_deltas = [], [], []
    for r in rows:
        scenarios = r["scenarios"] or []
        if not any(s.get("scenario") == "dec21_12pm" for s in scenarios):
            continue
        carries_dec += 1
        if r["lat"] is None or r["lng"] is None:
            continue
        lat, lng = float(r["lat"]), float(r["lng"])
        alt_old, az_old = sun(dec_old, lat, lng)
        alt_new, az_new = sun(dec_fixed, lat, lng)
        bearing_shifts.append(abs(_angular_difference(az_old, az_new)))
        altitude_shifts.append(alt_old - alt_new)
        h = float(r["height_m"]) if r["height_m"] is not None else 9.0
        if alt_old > 0.5 and alt_new > 0.5:
            length_deltas.append(abs(h / math.tan(math.radians(alt_old))
                                     - h / math.tan(math.radians(alt_new))))

    def stat(values, fmt="{:.2f}"):
        if not values:
            return "n/a"
        s = sorted(values)
        return (f"min {fmt.format(s[0])}  median {fmt.format(s[len(s)//2])}  "
                f"max {fmt.format(s[-1])}")

    print(f"    reports carrying a December scenario: {carries_dec} / {len(rows)}")
    print(f"    shadow-bearing error:  {stat(bearing_shifts)} deg")
    print(f"    solar-altitude error:  {stat(altitude_shifts, '{:+.2f}')} deg")
    print(f"    shadow-length error:   {stat(length_deltas)} m")

    # ---------------------------------------------------------------- defect 3
    print("\n[2] FIXED COMPASS CONSTANT — one bearing served for every address")
    print("    (8-point compass, 45 deg buckets, matching bearingToCompass in the PDF)")
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

    def compass(deg):
        return dirs[round(deg / 45) % 8]

    for key in SCENARIOS:
        _, old_utc = instants(key)
        stored = RETIRED_DIRECTION_DEG[key]
        errors, flips = [], 0
        for r in rows:
            if r["lat"] is None or r["lng"] is None:
                continue
            _, az = sun(old_utc, float(r["lat"]), float(r["lng"]))
            errors.append(abs(_angular_difference(stored, az)))
            if compass(az) != compass(stored):
                flips += 1
        if not errors:
            continue
        s = sorted(errors)
        print(f"    {key:<12} stored {stored:>6} ({compass(stored)})  "
              f"median err {s[len(s)//2]:>6.2f}  max {s[-1]:>6.2f}  "
              f"DISPLAYED LABEL WRONG: {flips}/{len(errors)}")

    # ---------------------------------------------------------------- defect 5
    print("\n[3] SURFACE-CHANGE CLAIM — what evidence sits behind it")
    buckets = Counter()
    for r in rows:
        note, score = r["change_note"], r["change_score"]
        if note:
            buckets[f"no reading: {note}"] += 1
        elif score is None:
            buckets["no reading: null score, no note"] += 1
        elif float(score) == 0.0:
            buckets["no reading: legacy score exactly 0.0, no note"] += 1
        else:
            buckets[f"REAL READING: score {score}"] += 1
    for label, n in buckets.most_common():
        print(f"    {n:>5}  {label}")
    detected = sum(1 for r in rows if str(r["change_detected"]).lower() == "true")
    real = sum(n for k, n in buckets.items() if k.startswith("REAL"))
    print(f"    -> reports that ever DETECTED change: {detected}")
    print(f"    -> reports with any real reading:     {real}")
    print(f"    -> reports asserting a negative from no reading: {len(rows) - real - detected}")

    # ---------------------------------------------------------------- defect 6
    print("\n[4] PHYSICALLY IMPOSSIBLE SHADOW REACH (reach > ceiling x "
          f"{REACH_CEILING_TOLERANCE})")
    offenders, offending_rows, worst = set(), 0, []
    for r in rows:
        if r["lat"] is None or r["lng"] is None or r["height_m"] is None:
            continue
        lat, lng, h = float(r["lat"]), float(r["lng"]), float(r["height_m"])
        for s in (r["scenarios"] or []):
            key, reach = s.get("scenario"), s.get("shadow_length_m")
            if key not in SCENARIOS or reach is None:
                continue
            _, old_utc = instants(key)
            alt, _az = sun(old_utc, lat, lng)
            if alt <= 0.5:
                continue
            ceiling = h / math.tan(math.radians(alt))
            if float(reach) > ceiling * REACH_CEILING_TOLERANCE:
                offenders.add(str(r["id"]))
                offending_rows += 1
                worst.append((float(reach) / ceiling, key, float(reach), ceiling, h))
    print(f"    scenario-rows exceeding the ceiling: {offending_rows}")
    print(f"    reports affected:                    {len(offenders)} / {len(rows)}")
    for ratio, key, reach, ceiling, h in sorted(worst, reverse=True)[:5]:
        print(f"      ratio {ratio:>8.1f}  {key:<12} reach {reach:>8.1f} m  "
              f"ceiling {ceiling:>6.1f} m  height {h:.0f} m")

    print("\n" + "=" * 88)
    print("READ-ONLY: no UPDATE, INSERT or DELETE was issued. Repair is a separate,")
    print("separately authorised pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
