#!/usr/bin/env python3
"""Checks for the plan-brief outreach claims OC-22..OC-29 (the "top 5 rules per category" claim).

prior-art-checked: scripts/outreach_claim_checks.py (helpers sql_count / jest_file, claim table), scripts/dq_db.py (read-only
connection), scripts/dq_probe_live.py. None of them scores the brief: no existing script computes "is the proven rule in the
top 5 of its row" or reads project_brief_rows. The scoring research code lived outside the repo
(~/.claude/plans/ce-applies-when-2026-11-07/gold_eval.py, score_built.py); this is its in-repo, read-only form.

Everything is computed from the live tables, never from a stored result, so a rebuilt or reloaded brief is re-judged:
  recall      project_brief_rows vs gold (dcp_setback_controls verbatim rows matched to clauses; plus the blind hold-out
              gold in data/plan_brief_gold_holdout.json). Zone group used = the project type's normal one, as the product does.
  page proof  share of brief rows whose clause has page_check = 'on_page'.
  integrity   every brief row points at a current, actionable clause that belongs to the row's council.
  session read  data/plan_brief_session_read_2026-11-08.json: 30 rows read by the Claude session. NOT independent of the
              build. It goes stale (FAIL) the moment a recorded first clause is no longer the row's first clause.

Exit codes follow outreach_claim_checks.py: PASS / FAIL / UNKNOWN (could not run here: no database, no node_modules, no URL).
"""
from __future__ import annotations

import collections
import json
import math
import os
import re
import statistics
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"
Result = tuple[str, str]

CORE_ZONE = {"dwelling_house": "R2", "dual_occupancy": "R2", "secondary_dwelling": "R2",
             "multi_dwelling_housing": "R3", "residential_flat_building": "R4", "shop_top_housing": "B"}  # noqa: zone-codes -- the brief build's own group labels
ROW_TYPES = {"front_setback", "side_setback", "rear_setback", "secondary_street_setback", "car_parking",
             "landscaping_min", "private_open_space", "max_site_coverage", "max_height", "deep_soil_min"}
HOLDOUT = {"hornsby", "wollongong", "woollahra"}
RECALL_BAR = 0.90
PAGE_BAR = 0.98
# Gold cells dropped because the "proven" clause does not state a requirement for that row (decided 2026-11-08, listed not hidden).
WEAK_GOLD = {
    ("blacktown", "dual_occupancy", "landscaping_min"), ("blacktown", "secondary_dwelling", "landscaping_min"),   # 4.3.15: owner maintains grounds, no figure
    ("cumberland", "dual_occupancy", "front_setback"), ("cumberland", "dual_occupancy", "rear_setback"),
    ("cumberland", "dual_occupancy", "side_setback"),                                                              # 2.1: cross-reference to a state guide
    ("city_of_sydney", "dwelling_house", "side_setback"),                                                          # 4.1.2: heritage conservation areas only
}


def _conn():
    try:
        from dq_db import connect
        return connect()
    except Exception:  # noqa: BLE001 - unreachable is UNKNOWN, reported by the caller
        return None


def _norm(t: str | None) -> str:
    return re.sub(r"[^a-z0-9.%]", "", (t or "").lower())


def _wilson_lower(k: int, n: int, z: float = 1.96) -> float:
    p = k / n
    d = 1 + z * z / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


def _brief_top5(cur) -> dict:
    cur.execute("SELECT council, dev_type, zone_group, row_type, rank, provision_id FROM project_brief_rows WHERE rank <= 5")
    top: dict = collections.defaultdict(list)
    for council, dev, zone, row, rank, pid in cur.fetchall():
        top[(council, dev, zone, row)].append((rank, pid))
    return {k: [pid for _, pid in sorted(v)] for k, v in top.items()}


def _gold_cells(cur, councils: set[str]) -> dict:
    cells: dict = collections.defaultdict(set)
    cur.execute("SELECT lga, dev_type, control_type, source_text, pdf_page FROM dcp_setback_controls "
                "WHERE is_current AND quote_status = 'verbatim' AND (needs_review IS NULL OR needs_review = false) "
                "AND lga <> 'nsw_statewide' AND source_text IS NOT NULL")
    by = collections.defaultdict(list)
    for lga, dev, ct, q, pg in cur.fetchall():
        if lga in councils and ct in ROW_TYPES and dev in CORE_ZONE and len(_norm(q)) >= 15:
            by[lga].append((dev, ct, _norm(q), pg))
    for lga, rows in by.items():
        cur.execute("SELECT id, provision_text, pdf_page FROM regulatory_provisions "
                    "WHERE source_council = %s AND is_current AND v2_is_actionable", (lga,))
        pv = [(i, _norm(t), p) for i, t, p in cur.fetchall()]
        for dev, ct, q, pg in rows:
            hit = [i for i, t, p in pv if q in t and (p is None or pg is None or abs(p - pg) <= 1)]
            if 1 <= len(hit) <= 3:
                cells[(lga, dev, ct)] |= set(hit)
    gold_b = json.loads((ROOT / "data" / "plan_brief_gold_holdout.json").read_text(encoding="utf-8"))
    for it in gold_b:
        if it["council"] in councils and it["council"] in HOLDOUT:
            devs = [d for d in it["applies_to"] if d in CORE_ZONE] or ["dwelling_house"]
            cells[(it["council"], devs[0], it["rule_type"])].add(it["id"])
    return {k: v for k, v in cells.items() if k not in WEAK_GOLD}


