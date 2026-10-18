#!/usr/bin/env python3
"""Drop the invisible (white) twin of every line from served council rows. DRY RUN: reads only.

prior-art-checked: scripts/page_evidence.py (normalise, rule_words, find_span, MATCHER_VERSION) is the
matcher and is reused as-is; scripts/page_proof_council.py (held/primary page logic) is mirrored, not
copied. Nothing else in scripts/ reads span colour: grep -n "color" scripts/page_evidence.py finds none.

WHY. The Campbelltown DCP Part 3 PDF carries a WHITE copy of each line at the same box as the dark
copy (PyMuPDF span colour 16777215). get_text() reads both, so served rows came out with every
line twice, and the page proof passed them (the doubled words ARE on the page, once visible once not).
No model is called anywhere: this is string comparison only.

A row is rewritten ONLY when the text with its immediately repeated lines collapsed is ONE contiguous
word run of the VISIBLE-only text (non-white spans) of a page the row already points at (pdf_page or
page_range). A doubled pair that the council really printed twice (visible-only text holds the doubled
form) is never collapsed. Background colour other than white is NOT detected (measured: only white
and dark colours occur in this PDF).

    python scripts/visible_text_repair.py PDF [--write-plan]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import page_evidence as pe  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WHITE = 0xFFFFFF
CHAPTER = "campbelltown-dcp-part3-low-medium"
MIN_REPEAT_WORDS = 1   # short wrapped lines ("room", "and", "i)") are doubled too; the visible-page proof gates every collapse
_MARKER = re.compile(r"^\s*(?:\(\w{1,4}\)|\w{1,4}[.)])\s+")


# -- visible-only page text ----------------------------------------------------------

def _lines(page_dict: dict) -> list[str]:
    out = []
    for b in page_dict["blocks"]:
        if b["type"] != 0:
            continue
        for ln in b["lines"]:
            t = "".join(s["text"] for s in ln["spans"] if s["color"] != WHITE)
            if t.strip():
                out.append(t)
    return out


def visible_texts(page) -> dict[str, str]:
    """order -> normalised text of the non-white spans only (same two orders as page_evidence)."""
    return {"raw": pe.normalise("\n".join(_lines(page.get_text("dict")))),
            "sorted": pe.normalise("\n".join(_lines(page.get_text("dict", sort=True))))}


def white_report(doc) -> dict:
    """Spans/chars by colour, and white characters with no same-character visible twin in the same box."""
    cols, orphans = Counter(), {}
    nwhite = nvis = 0
    for pno, page in enumerate(doc, 1):
        W, V = [], []
        for b in page.get_text("rawdict")["blocks"]:
            if b["type"] != 0:
                continue
            for ln in b["lines"]:
                for s in ln["spans"]:
                    if any(not c["c"].isspace() for c in s["chars"]):
                        cols[s["color"]] += 1
                    for c in s["chars"]:
                        if not c["c"].isspace():
                            (W if s["color"] == WHITE else V).append((c["c"], c["bbox"]))
        nwhite += len(W)
        nvis += len(V)
        lone = ""
        for ch, bb in W:
            cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
            if not any(vc == ch and v[0] - 1 <= cx <= v[2] + 1 and v[1] - 1 <= cy <= v[3] + 1 for vc, v in V):
                lone += ch
        if lone:
            orphans[pno] = lone
    return {"span_colours": dict(cols), "white_chars": nwhite, "visible_chars": nvis,
            "white_chars_without_visible_twin": sum(len(v) for v in orphans.values()),
            "pages_with_such_chars": len(orphans), "orphans": orphans}


# -- collapsing ----------------------------------------------------------------------

_MARKER_ONLY = re.compile(r"^\s*(?:\(\w{1,4}\)|\w{1,4}[.)])\s*$")


def _key(line: str) -> str:
    return pe.normalise(_MARKER.sub("", line, count=1)) or pe.normalise(line)


def _lone_marker_of(prev: str, ln: str) -> bool:
    """prev is a bare list marker ("i)") and ln starts with the same marker: prev is the stray twin."""
    m = _MARKER.match(ln)
    return bool(m and _MARKER_ONLY.match(prev) and pe.normalise(prev) == pe.normalise(m.group(0)))


def _has_marker(line: str) -> bool:
    return bool(_MARKER.match(line))


def collapse(text: str, printed_twice=None) -> str:
    """Collapse immediately repeated lines (equal after normalising and dropping a leading list marker),
    keeping the copy that carries the marker (else the first). Lines of < MIN_REPEAT_WORDS words are
    never collapsed. printed_twice(words) -> True when the council's visible page holds that pair
    doubled: such a pair is a real repeat (a table cell) and stays."""
    out: list[str] = []
    for ln in text.split("\n"):
        k = _key(ln)
        if out and _lone_marker_of(out[-1], ln):
            w = pe.normalise(out[-1])
            if printed_twice is None or not printed_twice(w + " " + w):
                out.pop()
        if out and k and len(k.split()) >= MIN_REPEAT_WORDS and _key(out[-1]) == k:
            if printed_twice is not None and printed_twice(k + " " + k):
                out.append(ln)
                continue
            if _has_marker(ln) and not _has_marker(out[-1]):
                out[-1] = ln
            continue
        out.append(ln)
    return "\n".join(_collapse_blocks(out, printed_twice))


MAX_BLOCK = 15


def _collapse_blocks(lines: list[str], printed_twice) -> list[str]:
    """A run of 2..MAX_BLOCK lines immediately followed by the same run (the white copy of a wrapped
    paragraph read after the dark one) keeps one copy -- the one with more list markers, else the first."""
    keys = [_key(x) for x in lines]
    out: list[str] = []
    i = 0
    while i < len(lines):
        for k in range(min(MAX_BLOCK, (len(lines) - i) // 2), 1, -1):
            a, b = keys[i:i + k], keys[i + k:i + 2 * k]
            if a == b and all(a):
                w = " ".join(a)
                if printed_twice is not None and printed_twice(w + " " + w):
                    continue
                first, second = lines[i:i + k], lines[i + k:i + 2 * k]
                out.extend(second if sum(map(_has_marker, second)) > sum(map(_has_marker, first)) else first)
                i += 2 * k
                break
        else:
            out.append(lines[i])
            i += 1
    return out


def has_block_repeat(text: str) -> bool:
    lines = text.split("\n")
    return len(_collapse_blocks(lines, None)) < len(lines)


def has_repeat(text: str) -> bool:
    if has_block_repeat(text):
        return True
    prev = None
    for ln in text.split("\n"):
        k = _key(ln)
        if k and len(k.split()) >= MIN_REPEAT_WORDS and k == prev:
            return True
        prev = k
    return False


# -- proof against the visible-only page --------------------------------------------

def on_visible(words: str, vis: dict, held, primary):
    """Evidence dict for `words` as one contiguous run of the visible text of a held page, else None."""
    if len(words.split()) < pe.MIN_WORDS:
        return None
    order = sorted(set(held) & set(vis), key=lambda p: (p != primary, p))
    for pno in order:
        for o in pe.ORDERS:
            for s in pe.find_span(vis[pno].get(o, ""), words):   # visible text has only raw/sorted
                return {"page": pno, "order": o, "start": s, "end": s + len(words), "span": words,
                        "span_sha256": hashlib.sha256(words.encode()).hexdigest(),
                        "matcher_version": pe.MATCHER_VERSION + "+visible-only"}
    return None


def plan_row(row: dict, vis: dict) -> dict:
    """Verdict for one row. row: id, provision_text, pdf_page, page_range. Pure."""
    text = row["provision_text"] or ""
    held = set(row.get("page_range") or []) | ({row["pdf_page"]} if row.get("pdf_page") else set())
    primary = row.get("pdf_page")
    cur_ev = on_visible(pe.rule_words(text), vis, held, primary)
    base = {"id": row["id"], "md5": hashlib.md5(text.encode("utf-8")).hexdigest(), "old_text": text,
            "page": primary, "current_on_visible_page": cur_ev is not None}
    if not has_repeat(text):
        return {**base, "verdict": "unchanged", "reason": "no repeated line"
                + ("" if cur_ev else "; current text is NOT on the visible page")}
    if cur_ev is not None:
        return {**base, "verdict": "unchanged", "reason": "doubled form is printed on the visible page"}

    def printed(w: str) -> bool:
        return on_visible(w, vis, held, primary) is not None

    new = collapse(text, printed)
    if new == text:
        return {**base, "verdict": "refused", "reason": "nothing to collapse after the printed-repeat exemption"}
    ev = on_visible(pe.rule_words(new), vis, held, primary)
    if ev is None:
        return {**base, "verdict": "refused", "reason": "collapsed text is not one run of the visible page"}
    return {**base, "verdict": "fix", "new_text": new, "evidence": ev}


# -- database + rules ----------------------------------------------------------------

ROWS_SQL = ("SELECT id, provision_text, pdf_page, page_range, page_check, citation_status, v2_extracted_rules "
            "FROM regulatory_provisions WHERE source_council = 'campbelltown' AND source_chapter_key = %s "
            "AND is_current AND v2_is_actionable AND (v2_provision_type IS NULL OR v2_provision_type <> 'TOC') ORDER BY id")


def rules_lost(old_rules, new_text: str) -> int:
    """Numeric rules whose raw_match (whitespace-normalised, lower) is no longer in the new text."""
    rules = old_rules
    if isinstance(rules, str):
        try:
            rules = json.loads(rules)
        except ValueError:
            return 1   # unreadable rules are not "no rules": count as at risk so the fix is refused (cross-review)
    items = rules if isinstance(rules, list) else (rules or {}).get("rules") or []
    hay = re.sub(r"\s+", " ", new_text).strip().lower()
    lost = 0
    for r in items or []:
        if isinstance(r, dict) and r.get("compliance_type") == "numeric_check":
            raw = re.sub(r"\s+", " ", str(r.get("raw_match") or "")).strip().lower()
            if raw and raw not in hay:
                lost += 1
    return lost


def build(pdf: Path, rows: list[dict]):
    import fitz
    sha = pe.sha256_file(pdf)
    with fitz.open(str(pdf)) as doc:
        vis = {pno: visible_texts(p) for pno, p in enumerate(doc, 1)}
        wr = white_report(doc)
    plans = []
    for r in rows:
        p = plan_row(r, vis)
        p["rules_lost"] = rules_lost(r.get("v2_extracted_rules"), p.get("new_text", r["provision_text"] or ""))
        if p["verdict"] == "fix" and p["rules_lost"]:   # a numeric rule would quote words the fix removes
            p = {**p, "verdict": "refused", "reason": f"{p['rules_lost']} numeric rule(s) quote words the fix removes"}
        p["page_check"], p["citation_status"] = r.get("page_check"), r.get("citation_status")
        if p["verdict"] == "fix":
            p["evidence"]["pdf_sha256"] = sha
        plans.append(p)
    return sha, plans, wr


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--write-plan", action="store_true")
    ap.add_argument("--date", default="2026-10-17")
    a = ap.parse_args(argv)
    from state_law_proof import connect
    conn = connect()
    cur = conn.cursor()
    cur.execute("SET statement_timeout = 30000")
    cur.execute(ROWS_SQL, (CHAPTER,))
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    sha, plans, wr = build(Path(a.pdf), rows)
    c = Counter(p["verdict"] for p in plans)
    print(f"rows {len(rows)}  {dict(c)}  refusals {dict(Counter(p['reason'] for p in plans if p['verdict'] == 'refused'))}")
    print("unchanged reasons", dict(Counter(p["reason"] for p in plans if p["verdict"] == "unchanged")))
    print("rules lost on fix rows:", sum(p["rules_lost"] for p in plans if p["verdict"] == "fix"))
    print("white report:", {k: v for k, v in wr.items() if k != "orphans"})
    for p in [x for x in plans if x["verdict"] == "fix"][:5]:
        print("EX", p["id"], repr(p["old_text"][:150]), "->", repr(p["new_text"][:150]))
    if a.write_plan:
        out = ROOT / "data" / f"campbelltown_visible_text_plan_{a.date}.json"
        out.write_text(json.dumps({"pdf_sha256": sha, "chapter": CHAPTER, "date": a.date,
                                   "rows": [p for p in plans if p["verdict"] == "fix"],
                                   "not_fixed": [{k: p[k] for k in ("id", "verdict", "reason", "md5")}
                                                 for p in plans if p["verdict"] != "fix"]},
                                  indent=1, ensure_ascii=False), encoding="utf8")
        print("wrote", out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
