#!/usr/bin/env python3
# prior-art-checked: same four sweeps as sample_structure_label_set.py
# (2026-08-08, origin/main af7982a8). No recall, precision or IoU measurement
# exists anywhere in the repo: `git grep -riE "recall|precision|iou|
# intersection.over.union"` over scripts/ services/ tests/ returns only
# unrelated prose. scripts/measure_granny_confidence_states.py measures the
# STATE MACHINE (how many rows are high/medium/low), never detector accuracy.
"""Compare human structure labels against the detector. Recall and precision.

THE PASS MARK IS COMMITTED IN THIS FILE, BEFORE ANY LABEL EXISTS.
================================================================
This is the whole point. The shadow calibration worked because 0.50 degrees
was written down before the first run, so the result could not be
renegotiated once it arrived. The granny-flat "13 of 16 confirmations" failed
because the number was interpreted after the fact and turned out to contain
zero human input.

So: the thresholds below are set now, while nobody knows the answer. If the
detector misses the mark, the honest response is to say so and change the
product's wording -- not to move the line.

    RECALL_FLOOR      = 0.70   of the structures a human can see, the detector
                               must find at least 70%
    PRECISION_FLOOR   = 0.60   of what the detector reports, at least 60% must
                               correspond to something a human can see
    IOU_MATCH         = 0.30   two boxes are "the same structure" at 30%
                               overlap; deliberately loose, because the
                               question is "did it find the shed", not "did it
                               trace the shed's outline"
    MIN_LABELLED      = 40     below this the confidence interval is too wide
                               for any verdict; the run reports UNKNOWABLE

WHY A LOOSE IOU IS THE HONEST CHOICE
------------------------------------
A strict IoU would measure segmentation quality, which is not what the product
claims. The product claims to notice that a secondary structure exists. A box
that covers a third of the shed has noticed the shed. Setting the bar at 0.30
and saying so is more honest than setting it at 0.50 and quietly reporting a
worse number as if it were the same measurement.

WHAT THIS CANNOT TELL YOU
-------------------------
* Nothing about lots outside the sample, which is 4 councils and one lot-size
  band. Recall on rural or industrial land is not measured and must not be
  inferred.
* Nothing about structures invisible from above. A human reading imagery is
  the ceiling here, not the truth -- a shed under a tree is missed by both and
  counts as agreement.
* Nothing about whether a detected structure is legally a secondary dwelling.
  That is the eligibility question, which is separate and rule-based.

USAGE
    python scripts/measure_structure_detection_recall.py --sample-id gf-recall-001
    python scripts/measure_structure_detection_recall.py --sample-id ... --json out.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

import psycopg2
import psycopg2.extras

# ---- PRE-COMMITTED THRESHOLDS. Changing these after a run is the failure
# ---- this file exists to prevent. If they move, the commit that moves them
# ---- must say why, and the previous result stays on the record.
RECALL_FLOOR = 0.70
PRECISION_FLOOR = 0.60
IOU_MATCH = 0.30
MIN_LABELLED = 40


def iou(a: list[int], b: list[int]) -> float:
    """Intersection over union for two [x0,y0,x1,y1] pixel boxes."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    # Normalise in case a box was drawn right-to-left or bottom-to-top.
    ax0, ax1 = min(ax0, ax1), max(ax0, ax1)
    ay0, ay1 = min(ay0, ay1), max(ay0, ay1)
    bx0, bx1 = min(bx0, bx1), max(bx0, bx1)
    by0, by1 = min(by0, by1), max(by0, by1)

    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    if inter == 0:
        return 0.0
    area_a = (ax1 - ax0) * (ay1 - ay0)
    area_b = (bx1 - bx0) * (by1 - by0)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def match_boxes(truth: list[dict], pred: list[dict]) -> tuple[int, int, int]:
    """Greedy one-to-one matching. Returns (matched, missed, spurious).

    Greedy by descending overlap, and each predicted box may only claim one
    truth box. Without the one-to-one rule a single large prediction covering
    a whole yard would "find" every structure on it and recall would read 100%.
    """
    pairs = []
    for ti, t in enumerate(truth):
        for pi, p in enumerate(pred):
            score = iou(t["bbox_pixel"], p["bbox_pixel"])
            if score >= IOU_MATCH:
                pairs.append((score, ti, pi))
    pairs.sort(reverse=True)

    used_t: set[int] = set()
    used_p: set[int] = set()
    for _score, ti, pi in pairs:
        if ti in used_t or pi in used_p:
            continue
        used_t.add(ti)
        used_p.add(pi)

    matched = len(used_t)
    return matched, len(truth) - matched, len(pred) - len(used_p)


