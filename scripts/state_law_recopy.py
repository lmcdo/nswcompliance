#!/usr/bin/env python3
"""Re-copy served state-law rows from the law itself, one structural unit at a time. No model reads or writes text.

prior-art-checked: extends scripts/state_law_proof.py + state_law_proof2.py (candidate cache, normaliser, Doc.contains);
nothing else in scripts/ cuts a NSW instrument into its numbered units (law_change_diff.paragraphs flattens them).

Problem: ~830 served rows are the law's text stored imperfectly (ellipses, split sub-clauses, table/markdown
leftovers, dash/superscript variants) and 49 are wording amended since. For each row this finds the ONE unit of the
instrument (section/clause, sub-clause, or paragraph, from the id path the legislation HTML itself carries, e.g.
'sec.58-ssec.2-para1.c') that the row is a copy of, and proposes the unit's verbatim text as the row's text.

Unit choice: units holding >= 90% of the row's 5-word runs; the SMALLEST qualifying units (no qualifying descendant);
exactly one => chosen, several => AMBIGUOUS (skipped), none => skipped.
Acceptance (all required, else skipped with the reason):
  a  new text verbatim in today's instrument (state_law_proof2.Doc.contains, the proof the site's check uses)
  b  every word of the row is in the unit, in order, once list markers '(a)', ellipses '...', markdown/html
     markup and page furniture are set aside: 0 content words dropped
  c  length ratio new/old in [0.8, 3.0]
  d  every number in the old text is in the new text
  e  amended rows: old text verbatim in the point-in-time instrument and absent from today's; the new unit is the
     SAME id path in today's instrument and shares >= 50% of the old text's runs (same provision, not renumbered).
     For these (b) and (d) are not applicable -- the words that changed ARE the amendment -- and the words
     dropped/added are recorded in the plan instead.

    python scripts/state_law_recopy.py            # plan + skipped CSV + counts + 10 random examples
Apply with scripts/apply_state_law_recopy.py.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import state_law_proof as p1  # noqa: E402
import state_law_proof2 as p2  # noqa: E402
from law_change_diff import paragraphs  # noqa: E402

ROOT = p1.ROOT
RUN = 5
QUALIFY_AT = 0.90
MIN_WORDS = 8
RESCUE_FROM = 0.5
SHINGLE_CH = 20
RATIO_MIN, RATIO_MAX = 0.8, 3.0
AMEND_SAME_PROVISION_AT = 0.5

UNIT_CLASSES = {"frag-clause", "frag-subclause", "frag-li", "frag-note", "frag-table"}
BLOCK_TAGS = {"div", "blockquote", "p", "tr", "li", "ul", "ol", "table", "h1", "h2", "h3", "h4", "h5", "h6", "br"}
CELL_TAGS = {"td", "th"}
VOID_TAGS = {"br", "img", "meta", "link", "hr", "input", "col", "area", "base", "wbr"}
SKIP_CLASSES = {"frag-historynote"}   # 's 57: Am 2023 (83)' amendment history: editorial, not the operative words

# Page furniture that the PDF/HTML print of an instrument leaves inside a stored row.
FURNITURE = re.compile(
    r"(?:State Environmental Planning Policy|Environmental Planning and Assessment)[^\n]{0,140}? - NSW Legislation"
    r"|Current version for [^\n]{0,80}?(?:\(accessed [^)]*\))?"
    r"|\bPage \d+ of \d+\b"
    r"|\\[a-z]+\b", re.I)   # last: LaTeX leftovers such as backslash-cdot
ELLIPSIS = re.compile(r"\.{3,}|…")
MARKER = re.compile(r"\(\s*(?:[a-z]{1,4}|\d{1,3}[A-Z]?)\s*\)")
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


# ----------------------------------------------------------------------------------------------- units
class Unit:
    __slots__ = ("id", "parent", "cls", "parts", "text", "depth")

    def __init__(self, uid: str, parent: str | None, cls: str, depth: int):
        self.id, self.parent, self.cls, self.depth = uid, parent, cls, depth
        self.parts: list[str] = []
        self.text = ""


def _tidy(parts: list[str]) -> str:
    """Join text pieces: lines at block boundaries, nbsp -> space, single spaces, no space before , . ; :"""
    raw = "".join(parts).replace("\xa0", " ")
    lines = []
    for ln in raw.split("\n"):
        ln = re.sub(r"[ \t\r\f\v]+", " ", ln).strip()
        ln = re.sub(r" ([,.;:])", r"\1", ln)
        if ln:
            lines.append(ln)
    return "\n".join(lines)


class _UnitParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, Unit | None, bool]] = []   # (tag, unit opened here, skip opened here)
        self.units: dict[str, Unit] = {}
        self.open_units: list[Unit] = []
        self.skip = 0
        self.dead = 0   # inside script/style

    def _emit(self, s: str) -> None:
        if self.skip or self.dead:
            return
        for u in self.open_units:
            u.parts.append(s)

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            if tag == "br":
                self._emit("\n")
            return
        a = dict(attrs)
        classes = set((a.get("class") or "").split())
        uid = a.get("id")
        unit = None
        if uid and classes & UNIT_CLASSES and uid not in self.units and not self.skip:
            cls = next(iter(classes & UNIT_CLASSES))
            parent = self.open_units[-1].id if self.open_units else None
            unit = Unit(uid, parent, cls, len(self.open_units))
            self.units[uid] = unit
            self.open_units.append(unit)
        skip = bool(classes & SKIP_CLASSES)
        if skip:
            self.skip += 1
        if tag in ("script", "style"):
            self.dead += 1
        if tag in BLOCK_TAGS:
            self._emit("\n")
        elif tag in CELL_TAGS:
            self._emit(" ")
        self.stack.append((tag, unit, skip))

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self._emit("\n")

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        idx = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i][0] == tag), None)
        if idx is None:
            return
        while len(self.stack) > idx:
            t, unit, skip = self.stack.pop()
            if t in BLOCK_TAGS:
                self._emit("\n")
            elif t in CELL_TAGS:
                self._emit(" ")
            if unit is not None:
                self.open_units.remove(unit)
                unit.text = _tidy(unit.parts)
                unit.parts = []
            if skip:
                self.skip -= 1
            if t in ("script", "style"):
                self.dead -= 1

    def handle_data(self, data):
        self._emit(data)

    def close(self):
        super().close()
        for u in list(self.open_units):
            u.text = _tidy(u.parts)
            u.parts = []


def parse_units(page: str) -> dict[str, Unit]:
    """Every id'd clause / sub-clause / paragraph / note / table of the instrument -> its verbatim text."""
    p = _UnitParser()
    p.feed(page)
    p.close()
    return p.units


