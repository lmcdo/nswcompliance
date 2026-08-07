#!/usr/bin/env python3
# prior-art-checked: this IS the prior art — it began as
# repair_shadow_impossible_reach.py (PR #883) and is renamed and generalised
# here rather than copied, so both authorized passes share ONE proven guard
# chain. No parallel repair surface exists: sibling scripts either measure
# (measure_shadow_calibration_damage.py, read-only) or repair other corpora
# (dcp_setback_controls).
"""AUTHORIZED REPAIR of stored shadow reports. Two passes, one guard chain.

    --pass impossible-reach   the 19 reports whose stored reach exceeded the
                              physical ceiling. EXECUTED 2026-08-07 (PR #883).
                              Now idempotent: re-running selects zero.

    --pass december-dst       the 519 reports whose December scenario was cast
                              at 13:00 AEDT while labelled 12:00, and whose
                              Direction column served the retired constant
                              183.0. AUTHORIZED 2026-08-07.

WHAT REGENERATION TOUCHES — read before running
-----------------------------------------------
Regeneration is whole-report, not field-surgical: there is no way to recompute
one scenario without leaving a row half-written by two code generations. Every
run recomputes all five scenarios, the north proxy, adg_compliant,
worst_case_scenario and confidence, through the pipeline's OWN functions:

    northern_neighbour_proxy(lot) -> model_all_scenarios(proxy, height)
                                  -> _build_scenario_list(...)
                                  -> _adg_compliant / _worst_case

PRESERVED VERBATIM: the Sentinel-2 surface-change fields
(construction_change_score / _detected / _note, s2_latest_acquisition). Those
are a network measurement with a different answer on every run, they are a
separate defect already fixed at render time, and re-running them was not
authorized. The dry run ASSERTS they are unchanged and aborts if not.

INPUTS ARE THE STORED ONES. Lot polygon and height come from the stored row,
not a fresh Planning Portal fetch — that isolates the change to the
computation and keeps the run reproducible; re-fetching could silently
substitute a different parcel.

GUARDS — none skippable, at any scale
-------------------------------------
1. BACKUP first: full pre-state outputs + confidence + server-side
   md5(outputs::text), asserted to cover EVERY row in the write set.
2. Selection re-derived live and checked against the measured count; a drifted
   selection refuses to --execute.
3. PREDICT the complete post-state for every row, persist it, and print a
   blast-radius breakdown BEFORE writing.
4. Per-row guarded UPDATE: WHERE id AND product='shadow' AND
   md5(outputs::text) = <pre-state md5>. rowcount != 1 rolls back the batch.
5. BATCHED: each batch is its own transaction, so nothing holds locks across
   the corpus. Partial completion is resumable — selection excludes
   rows already carrying a repair tag, so a re-run picks up the remainder.
6. VERIFY: re-read and deep-compare against the prediction, JSON-normalised
   (shapely emits coordinate tuples; Postgres returns lists).
7. IDEMPOTENCE: a second run selects zero rows.
8. ROLLBACK: --rollback restores from the backup, guarded on the post-repair
   md5 so it cannot clobber later state.

Usage:
    DATABASE_URL=... python scripts/repair_shadow_reports.py \
        --pass december-dst --backup-dir <dir>              # dry run + report
    ... --execute [--batch-size 50]                          # guarded write
    ... --verify-only                                        # re-verify + arm
    ... --rollback <backup.json>                             # restore
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import sys
from collections import Counter
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

SCENARIOS = {"jun21_9am": (6, 21, 9), "jun21_12pm": (6, 21, 12),
             "jun21_3pm": (6, 21, 15), "sep21_12pm": (9, 21, 12),
             "dec21_12pm": (12, 21, 12)}
# The UTC instant each STORED scenario was actually cast at (pre-fix code) —
# used only to evaluate predicates against the stored values.
OLD_HOUR_UTC = {"jun21_9am": 23, "jun21_12pm": 2, "jun21_3pm": 5,
                "sep21_12pm": 2, "dec21_12pm": 2}
SCENARIO_YEAR = 2025
REACH_CEILING_TOLERANCE = 1.25
DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

# The impossible-reach corpus measured 2026-08-07 and repaired in PR #883.
IMPOSSIBLE_REACH_IDS = {
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

# Sentinel-2 fields the repair must NOT touch.
PRESERVED_KEYS = ("construction_change_score", "construction_change_detected",
                  "construction_change_note", "s2_latest_acquisition")


def _old_instant(key: str) -> datetime:
    if key == "jun21_9am":
        return datetime(SCENARIO_YEAR, 6, 20, 23, 0, tzinfo=timezone.utc)
    month, day, _ = SCENARIOS[key]
    return datetime(SCENARIO_YEAR, month, day, OLD_HOUR_UTC[key], 0,
                    tzinfo=timezone.utc)


def _sun_altitude_deg(dt: datetime, lat: float, lng: float) -> float:
    return math.degrees(get_position(dt, lng, lat)["altitude"])  # lng FIRST


def _compass(deg) -> str:
    """The 8-point letter the PDF Direction column actually prints."""
    return "—" if deg is None else DIRS[round(float(deg) / 45) % 8]


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
        # Nullable BY DESIGN: a repaired row stores shadow_length_m = null for
        # every unavailable scenario, so a sweep over a partly-repaired corpus
        # meets None routinely. Narrow at the point of use.
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


# --- pass definitions ------------------------------------------------------

def _select_impossible_reach(row: dict) -> bool:
    return bool(_offending_scenarios(row))


def _select_december_dst(row: dict) -> bool:
    """Rows still carrying the pre-fix December scenario.

    A row regenerated by EITHER pass carries `outputs.repair`, so this
    predicate is self-excluding: the run is resumable and idempotent by
    construction rather than by bookkeeping.
    """
    outputs = row["outputs"] or {}
    if outputs.get("repair"):
        return False
    return any(s.get("scenario") == "dec21_12pm"
               for s in (outputs.get("scenarios") or []))


PASSES = {
    "impossible-reach": {
        "select": _select_impossible_reach,
        "expected_count": 0,   # executed in PR #883; the live corpus is clean
        "expected_ids": IMPOSSIBLE_REACH_IDS,
        "tag": "shadow-reach-regeneration-2026-08-07",
        "reason": ("stored shadow_length_m came from the retired "
                   "centroid-to-all-vertices metric and exceeded the physical "
                   "ceiling; regenerated through the current pipeline"),
    },
    "december-dst": {
        "select": _select_december_dst,
        "expected_count": 519,
        "expected_ids": None,
        "tag": "shadow-december-dst-regeneration-2026-08-07",
        "reason": ("the December scenario was cast at 13:00 AEDT while "
                   "labelled 12:00, and the Direction column served the "
                   "retired constant 183.0; regenerated through the current "
                   "pipeline, which derives each scenario instant from the "
                   "IANA database and computes the bearing per address"),
    },
}


def _regenerate_outputs(row: dict, pass_cfg: dict) -> dict:
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
        "tag": pass_cfg["tag"],
        "reason": pass_cfg["reason"],
        "regenerated": ["scenarios", "north_proxy_polygon", "adg_compliant",
                        "worst_case_scenario"],
        "preserved": ["lot_polygon", "height_m", "construction_change_*"],
    }
    return outputs


def _regeneratable(row: dict) -> str | None:
    """None if the row can be regenerated, else the reason it cannot.

    Reported, never guessed: a row without geometry is excluded from the write
    set and named in the run output, rather than silently skipped.
    """
    if row["lat"] is None or row["lng"] is None:
        return "no coordinates"
    if row["height_m"] is None:
        return "no height_m"
    if not (row["outputs"] or {}).get("lot_polygon"):
        return "no stored lot_polygon"
    return None


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


def _json_norm(obj):
    """Normalise for comparison across the jsonb boundary.

    shapely's `mapping()` yields coordinate TUPLES and Postgres returns JSON
    arrays as LISTS, so a raw `==` between the in-memory prediction and the
    re-read row is always False even when the data is identical. A check that
    can only fail is worth as little as one that can only pass.
    """
    return json.loads(json.dumps(obj, default=str))


def _blast_radius(rows_before_after: list[tuple]) -> dict:
    """Aggregate what a customer would actually SEE change.

    'Numbers move' and 'a verdict flips' are counted separately on purpose.
    """
    agg = {
        "reports": len(rows_before_after),
        "adg": Counter(), "confidence": Counter(), "worst_case": 0,
        "status_gained_unavailable": 0, "compass_any": 0,
        "compass_by_scenario": Counter(), "preserved_violations": [],
        "verdict_changed": 0, "numbers_only": 0, "identical": 0,
        "reach_deltas": [], "overlap_pct_deltas": [], "adg_examples": {},
    }
    for row, new_out, new_conf in rows_before_after:
        old_out, old_conf = row["outputs"], row["confidence"]
        changed_verdict = False

        old_adg, new_adg = old_out.get("adg_compliant"), new_out["adg_compliant"]
        if old_adg != new_adg:
            key = f"{old_adg} -> {new_adg}"
            agg["adg"][key] += 1
            agg["adg_examples"].setdefault(key, []).append(
                (row["id"][:8], row["address"][:44]))
            changed_verdict = True
        if old_conf != new_conf:
            agg["confidence"][f"{old_conf} -> {new_conf}"] += 1
            changed_verdict = True
        if old_out.get("worst_case_scenario") != new_out["worst_case_scenario"]:
            agg["worst_case"] += 1
            changed_verdict = True

        for k in PRESERVED_KEYS:
            if _json_norm(old_out.get(k)) != _json_norm(new_out.get(k)):
                agg["preserved_violations"].append((row["id"], k))

        old_by = {s.get("scenario"): s for s in (old_out.get("scenarios") or [])}
        letter_changed = False
        for s in new_out["scenarios"]:
            o = old_by.get(s["scenario"], {})
            if (o.get("status") != "unavailable"
                    and s.get("status") == "unavailable"):
                agg["status_gained_unavailable"] += 1
                changed_verdict = True
            if _compass(o.get("shadow_direction_deg")) != _compass(
                    s.get("shadow_direction_deg")):
                agg["compass_by_scenario"][s["scenario"]] += 1
                letter_changed = True
            if (o.get("shadow_length_m") is not None
                    and s.get("shadow_length_m") is not None):
                agg["reach_deltas"].append(
                    abs(float(s["shadow_length_m"]) - float(o["shadow_length_m"])))
            if (o.get("shadow_overlap_fraction") is not None
                    and s.get("shadow_overlap_fraction") is not None):
                agg["overlap_pct_deltas"].append(abs(
                    round(float(s["shadow_overlap_fraction"]) * 100)
                    - round(float(o["shadow_overlap_fraction"]) * 100)))
        if letter_changed:
            agg["compass_any"] += 1
            changed_verdict = True

        if changed_verdict:
            agg["verdict_changed"] += 1
        elif _json_norm(old_out.get("scenarios")) != _json_norm(new_out["scenarios"]):
            agg["numbers_only"] += 1
        else:
            agg["identical"] += 1
    return agg


def _stat(v, f="{:.2f}"):
    if not v:
        return "n/a"
    s = sorted(v)
    return (f"min {f.format(s[0])}  median {f.format(s[len(s)//2])}  "
            f"p95 {f.format(s[int(len(s)*0.95)])}  max {f.format(s[-1])}")


def _print_blast_radius(agg: dict, pass_name: str) -> None:
    print("\n" + "=" * 78)
    print(f"BLAST RADIUS — {pass_name}  ({agg['reports']} reports in the write set)")
    print("=" * 78)
    print(f"\nReports changing a CUSTOMER-VISIBLE VERDICT : {agg['verdict_changed']}")
    print(f"Reports where only NUMBERS move            : {agg['numbers_only']}")
    print(f"Reports identical after regeneration       : {agg['identical']}")

    print("\n-- which verdict --")
    print(f"  ADG solar-access verdict changed : {sum(agg['adg'].values())}")
    for k, n in agg["adg"].most_common():
        print(f"      {n:>5}  adg_compliant {k}")
        for rid, addr in agg["adg_examples"].get(k, [])[:3]:
            print(f"             e.g. {rid}  {addr}")
    print(f"  Confidence changed               : {sum(agg['confidence'].values())}")
    for k, n in agg["confidence"].most_common():
        print(f"      {n:>5}  confidence {k}")
    print(f"  Worst-case scenario changed      : {agg['worst_case']}")
    print(f"  Scenario became 'not assessed'   : {agg['status_gained_unavailable']}")
    print(f"  Compass LETTER changed (reports) : {agg['compass_any']}")
    for k, n in agg["compass_by_scenario"].most_common():
        print(f"      {n:>5}  {k}")

    print("\n-- magnitude of the numbers that move --")
    print(f"  reach delta (m)     : {_stat(agg['reach_deltas'])}")
    print(f"  coverage delta (pp) : {_stat(agg['overlap_pct_deltas'], '{:.0f}')}")

    if agg["preserved_violations"]:
        print(f"\n*** PRESERVED-FIELD VIOLATIONS: {len(agg['preserved_violations'])}"
              f" — Sentinel-2 fields must not change. "
              f"First few: {agg['preserved_violations'][:5]}")
    else:
        print("\n  Sentinel-2 surface-change fields: UNCHANGED on every row (asserted)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass", dest="pass_name", default="impossible-reach",
                    choices=sorted(PASSES), help="which repair pass to run")
    ap.add_argument("--backup-dir", help="directory for backup + prediction files")
    ap.add_argument("--execute", action="store_true",
                    help="perform the guarded write (default: dry run)")
    ap.add_argument("--batch-size", type=int, default=50,
                    help="rows per transaction when writing (default 50)")
    ap.add_argument("--rollback", metavar="BACKUP_JSON",
                    help="restore outputs from a backup file and exit")
    ap.add_argument("--verify-only", action="store_true",
                    help="compare live rows against an existing prediction file "
                         "and arm the backup with post-repair hashes")
    args = ap.parse_args()

    pass_cfg = PASSES[args.pass_name]
    stamp = "2026-08-07"
    slug = args.pass_name.replace("-", "_")

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
                conn.close()
                sys.exit(f"ROLLBACK ABORTED at {b['id']}: current state does not "
                         f"match the recorded post-repair hash "
                         f"(rowcount={cur.rowcount}). Nothing committed.")
            restored += 1
        conn.commit()
        conn.close()
        print(f"ROLLBACK COMPLETE: {restored} rows restored.")
        return 0

    if not args.backup_dir:
        sys.exit("--backup-dir is required")
    os.makedirs(args.backup_dir, exist_ok=True)
    backup_path = os.path.join(args.backup_dir, f"shadow_{slug}_backup_{stamp}.json")
    pred_path = os.path.join(args.backup_dir, f"shadow_{slug}_predicted_{stamp}.json")

    # ------------------------------------------------------------ verify-only
    if args.verify_only:
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
            sys.exit(f"VERIFY FAILED: rows absent: {sorted(missing)[:10]}")
        mismatches = [
            rid for rid, pred in predictions.items()
            if _json_norm(after[rid]["outputs"]) != _json_norm(pred["outputs"])
            or after[rid]["confidence"] != pred["confidence"]]
        if mismatches:
            sys.exit(f"VERIFY FAILED for {len(mismatches)} rows, e.g. "
                     f"{mismatches[:5]}. Backup at {backup_path}.")
        for b in backup["rows"]:
            if b["id"] in after:
                b["post_repair_md5"] = after[b["id"]]["outputs_md5"]
        backup["guard"] = ("pre-repair outputs + md5; post_repair_md5 armed by "
                           "--verify-only")
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(backup, f, indent=1, default=str)
        print(f"MATCHED: all {len(predictions)} rows equal the prediction "
              f"exactly (JSON-normalised).")
        print(f"ROLLBACK ARMED -> {backup_path}")
        return 0

    # -------------------------------------------------------- guard 2: select
    conn, cur = _connect(readonly=True)
    corpus = _fetch_corpus(cur)
    conn.close()

    selected = [r for r in corpus if pass_cfg["select"](r)]
    if not selected:
        print(f"NO ROWS SELECTED [{args.pass_name}]: zero of "
              f"{len(corpus)} rows match this pass — nothing written.")
        return 0

    blocked = [(r, why) for r in selected for why in [_regeneratable(r)] if why]
    writable = [r for r in selected if _regeneratable(r) is None]
    print(f"CORPUS {len(corpus)} shadow reports")
    print(f"SELECTED [{args.pass_name}]: {len(selected)}  "
          f"(expected {pass_cfg['expected_count']})")
    if blocked:
        print(f"CANNOT REGENERATE: {len(blocked)} — reported, never guessed:")
        for r, why in blocked[:20]:
            print(f"    {r['id'][:8]}  {why:<22} {r['address'][:44]}")
    if pass_cfg["expected_ids"] is not None and \
            {r["id"] for r in selected} != pass_cfg["expected_ids"]:
        sys.exit("ABORTED: selection drifted from the measured id set.")
    if len(selected) != pass_cfg["expected_count"]:
        print(f"\n*** SELECTION COUNT DIFFERS FROM THE MEASURED EXPECTATION "
              f"({len(selected)} vs {pass_cfg['expected_count']}) — confirm "
              f"before executing.")
        if args.execute:
            sys.exit("Refusing to --execute on a drifted selection. Re-measure.")

    # ------------------------------------------------------- guard 1: backup
    backup_rows = [{"id": r["id"], "address": r["address"],
                    "run_date": r["run_date"], "confidence": r["confidence"],
                    "outputs": r["outputs"], "pre_md5": r["outputs_md5"]}
                   for r in writable]
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump({"taken": datetime.now(timezone.utc).isoformat(),
                   "pass": args.pass_name,
                   "guard": "pre-repair full outputs + server-side md5",
                   "rows": backup_rows}, f, indent=1, default=str)
    if {r["id"] for r in backup_rows} != {r["id"] for r in writable}:
        sys.exit("BACKUP DOES NOT COVER THE WRITE SET — aborting before any write")
    print(f"BACKUP ({len(backup_rows)} full rows) -> {backup_path}")

    # ------------------------------------------------------ guard 3: predict
    predictions, before_after = {}, []
    for i, row in enumerate(writable, 1):
        new_outputs = _regenerate_outputs(row, pass_cfg)
        new_conf = _confidence_for(new_outputs, row)
        predictions[row["id"]] = {"pre_md5": row["outputs_md5"],
                                  "outputs": new_outputs,
                                  "confidence": new_conf}
        before_after.append((row, new_outputs, new_conf))
        if i % 50 == 0:
            print(f"  ... predicted {i}/{len(writable)}", flush=True)
    with open(pred_path, "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=1, default=str)
    print(f"PREDICTED post-state -> {pred_path}")

    agg = _blast_radius(before_after)
    _print_blast_radius(agg, args.pass_name)

    if agg["preserved_violations"]:
        sys.exit("\nABORTING: the repair would alter preserved Sentinel-2 "
                 "fields. Nothing written.")

    if not args.execute:
        print(f"\nDRY RUN — nothing written. Re-run with --execute "
              f"(--batch-size {args.batch_size}) to repair.")
        return 0

    # ------------------------------------- guards 4+5: batched guarded write
    written = 0
    batches = [writable[i:i + args.batch_size]
               for i in range(0, len(writable), args.batch_size)]
    for bi, batch in enumerate(batches, 1):
        conn, cur = _connect(readonly=False)
        try:
            for row in batch:
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
                    sys.exit(
                        f"WRITE ABORTED in batch {bi} at {row['id']}: pre-state "
                        f"hash did not match (rowcount={cur.rowcount}). This "
                        f"batch rolled back; {written} rows from earlier batches "
                        f"are committed and remain in place — re-running selects "
                        f"only the "
                        f"remainder.")
            conn.commit()
        finally:
            conn.close()
        written += len(batch)
        print(f"  batch {bi}/{len(batches)} committed  "
              f"({written}/{len(writable)})", flush=True)
    print(f"WROTE {written} rows across {len(batches)} batches; all pre-state "
          f"guards held.")

    # ----------------------------------------------------- guard 6: verify
    conn, cur = _connect(readonly=True)
    cur.execute(
        """SELECT id::text AS id, outputs, confidence,
                  md5(outputs::text) AS outputs_md5
           FROM property_reports
           WHERE product = 'shadow' AND id::text = ANY(%s)""",
        (sorted(predictions.keys()),))
    after = {r["id"]: r for r in cur.fetchall()}
    conn.close()
    mismatches = [
        rid for rid, pred in predictions.items()
        if _json_norm(after.get(rid, {}).get("outputs")) != _json_norm(pred["outputs"])
        or after.get(rid, {}).get("confidence") != pred["confidence"]]
    if mismatches:
        sys.exit(f"VERIFY FAILED for {len(mismatches)} rows, e.g. "
                 f"{mismatches[:5]}. Backup at {backup_path} — use --rollback.")
    for b in backup_rows:
        b["post_repair_md5"] = after[b["id"]]["outputs_md5"]
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump({"taken": datetime.now(timezone.utc).isoformat(),
                   "pass": args.pass_name,
                   "guard": "pre-repair outputs + md5; post_repair_md5 added "
                            "after verify",
                   "rows": backup_rows}, f, indent=1, default=str)
    print(f"MATCHED: all {len(predictions)} rows equal the prediction exactly.")
    print("Rollback armed. Re-run without --execute to confirm idempotence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
