#!/usr/bin/env python3
"""Fix the ref_number of served SEPP rows whose WORDS are in the law but whose label points elsewhere (ref_mismatch).

prior-art-checked: extends scripts/sepp_marker_blind.py (Snapshot, find_seq, pick_exact, decide, decide_recopy, ref_full)
and reads its refused CSV; nothing else in scripts/ or the frontend derives a label from a unit id.
No model reads or writes text: every step is string comparison.

For each ref_mismatch row (current, state law, not proven, mapped instrument):
  1. find the law unit IGNORING the label: contiguous words (find_seq) -> prefer units the row fills >= SPAN_MIN ->
     unique smallest (pick_exact, ref=None); with no contiguous hit, decide_recopy(ignore_ref=True) incl. its peer check.
     Two or more unrelated candidates -> REFUSED ambiguous_unit. Never picked by sort order.
  2. unit id -> label by grammar only:  [sch.X-]sec.N[-ssec.M][-para1.a][-para2.i][-para3.A]
        -> 'Section N(M)(a)(i)'  or  'Schedule X, section N(M)(a)'.   Any other shape -> unit_not_a_clause.
  3. the label must pass the site's display check (port of stateClauseLabel in frontend-nextjs/lib/citation-display.ts).
  4. re-decide with the NEW label: decide(old_text, new_label, snap) must be accept/recopy AND ref_full(new_label)[0]
     must equal the decided unit (the label names exactly the unit the words are proven against).
  Recopy rows with version history -> has_version_history.

    python scripts/sepp_ref_fix.py            # read-only DB session; writes plan + evidence + refused CSV (dry run)
Verify: scripts/verify_sepp_marker_blind.py (handles new_ref_number rows). Apply: scripts/apply_sepp_marker_blind.py.
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

p1 = mb.p1
ROOT = mb.ROOT

# ---------------------------------------------------------------------------------- unit id -> label grammar
_UNIT = re.compile(
    r"^(?:sch\.(?P<sch>\d+[A-Z]{0,2})-)?sec\.(?P<sec>\d+[A-Z]{0,3}(?:\.\d+[A-Z]{0,3})?)"
    r"(?:-ssec\.(?P<ssec>\d+[A-Z]?))?"
    r"(?:-para1\.(?P<p1>[a-z]{1,2})(?:-para2\.(?P<p2>[ivxlc]{1,6})(?:-para3\.(?P<p3>[A-Z]{1,2}))?)?)?$")


def unit_label(uid: str | None) -> str | None:
    """'sch.11-sec.4' -> 'Schedule 11, section 4'; 'sec.3.4-ssec.2-para1.e' -> 'Section 3.4(2)(e)'; else None."""
    m = _UNIT.match(uid or "")
    if not m:
        return None
    tail = "".join(f"({m.group(k)})" for k in ("ssec", "p1", "p2", "p3") if m.group(k))
    if m.group("sch"):
        return f"Schedule {m.group('sch')}, section {m.group('sec')}{tail}"
    return f"Section {m.group('sec')}{tail}"


# ------------------------------------------------------------- port of stateClauseLabel (citation-display.ts)
_NUM = r"\d+[A-Z]{0,2}(?:\.\d+[A-Z]{0,2})*(?:\s*\([A-Za-z0-9]{1,4}\))*"
_DIV = r"(?:schedule|sch|chapter|part|division|div)\.?\s+\d+[A-Z]{0,2}"
_CW = r"(?:clause|cl|section|sec|s)\.?\s*"
STATE_CLAUSE_RE = re.compile(rf"^(?:{_DIV}(?:\s*,?\s*{_DIV})*(?:\s*,?\s*(?:{_CW})?{_NUM})?|(?:{_CW}){_NUM}|{_NUM})$", re.I)


def state_clause_label(ref) -> str | None:
    if not isinstance(ref, str):
        return None
    s = ref.strip()
    if not s or len(s) > 60:
        return None
    if re.search(r"provision|layout|_|__|~", s, re.I) or re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-", s, re.I):
        return None
    if re.fullmatch(r"\d{4,}", s):
        return None
    return s if STATE_CLAUSE_RE.match(s) else None


# ----------------------------------------------------------------------------------------- find the unit
def find_unit(old: str, snap: mb.Snapshot) -> dict:
    """The unit the row's words are in, ignoring ref_number. -> {unit, how} or {reason, ...} (refuse)."""
    row = mb.norm_tokens(old)
    if len(row) < mb.MIN_WORDS:
        return {"reason": "too_short"}
    hits = mb.find_seq(snap, row)
    if hits:
        filled = [u for u in sorted(hits) if len(row) / len(snap.tokens[u]) >= mb.SPAN_MIN]
        uid, how = mb.pick_exact(snap, filled or sorted(hits), None)
        if uid is None:
            return {"reason": "ambiguous_unit", "candidates": sorted(hits)[:6]}
        # The words also sitting in an unrelated branch (e.g. inside a longer section elsewhere) leaves the unit
        # undecided even when only one hit is filled: refuse (cross-review 2026-10-17).
        unrelated = [u for u in sorted(hits) if not mb._related(snap, u, uid)]
        if unrelated:
            return {"reason": "ambiguous_unit", "candidates": [uid] + unrelated[:5]}
        return {"unit": uid, "how": "contiguous_" + how}
    d = mb.decide_recopy(old, row, None, snap, ignore_ref=True)
    if d["verdict"] != "recopy":
        return {"reason": d["reason"], "candidates": d.get("candidates") or [], "unit": d.get("unit") or "",
                "detail": ",".join(d.get("numbers_lost") or [])}
    return {"unit": d["unit"], "how": "ordered_" + d["reason"]}


