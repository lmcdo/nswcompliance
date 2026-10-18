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
is printed on and the span is a sentence (>= MIN_WORDS_SHARED words, half distinct; matcher v3): then the stored page does hold the words -> proven, and the
evidence lists EVERY page the span is on (`all_pages`) so a reader sees it was ambiguous. No page
is picked: if the stored page is not among them the row stays `unresolved`.
No page -> `not_found`. Fewer than MIN_WORDS words -> `too_short`.
"""
from __future__ import annotations

import hashlib
from collections import Counter
import re
import unicodedata

MIN_WORDS = 3
# A span printed on several pages proves the stored page only if it is a real sentence, not a label
# or a repeated table cell ("3 2 3 height", "queen anne ... queen anne"): >= 10 words, at least
# half of them distinct. User review 2026-10-18 of the first 21 multi-page proofs.
MIN_WORDS_SHARED = 10
MIN_DISTINCT_SHARED = 0.5
MATCHER_VERSION = "page-evidence-v3-shared-page-needs-a-sentence"
ORDERS = ("raw", "sorted", "clean")
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


_SECTION_NO = re.compile(r"^#+\s*(\d+(?:\.\d+)+)(?![\d.])")


def row_heading(provision_text: str | None) -> str | None:
    """The row's own section number from its '# 6.4 e) Design principle' first line, normalised ('6 4'); None when
    the first line carries no dotted section number. Used only to choose among pages that ALL hold the words."""
    m = _SECTION_NO.match((provision_text or "").lstrip())
    return normalise(m.group(1)) if m else None


# A number after one of these words is a cross-reference ("see section 6 4"), not the page's own heading.
_REFERENCE_WORD = re.compile(r"(?:^|\s)(?:see|section|sections|clause|clauses|cl|part|parts|figure|fig|table|"
                             r"control|controls|requirement|requirements|under|in|at|of|to|and|or|with|per|s)\s+$")
#: A heading is printed at the top of the page: within this many words of the page's visual (sorted) order.
HEADING_TOP_WORDS = 40


def heading_pages(heading: str, pages: dict, hits: dict) -> list:
    """Pages of `hits` (page -> match_page() results) whose TOP (first HEADING_TOP_WORDS words of the sorted,
    top-to-bottom reading order) prints the row's section number as whole words, not right after a referencing word.
    Cross-review 2026-10-17: a number anywhere on the page, or merely before the words, can be a cross-reference."""
    pat = re.compile(rf"(?<![a-z0-9]){re.escape(heading)}(?![a-z0-9])")
    out = []
    for pno in hits:
        texts = pages[pno][0]
        words = (texts.get("sorted") or texts.get("raw") or "").split()
        top = " ".join(words[:HEADING_TOP_WORDS])
        if any(not _REFERENCE_WORD.search(top[:h.start()]) for h in pat.finditer(top)):
            out.append(pno)
    return sorted(out)


# -- reading a PDF -------------------------------------------------------------------

def clean_text(page) -> str:
    """The page with text printed twice at the same spot kept once (Campbelltown prints a hidden white copy under
    every line, so the raw text layer stutters; 2026-10-18). Same rule as ai_extractor.doubled_text."""
    seen, parts = set(), []
    for block in page.get_text("dict")["blocks"]:
        for ln in block.get("lines") or []:
            for sp in ln["spans"]:
                t = sp["text"].strip()
                if not t:
                    continue
                k = (t, tuple(round(v) for v in sp["bbox"]))
                if k in seen:
                    continue
                seen.add(k)
                parts.append(t)
    return " ".join(parts)


def page_texts(page) -> dict[str, str]:
    """order -> normalised text of the page."""
    return {"raw": normalise(page.get_text("text")),
            "sorted": normalise(page.get_text("text", sort=True)),
            "clean": normalise(clean_text(page))}


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


def prove(words: str, pages: dict, held=None, primary=None, heading=None):
    """(verdict, evidence-or-None, info) for `words` over every page of a PDF.

    pages: page number -> (texts, prepare(grids)). held: pages the row already points at
    (pdf_page + page_range), primary the row's pdf_page (preferred when it is among the hits;
    with several held hits and no primary match nothing is picked). Verdict: proven | unresolved | not_found | too_short.
    info always carries the pages that matched, so an `unresolved` says where the rival is.
    A span on several pages is proven only on a page in `held`; evidence.all_pages lists all.
    heading (row_heading of the row; DQ-145 step 3, user 2026-10-17): when no held page settles it, the ONE page of
    the hits that also prints the row's own section number is proven (evidence.by_heading); else unresolved.
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
        toks = words.split()
        if len(toks) < MIN_WORDS_SHARED or len(set(toks)) / len(toks) < MIN_DISTINCT_SHARED:
            return "unresolved", None, {"pages": sorted(hits), "reason": "span on several pages is a label or repeated cells"}
        both = sorted(set(held or ()) & set(hits))
        if primary in both:
            pno = primary                  # the row's own page; never swapped for a range member
        elif len(both) == 1:
            pno = both[0]
        elif heading and len(heading_pages(heading, pages, hits)) == 1:
            (pno,) = heading_pages(heading, pages, hits)   # the one page with both the words and the row's heading
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
    if len(hits) > 1 and heading and pno not in set(held or ()):
        ev["by_heading"] = heading
    ev["span_sha256"] = hashlib.sha256(words.encode()).hexdigest()
    return "proven", ev, {"pages": sorted(hits), "alternatives": len(m)}


