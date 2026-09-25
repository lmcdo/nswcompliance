"""Which pages did a reading leave out? Counted by code, not by the model.

The AI reader returns SOMETHING for every batch of pages, so the chunk-loss
guard (a batch returning nothing) stays quiet -- while the model silently skips
pages inside the batch. Measured 2026-09-25: the Warringah DCP re-read left out
most of 21 of 226 pages (G1 Dee Why, G5, G9 Frenchs Forest, E1, E11 ...); 172
live rules whose words ARE printed would have been deleted. Canterbury-Bankstown
6-2, committed the day before, is missing 33 pages of objectives and principles.

The check: every sentence-like line on a page (six or more words) should appear
in what the reader returned. A page where most of them do not was skipped.

Two things in real PDFs made a naive version cry wolf, and are handled:
* Campbelltown draws every line twice, one copy on top of the other: identical
  lines on a page count once.
* Canterbury-Bankstown map labels are letter-spaced ("S a l t  P a n"): a line
  that is mostly single letters is a label, not a sentence.

prior-art-checked: reuse not viable because ai_extractor._rule_bearing_pages
only asks whether a page COULD hold a rule (for empty batches); nothing compares
a page's own lines with what the reader returned for it. Lines come from
PyMuPDF (as citation_proof does) because pypdf merges the doubled copies into
one line and they no longer match.
"""
from __future__ import annotations

import re

_WORD = re.compile(r"[a-z0-9]+")
#: A line with fewer words is a heading, label or caption, not a sentence.
MIN_WORDS = 6
#: A page with fewer sentence lines than this is a figure, map or cover.
MIN_LINES = 5
#: A line counts as read when half its four-word runs are in the output.
LINE_HIT = 0.5
#: A page is skipped when fewer than this share of its sentence lines were read.
PAGE_HIT = 0.3


def _grams(words: list[str]) -> set[str]:
    return {" ".join(words[i:i + 4]) for i in range(max(0, len(words) - 3))}


def sentence_lines(texts: list[str]) -> list[list[str]]:
    """The sentence-like lines of one page, each as its words. Pure."""
    seen, out = set(), []
    for text in texts:
        words = _WORD.findall(text.lower())
        if len(words) < MIN_WORDS or sum(len(w) == 1 for w in words) > len(words) / 2:
            continue
        key = " ".join(words)
        if key in seen:            # the same line drawn twice
            continue
        seen.add(key)
        out.append(words)
    return out


def skipped_pages(pages: dict[int, list[str]], output_texts: list[str]) -> list[int]:
    """Page numbers whose sentences are mostly absent from the output. Pure.

    `pages` maps page number -> that page's text lines; `output_texts` is every
    text the reader returned for the document.
    """
    out: set[str] = set()
    for t in output_texts:
        out |= _grams(_WORD.findall((t or "").lower()))
    missing = []
    for pno in sorted(pages):
        lines = sentence_lines(pages[pno])
        if len(lines) < MIN_LINES:
            continue
        read = sum(len(_grams(w) & out) / len(_grams(w)) >= LINE_HIT for w in lines)
        if read / len(lines) < PAGE_HIT:
            missing.append(pno)
    return missing


#: Words a control is written in. A page still left out after its re-read
#: refuses the chapter only if it carries at least RULE_WORDS_MIN of them.
#: Warringah 2026-09-25: the 4 pages the model still passed over (amendment
#: table, definitions x2, suburb history) held 0, 0, 1, 0; the 17 it recovered
#: held up to 6.
_OBLIGATION = re.compile(r"\b(must|shall|is to be|are to be|is required|are required|"
                         r"not permitted|prohibited|minimum|maximum|not exceed)\b")
RULE_WORDS_MIN = 2


def holds_rules(texts: list[str]) -> bool:
    """True when a page's text carries the words controls are written in. Pure."""
    return len(_OBLIGATION.findall(" ".join(texts).lower())) >= RULE_WORDS_MIN


def pdf_page_lines(pdf_path: str) -> dict[int, list[str]]:
    """page number -> text lines, read with PyMuPDF."""
    import fitz
    out: dict[int, list[str]] = {}
    with fitz.open(str(pdf_path)) as doc:
        for pno, page in enumerate(doc, 1):
            out[pno] = [" ".join(s["text"] for s in ln["spans"])
                        for block in page.get_text("dict")["blocks"]
                        for ln in block.get("lines") or []]
    return out


def runs(pages: list[int], limit: int) -> list[tuple[int, int]]:
    """Consecutive pages as (first, last) runs of at most `limit` pages. Pure."""
    out: list[tuple[int, int]] = []
    for p in sorted(pages):
        if out and p == out[-1][1] + 1 and p - out[-1][0] < limit:
            out[-1] = (out[-1][0], p)
        else:
            out.append((p, p))
    return out
