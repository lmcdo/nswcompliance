#!/usr/bin/env python3
"""Prove served LEP rows (instrument_registry type 'lep') verbatim against the instrument in force.

prior-art-checked: extends scripts/state_law_proof.py + state_law_proof2.py (merged #1304), which select only
source_council IS NULL rows. This reuses their parser, cache, Law (derived clause) and classify() unchanged and
only changes WHICH rows are candidates: any unproven served row whose document_id is the title of an
instrument_registry LEP (e.g. Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_1_50 -> epi-2022-0457).
No model reads anything. Read-only database session.

Fetch the instrument ONCE via the Fly app (legislation.nsw.gov.au 403s locally; state_law_proof.FETCH_HELP) into
data/law_text_cache/<epi>_<date>.html. --fetch also pulls point-in-time versions for the 'amended' test.

    python scripts/lep_law_proof.py [--fetch]            # CSV, plan, paraphrase and amended lists
    python scripts/lep_law_proof.py --council-remainder  # list (no fix) the unproven council DCP rows
Apply the plan with: scripts/apply_state_law_proof.py <plan> --include-registry-lep  (NOT applied here).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import state_law_proof as p1  # noqa: E402
import state_law_proof2 as p2  # noqa: E402
from law_change_diff import paragraphs  # noqa: E402

ROOT = p1.ROOT
SCOPE = "registry_lep"

# Same served/unproven definition as DQ-145 (scripts/dq_probe_live.py), without the source_council restriction.
CANDIDATES_SQL = (
    "SELECT id, document_id, ref_number, provision_text, md5(provision_text), last_updated, created_at, "
    "source_council FROM regulatory_provisions "
    "WHERE is_current AND v2_is_actionable AND (v2_provision_type IS NULL OR v2_provision_type <> 'TOC') "
    "AND NOT (COALESCE(citation_status,'') IN ('proven','imprecise') "
    "OR COALESCE(page_check,'') IN ('on_page','moved')) ORDER BY id"
)
REGISTRY_SQL = ("SELECT instrument_label, pco_instrument_id FROM instrument_registry "
                "WHERE is_active AND instrument_type = 'lep' AND pco_instrument_id IS NOT NULL")


def slug(text: str) -> str:
    """Letters/digits only, runs of anything else -> one underscore, lower case."""
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")


def build_title_map(registry: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """[(slug of instrument label, epi)] longest label first, so a longer title wins over a prefix of it."""
    return sorted(((slug(label), epi) for label, epi in registry if label and epi),
                  key=lambda t: -len(t[0]))


def lep_for(document_id: str, title_map: list[tuple[str, str]]) -> str | None:
    """The registry LEP whose title opens this document_id (on a word boundary), else None.

    A DCP document ('Inner_West_Ashfield_DCP_2016__chapter_e1') never starts with an LEP title; a SEPP is not
    in the LEP-only registry list, so it stays with state_law_proof.py.
    """
    d = slug(document_id)
    for label, epi in title_map:
        if d == label or d.startswith(label + "_"):
            return epi
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Prove served LEP rows against the instrument in force")
    ap.add_argument("--fetch", action="store_true", help="fetch missing point-in-time versions via the Fly app")
    ap.add_argument("--council-remainder", action="store_true", help="only list the unproven council DCP rows")
    ap.add_argument("--date", default=None)
    args = ap.parse_args(argv)
    stamp = args.date or date.today().isoformat()

    conn = p1.connect()
    cur = conn.cursor()
    cur.execute(REGISTRY_SQL)
    title_map = build_title_map(cur.fetchall())
    cur.execute(CANDIDATES_SQL)
    rows = cur.fetchall()
    conn.close()
    print(f"DQ-145 unproven served rows: {len(rows)}")

    by_epi: dict[str, list] = defaultdict(list)
    other = []
    for r in rows:
        epi = lep_for(r[1], title_map)
        if epi:
            by_epi[epi].append(r)
        else:
            other.append(r)
    print(f"registry-LEP rows: {sum(map(len, by_epi.values()))}  other: {len(other)}")
    if args.council_remainder:
        return remainder(other, stamp)

    manifest: dict = {}
    results, texts = [], {}
    missing_pit = []
    for epi in sorted(by_epi):
        f = p1.latest_cache(epi)
        if f is None:
            raise SystemExit(f"no cache for {epi}; fetch once from the Fly app:\n  {p1.FETCH_HELP}")
        raw = f.read_bytes()
        paras = paragraphs(raw.decode("utf-8", errors="replace"))
        law, today = p1.Law(paras), p2.Doc(paras)
        law_date = f.stem.rpartition("_")[2]
        manifest[epi] = {"file": f.name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                         "source": p1.LAW_URL.format(epi=epi)}
        pending = []
        for rid, doc, ref, text, md5, lu, ca, council in by_epi[epi]:
            texts[rid] = text
            c = p2.classify(text, today, None)
            if c["status"] in ("proven", "short_unproven"):
                results.append((rid, doc, epi, law_date, md5, council, c, "", law.prove(text)))
            else:
                pending.append((rid, doc, md5, council, text, p2.row_day(lu, ca)))
        days = sorted({d for *_, d in pending})
        olds = {}
        for d in days:
            f2 = p2.PIT / f"{epi}_{d}.html"
            if not f2.exists() and args.fetch:
                f2 = p2.fetch_pit(epi, d)
            if f2 and f2.exists():
                olds[d] = p2.Doc(paragraphs(f2.read_text(encoding="utf-8", errors="replace")))
            else:
                missing_pit.append((epi, d))
        for rid, doc, md5, council, text, d in pending:
            c = p2.classify(text, today, olds.get(d))
            c["pit"] = d if d in olds else "unavailable"
            results.append((rid, doc, epi, law_date, md5, council, c, d, {"clause": "", "candidates": []}))
        print(f"{epi}: {len(by_epi[epi])} rows, {len(days)} dates, {len(olds)} versions loaded")
    if missing_pit:
        print("MISSING point-in-time versions (rerun with --fetch):", sorted(set(missing_pit))[:10])

    print("\nstatus counts:", dict(Counter(r[6]["status"] for r in results)))
    for doc in sorted({r[1] for r in results}):
        print(f"  {doc}: {dict(Counter(r[6]['status'] for r in results if r[1] == doc))}")
    clause = Counter("unique" if r[8]["clause"] else ("ambiguous" if r[8]["candidates"] else "none")
                     for r in results if r[6]["status"] == "proven")
    print("proven derived_clause:", dict(clause))

    out = ROOT / "data" / f"lep_law_proof_{stamp}.csv"
    with out.open("w", newline="", encoding="utf8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "document_id", "epi", "source_council", "status", "derived_clause", "run_share",
                    "words", "pit_date", "head"])
        for rid, doc, epi, ld, md5, council, c, d, v in results:
            w.writerow([rid, doc, epi, council, c["status"], v["clause"], c["share"], c["words"],
                        c.get("pit") or "", re.sub(r"\s+", " ", texts[rid])[:120]])
    plan = {"generated": stamp, "scope": SCOPE, "set": {"citation_status": "proven"},
            "note": "Registry-listed LEP rows proven verbatim (>= 8 words) after the state_law_proof2 normaliser. "
                    "Only citation_status (+ source path/checked_at) is written. Apply needs --include-registry-lep.",
            "manifest": manifest,
            "rows": [{"id": rid, "md5": md5, "epi": epi, "law_date": ld, "source": p1.LAW_URL.format(epi=epi),
                      "source_council": council, "derived_clause": v["clause"] or None}
                     for rid, doc, epi, ld, md5, council, c, d, v in results if c["status"] == "proven"]}
    pp = ROOT / "data" / f"lep_law_proof_plan_{stamp}.json"
    pp.write_text(json.dumps(plan, indent=1) + "\n", encoding="utf8")
    para = [{"id": r[0], "document_id": r[1], "run_share": r[6]["share"], "text": texts[r[0]]}
            for r in results if r[6]["status"] == "paraphrase"]
    (ROOT / "data" / f"lep_law_paraphrase_{stamp}.json").write_text(
        json.dumps(para, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    am = [{"id": r[0], "document_id": r[1], "epi": r[2], "in_force_date": r[7], "text": texts[r[0]]}
          for r in results if r[6]["status"] == "amended"]
    (ROOT / "data" / f"lep_law_amended_{stamp}.json").write_text(
        json.dumps(am, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    print(f"wrote {out.name}, {pp.name} ({len(plan['rows'])} rows), paraphrase ({len(para)}), amended ({len(am)})")
    return 0


def remainder(rows: list, stamp: str) -> int:
    """List (no fix) unproven council rows by council x page_check x citation_status with 5 examples each."""
    conn = p1.connect()
    cur = conn.cursor()
    ids = [r[0] for r in rows if r[7]]
    cur.execute("SELECT id, source_council, COALESCE(page_check,'(null)'), COALESCE(citation_status,'(null)'), "
                "document_id, ref_number, left(regexp_replace(provision_text, '\\s+', ' ', 'g'), 100) "
                "FROM regulatory_provisions WHERE id = ANY(%s) ORDER BY source_council, id", (ids,))
    got = cur.fetchall()
    conn.close()
    groups: dict[tuple, list] = defaultdict(list)
    for g in got:
        groups[(g[1], g[2], g[3])].append(g)
    state = sum(1 for r in rows if not r[7])
    print(f"council rows: {len(got)}  (state-law rows, source_council NULL, left to state_law_proof: {state})")
    per_council = Counter(g[1] for g in got)
    for council, n in per_council.most_common():
        print(f"\n{council}: {n}")
        for (c, pc, cs), items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            if c != council:
                continue
            print(f"  page_check={pc} citation_status={cs}: {len(items)}")
            for it in items[:5]:
                print(f"     {it[0]} [{it[4][-45:]}] {it[5]} :: {it[6]}")
    out = ROOT / "data" / f"dq145_council_remainder_{stamp}.csv"
    with out.open("w", newline="", encoding="utf8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "source_council", "page_check", "citation_status", "document_id", "ref_number", "head"])
        w.writerows(got)
    print(f"\nwrote {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
