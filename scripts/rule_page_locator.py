"""Which page of a PDF a DCP rule is on, and what page number that page prints. Pure.

prior-art-checked: citation_proof._anchors locates a rule's wording but uses the stored
page only to ORDER its tries and never reports whether that page holds the rule;
dcp_extract_changed.assign_pages_from_markers settles pages only on the page-range path.
The AI reader path (ai_extractor.ai_extract_chapter) stored the first page of its
12-page chunk for every rule it returned (measured 2026-09-26 over all 237 served
chapter PDFs: 45% of 17,489 served rules linked to a page that does not hold them).

One definition, used by the reader when it writes a page and by
scripts/dcp_page_repair.py when it checks and corrects the stored ones:

  * the rule is found in the document's own word stream: every 6-word piece of it is looked
    up, and pieces printed close together form one occurrence. An occurrence counts only when
    at least half the rule's pieces are there (each piece is 6 words in order, so the same
    words scrambled never match). Its page is where its earliest found words are printed.
  * one occurrence clearly best = that page. Two equally good = the rule really is printed
    twice (a control restated per site): the copy printed under the rule's own heading words
    ("C4 Goodwin Avenue") wins, else the reader's chunk decides if only one lies in it,
    otherwise no answer -- never a guess.
  * both of a PDF's reading orders are searched (a two-column page read top-to-bottom
    interleaves its columns).

Measured on the first version, which tested page by page: a rule on page 21 also
"matched" pages 20 and 22 (a test that allowed a rule to run onto the next page), and
testing only the opening words matched generic openings everywhere -- 1,262 rules were
wrongly called repeated. Locating the START in the word stream removes both.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

_WORD = re.compile(r"[a-z0-9]+")
PIECE = 6            # words per piece looked up
STEP = 3             # a piece starts every STEP words of the rule
HOLD = 0.5           # share of the rule's pieces an occurrence needs
WEAK_HOLD = 0.3      # ...or this much, when it is the only place anything like the rule is printed
TIE = 0.8            # a second occurrence within this share of the best is a real repeat
MIN_TOKENS = 5       # a shorter rule ("See above.") cannot be located honestly
HEAD_WINDOW = 200    # words above an occurrence searched for the rule's own heading words

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


def heading_words(text: str | None) -> set[str]:
    """Words of the rule's '# code title' line that name it: 'Goodwin', 'Avenue' -- not codes."""
    t = (text or "").lstrip()
    if not t.startswith("#") or "\n" not in t:
        return set()
    head = t.partition("\n")[0]
    return {w for w in tokens(head) if len(w) > 3 and not any(ch.isdigit() for ch in w)}


class Doc:
    """One reading of a document as a word stream, each word knowing its page."""

    def __init__(self, pages: dict[int, str]):
        self.tok: list[str] = []
        self.page: list[int] = []
        for p in sorted(pages):
            for w in tokens(pages[p]):
                self.tok.append(w)
                self.page.append(p)
        self.index = defaultdict(list)
        for k in range(len(self.tok) - PIECE + 1):
            self.index[tuple(self.tok[k:k + PIECE])].append(k)
        self.at = defaultdict(list)                 # word -> positions, for short rules
        for k, w in enumerate(self.tok):
            self.at[w].append(k)

    def above(self, k: int) -> set[str]:
        return set(self.tok[max(0, k - HEAD_WINDOW):k])


def occurrences(rule_tokens: list[str], doc: Doc) -> list[tuple[float, int, set, int]]:
    """Each place the rule is printed: (share of its pieces found there, the page its earliest
    found words are on, every page its found pieces are on, position of those earliest words).

    Pieces are 6 words in order, so the same words scrambled never match. A rule shorter than
    a piece is looked up whole. A place is scored over a stretch of the document as long as
    the rule itself, from where its pieces begin: every distinct piece in that stretch counts,
    in whatever order the page prints them. Two earlier designs failed on real rows --
    grouping by the START each piece implies split a rule whose stored text orders its parts
    differently from the page (Ku-ring-gai 4.1C.6: 0.44 + 0.22 + 0.17, all on page 21), and
    splitting on a repeated piece chopped whole sections stored as one rule (743 to 4,351
    words) into fragments none of which reached the bar. Stretches that overlap are one place.
    """
    n = len(rule_tokens)
    if n < MIN_TOKENS or not doc.tok:
        return []
    if n < PIECE:
        return [(1.0, doc.page[k], {doc.page[k]}, k) for k in doc.at.get(rule_tokens[0], ())
                if doc.tok[k:k + n] == rule_tokens]
    pieces = [(o, tuple(rule_tokens[o:o + PIECE])) for o in range(0, n - PIECE + 1, STEP)]
    hits = sorted((k, o) for o, g in pieces for k in doc.index.get(g, ()))
    if not hits:
        return []
    span = int(n * 1.3) + 40                       # the rule's length, plus words the page adds
    # Candidate starts: a hit with no hit in the `gap` words before it opens a stretch.
    gap = 40 + n // 4
    starts, last = [], None
    for k, _o in hits:
        if last is None or k - last > gap:
            starts.append(k)
        last = k
    places = []
    for k0 in starts:
        inside = [(k, o) for k, o in hits if k0 <= k <= k0 + span]
        o_min, k_min = min((o, k) for k, o in inside)
        places.append((len({o for _k, o in inside}) / len(pieces), doc.page[k_min],
                       {doc.page[k] for k, _o in inside}, k_min, k0))
    places.sort(key=lambda x: -x[0])
    kept: list[tuple] = []
    for pl in places:                              # overlapping stretches are one place
        if all(abs(pl[4] - q[4]) > span for q in kept):
            kept.append(pl)
    return [pl[:4] for pl in kept]


