#!/usr/bin/env python3
"""Marker-blind proof and re-copy of unproven served SEPP rows against the law's own structural units.

prior-art-checked: extends scripts/state_law_recopy.py (unit parser, Instrument, verbatim, numbers) and
scripts/state_law_proof.py (cache, connect, instrument_for). Those two compare after setting aside markers/ellipses/
furniture but accept a row only when 0 content words are dropped against ONE smallest unit holding >=90% of its
5-word runs; neither records word offsets, a normaliser version, or recopies rows that drop words.
No model reads or writes text: every verdict is string comparison.

User decision 2026-10-18:
  Rule 1 ACCEPT  the row's words (marker-blind normaliser sl-norm/2) are an exact contiguous word sequence of ONE
                 unit's text. Nothing is written but citation_status='proven' (+ source path / checked-at).
  Rule 2 RECOPY  the row drops words: its words appear IN ORDER in one unit (ordered subsequence, matcher sl-match/1)
                 with coverage >= 0.9 of the row's words, the unit is <= 3x the row's words, and every number in the
                 row is in the unit. provision_text := the unit's text verbatim from the snapshot.
  Out of scope: paraphrase / fragment_short / partial_overlap / merge rows (never touched).
Unit choice: the unit whose id matches the row's ref_number; else the unique smallest matching unit; 2+ equal
candidates and nothing picks one -> REFUSED (stays unproven). Never a guess.

sl-norm/2 (versioned; change = new version, old evidence stays valid only against its own version):
  NFKC; a leading '# ' title line dropped (the extractor's own line, as state_law_proof.strip_heading does); list
  markers '(a)' '(A)' '(aa)' '(ii)' '(2)' '(2A)' removed when NOT attached to a preceding letter/digit (so '5(2)' keeps
  its '2'); then tokens = runs of letters/digits, case KEPT. Dashes, bullets, markdown, punctuation and whitespace
  therefore vanish. No page-furniture removal, no ellipsis special-casing (an ellipsis is punctuation).

    python scripts/sepp_marker_blind.py                  # plan + evidence + refused CSV, read-only DB session
Verify with scripts/verify_sepp_marker_blind.py; apply (dry run by default) with scripts/apply_sepp_marker_blind.py.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import state_law_proof as p1  # noqa: E402
import state_law_recopy as rc  # noqa: E402

ROOT = p1.ROOT
NORM_VERSION = "sl-norm/2"
MATCH_VERSION = "sl-match/1"
MIN_WORDS = 8
COVERAGE_MIN = 0.90
SIZE_MAX = 3.0
PEER_MARGIN = 0.05
PREFILTER = 0.80          # row's distinct words found in the unit before the ordered match is even tried
SPAN_MIN = 0.90          # rule 1 only when the row is >= this share of the unit's words
IN_SCOPE = {"near_copy", "copy_with_gaps"}

_LET = r"(?:[a-z]|(?P<l>[a-z])(?P=l)|[ivxlc]{2,6}|[A-Z]|(?P<u>[A-Z])(?P=u))"
MARKER = re.compile(r"(?<![0-9A-Za-z])(?:\(\s*(?:" + _LET + r"|\d{1,3}[A-Z]{0,2})\s*\)\s*)+")
TOKEN = re.compile(r"[^\W_]+")


# ------------------------------------------------------------------------------------------------ normaliser
def norm_tokens(text: str) -> list[str]:
    """sl-norm/2: marker-blind word list of a stored row or of a unit's text."""
    t = unicodedata.normalize("NFKC", text or "")
    t = p1.strip_heading(t)
    t = MARKER.sub(" ", t)
    return TOKEN.findall(t)