# ------------------------------------------------------------------------------------------- tokenising
def clean(text: str) -> str:
    """Set aside page furniture (explained removals) before comparing a stored row."""
    return FURNITURE.sub(" ", text or "")


def segments(text: str) -> list[list[str]]:
    """Word lists of the cleaned text, split at ellipses; list markers '(a)' and '(2A)' set aside."""
    out = []
    for seg in ELLIPSIS.split(clean(text)):
        w = re.findall(r"[a-z0-9]+", MARKER.sub(" ", p2.prep(seg)).lower())
        if w:
            out.append(w)
    return out


def runs_of(words: list[str]) -> list[tuple]:
    return [tuple(words[i:i + RUN]) for i in range(len(words) - RUN + 1)]


def row_runs(text: str) -> list[tuple]:
    return [r for seg in segments(text) for r in runs_of(seg)]


def numbers(text: str) -> set[str]:
    t = re.sub(r"(?<=\d)\s+(?=\d{3}\b)", "", p2.prep(clean(text)))   # '4 000' == '4000' (thousands group)
    return {n.replace(",", "") for n in NUMBER.findall(t)}


class Instrument:
    """One instrument version: units + inverted index run-hash -> unit ids + the proof Doc."""

    def __init__(self, page: str):
        self.units = parse_units(page)
        self.words: dict[str, list[str]] = {}
        self.index: dict[int, set[str]] = defaultdict(set)
        self.runs: dict[str, set[int]] = {}
        for uid, u in self.units.items():
            w = [t for seg in segments(u.text) for t in seg]
            self.words[uid] = w
            hs = {hash(r) for seg in segments(u.text) for r in runs_of(seg)}
            self.runs[uid] = hs
            for h in hs:
                self.index[h].add(uid)
        paras = paragraphs(page)
        self.doc = p2.Doc(paras)
        self.law1 = p1.Law(paras)   # the site's own pass-1 prover
        self.children: dict[str, list[str]] = defaultdict(list)
        for uid, u in self.units.items():
            if u.parent:
                self.children[u.parent].append(uid)

    def qualifying(self, text: str) -> list[str]:
        rr = row_runs(text)
        if not rr:
            return []
        hits: Counter = Counter()
        for r in rr:
            for uid in self.index.get(hash(r), ()):
                hits[uid] += 1
        out = [uid for uid, n in hits.items() if n / len(rr) >= QUALIFY_AT]
        # Rescue: encoding damage (lost f-ligatures, split numbers) breaks word runs. Re-test the units that hold
        # >= 50% of the runs on letters only (f-ligatures and whitespace folded), 20-character shingles.
        for uid, n in hits.items():
            if uid not in out and n / len(rr) >= RESCUE_FROM and self.char_share(text, uid) >= QUALIFY_AT:
                out.append(uid)
        return out

    def char_share(self, text: str, uid: str) -> float:
        unit = self._letters(self.units[uid].text)
        grams = {unit[i:i + SHINGLE_CH] for i in range(max(0, len(unit) - SHINGLE_CH + 1))}
        tot = hit = 0
        for seg in ELLIPSIS.split(clean(text)):
            s = self._letters(seg)
            for i in range(len(s) - SHINGLE_CH + 1):
                tot += 1
                hit += s[i:i + SHINGLE_CH] in grams
        return hit / tot if tot else 0.0

    @staticmethod
    def _letters(t: str) -> str:
        return lig_fold(re.sub(r"[^a-z0-9]+", "", MARKER.sub(" ", p2.prep(t)).lower()))

    def minimal(self, qual: list[str]) -> list[str]:
        """Qualifying units with no qualifying descendant."""
        q = set(qual)
        has_q_desc: set[str] = set()
        for uid in q:
            p = self.units[uid].parent
            while p:
                if p in has_q_desc:
                    break
                has_q_desc.add(p)
                p = self.units[p].parent
        return sorted(u for u in q if u not in has_q_desc)

    def share(self, text: str, uid: str) -> float:
        rr = row_runs(text)
        return sum(hash(r) in self.runs[uid] for r in rr) / len(rr) if rr else 0.0