def brief_recall() -> Result:
    conn = _conn()
    if conn is None:
        return UNKNOWN, "recall: database unreachable"
    try:
        with conn.cursor() as cur:
            top = _brief_top5(cur)
            councils = {k[0] for k in top}
            if not councils:
                return FAIL, "recall: project_brief_rows is empty"
            cells = _gold_cells(cur, councils)
    except Exception as exc:  # noqa: BLE001 - a query that no longer runs is a broken check
        return FAIL, f"recall: query failed ({exc})"
    finally:
        conn.close()
    allk = holdk = alln = holdn = 0
    for (council, dev, row), ids in cells.items():
        hit = bool(ids & set(top.get((council, dev, CORE_ZONE[dev], row), [])))
        alln += 1
        allk += hit
        if council in HOLDOUT:
            holdn += 1
            holdk += hit
    if alln < 100 or holdn < 30:
        return FAIL, f"recall: only {alln} gold cells ({holdn} hold-out) - too few to mean anything"
    a, h = allk / alln, holdk / holdn
    detail = (f"proven rule in the top 5: {allk}/{alln} = {a:.0%} overall (lower 95% bound {_wilson_lower(allk, alln):.0%}); "
              f"hold-out {holdk}/{holdn} = {h:.0%} (bound {_wilson_lower(holdk, holdn):.0%}); bar {RECALL_BAR:.0%}")
    return (PASS if a >= RECALL_BAR and h >= RECALL_BAR else FAIL), detail


def _scalar(label: str, sql: str):
    conn = _conn()
    if conn is None:
        return None, f"{label}: database unreachable"
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone(), ""
    except Exception as exc:  # noqa: BLE001
        return "ERR", f"{label}: query failed ({exc})"
    finally:
        conn.close()


def brief_page_proof() -> Result:
    row, err = _scalar("page proof", "SELECT count(*) FILTER (WHERE rp.page_check = 'on_page'), count(*) "
                                     "FROM project_brief_rows b JOIN regulatory_provisions rp ON rp.id = b.provision_id")
    if row is None:
        return UNKNOWN, err
    if row == "ERR":
        return FAIL, err
    ok, n = row
    if not n:
        return FAIL, "page proof: no brief rows"
    return (PASS if ok / n >= PAGE_BAR else FAIL), f"brief rows on their cited page: {ok}/{n} = {ok / n:.1%} (bar {PAGE_BAR:.0%})"


def brief_integrity() -> Result:
    row, err = _scalar("integrity", "SELECT count(*) FILTER (WHERE NOT (rp.is_current AND rp.v2_is_actionable) OR rp.source_council <> b.council), "
                                    "count(*) FROM project_brief_rows b JOIN regulatory_provisions rp ON rp.id = b.provision_id")
    if row is None:
        return UNKNOWN, err
    if row == "ERR":
        return FAIL, err
    bad, n = row
    if not n:
        return FAIL, "integrity: no brief rows"
    return (PASS if bad == 0 else FAIL), f"brief rows pointing at a stale, non-actionable or other-council clause: {bad} of {n} (must be 0). Rows only point at stored clauses, so no figure can be invented"


def brief_rows_from_stale_chapters() -> Result:
    """OB-4: no brief row may come from a chapter whose PDF has changed since it was read (the DQ-70 predicate, applied to the brief)."""
    row, err = _scalar("stale chapters", "SELECT count(*) FILTER (WHERE r.content_hash <> r.provisions_extracted_from_hash), count(*) "
                                         "FROM project_brief_rows b JOIN regulatory_provisions p ON p.id = b.provision_id "
                                         "JOIN dcp_chapter_registry r ON r.council = p.source_council AND r.chapter_key = p.source_chapter_key "
                                         "WHERE r.is_active AND r.provisions_extracted_from_hash IS NOT NULL AND r.content_hash IS NOT NULL")
    if row is None:
        return UNKNOWN, err
    if row == "ERR":
        return FAIL, err
    bad, n = row
    return (PASS if bad == 0 else FAIL), f"brief rows from a chapter whose PDF changed since it was read: {bad} (of {n} brief rows with a recorded hash; must be 0)"


def _src_has(path: str, *needles: str) -> Result:
    text = (ROOT / path).read_text(encoding="utf-8")
    missing = [n for n in needles if n not in text]
    return (PASS if not missing else FAIL), f"{path}: " + ("flag guard present" if not missing else f"missing {missing}")


def flag_guard_route() -> Result:
    return _src_has("frontend-nextjs/app/api/brief/for-property/route.ts", "process.env.PLAN_BRIEF !== 'on'", "enabled: false")


def flag_guard_ui() -> Result:
    return _src_has("frontend-nextjs/components/compliance/YourProjectSummary.tsx", "process.env.NEXT_PUBLIC_PLAN_BRIEF === 'on'")