# -- fallbacks after prove() finds no exact span (DQ-145 council rows, user 2026-10-18) -------------------------------
# Tried ONLY when prove() returns not_found / too_short. Each keeps the one-page rule of prove().
#   full_text       the extractor put most of the rule into our '# code title' line ('# preamble ... O1 To Maintain ...'
#                   with body 'low income'): the row's whole text, dropping leading words of our heading line only and
#                   never the body, is one exact span on exactly one page. Evidence is an ordinary text-run/table-cells
#                   proof of that span, so check_evidence re-reads it unchanged.
#   all_words_label a table or figure prints a rule's words out of order: EVERY distinct word of the rule is on the
#                   page AND the rule's own label (Table/Figure number, or control code C9 / C.48 / O1) is printed there.
#                   Weaker than a span, so it needs >= MIN_WORDS_BAG words and a label.
FALLBACK_VERSION = "page-evidence-fallback-v1"
#: words that change what a rule requires: never among the heading words full_text may drop (cross-review 2026-10-18)
OPERATIVE_WORDS = frozenset("must not no shall may should only unless except prohibited permitted required "
                            "cannot can maximum minimum least more less than exceed exceeding".split())
MIN_WORDS_FULL = 8
MIN_WORDS_BAG = 10
LABEL_WINDOW = 12   # a control code must sit in the heading line or the first words of the body to be the rule's own
_LABEL_TF = re.compile(r"\b(?:Table|Figure)\s+\d+(?:[.\-]\w+)*", re.I)
_LABEL_CODE = re.compile(r"(?<![A-Za-z0-9])[CO]\.?\s?\d{1,3}[a-z]?(?![A-Za-z0-9])")


def full_text_words(provision_text: str | None) -> str:
    """Normalised words of the whole row, '#' heading markers removed (rule_body would drop the first line)."""
    return normalise(re.sub(r"^\s*#+", "", provision_text or ""))


def row_labels(provision_text: str | None) -> list:
    """The rule's own labels, normalised: Table/Figure numbers and control codes (C9, C.48, O1) in its heading line
    or the first LABEL_WINDOW words of its body. [] when it prints none."""
    t = (provision_text or "").lstrip()
    head, _, body = t.partition("\n") if t.startswith("#") else ("", "", t)
    first = " ".join(body.split()[:LABEL_WINDOW])
    out = [normalise(m.group(0)) for m in _LABEL_TF.finditer(head + " " + first)]
    out += [normalise(m.group(0)) for m in _LABEL_CODE.finditer(head + " " + first)]
    return list(dict.fromkeys(x for x in out if x))


def page_words(texts: dict, streams: list) -> set:
    """Every word printed on a page: both reading orders and every table cell."""
    words = set()
    for t in texts.values():
        words.update(t.split())
    for _ti, _kind, _coords, hay, _offs, _parts in streams:
        words.update(hay.split())
    return words


def has_label(label: str, texts: dict) -> bool:
    pat = re.compile(rf"(?<![a-z0-9]){re.escape(label)}(?![a-z0-9])")
    return any(pat.search(t) for t in texts.values())


def _numbers(words: str) -> list:
    """Every number of `words` in order. normalise() splits '1.5m' into '1 5m' and '3.2.4' into '3 2 4': a number
    continues only after a BARE digit token, so neighbouring cells '10m 3m' stay two numbers."""
    out, run = [], []
    for w in words.split() + [""]:
        if w[:1].isdigit() and (not run or run[-1].isdigit()):
            run.append(w)
            continue
        if run:
            out.append(" ".join(run))
        run = [w] if w[:1].isdigit() else []
    return out


