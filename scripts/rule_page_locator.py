"""Which page of a PDF a DCP rule is on, and what page number that page prints. Pure.

prior-art-checked: citation_proof._anchors locates a rule's wording but uses the stored
page only to ORDER its tries and never reports whether that page holds the rule;
dcp_extract_changed.assign_pages_from_markers settles pages only on the page-range path.
The AI reader path (ai_extractor.ai_extract_chapter) stored the first page of its
12-page chunk for every rule it returned (measured 2026-09-26 over all 237 served
chapter PDFs: 45% of 17,489 served rules linked to a page that does not hold them).

One definition, used by the reader when it writes a page and by
scripts/dcp_page_repair.py when it checks and corrects the stored ones:

  * a page HOLDS a rule only when the rule's words are printed there IN ORDER: an 8-word
    run of it (running onto the next page is allowed), or citation_proof's 6-word anchors.
    80% of the same common words is used to FIND candidate pages, never to accept one;
  * several equally good pages and no way to choose = no answer, never a guess.
"""
from __future__ import annotations

import re
from collections import Counter

_WORD = re.compile(r"[a-z0-9]+")
HOLD_SHARE = 0.8
PHRASE = 8           # words in an ordered run
PHRASE_TRIES = 6     # runs tried, from the start of the rule, every 4 words
MIN_WORDS = 4        # fewer content words than this cannot be located honestly

VERDICTS = ("on_page", "moved", "unresolved", "not_found", "too_short", "no_source")


def tokens(text: str | None) -> list[str]:
    return _WORD.findall((text or "").lower())


def rule_body(text: str | None) -> str:
    """The council's words: our own '# code title' first line is dropped."""
    t = (text or "").lstrip()
    if t.startswith("#"):
        _head, _, rest = t.partition("\n")
        if rest.strip():
            return rest
    return t


def content_words(text: str | None) -> list[str]:
    return [w for w in tokens(rule_body(text)) if len(w) > 3]


class Pages:
    """A document's page texts, indexed once. `pages` maps 1-based page -> text."""

    def __init__(self, pages: dict[int, str]):
        toks = {p: tokens(t) for p, t in pages.items()}
        self.sets = {p: set(ws) for p, ws in toks.items()}
        self.joined = {p: " ".join(ws) for p, ws in toks.items()}

    def share(self, words: list[str], pages: list[int]) -> float:
        s = set().union(*(self.sets.get(p, set()) for p in pages))
        return sum(w in s for w in words) / len(words) if words else 0.0

    def phrase_on(self, rule_tokens: list[str], page: int) -> bool:
        """An ordered 8-word run of the rule printed on this page (or running onto the next)."""
        text = " ".join(x for x in (self.joined.get(page, ""), self.joined.get(page + 1, "")) if x)
        if not text or len(rule_tokens) < PHRASE:
            return False
        starts = list(range(0, len(rule_tokens) - PHRASE + 1, 4))[:PHRASE_TRIES]
        return any(" ".join(rule_tokens[o:o + PHRASE]) in text for o in starts)

    def _starts_here(self, words: list[str], page: int) -> bool:
        one = self.share(words, [page])
        return one >= HOLD_SHARE or (one >= 0.3 and self.share(words, [page, page + 1]) >= HOLD_SHARE)

    def candidates(self, words: list[str]) -> list[int]:
        """Pages where the rule starts, by word share (whole page, or over a page break)."""
        full = [p for p in sorted(self.sets) if self.share(words, [p]) >= HOLD_SHARE]
        return full or [p for p in sorted(self.sets) if self._starts_here(words, p)]