# --------------------------------------------------------------------------------------------- checks
LIGATURE = re.compile(r"f+[il]?")


def lig_fold(s: str) -> str:
    """Fold away the letters a lost f-ligature (ff, fi, fl, ffi, ffl) takes with it: 'af ordable' == 'affordable'."""
    return LIGATURE.sub("", s)


def words_dropped(old: str, unit_words: list[str], repairs: list[str] | None = None) -> list[str]:
    """Words of the old text that are not in the unit, in order. Ellipses/markup/markers/furniture are already gone.
    A replaced block is explained (not dropped) when the row's words and the unit's words are the same letters
    once whitespace and lost f-ligatures are ignored (the PDF-to-text encoding losses: 'Af ordable', 'de ned',
    '10 00' for '1 000'); every such repair is appended to `repairs`."""
    out = []
    segs = segments(old)
    last = segs[-1] if segs else None
    for seg in segs:
        sm = difflib.SequenceMatcher(a=seg, b=unit_words, autojunk=False)
        for tag, a1, a2, b1, b2 in sm.get_opcodes():
            if tag == "equal":
                continue
            if tag == "replace" and (a2 - a1) <= 6 and (b2 - b1) <= 6:
                ra, rb = "".join(seg[a1:a2]), "".join(unit_words[b1:b2])
                if lig_fold(ra) == lig_fold(rb):
                    if repairs is not None:
                        repairs.append(f"{' '.join(seg[a1:a2])} -> {' '.join(unit_words[b1:b2])}")
                    continue
                # A row cut off mid-word at its end ('the relevant council ha'): its last words are the start
                # of the unit's words there. Only the final block of the row's final segment may do this.
                if a2 == len(seg) and seg is last and len(ra) >= 2 and rb.startswith(ra):
                    if repairs is not None:
                        repairs.append(f"{' '.join(seg[a1:a2])} (row ends here) -> {' '.join(unit_words[b1:b2])}")
                    continue
            out += seg[a1:a2]
    return out


def length_ratio(old: str, new: str) -> float:
    """new/old length with whitespace collapsed; old has html/markdown markup and page furniture taken out first."""
    o = len(re.sub(r"\s+", " ", p2.prep(clean(old))).strip())
    n = len(re.sub(r"\s+", " ", new).strip())
    return round(n / o, 3) if o else 0.0


def verbatim(inst: Instrument, new: str) -> bool:
    """The new text is in today's instrument by BOTH provers (pass 2 squash form and pass 1 exact/relaxed)."""
    if not new or "\ufffd" in new:
        return False
    flat = new.replace("\n", " ")
    return inst.doc.contains(flat) and inst.law1.prove(flat)["status"] == "proven"