def _number_runs(words: str) -> list:
    """Every multi-part number of `words`, once per occurrence ('1 5m', '3 2 4')."""
    return [n for n in _numbers(words) if " " in n]


def number_phrases(words: str) -> list:
    """Every number of `words` as the phrase normalise() leaves it in: '1.5m' -> '1 5m', '3.2.4' -> '3 2 4'. A bag of
    words loses these ('2.5m' would pass on a page printing '2' and '1.5m'), so each must be printed whole."""
    return list(dict.fromkeys(_number_runs(words)))


def phrase_on_page(phrase: str, texts: dict, streams: list) -> bool:
    return any(find_span(t, phrase) for t in texts.values()) or any(find_span(st[3], phrase) for st in streams)


def word_counts(texts: dict, streams: list) -> Counter:
    """How often the page prints each word: the most any one reading of it gives (both reading orders hold the same
    words, so they are not added), plus words only a table cell reading holds."""
    best = Counter()
    for t in texts.values():
        best |= Counter(t.split())
    cells = Counter()
    for st in streams:
        cells |= Counter(st[3].split())
    return best | cells


def phrase_count(phrase: str, texts: dict) -> int:
    return max((len(find_span(t, phrase)) for t in texts.values()), default=0)


def bag_ok(words: str, texts: dict, streams: list, labels=()) -> bool:
    """Every word of `words` is printed on the page at least as often as the rule uses it, and every multi-part number
    is printed whole as often (cross-review 2026-10-18: a set lost '6m' needed twice). Which cell goes with which is
    NOT checked -- the accepted limit of this fallback (user 2026-10-18)."""
    have = word_counts(texts, streams)
    if Counter(words.split()) - have:
        return False
    need = Counter(ph for ph in _number_runs(words))
    if not all(max(phrase_count(ph, texts), int(phrase_on_page(ph, {}, streams))) >= n for ph, n in need.items()):
        return False
    return numbers_in_order(value_words(words, labels), texts, streams)


def value_words(words: str, labels=()) -> str:
    """`words` without the rule's own label phrases ('table 3 2 4 a', 'c9') and without a leading section number
    ('4 3 3 6 communal ...'): those are checked as labels, and only VALUES must keep their order."""
    w = f" {words} "
    for lb in labels:
        w = w.replace(f" {lb} ", " ", 1)
    toks = w.split()
    i = 0
    while i < len(toks) and toks[i][:1].isdigit():
        i += 1
    return " ".join(toks[i:] if i > 1 else toks)


def number_seq(words: str) -> list:
    """The numbers of `words` in order, multi-part numbers whole ('front 6m side 1 5m' -> ['6m', '1 5m'])."""
    return _numbers(words)


def _is_subsequence(need: list, have: list) -> bool:
    it = iter(have)
    return all(any(x == y for y in it) for x in need)


def numbers_in_order(words: str, texts: dict, streams: list) -> bool:
    """The rule's numbers appear in the SAME ORDER in at least one reading of the page: either text order, or one table
    read row by row / column by column. A page printing 'front 3m side 6m' does not prove 'front 6m side 3m'
    (cross-review 2026-10-18). Cell-to-label pairing beyond order is still not checked."""
    need = number_seq(words)
    if len(need) < 2:
        return True
    readings = list(texts.values())
    by_table: dict = {}
    for ti, kind, _coords, hay, _offs, _parts in streams:
        if kind in ("row", "col"):
            by_table.setdefault((ti, kind), []).append(hay)
    readings += [" ".join(v) for v in by_table.values()]
    return any(_is_subsequence(need, number_seq(r)) for r in readings)


def table_or_figure(words: str, labels: list, streams: list) -> bool:
    """The every-word rule is for TABLES AND FIGURES only (user 2026-10-18): the rule's label is a Table/Figure number,
    or every word of it sits inside one table on the page. Prose must prove by exact words."""
    if any(lb.startswith(("table ", "figure ")) for lb in labels):
        return True
    need = set(words.split()) - set(" ".join(labels).split())
    tables: dict = {}
    for ti, _kind, _coords, hay, _offs, _parts in streams:
        tables.setdefault(ti, set()).update(hay.split())
    return any(need <= t for t in tables.values())


def bag_pages(words: str, labels: list, pages: dict) -> list:
    """Pages printing every distinct word of `words` (numbers whole) and at least one of `labels`, where the rule is a
    table or figure."""
    return sorted(p for p, (texts, streams) in pages.items()
                  if bag_ok(words, texts, streams, labels) and any(has_label(lb, texts) for lb in labels)
                  and table_or_figure(words, labels, streams))


