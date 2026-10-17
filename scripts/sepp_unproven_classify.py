#!/usr/bin/env python3
"""Classify the served state-law rows that are still unproven, by how they relate to the law's own units.

READ-ONLY: one SELECT, no model, writes only the CSV. Reuses scripts/state_law_recopy.py (unit parser, pick_unit,
judge, segments) and scripts/state_law_proof.py (law cache, instrument_for).

    python sepp_unproven_classify.py [--date 2026-10-18]
"""
from __future__ import annotations

import argparse
import csv
import difflib
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import state_law_proof as p1  # noqa: E402
import state_law_recopy as rc  # noqa: E402

ROOT = p1.ROOT
NEAR = 0.90
LOW = 0.60
MIN_WORDS = 8
SQL = ("SELECT id, document_id, ref_number, provision_text FROM regulatory_provisions "
       "WHERE document_id LIKE 'State_Environmental_Planning_P%%' AND is_current AND v2_is_actionable "
       "AND (v2_provision_type IS NULL OR v2_provision_type <> 'TOC') "
       "AND NOT (COALESCE(citation_status,'') IN ('proven','imprecise') OR COALESCE(page_check,'') IN ('on_page','moved')) "
       "ORDER BY id")


def row_words(text: str) -> list[str]:
    return [w for seg in rc.segments(p1.strip_heading(text)) for w in seg]


def match_stats(a: list[str], b: list[str]) -> tuple[float, float]:
    """(longest contiguous run / len(a), words in blocks of >=3 / len(a))."""
    if not a or not b:
        return 0.0, 0.0
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    run = sm.find_longest_match(0, len(a), 0, len(b)).size
    cov = sum(m.size for m in sm.get_matching_blocks() if m.size >= 3)
    return run / len(a), cov / len(a)


def clause_status(ref, inst) -> tuple[str, str]:
    """(status, unit): exists | absent | repealed | no_ref, from the unit ids the legislation HTML carries."""
    m = re.match(r"^\s*(Section|Clause|cl|s)\s*(\d+[A-Z]{0,3}(?:\.\d+[A-Z]{0,3})?)", ref or "", re.I)
    if m:
        uid = f"sec.{m.group(2)}"
    else:
        m = re.match(r"^\s*Schedule\s+(\d+[A-Z]{0,2})", ref or "", re.I)
        if not m:
            return "no_ref", ""
        uid = f"sch.{m.group(1)}"
    if not any(u == uid or u.startswith(uid + "-") for u in inst.units):
        return "absent", uid
    head = inst.units.get(uid)
    if head and re.search(r"\[(Repealed|Omitted)\]|^\W*(Repealed|Omitted)\b", head.text[:160], re.I):
        return "repealed", uid
    return "exists", uid


def independent(a: str, b: str) -> bool:
    return not (b.startswith(a + "-") or a.startswith(b + "-"))