def tokens_sha(tokens: list[str]) -> str:
    return hashlib.sha256(" ".join(tokens).encode("utf-8")).hexdigest()


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def md5(s: str) -> str:
    return hashlib.md5((s or "").encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------------------------------- snapshot
class Snapshot:
    """One instrument file: units, their normalised word lists, the proof Instrument (for verbatim/numbers)."""

    def __init__(self, path: Path):
        raw = path.read_bytes()
        self.path, self.file, self.sha256 = path, path.name, hashlib.sha256(raw).hexdigest()
        self.page = raw.decode("utf-8", errors="replace")
        self.units = rc.parse_units(self.page)
        self.tokens = {u: norm_tokens(x.text) for u, x in self.units.items()}
        self.joined = {u: " " + " ".join(t) + " " for u, t in self.tokens.items()}
        self._inst = None

    @property
    def inst(self) -> "rc.Instrument":
        if self._inst is None:
            self._inst = rc.Instrument(self.page)
        return self._inst

    def ancestors(self, uid: str) -> list[str]:
        out, p = [], self.units[uid].parent
        while p:
            out.append(p)
            p = self.units[p].parent
        return out


def ref_unit(ref: str | None) -> str | None:
    """Unit id a ref_number points at ('Clause 3C.24' -> 'sec.3C.24', 'Section 86(2)' -> 'sec.86-ssec.2'), else None."""
    r = (ref or "").strip()
    m = re.match(r"^Schedule\s+(\d+[A-Z]{0,2})\b", r, re.I)
    if m:
        return f"sch.{m.group(1)}"
    m = re.match(r"^(?:Section|Clause|Subclause|cl|s)?\s*(\d+[A-Z]{0,3}(?:\.\d+[A-Z]{0,3})?)(?:\((\d+[A-Z]?)\))?", r, re.I)
    if not m:
        return None
    return f"sec.{m.group(1)}" + (f"-ssec.{m.group(2)}" if m.group(2) else "")


# ------------------------------------------------------------------------------------------------- matching
def find_seq(snap: Snapshot, row: list[str]) -> dict[str, list[int]]:
    """unit id -> word offsets at which the row's words occur as one contiguous run of the unit's words."""
    needle = " " + " ".join(row) + " "
    out: dict[str, list[int]] = {}
    for uid, hay in snap.joined.items():
        i = hay.find(needle)
        if i == -1:
            continue
        offs = []
        while i != -1:
            offs.append(hay.count(" ", 0, i + 1) - 1)   # words before position i (hay starts with a space)
            i = hay.find(needle, i + 1)   # overlapping repeats count: a repeated run is ambiguous
        out[uid] = offs
    return out


def ordered_cover(row: list[str], unit: list[str]) -> tuple[int, float]:
    """(row words matched in order inside the unit, share of the row's words): sl-match/1 = difflib blocks."""
    sm = difflib.SequenceMatcher(a=row, b=unit, autojunk=False)
    n = sum(b.size for b in sm.get_matching_blocks())
    return n, (n / len(row) if row else 0.0)


def _related(snap: Snapshot, a: str, b: str) -> bool:
    return a == b or a in snap.ancestors(b) or b in snap.ancestors(a)


def ref_related(snap: Snapshot, rf: str | None, uid: str) -> bool:
    """Informational: the chosen unit is the ref_number's unit, inside it, or contains it."""
    return bool(rf and rf in snap.units and _related(snap, rf, uid))


def pick_exact(snap: Snapshot, cands: list[str], ref: str | None) -> tuple[str | None, str]:
    """Rule 1 unit choice: ref's own unit, else the unique smallest (no matching descendant), else refuse."""
    if ref and ref in cands:
        return ref, "ref_number_unit"
    pool = [c for c in cands if ref and c.startswith(ref + "-")] or cands
    smallest = [c for c in pool if not any(c in snap.ancestors(o) for o in pool if o != c)]
    if len(smallest) == 1:
        return smallest[0], "unique_smallest" if len(cands) > 1 else "unique"
    return None, "ambiguous_unit"


_PARA_KIND = (r"[a-z]{1,2}", r"[ivxlc]{1,6}", r"[A-Z]{1,2}")


def ref_full(ref: str | None) -> tuple[str | None, bool]:
    """(unit id the WHOLE ref names, ref goes below the section/subclause). 'Section 107(2)(d)' ->
    ('sec.107-ssec.2-para1.d', True); 'Clause 5A.20(a)' -> ('sec.5A.20-para1.a', True); a paren group that does not
    parse as the next level gives (None, True): the ref is more specific than anything we can resolve."""
    m = re.match(r"^(?:Section|Clause|Subclause|cl|s)?\s*(\d+[A-Z]{0,3}(?:\.\d+[A-Z]{0,3})?)((?:\s*\([^)]*\))*)",
                 (ref or "").strip(), re.I)
    if not m:
        return None, False
    uid, extra, level = f"sec.{m.group(1)}", False, 0
    for i, g in enumerate(re.findall(r"\(\s*([^)]*?)\s*\)", m.group(2))):
        if i == 0 and re.fullmatch(r"\d+[A-Z]?", g):
            uid += f"-ssec.{g}"
            continue
        if uid is not None and level < 3 and re.fullmatch(_PARA_KIND[level], g):
            extra = True
            level += 1
            uid += f"-para{level}.{g}"
        elif re.fullmatch(r"[A-Za-z][A-Za-z ,'&-]{3,}", g) and not re.fullmatch(_PARA_KIND[1], g):
            continue   # a title in brackets, '3D.61 (Excavation)': a label, not a sub-unit
        else:
            extra = True
            uid = None
    return uid, extra


def decide(old: str, ref: str | None, snap: Snapshot, allow_recopy: bool = True) -> dict:
    """_decide plus: a ref naming a paragraph/sub-unit more specific than the chosen unit is refused (the site would
    show that paragraph's citation as checked against a wider unit's text)."""
    d = _decide(old, ref, snap, allow_recopy)
    if d["verdict"] == "refuse":
        return d
    full, extra = ref_full(ref)
    if extra and not (full in snap.units and (d["unit"] == full or full in snap.ancestors(d["unit"]))):
        return {"verdict": "refuse", "reason": "ref_more_specific_than_unit", "unit": d["unit"],
                "detail": full or "unresolved", "n_words": d["n_words"]}
    return d


def _decide(old: str, ref: str | None, snap: Snapshot, allow_recopy: bool = True) -> dict:
    """The whole verdict for one row against one snapshot. Everything the verifier re-derives comes from here.
    -> {verdict: accept|recopy|refuse, reason, unit, ...evidence fields}"""
    row = norm_tokens(old)
    if len(row) < MIN_WORDS:
        return {"verdict": "refuse", "reason": "too_short", "n_words": len(row)}
    rf = ref_unit(ref)
    hits = find_seq(snap, row)
    if hits:
        rel = [u for u in sorted(hits) if ref_related(snap, rf, u)]
        if not rel:   # citation_status='proven' shows ref_number as a checked clause: the unit must relate to it
            return {"verdict": "refuse", "reason": "ref_mismatch", "candidates": sorted(hits)[:6], "n_words": len(row)}
        # Prefer a related unit the row fills (>= SPAN_MIN of its words): a row equal to a sub-clause is proven against
        # that sub-clause even when ref_number names its section. Only if none is filled is the row an excerpt.
        full = [u for u in rel if len(row) / len(snap.tokens[u]) >= SPAN_MIN]
        uid, how = pick_exact(snap, full or rel, rf)
        if uid is None:
            return {"verdict": "refuse", "reason": "ambiguous_unit", "candidates": rel[:6], "n_words": len(row)}
        if len(hits[uid]) != 1:
            return {"verdict": "refuse", "reason": "repeated_in_unit", "unit": uid, "n_words": len(row)}
        s = hits[uid][0]
        ut = snap.tokens[uid]
        share = round(len(row) / len(ut), 3)
        if share >= SPAN_MIN:
            return {"verdict": "accept", "reason": how, "unit": uid, "word_start": s, "word_end": s + len(row),
                    "n_words": len(row), "unit_words": len(ut), "span_share": share,
                    "tokens_sha256": tokens_sha(row), "ref_related": True}
        # A run that stops short of the clause may have dropped a condition: re-copy the whole unit (rule 2) or refuse.
        if not allow_recopy:
            return {"verdict": "refuse", "reason": "excerpt", "unit": uid, "n_words": len(row)}
        d = decide_recopy(old, row, rf, snap)
        if d["verdict"] == "recopy":
            d["excerpt"] = True
            return d
        return {"verdict": "refuse", "reason": "excerpt", "unit": uid, "n_words": len(row),
                "detail": d["reason"]}
    if not allow_recopy:
        return {"verdict": "refuse", "reason": "not_contiguous", "n_words": len(row)}
    return decide_recopy(old, row, rf, snap)


def decide_recopy(old: str, row: list[str], rf: str | None, snap: Snapshot) -> dict:
    rset = set(row)
    scored, why = [], Counter()
    for uid, ut in snap.tokens.items():
        if len(ut) < len(row) * COVERAGE_MIN or not ut:
            continue
        if len(rset & set(ut)) / len(rset) < PREFILTER:
            continue
        n, cov = ordered_cover(row, ut)
        if cov < COVERAGE_MIN:
            why["coverage"] += 1
            continue
        if len(ut) > SIZE_MAX * len(row):
            why["too_big"] += 1
            continue
        scored.append((uid, n, cov))
    if not scored:
        r = "unit_too_big" if why["too_big"] else "no_unit_covers_90pct"
        return {"verdict": "refuse", "reason": r, "n_words": len(row)}
    related = [t for t in scored if ref_related(snap, rf, t[0])]
    if not related:
        best = max(scored, key=lambda t: t[2])
        return {"verdict": "refuse", "reason": "ref_mismatch", "unit": best[0], "n_words": len(row)}
    scored = related
    # numbers: every number in the row must be in the unit; a unit that lacks one is not a candidate
    lost_all = {}
    ok = []
    row_nums = rc.numbers(old)
    for uid, n, cov in scored:
        lost = sorted(row_nums - rc.numbers(snap.units[uid].text))
        if lost:
            lost_all[uid] = lost
        else:
            ok.append((uid, n, cov))
    if not ok:
        u0 = scored[0][0]
        return {"verdict": "refuse", "reason": "number_missing", "unit": u0, "numbers_lost": lost_all[u0],
                "n_words": len(row)}
    cands = {u: (n, c) for u, n, c in ok}
    if rf and rf in cands:
        top, how = rf, "ref_number_unit"
    else:
        pool = [u for u in cands if rf and u.startswith(rf + "-")] or list(cands)
        pool.sort(key=lambda u: (-cands[u][1], len(snap.tokens[u]), u))
        top = pool[0]
        peers = [u for u in pool[1:] if not _related(snap, u, top) and cands[u][1] >= cands[top][1] - PEER_MARGIN]
        if peers:
            return {"verdict": "refuse", "reason": "ambiguous_unit", "candidates": [top] + peers[:5],
                    "n_words": len(row)}
        how = "best_coverage"
    n, cov = cands[top]
    new = snap.units[top].text
    if not rc.verbatim(snap.inst, new):
        return {"verdict": "refuse", "reason": "unit_text_not_verbatim_in_law", "unit": top, "n_words": len(row)}
    if md5(new) == md5(old):
        return {"verdict": "refuse", "reason": "already_identical", "unit": top, "n_words": len(row)}
    return {"verdict": "recopy", "reason": how, "unit": top, "n_words": len(row), "matched_words": n,
            "coverage": round(cov, 4), "unit_words": len(snap.tokens[top]),
            "size_ratio": round(len(snap.tokens[top]) / len(row), 3), "new_sha256": sha256(new),
            "tokens_sha256": tokens_sha(row), "ref_related": ref_related(snap, rf, top)}


# ------------------------------------------------------------------------------------------------------ main
SQL = ("SELECT id, document_id, ref_number, provision_text, md5(provision_text), citation_status, is_current, "
       "source_council, (SELECT count(*) FROM provision_versions v WHERE v.provision_id = p.id) "
       "FROM regulatory_provisions p WHERE id = ANY(%s)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--classified", default=str(ROOT / "data" / "sepp_unproven_classified_2026-10-18.csv"))
    ap.add_argument("--date", default="2026-10-18")
    args = ap.parse_args(argv)
    stamp = args.date
    cls = {int(r["id"]): r for r in csv.DictReader(open(args.classified, encoding="utf8"))}
    ids = [i for i, r in cls.items() if r["bucket"] in IN_SCOPE]
    conn = p1.connect()
    cur = conn.cursor()
    cur.execute("SET statement_timeout = 30000")
    cur.execute(SQL, (ids,))
    rows = {r[0]: r for r in cur.fetchall()}
    conn.close()
    print(f"classified rows {len(cls)}  in scope {len(ids)}  fetched {len(rows)}")

    refused: list[dict] = []
    plan_rows: list[dict] = []
    evidence: list[dict] = []
    manifest: dict = {}
    out_of_scope = Counter(r["bucket"] for r in cls.values() if r["bucket"] not in IN_SCOPE)
    by_epi: dict[str, list] = defaultdict(list)
    for i in sorted(ids):
        r = rows.get(i)
        if r is None or not r[6] or r[7] is not None:
            refused.append({"id": i, "rule": "", "reason": "row_not_current_or_not_state_law", "detail": ""})
        elif r[5] == "proven":
            refused.append({"id": i, "rule": "", "reason": "already_proven", "detail": ""})
        else:
            epi = p1.instrument_for(r[1])
            if epi is None:
                refused.append({"id": i, "rule": "", "reason": "unmapped_instrument", "detail": r[1]})
            else:
                by_epi[epi].append(r)
    for epi in sorted(by_epi):
        f = p1.latest_cache(epi)
        snap = Snapshot(f)
        manifest[epi] = {"file": f.name, "sha256": snap.sha256, "bytes": f.stat().st_size,
                         "source": p1.LAW_URL.format(epi=epi)}
        law_date = f.stem.rpartition("_")[2]
        print(f"{epi}: {len(snap.units)} units, {len(by_epi[epi])} rows", flush=True)
        for rid, doc, ref, old, om5, _cs, _cur, _sc, nver in by_epi[epi]:
            d = decide(old, ref, snap)
            if d["verdict"] == "refuse":
                refused.append({"id": rid, "rule": "", "reason": d["reason"], "ref_number": ref,
                                "unit_found": ";".join(d.get("candidates", [])) or d.get("unit", ""),
                                "detail": d.get("detail", "") or ",".join(d.get("numbers_lost", []))})
                continue
            if d["verdict"] == "recopy" and nver:
                refused.append({"id": rid, "rule": "recopy", "reason": "has_version_history", "detail": f"{nver} versions"})
                continue
            uid = d["unit"]
            src = f"{p1.LAW_URL.format(epi=epi)}#{uid}"
            rule = "accept" if d["verdict"] == "accept" else "recopy"
            ev = {"id": rid, "rule": rule, "epi": epi, "snapshot_file": f.name, "snapshot_sha256": snap.sha256,
                  "law_date": law_date, "unit_id": uid, "norm_version": NORM_VERSION, "match_version": MATCH_VERSION,
                  "old_md5": om5, "ref_number": ref, "pick": d["reason"]}
            ev.update({k: d[k] for k in ("word_start", "word_end", "n_words", "unit_words", "span_share",
                                         "tokens_sha256", "ref_related", "excerpt", "matched_words", "coverage", "size_ratio", "new_sha256")
                       if k in d})
            new = snap.units[uid].text if rule == "recopy" else None
            plan_rows.append({"id": rid, "md5": om5, "rule": rule, "kind": "marker_blind_" + rule, "epi": epi,
                              "document_id": doc, "ref_number": ref, "unit_id": uid, "source": src,
                              "law_date": law_date, "old_text": old, "new_text": new})
            evidence.append(ev)

    plan = {"generated": stamp, "norm_version": NORM_VERSION, "match_version": MATCH_VERSION, "manifest": manifest,
            "method": "scripts/sepp_marker_blind.py (docstring has the rules). No model reads or writes text.",
            "rows": plan_rows}
    pp = ROOT / "data" / f"sepp_marker_blind_plan_{stamp}.json"
    pp.write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    ep = ROOT / "data" / f"sepp_marker_blind_evidence_{stamp}.jsonl"
    ep.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in evidence), encoding="utf8")
    rp = ROOT / "data" / f"sepp_marker_blind_refused_{stamp}.csv"
    with rp.open("w", newline="", encoding="utf8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "rule", "reason", "ref_number", "unit_found", "detail"], restval="")
        w.writeheader()
        w.writerows(refused)

    n_acc = sum(e["rule"] == "accept" for e in evidence)
    n_rec = sum(e["rule"] == "recopy" for e in evidence)
    print(f"\nACCEPTED (rule 1, mark proven): {n_acc}\nRECOPIED (rule 2, text := law unit): {n_rec}\n"
          f"REFUSED (stay unproven): {len(refused)}")
    for k, n in Counter(r["reason"] for r in refused).most_common():
        print(f"  {n:5}  {k}")
    print(f"out of scope, untouched: {dict(out_of_scope)}")
    print(f"rule 1 span_share<0.9 (row is part of a longer unit): "
          f"{sum(1 for e in evidence if e['rule'] == 'accept' and e['span_share'] < 0.9)}")
    print(f"wrote {pp.relative_to(ROOT)}, {ep.relative_to(ROOT)}, {rp.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