def pick_page(hits: list, held=None, primary=None):
    """One page of `hits`, or None: the only hit; else the row's stored page when it is a hit; else the one held hit."""
    if len(hits) == 1:
        return hits[0]
    both = sorted(set(held or ()) & set(hits))
    if primary in both:
        return primary
    return both[0] if len(both) == 1 else None


MIN_PART = 10   # words on each side of a page break


def page_break_hits(words: str, pages: dict) -> list:
    """(page, split, order_a, start_a, order_b, start_b) for every way `words` runs unbroken to the end of a page's
    text block and on, unbroken, on the next page: words[:split] on page P and words[split:] on page P + 1, each at
    least MIN_PART words. Only the page footer/header may sit between the two halves."""
    toks = words.split()
    out = []
    for pno in sorted(pages):
        nxt = pno + 1
        if nxt not in pages:
            continue
        for k in range(MIN_PART, len(toks) - MIN_PART + 1):
            a, b = " ".join(toks[:k]), " ".join(toks[k:])
            ha = [(o, find_span(pages[pno][0][o], a)) for o in ORDERS]
            ha = [(o, s[0]) for o, s in ha if s]
            if not ha:
                continue
            hb = [(o, find_span(pages[nxt][0][o], b)) for o in ORDERS]
            hb = [(o, s[0]) for o, s in hb if s]
            if hb:
                out.append((pno, k, ha[0][0], ha[0][1], hb[0][0], hb[0][1]))
                break
    return out


def prove_fallback(provision_text: str | None, pages: dict, held=None, primary=None):
    """(verdict, evidence-or-None, info) using the two fallbacks above, full_text first. Same one-page rule as prove():
    several pages -> the row's own stored page if it is one of them, else unresolved."""
    full, body = full_text_words(provision_text).split(), rule_words(provision_text).split()
    for k in range(0, max(0, len(full) - len(body)) + 1):        # drop heading words only, never the body
        if len(full) - k < MIN_WORDS_FULL:
            break
        if OPERATIVE_WORDS & set(full[:k]):
            break                                                  # would drop a word that changes the rule
        cand = " ".join(full[k:])
        v, ev, info = prove(cand, pages, held, primary)
        if v == "proven":
            ev.update(fallback="full_text", dropped_head_words=k, fallback_version=FALLBACK_VERSION)
            return v, ev, info
        if v == "unresolved":
            return v, None, info
    words = " ".join(body)
    if len(body) >= 2 * MIN_PART:   # a rule that runs on over a page break: exact words on each side
        breaks = page_break_hits(words, pages)
        starts = sorted({b[0] for b in breaks})
        pno = pick_page(starts, held, primary) if starts else None
        if pno is not None:
            _p, k, oa, sa, ob, sb = next(b for b in breaks if b[0] == pno)
            ev = {"matcher": "page-break", "page": pno, "next_page": pno + 1, "split": k, "order_a": oa,
                  "start_a": sa, "order_b": ob, "start_b": sb, "all_pages": starts, "span": words, "start": 0,
                  "end": len(words), "fallback": "page_break", "fallback_version": FALLBACK_VERSION,
                  "matcher_version": MATCHER_VERSION, "span_sha256": hashlib.sha256(words.encode()).hexdigest()}
            return "proven", ev, {"pages": starts}
        if starts:
            return "unresolved", None, {"pages": starts, "reason": "runs over a page break at several places"}
    labels = row_labels(provision_text)
    if len(body) < MIN_WORDS_BAG or not labels:
        return "not_found", None, {"pages": [], "reason": "no label or too few words for all_words_label"}
    hits = bag_pages(words, labels, pages)
    if not hits:
        return "not_found", None, {"pages": []}
    pno = pick_page(hits, held, primary)
    if pno is None:
        return "unresolved", None, {"pages": hits, "reason": "every word and the label on several pages"}
    texts = pages[pno][0]
    ev = {"matcher": "all-words+label", "page": pno, "all_pages": hits, "span": words, "start": 0, "end": len(words),
          "labels": [lb for lb in labels if has_label(lb, texts)], "row_labels": labels, "fallback": "all_words_label",
          "fallback_version": FALLBACK_VERSION, "matcher_version": MATCHER_VERSION,
          "span_sha256": hashlib.sha256(words.encode()).hexdigest()}
    return "proven", ev, {"pages": hits}
