#!/usr/bin/env python3
"""Prove the unproven served Inner West LEP rows with the SEPP deciders, in order (opt-in scope registry_lep).

prior-art-checked: composes scripts/sepp_marker_blind.py (decide), scripts/sepp_ref_fix.py (fix_row, label path) and
scripts/sepp_complete_unit.py (decide_smallest_unit); row selection is scripts/lep_law_proof.py's CANDIDATES_SQL and
lep_for() (instrument_registry title -> epi). Nothing else in scripts/ chains the three deciders. No model reads or writes text.

Per row (served, not proven, source_council 'inner_west', mapped to a registry LEP):
  1. mb.decide(old, own ref_number)                         -> accept / recopy, else on ref_mismatch:
  2. rf.fix_row(old, snap, 'registry_lep')  (label-blind unit; LEP label 'Clause N(M)(a)') -> accept / recopy, else on unit_too_big:
  3. cu.decide_smallest_unit(old, snap, 'registry_lep')    -> recopy of the smallest complete unit.
Anything else stays unproven and is listed in the refused CSV with its stage and reason.

    python scripts/sepp_lep_proof.py --scope registry_lep      # read-only DB session; plan + evidence + refused (dry run)
Verify: verify_sepp_marker_blind.py <plan> <evidence>.  Apply: apply_sepp_marker_blind.py <plan> <evidence> --scope registry_lep
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lep_law_proof as lp  # noqa: E402
import sepp_complete_unit as cu  # noqa: E402
import sepp_marker_blind as mb  # noqa: E402
import sepp_ref_fix as rf  # noqa: E402

p1 = mb.p1
ROOT = mb.ROOT
SCOPE = lp.SCOPE            # 'registry_lep'
COUNCIL = "inner_west"
DOC_PREFIX = "Inner_West_Local_Environmental_Plan_2022"
EVID_KEYS = ("word_start", "word_end", "n_words", "unit_words", "span_share", "tokens_sha256", "ref_related", "excerpt",
             "matched_words", "coverage", "size_ratio", "new_sha256")


def decide_chain(old: str, ref: str | None, snap: mb.Snapshot) -> tuple[str, dict]:
    """-> (stage, decision). stage in marker_blind | ref_fix | complete_unit; decision.verdict accept|recopy|refuse."""
    d = mb.decide(old, ref, snap)
    if d["verdict"] != "refuse" or d["reason"] not in ("ref_mismatch", "unit_too_big"):
        return "marker_blind", d
    if d["reason"] == "ref_mismatch":
        return "ref_fix", rf.fix_row(old, snap, SCOPE)
    return "complete_unit", cu.decide_smallest_unit(old, snap, SCOPE)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=[SCOPE], required=True, help="explicit opt-in: Inner West LEP rows, not state law")
    ap.add_argument("--date", default="2026-10-17")
    args = ap.parse_args(argv)
    stamp = args.date
    conn = p1.connect()
    cur = conn.cursor()
    cur.execute("SET statement_timeout = 30000")
    cur.execute(lp.REGISTRY_SQL)
    title_map = lp.build_title_map(cur.fetchall())
    cur.execute(lp.CANDIDATES_SQL)
    cand = [r for r in cur.fetchall() if r[7] == COUNCIL and (r[1] or "").startswith(DOC_PREFIX)]
    ids = [r[0] for r in cand]
    cur.execute(mb.SQL, (ids,))
    rows = {r[0]: r for r in cur.fetchall()}
    conn.close()
    print(f"candidate rows {len(cand)}  fetched {len(rows)}")

    refused, plan_rows, evidence, manifest = [], [], [], {}
    by_epi: dict[str, list] = defaultdict(list)
    for i in ids:
        r = rows[i]
        epi = lp.lep_for(r[1], title_map)
        if not r[6] or r[7] != COUNCIL:
            refused.append({"id": i, "stage": "", "reason": "row_not_current_or_not_inner_west"})
        elif r[5] == "proven":
            refused.append({"id": i, "stage": "", "reason": "already_proven"})
        elif epi is None:
            refused.append({"id": i, "stage": "", "reason": "unmapped_instrument", "detail": r[1]})
        else:
            by_epi[epi].append(r)
    for epi in sorted(by_epi):
        f = p1.latest_cache(epi)
        snap = mb.Snapshot(f)
        manifest[epi] = {"file": f.name, "sha256": snap.sha256, "bytes": f.stat().st_size,
                         "source": p1.LAW_URL.format(epi=epi)}
        law_date = f.stem.rpartition("_")[2]
        print(f"{epi}: {len(snap.units)} units, {len(by_epi[epi])} rows", flush=True)
        for rid, doc, ref, old, om5, _cs, _cur, _sc, nver in by_epi[epi]:
            stage, d = decide_chain(old, ref, snap)
            if d["verdict"] == "refuse":
                refused.append({"id": rid, "stage": stage, "reason": d["reason"], "ref_number": ref,
                                "unit_found": ";".join(d.get("candidates") or []) or d.get("unit") or "",
                                "detail": d.get("detail") or ",".join(d.get("numbers_lost") or [])})
                continue
            if d["verdict"] == "recopy" and nver:
                refused.append({"id": rid, "stage": stage, "reason": "has_version_history", "ref_number": ref,
                                "unit_found": d["unit"], "detail": f"{nver} versions"})
                continue
            uid = d["unit"]
            rule = "accept" if d["verdict"] == "accept" else "recopy"
            new_ref = d.get("new_ref")
            if stage == "complete_unit" and new_ref == ref:
                new_ref = None
            ev = {"id": rid, "rule": rule, "epi": epi, "snapshot_file": f.name, "snapshot_sha256": snap.sha256,
                  "law_date": law_date, "unit_id": uid, "norm_version": mb.NORM_VERSION,
                  "match_version": mb.MATCH_VERSION, "old_md5": om5, "ref_number": new_ref or ref}
            row = {"id": rid, "md5": om5, "rule": rule, "epi": epi, "document_id": doc, "ref_number": ref,
                   "unit_id": uid, "source": f"{p1.LAW_URL.format(epi=epi)}#{uid}", "law_date": law_date,
                   "source_council": COUNCIL, "old_text": old,
                   "new_text": snap.units[uid].text if rule == "recopy" else None}
            if stage == "marker_blind":
                ev["pick"] = d["reason"]
                row["kind"] = "marker_blind_" + rule
            elif stage == "ref_fix":
                ev.update({"pick": d["reason"], "find_how": d["how"], "old_ref_number": ref, "new_ref_number": new_ref})
                row.update({"kind": "ref_fix_" + rule, "old_ref_number": ref, "new_ref_number": new_ref})
            else:
                ev.update({"mode": cu.MODE, "pick": cu.MODE})
                row["kind"] = "complete_unit_recopy"
                if new_ref:
                    ev.update({"old_ref_number": ref, "new_ref_number": new_ref})
                    row.update({"old_ref_number": ref, "new_ref_number": new_ref})
            ev.update({k: d[k] for k in EVID_KEYS if k in d})
            ev["stage"] = stage
            row["stage"] = stage
            plan_rows.append(row)
            evidence.append(ev)

    plan = {"generated": stamp, "scope": SCOPE, "norm_version": mb.NORM_VERSION, "match_version": mb.MATCH_VERSION,
            "manifest": manifest,
            "method": "scripts/sepp_lep_proof.py (docstring has the rules). No model reads or writes text.",
            "rows": plan_rows}
    pp = ROOT / "data" / f"inner_west_lep_proof_plan_{stamp}.json"
    pp.write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    ep = ROOT / "data" / f"inner_west_lep_proof_evidence_{stamp}.jsonl"
    ep.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in evidence), encoding="utf8")
    rp = ROOT / "data" / f"inner_west_lep_proof_refused_{stamp}.csv"
    with rp.open("w", newline="", encoding="utf8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "stage", "reason", "ref_number", "unit_found", "detail"], restval="")
        w.writeheader()
        w.writerows(refused)
    print(f"\nPLAN rows: {len(plan_rows)}  by stage/rule {dict(Counter((e['stage'], e['rule']) for e in evidence))}"
          f"\nREFUSED: {len(refused)}")
    for k, n in Counter((r.get("stage", ""), r["reason"]) for r in refused).most_common():
        print(f"  {n:5}  {k}")
    print(f"wrote {pp.relative_to(ROOT)}, {ep.relative_to(ROOT)}, {rp.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