_JEST: Result | None = None


def brief_jest() -> Result:
    """The component tests: renders nothing without rows, empty row says so, wording is indicative. Run once per process."""
    global _JEST
    if _JEST is None:
        from outreach_claim_checks import jest_file
        _JEST = jest_file("__tests__/components/plan-brief.test.tsx")
    return _JEST


def brief_speed() -> Result:
    base = os.environ.get("PLAN_BRIEF_URL")
    if not base:
        return UNKNOWN, ("speed: set PLAN_BRIEF_URL to a deployment with PLAN_BRIEF=on (and PLAN_BRIEF_HEADERS if protected) "
                         "to time it. Measured by hand 2026-11-08 on a preview: p50 0.98 s, p95 1.19 s over 102 calls; not a pass here")
    headers = dict(h.split(":", 1) for h in (os.environ.get("PLAN_BRIEF_HEADERS") or "").split(";") if ":" in h)
    combos = [(c, d) for c in ("ashfield", "penrith", "waverley", "wollongong", "georges_river", "hornsby") for d in CORE_ZONE]
    times = []
    for council, dev in combos * 2:
        url = f"{base.rstrip('/')}/api/brief/for-property?council={council}&dev_type={dev}&zone={CORE_ZONE[dev]}"
        t0 = time.perf_counter()
        try:
            urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20).read()
        except Exception as exc:  # noqa: BLE001
            return FAIL, f"speed: {url} failed ({exc})"
        times.append(time.perf_counter() - t0)
        time.sleep(2.1)       # the route allows 30 requests a minute
    times.sort()
    p95 = times[min(len(times) - 1, math.ceil(0.95 * len(times)) - 1)]
    return (PASS if p95 < 2.0 else FAIL), f"speed: {len(times)} calls, p50 {statistics.median(times):.2f}s, p95 {p95:.2f}s (bar 2 s)"


def session_read() -> Result:
    path = ROOT / "data" / "plan_brief_session_read_2026-11-08.json"
    rec = json.loads(path.read_text(encoding="utf-8"))["rows"]
    wrong = [r for r in rec if r["grade"] == "WRONG"]
    if len(rec) < 30:
        return FAIL, f"session read: only {len(rec)} rows recorded, need 30"
    conn = _conn()
    if conn is None:
        return UNKNOWN, "session read: database unreachable"
    stale = []
    try:
        with conn.cursor() as cur:
            top = _brief_top5(cur)
    finally:
        conn.close()
    for r in rec:
        first = (top.get((r["council"], r["dev_type"], r["zone_group"], r["row_type"])) or [None])[0]
        if first != r["first_provision_id"]:
            stale.append((r["council"], r["row_type"]))
    if stale:
        return FAIL, f"session read is STALE: {len(stale)} of {len(rec)} rows have a different first clause now (e.g. {stale[:3]}). Re-read them"
    return (PASS if len(wrong) < 2 else FAIL), (f"session read (Claude, not independent of the build): {len(rec)} rows across "
                                                f"{len({r['council'] for r in rec})} councils, {len(wrong)} WRONG (limit: fewer than 2), "
                                                f"{sum(r['grade'] == 'WEAK' for r in rec)} weak; every recorded first clause is still the row's first clause")


def owner_read() -> Result:
    """OC-29: the owner's recorded read of 30 brief rows (data/plan_brief_owner_read_2026-11-09.json).
    Passes only when 30 rows are recorded, at least 28 are right, fewer than 2 are wrong, and every recorded
    first clause is still the row's first clause now (a rebuilt or reloaded brief makes the read stale)."""
    path = ROOT / "data" / "plan_brief_owner_read_2026-11-09.json"
    if not path.exists():
        return FAIL, "owner read: no recorded read yet (data/plan_brief_owner_read_2026-11-09.json is missing)"
    rec = json.loads(path.read_text(encoding="utf-8"))["rows"]
    right = [r for r in rec if r["mark"] == "right"]
    wrong = [r for r in rec if r["mark"] == "wrong"]
    if len(rec) < 30:
        return FAIL, f"owner read: only {len(rec)} rows recorded, need 30"
    conn = _conn()
    if conn is None:
        return UNKNOWN, "owner read: database unreachable"
    try:
        with conn.cursor() as cur:
            top = _brief_top5(cur)
    finally:
        conn.close()
    stale = [(r["council"], r["row_type"]) for r in rec
             if ((top.get((r["council"], r["dev_type"], r["zone_group"], r["row_type"])) or [None])[0]) != r["first_provision_id"]]
    if stale:
        return FAIL, f"owner read is STALE: {len(stale)} of {len(rec)} rows have a different first clause now (e.g. {stale[:3]}). Read them again"
    ok = len(right) >= 28 and len(wrong) < 2
    return (PASS if ok else FAIL), (f"owner read: {len(rec)} rows across {len({r['council'] for r in rec})} councils, {len(right)} right, "
                                    f"{len(wrong)} wrong, {sum(r['mark'] == 'unsure' for r in rec)} not sure (bar: 28 or more right, fewer than 2 wrong); "
                                    f"every recorded first clause is still the row's first clause")
