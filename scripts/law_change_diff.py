#!/usr/bin/env python3
"""List the passages of an NSW instrument that changed between two dates (DQ-88 review).

prior-art-checked: reuse not viable because the 2026-09-15 refresh did this by hand in a
scratchpad (memory: reference-law-text-refresh-method-2026-09) and nothing in scripts/ diffs two
in-force versions; update_instrument_provisions.py only clears the flag after a review.

Runs where legislation.nsw.gov.au answers (the Fly legislation monitor's IP; it returns 403 to
local machines). Fetches the whole instrument as in force on DATE and as in force today,
normalises both the way the 2026-09-15 method did (tags to spaces, collapse whitespace, no space
before , . ; :), splits on block elements, and prints every paragraph that was removed or added,
each under the nearest preceding heading. It decides nothing: a human reads the output against
what we store.

    python3 law_change_diff.py epi-2015-0239 2026-05-12 [--json]
"""
from __future__ import annotations

import difflib
import html
import json
import re
import sys

import requests

BASE = "https://legislation.nsw.gov.au/view/whole/html/inforce/{when}/{epi}"
BLOCK = re.compile(r"<(?:p|h[1-6]|li|tr|div)\b[^>]*>", re.I)
HEAD = re.compile(r"^(?:Part|Division|Schedule|Zone|\d+[A-Z]*\.?\d*[A-Z]*)\b")


def fetch(epi: str, when: str) -> str:
    r = requests.get(BASE.format(when=when, epi=epi), timeout=120, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.text


def paragraphs(page: str) -> list[str]:
    """Block-level text, normalised; script/style dropped."""
    page = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", page)
    out = []
    for chunk in BLOCK.split(page):
        t = html.unescape(re.sub(r"<[^>]+>", " ", chunk))
        t = re.sub(r"\s+", " ", t).strip()
        t = re.sub(r" ([,.;:])", r"\1", t)
        if t:
            out.append(t)
    return out


def diff(old: list[str], new: list[str]) -> list[dict]:
    changes, heading = [], ""
    sm = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        for t in new[j1:j2] if tag == "equal" else []:
            if HEAD.match(t) and len(t) < 160:
                heading = t
        if tag == "equal":
            continue
        for t in old[i1:i2]:
            changes.append({"heading": heading, "op": "removed", "text": t})
        for t in new[j1:j2]:
            if HEAD.match(t) and len(t) < 160:
                heading = t
            changes.append({"heading": heading, "op": "added", "text": t})
    return changes


def main(argv: list[str]) -> int:
    epi, when = argv[0], argv[1]
    old, new = paragraphs(fetch(epi, when)), paragraphs(fetch(epi, "current"))
    changes = diff(old, new)
    if "--json" in argv:
        print(json.dumps({"epi": epi, "from": when, "old_paragraphs": len(old),
                          "new_paragraphs": len(new), "changes": changes}))
        return 0
    print(f"{epi}: {when} -> current; {len(old)} -> {len(new)} paragraphs; {len(changes)} changed")
    for c in changes:
        print(f"  [{c['op']}] {c['heading'][:60]} | {c['text'][:300]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
