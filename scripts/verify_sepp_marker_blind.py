#!/usr/bin/env python3
"""Re-derive every marker-blind proof and re-copy from the law snapshot. Trusts nothing in the plan but the row text.

prior-art-checked: no verifier exists for sepp_marker_blind (scripts/verify_* are DCP/page/coverage checks); this
imports the SAME decide() as the planner, plus direct token checks of the claimed offsets, so a tampered plan fails.

Per evidence row:
  - snapshot file exists, its sha256 == evidence == plan manifest == data/law_text_cache/manifest.json
  - norm/match versions are the current ones
  - the plan row (old_text md5 == evidence old_md5) is re-decided from the snapshot: verdict, unit, offsets,
    coverage, hashes must equal the evidence
  - accept: unit tokens[word_start:word_end] == the row's tokens (checked directly, not via decide)
  - recopy: new_text == the unit's text in the snapshot, sha256 == evidence, coverage >= 0.9, size <= 3x,
    every number of the old text is in the new text
Exit 0 all verified; 1 on any mismatch; 2 if nothing was verified.

    python scripts/verify_sepp_marker_blind.py data/sepp_marker_blind_plan_<d>.json data/sepp_marker_blind_evidence_<d>.jsonl
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sepp_marker_blind as mb  # noqa: E402
import sepp_ref_fix as rf  # noqa: E402

CHECKED = ("unit_id", "word_start", "word_end", "n_words", "unit_words", "tokens_sha256", "matched_words",
           "coverage", "size_ratio", "new_sha256")


def verify(plan: dict, evidence: list[dict], cache_dir: Path | None = None) -> tuple[int, list[str]]:
    cache_dir = cache_dir or mb.p1.CACHE
    bad: list[str] = []
    ok = 0
    prow = {r["id"]: r for r in plan["rows"]}
    cache_manifest = json.loads((cache_dir / "manifest.json").read_text(encoding="utf8"))
    snaps: dict[str, mb.Snapshot] = {}
    for r in plan["rows"]:
        if r["id"] not in {e["id"] for e in evidence}:
            bad.append(f"{r['id']}: plan row has no evidence")
    for e in evidence:
        rid = e["id"]
        r = prow.get(rid)
        if r is None:
            bad.append(f"{rid}: evidence without a plan row")
            continue
        if e.get("norm_version") != mb.NORM_VERSION or e.get("match_version") != mb.MATCH_VERSION:
            bad.append(f"{rid}: normaliser/matcher version {e.get('norm_version')}/{e.get('match_version')}")
            continue
        epi = e["epi"]
        if epi not in snaps:
            f = cache_dir / e["snapshot_file"]
            if not f.exists():
                bad.append(f"{rid}: snapshot {e['snapshot_file']} missing")
                continue
            snaps[epi] = mb.Snapshot(f)
        snap = snaps[epi]
        want = cache_manifest.get(epi, {}).get("sha256")
        if not (snap.sha256 == e["snapshot_sha256"] == plan["manifest"].get(epi, {}).get("sha256") == want):
            bad.append(f"{rid}: snapshot sha256 differs from evidence/plan/cache manifest")
            continue
        # the applier writes plan source as citation_source_path: it must be exactly the verified unit's URL
        if (r.get("source") != f"{mb.p1.LAW_URL.format(epi=epi)}#{e['unit_id']}" or r.get("epi") != epi
                or r.get("law_date") != e.get("law_date")):
            bad.append(f"{rid}: plan source/epi/law_date differ from the verified unit")
            continue
        if mb.md5(r["old_text"]) != e["old_md5"] or r["md5"] != e["old_md5"]:
            bad.append(f"{rid}: old text md5 does not match the evidence")
            continue
        if r["rule"] != e["rule"] or r["unit_id"] != e["unit_id"]:
            bad.append(f"{rid}: plan rule/unit differ from evidence")
            continue
        uid = e["unit_id"]
        if uid not in snap.units:
            bad.append(f"{rid}: unit {uid} not in snapshot")
            continue
        row = mb.norm_tokens(r["old_text"])
        ut = snap.tokens[uid]
        new_ref = r.get("new_ref_number")
        if new_ref is not None:   # ref-fix row: the label is derived from the unit id, never trusted from the plan
            if (rf.unit_label(uid) != new_ref or mb.ref_full(new_ref)[0] != uid or rf.state_clause_label(new_ref) != new_ref
                    or r.get("old_ref_number") != r.get("ref_number") or e.get("new_ref_number") != new_ref
                    or e.get("old_ref_number") != r.get("old_ref_number") or e.get("ref_number") != new_ref):
                bad.append(f"{rid}: new_ref_number {new_ref!r} is not the grammar label of unit {uid} / fails display check")
                continue
            f = rf.find_unit(r["old_text"], snap)   # the unit found without any label must be this unit
            if f.get("unit") != uid:
                bad.append(f"{rid}: label-blind unit search gives {f.get('unit') or f.get('reason')}, plan says {uid}")
                continue
        d = mb.decide(r["old_text"], new_ref if new_ref is not None else r.get("ref_number"), snap)
        want_verdict = e["rule"]
        if d["verdict"] != want_verdict:
            bad.append(f"{rid}: re-derived verdict {d['verdict']} ({d.get('reason')}), evidence says {want_verdict}")
            continue
        diff = [k for k in CHECKED if k in e and (d.get("unit") if k == "unit_id" else d.get(k)) != e[k]]
        if diff:
            bad.append(f"{rid}: evidence fields differ from re-derivation: {diff}")
            continue
        if e["rule"] == "accept":
            if ut[e["word_start"]:e["word_end"]] != row or e["word_end"] - e["word_start"] != len(row):
                bad.append(f"{rid}: offsets do not select the row's words in unit {uid}")
                continue
            if r.get("new_text") is not None:
                bad.append(f"{rid}: accept row carries new_text")
                continue
        else:
            new = snap.units[uid].text
            if r["new_text"] != new or mb.sha256(new) != e["new_sha256"]:
                bad.append(f"{rid}: new_text is not the snapshot unit text")
                continue
            if e["coverage"] < mb.COVERAGE_MIN or len(ut) > mb.SIZE_MAX * len(row):
                bad.append(f"{rid}: coverage/size outside the rule")
                continue
            if mb.numbers_for_check(r["old_text"], snap, uid) - mb.rc.numbers(new):
                bad.append(f"{rid}: a number of the old text is missing from the new text")
                continue
        ok += 1
    return ok, bad


def main(argv=None) -> int:
    a = sys.argv[1:] if argv is None else argv
    if len(a) != 2:
        print(__doc__)
        return 2
    plan = json.loads(Path(a[0]).read_text(encoding="utf8"))
    evidence = [json.loads(line) for line in Path(a[1]).read_text(encoding="utf8").splitlines() if line.strip()]
    ok, bad = verify(plan, evidence)
    by = {}
    for e in evidence:
        by[e["rule"]] = by.get(e["rule"], 0) + 1
    print(f"evidence rows {len(evidence)} {by}  verified {ok}  mismatches {len(bad)}")
    for b in bad[:20]:
        print("  MISMATCH", b)
    if bad:
        return 1
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
