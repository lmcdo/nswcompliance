#!/usr/bin/env python3
"""State-law proof, pass 4: deterministic, evidence-recording proof of the still-unproven served state-law rows.

prior-art-checked: extends scripts/state_law_proof.py (candidate query, instrument map, snapshot manifest) with the
matchers in scripts/state_law_evidence.py; read-only database session; apply with apply_state_law_proof.py
--evidence; re-check with verify_state_law_evidence.py. No model call anywhere.

    python scripts/state_law_proof4.py                    # counts, 5 examples per rule, writes plan + evidence
    python scripts/state_law_proof4.py --pdf-dir DIR      # rule 3: old PDFs by file name (none in R2: page PNGs only)

Writes data/state_law_proof_plan4_<date>.json (apply_state_law_proof.py format + `evidence` per row),
data/state_law_evidence_<date>.jsonl (the verifier's input) and data/state_law_proof4_unproven_<date>.csv.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import state_law_evidence as ev  # noqa: E402
import state_law_proof as p1  # noqa: E402

ROOT = p1.ROOT
SQL = p1.CANDIDATES_SQL.replace("md5(provision_text) FROM", "md5(provision_text), pdf_page, pdf_source_file FROM")


def pdf_page_text(pdf_dir: Path | None, name: str | None, page: int | None) -> tuple[dict, str | None, str]:
    """(pdf info, page text | None, reason). Only a PDF found by file name under --pdf-dir counts."""
    if not name or not page:
        return {}, None, "no_pdf_page_stored"
    if pdf_dir is None or not (pdf_dir / name).is_file():
        return {}, None, "no_old_pdf"
    import fitz
    f = pdf_dir / name
    with fitz.open(f) as doc:
        if page > len(doc):
            return {}, None, "pdf_page_out_of_range"
        text = doc[page - 1].get_text()
    return {"file": name, "sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "page": page}, text, ""


def load_manifest() -> dict:
    return json.loads(p1.MANIFEST.read_text(encoding="utf8"))


def run(rows, manifest, cache: Path, pdf_dir: Path | None):
    """-> (proven [(row, evidence)], unproven [(row, reason)]). Pure over its inputs (rows are tuples)."""
    snaps, proven, unproven = {}, [], []
    for r in rows:
        rid, doc, ref, text, md5, page, pdf_name = r
        epi = p1.instrument_for(doc)
        if not epi:
            unproven.append((r, "unmapped_instrument"))
            continue
        if epi not in snaps:
            snaps[epi] = ev.load_snapshot(epi, manifest[epi]["sha256"], cache)
        snap = snaps[epi]
        rn = ev.row_norm(text)
        v = ev.prove(snap, rn)
        if v["status"] == "proven":
            proven.append((r, rn, v))
        elif v["status"] == "ambiguous":
            info, ptext, why = pdf_page_text(pdf_dir, pdf_name, page)
            if ptext is None:
                unproven.append((r, "occurs_in_several_places;" + why))
                continue
            v3 = ev.prove_by_page_heading(snap, rn, ptext)
            if v3 is None:
                unproven.append((r, "occurs_in_several_places;page_heading_does_not_single_one_out"))
            else:
                v3["pdf"].update(info)
                proven.append((r, rn, v3))
        else:
            unproven.append((r, v["reason"]))
    return proven, unproven


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--pdf-dir", default=None)
    args = ap.parse_args(argv)
    stamp = args.date or date.today().isoformat()
    conn = p1.connect()
    cur = conn.cursor()
    cur.execute(SQL)
    rows = cur.fetchall()
    conn.close()
    manifest = load_manifest()
    proven, unproven = run(rows, manifest, ev.CACHE, Path(args.pdf_dir) if args.pdf_dir else None)
    print(f"candidates: {len(rows)}  proven: {len(proven)}  unproven: {len(unproven)}")
    by_rule = defaultdict(list)
    for r, rn, v in proven:
        by_rule[v["rule"]].append((r, rn, v))
    for rule, name in ((1, "EXCERPT"), (2, "ADJACENT-SPAN"), (3, "PART-DISAMBIGUATION")):
        items = by_rule.get(rule, [])
        print(f"\nRULE {rule} {name}: {len(items)}")
        for r, rn, v in items[:5]:
            u = v["units"]
            print(f"  id={r[0]} epi={v['epi']} units={[x['id'] for x in u]} "
                  f"offsets={[(x['start'], x['end']) for x in u]} tier={v['tier']}\n    old: {rn[:110]}")
    print("\nRULE 4 UNPROVEN by reason:")
    for why, n in Counter(w for _, w in unproven).most_common():
        print(f"  {n:5} {why}")

    rows_out, lines = [], []
    for r, rn, v in sorted(proven, key=lambda x: x[0][0]):
        rid, doc, ref, text, md5, page, pdf_name = r
        epi = v["epi"]
        evd = {k: x for k, x in v.items() if k not in ("status", "spans")}
        rows_out.append({"id": rid, "md5": md5, "epi": epi, "law_date": manifest[epi]["file"].rpartition("_")[2][:10],
                         "source": f"{p1.LAW_URL.format(epi=epi)}#{v['units'][0]['id']}", "derived_clause": None,
                         "evidence": evd})
        lines.append(json.dumps({"id": rid, "text_md5": md5, "row_norm": rn, "row_norm_md5": ev.md5(rn),
                                 "evidence": evd}, ensure_ascii=False, sort_keys=True))
    plan = {"generated": stamp, "set": {"citation_status": "proven"},
            "note": "Pass 4: rules 1-3 of scripts/state_law_evidence.py. Only citation_status (+ source path / "
                    "checked_at) is written; evidence lives in the committed JSONL, keyed by id + text md5.",
            "manifest": {e: {k: manifest[e][k] for k in ("file", "sha256", "bytes", "source")}
                         for e in sorted({x[2]["epi"] for x in proven})},
            "evidence_file": f"data/state_law_evidence_{stamp}.jsonl", "rows": rows_out}
    (ROOT / "data" / f"state_law_proof_plan4_{stamp}.json").write_text(json.dumps(plan, indent=1) + "\n", encoding="utf8")
    (ROOT / "data" / f"state_law_evidence_{stamp}.jsonl").write_text("".join(x + "\n" for x in lines), encoding="utf8")
    with (ROOT / "data" / f"state_law_proof4_unproven_{stamp}.csv").open("w", newline="", encoding="utf8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "document_id", "reason"])
        for r, why in sorted(unproven, key=lambda x: x[0][0]):
            w.writerow([r[0], r[1], why])
    print(f"\nwrote plan4 ({len(rows_out)} rows), evidence jsonl, unproven csv for {stamp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