def judge(old: str, inst: Instrument, uid: str) -> dict:
    """Run acceptance checks a-d for one row against one unit. Returns {ok, failed, ...}."""
    new = inst.units[uid].text
    repairs: list[str] = []
    dropped = words_dropped(old, inst.words[uid], repairs)
    ratio = length_ratio(old, new)
    lost_numbers = sorted(numbers(old) - numbers(new))
    checks = {
        "a_verbatim_in_law": verbatim(inst, new),
        "b_no_content_word_dropped": not dropped,
        "c_length_ratio": RATIO_MIN <= ratio <= RATIO_MAX,
        "d_numbers_kept": not lost_numbers,
    }
    return {"ok": all(checks.values()), "failed": [k for k, v in checks.items() if not v], "checks": checks,
            "words_dropped": dropped, "repairs": repairs, "ratio": ratio, "numbers_lost": lost_numbers}


def pick_unit(text: str, inst: Instrument) -> tuple[str | None, str, list[str]]:
    """(unit id | None, reason, candidates). Reason 'ok' when exactly one smallest qualifying unit."""
    if len(p2.words2(clean(text))) < MIN_WORDS:
        return None, "too_short", []
    q = inst.qualifying(text)
    if not q:
        return None, "no_unit_holds_90pct", []
    m = inst.minimal(q)
    if len(m) > 1:
        return None, "ambiguous", m[:6]
    return m[0], "ok", m


def judge_amended(old: str, today: Instrument, pit: Instrument) -> tuple[dict | None, str, str | None]:
    """Check e. Returns (judgement, reason, unit id)."""
    if not pit.doc.contains(old):
        return None, "e_old_not_verbatim_in_pit", None
    if today.doc.contains(old):
        return None, "e_old_still_in_today", None
    uid, why, cand = pick_unit(old, pit)
    if uid is None:
        return None, f"e_pit_unit_{why}", None
    if uid not in today.units:
        return None, "e_id_path_absent_today", uid
    sh = today.share(old, uid)
    if sh < AMEND_SAME_PROVISION_AT:
        return None, "e_id_path_drift", uid
    new = today.units[uid].text
    ratio = length_ratio(old, new)
    dropped = words_dropped(old, today.words[uid])
    pit_words = pit.words[uid]
    added = words_dropped(" ".join(today.words[uid]), pit_words)
    checks = {"a_verbatim_in_law": verbatim(today, new),
              "c_length_ratio": RATIO_MIN <= ratio <= RATIO_MAX,
              "e_same_provision_share": True}
    return ({"ok": all(checks.values()), "failed": [k for k, v in checks.items() if not v], "checks": checks,
             "words_dropped": dropped, "words_added": added, "ratio": ratio,
             "numbers_lost": sorted(numbers(old) - numbers(new)), "same_provision_share": round(sh, 3)},
            "ok", uid)


# ------------------------------------------------------------------------------------------------ main
def load_instrument(path: Path) -> Instrument:
    return Instrument(path.read_text(encoding="utf-8", errors="replace"))


