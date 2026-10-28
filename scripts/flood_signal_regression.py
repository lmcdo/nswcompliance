"""Re-score every saved customer flood check with the current flood_signal rule.

prior-art-checked: scripts/run_flood_calibration_2022.py samples NEW points from
Copernicus observed extents and runs the full pipeline to measure recall; this
re-scores the SAVED inputs of real customer checks (no API calls) to measure what
a rule change does to answers already served. Different population, different
question. The .env is found with scripts/dq_db.main_checkout.

Why: on 2026-10-28, 150 of 308 checked addresses got a flood signal whose only
positive source was Copernicus EMSR567, stored as an 86,349 km2 shape (the ingest
merged every layer in each ZIP, not only the flood extent). This is the measured
gate for changing the rule. It prints

    TOTAL=<n> EMS_ONLY_POSITIVE=<n> (any level decided by EMS alone) RAISED=<n> LOWERED=<n> UNCHANGED=<n>

RAISED/LOWERED compare against --baseline (a snapshot written by an earlier run
with --write-snapshot). A rule fix must print EMS_ONLY_POSITIVE=0 and RAISED=0.

--build-fixture writes tests/fixtures/flood_known_answers.json: real saved inputs
for addresses chosen by query (never typed), with the class each should get.
tests/test_flood_signal_known_answers.py runs them offline.

Usage:
    python scripts/flood_signal_regression.py --write-snapshot data/flood_signal_baseline.json
    python scripts/flood_signal_regression.py --baseline data/flood_signal_baseline.json
    python scripts/flood_signal_regression.py --build-fixture
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

WT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WT))
sys.path.insert(0, str(WT / "services"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
# A worktree has no .env of its own; dq_db finds the main checkout's (DQ-54).
from dq_db import main_checkout  # noqa: E402

ROOT = main_checkout()

from services.flood_truth import _compute_flood_signal  # noqa: E402

FIXTURE = WT / "tests" / "fixtures" / "flood_known_answers.json"
LEVEL = {"unavailable": 0, "none": 0, "low": 1, "moderate": 2, "elevated": 3}

# Latest saved inputs per address. run_date is a DATE, so same-day reruns tie;
# id breaks the tie so the chosen row never changes between runs. Rows without
# the EPI field carry no flood inputs (poisoned cache rows) and are skipped, as
# the cache read does. Calibration runs use persist=False; excluded regardless.
LATEST_SQL = """
    SELECT DISTINCT ON (address) address, outputs
    FROM property_reports
    WHERE product = 'flood' AND outputs ? 'epi_flood_class'
      AND address NOT ILIKE 'calibration %%'
    ORDER BY address, run_date DESC NULLS LAST, id DESC
