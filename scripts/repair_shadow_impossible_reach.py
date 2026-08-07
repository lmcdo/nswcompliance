#!/usr/bin/env python3
# prior-art-checked: sibling scripts either measure (measure_shadow_calibration_damage.py,
# read-only by design) or repair other corpora (dcp_setback_controls). None
# regenerates property_reports shadow rows. Same guard pattern as the DQ-40
# authorized repairs: backup -> predict -> guarded write -> verify -> idempotence.
"""AUTHORIZED REPAIR: regenerate the 19 stored shadow reports serving a
physically impossible reach. User-authorized 2026-08-07; every other stored
shadow report remains unauthorized and untouched.

WHAT WENT WRONG IN THE STORED ROWS
-----------------------------------
Not corrupt geometry — a RETIRED METRIC. The stored `shadow_length_m` on these
rows came from the old `shadow_length_m`, which measured from the lot centroid
to every shadow vertex INCLUDING the modelled building to the north. The
current `shadow_reach_m` clips the shadow to the lot and measures the
penetration from the lot's northern bound, so it is mathematically bounded by
the lot's own depth. That is why an 11.3 m lot stored a 1,779.5 m "reach".

Evidence the cause is the metric and not the data (measured 2026-08-07,
read-only, all 538 stored reports):
  * every offender was written between 2026-04-08 and 2026-04-16;
  * ZERO of the 485 reports written on 2026-04-17 or later offend;
  * the offenders' lots are SMALLER than the corpus median (35.1 m vs 40.6 m
    N-S span), and 86 non-offenders have lots over 100 m — so lot size does
    not predict the defect;
  * 15 of the 19 store a reach exceeding their own lot's N-S span, which the
    current metric cannot produce at all.

WHAT THIS SCRIPT DOES
---------------------
A genuine regeneration through the pipeline's OWN functions — not a
hand-written transform:

    northern_neighbour_proxy(lot)  ->  model_all_scenarios(proxy, height)
                                   ->  _build_scenario_list(...)
                                   ->  _adg_compliant / _worst_case

`_build_scenario_list` carries the fixed per-address bearing, the DST-correct
scenario instants and the physical-ceiling guard, so anything still impossible
after regeneration is emitted as typed-unavailable by the pipeline itself
rather than by this script.

INPUTS ARE THE STORED ONES, DELIBERATELY. The lot polygon and height come from
the stored row, not from a fresh NSW Planning Portal fetch. That isolates the
change to the metric and keeps the run reproducible; re-fetching could silently
substitute a different parcel and confound the repair.

SCOPE NOTE — READ THIS. Regenerating a report recomputes ALL FIVE scenarios;
there is no way to recompute reach alone without leaving a row half-written by
each code generation. These 19 therefore also receive corrected December
(daylight-saving) values as a consequence. The other 519 reports carrying the
December defect are NOT touched here and remain unauthorized.

NOT RE-RUN: the Sentinel-2 surface-change fields. Those are a network
measurement with a different result on every run, they are a separate defect,
and re-running them here was not authorized. They are preserved verbatim.

GUARDS — none skippable
-----------------------
1. BACKUP first: full rows + server-side md5(outputs::text), asserted to cover
   every expected id BEFORE any write.
2. The offender set is re-derived live and must EQUAL the measured 19; a
   drifted corpus aborts before writing.
3. PREDICT the complete post-state per row and persist it before writing.
4. Per-row guarded UPDATE: WHERE id AND product='shadow' AND
   md5(outputs::text) = <pre-state md5>. rowcount != 1 aborts the whole
   transaction.
5. VERIFY: re-read and deep-compare every row against the prediction.
6. IDEMPOTENCE: a second run re-derives zero offenders.
7. ROLLBACK: --rollback restores outputs from the backup, itself guarded on
   the post-repair md5 so it cannot clobber later state.

Usage:
    DATABASE_URL=... python scripts/repair_shadow_impossible_reach.py \
        --backup-dir <dir>            # dry run: backup + predict + report
    ... --execute                     # guarded write + verify
    ... --rollback <backup.json>      # restore from a backup file
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import sys
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from suncalc import get_position

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _REPO_ROOT)
# shadow_detector's intra-package fallback imports resolve bare, so services/
# must be importable too:
sys.path.insert(0, os.path.join(_REPO_ROOT, "services"))
from services.shadow_model import (  # noqa: E402
    model_all_scenarios, northern_neighbour_proxy,
)
from services.shadow_detector import (  # noqa: E402
    DEFAULT_HEIGHT_M, _adg_compliant, _build_scenario_list, _worst_case,
)

# The corpus measured 2026-08-07. The live re-derivation must equal this set
# exactly, or the corpus has drifted and the run aborts before writing.
EXPECTED_IDS = {
    "feeeac25-4c1a-4f15-94b4-1da4607ae254",
    "00000000-0000-0000-0000-000000000002",
    "7a399cee-f8f8-47ce-8772-cfca5d976189",
    "7418fb0c-adcc-4649-88cc-0e360a87fd18",
    "fd456cb2-2db2-4261-8b26-ee86674c8c39",
    "48b12484-c06d-4191-ab08-b6cfc93068bf",
    "fd0e401c-7998-46bd-b231-e73bac060391",
    "f25a338f-7db2-42d6-946c-f88ccc8d5dcf",
    "817b8969-7747-432b-a398-f191643c5bf4",
    "60a5aef8-7d8b-466d-b071-5a8fc4edda58",
    "e5d13ab4-d6e5-4b61-b1b7-b8e351ae9160",
    "e0190e04-15b7-49fe-9674-06f0b10e9e04",
    "2d1fab82-19a4-40d7-a935-25e8d4267188",
    "30faf63f-98f6-49af-b30c-62dc8d732f39",
    "550c0ea3-17b9-4780-b41b-6b4375886ec7",
    "30e4ebb5-6acd-4f80-b705-c25634b8d6da",
    "262722f1-f2e2-4053-9bc2-4c42a485cdd1",
    "a9e61262-6d48-4d63-9f39-b0af093464b9",
    "43da6a2f-9c34-4476-81b8-a887002708d7",
}

SCENARIOS = {"jun21_9am": (6, 21, 9), "jun21_12pm": (6, 21, 12),
             "jun21_3pm": (6, 21, 15), "sep21_12pm": (9, 21, 12),
             "dec21_12pm": (12, 21, 12)}
# The UTC instant each STORED scenario was actually cast at (pre-fix code) —
# used only to evaluate the offender predicate against the stored values.
OLD_HOUR_UTC = {"jun21_9am": 23, "jun21_12pm": 2, "jun21_3pm": 5,
                "sep21_12pm": 2, "dec21_12pm": 2}
SCENARIO_YEAR = 2025
REACH_CEILING_TOLERANCE = 1.25
REPAIR_TAG = "shadow-reach-regeneration-2026-08-07"


def _old_instant(key: str) -> datetime:
    if key == "jun21_9am":
        return datetime(SCENARIO_YEAR, 6, 20, 23, 0, tzinfo=timezone.utc)
    month, day, _ = SCENARIOS[key]
    return datetime(SCENARIO_YEAR, month, day, OLD_HOUR_UTC[key], 0,
                    tzinfo=timezone.utc)


def _sun_altitude_deg(dt: datetime, lat: float, lng: float) -> float:
    return math.degrees(get_position(dt, lng, lat)["altitude"])  # lng FIRST


def _offending_scenarios(row: dict) -> list[dict]:
    """[{key, reach, ceiling}] for STORED scenarios exceeding the ceiling.

    Identical predicate to scripts/measure_shadow_calibration_damage.py.
    """
    if row["lat"] is None or row["lng"] is None or row["height_m"] is None:
        return []
    lat, lng = float(row["lat"]), float(row["lng"])
    h = float(row["height_m"])
    out = []
    for s in (row["outputs"].get("scenarios") or []):
        key = s.get("scenario")
        raw_reach = s.get("shadow_length_m")
        # Nullable BY DESIGN, and increasingly so: a repaired row stores
        # shadow_length_m = null for every unavailable scenario, so a later
        # sweep over a partly-repaired corpus meets None routinely. Narrow at
        # the point of use rather than relying on a guard several lines up.
        reach_m = float(raw_reach) if raw_reach is not None else None
        if key not in SCENARIOS or reach_m is None:
            continue
        alt = _sun_altitude_deg(_old_instant(key), lat, lng)
        if alt <= 0.5:
            continue
        ceiling = h / math.tan(math.radians(alt))
        if reach_m > ceiling * REACH_CEILING_TOLERANCE:
            out.append({"key": key, "reach": reach_m,
                        "ceiling": round(ceiling, 1)})
    return out


def _regenerate_outputs(row: dict) -> dict:
    """The complete post-repair outputs, via the pipeline's own functions."""
    outputs = copy.deepcopy(row["outputs"])
    lot = outputs.get("lot_polygon")
    height_m = float(row["height_m"])
    lat, lng = float(row["lat"]), float(row["lng"])

    proxy = northern_neighbour_proxy(lot)
    shadow_map = model_all_scenarios(proxy, height_m)
    scenarios = _build_scenario_list(shadow_map, lot, lng, lat, height_m)

    outputs["north_proxy_polygon"] = proxy
    outputs["scenarios"] = scenarios
    outputs["adg_compliant"] = _adg_compliant(scenarios)
    outputs["worst_case_scenario"] = _worst_case(scenarios)
    # Provenance on the row itself, so the change is self-describing to anyone
    # reading the record later. Not rendered by any surface.
    outputs["repair"] = {
        "tag": REPAIR_TAG,
        "reason": "stored shadow_length_m came from the retired centroid-to-"
                  "all-vertices metric and exceeded the physical ceiling; "
                  "regenerated through the current pipeline",
        "regenerated": ["scenarios", "north_proxy_polygon", "adg_compliant",
                        "worst_case_scenario"],
        "preserved": ["lot_polygon", "height_m", "construction_change_*"],
    }
    return outputs