def fetch_rows(ids: list[int]) -> list[tuple]:
    conn = p1.connect()
    cur = conn.cursor()
    cur.execute("SELECT id, document_id, provision_text, md5(provision_text), "
                "(SELECT count(*) FROM provision_versions v WHERE v.provision_id = p.id) "
                "FROM regulatory_provisions p WHERE id = ANY(%s) AND is_current AND source_council IS NULL", (ids,))
    rows = cur.fetchall()
    conn.close()
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass2", default=str(ROOT / "data" / "state_law_proof_pass2_2026-10-16.csv"))
    ap.add_argument("--amended", default=str(ROOT / "data" / "state_law_amended_2026-10-16.json"))
    ap.add_argument("--date", default=None)
    ap.add_argument("--limit", type=int, default=0, help="debug: first N rows only")
    args = ap.parse_args(argv)
    stamp = args.date or date.today().isoformat()

    pass2 = list(csv.DictReader(open(args.pass2, encoding="utf8")))
    partial_ids = [int(r["id"]) for r in pass2 if r["status"] in ("partial_high", "partial_unresolved")]
    status_of = {int(r["id"]): r["status"] for r in pass2}
    amended = {a["id"]: a for a in json.load(open(args.amended, encoding="utf8"))}
    ids = partial_ids + list(amended)
    if args.limit:
        ids = ids[:args.limit]
    rows = {r[0]: r for r in fetch_rows(ids)}
    print(f"rows: asked {len(ids)}  fetched (still current, state-law) {len(rows)}")

    by_epi: dict[str, list[int]] = defaultdict(list)
    skipped: list[dict] = []
    for i in ids:
        if i not in rows:
            skipped.append({"id": i, "reason": "row_not_current_or_not_state_law", "detail": ""})
            continue
        if rows[i][4]:
            skipped.append({"id": i, "reason": "has_version_history", "detail": f"{rows[i][4]} version rows"})
            continue
        epi = p1.instrument_for(rows[i][1])
        if epi is None:
            skipped.append({"id": i, "reason": "unmapped_instrument", "detail": rows[i][1]})
            continue
        by_epi[epi].append(i)

    accepted, manifest = [], {}
    for epi in sorted(by_epi):
        f = p1.latest_cache(epi)
        raw = f.read_bytes()
        law_date = f.stem.rpartition("_")[2]
        manifest[epi] = {"file": f.name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                         "source": p1.LAW_URL.format(epi=epi)}
        today = Instrument(raw.decode("utf-8", errors="replace"))
        pits: dict[str, Instrument | None] = {}
        print(f"{epi}: {len(today.units)} units, {len(by_epi[epi])} rows", flush=True)
        for rid in by_epi[epi]:
            _, doc, old, md5, _nv = rows[rid]
            if rid in amended:
                day = amended[rid]["in_force_date"]
                if day not in pits:
                    pf = p2.PIT / f"{epi}_{day}.html"
                    pits[day] = load_instrument(pf) if pf.exists() else None
                if pits[day] is None:
                    skipped.append({"id": rid, "reason": "e_pit_version_missing", "detail": f"{epi} {day}"})
                    continue
                j, why, uid = judge_amended(old, today, pits[day])
                if j is None:
                    skipped.append({"id": rid, "reason": why, "detail": uid or ""})
                    continue
                kind, pit_date = "amended", day
            else:
                uid, why, cand = pick_unit(old, today)
                if uid is None:
                    skipped.append({"id": rid, "reason": why, "detail": ";".join(cand)})
                    continue
                j = judge(old, today, uid)
                kind, pit_date = "partial", None
            if not j["ok"]:
                skipped.append({"id": rid, "reason": "failed_" + "+".join(j["failed"]),
                                "detail": f"{uid} ratio={j['ratio']} dropped={' '.join(j['words_dropped'][:8])} "
                                          f"nums_lost={','.join(j['numbers_lost'][:5])}"})
                continue
            new = today.units[uid].text
            if hashlib.md5(new.encode("utf-8")).hexdigest() == md5:
                skipped.append({"id": rid, "reason": "already_identical", "detail": uid})
                continue
            accepted.append({"id": rid, "md5": md5, "kind": kind, "pass2_status": status_of.get(rid, "amended"),
                             "epi": epi, "document_id": doc, "unit_id": uid, "unit_class": today.units[uid].cls,
                             "unit_parent": today.units[uid].parent, "source": f"{p1.LAW_URL.format(epi=epi)}#{uid}",
                             "law_date": law_date, "pit_date": pit_date, "old_text": old, "new_text": new,
                             "checks": j["checks"], "ratio": j["ratio"], "words_dropped": j["words_dropped"], "repairs": j.get("repairs", []),
                             "words_added": j.get("words_added", []), "numbers_lost": j["numbers_lost"],
                             "same_provision_share": j.get("same_provision_share")})

    plan = {"generated": stamp, "manifest": manifest,
            "method": "scripts/state_law_recopy.py: smallest unique unit holding >=90% of the row's 5-word runs; "
                      "checks a-e in its docstring. No model reads or writes text.",
            "rows": accepted}
    pp = ROOT / "data" / f"state_law_recopy_plan_{stamp}.json"
    pp.write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    sp = ROOT / "data" / f"state_law_recopy_skipped_{stamp}.csv"
    with sp.open("w", newline="", encoding="utf8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "reason", "detail"])
        w.writeheader()
        w.writerows(skipped)

    print(f"\nREPLACED (planned): {len(accepted)}  by kind {dict(Counter(a['kind'] for a in accepted))}  "
          f"by unit class {dict(Counter(a['unit_class'] for a in accepted))}")
    print(f"SKIPPED: {len(skipped)}")
    for r, n in Counter(s["reason"] for s in skipped).most_common():
        print(f"  {n:5}  {r}")
    rnd = random.Random(7)
    print("\n--- 10 random accepted examples ---")
    for a in rnd.sample(accepted, min(10, len(accepted))):
        o = re.sub(r"\s+", " ", a["old_text"])[:150]
        n = re.sub(r"\s+", " ", a["new_text"])[:150]
        print(f"{a['id']} [{a['kind']} {a['unit_id']} ratio={a['ratio']}]\n  OLD: {o}\n  NEW: {n}")
    print(f"\nwrote {pp.relative_to(ROOT)} and {sp.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
