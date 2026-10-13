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

ROW_DY = 6.0       # points: cells of one printed row start within this height of each other
MIN_CELLS = 2


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.split("|") if c.strip()]


def prove_rows(body: str, streams, page: int | None, norm) -> dict | None:
    """{'quote', 'quote_page'} when every line of `body` is a proven table row, else None."""
    lines = [ln for ln in body.splitlines() if ln.strip()]
    if not lines or not all(len(_cells(ln)) >= MIN_CELLS for ln in lines):
        return None
    for st in streams:
        pages = [p for p in ((page, page - 1, page + 1) if page else ()) if p and p >= 1]
        for p in pages:
            out = []
            for ln in lines:
                row = _prove_row(_cells(ln), st, p, norm)
                if row is None:
                    break
                out.append(row)
            else:
                return {"quote": "\n".join(out), "quote_page": p}
    return None


def _prove_row(cells: list[str], st, page: int, norm) -> str | None:
    hits = []
    for c in cells:
        q = norm(c)
        if not q:
            return None
        found = [k for k in st.find_all(q, cap=200) if st.page(k) == page]
        if not found:
            return None
        hits.append([(k, k + len(q) - 1) for k in found])
    # choose one placement per cell: same printed row as the first cell, left to right
    for k0, e0 in hits[0]:
        y0 = st.lines[st.at[k0][0]].y
        x_prev = st.lines[st.at[k0][0]].x
        chosen = [(k0, e0)]
        for cell_hits in hits[1:]:
            ok = [(k, e) for k, e in cell_hits
                  if abs(st.lines[st.at[k][0]].y - y0) <= ROW_DY and st.lines[st.at[k][0]].x > x_prev]
            if not ok:
                break
            k, e = min(ok, key=lambda h: st.lines[st.at[h[0]][0]].x)
            chosen.append((k, e))
            x_prev = st.lines[st.at[k][0]].x
        else:
            return " | ".join(st.copy(k, e) for k, e in chosen)
    return None