def classify(text, inst, order, by_pos, wordsets) -> dict:
    rw = row_words(text)
    out = {"n_words": len(rw), "best_unit": "", "containment": 0.0, "jaccard": 0.0, "run_share": 0.0,
           "coverage": 0.0, "merge_units": "", "merge_coverage": 0.0}
    if not rw:
        out["bucket"] = "fragment_short"
        return out
    rs = set(rw)
    hits: Counter = Counter()
    for r in rc.row_runs(p1.strip_heading(text)):
        for uid in inst.index.get(hash(r), ()):
            hits[uid] += 1
    cont = []
    for uid, ws in wordsets.items():
        i = len(rs & ws) if ws else 0
        if i:
            cont.append((i / len(rs), i / len(rs | ws), uid))
    cont.sort(key=lambda t: (-t[0], -t[1], len(inst.words[t[2]])))
    cands = list(dict.fromkeys([u for u, _ in hits.most_common(8)] + [t[2] for t in cont[:8]]))
    cj = {t[2]: (t[0], t[1]) for t in cont}
    best = None
    for uid in cands:
        run, cov = match_stats(rw, inst.words[uid])
        key = (round(cov, 3), round(run, 3), -len(inst.words[uid]))
        if best is None or key > best[0]:
            best = (key, uid, run, cov)
    if best is None:
        out["bucket"] = "paraphrase"
        return out
    _, uid, run, cov = best
    out.update(best_unit=uid, run_share=round(run, 3), coverage=round(cov, 3),
               containment=round(cj.get(uid, (0, 0))[0], 3), jaccard=round(cj.get(uid, (0, 0))[1], 3))
    if cov < NEAR:
        pos = order[uid]
        bestm = (0.0, "")
        for size in (2, 3):
            for start in range(max(0, pos - size + 1), pos + 1):
                win = by_pos[start:start + size]
                if len(win) < size or uid not in win:
                    continue
                if not all(independent(a, b) for i, a in enumerate(win) for b in win[i + 1:]):
                    continue
                _, mc = match_stats(rw, [w for u in win for w in inst.words[u]])
                if mc > bestm[0]:
                    bestm = (mc, ";".join(win))
        out["merge_coverage"], out["merge_units"] = round(bestm[0], 3), bestm[1]
    if len(rw) < MIN_WORDS:
        out["bucket"] = "fragment_short"
    elif run >= NEAR:
        out["bucket"] = "near_copy"
    elif cov >= NEAR:
        out["bucket"] = "copy_with_gaps"
    elif out["merge_coverage"] >= NEAR:
        out["bucket"] = "merge_2_3_units"
    elif cov >= LOW:
        out["bucket"] = "partial_overlap"
    else:
        out["bucket"] = "paraphrase"
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-10-18")
    args = ap.parse_args(argv)
    conn = p1.connect()
    cur = conn.cursor()
    cur.execute("SET statement_timeout = 30000")
    cur.execute(SQL)
    rows = cur.fetchall()
    conn.close()
    by_epi: dict[str, list] = defaultdict(list)
    res = []
    for r in rows:
        epi = p1.instrument_for(r[1])
        if epi:
            by_epi[epi].append(r)
        else:
            res.append({"id": r[0], "ref_number": r[2], "epi": "", "bucket": "unmapped_instrument",
                        "head": re.sub(r"\s+", " ", r[3] or "")[:80]})
    print(f"rows {len(rows)}  mapped {sum(map(len, by_epi.values()))}")
    for epi in sorted(by_epi):
        inst = rc.Instrument(p1.latest_cache(epi).read_text(encoding="utf-8", errors="replace"))
        by_pos = list(inst.units)
        order = {u: i for i, u in enumerate(by_pos)}
        wordsets = {u: set(w) for u, w in inst.words.items()}
        print(f"{epi}: {len(by_pos)} units, {len(by_epi[epi])} rows", flush=True)
        for rid, doc, ref, text in by_epi[epi]:
            c = classify(text or "", inst, order, by_pos, wordsets)
            cs, cdetail = clause_status(ref, inst)
            uid, why, _ = rc.pick_unit(text or "", inst)
            if uid is None:
                tool = f"skipped:{why}"
            else:
                j = rc.judge(text or "", inst, uid)
                tool = "recopy_ok" if j["ok"] else "skipped:failed_" + "+".join(j["failed"])
            res.append({"id": rid, "ref_number": ref, "epi": epi, "bucket": c["bucket"], "best_unit": c["best_unit"],
                        "n_words": c["n_words"], "containment": c["containment"], "jaccard": c["jaccard"],
                        "run_share": c["run_share"], "coverage": c["coverage"], "merge_units": c["merge_units"],
                        "merge_coverage": c["merge_coverage"], "ref_clause_status": cs, "ref_clause_unit": cdetail,
                        "recopy_tool": tool, "head": re.sub(r"\s+", " ", text or "")[:80]})
    cols = ["id", "ref_number", "epi", "bucket", "best_unit", "n_words", "containment", "jaccard", "run_share",
            "coverage", "merge_units", "merge_coverage", "ref_clause_status", "ref_clause_unit", "recopy_tool", "head"]
    out = ROOT / "data" / f"sepp_unproven_classified_{args.date}.csv"
    with out.open("w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(res)
    print(f"\n{'bucket':20}{'rows':>6}{'recopy_ok':>11}{'clause_absent':>15}{'repealed':>10}")
    for b, n in Counter(r["bucket"] for r in res).most_common():
        sub = [r for r in res if r["bucket"] == b]
        print(f"{b:20}{n:6}{sum(r.get('recopy_tool') == 'recopy_ok' for r in sub):11}"
              f"{sum(r.get('ref_clause_status') == 'absent' for r in sub):15}"
              f"{sum(r.get('ref_clause_status') == 'repealed' for r in sub):10}")
    print(f"{'ALL':20}{len(res):6}{sum(r.get('recopy_tool') == 'recopy_ok' for r in res):11}")
    print("ref clause status:", dict(Counter(r.get("ref_clause_status") for r in res)))
    print("recopy tool:", dict(Counter(r.get("recopy_tool") for r in res)))
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
