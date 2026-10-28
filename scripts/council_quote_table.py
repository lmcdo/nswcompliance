"""Prove a table rule cell by cell: council_quote.judge calls this when a rule is not printed whole.

prior-art-checked: council_quote proves running text only. A PDF's text layer reads a table's cells in column or
interleaved order, so a row like "Bulky goods premises | 1 space per 45sq.m GFA" is never printed as one string,
and 220 of 782 unproven re-read rules (2026-10-13) were tables. The reader now writes each printed table row as
"cell | cell | cell" (scripts/ai_extractor.py brief), which this checks.

A row is proven when, on one page (the stored page or the one either side):
  - every cell is printed whole (its own words, in order) somewhere on that page,
  - all cells sit on one printed row: their first lines are within ROW_DY points of the first cell's, and
  - they run left to right in the order written.
The quote is the council's own text of each cell, copied from the PDF, joined with " | ". Every line of the rule
must be such a row (a rule mixing prose and a table is left to the other checks).
"""
from __future__ import annotations

import collections

WRAP_MAX = 4        # a wrapped cell spans at most this many printed lines
WRAP_DY = 16.0      # points: consecutive lines of one wrapped cell are at most this far apart
ROW_DY = 6.0       # points: cells of one printed row start within this height of each other
MIN_CELLS = 2


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.split("|") if c.strip()]


def prove_rows(body: str, streams, page: int | None, norm) -> dict | None:
    """{'quote', 'quote_page'} when every line of `body` is a proven table row, else None."""
    lines = [ln for ln in body.splitlines() if ln.strip()]
    rows = [ln for ln in lines if len(_cells(ln)) >= MIN_CELLS]
    # A table rule may carry its lead-in sentence or its caption ("Table 3.2.5-a: Facade Articulation"), Hornsby
    # 2026-10-28. Each such line must be printed WHOLE on the table's page or the one either side, and the table
    # itself must still be two or more proven rows.
    if not lines or len(rows) < (MIN_CELLS if len(rows) < len(lines) else 1):
        return None
    # ...and only BEFORE the table or AFTER it: a plain line between two rows is a wrapped half-row the reader split
    # off, and copying it would print the table scrambled (Ashfield 249834, fleet run 2026-10-28)
    is_row = [len(_cells(ln)) >= MIN_CELLS for ln in lines]
    first, last = is_row.index(True), len(is_row) - 1 - is_row[::-1].index(True)
    if not all(is_row[first:last + 1]):
        return None
    for st in streams:
        pages = [p for p in ((page, page - 1, page + 1) if page else ()) if p and p >= 1]
        for p in pages:
            out = []
            for ln in lines:
                if len(_cells(ln)) < MIN_CELLS:
                    q = norm(ln)
                    k = next((k for k in st.find_all(q, cap=200) if abs(st.page(k) - p) <= 1
                              and _whole_lines(st, k, k + len(q) - 1)), None) if q else None
                    if k is None:
                        break
                    out.append(st.copy(k, k + len(q) - 1))
                    continue
                row = _prove_row(_cells(ln), st, p, norm)
                if row is None:
                    break
                out.append(row)
            else:
                return {"quote": "\n".join(out), "quote_page": p}
    return None


def _has_neighbour(st, i: int) -> bool:
    """Text printed beside line i in a column to its right: then line i starts a ROW of its own (a compact table's
    next row, "Bulky goods premises | 1 space per 45sq.m"), not the second line of a wrapped cell (cross-review)."""
    ln = st.lines[i]
    return any(o.page == ln.page and o.x > ln.x + 2 and abs(o.y - ln.y) < 3 for o in st.lines)


def _whole_lines(st, k: int, e: int) -> bool:
    """The match [k, e] starts at the first character of its line and ends at the last of its line: a lead-in or
    caption printed whole, not part of a longer printed line (cross-review)."""
    i0, i1 = st.at[k][0], st.at[e][0]
    return (k == 0 or st.at[k - 1][0] != i0) and (e + 1 >= len(st.at) or st.at[e + 1][0] != i1)


def _wrapped_hits(q: str, st, page: int, norm) -> list[tuple[int, list[int]]]:
    """Lines where a cell printed over WRAP_MAX consecutive lines of one column starts ("For facades that" /
    "face a street", Hornsby 2026-10-28). The cell must cover those lines exactly -- from the start of the first to
    the end of the last -- and the lines must be one column: same left edge, each within WRAP_DY of the one above."""
    col = collections.defaultdict(list)
    for i, ln in enumerate(st.lines):
        if ln.page == page:
            col[round(ln.x / 2)].append(i)
    out = []
    for idx in col.values():
        idx.sort(key=lambda i: st.lines[i].y)
        for a in range(len(idx)):
            joined = ""
            for b in range(a, min(a + WRAP_MAX, len(idx))):
                if b > a and (not 0 < st.lines[idx[b]].y - st.lines[idx[b - 1]].y <= WRAP_DY
                              or _has_neighbour(st, idx[b])):
                    break
                joined += norm(st.text[idx[b]])
                if b > a and joined == q:
                    out.append((idx[a], idx[a:b + 1]))
                if len(joined) >= len(q):
                    break
    return out


def _prove_row(cells: list[str], st, page: int, norm) -> str | None:
    hits = []
    for c in cells:
        q = norm(c)
        if not q:
            return None
        # a cell must be printed within ONE line: a match running on into the next line could join the next row's
        # text to this one (cross-review). A cell wrapped over two lines stays unproven -- the safe direction.
        found = [(st.at[k][0], st.copy(k, k + len(q) - 1)) for k in st.find_all(q, cap=200)
                 if st.page(k) == page and st.at[k][0] == st.at[k + len(q) - 1][0]]
        # ...unless it is printed over consecutive lines of one column and covers them exactly (_wrapped_hits)
        found += [(first, " ".join(st.text[i].strip() for i in span)) for first, span in _wrapped_hits(q, st, page, norm)]
        if not found:
            return None
        hits.append(found)
    # choose one placement per cell: same printed row as the first cell, left to right
    for i0, t0 in hits[0]:
        y0 = st.lines[i0].y
        x0 = st.lines[i0].x
        # the row band comes from the table itself: half the gap to the nearest other line in the first cell's
        # column, never more than ROW_DY -- so a compact table's next row can never fall inside it (cross-review)
        gaps = [abs(ln.y - y0) for ln in st.lines if ln.page == page and abs(ln.x - x0) <= 2 and ln.y != y0]
        band = min([ROW_DY] + [g / 2 for g in gaps])
        x_prev = x0
        chosen = [t0]
        for cell_hits in hits[1:]:
            ok = [(i, t) for i, t in cell_hits
                  if abs(st.lines[i].y - y0) < band and st.lines[i].x > x_prev]
            if not ok:
                break
            i, t = min(ok, key=lambda h: st.lines[h[0]].x)
            chosen.append(t)
            x_prev = st.lines[i].x
        else:
            return " | ".join(chosen)
    return None