def _confidence_for(outputs: dict, row: dict) -> str:
    """The pipeline's own confidence rule (services/shadow_detector.py)."""
    lep_name = outputs.get("lep_name")
    height_m = float(row["height_m"])
    conf = ("medium" if height_m != DEFAULT_HEIGHT_M
            and lep_name != "Local Environmental Plan" else "low")
    if any(s.get("status") == "unavailable"
           for s in (outputs.get("scenarios") or [])):
        conf = "low"
    return conf


def _connect(readonly: bool):
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        sys.exit("DATABASE_URL is not set")
    conn = psycopg2.connect(dsn, connect_timeout=30)
    if readonly:
        conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SET statement_timeout = '30s'")
    return conn, cur


def _fetch_corpus(cur) -> list[dict]:
    cur.execute("""
        SELECT id::text AS id, address, lat, lng, run_date::text AS run_date,
               confidence, outputs,
               (outputs ->> 'height_m')::numeric AS height_m,
               md5(outputs::text) AS outputs_md5
        FROM property_reports
        WHERE product = 'shadow'
    """)
    return cur.fetchall()


def _fmt(v, spec="{:.1f}"):
    return "—" if v is None else spec.format(v)


def _json_norm(obj):
    """Normalise for comparison across the jsonb boundary.

    shapely's `mapping()` yields coordinate TUPLES, and Postgres returns JSON
    arrays as LISTS, so a raw `==` between the in-memory prediction and the
    re-read row is always False even when the data is identical. The first run
    of this script failed its own verify for exactly that reason — a check that
    can only fail is worth as little as one that can only pass, so compare both
    sides through the same JSON round-trip.
    """
    return json.loads(json.dumps(obj, default=str))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backup-dir", help="directory for backup + prediction files")
    ap.add_argument("--execute", action="store_true",
                    help="perform the guarded write (default: dry run)")
    ap.add_argument("--rollback", metavar="BACKUP_JSON",
                    help="restore outputs from a backup file and exit")
    ap.add_argument("--verify-only", action="store_true",
                    help="compare the live rows against an existing prediction "
                         "file and arm the backup with post-repair hashes; "
                         "no writes to property_reports")
    args = ap.parse_args()

    # ------------------------------------------------------- verify-only
    if args.verify_only:
        if not args.backup_dir:
            sys.exit("--backup-dir is required for --verify-only")
        stamp = "2026-08-07"
        pred_path = os.path.join(
            args.backup_dir, f"shadow_impossible_reach_predicted_{stamp}.json")
        backup_path = os.path.join(
            args.backup_dir, f"shadow_impossible_reach_backup_{stamp}.json")
        with open(pred_path, encoding="utf-8") as f:
            predictions = json.load(f)
        with open(backup_path, encoding="utf-8") as f:
            backup = json.load(f)

        conn, cur = _connect(readonly=True)
        cur.execute(
            """SELECT id::text AS id, outputs, confidence,
                      md5(outputs::text) AS outputs_md5
               FROM property_reports
               WHERE product = 'shadow' AND id::text = ANY(%s)""",
            (sorted(predictions.keys()),))
        after = {r["id"]: r for r in cur.fetchall()}
        conn.close()

        missing = set(predictions) - set(after)
        if missing:
            sys.exit(f"VERIFY FAILED: rows absent from the corpus: {sorted(missing)}")
        mismatches = [
            rid for rid, pred in predictions.items()
            if _json_norm(after[rid]["outputs"]) != _json_norm(pred["outputs"])
            or after[rid]["confidence"] != pred["confidence"]]
        if mismatches:
            sys.exit(f"VERIFY FAILED: live state differs from the prediction "
                     f"for {mismatches}. Backup at {backup_path}.")

        for b in backup["rows"]:
            b["post_repair_md5"] = after[b["id"]]["outputs_md5"]
        backup["guard"] = ("pre-repair full outputs + server-side md5; "
                           "post_repair_md5 armed by --verify-only")
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(backup, f, indent=1, default=str)
        print(f"VERIFIED: all {len(predictions)} rows match the prediction "
              f"exactly (JSON-normalised).")
        print(f"ROLLBACK ARMED: post-repair hashes written to {backup_path}")
        return 0

    # ---------------------------------------------------------------- rollback
    if args.rollback:
        with open(args.rollback, encoding="utf-8") as f:
            backup = json.load(f)
        conn, cur = _connect(readonly=False)
        restored = 0
        for b in backup["rows"]:
            cur.execute(
                """UPDATE property_reports
                   SET outputs = %s, confidence = %s
                   WHERE id = %s AND product = 'shadow'
                     AND md5(outputs::text) = %s""",
                (psycopg2.extras.Json(b["outputs"]), b["confidence"], b["id"],
                 b.get("post_repair_md5") or ""))
            if cur.rowcount != 1:
                conn.rollback()
                sys.exit(f"ROLLBACK ABORTED at {b['id']}: current state does "
                         f"not match the recorded post-repair hash "
                         f"(rowcount={cur.rowcount}). Nothing committed.")
            restored += 1
        conn.commit()
        conn.close()
        print(f"ROLLBACK COMPLETE: {restored} rows restored.")
        return 0

    if not args.backup_dir:
        sys.exit("--backup-dir is required for repair runs")
    os.makedirs(args.backup_dir, exist_ok=True)

    # ------------------------------------------------------ derive + guard 2
    conn, cur = _connect(readonly=True)
    corpus = _fetch_corpus(cur)
    conn.close()

    offenders = [(r, bad) for r in corpus for bad in [_offending_scenarios(r)] if bad]
    derived_ids = {r["id"] for r, _ in offenders}

    if not derived_ids:
        print("IDEMPOTENCE CONFIRMED: zero offending scenarios remain in the "
              "corpus — nothing to do, nothing written.")
        return 0
    if derived_ids != EXPECTED_IDS:
        sys.exit(f"ABORTED: offender set drifted from the measured set.\n"
                 f"  missing from live: {sorted(EXPECTED_IDS - derived_ids)}\n"
                 f"  unexpected extra:  {sorted(derived_ids - EXPECTED_IDS)}\n"
                 f"Nothing written. Re-measure before repairing.")
    print(f"OFFENDER SET VERIFIED: {len(derived_ids)} reports, "
          f"{sum(len(b) for _, b in offenders)} scenario-rows, "
          f"matching the set measured 2026-08-07.")

    # ------------------------------------------------------ guard 1: backup
    stamp = "2026-08-07"
    backup_path = os.path.join(
        args.backup_dir, f"shadow_impossible_reach_backup_{stamp}.json")
    backup_rows = [{"id": r["id"], "address": r["address"],
                    "run_date": r["run_date"], "confidence": r["confidence"],
                    "outputs": r["outputs"], "pre_md5": r["outputs_md5"]}
                   for r, _ in offenders]
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump({"taken": datetime.now(timezone.utc).isoformat(),
                   "guard": "pre-repair full outputs + server-side md5",
                   "rows": backup_rows}, f, indent=1, default=str)
    if {r["id"] for r in backup_rows} != EXPECTED_IDS:
        sys.exit("BACKUP DOES NOT COVER THE REPAIR SET — aborting before any write")
    print(f"BACKUP ({len(backup_rows)} full rows) -> {backup_path}")

    # ------------------------------------------------------ guard 3: predict
    predictions, report_lines = {}, []
    for row, bad in offenders:
        new_outputs = _regenerate_outputs(row)
        predictions[row["id"]] = {
            "pre_md5": row["outputs_md5"],
            "outputs": new_outputs,
            "confidence": _confidence_for(new_outputs, row),
        }
        old_by_key = {s["scenario"]: s for s in (row["outputs"].get("scenarios") or [])}
        report_lines.append((row, old_by_key, new_outputs))

    pred_path = os.path.join(
        args.backup_dir, f"shadow_impossible_reach_predicted_{stamp}.json")
    with open(pred_path, "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=1, default=str)
    print(f"PREDICTED post-state -> {pred_path}\n")

    # ------------------------------------------------------------ per-row report
    for row, old_by_key, new_outputs in report_lines:
        old_adg = row["outputs"].get("adg_compliant")
        new_adg = new_outputs["adg_compliant"]
        flag = "   *** ADG VERDICT CHANGES ***" if old_adg != new_adg else ""
        print(f"{row['id'][:8]}  {row['address'][:46]}{flag}")
        for s in new_outputs["scenarios"]:
            o = old_by_key.get(s["scenario"], {})
            print(f"    {s['scenario']:<12} reach {str(o.get('shadow_length_m')):>8} "
                  f"-> {_fmt(s['shadow_length_m']):>7}   "
                  f"dir {str(o.get('shadow_direction_deg')):>6} -> "
                  f"{_fmt(s.get('shadow_direction_deg'), '{:.0f}'):>4}   "
                  f"status {s.get('status')}")
        print(f"    adg_compliant {old_adg} -> {new_adg}    "
              f"worst_case {row['outputs'].get('worst_case_scenario')} -> "
              f"{new_outputs['worst_case_scenario']}    "
              f"confidence {row['confidence']} -> "
              f"{predictions[row['id']]['confidence']}\n")

    if not args.execute:
        print("DRY RUN — nothing written. Re-run with --execute to repair.")
        return 0

    # ------------------------------------------------------ guard 4: write
    conn, cur = _connect(readonly=False)
    for row, _bad in offenders:
        pred = predictions[row["id"]]
        cur.execute(
            """UPDATE property_reports
               SET outputs = %s, confidence = %s
               WHERE id = %s AND product = 'shadow'
                 AND md5(outputs::text) = %s""",
            (psycopg2.extras.Json(pred["outputs"]), pred["confidence"],
             row["id"], pred["pre_md5"]))
        if cur.rowcount != 1:
            conn.rollback()
            conn.close()
            sys.exit(f"WRITE ABORTED at {row['id']}: pre-state hash did not "
                     f"match (rowcount={cur.rowcount}). Transaction rolled "
                     f"back — nothing from this run is committed.")
    conn.commit()
    conn.close()
    print(f"WROTE {len(offenders)} rows in a single transaction; all "
          f"pre-state guards held.")

    # ----------------------------------------------------- guard 5: verify
    conn, cur = _connect(readonly=True)
    cur.execute(
        """SELECT id::text AS id, outputs, confidence,
                  md5(outputs::text) AS outputs_md5
           FROM property_reports
           WHERE product = 'shadow' AND id::text = ANY(%s)""",
        (sorted(EXPECTED_IDS),))
    after = {r["id"]: r for r in cur.fetchall()}
    conn.close()

    mismatches = [
        rid for rid, pred in predictions.items()
        if _json_norm(after.get(rid, {}).get("outputs")) != _json_norm(pred["outputs"])
        or after.get(rid, {}).get("confidence") != pred["confidence"]]
    if mismatches:
        sys.exit(f"VERIFY FAILED: post-state differs from prediction for "
                 f"{mismatches}. Backup at {backup_path} — use --rollback.")

    for b in backup_rows:
        b["post_repair_md5"] = after[b["id"]]["outputs_md5"]
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump({"taken": datetime.now(timezone.utc).isoformat(),
                   "guard": "pre-repair full outputs + server-side md5; "
                            "post_repair_md5 added after verify",
                   "rows": backup_rows}, f, indent=1, default=str)
    print(f"VERIFIED: all {len(predictions)} rows match the prediction exactly.")
    print("Rollback file updated with post-repair hashes.")
    print("Re-run WITHOUT --execute to confirm idempotence (expect zero offenders).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
