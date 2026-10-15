#!/usr/bin/env python3
"""Served rules whose words run back and forth across a two-column page's gutter (a column splice).

prior-art-checked: reuse not viable -- the council-words check (quote_status) compares a rule with the PDF's text
layer, and on a two-column page that layer is itself interleaved, so a splice reads as 'exact'. Hornsby DCP 2024
Parts 1 and 3: 9 of 20 rules in the 2026-10-15 address audit were splices, every one quote_status 'exact'
(~/.claude/plans/ce-council-words-probes/audit-2026-10-15/run2/labels.jsonl). Nothing in scripts/ reads word
POSITIONS on the page (grep get_text("words") 2026-10-15: only the figure/outline tools).

Method, deterministic: each 3-word window of the rule is placed where it is printed (PyMuPDF "words" carry x, y).
A splice reads straight across the gutter at one height; a real rule never does, except across a drawn table row.
See same_row_jumps.

    python scripts/dq_probe_column_splice.py --council hornsby [--chapter part-1-general] [--ids 1,2] [--show]

Exit 0 always: this is a probe that reports a count, not a gate.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import urllib.request
from pathlib import Path

W = re.compile(r"[a-z0-9]+")
R2 = "https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/"
CACHE = Path(os.environ.get("SPLICE_PDF_CACHE", Path.home() / ".cache" / "splice_pdfs"))


def toks(text: str) -> list[str]:
    return W.findall((text or "").lower())


def same_row_jumps(rule_text: str, page: dict) -> int | None:
    """How often the rule's next stored line is printed across the page centre at the SAME height (within 12pt).

    Each stored line of the rule is placed where its first words are printed (PyMuPDF "words" carry x, y; the
    occurrence nearest the previous line). A rule read down one column never jumps; a rule continued from the foot of
    the left column to the head of the right jumps to a line far ABOVE. Two columns read row by row -- what the
    interleaved text layer does -- jump at one height, including a one-line heading of the other column dropped into
    the sentence ("... where opportunities / Desired Outcomes / for deep soil ..."). Not counted when either line
    is level with a drawn table cell: a table row is read across on purpose.
    None when fewer than 60% of the lines are found on the page.
    """
    # "# <code> <title>" is the pipeline's own header line, not printed text
    lines = [toks(ln) for ln in (rule_text or "").splitlines() if not ln.lstrip().startswith("#")]
    lines = [ln for ln in lines if ln]
    if len(lines) < 2:
        return 0
    words, centre, cells = page["words"], page["centre"], page["cells"]
    pw = [w for w, _x, _y in words]
    pts, found = [], 0
    for ln in lines:
        head = ln[:3]
        cand = [j for j in range(len(pw) - len(head) + 1) if pw[j:j + len(head)] == head]
        if not cand:
            pts.append(None)
            continue
        found += 1
        prev = next((q for q in reversed(pts) if q is not None), None)
        j = min(cand, key=lambda j: 0 if prev is None else abs(words[j][2] - prev[1]) + abs(words[j][1] - prev[0]) / 4)
        pts.append((words[j][1], words[j][2]))
    if found < 0.6 * len(lines):
        return None
    def in_cell(x, y):
        # a drawn cell at this height anywhere on the row: tables here shade only some cells (Hornsby p29 shades the
        # use column; the rate cells beside it are blank)
        return any(y0 - 1 <= y + 4 <= y1 + 1 for x0, y0, x1, y1 in cells)
    placed = [q for q in pts if q is not None]
    jumps = 0
    for (x1, y1), (x2, y2) in zip(placed, placed[1:]):
        if (x1 < centre) != (x2 < centre) and abs(y1 - y2) <= 12 and not (in_cell(x1, y1) or in_cell(x2, y2)):
            jumps += 1
    return jumps


def page_words(pdf: Path, page: int) -> dict:
    import fitz
    with fitz.open(str(pdf)) as d:
        if not 1 <= page <= d.page_count:
            return {"words": [], "centre": 0.0, "cells": []}
        pg = d[page - 1]
        out = []
        for x0, y0, _x1, _y1, word, *_ in pg.get_text("words"):
            for t in toks(word):
                out.append((t, x0, y0))
        cells = [(it[1].x0, it[1].y0, it[1].x1, it[1].y1) for dr in pg.get_drawings() for it in dr["items"]
                 if it[0] == "re" and it[1].height >= 8 and it[1].width >= 40]
        return {"words": out, "centre": pg.rect.width / 2, "cells": cells}


def pdf_for(path: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (hashlib.sha1(path.encode()).hexdigest() + ".pdf")
    if not f.exists():
        req = urllib.request.Request(R2 + path, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=300) as r:
            f.write_bytes(r.read())
    return f


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--council", required=True)
    ap.add_argument("--chapter")
    ap.add_argument("--ids")
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=20)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = 30000")
    sql = ("SELECT id, provision_text, pdf_page, COALESCE(page_source_path, quote_source_path) FROM regulatory_provisions "
           "WHERE is_current AND v2_is_actionable AND source_council = %s AND pdf_page IS NOT NULL")
    args: list = [a.council]
    if a.chapter:
        sql += " AND source_chapter_key = %s"
        args.append(a.chapter)
    if a.ids:
        sql += " AND id = ANY(%s)"
        args.append([int(x) for x in a.ids.split(",")])
    cur.execute(sql, args)
    rows = cur.fetchall()
    pages: dict = {}
    spliced, unplaced = [], 0
    for rid, text, page, path in rows:
        if not path:
            unplaced += 1
            continue
        key = (path, page)
        if key not in pages:
            pages[key] = page_words(pdf_for(path), page)
        n = same_row_jumps(text, pages[key])
        if n is None:
            unplaced += 1
            if a.show:
                print(f"  unplaced {rid} p{page}")
            continue
        if n >= 1:
            spliced.append(rid)
            if a.show:
                print(f"  SPLICE {rid} p{page} same-height jumps={n}: {(text or '')[:100]!r}")
    print(f"{a.council}{'/' + a.chapter if a.chapter else ''}: rules {len(rows)} | spliced across the gutter "
          f"{len(spliced)} | not placed on their page {unplaced}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
