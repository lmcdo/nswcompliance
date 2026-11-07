"""Scratchpad: score for the RANGE design (borderline lots show a range and a lean instead of "can't tell").
Usage: python -I lmr_area_score2.py [results.json]
Three honest measures, each printed with its numbers:
  1. YES/NO answers: share that match the independent router's side of the limit; wrong "yes" and wrong "no" counted separately.
  2. RANGE VALIDITY: for every lot with a stated range (yes, no, borderline), is the router's walk inside [low, high]?
     (the range is a claim: "the true walk is between these"; this measures how often that claim holds)
  3. BORDERLINE: how many, and does the lean (share of range inside the limit >= 50%) match the router's side?
  Real "can't tell" (a measurement did not come back) is reported on its own: it is a failure, not an answer.
Pass: yes/no match >= 90% with 0 opposite; range validity >= 90%; real can't-tell <= 5%."""
# prior-art-checked: 2026-11-07. A grep of scripts/ and services/ for station entrance, walking surface, valhalla and gtfs finds no
# existing builder or test of this data; this script is part of the low-and-mid-rise area-check data pipeline
# (see ~/.claude/plans/ce-NEXT-PROMPT-2026-11-07b-lmr-area-check-build.md). Working files go to data/lmr_area_work/ (not committed).
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__import__("os").environ.get("LMR_WORK", REPO / "data" / "lmr_area_work"))  # working folder, not committed
HERE.mkdir(parents=True, exist_ok=True)
R = json.loads((HERE / (sys.argv[1] if len(sys.argv) > 1 else "test_results.json")).read_text())["lots"]
LIMIT = json.loads((REPO / "data" / "law" / "housing_sepp_lmr_facts.json").read_text(encoding="utf-8"))["facts"]["lmr_outer_distance"]["value"]  # the law's walking limit, read from the saved law


def side(w):
    return "inside" if w <= LIMIT else "outside"


def report(rows, label):
    n = len(rows)
    yn = [r for r in rows if r["fix"] in ("yes", "no")]
    ok = [r for r in yn if (r["fix"] == "yes") == (r["judge_walk"] is not None and r["judge_walk"] <= LIMIT) or r["fix_code"] in ("chapter5", "beyond_straight_line") and r["fix"] == r["judge"]]
    wy = [r for r in yn if r["fix"] == "yes" and r["judge"] == "no"]
    wn = [r for r in yn if r["fix"] == "no" and r["judge"] == "yes"]
    bd = [r for r in rows if r["fix"] == "borderline"]
    ct = [r for r in rows if r["fix"] == "cant_tell"]
    ranged = [r for r in rows if r.get("fix_low") is not None and r["judge_walk"] is not None]
    inrange = [r for r in ranged if r["fix_low"] <= r["judge_walk"] <= r["fix_high"]]
    lean_ok = [r for r in bd if r["judge_walk"] is not None and r["fix_lean"] == side(r["judge_walk"])]
    pct = lambda a, b: 100 * a / b if b else 0.0
    agree = [r for r in yn if r["fix"] == r["judge"]]
    print(f"[{label}] lots {n}: yes/no {len(yn)} (match router {len(agree)}/{len(yn)} = {pct(len(agree), len(yn)):.0f}%, wrong-yes {len(wy)}, wrong-no {len(wn)})"
          f" | borderline {len(bd)} (lean matches router {len(lean_ok)}/{len(bd)}) | real can't-tell {len(ct)} ({pct(len(ct), n):.0f}%)")
    print(f"      range validity: router's walk inside our range for {len(inrange)}/{len(ranged)} lots = {pct(len(inrange), len(ranged)):.0f}%"
          f" | median range width {sorted(r['fix_high'] - r['fix_low'] for r in ranged)[len(ranged)//2] if ranged else None} m")
    passed = pct(len(agree), len(yn)) >= 90 and len(wy) + len(wn) == 0 and pct(len(inrange), len(ranged)) >= 90 and pct(len(ct), n) <= 5
    print("      =>", "PASS" if passed else "FAIL")
    report.last_passed = passed
    return wy, wn, [r for r in ranged if r not in inrange], [r for r in bd if r not in lean_ok and r["judge_walk"] is not None]


wy, wn, outside, badlean = report(R, "ALL")
all_passed = report.last_passed
report([r for r in R if r.get("fix_extra_m")], "stations with unmapped entrance")
report([r for r in R if r["fix_code"] not in ("chapter5", "beyond_straight_line")], "walk-decided lots only")
print("--- break-it versions (each must FAIL the yes/no match) ---")
weak_controls = []
for name, f in (("always yes", lambda r: "yes"), ("always no", lambda r: "no")):
    ag = sum(1 for r in R if f(r) == r["judge"])
    if 100 * ag / len(R) >= 90:
        weak_controls.append(name)
    print(f"{name:<12} match router {ag}/{len(R)} = {100 * ag / len(R):.0f}%  => {'FAIL (good)' if 100 * ag / len(R) < 90 else 'PASS (test too weak)'}")
print("--- lots a person should read: router walk OUTSIDE our stated range ---")
for r in outside:
    print(r["address"], "|", r["anchor"], "| our range", r["fix_low"], "-", r["fix_high"], "| router", round(r["judge_walk"]), "| answer", r["fix"])
print("--- borderline lots whose lean points the wrong side ---")
for r in badlean:
    print(r["address"], "| range", r["fix_low"], "-", r["fix_high"], "| lean", r["fix_lean"], "| router", round(r["judge_walk"]))

# A failed accuracy result or a break-it control that passes must fail the pipeline step, not just print FAIL.
sys.exit(0 if all_passed and not weak_controls else 1)
