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


#: Words a line is written in when it could be carrying a rule. The canonical
#: definition lives here because both users need it -- ai_extractor imports it as
#: `_RULE_WORDS` for `_rule_bearing_pages`, and `skipped_pages` scores against it.
RULE_WORDS = re.compile(
    r"\b(shall|must|should|required|requirements?|minimum|maximum|controls?|objectives?|"
    r"not permitted|is to be|are to be|provide|retain|avoid|ensure)\b", re.IGNORECASE)


def rule_lines(lines: list[list[str]]) -> list[list[str]]:
    """The sentence lines that could be carrying a rule, or all of them when none
    is. Pure. The fallback keeps a page of pure narrative scored as before, so the
    re-read trigger stays exactly as sensitive as it was on those pages.
    """
    ruled = [w for w in lines if RULE_WORDS.search(" ".join(w))]
    return ruled or lines


def skipped_pages(pages: dict[int, list[str]], output_texts: list[str]) -> list[int]:
    """Page numbers whose RULE-BEARING sentences are mostly absent from the output.

    `pages` maps page number -> that page's text lines; `output_texts` is every
    text the reader returned for the document. Pure.

    Scored against the lines that could hold a rule, not every sentence on the
    page. Counting all of them refused a page from which NOTHING was missing:
    City of Sydney `schedules` page 65 prints clause 11.2(10)(a)-(d) and then a
    30-line "Resources/Notes" commentary about AS 4282-1997. 47 sentence lines, 7
    of them rule-bearing. A correct extraction of the controls matches every one
    of the 7 and scores 14/47 = 0.2979 against PAGE_HIT -- refused by ONE line,
    four times across two sessions, for returning exactly what it should.
    A provision reader is not contracted to transcribe commentary, so commentary
    does not belong in the denominator.

    Measured 2026-10-02 on that page: all lines 14/47 = 0.2979 (refused),
    _OBLIGATION lines 7/7, RULE_WORDS lines 7/13 = 0.5385. The broader RULE_WORDS
    set is used deliberately -- it keeps six commentary lines in the denominator
    ("control of light spill and glare", "requirements for the lighting design of
    pedestrian and road lighting") so the result has margin instead of sitting on
    a cliff at 1.00.

    This cannot blind the guard to the loss it was built for. A page whose rule
    lines are all absent still scores 0 -- Warringah's 21 pages and
    Canterbury-Bankstown 6-2's 33 would score 0 the same as before. And the
    refusal in `ai_extractor._reread_skipped_pages` is already gated on
    `holds_rules` (two or more obligation words), so a page carrying no rule words
    could never refuse a chapter today: narrowing the score changes the number on
    pages that already qualify, not which pages qualify.
    """
    out: set[str] = set()
    for t in output_texts:
        out |= _grams(_WORD.findall((t or "").lower()))
    missing = []
    for pno in sorted(pages):
        lines = sentence_lines(pages[pno])
        if len(lines) < MIN_LINES:
            continue
        scored = rule_lines(lines)
        read = sum(len(_grams(w) & out) / len(_grams(w)) >= LINE_HIT for w in scored)
        if read / len(scored) < PAGE_HIT:
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
