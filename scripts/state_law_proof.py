#!/usr/bin/env python3
"""Prove each served state-law rule (SEPP rows, source_council IS NULL) against the instrument in force.

prior-art-checked: reuse not viable -- scripts/citation_proof.py + dcp_citation_status.py judge a
council DCP clause number against the council's PDF page and skip rows with no source_council;
scripts/law_change_diff.py is the only reader of legislation.nsw.gov.au HTML and only diffs two
dates. This reuses its paragraph parser (law_change_diff.paragraphs) and adds the verbatim test.
Closes the state-law half of DQ-145 (outreach claim OC-20).

legislation.nsw.gov.au answers 403 to local machines. Fetch each instrument ONCE from the Fly app
plotdetect-legislation-monitor (see FETCH_HELP) into data/law_text_cache/<epi>_<date>.html; this
script only reads that cache and the database (read-only session).

Verdict per candidate row (provision_text, any leading '# heading' line removed, normalised):
  proven          the whole text occurs verbatim in the normalised instrument. Tier 'exact', else
                  'relaxed' = the same after removing whitespace, a hyphen at a line break, and
                  folding unicode dashes/quotes (encoding differences only; no word is altered).
  partial         not found whole, but >= 90% of its 8-word runs occur in the instrument.
  text_not_found  anything else (stale or garbled): DQ-88 candidates.
derived_clause = nearest preceding section/clause heading of the (unique) match, e.g. '3B.42'.
Several different clauses (a short sentence repeated) => derived_clause empty, clause_candidates set.

    python scripts/state_law_proof.py                 # dry run: counts, examples, CSV
    python scripts/state_law_proof.py --write-plan    # + data/state_law_proof_plan_<date>.json
Apply the plan with scripts/apply_state_law_proof.py.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import html
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from law_change_diff import paragraphs  # noqa: E402  (shared parser: tags->space, collapse, no space before , . ; :)

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "law_text_cache"
MANIFEST = CACHE / "manifest.json"
FETCH_HELP = ("fly ssh console -a plotdetect-legislation-monitor -C \"python3 -c \\\"import urllib.request;"
              "print(urllib.request.urlopen(urllib.request.Request('https://legislation.nsw.gov.au/view/whole/"
              "html/inforce/current/<epi>',headers={'User-Agent':'Mozilla/5.0'})).read().decode())\\\"\"")
LAW_URL = "https://legislation.nsw.gov.au/view/whole/html/inforce/current/{epi}"

# Title words in a document_id -> instrument (epi ids are instrument_registry.pco_instrument_id).
INSTRUMENTS = [
    (r"Exempt_and_Complying", "epi-2008-0572"),
    (r"Transport_and_Infrastructure", "epi-2021-0732"),
    (r"Biodiversity_and_Conservation", "epi-2021-0722"),
    (r"Industry_and_Employment", "epi-2021-0723"),
    (r"Planning_Systems", "epi-2021-0724"),
    (r"Resilience_and_Hazards", "epi-2021-0730"),
    (r"Primary_Production", "epi-2021-0729"),
    (r"Sustainable_Buildings", "epi-2022-0521"),
    (r"Housing", "epi-2021-0714"),
]
CANDIDATES_SQL = (
    "SELECT id, document_id, ref_number, provision_text, md5(provision_text) FROM regulatory_provisions "
    "WHERE is_current AND v2_is_actionable AND (v2_provision_type IS NULL OR v2_provision_type <> 'TOC') "
    "AND source_council IS NULL AND NOT (COALESCE(citation_status,'') IN ('proven','imprecise') "
    "OR COALESCE(page_check,'') IN ('on_page','moved')) ORDER BY id"
)

# A section/clause heading: '3B.42 Privacy screens ...', '26 Must be used ...' (heading and body can share a
# paragraph in the HTML, so no length cap). Notes ('s 25: Am 2022'), list items and 'Note 1.' do not match.
CLAUSE = re.compile(r"^(\d+[A-Z]{0,3}(?:\.\d+[A-Z]{0,3})?)\s+(?=[A-Z(])")
SCHEDULE = re.compile(r"^Schedule (\d+[A-Z]{0,2})\b")
SHINGLE = 8
PARTIAL_AT = 0.90


def normalise(text: str) -> str:
    """Tags -> spaces, unescape, collapse whitespace, no space before , . ; :  (the established method)."""
    t = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r" ([,.;:])", r"\1", t)


def strip_heading(text: str) -> str:
    """Drop a leading '# ...' first line (the extractor's own title line)."""
    t = (text or "").lstrip()
    if t.startswith("#"):
        nl = t.find("\n")
        return t[nl + 1:] if nl != -1 else ""
    return text or ""


_FOLD = str.maketrans({"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
                       "‘": "'", "’": "'", "“": '"', "”": '"', " ": " "})


def squash(text: str) -> str:
    """Relaxed form: hyphen at a line break joined, unicode dash/quote folded, ALL whitespace removed."""
    t = re.sub(r"(?<=\w)-[ \t]*\n[ \t]*(?=\w)", "", text)  # before whitespace is collapsed
    return re.sub(r"\s+", "", normalise(t).translate(_FOLD))


def tokens(text: str) -> list[str]:
    return normalise(text).translate(_FOLD).split()


def instrument_for(document_id: str) -> str | None:
    for pat, epi in INSTRUMENTS:
        if re.search(pat, document_id or ""):
            return epi
    return None


class Law:
    """One instrument: exact string, squashed string, per-paragraph clause index, 8-word run set."""

    def __init__(self, paras: list[str]):
        self.exact_starts, self.squash_starts = [], []
        self.clauses: list[str] = []  # clause label in force at each paragraph
        squash_parts = []
        clause, sched = "", ""
        pos_e = pos_s = 0
        for p in paras:
            if len(p) < 160 and (m := SCHEDULE.match(p)):
                sched, clause = f"Schedule {m.group(1)}", ""
            elif m := CLAUSE.match(p):
                clause = m.group(1) if not sched else f"{sched} cl {m.group(1)}"
            self.clauses.append(clause)
            self.exact_starts.append(pos_e)
            self.squash_starts.append(pos_s)
            sp = squash(p)
            squash_parts.append(sp)
            pos_e += len(p) + 1
            pos_s += len(sp)
        self.exact = " ".join(paras)
        self.squashed = "".join(squash_parts)
        words = [w for p in paras for w in tokens(p)]
        self.runs = {tuple(words[i:i + SHINGLE]) for i in range(max(0, len(words) - SHINGLE + 1))}

    def _clauses_at(self, hay: str, needle: str, starts: list[int]) -> tuple[int, set[str]]:
        found, i = 0, hay.find(needle)
        labels: set[str] = set()
        while i != -1 and found < 50:
            found += 1
            labels.add(self.clauses[bisect.bisect_right(starts, i) - 1])
            i = hay.find(needle, i + 1)
        return found, labels

    def prove(self, raw_text: str) -> dict:
        body = strip_heading(raw_text)
        norm = normalise(body)
        if not norm:
            return {"status": "text_not_found", "tier": "empty", "clause": "", "candidates": []}
        n, labels = self._clauses_at(self.exact, norm, self.exact_starts)
        tier = "exact"
        if not n:
            sq = squash(body)
            n, labels = self._clauses_at(self.squashed, sq, self.squash_starts) if sq else (0, set())
            tier = "relaxed"
        if n:
            labels.discard("")
            cl = next(iter(labels)) if len(labels) == 1 else ""
            return {"status": "proven", "tier": tier, "clause": cl, "candidates": sorted(labels)[:6]}
        words = tokens(body)
        runs = [tuple(words[i:i + SHINGLE]) for i in range(len(words) - SHINGLE + 1)]
        if runs and sum(r in self.runs for r in runs) / len(runs) >= PARTIAL_AT:
            return {"status": "partial", "tier": "runs", "clause": "", "candidates": []}
        return {"status": "text_not_found", "tier": "", "clause": "", "candidates": []}


def ref_clause(ref_number: str | None) -> str | None:
    """A clause number stored in ref_number ('Section 86(2)', 'Clause 21') or None ('provision_2344')."""
    m = re.match(r"^(?:Section|Clause|cl|s)\s*(\d+[A-Z]{0,3}(?:\.\d+[A-Z]{0,3})?)", ref_number or "", re.I)
    return m.group(1) if m else None


def latest_cache(epi: str) -> Path | None:
    files = sorted(CACHE.glob(f"{epi}_*.html"))
    return files[-1] if files else None


def load_law(epi: str, manifest: dict) -> tuple[Law, str]:
    f = latest_cache(epi)
    if f is None:
        raise SystemExit(f"no cache for {epi}; fetch once from the Fly app:\n  {FETCH_HELP}")
    raw = f.read_bytes()
    manifest[epi] = {"file": f.name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                     "source": LAW_URL.format(epi=epi)}
    return Law(paragraphs(raw.decode("utf-8", errors="replace"))), f.stem.rpartition("_")[2]


def connect():
    import psycopg2
    envf = ROOT / ".env"
    if not os.environ.get("DATABASE_URL"):
        for cand in (envf, *[p / ".env" for p in ROOT.parents[:4]]):
            if cand.exists():
                for line in cand.read_text(encoding="utf8").splitlines():
                    if line.startswith("DATABASE_URL="):
                        os.environ["DATABASE_URL"] = line.partition("=")[2].strip().strip("\"'")
                        break
    return psycopg2.connect(os.environ["DATABASE_URL"], options="-c default_transaction_read_only=on")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Prove served state-law rules against the instrument in force")
    ap.add_argument("--write-plan", action="store_true", help="also write data/state_law_proof_plan_<date>.json")
    ap.add_argument("--date", default=None, help="output date stamp (default: today)")
    args = ap.parse_args(argv)
    from datetime import date
    stamp = args.date or date.today().isoformat()

    conn = connect()
    cur = conn.cursor()
    cur.execute(CANDIDATES_SQL)
    rows = cur.fetchall()
    conn.close()
    by_epi: dict[str, list] = defaultdict(list)
    unmapped = Counter()
    for r in rows:
        epi = instrument_for(r[1])
        if epi:
            by_epi[epi].append(r)
        else:
            unmapped[r[1]] += 1
    print(f"candidates: {len(rows)}  mapped: {sum(map(len, by_epi.values()))}  unmapped: {sum(unmapped.values())}")

    manifest: dict = {}
    results, counts, examples = [], defaultdict(Counter), defaultdict(list)
    for epi in sorted(by_epi):
        law, law_date = load_law(epi, manifest)
        for rid, doc, ref, text, md5 in by_epi[epi]:
            v = law.prove(text)
            rc = ref_clause(ref)
            agrees = "na" if not rc or not v["clause"] else ("yes" if rc.upper() == v["clause"].upper() else "no")
            results.append({"id": rid, "document_id": doc, "epi": epi, "law_date": law_date, "status": v["status"],
                            "tier": v["tier"], "derived_clause": v["clause"],
                            "clause_candidates": ";".join(v["candidates"]), "ref_number": ref, "ref_agrees": agrees,
                            "md5": md5, "head": re.sub(r"\s+", " ", text or "")[:120]})
            counts[epi][v["status"]] += 1
            if len(examples[v["status"]]) < 10:
                examples[v["status"]].append(results[-1])

    print(f"\n{'instrument':16}{'proven':>8}{'partial':>9}{'not_found':>11}{'total':>8}")
    tot = Counter()
    for epi in sorted(counts):
        c = counts[epi]
        tot.update(c)
        print(f"{epi:16}{c['proven']:8}{c['partial']:9}{c['text_not_found']:11}{sum(c.values()):8}")
    print(f"{'ALL':16}{tot['proven']:8}{tot['partial']:9}{tot['text_not_found']:11}{sum(tot.values()):8}")
    tiers = Counter(r["tier"] for r in results if r["status"] == "proven")
    clause = Counter("unique" if r["derived_clause"] else ("ambiguous" if r["clause_candidates"] else "none")
                     for r in results if r["status"] == "proven")
    agree = Counter(r["ref_agrees"] for r in results if r["status"] == "proven")
    print(f"\nproven tiers: {dict(tiers)}  derived_clause: {dict(clause)}  ref_number agrees: {dict(agree)}")
    short = sum(1 for r in results if r["status"] == "proven" and len(r["head"].split()) < SHINGLE)
    print(f"proven rows under {SHINGLE} words (weak evidence, listed in the CSV by head): {short}")
    if unmapped:
        print("\nUNMAPPED document_ids (left out):")
        for d, n in unmapped.most_common():
            print(f"  {n:5}  {d}")
    for st in ("proven", "partial", "text_not_found"):
        print(f"\n--- {st}: {len(examples[st])} examples ---")
        for e in examples[st]:
            print(f"  {e['id']} [{e['epi']} {e['tier']} cl={e['derived_clause'] or '-'}] {e['head'][:100]}")

    out = ROOT / "data" / f"state_law_proof_{stamp}.csv"
    cols = ["id", "document_id", "epi", "status", "derived_clause", "head"]
    with out.open("w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf8")
    print(f"\nwrote {out.relative_to(ROOT)} ({len(results)} rows) and {MANIFEST.relative_to(ROOT)}")

    if args.write_plan:
        plan = {"generated": stamp, "set": {"citation_status": "proven"},
                "note": "Only citation_status (+ citation_source_path/citation_checked_at) is written. No clause "
                        "column is proposed: the site reads none for state rows.",
                "manifest": manifest,
                "rows": [{"id": r["id"], "md5": r["md5"], "epi": r["epi"], "law_date": r["law_date"],
                          "source": LAW_URL.format(epi=r["epi"]), "derived_clause": r["derived_clause"] or None}
                         for r in results if r["status"] == "proven"]}
        p = ROOT / "data" / f"state_law_proof_plan_{stamp}.json"
        p.write_text(json.dumps(plan, indent=1) + "\n", encoding="utf8")
        print(f"wrote {p.relative_to(ROOT)} ({len(plan['rows'])} rows to set proven)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
