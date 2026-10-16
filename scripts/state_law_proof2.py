#!/usr/bin/env python3
"""State-law proof, pass 2: deterministic triage of the rows pass 1 (state_law_proof.py) could not prove.

prior-art-checked: extends scripts/state_law_proof.py (imports its candidate query, parser and cache); no model
reads anything.

For each still-unproven state row (same candidate query as pass 1, so already-proven rows drop out):
  proven             verbatim in today's instrument after a stronger normaliser applied to BOTH sides
                     (NFKC: superscripts/nbsp; dashes+quotes folded; html tags inside stored text stripped;
                     markdown emphasis/table pipes removed; all whitespace removed) and >= MIN_WORDS words.
  amended            not in today's law, but verbatim in the instrument as in force on the row's last_updated /
                     created_at date: DQ-88 law-change candidate (text NOT changed here).
  paraphrase         share of the row's 5-word runs found in today's or the older law < 0.5: not the law's words.
  partial_unresolved 0.5 <= share < 0.9.      partial_high  share >= 0.9 but not verbatim (kept apart).
  short_unproven     verbatim but under MIN_WORDS words (not evidence).
Point-in-time versions: one fetch per instrument per distinct date, cached in data/law_text_cache/pit/, fetched
through the Fly app (local fetch is 403) when --fetch is given.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import random
import re
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import state_law_proof as p1  # noqa: E402
from law_change_diff import paragraphs  # noqa: E402

ROOT = p1.ROOT
PIT = p1.CACHE / "pit"
PIT_URL = "https://legislation.nsw.gov.au/view/whole/html/inforce/{day}/{epi}"
MIN_WORDS = 8
RUN = 5
PARAPHRASE_BELOW = 0.5
PARTIAL_HIGH_AT = 0.9

_FOLD = str.maketrans({"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-", "‘": "'", "’": "'",
                       "“": '"', "”": '"', "´": "'", "`": "'"})


def prep(text: str) -> str:
    """Common front half of the normaliser: html tags -> space, entities, NFKC, fold dashes/quotes, drop markdown."""
    t = re.sub(r"<[^>]+>", " ", text or "")
    t = html.unescape(t)
    t = re.sub(r"(?<=\w)-[ \t]*\n[ \t]*(?=\w)", "", t)      # ASCII hyphen at a line break, BEFORE folding so an
    t = unicodedata.normalize("NFKC", t).translate(_FOLD)   # em dash ending a line survives.  ² -> 2, nbsp -> space
    for ch in "*_#":
        t = t.replace(chr(92) + ch, ch)                      # markdown escapes such as backslash-star
    t = re.sub(r"[*_`]{1,3}", "", t)                         # markdown emphasis
    t = re.sub(r"^\s*#+\s*", "", t, flags=re.M)              # markdown heading marks
    return t.replace("|", " ")                               # markdown table pipes


def squash2(text: str) -> str:
    """Whitespace-free comparison form; BOTH sides go through this."""
    return re.sub(r"\s+", "", prep(text))


def words2(text: str) -> list[str]:
    """Word tokens for run-share: lowercase alphanumerics, so 'm 2' / 'm2' and list marks do not matter."""
    return re.findall(r"[a-z0-9]+", prep(text).lower())


class Doc:
    """One instrument version: squashed text + 5-word run set."""

    def __init__(self, paras: list[str]):
        self.squashed = "".join(squash2(x) for x in paras)
        w = [t for x in paras for t in words2(x)]
        self.runs = {tuple(w[i:i + RUN]) for i in range(max(0, len(w) - RUN + 1))}

    def contains(self, text: str) -> bool:
        s = squash2(text)
        return bool(s) and s in self.squashed

    def share(self, text: str) -> tuple[int, int]:
        w = words2(text)
        runs = [tuple(w[i:i + RUN]) for i in range(len(w) - RUN + 1)]
        return sum(r in self.runs for r in runs), len(runs)


def classify(text: str, today: Doc, older: Doc | None) -> dict:
    """Pure classifier. `older` is the point-in-time instrument or None."""
    body = p1.strip_heading(text)
    n_words = len(words2(body))
    if not squash2(body):
        return {"status": "paraphrase", "share": 0.0, "words": 0}
    if today.contains(body):
        return {"status": "proven" if n_words >= MIN_WORDS else "short_unproven", "share": 1.0, "words": n_words}
    if older is not None and older.contains(body):
        return {"status": "amended" if n_words >= MIN_WORDS else "short_unproven", "share": 1.0, "words": n_words}
    hit_t, tot = today.share(body)
    if tot == 0:  # fewer than RUN words and not verbatim: no basis to call it a paraphrase
        return {"status": "partial_unresolved", "share": 0.0, "words": n_words}
    hit_o = older.share(body)[0] if older else 0
    share = max(hit_t, hit_o) / tot
    if share < PARAPHRASE_BELOW:
        st = "paraphrase"
    elif share < PARTIAL_HIGH_AT:
        st = "partial_unresolved"
    else:
        st = "partial_high"
    return {"status": st, "share": round(share, 3), "words": n_words}


def fetch_pit(epi: str, day: str) -> Path | None:
    f = PIT / f"{epi}_{day}.html"
    if f.exists() and f.stat().st_size > 10000:
        return f
    cmd = ["fly", "ssh", "console", "-a", "plotdetect-legislation-monitor", "-C",
           "python3 -c \"import urllib.request;print(urllib.request.urlopen(urllib.request.Request("
           f"'{PIT_URL.format(day=day, epi=epi)}',headers={{'User-Agent':'Mozilla/5.0'}})).read().decode())\""]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    if r.returncode or len(r.stdout) < 10000:
        print(f"  fetch failed {epi} {day}: rc={r.returncode} len={len(r.stdout)} {r.stderr[-200:]}")
        return None
    PIT.mkdir(parents=True, exist_ok=True)
    f.write_text(r.stdout, encoding="utf-8")
    return f


def row_day(last_updated, created_at) -> str:
    d = last_updated or created_at
    return d.date().isoformat() if hasattr(d, "date") else str(d)[:10]


SQL = p1.CANDIDATES_SQL.replace("md5(provision_text) FROM", "md5(provision_text), last_updated, created_at FROM")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="fetch missing point-in-time versions via the Fly app")
    ap.add_argument("--date", default=None)
    args = ap.parse_args(argv)
    stamp = args.date or date.today().isoformat()
    conn = p1.connect()
    cur = conn.cursor()
    cur.execute(SQL)
    rows = cur.fetchall()
    conn.close()
    manifest: dict = {}
    by_epi = defaultdict(list)
    unmapped: Counter = Counter()
    for r in rows:
        epi = p1.instrument_for(r[1])
        if epi:
            by_epi[epi].append(r)
        else:
            unmapped[r[1]] += 1
    print(f"candidates: {len(rows)} mapped: {sum(map(len, by_epi.values()))} unmapped: {sum(unmapped.values())}")

    results, texts, missing_pit = [], {}, []
    for epi in sorted(by_epi):
        f = p1.latest_cache(epi)
        raw = f.read_bytes()
        today = Doc(paragraphs(raw.decode("utf-8", errors="replace")))
        law_date = f.stem.rpartition("_")[2]
        manifest[epi] = {"file": f.name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                         "source": p1.LAW_URL.format(epi=epi)}
        pending = []
        for rid, doc, ref, text, md5, lu, ca in by_epi[epi]:
            c = classify(text, today, None)  # cheap: today's law only; the rest need an older version
            if c["status"] in ("proven", "short_unproven"):
                results.append((rid, doc, epi, law_date, md5, c, ""))
                texts[rid] = text
            else:
                pending.append((rid, doc, md5, text, row_day(lu, ca)))
        days = sorted({d for *_, d in pending})
        olds = {}
        for d in days:
            f2 = PIT / f"{epi}_{d}.html"
            if not f2.exists() and args.fetch:
                f2 = fetch_pit(epi, d)
            if f2 and f2.exists():
                olds[d] = Doc(paragraphs(f2.read_text(encoding="utf-8", errors="replace")))
            else:
                missing_pit.append((epi, d))
        for rid, doc, md5, text, d in pending:
            c = classify(text, today, olds.get(d))
            c["pit"] = d if d in olds else "unavailable"
            results.append((rid, doc, epi, law_date, md5, c, d))
            texts[rid] = text
        print(f"{epi}: {len(by_epi[epi])} rows, {len(days)} dates, {len(olds)} versions loaded")
    if missing_pit:
        print("MISSING point-in-time versions (rerun with --fetch):", len(set(missing_pit)), sorted(set(missing_pit))[:10])

    print("\nstatus counts:", dict(Counter(c["status"] for *_, c, _ in results)))
    per = defaultdict(Counter)
    for rid, doc, epi, ld, md5, c, d in results:
        per[epi][c["status"]] += 1
    for e in sorted(per):
        print(f"  {e}: {dict(per[e])}")

    import csv
    prev = {}
    pc = ROOT / "data" / "state_law_proof_2026-10-16.csv"
    if pc.exists():
        prev = {int(r["id"]): r for r in csv.DictReader(pc.open(encoding="utf8"))}
    out = ROOT / "data" / f"state_law_proof_pass2_{stamp}.csv"
    with out.open("w", newline="", encoding="utf8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "document_id", "epi", "pass1_status", "status", "run_share", "words", "pit_date", "head"])
        for rid, doc, epi, ld, md5, c, d in results:
            w.writerow([rid, doc, epi, (prev.get(rid) or {}).get("status") or "", c["status"], c["share"], c["words"],
                        c.get("pit") or "", re.sub(r"\s+", " ", texts[rid])[:120]])
    print(f"wrote {out.relative_to(ROOT)}")

    plan = {"generated": stamp, "set": {"citation_status": "proven"},
            "note": "Pass 2: verbatim after the stronger normaliser (state_law_proof2.py), >= 8 words. Only "
                    "citation_status (+ source path/checked_at) is written.",
            "manifest": manifest,
            "rows": [{"id": rid, "md5": md5, "epi": epi, "law_date": ld, "source": p1.LAW_URL.format(epi=epi),
                      "derived_clause": None}
                     for rid, doc, epi, ld, md5, c, d in results if c["status"] == "proven"]}
    pp = ROOT / "data" / f"state_law_proof_plan2_{stamp}.json"
    pp.write_text(json.dumps(plan, indent=1) + "\n", encoding="utf8")
    para = [{"id": rid, "document_id": doc, "run_share": c["share"], "text": texts[rid]}
            for rid, doc, epi, ld, md5, c, d in results if c["status"] == "paraphrase"]
    pf = ROOT / "data" / f"state_law_paraphrase_{stamp}.json"
    pf.write_text(json.dumps(para, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    am = [{"id": rid, "document_id": doc, "epi": epi, "in_force_date": d, "text": texts[rid]}
          for rid, doc, epi, ld, md5, c, d in results if c["status"] == "amended"]
    af = ROOT / "data" / f"state_law_amended_{stamp}.json"
    af.write_text(json.dumps(am, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    print(f"wrote plan2 ({len(plan['rows'])} rows), paraphrase ({len(para)}), amended ({len(am)})")
    print("amended by instrument:", dict(Counter(a["epi"] for a in am)))
    rnd = random.Random(1)
    for st in ("paraphrase", "partial_unresolved"):
        pool = [(rid, c, texts[rid]) for rid, doc, epi, ld, md5, c, d in results if c["status"] == st]
        print(f"\n--- {st}: {len(pool)} ---")
        for rid, c, t in rnd.sample(pool, min(15, len(pool))):
            print(f"  {rid} share={c['share']} :: {t[:140].replace(chr(10), ' ')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