def locate(text: str | None, pages: Pages, stored: int | None = None,
           window: range | None = None, anchor_pages=frozenset()) -> tuple[int | None, str]:
    """-> (page, verdict). verdict: on_page | moved | unresolved | not_found | too_short.

    stored: the page currently recorded. window: pages the rule must lie in when known
    (the reader's chunk). anchor_pages: start pages found independently (citation_proof).
    `page` is the page to link to, or None when the stored one must be left alone.
    """
    words = content_words(text)
    rt = tokens(rule_body(text))
    if len(words) < MIN_WORDS:
        return None, "too_short"
    anchors = set(anchor_pages)
    # The stored page must show the rule's words IN ORDER (an 8-word run here, or citation_proof's
    # 6-word anchors): 80% of the same common words can sit on a page that does not hold the rule.
    if stored and (stored in anchors or pages.phrase_on(rt, stored)):
        return stored, "on_page"
    found = pages.candidates(words)
    # A candidate must print the rule in order too: a page holding only the same common words
    # would otherwise make the real page look ambiguous.
    by_words = {p for p in found if pages.phrase_on(rt, p)}
    if window is not None:
        anchors = {p for p in anchors if p in window}
        by_words = {p for p in by_words if p in window}
    pool = anchors | by_words
    if not pool:
        return None, "unresolved" if (anchor_pages or found) else "not_found"
    pick = None
    if len(anchors) == 1 and (not by_words or anchors <= by_words):
        pick = next(iter(anchors))                 # both methods agree, or the anchor alone
    elif len(pool) == 1:
        pick = next(iter(pool))
    if pick is None or not pages.phrase_on(rt, pick):
        return None, "unresolved"
    return pick, ("moved" if pick != stored else "on_page")


def batch_size(stored_pages, sizes=(30, 12, 6), share: float = 0.9) -> int | None:
    """The reader's chunk size, when a document's stored pages are nearly all chunk
    starts (1, 13, 25, ...). None when they are not: then no window is assumed."""
    ps = [p for p in stored_pages if p]
    for k in sizes:
        if ps and sum((p - 1) % k == 0 for p in ps) / len(ps) >= share:
            return k
    return None


# -- printed page numbers ------------------------------------------------------------

#: A page-number token in a header/footer line: "12", "B5" ("Page B5 of B54"),
#: "14-117" ("p 14-117"), "4.1-2", "1-5", "pg.3". The trailing number is what counts up.
_TOKEN = re.compile(
    r"(?<![\w.])(?:(?:page|pg|p)\.?\s*)?([A-Za-z]{0,2}\d{1,4}(?:\s*[.\-–]\s*\d{1,4}){0,3})"
    r"(?:\s*of\s*[A-Za-z]{0,2}\d{1,4})?(?![\w])", re.I)
_TAIL = re.compile(r"(\d+)$")
_DIGITS = re.compile(r"\d+")
SHORT_LINE = 25
MIN_COVERAGE = 0.5


def _norm(token: str) -> str:
    return re.sub(r"\s*([.\-–])\s*", lambda m: m.group(1), token).replace("–", "-")


def _split(token: str) -> tuple[str, int] | None:
    m = _TAIL.search(token)
    return (token[:m.start()].lower().replace("–", "-"), int(m.group(1))) if m else None


def printed_labels(margins: dict[int, list[str]]) -> dict[int, str]:
    """page -> the page number printed in its header/footer, as printed.

    `margins` maps page -> the text lines in its top and bottom margins. A token is
    taken only when a neighbouring page (1 or 2 away) prints a token with the same
    prefix counting by exactly the page distance, and does not print this token itself:
    a year, a date, a chapter code or a lot number is the same on every page and never
    counts. Two such tokens = no label. Spacing is dropped ("D2 - 10" -> "D2-10").
    """
    # Page furniture only: a short line, or one whose wording (numbers aside) repeats on 3+ pages.
    # A numbered requirement at the foot of a page counts up too, and is body text.
    shape = Counter(_DIGITS.sub("#", ln.strip().lower()) for ls in margins.values() for ln in set(ls))
    furniture = {p: [ln for ln in ls if len(ln.strip()) <= SHORT_LINE
                     or shape[_DIGITS.sub("#", ln.strip().lower())] >= 3]
                 for p, ls in margins.items()}
    split = {p: {t: s for ln in ls for t in map(_norm, _TOKEN.findall(ln)) if (s := _split(t))}
             for p, ls in furniture.items()}
    out = {}
    for p, ts in split.items():
        # A page number changes from page to page; a year or a code printed on every page does
        # not -- and two such constants (Hornsby's "2024" and "2025") must not pair up as a count.
        ok = {t for t, (pre, n) in ts.items()
              if any(pre == pre2 and n2 - n == d and t not in split.get(p + d, {})
                     for d in (-2, -1, 1, 2) for pre2, n2 in split.get(p + d, {}).values())}
        if len(ok) == 1:
            out[p] = ok.pop()
    # A page-number footer is on most pages. A few counting tokens in a document that has none
    # are headings or list numbers that happen to count (Northern Beaches' web-page render).
    return out if len(out) >= MIN_COVERAGE * len(margins) else {}
