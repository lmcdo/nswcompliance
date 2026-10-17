#!/usr/bin/env python3
"""Re-copy rows whose words are in a law unit that is more than 3x their length: use the SMALLEST COMPLETE unit.

prior-art-checked: extends scripts/sepp_marker_blind.py (Snapshot, ordered_cover, numbers_for_check, _related, constants)
and scripts/sepp_ref_fix.py (unit_label, state_clause_label); a new explicit mode -- decide()/decide_recopy()/SIZE_MAX
are untouched. No model reads or writes text: every step is string comparison.

User decision 2026-10-17: a row whose words appear IN ORDER (>= COVERAGE_MIN) in a law unit, but only in units > 3x its
length (refused unit_too_big), is replaced by the smallest complete unit of the law that holds its words, never a partial
clause. Mode name in evidence: "smallest_complete_unit".
  1. candidates = units with ordered coverage >= COVERAGE_MIN (same prefilter as decide_recopy, no size cap)
  2. smallest = candidates with no covering descendant. Exactly ONE, and every other candidate related to it
     (ancestor/descendant) -> else REFUSE ambiguous_unit
  3. unit_label(unit) is not None, passes the display check and ref_full(label) names the unit -> else unit_not_a_clause
  4. unit has <= MAX_WORDS tokens -> else unit_over_600_words
  5. every number of the row (numbers_for_check) is in the unit -> else number_missing
  6. unit text verbatim in the law -> else unit_text_not_verbatim_in_law; identical to the stored text -> already_identical
  Plan row: rule recopy, new_text = unit text, new_ref_number = unit_label when it differs from the stored ref_number.
  Recopy rows with version history -> has_version_history.

    python scripts/sepp_complete_unit.py       # read-only DB session; writes plan + evidence + refused CSV (dry run)
Verify: scripts/verify_sepp_marker_blind.py (re-decides mode rows with decide_smallest_unit). Apply: apply_sepp_marker_blind.py.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sepp_marker_blind as mb  # noqa: E402
import sepp_ref_fix as rf  # noqa: E402

p1 = mb.p1
ROOT = mb.ROOT
MODE = "smallest_complete_unit"
MAX_WORDS = 600


def covering_units(row: list[str], snap: mb.Snapshot) -> dict[str, tuple[int, float]]:
    """unit id -> (matched words, coverage) for every unit holding >= COVERAGE_MIN of the row's words in order."""
    rset = set(row)
    out = {}
    for uid, ut in snap.tokens.items():
        if not ut or len(ut) < len(row) * mb.COVERAGE_MIN:
            continue
        if len(rset & set(ut)) / len(rset) < mb.PREFILTER:
            continue
        n, cov = mb.ordered_cover(row, ut)
        if cov >= mb.COVERAGE_MIN:
            out[uid] = (n, cov)
    return out


def branch(uid: str | None) -> str | None:
    """The code / schedule a unit sits in: 'sch.6A-sec.4' -> 'sch.6A', 'sec.3D.61-ssec.2' -> 'sec.3D', 'sec.29' -> 'sec.29'."""
    m = re.match(r"(sch\.[0-9A-Z]+)", uid or "") or re.match(r"(sec\.\d+[A-Z]{0,2})", uid or "")
    return m.group(1) if m else None


def tiebreaks(ref: str | None, neighbour_refs: tuple[str | None, str | None]) -> list[tuple[str, str]]:
    """Context that can pick ONE of several places holding the same words, in the order it is tried:
    ('own_label', branch of the row's own ref_number), then ('neighbour_labels', branch) when the nearest earlier AND
    nearest later row of the same document both carry a clause label in that same branch."""
    out = []
    if mb.ref_unit(ref):
        out.append(("own_label_unit", mb.ref_unit(ref)))   # the clause the label names (and units inside / above it)
    own = branch(mb.ref_unit(ref))
    if own:
        out.append(("own_label", own))
    before, after = (branch(mb.ref_unit(x)) for x in neighbour_refs)
    if before and before == after:
        out.append(("neighbour_labels", before))
    return out


