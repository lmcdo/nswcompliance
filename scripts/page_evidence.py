"""Deterministic page proof for a served council DCP rule: pinned PDF, matcher, evidence.

prior-art-checked: scripts/rule_page_locator.py scores 6-word pieces and tolerates a
half-matched rule (HOLD 0.5) -- right for "which page", wrong for "prove it": it cannot say
which words matched where, so a second person cannot re-derive its verdict. This module is
the strict counterpart for the rows it leaves not_found / unresolved / too_short (DQ-145).
No model is called anywhere. Nothing here touches the database.

A proof is an EVIDENCE dict that scripts/verify_page_evidence.py re-derives from the PDF alone:

  text-run     the rule's whole normalised word sequence is one contiguous span of ONE page's
               normalised text, in one of two PyMuPDF reading orders. Evidence: pdf sha256,
               page, order, char start/end in the page's normalised text, and the span itself.
  table-cells  the same sequence is contiguous in the cells of ONE table of ONE page, read as
               a row, a column, or header-row + one data row. Evidence: pdf sha256, page,
               table index, the (row, col) of every cell used (merged cells are None and never
               used -- PyMuPDF Table.extract(), never to_markdown), char start/end in the
               normalised stream of those cells, and the span itself.

Fail closed: the span must lie on exactly ONE page of the whole PDF (any matcher, any order),
EXCEPT when the row's own stored page (pdf_page or a page of page_range) is one of the pages it
is printed on (matcher v2): then the stored page does hold the words -> proven, and the
evidence lists EVERY page the span is on (`all_pages`) so a reader sees it was ambiguous. No page
is picked: if the stored page is not among them the row stays `unresolved`.
No page -> `not_found`. Fewer than MIN_WORDS words -> `too_short`.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

MIN_WORDS = 3
MATCHER_VERSION = "page-evidence-v2-stored-page-among-several"
ORDERS = ("raw", "sorted")
_WORD = re.compile(r"[a-z0-9]+")
_BULLETS = re.compile("[•‣▪●◦⁃∙·]")
_SOFT = re.compile("[­​‌‍⁠﻿]")
_HYPH_BREAK = re.compile("(\\w)[-‐‑]\\s*\\n\\s*([a-z])")
_UNIT_M2 = re.compile("\\bm\\s*(?:2|²)(?!\\d)")
_UNIT_M3 = re.compile("\\bm\\s*(?:3|³)(?!\\d)")
_NUM_UNIT = re.compile(r"(?<=\d)\s+(?=(?:m2|m3|m|mm|cm|km|ha)\b)")


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalise(text: str | None) -> str:
    """Words of `text` joined by single spaces. Same function on rule and page, so a
    difference here can never make one side match what the other does not print.

    Ligatures and width forms fold (NFKC), soft hyphens go, a word hyphenated across a line
    break is rejoined, bullets go, 'm 2' / 'm2' -> 'm2', '4 m' -> '4m'. Lower case, letters
    and digits only. Deliberately NOT done: synonyms, '&' -> 'and', plurals.
    """
    t = unicodedata.normalize("NFKC", text or "")
    t = _SOFT.sub("", t)
    t = _HYPH_BREAK.sub(r"\1\2", t)
    t = _BULLETS.sub(" ", t).lower()
    t = _UNIT_M2.sub("m2", t)
    t = _UNIT_M3.sub("m3", t)
    t = _NUM_UNIT.sub("", t)
    return " ".join(_WORD.findall(t))


def rule_body(text: str | None) -> str:
    """The council's words: our own '# code title' first line is dropped (as rule_page_locator)."""
    t = (text or "").lstrip()
    if t.startswith("#"):
        _h, _, rest = t.partition("\n")
        if rest.strip():
            return rest
    return t


def rule_words(provision_text: str | None) -> str:
    return normalise(rule_body(provision_text))


# -- reading a PDF -------------------------------------------------------------------

def page_texts(page) -> dict[str, str]:
    """order -> normalised text of the page."""
    return {"raw": normalise(page.get_text("text")),
            "sorted": normalise(page.get_text("text", sort=True))}


def page_tables(page) -> list:
    """Cell grids (None = merged cell) of the page's ruled tables, in PyMuPDF's order."""
    try:
        tf = page.find_tables(strategy="lines")
    except Exception:  # noqa: BLE001 -- a page with no readable tables simply has none
        return []
    return [t.extract() for t in tf.tables]


def _cell_words(cell) -> str:
    return normalise(cell) if cell else ""