def _by_heading(text: str | None, top: list, docs: list[Doc]) -> list:
    """Of several real copies, the ones printed under the rule's own heading words. Only words
    that tell the copies apart count; every copy equally named = no choice."""
    # A heading word the rule's own text also uses ("front" in "set back from the front
    # boundary") is printed in the copy above this one too, and tells nothing apart.
    head = heading_words(text) - set(tokens(rule_body(text)))
    if not head:
        return top
    seen = [head & docs[i].above(k) for (_c, _p, _ps, k, i) in top]
    shared = set.intersection(*seen) if seen else set()
    score = [len(s - shared) for s in seen]
    best = max(score)
    return [occ for occ, s in zip(top, score) if s == best] if best else top


def locate(text: str | None, docs: list[Doc], stored: int | None = None,
           window: range | None = None) -> tuple[int | None, str]:
    """-> (page, verdict). verdict: on_page | moved | unresolved | not_found | too_short.

    docs: the document's readings. stored: the page currently recorded. window: pages the
    rule must lie in when known (the reader's chunk). `page` is None when the stored one
    must be left alone.
    """
    rt = tokens(rule_body(text))
    if len(rt) < MIN_TOKENS:
        return None, "too_short"
    found = [occ + (i,) for i, d in enumerate(docs) for occ in occurrences(rt, d)]
    if not found:
        return None, "not_found"
    best = max(occ[0] for occ in found)
    rivals = [occ for occ in found if occ[0] >= TIE * best]
    if best < HOLD:
        # Only part of the stored text is the council's (map labels, figure text mixed in):
        # accepted only where one place clearly holds the most of it.
        if best < WEAK_HOLD or len({occ[1] for occ in rivals}) > 1 or any(
                occ[0] >= 0.5 * best and occ[1] != rivals[0][1] for occ in found):
            return None, "unresolved"
    top = rivals
    # A stored page that holds the rule is never moved off: a best match (a rule running over
    # a page break is on both pages), or any strong one -- Woollahra B1.11.1 "Vaucluse East" was
    # on its stored page 41 and scored a little lower than the near-identical "Vaucluse West"
    # text on page 38. A table prints a rule's cells out of order, so a third in order is enough
    # to keep the stored page (27 moves left a page printing every word of the rule).
    keep = [occ for occ in found if occ[0] >= min(WEAK_HOLD, TIE * best)]
    if stored is not None and any(stored in occ[2] for occ in keep):
        return stored, "on_page"
    if len({occ[1] for occ in top}) > 1:
        top = _by_heading(text, top, docs)
    starts = sorted({occ[1] for occ in top})
    if len(starts) > 1 and window is not None:
        starts = [p for p in starts if p in window]
    if len(starts) != 1:
        return None, "unresolved"
    return starts[0], "moved"


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
RUN_MIN = 3           # readable pages that must agree on a numbering offset


def _norm(token: str) -> str:
    return re.sub(r"\s*([.\-–])\s*", lambda m: m.group(1), token).replace("–", "-")


def _split(token: str) -> tuple[str, int] | None:
    m = _TAIL.search(token)
    return (token[:m.start()].lower().replace("–", "-"), int(m.group(1))) if m else None


def _read_labels(margins: dict[int, list[str]]) -> dict[int, str]:
    """page -> the page number its own header/footer prints, where it can be read.

    A token is taken only when a neighbouring page (1 or 2 away) prints a token with the same
    prefix counting by exactly the page distance, and does not print this token itself: a
    year, a date, a chapter code or a lot number is the same on every page and never counts.
    Two such tokens = no label. Spacing is dropped ("D2 - 10" -> "D2-10").
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
    return out


def page_numbering(margins: dict[int, list[str]]) -> list[dict]:
    """A document's page numbering as runs: printed number = prefix + (PDF page + offset).

    Found once per document from the pages whose footer can be read, then applied to every
    page of the run -- including pages whose footer could not be read (Leichhardt Part C s1:
    38 of 109 read). A run needs RUN_MIN readable pages agreeing on prefix and offset; a new
    run starts where the numbering restarts (City of Sydney "4.1-1", "4.2-1"). Headings or
    list numbers that happen to count never agree for three pages at one offset.
    """
    read = _read_labels(margins)
    runs: list[dict] = []
    for p in sorted(read):
        tok = read[p]
        m = _TAIL.search(tok)
        prefix, offset = tok[:m.start()], int(m.group(1)) - p
        r = runs[-1] if runs else None
        if r and r["prefix"].lower() == prefix.lower() and r["offset"] == offset:
            r["last"], r["seen"] = p, r["seen"] + 1
        else:
            runs.append({"prefix": prefix, "offset": offset, "first": p, "last": p, "seen": 1})
    # Filled only BETWEEN readable pages of a run, never carried past the last one: measured
    # 2026-09-26 by hiding each readable footer and predicting it (3,589 pages, 237 PDFs),
    # carrying 3 pages on gave 16 wrong numbers -- all the first page of a new section taking
    # the previous section's count -- and filling between gave 1.
    return [r for r in runs if r["seen"] >= RUN_MIN]


def printed_labels(margins: dict[int, list[str]]) -> dict[int, str]:
    """page -> the page number printed on it, from the document's numbering runs."""
    out = {}
    for r in page_numbering(margins):
        for p in range(r["first"], r["last"] + 1):
            n = p + r["offset"]
            if n > 0:
                out[p] = f"{r['prefix']}{n}"
    # A page-number footer is on most pages. A few counting tokens in a document that has none
    # are headings or list numbers that happen to count (Northern Beaches' web-page render).
    return out if len(out) >= MIN_COVERAGE * len(margins) else {}