"""


def water_pct(o: dict) -> float:
    """Same choice as the rule: JRC when it has a value, else DEA WOfS."""
    jrc = o.get("jrc_water_occurrence_pct") or 0.0
    return jrc if jrc > 0 else (o.get("dea_wofs_frequency_pct") or 0.0)


def positive_sources(o: dict) -> list[str]:
    """Every source that says 'flood' for these inputs, to report WHY a level was given."""
    out = []
    if o.get("epi_flood_class") not in (None, "none", ""):
        out.append("epi_overlay")
    if o.get("ses_in_flood_planning_area") is True:
        out.append("council_fpa")
    studies = o.get("flood_studies") or []
    if any((s.get("design") or {}).get("1pct") is not None for s in studies) \
            or o.get("hawkesbury_flood_level_100aep") is not None:
        out.append("flood_study_1pct")
    if o.get("ems_flood_detected") is True:
        out.append("ems")
    # The rule's own bands: under 15% is 'low' (a trace that cannot raise a
    # level alone); 15% and over is a source in its own right.
    pct = water_pct(o)
    if pct >= 15:
        out.append("water_history")
    elif pct > 0:
        out.append("water_trace")
    if o.get("bom_last_major_flood_date") is not None:
        out.append("bom_major_flood")
    return out


def ems_alone(positives: list[str]) -> bool:
    """EMS is the only positive, or EMS plus a water trace under 15% -- either
    way, EMS decided the level."""
    return "ems" in positives and set(positives) <= {"ems", "water_trace"}


def score(o: dict) -> dict:
    return {"signal": _compute_flood_signal(o), "positives": positive_sources(o)}


def _connect():
    import psycopg2
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=15)
    conn.cursor().execute("SET statement_timeout = 30000")
    return conn


def load_latest() -> list[tuple[str, dict]]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(LATEST_SQL)
        return cur.fetchall()
    finally:
        conn.close()


def run(baseline: Path | None, snapshot: Path | None) -> int:
    # With --baseline, re-score the SNAPSHOT's own inputs, so RAISED/LOWERED
    # measure the rule change alone, never inputs re-saved since the snapshot.
    before = json.loads(baseline.read_text(encoding="utf-8")) if baseline else None
    rows = [(a, r["inputs"]) for a, r in before.items()] if before else load_latest()
    results = {}
    for i, (address, o) in enumerate(rows, 1):
        results[address] = {**score(o), "inputs": o}
        if i % 50 == 0 or i == len(rows):
            print(f"DONE {i}/{len(rows)}", flush=True)

    # Any level at all (low included) decided by EMS alone counts.
    ems_only = [a for a, r in results.items() if LEVEL[r["signal"]] >= 1 and ems_alone(r["positives"])]
    counts: dict[str, int] = {}
    for r in results.values():
        counts[r["signal"]] = counts.get(r["signal"], 0) + 1

    raised = lowered = unchanged = 0
    changes = []
    if before:
        for a, r in results.items():
            if a not in before:
                continue
            b, n = LEVEL[before[a]["signal"]], LEVEL[r["signal"]]
            raised += n > b
            lowered += n < b
            unchanged += n == b
            if before[a]["signal"] != r["signal"]:
                changes.append((a, before[a]["signal"], r["signal"], r["positives"]))

    if snapshot:
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_text(json.dumps(results, indent=1, sort_keys=True), encoding="utf-8")
        print(f"snapshot written: {snapshot}")

    print("levels:", json.dumps(dict(sorted(counts.items()))))
    for a, b, n, p in sorted(changes, key=lambda c: LEVEL[c[2]] - LEVEL[c[1]], reverse=True)[:40]:
        print(f"  CHANGED {b} -> {n}  {a}  positives={p}")
    print(f"TOTAL={len(results)} EMS_ONLY_POSITIVE={len(ems_only)} "
          f"RAISED={raised} LOWERED={lowered} UNCHANGED={unchanged}")
    return 0


# (group, how many, expected class, WHERE over the latest saved inputs).
# 'positive' = low or above; 'no_signal' = none or unavailable.
FIXTURE_GROUPS = [
    ("epi_overlay", 4, "positive",
     "coalesce(outputs->>'epi_flood_class','none') NOT IN ('none','')"),
    ("council_fpa", 2, "positive",
     "(outputs->>'ses_in_flood_planning_area') = 'true'"),
    ("hawkesbury_1pct", 2, "positive",
     "outputs->>'hawkesbury_flood_level_100aep' IS NOT NULL"),
    ("ems_alone_ridge_over_80m", 4, "no_signal",
     "(outputs->>'ems_flood_detected') = 'true' AND (outputs->>'ground_elevation_m_ahd')::float > 80"),
    # Any EMS-alone checks, ordered by md5(address) so the pick is stable and
    # no customer address ever appears in this file.
    ("ems_alone_any", 3, "no_signal",
     "(outputs->>'ems_flood_detected') = 'true' AND coalesce((outputs->>'ground_elevation_m_ahd')::float, 0) <= 80"),
    # Nothing positive at all (checked in Python with positive_sources, so a
    # high water history can never be labelled 'no flood evidence').
    ("no_evidence", 3, "no_signal",
     "coalesce(outputs->>'ems_flood_detected','false') <> 'true' "
     "AND coalesce(outputs->>'epi_flood_class','none') IN ('none','') "
     "AND outputs->>'ses_in_flood_planning_area' IS NULL"),
    # Real 2022 NSW extents (NSW-202207/202210). Whether a hit inside one counts
    # on its own is a rule decision for the fix PR, not a known answer, so these
    # carry expect=None and are only reported.
    ("nsw_2022_real_extent", 3, None,
     "jsonb_typeof(outputs->'ems_activations') = 'array' AND EXISTS (SELECT 1 FROM "
     "jsonb_array_elements(outputs->'ems_activations') a WHERE a->>'activation_id' LIKE 'NSW-2022%%')"),
]


OMITTED_FIELDS = {"address_council"}


def matches(expect: str | None, signal: str) -> bool | None:
    if expect is None:
        return None
    return LEVEL[signal] >= 1 if expect == "positive" else LEVEL[signal] == 0


def build_fixture() -> int:
    conn = _connect()
    cases = []
    try:
        cur = conn.cursor()
        for group, n, expect, where in FIXTURE_GROUPS:
            cur.execute(f"WITH latest AS ({LATEST_SQL}) SELECT address, outputs FROM latest "
                        f"WHERE {where} ORDER BY md5(address)")
            picked = 0
            for address, o in cur.fetchall():
                r = score(o)
                if group.startswith("ems_alone") and not ems_alone(r["positives"]):
                    continue
                if group == "no_evidence" and r["positives"]:
                    continue
                # Customer addresses stay out of the repo: a stable hash names
                # the case, and the free-text council field is dropped.
                inputs = {k: v for k, v in o.items() if k not in OMITTED_FIELDS}
                cases.append({
                    "group": group, "case_id": hashlib.sha256(address.encode()).hexdigest()[:12],
                    "expect": expect,
                    "signal_at_build": r["signal"], "positives": r["positives"],
                    "correct_at_build": matches(expect, r["signal"]), "inputs": inputs,
                })
                picked += 1
                if picked == n:
                    break
            print(f"{group}: {picked}/{n}", flush=True)
    finally:
        conn.close()
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(json.dumps(cases, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                       encoding="utf-8")
    wrong = sum(1 for c in cases if c["correct_at_build"] is False)
    print(f"fixture written: {FIXTURE.relative_to(WT)}  cases={len(cases)}  wrong_at_build={wrong}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--baseline", type=Path)
    p.add_argument("--write-snapshot", type=Path)
    p.add_argument("--build-fixture", action="store_true")
    a = p.parse_args()
    return build_fixture() if a.build_fixture else run(a.baseline, a.write_snapshot)


if __name__ == "__main__":
    sys.exit(main())