def _connect():
    host = os.environ.get("PGHOST") or os.environ.get("DB_HOST")
    if not host:
        sys.exit("No database credentials. Source the repo-root .env first.")
    return psycopg2.connect(
        host=host,
        port=os.environ.get("PGPORT", "5432"),
        user=os.environ.get("PGUSER") or os.environ.get("DB_USER"),
        password=os.environ.get("PGPASSWORD") or os.environ.get("DB_PASSWORD"),
        dbname=os.environ.get("PGDATABASE") or os.environ.get("DB_NAME", "postgres"),
        sslmode=os.environ.get("PGSSLMODE", "require"),
        connect_timeout=20,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample-id", default="gf-recall-001")
    ap.add_argument("--json", help="Write the full result to this path.")
    args = ap.parse_args()

    conn = _connect()
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        """
        SELECT status, count(*) AS n
        FROM structure_labels WHERE sample_id = %s GROUP BY status
        """,
        (args.sample_id,),
    )
    counts = {r["status"]: r["n"] for r in cur.fetchall()}
    labelled = counts.get("labelled", 0)

    print(f"=== structure detection recall: {args.sample_id} ===")
    print(f"  pending  {counts.get('pending', 0)}")
    print(f"  labelled {labelled}")
    print(f"  skipped  {counts.get('skipped', 0)}")
    print()
    print(f"  pass mark (committed before any label existed):")
    print(f"    recall    >= {RECALL_FLOOR:.2f}")
    print(f"    precision >= {PRECISION_FLOOR:.2f}")
    print(f"    iou match  = {IOU_MATCH:.2f}")
    print(f"    min sample = {MIN_LABELLED}")
    print()

    if labelled < MIN_LABELLED:
        # Three states, never two. Too little data is not a failure and is
        # certainly not a pass -- it is unknowable, and that is reportable.
        print(f"VERDICT: UNKNOWABLE -- {labelled} labelled rows, "
              f"{MIN_LABELLED} required.")
        print("Not a pass and not a fail. Label more tiles, then re-run.")
        return 0

    # Join on LOCATION, not on a tile hash.
    #
    # Measured 2026-08-08: the detector stores no tile hash, and no stored row
    # carries the aerial_tile identity block at all. An earlier version of this
    # script joined on outputs->>'tile_sha256'; that key does not exist, so it
    # would have matched nothing on every run and reported UNKNOWABLE forever
    # while appearing to work. Joining on rounded lat/lng is the honest
    # available key -- it is the same key nsw_imagery uses for its own tile
    # cache, so two runs at the same rounded coordinates fetch the same tile.
    #
    # What this join does NOT establish: that the human and the detector saw
    # identical PIXELS. The LPI "Best" mosaic can be refreshed between runs and
    # publishes no capture date. That limitation is reported in the output
    # rather than papered over.
    cur.execute(
        """
        SELECT sl.id, sl.address, sl.lat, sl.lng, sl.tile_sha256, sl.labels,
               gf.outputs AS detector
        FROM structure_labels sl
        LEFT JOIN LATERAL (
            SELECT outputs, created_at FROM granny_flat_reports g
            WHERE round((g.outputs->>'lat')::numeric, 6) = round(sl.lat::numeric, 6)
              AND round((g.outputs->>'lng')::numeric, 6) = round(sl.lng::numeric, 6)
            ORDER BY g.created_at DESC LIMIT 1
        ) gf ON TRUE
        WHERE sl.sample_id = %s AND sl.status = 'labelled'
        """,
        (args.sample_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    tot_matched = tot_missed = tot_spurious = 0
    unpaired = 0
    per_lot = []

    for r in rows:
        det = r["detector"]
        if not det:
            unpaired += 1
            continue
        # `or []` rather than a .get default: the key can be PRESENT with a
        # value of null, in which case the default is not used and iterating
        # would raise. A detector run that stored an explicit null is exactly
        # the "failed, not empty" case this project keeps mishandling, and it
        # must degrade to an empty list here rather than crash the whole run.
        truth = [t for t in (r["labels"] or []) if not t.get("is_main_dwelling")]
        pred = [
            p for p in (det.get("detected_structures") or [])
            if not p.get("is_main_dwelling")
        ]
        m, miss, spur = match_boxes(truth, pred)
        tot_matched += m
        tot_missed += miss
        tot_spurious += spur
        per_lot.append({
            "address": r["address"], "truth": len(truth), "pred": len(pred),
            "matched": m, "missed": miss, "spurious": spur,
        })

    if unpaired:
        print(f"  ! {unpaired} labelled lots have no detector run at the same "
              f"coordinates -- EXCLUDED from the numbers below rather than "
              f"matched against a different lot. Run the detector on these "
              f"before treating the result as covering the whole sample.")
    print("  ! Pixel equality is UNPROVEN: the detector records no tile hash, "
          "so this compares a human reading and a machine reading of the same "
          "LOCATION, not provably the same image.")

    truth_total = tot_matched + tot_missed
    pred_total = tot_matched + tot_spurious

    if truth_total == 0:
        print("VERDICT: UNKNOWABLE -- no secondary structures in the labelled "
              "set, so recall has no denominator.")
        return 0

    recall = tot_matched / truth_total
    precision = tot_matched / pred_total if pred_total else 0.0

    print(f"  lots compared      {len(per_lot)}")
    print(f"  structures (human) {truth_total}")
    print(f"  found              {tot_matched}")
    print(f"  MISSED             {tot_missed}")
    print(f"  spurious           {tot_spurious}")
    print()
    print(f"  RECALL    {recall:.3f}   (floor {RECALL_FLOOR:.2f})")
    print(f"  PRECISION {precision:.3f}   (floor {PRECISION_FLOOR:.2f})")
    print()

    passed = recall >= RECALL_FLOOR and precision >= PRECISION_FLOOR
    if passed:
        print("VERDICT: PASS against the pre-committed mark.")
        print("Wording earned: 'checked against human review of aerial imagery "
              f"on {len(per_lot)} lots; found {recall:.0%} of visible "
              "structures'. NOT 'accurate' and NOT 'verified'.")
    else:
        print("VERDICT: BELOW THE MARK.")
        print("The honest response is to state the measured figure on the "
              "product, not to move the threshold. A detector that finds "
              f"{recall:.0%} of structures is still useful if it says so.")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({
                "sample_id": args.sample_id,
                "thresholds": {
                    "recall_floor": RECALL_FLOOR,
                    "precision_floor": PRECISION_FLOOR,
                    "iou_match": IOU_MATCH,
                    "min_labelled": MIN_LABELLED,
                },
                "labelled": labelled,
                "lots_compared": len(per_lot),
                "unpaired_excluded": unpaired,
                "recall": recall,
                "precision": precision,
                "matched": tot_matched,
                "missed": tot_missed,
                "spurious": tot_spurious,
                "passed": passed,
                "per_lot": per_lot,
            }, fh, indent=2)
        print(f"\nwrote {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