def decide_smallest_unit(old: str, snap: mb.Snapshot, scope: str | None = None,
                         context: list[tuple[str, str]] | None = None) -> dict:
    """-> {verdict: recopy|refuse, reason, unit, new_ref (label) ...evidence fields}. The words alone choose the unit;
    only when they fit several places is `context` (tiebreaks()) used, and it must leave exactly ONE (user 2026-10-17)."""
    row = mb.norm_tokens(old)
    if len(row) < mb.MIN_WORDS:
        return {"verdict": "refuse", "reason": "too_short", "n_words": len(row)}
    cover = covering_units(row, snap)
    if not cover:
        return {"verdict": "refuse", "reason": "no_unit_covers_90pct", "n_words": len(row)}
    smallest = sorted(u for u in cover if not any(u in snap.ancestors(o) for o in cover if o != u))
    outside = [u for u in cover if not mb._related(snap, u, smallest[0])]
    tiebreak = None
    if len(smallest) != 1 or outside:
        for by, br in context or []:
            if by == "own_label_unit":   # in the labelled clause's own line: the clause, inside it, or above it
                same = (lambda u, br=br: br in snap.units and mb._related(snap, u, br))
            else:
                same = (lambda u, br=br: branch(u) == br)
            inb = [u for u in smallest if same(u)]
            if len(inb) == 1 and not [u for u in cover if same(u) and not mb._related(snap, u, inb[0])]:
                smallest, tiebreak = inb, {"by": by, "branch": br}
                break
        else:
            return {"verdict": "refuse", "reason": "ambiguous_unit", "candidates": (smallest + outside)[:6],
                    "n_words": len(row)}
    uid = smallest[0]
    label = rf.unit_label(uid, scope)
    if label is None or rf.state_clause_label(label) != label or mb.ref_full(label)[0] != uid:
        return {"verdict": "refuse", "reason": "unit_not_a_clause", "unit": uid, "n_words": len(row)}
    ut = snap.tokens[uid]
    if len(ut) > MAX_WORDS:
        return {"verdict": "refuse", "reason": "unit_over_600_words", "unit": uid, "n_words": len(row),
                "unit_words": len(ut), "detail": str(len(ut))}
    lost = sorted(mb.numbers_for_check(old, snap, uid) - mb.rc.numbers(snap.units[uid].text))
    if lost:
        return {"verdict": "refuse", "reason": "number_missing", "unit": uid, "numbers_lost": lost, "n_words": len(row)}
    new = snap.units[uid].text
    if not mb.rc.verbatim(snap.inst, new):
        return {"verdict": "refuse", "reason": "unit_text_not_verbatim_in_law", "unit": uid, "n_words": len(row)}
    if mb.md5(new) == mb.md5(old):
        return {"verdict": "refuse", "reason": "already_identical", "unit": uid, "n_words": len(row)}
    n, cov = cover[uid]
    return {"verdict": "recopy", "reason": MODE, "unit": uid, "new_ref": label, "n_words": len(row), "matched_words": n,
            "coverage": round(cov, 4), "unit_words": len(ut), "size_ratio": round(len(ut) / len(row), 3),
            "new_sha256": mb.sha256(new), "tokens_sha256": mb.tokens_sha(row), "tiebreak": tiebreak}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refused", default=str(ROOT / "data" / "sepp_marker_blind_refused_2026-10-17.csv"))
    ap.add_argument("--date", default="2026-10-17")
    ap.add_argument("--context", action="store_true",
                    help="re-run the ambiguous_unit rows of data/sepp_complete_unit_refused_<date>.csv and "
                         "data/sepp_ref_fix_refused_<date>.csv with the own-label / neighbour-label tie-break; "
                         "outputs are named sepp_context_unit_*")
    args = ap.parse_args(argv)
    stamp = args.date
    if args.context:
        srcs = [ROOT / "data" / f"sepp_complete_unit_refused_{stamp}.csv", ROOT / "data" / f"sepp_ref_fix_refused_{stamp}.csv"]
        ids = sorted({int(r["id"]) for s in srcs for r in csv.DictReader(open(s, encoding="utf8"))
                      if r["reason"] == "ambiguous_unit"})
    else:
        ids = [int(r["id"]) for r in csv.DictReader(open(args.refused, encoding="utf8")) if r["reason"] == "unit_too_big"]
    conn = p1.connect()
    cur = conn.cursor()
    cur.execute("SET statement_timeout = 30000")
    cur.execute(mb.SQL, (ids,))
    rows = {r[0]: r for r in cur.fetchall()}
    neighbours: dict[int, tuple[str | None, str | None]] = {}
    if args.context:
        # prior-art-checked: reuse not viable -- the suggested routes/monitor serve or fetch provisions; none reads the
        # labels of a row's neighbours in its own document. Same table, same read-only session as mb.SQL above.
        docs = sorted({r[1] for r in rows.values()})
        cur.execute("SELECT id, document_id, ref_number FROM regulatory_provisions WHERE is_current AND document_id = ANY(%s)"
                    " ORDER BY document_id, id", (docs,))
        labelled: dict[str, list] = defaultdict(list)
        for i, d, rn in cur.fetchall():
            if mb.ref_unit(rn):
                labelled[d].append((i, rn))
        for i, r in rows.items():
            lst = labelled.get(r[1], [])
            before = [rn for j, rn in lst if j < i]
            after = [rn for j, rn in lst if j > i]
            neighbours[i] = (before[-1] if before else None, after[0] if after else None)
    conn.close()
    print(f"unit_too_big ids {len(ids)}  fetched {len(rows)}")

    refused, plan_rows, evidence, manifest = [], [], [], {}
    by_epi: dict[str, list] = defaultdict(list)
    for i in sorted(ids):
        r = rows.get(i)
        if r is None or not r[6] or r[7] is not None:
            refused.append({"id": i, "reason": "row_not_current_or_not_state_law"})
        elif r[5] == "proven":
            refused.append({"id": i, "reason": "already_proven"})
        else:
            epi = p1.instrument_for(r[1])
            if epi is None:
                refused.append({"id": i, "reason": "unmapped_instrument", "detail": r[1]})
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
            nb = neighbours.get(rid, (None, None))
            d = decide_smallest_unit(old, snap, None, tiebreaks(ref, nb) if args.context else None)
            if d["verdict"] == "refuse":
                refused.append({"id": rid, "reason": d["reason"], "ref_number": ref,
                                "unit_found": ";".join(d.get("candidates") or []) or d.get("unit") or "",
                                "detail": d.get("detail") or ",".join(d.get("numbers_lost") or [])})
                continue
            if nver:
                refused.append({"id": rid, "reason": "has_version_history", "ref_number": ref,
                                "unit_found": d["unit"], "detail": f"{nver} versions"})
                continue
            uid, label = d["unit"], d["new_ref"]
            new_ref = label if label != ref else None
            ev = {"id": rid, "rule": "recopy", "mode": MODE, "epi": epi, "snapshot_file": f.name,
                  "snapshot_sha256": snap.sha256, "law_date": law_date, "unit_id": uid, "norm_version": mb.NORM_VERSION,
                  "match_version": mb.MATCH_VERSION, "old_md5": om5, "ref_number": new_ref or ref, "pick": MODE}
            if new_ref:
                ev.update({"old_ref_number": ref, "new_ref_number": new_ref})
            ev.update({k: d[k] for k in ("n_words", "unit_words", "tokens_sha256", "matched_words", "coverage",
                                         "size_ratio", "new_sha256")})
            if args.context:   # the verifier rebuilds the context from the plan's ref_number + these neighbour labels
                ev.update({"neighbour_refs": list(nb), "tiebreak": d["tiebreak"]})
            row = {"id": rid, "md5": om5, "rule": "recopy", "kind": "complete_unit_recopy", "epi": epi,
                   "document_id": doc, "ref_number": ref, "unit_id": uid, "source": f"{p1.LAW_URL.format(epi=epi)}#{uid}",
                   "law_date": law_date, "old_text": old, "new_text": snap.units[uid].text}
            if new_ref:
                row.update({"old_ref_number": ref, "new_ref_number": new_ref})
            plan_rows.append(row)
            evidence.append(ev)

    plan = {"generated": stamp, "norm_version": mb.NORM_VERSION, "match_version": mb.MATCH_VERSION, "manifest": manifest,
            "method": "scripts/sepp_complete_unit.py (docstring has the rules). No model reads or writes text.",
            "rows": plan_rows}
    name = "sepp_context_unit" if args.context else "sepp_complete_unit"
    pp = ROOT / "data" / f"{name}_plan_{stamp}.json"
    pp.write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    ep = ROOT / "data" / f"{name}_evidence_{stamp}.jsonl"
    ep.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in evidence), encoding="utf8")
    rp = ROOT / "data" / f"{name}_refused_{stamp}.csv"
    with rp.open("w", newline="", encoding="utf8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "reason", "ref_number", "unit_found", "detail"], restval="")
        w.writeheader()
        w.writerows(refused)
    print(f"\nRECOPY (smallest complete unit): {len(evidence)}\nREFUSED: {len(refused)}")
    for k, n in Counter(r["reason"] for r in refused).most_common():
        print(f"  {n:5}  {k}")
    print(f"wrote {pp.relative_to(ROOT)}, {ep.relative_to(ROOT)}, {rp.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