def table_streams(grid) -> list:
    """(kind, ordered [(row, col)] of the non-empty cells) for every row, column and
    header-row + data-row reading of one table. The stream a matcher searches is those
    cells' words in that order."""
    out = []
    nrow = len(grid)
    ncol = max((len(r) for r in grid), default=0)

    def cells(coords):
        return [(r, c) for r, c in coords if c < len(grid[r]) and _cell_words(grid[r][c])]

    for r in range(nrow):
        out.append(("row", cells([(r, c) for c in range(ncol)])))
    for c in range(ncol):
        out.append(("col", cells([(r, c) for r in range(nrow)])))
    if nrow > 1:
        head = [(0, c) for c in range(ncol)]
        for r in range(1, nrow):
            out.append(("header+row", cells(head + [(r, c) for c in range(ncol)])))
    return out


def stream_text(grid, coords):
    """Normalised words of `coords` cells joined; char offset where each cell starts; cell words."""
    parts, offs, pos = [], [], 0
    for r, c in coords:
        w = _cell_words(grid[r][c])
        offs.append(pos)
        parts.append(w)
        pos += len(w) + 1
    return " ".join(parts), offs, parts


def find_span(hay: str, needle: str) -> list:
    """Every start of `needle` in `hay` that begins and ends on a word boundary."""
    out, i = [], hay.find(needle)
    while i != -1:
        j = i + len(needle)
        if (i == 0 or hay[i - 1] == " ") and (j == len(hay) or hay[j] == " "):
            out.append(i)
        i = hay.find(needle, i + 1)
    return out


def cells_for_span(offs, texts, start: int, end: int) -> list:
    """Indices of the cells a [start, end) span of the joined stream touches."""
    return [i for i, (o, t) in enumerate(zip(offs, texts)) if o < end and o + len(t) > start]


def prepare(grids: list) -> list:
    """Every table reading of a page, built once: (table, kind, coords, text, cell offsets, cell words)."""
    out = []
    for ti, grid in enumerate(grids):
        for kind, coords in table_streams(grid):
            if coords:
                hay, offs, parts = stream_text(grid, coords)
                out.append((ti, kind, coords, hay, offs, parts))
    return out


def match_page(words: str, texts: dict, streams: list) -> list:
    """Every proof of `words` on one page (before the one-page-only rule is applied)."""
    found = []
    for order in ORDERS:
        for s in find_span(texts[order], words):
            found.append({"matcher": "text-run", "order": order, "start": s,
                          "end": s + len(words), "span": words})
    for ti, kind, coords, hay, offs, parts in streams:
        for s in find_span(hay, words):
            used = cells_for_span(offs, parts, s, s + len(words))
            rel = s - offs[used[0]]          # offsets are within the USED cells' own stream
            found.append({"matcher": "table-cells", "table": ti, "reading": kind,
                          "cells": [list(coords[i]) for i in used],
                          "start": rel, "end": rel + len(words), "span": words})
    return found


def prove(words: str, pages: dict, held=None, primary=None):
    """(verdict, evidence-or-None, info) for `words` over every page of a PDF.

    pages: page number -> (texts, prepare(grids)). held: pages the row already points at
    (pdf_page + page_range), primary the row's pdf_page (preferred when it is among the hits;
    with several held hits and no primary match nothing is picked). Verdict: proven | unresolved | not_found | too_short.
    info always carries the pages that matched, so an `unresolved` says where the rival is.
    A span on several pages is proven only on a page in `held`; evidence.all_pages lists all.
    """
    if len(words.split()) < MIN_WORDS:
        return "too_short", None, {"pages": []}
    hits = {}
    for pno, (texts, grids) in pages.items():
        m = match_page(words, texts, grids)
        if m:
            hits[pno] = m
    if not hits:
        return "not_found", None, {"pages": []}
    if len(hits) > 1:
        both = sorted(set(held or ()) & set(hits))
        if primary in both:
            pno = primary                  # the row's own page; never swapped for a range member
        elif len(both) == 1:
            pno = both[0]
        else:                              # none held, or several range members and no primary: no pick
            return "unresolved", None, {"pages": sorted(hits), "reason": "span printed on several pages"}
    else:
        (pno,) = hits
    m = hits[pno]
    m.sort(key=lambda x: (x["matcher"] != "text-run", x.get("order", ""), x["start"]))
    ev = dict(m[0])
    ev["page"] = pno
    ev["all_pages"] = sorted(hits)
    ev["matcher_version"] = MATCHER_VERSION
    ev["span_sha256"] = hashlib.sha256(words.encode()).hexdigest()
    return "proven", ev, {"pages": sorted(hits), "alternatives": len(m)}
