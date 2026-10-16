#!/usr/bin/env python3
"""Re-derive every state-law proof from its stored evidence alone. Exit 0 only if every checked record verifies.

prior-art-checked: new; nothing in scripts/ re-checks a proof from its evidence (apply_state_law_proof.py only
compares the row's md5 to the plan).

For each JSONL record written by scripts/state_law_proof4.py the verifier, with NO database and NO model:
  1  refuses unknown normaliser / parser / matcher versions;
  2  reloads the snapshot by its sha256 (never by file name) and re-parses it;
  3  checks md5(row_norm) == row_norm_md5 and that row_norm is already normalised (idempotent);
  4  checks the recorded offsets: squash(D[abs_start:abs_end]) == squash(row_norm), word-aligned, every named
     unit exists and unit.start+start .. unit.start+end is that same span;
  5  re-runs the matcher on row_norm and requires the SAME rule, units and offsets (rule 3: re-runs the container
     filter on the recorded container id; the recorded PDF page heading must contain the container heading).
Optional --db re-reads the row (read-only) and checks md5(provision_text) == text_md5.

    python scripts/verify_state_law_evidence.py data/state_law_evidence_2026-10-17.jsonl
    python scripts/verify_state_law_evidence.py EVIDENCE --sample 25 --cache data/law_text_cache
A snapshot missing from --cache is a failure (exit 1) unless --allow-missing-snapshots (then exit 2 if nothing
could be checked, so an empty check never looks green).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import state_law_evidence as ev  # noqa: E402


def verify_record(rec: dict, snaps: dict, cache: Path) -> list[str]:
    """Reasons this record does NOT verify; empty list = verified."""
    bad: list[str] = []
    e = rec.get("evidence") or {}
    for key, kind in (("normaliser", "normaliser"), ("parser", "parser"), ("matcher", "matcher")):
        if e.get(key) not in ev.KNOWN[kind]:
            return [f"unknown_{kind}_version:{e.get(key)}"]
    rnorm = rec.get("row_norm", "")
    if ev.md5(rnorm) != rec.get("row_norm_md5"):
        return ["row_norm_md5_mismatch"]
    if ev.normalise(rnorm) != rnorm:
        return ["row_norm_not_normalised"]
    if ev.n_words(rnorm) < ev.MIN_WORDS:
        return ["row_too_short"]
    key = (e.get("epi"), e.get("snapshot_sha256"))
    if key not in snaps:
        f = ev.find_snapshot_file(key[0], key[1], cache)
        snaps[key] = ev.parse_snapshot(key[0], f.read_bytes()) if f else None
    snap = snaps[key]
    if snap is None:
        return ["snapshot_missing"]
    s, t = e.get("abs_start"), e.get("abs_end")
    if not (isinstance(s, int) and isinstance(t, int) and 0 <= s < t <= len(snap.D)):
        return ["offsets_out_of_range"]
    if ev.squash(snap.D[s:t]) != ev.squash(rnorm):
        bad.append("span_text_differs_from_row")
    if not ev.word_aligned(snap.D, s, t):
        bad.append("span_not_word_aligned")
    if e.get("tier") != ("exact" if snap.D[s:t] == rnorm else "space-insensitive"):
        bad.append("tier_wrong")
    units = e.get("units") or []
    if not units:
        return bad + ["no_units"]
    for u in units:
        k = snap.by_id.get(u.get("id"))
        if k is None:
            return bad + [f"unit_absent:{u.get('id')}"]
    first, last = snap.items[snap.by_id[units[0]["id"]]], snap.items[snap.by_id[units[-1]["id"]]]
    if first.start + units[0]["start"] != s or last.start + units[-1]["end"] != t:
        bad.append("unit_offsets_do_not_match_span")
    rule = e.get("rule")
    if rule in (1, 2):
        again = ev.prove(snap, rnorm)
        if again.get("status") != "proven" or again.get("rule") != rule or again.get("units") != units \
                or (again["abs_start"], again["abs_end"]) != (s, t):
            bad.append("rederivation_differs")
    elif rule == 3:
        cid = e.get("container_id")
        again = ev.prove_in_container(snap, rnorm, cid) if cid else None
        if again is None or again.get("units") != units or (again["abs_start"], again["abs_end"]) != (s, t):
            bad.append("rederivation_differs")
        pdf = e.get("pdf") or {}
        head = ev.normalise(pdf.get("page_heading_text", ""))
        k = snap.by_id.get(cid)
        if k is None or not head or snap.items[k].heading not in head:
            bad.append("container_heading_not_on_recorded_pdf_page")
    else:
        bad.append(f"unknown_rule:{rule}")
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("evidence")
    ap.add_argument("--cache", default=str(ev.CACHE))
    ap.add_argument("--sample", type=int, default=0, help="verify every k-th record (deterministic) so ~N are checked")
    ap.add_argument("--allow-missing-snapshots", action="store_true")
    ap.add_argument("--db", action="store_true", help="also check md5(provision_text) against the live row (read-only)")
    args = ap.parse_args(argv)
    recs = [json.loads(ln) for ln in Path(args.evidence).read_text(encoding="utf8").splitlines() if ln.strip()]
    recs.sort(key=lambda r: r["id"])
    if args.sample and len(recs) > args.sample:
        step = len(recs) / args.sample
        recs = [recs[int(i * step)] for i in range(args.sample)]
    live = {}
    if args.db:
        import state_law_proof as p1
        conn = p1.connect()
        cur = conn.cursor()
        cur.execute("SELECT id, md5(provision_text) FROM regulatory_provisions WHERE id = ANY(%s)",
                    ([r["id"] for r in recs],))
        live = dict(cur.fetchall())
        conn.close()
    snaps: dict = {}
    failed, skipped, ok = [], 0, 0
    for r in recs:
        why = verify_record(r, snaps, Path(args.cache))
        if args.db and live.get(r["id"]) != r.get("text_md5"):
            why.append("db_text_md5_differs")
        if why == ["snapshot_missing"] and args.allow_missing_snapshots:
            skipped += 1
        elif why:
            failed.append((r["id"], why))
        else:
            ok += 1
    for rid, why in failed[:30]:
        print(f"FAIL id={rid}: {', '.join(why)}")
    print(f"checked={len(recs)} verified={ok} failed={len(failed)} skipped_missing_snapshot={skipped}")
    if failed:
        return 1
    if ok == 0:
        print("nothing was verified: NOT a pass")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