def fix_row(old: str, snap: mb.Snapshot) -> dict:
    """-> {verdict: accept|recopy|refuse, reason, unit, new_ref, how, ...decide() evidence fields}"""
    f = find_unit(old, snap)
    if "how" not in f:
        return dict(f, verdict="refuse")
    label = unit_label(f["unit"])
    if label is None:
        return {"verdict": "refuse", "reason": "unit_not_a_clause", "unit": f["unit"]}
    if state_clause_label(label) != label:
        return {"verdict": "refuse", "reason": "label_fails_display_check", "unit": f["unit"], "detail": label}
    d = mb.decide(old, label, snap)
    if d["verdict"] == "refuse":
        return dict(d, found_unit=f["unit"])
    if mb.ref_full(label)[0] != d["unit"]:
        return {"verdict": "refuse", "reason": "label_unit_mismatch", "unit": d["unit"],
                "detail": f"{label} names {mb.ref_full(label)[0]}"}
    return dict(d, new_ref=label, how=f["how"])


# ------------------------------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refused", default=str(ROOT / "data" / "sepp_marker_blind_refused_2026-10-18.csv"))
    ap.add_argument("--date", default="2026-10-17")
    args = ap.parse_args(argv)
    stamp = args.date
    ids = [int(r["id"]) for r in csv.DictReader(open(args.refused, encoding="utf8")) if r["reason"] == "ref_mismatch"]
    conn = p1.connect()
    cur = conn.cursor()
    cur.execute("SET statement_timeout = 30000")
    cur.execute(mb.SQL, (ids,))
    rows = {r[0]: r for r in cur.fetchall()}
    conn.close()
    print(f"ref_mismatch ids {len(ids)}  fetched {len(rows)}")

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
            d = fix_row(old, snap)
            if d["verdict"] == "refuse":
                refused.append({"id": rid, "reason": d["reason"], "ref_number": ref,
                                "unit_found": ";".join(d.get("candidates") or []) or d.get("unit") or "",
                                "detail": d.get("detail") or ""})
                continue
            if d["verdict"] == "recopy" and nver:
                refused.append({"id": rid, "reason": "has_version_history", "ref_number": ref,
                                "unit_found": d["unit"], "detail": f"{nver} versions"})
                continue
            uid, new_ref = d["unit"], d["new_ref"]
            rule = "accept" if d["verdict"] == "accept" else "recopy"
            ev = {"id": rid, "rule": rule, "epi": epi, "snapshot_file": f.name, "snapshot_sha256": snap.sha256,
                  "law_date": law_date, "unit_id": uid, "norm_version": mb.NORM_VERSION,
                  "match_version": mb.MATCH_VERSION, "old_md5": om5, "ref_number": new_ref,
                  "old_ref_number": ref, "new_ref_number": new_ref, "pick": d["reason"], "find_how": d["how"]}
            ev.update({k: d[k] for k in ("word_start", "word_end", "n_words", "unit_words", "span_share",
                                         "tokens_sha256", "ref_related", "excerpt", "matched_words", "coverage",
                                         "size_ratio", "new_sha256") if k in d})
            plan_rows.append({"id": rid, "md5": om5, "rule": rule, "kind": "ref_fix_" + rule, "epi": epi,
                              "document_id": doc, "ref_number": ref, "old_ref_number": ref, "new_ref_number": new_ref,
                              "unit_id": uid, "source": f"{p1.LAW_URL.format(epi=epi)}#{uid}", "law_date": law_date,
                              "old_text": old, "new_text": snap.units[uid].text if rule == "recopy" else None})
            evidence.append(ev)

    plan = {"generated": stamp, "norm_version": mb.NORM_VERSION, "match_version": mb.MATCH_VERSION,
            "manifest": manifest,
            "method": "scripts/sepp_ref_fix.py (docstring has the rules). No model reads or writes text.",
            "rows": plan_rows}
    pp = ROOT / "data" / f"sepp_ref_fix_plan_{stamp}.json"
    pp.write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    ep = ROOT / "data" / f"sepp_ref_fix_evidence_{stamp}.jsonl"
    ep.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in evidence), encoding="utf8")
    rp = ROOT / "data" / f"sepp_ref_fix_refused_{stamp}.csv"
    with rp.open("w", newline="", encoding="utf8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "reason", "ref_number", "unit_found", "detail"], restval="")
        w.writeheader()
        w.writerows(refused)
    print(f"\nFIXED accept: {sum(e['rule'] == 'accept' for e in evidence)}\n"
          f"FIXED recopy: {sum(e['rule'] == 'recopy' for e in evidence)}\nREFUSED: {len(refused)}")
    for k, n in Counter(r["reason"] for r in refused).most_common():
        print(f"  {n:5}  {k}")
    print(f"wrote {pp.relative_to(ROOT)}, {ep.relative_to(ROOT)}, {rp.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
