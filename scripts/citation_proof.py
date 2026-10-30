"""Prove a provision's CITATION against its source page, the way its text already is.

prior-art-checked: `dcp_fidelity_gate.ground_row` proves a row's words and numbers
and deliberately strips its own code numbers (`code_nums`) before doing so, so
nothing proved the citation (DQ-111). `measure_heading_detection.py` reads
headings from typography but scores a whole document, not one row's claim, and
found typography and regex each recover only ~half the headings (2026-09-24,
9/36 documents scorable). So this does not build a heading tree. It takes the
code the reader PROPOSED and checks it against the lines of the page.

THE RULE
--------
A citation is proven only when every piece of it is printed where a reader
would find it:

* the section code is printed at the START of a line -- a heading, not a
  mid-sentence cross-reference -- on or before the rule's own page;
* it is the NEAREST heading of its shape above the rule: no other ``8.2.39.x``
  between ``8.2.31.6`` and the text it claims;
* any parent pieces (Waverley's ``B14 > 14.3 > 14.3.7``) are printed as headings;
* the item label (``O1``, ``C12``) is printed between that heading and the rule.

"Printed anywhere in the document" is NOT proof. The DQ-111 probe used that
bar and missed Leichhardt rows citing ``G10.5.2`` under a printed ``G6.12``,
because ``G10.5.2`` exists elsewhere in the same PDF.

Every weakness the prototype hit on 9 chapters is handled below and pinned in
tests/test_citation_proof.py. Deterministic string work only -- no model.
"""
from __future__ import annotations

import bisect
import collections
import re
from dataclasses import dataclass, field

#: Prefix of every citation finding the fidelity gate writes to fidelity_detail.
#: dcp_approve_graded refuses rows carrying it. One definition, here, because
#: this module imports nothing and both of those can import it.
CITATION_FINDING = "citation not proven on its page"

# -- the ref's code ------------------------------------------------------------

_HEAD = re.compile(r"^([A-Za-z]{1,3})?(\d+[A-Za-z]?)$")
_CONT = re.compile(r"^\d+[A-Za-z]?$")


def code_groups(ref_number: str | None) -> list[tuple[str, list[str]]]:
    """Split a ref tail into (letter_prefix, [numeric parts]) groups, in order."""
    tail = (ref_number or "").split("__")[-1]
    tail = re.sub(r"\([^)]*\)", " ", tail)          # "(a)" sub-clauses: not a code
    # The repeated-ref marker (#1197): `..._7_4 (a)~2`. It has to be stripped, not
    # left to be "ignored". It IS ignored when an item marker sits between it and the
    # digits -- `7_4 (a)~2` becomes `7_4 ~2`, and `~2` is a token of its own that
    # `_HEAD` rejects. Attached straight to the clause number it EATS the last
    # component, because `3_15_5_2~2` splits into `3 15 5 2~2` and `2~2` fails
    # `_CONT`: `3.15.5.2` was judged as `3.15.5`, `3_1_1~4` as `3.1`, and `3_15~6`
    # as a bare `3` ("not discriminating"). All five such rows in the 2026-10-02
    # City of Sydney re-read were held as "citation not proven" while their own
    # number WAS printed on their page -- page 106 carries "3.15.5.2 Monitoring and
    # Review" verbatim. Mirrors the frontend strip in lib/citation-display.ts, so
    # both sides read one clause number.
    #
    # Anchored to the END, and repeatable. Both halves came out of the Sol
    # cross-review of the first version, which stripped `~\d+` anywhere:
    #   * unanchored, `3_15~2.4` became `3_15.4` -- a plausible clause the council
    #     never printed, invented out of a ref shape that should stay unjudged.
    #     That is the DQ-111 class, which is the whole reason for the anchor.
    #   * anchored but not repeatable (`~\d+$`, as the frontend has it) leaves
    #     `X_5~2` out of `X_5~2~3`, and dcp_extract_changed's `while` loop can mark
    #     a ref that already carries one -- so the eaten component comes straight
    #     back. Neither shape is in the queue today, because the producer only
    #     appends; one strip covering both is cheaper than finding out later.
    tail = re.sub(r"(?:~\d+)+$", "", tail)
    groups: list[tuple[str, list[str]]] = []
    for token in tail.split():
        current = None
        for part in re.split(r"[_\-.]+", token):
            if not part:
                continue
            if current is not None and _CONT.match(part):
                current[1].append(part)
                continue
            m = _HEAD.match(part)
            if m:
                current = ((m.group(1) or "").upper(), [m.group(2)])
                groups.append(current)
            else:
                current = None                        # a word breaks the group
    return groups


def split_ref(ref_number: str | None):
    """-> (sections, item, unjudged_reason). unjudged_reason is None when judged."""
    groups = code_groups(ref_number)
    item = None
    if len(groups) > 1 and groups[-1][0]:
        item = groups[-1]
        groups = groups[:-1]
    sections = [g for g in groups if g[0] or len(g[1]) >= 2]
    if sections:
        return sections, item, None
    if groups:
        return [], item, "bare integer section (not discriminating)"
    if item:
        return [], item, "item marker only, no section"
    return [], None, "no clause number in the ref"


def render(group) -> str:
    prefix, nums = group
    return prefix + ".".join(nums)


# -- the page's lines ------------------------------------------------------------

@dataclass(frozen=True)
class Line:
    page: int
    y: float
    x: float
    text: str            # lowercased, stripped


#: A code at the start of a line, optionally after "part"/"section"/"chapter".
#: The lookahead refuses a longer number, so "8.2.3" does not start "8.2.31".
#: A bare year ("1997 ...") and a standard's number ("1924.2-81 (playground ...)")
#: are not headings: counted as one, a year proved "1924.2 C10" (leichhardt C1).
CODE_AT_START = re.compile(
    r"^(?:(?:part|section|chapter)\s+)?(?!(?:1[89]|20)\d\d(?!\d))"
    r"((?:[a-z]{1,3})?\d+[a-z]?(?:\.\d+[a-z]?)*)(?![\d.]*\d)(?![-–/]\d)")
#: A contents-page line: title, leaders or space, page number.
_TOC_LINE = re.compile(r"(\.{3,}|\s)\d{1,4}\s*$")
#: A page number in the top/bottom margin. Harmless as text, but "1" at the
#: foot of a page starts with a code and was taken as the heading "1".
_PAGE_NUMBER = re.compile(r"^(?:page\s+)?\d{1,4}$|^\d+(?:\.\d+)*\s*[-–]\s*\d+$")
_KEYWORD_HEAD = re.compile(r"^(?:section|part|chapter)\s+(\d{1,3})(?![\d.])")
_WORD = re.compile(r"[a-z0-9]+")


@dataclass
class ChapterLines:
    """One document's lines, indexed for locating a row's wording. Build once per chapter."""
    lines: list[Line]
    toc_pages: set[int]
    tokens: list[str] = field(default_factory=list)
    token_line: list[int] = field(default_factory=list)
    index: dict = field(default_factory=dict)
    page_width: float | None = None
    #: code -> ascending line indices where that code STARTS a line. Built once;
    #: without it Warringah (1,600 rules) rescans every line per rule per reading.
    heads_at: dict = field(default_factory=dict)
    #: bare numbers printed after a heading word: "section 11 - corner hotels".
    #: A lone "11" is on every page; "Section 11" at a line start is a heading
    #: (Leichhardt Appendix B numbers its typologies this way and nothing else).
    keyword_heads: dict = field(default_factory=dict)
    full_text: str = ""
    #: Codes named by running headers ("e6 | sustainability"). Never a heading
    #: for a rule, but evidence that a PARENT piece is the council's own:
    #: Woollahra prints its chapter code only there and numbers sections
    #: inside without it, so E6 > 1.1 has no other printed "e6".
    header_codes: set = field(default_factory=set)
    #: code -> pages whose running header names it. "Names only the chapter" must be
    #: the header over the RULE's page: Woollahra's "c1.3 building types" header
    #: (pages 19-62) passed C1.3 for rules on pages 15-16, inside C1.2.3 (2026-10-30).
    header_pages: dict = field(default_factory=dict)
    #: code -> [(first page, last page)] from the PDF's own bookmarks (outline_ranges).
    #: Empty when the PDF has none, or they are broken.
    outline: dict = field(default_factory=dict)

    @classmethod
    def build(cls, raw: list[Line], page_width: float | None = None,
              keep_order: bool = False, outline: list | None = None) -> "ChapterLines":
        """keep_order: trust the PDF's own reading order (PyMuPDF block order)
        instead of sorting each page top-to-bottom. Sorting interleaves a
        two-column page line by line (Hornsby, Campbelltown), so a rule's
        wording is never found intact."""
        by_page = collections.defaultdict(list)
        for ln in raw:
            by_page[ln.page].append(ln)
        toc = set()
        for page, pl in by_page.items():
            hits = sum(1 for x in pl if _TOC_LINE.search(x.text) and len(x.text) > 12)
            if pl and hits / len(pl) > 0.4:
                toc.add(page)
        # Running headers/footers: a line repeated on 3+ pages, ONLY in the top
        # and bottom margins. Everywhere, it deleted real control wording a
        # council repeats per site -- Leichhardt prints "Buildings are to be
        # designed in accordance with the desired future character statement"
        # under many sites. A header that names a section ("chapter 7.6 belmore
        # and lakemba") is still a header: the heading itself is printed once,
        # in the body. Margins are per page because Canterbury-Bankstown mixes
        # landscape and portrait pages, and a document-wide bottom left its
        # landscape header mid-page, where it read as heading "7.6".
        bottom = {p: max(x.y for x in pl) for p, pl in by_page.items()}

        def in_margin(ln):
            b = bottom[ln.page]
            return ln.y < 0.08 * b or ln.y > 0.92 * b

        rep = collections.Counter(x.text for x in raw if in_margin(x))
        furniture = {t for t, n in rep.items() if n >= 3}
        kept = []
        for page in sorted(by_page):
            ordered = by_page[page] if keep_order else sorted(by_page[page], key=lambda x: (x.y, x.x))
            for ln in ordered:
                if in_margin(ln) and (ln.text in furniture or _PAGE_NUMBER.match(ln.text)):
                    continue
                kept.append(ln)
        out = cls(kept, toc, page_width=page_width)
        out.header_codes = {m.group(1) for t in furniture if (m := CODE_AT_START.match(t))}
        hp = collections.defaultdict(set)
        for x in raw:
            if in_margin(x) and x.text in furniture and (m := CODE_AT_START.match(x.text)):
                hp[m.group(1)].add(x.page)
        out.header_pages = dict(hp)
        heads = collections.defaultdict(list)
        for i, ln in enumerate(kept):
            m = CODE_AT_START.match(ln.text)
            if m:
                heads[m.group(1)].append(i)
        out.heads_at = dict(heads)
        kw = collections.defaultdict(list)
        for i, ln in enumerate(kept):
            m = _KEYWORD_HEAD.match(ln.text)
            if m:
                kw[m.group(1)].append(i)
        out.keyword_heads = dict(kw)
        out.full_text = "\n".join(ln.text for ln in kept)
        for i, ln in enumerate(kept):
            for w in _WORD.findall(ln.text):
                out.tokens.append(w)
                out.token_line.append(i)
        idx = collections.defaultdict(list)
        for k in range(len(out.tokens) - 5):
            idx[tuple(out.tokens[k:k + 6])].append(k)
        out.index = idx
        out.outline = outline_ranges(outline, kept)
        return out


def outline_entries(toc: list | None) -> list[tuple[int, str, str]]:
    """(page, lowercase code, title words) for each numbered bookmark; [] when the
    numbered bookmarks all point to one page (City of Sydney's broken outline)."""
    out = []
    for _lvl, title, page in toc or []:
        m = re.match(r"\s*([A-Za-z]{0,3}\d+(?:\.\d+)+)\.?\s+(.+)", title or "")
        if m and page and page > 0:
            out.append((page, m.group(1).lower(), " ".join(_WORD.findall(m.group(2).lower()))))
    if len(out) > 3 and len({p for p, _c, _t in out}) == 1:
        return []
    return out


def outline_ranges(toc: list | None, lines: list | None = None) -> dict:
    """code -> [(first page, last page)]. A section runs to the page where the next
    bookmark that is not its own sub-section starts (that page included: the next
    heading can sit low on it). With `lines`, a section is kept only when its
    bookmark is CONFIRMED -- its title's words are printed on the page it points
    to -- so a stale single bookmark cannot hide a proven number (cross-review,
    2026-10-30). Ends still come from every entry."""
    ent = outline_entries(toc)
    on_page = None
    if lines is not None:
        on_page = collections.defaultdict(str)
        for ln in lines:
            on_page[ln.page] += " " + " ".join(_WORD.findall(ln.text))
    rng = collections.defaultdict(list)
    for k, (page, code, title) in enumerate(ent):
        if on_page is not None and (len(title) < 4 or title not in on_page.get(page, "")):
            continue
        end = next((p for p, c, _ in ent[k + 1:] if c != code and not c.startswith(code + ".")), None)
        rng[code].append((page, end))
    return dict(rng)


def outline_allows(ch: ChapterLines, code: str, page: int) -> bool | None:
    """Do the PDF's own bookmarks put `page` inside section `code`? None = they do not say."""
    spans = ch.outline.get(code)
    if not spans:
        return None
    return any(s <= page and (e is None or page <= e) for s, e in spans)


def both_orders(raw: list[Line], page_width: float | None,
                outline: list | None = None) -> tuple[ChapterLines, ChapterLines]:
    """The same lines read two ways: the PDF's own reading order, and top-to-bottom.

    Neither is right everywhere. Top-to-bottom interleaves a two-column page
    (Hornsby); reading order can put a left-hand heading column AFTER the text
    column it heads (Canterbury-Bankstown). A citation printed above its rule
    in either reading is the council's; a wrong one has to fail in both.
    """
    return (ChapterLines.build(raw, page_width=page_width, keep_order=True, outline=outline),
            ChapterLines.build(raw, page_width=page_width, keep_order=False, outline=outline))


def read_outline(pdf_path: str) -> list:
    """The PDF's bookmarks as [level, title, page] (PyMuPDF get_toc)."""
    import fitz
    with fitz.open(pdf_path) as doc:
        return doc.get_toc()


# prior-art-checked: reuse not viable because dcp_extract_changed._extract_page_text
# returns flattened pdfplumber page strings with no per-line position, and
# measure_heading_detection's fitz reader keeps font size/bold but not x/y --
# the proof needs line starts and positions (side columns, margins, order).
def read_raw_lines(pdf_path: str) -> tuple[list[Line], float | None]:
    """A PDF's lines in its own reading order, with PyMuPDF (already a
    dependency) -- geometry the flattened page strings the gate grades words
    against do not keep."""
    import fitz
    import pdf_picture_labels as ppl
    raw, pictures, masks, read, ocr_cache = [], [], {}, [], {}
    width = None
    reader = ppl.ocr_reader()
    with fitz.open(pdf_path) as doc:
        for pno, page in enumerate(doc, 1):
            width = width or page.rect.width
            for block in page.get_text("dict")["blocks"]:
                for ln in block.get("lines") or []:
                    t = " ".join(s["text"] for s in ln["spans"]).strip().lower()
                    if t:
                        raw.append(Line(pno, ln["bbox"][1], ln["bbox"][0], t))
            pictures += [(pno, y, x, m, h) for y, x, m, h in ppl.page_label_pictures(doc, page, masks)]
            read += [(pno, y, x, t) for y, x, t in ppl.ocr_label_pictures(doc, page, ocr_cache, reader)]
        outline = doc.get_toc()
    pictures = [p[:4] for p in ppl.label_sized(pictures)]
    return restore_outline_numbers(ppl.merge_labels(raw, pictures, Line, read), outline), width


def restore_outline_numbers(lines: list[Line], outline: list) -> list[Line]:
    """Put a heading's number back where the page prints only its title.

    Parramatta prints "5.4.4" in a coloured box (no text, no OCR hit) beside the
    text "solar light reflectivity (glare)". Without the number, the heading that
    ENDS 5.4.3.5 is invisible and 5.4.3.5 kept proving rules from 5.4.4 and 5.4.7
    (2026-10-30). The PDF's own bookmark names the number and the page; it is used
    only when that page prints the bookmark's title as a line of its own, and never
    for an outline whose numbered entries all point to one page (City of Sydney's
    broken bookmarks)."""
    entries = outline_entries(outline)
    by_page = collections.defaultdict(list)
    for k, ln in enumerate(lines):
        by_page[ln.page].append(k)
    out = list(lines)
    for page, num, title in entries:
        if len(title) < 4 or any(out[k].text.startswith(num) for k in by_page.get(page, ())):
            continue
        hits = [k for k in by_page.get(page, ())
                if " ".join(_WORD.findall(out[k].text)) == title]
        if len(hits) == 1:
            k = hits[0]
            out[k] = Line(out[k].page, out[k].y, out[k].x, f"{num} {out[k].text}")
    return out


def load_lines(pdf_path: str) -> ChapterLines:
    """One reading (the PDF's own order). Proof should use load_readings."""
    raw, width = read_raw_lines(pdf_path)
    return ChapterLines.build(raw, page_width=width, keep_order=True)


def load_readings(pdf_path: str) -> tuple[ChapterLines, ChapterLines]:
    """Both readings of a PDF, for prove_citation_any."""
    raw, width = read_raw_lines(pdf_path)
    return both_orders(raw, width, read_outline(pdf_path))


# -- proof -------------------------------------------------------------------------

_RANK = {"absent": 0, "cross_ref_only": 1, "label_as_section": 1, "not_nearest": 2, "ancestor_missing": 3,
         "item_missing": 4, "item_format": 5, "imprecise": 6}


_NUM_LABEL = re.compile(r"^\(?(\d{1,3})[.)](?:\s|$)")


def _numeric_label_beside(L: list, start: int, lo: int) -> str | None:
    """The nearest number label ("14.", "(14)") at or up to three lines above the
    rule's first line, not above `lo` (its heading); None if there is none."""
    for i in range(start, max(lo, start - 3) - 1, -1):
        m = _NUM_LABEL.match(L[i].text)
        if m:
            return m.group(1)
    return None


#: A rule's sentence, not a heading's title: "Fences must be ...", "Buildings are to ...".
#: Until 2026-09-26 the file held literal backspace characters where the \b word
#: boundaries belong (an editing tool wrote \b unescaped), so this never matched and a
#: short rule sentence counted as a heading title.
_OBLIGATION = re.compile(r"\b(?:is|are) to\b|\b(?:must|shall|should|will|may)\b")


def _titled(L: list, h: int, code: str) -> bool:
    """Is the code on line h followed by a short title (a heading), rather than a
    rule's sentence (a label)? The title is the rest of line h, else line h+1."""
    rest = L[h].text[len(code):].strip(" .:-–	")
    if not rest and h + 1 < len(L):
        rest = L[h + 1].text.strip()
    words = rest.split()
    return (0 < len(words) <= 8 and not rest.endswith(".")
            and not _OBLIGATION.search(rest))


def _own_label(L: list, lo: int, start: int, end: int, hi: int, item: str) -> str | None:
    """The label printed for the rule matched on lines `start`..`end`: of the
    labels of the item's shape (same letters, same depth), the one whose block
    holds MOST of those lines, a tie going to the later block. None if no such
    label is printed at or above the rule.

    No "first label just after the rule" fallback: it proved an introduction as
    O1 and a note as C1 (cross-review; 5 rows corpus-wide depended on it, and
    of the 3 read, 2 were wrong -- 2026-09-25). A label set beside its rule
    already sorts onto the rule's row.

    Blocks, not "last label above the first line": stored text that opens with
    its sub-heading matches one line ABOVE its own label (C1.3 C8 read as C7).
    Not "nearest label": Marrickville stores a rule's first line in its heading,
    so the match starts on line two and the NEXT label is nearer (C15 as C16).
    """
    fam, depth = _shape(item)

    def label(i):
        m = CODE_AT_START.match(L[i].text)
        return m.group(1) if m and _shape(m.group(1)) == (fam, depth) else None

    owner, lines = None, collections.Counter()
    order = {}
    for i in range(lo, end + 1):
        if (c := label(i)):
            owner = c
            order.setdefault(c, i)
        if i >= start and owner:
            lines[owner] += 1
            order[owner] = max(order[owner], i)
    if lines:
        return max(lines, key=lambda c: (lines[c], order[c]))
    # A label beside the rule's first line, a point lower on the page, sorts
    # just after it top-to-bottom. Only that geometry counts: same page, same
    # row, left of the rule.
    first = L[start]
    return next((c for i in range(start + 1, hi)
                 if L[i].page == first.page and abs(L[i].y - first.y) <= 3.0
                 and L[i].x < first.x and (c := label(i))), None)


def _shape(code: str) -> tuple[str, int]:
    m = re.match(r"([a-z]*)(.*)", code)
    return m.group(1), m.group(2).count(".")


#: "0.5 metre freeboard", "2.4m", "1.5 car space": a measurement, not a heading.
_MEASURE = re.compile(r"^[a-z]*\d+(?:\.\d+)*\s*(?:m\b|mm\b|m2\b|m\u00b2|metres?\b|%|car\b|spaces?\b|per\b|x\b)")


def _heading_like(line: Line, page_width: float | None) -> bool:
    """Can this line close a section? Not a long sentence, not a measurement, and
    not a navigation tab in the outer margin (Marrickville prints "8.5 HCA style
    sheets" at x=551 on every page of 8.4)."""
    # A ")" with no "(" is the tail of a sentence's cross-reference: "...(see
    # C1.11.7 Recognised shopping streets)" proved C1.11.7 for leichhardt C1 rules.
    return (len(line.text) < 90 and not _MEASURE.match(line.text)
            and line.text.count(")") <= line.text.count("(")
            and (page_width is None or line.x < 0.75 * page_width))


def _ends_scope(other: str, leaf: str, item_family: str = "") -> bool:
    """Does a heading ``other``, printed between ``leaf`` and the rule, close leaf's scope?

    Same family (letter prefix) and either the same depth (8.2.39.6 after
    8.2.31.6), or shallower on the same first number without being leaf's own
    parent (8.2.39 after 8.2.31.6; G6.14 after G8.6.4 in the same prefix).
    A bare number or an undotted, unprefixed line is a list item, never a
    heading here: "2." inside a section must not end it, and neither must a
    table cell "1.5 car space per service room" under section 3.2.

    An undotted lettered code ("c11") in the row's OWN item family is an item
    label, not a heading. Leichhardt Part C numbers sections C2.2.4.1 and its
    controls C1..C11 in the same letter; reading "c11" as a closing heading
    rejected correct rows by the hundred.
    """
    if other == leaf or leaf.startswith(other + ".") or other.startswith(leaf + "."):
        return False
    fam_o, depth_o = _shape(other)
    fam_l, depth_l = _shape(leaf)
    if fam_o != fam_l or ("." not in other and not fam_o):
        return False
    if "." not in other and fam_o == item_family:
        return False
    if depth_o == depth_l:
        return True
    if depth_o < depth_l:
        if fam_o:
            return True
        return other.split(".")[0] == leaf.split(".")[0]
    return False


def _readings(group) -> list[tuple[list[str], str | None]]:
    """Ways a stored code can be printed: (heading pieces outermost-first, numbered item).

    * as written: ``8.2.4.7``
    * section + numbered control: ``6.3.29`` then ``(1)`` for ``6_3_29_1``
    * joined headings: ``B14`` > ``14.3`` > ``14.3.7`` for ``B14_14_3_14_3_7``

    A bare single number is never a heading piece on its own -- "9" is on every
    page, and allowing it let Leichhardt's ``C4.4`` pass as "C4 > 4".
    """
    prefix, nums = group
    out = [([render(group).lower()], None)]
    if len(nums) >= 3 or (prefix and len(nums) >= 2):
        out.append(([render((prefix, nums[:-1])).lower()], nums[-1]))
    if prefix and len(nums) >= 3:
        def splits(rest):
            if not rest:
                yield []
                return
            for k in range(len(rest), 1, -1):
                for tail in splits(rest[k:]):
                    yield [".".join(rest[:k])] + tail
        for sp in splits(nums[1:]):
            out.append(([(prefix + nums[0]).lower()] + sp, None))
    return out[:12]


def _prove_group(ch: ChapterLines, end: int, start: int, group, item: str | None,
                 bare: bool = False, item_end: int | None = None) -> str:
    """`item_end`: the last line of the WHOLE matched rule from `start`. The
    label is judged over that span, never over a six-word opening -- which, for
    text that opens with a sub-heading, sits in the previous rule's block."""
    L, toc = ch.lines, ch.toc_pages
    best = "absent"

    def keep(verdict):
        nonlocal best
        if _RANK[verdict.split(":")[0]] > _RANK[best.split(":")[0]]:
            best = verdict

    item_family = re.match(r"[a-z]*", item or "").group(0)
    for pieces, numbered in _readings(group):
        leaf = pieces[-1]
        at = (ch.keyword_heads if bare else ch.heads_at).get(leaf, [])
        heads = [i for i in at if i <= end and L[i].page not in toc]
        # A heading set in a side column can sort just after the rule's first line --
        # but only if it sits level with or above that line on the page. Without
        # the geometry, the NEXT section's heading printed below the rule proved
        # a row citing that next section (cross-review, 2026-09-24).
        heads += [i for i in at if end < i < end + 12 and L[i].page == L[start].page
                  and L[i].y <= L[start].y + 2.0]
        if not heads:
            # Not for the "section + numbered item" reading: "C1.3" read as chapter "c1"
            # (in every header) + item "3" that nothing checked passed 21 Woollahra rules
            # sitting in C1.2.3 (2026-10-30).
            if not numbered and L[start].page in ch.header_pages.get(leaf, ()):
                # "E2 C6": the chapter, named only in its running header. True,
                # but C6 recurs in every section, so nobody can find the rule.
                keep("imprecise:names only the chapter")
            elif leaf in ch.full_text:
                keep("cross_ref_only")
            continue
        above = [i for i in heads if i <= end]
        h = max(above) if above else min(heads)   # below only for a side-column heading
        # A heading printed INSIDE the rule's own span heads it only when the rule
        # opened under that heading's own parent (City of Sydney rows open with the
        # parent site's preamble, then "6.3.29.1"). If the rule opened under a
        # different section, its stored wording ran on into the NEXT section and that
        # section's heading proved it: Blacktown 4.3.3 from inside 4.3.2, Wollongong
        # 4.2.1/3.7.1, Parramatta 9.3.5.2.2 (2026-10-30).
        if start < h <= end:
            opened = [i for i in range(start, max(-1, start - 400), -1)
                      if L[i].page not in toc and _heading_like(L[i], ch.page_width)
                      and (m := CODE_AT_START.match(L[i].text)) and "." in m.group(1)
                      and _shape(m.group(1))[0] == _shape(leaf)[0]]
            parent = CODE_AT_START.match(L[opened[0]].text).group(1) if opened else None
            tl = ch.token_line            # ascending: tokens were added line by line
            before = bisect.bisect_left(tl, h) - bisect.bisect_left(tl, start)
            after = bisect.bisect_right(tl, end) - bisect.bisect_right(tl, h)
            if parent and not leaf.startswith(parent + ".") and parent != leaf or (not parent and before > after):
                keep("not_nearest:heading after most of the rule")
                continue
        lo = min(h, start)
        # "C12" with no section is the rule's own LABEL, not a heading: what follows
        # it is the rule's sentence. A lettered section is followed by a title, on
        # its line or the next ("b6" / "accessibility and adaptability", Waverley). The cheap reader drops the section
        # this way, and ~230 served rows were cited by a bare label (2026-09-25).
        if not item and not bare and re.fullmatch(r"[a-z]{1,3}\d+[a-z]?", leaf)                 and not _titled(L, h, leaf):
            keep("label_as_section")
            continue
        if bare:
            closing = [L[i].text for i in range(lo + 1, end + 1)
                       if (m := _KEYWORD_HEAD.match(L[i].text)) and m.group(1) != leaf]
            if closing:
                keep("not_nearest:" + closing[-1][:30])
                continue
        between = [L[i].text for i in range(lo + 1, end + 1)
                   if L[i].page not in toc and _heading_like(L[i], ch.page_width)
                   and (m := CODE_AT_START.match(L[i].text)) and _ends_scope(m.group(1), leaf, item_family)
                   # a summary line whose own bookmark starts on another page is not that heading
                   and outline_allows(ch, m.group(1), L[i].page) is not False]
        if between:
            keep("not_nearest:" + between[-1][:30])
            continue
        if not all(a in ch.header_codes or any(i <= end for i in ch.heads_at.get(a, []))
                   for a in pieces[:-1]):
            keep("ancestor_missing")
            continue
        # A MORE specific heading printed between the cited one and the rule:
        # true but coarse -- the collapsed-parent defect (2.25 for a rule under
        # 2.25.3.4). Counted apart from wrong citations, never as proven.
        finer = [L[i].text for i in range(lo + 1, end + 1)
                 if L[i].page not in toc and _heading_like(L[i], ch.page_width)
                 and (m := CODE_AT_START.match(L[i].text)) and m.group(1).startswith(leaf + ".")
                 and outline_allows(ch, m.group(1), L[i].page) is not False]
        hi = min(len(L), end + 3)
        # "4.3.3" read as section 4.3 + item 3: a sub-heading 4.3.x printed between
        # the 4.3 heading and the rule says which sub-section the rule is in, and it
        # must be 4.3.3. Blacktown 4.3.2 and Campbelltown 2.1.7 rules passed as .3/.8.
        if numbered and finer:
            sub = CODE_AT_START.match(finer[-1]).group(1)
            if sub != f"{leaf}.{numbered}" and not sub.startswith(f"{leaf}.{numbered}."):
                keep("not_nearest:" + finer[-1][:30])
                continue
        if numbered and not any(re.match(r"^\(?" + re.escape(numbered) + r"[.)]\s", L[i].text)
                                for i in range(lo, hi)):
            keep("item_missing")
            continue
        if item:
            # The rule's OWN label (see _own_label). "Anywhere between heading
            # and rule" proved C10 as C9, because C9 is printed above C10 -- 474
            # of 517 shifted labels passed (2026-09-25).
            own = _own_label(L, lo, start, end if item_end is None else item_end, hi, item)
            if own == item:
                if finer:
                    keep("imprecise:" + finer[-1][:30])
                    continue
                return "proven"
            digits = re.sub(r"^[a-z]+", "", item)
            # Warringah prints its controls "14." and we store "C14": the same
            # number, when it is the NEAREST number label printed where the rule's
            # words start (not merely somewhere in the section -- that let shifted
            # labels through). Letters ("c)" for 3) are not accepted this way.
            if digits.isdigit() and _numeric_label_beside(L, start, lo) == digits:
                if finer:
                    keep("imprecise:" + finer[-1][:30])
                    continue
                return "proven"
            # The council's own label for the same position: "7." (Warringah) or
            # "g)" (Campbelltown letters its controls; we store "C7" for both).
            printed = [re.escape(digits)]
            if digits.isdigit() and 1 <= int(digits) <= 26:
                printed.append(chr(ord("a") + int(digits) - 1))
            if digits and any(re.match(r"^\(?(?:" + "|".join(printed) + r")[.)]\s", L[i].text)
                              for i in range(lo, hi)):
                keep("item_format")    # printed under the council's own label, not ours
                continue
            keep("item_missing")
            continue
        if finer:
            keep("imprecise:" + finer[-1][:30])
            continue
        return "proven"
    return best


def _anchors(ch: ChapterLines, text: str, page_hint) -> list[tuple[int, int]]:
    """(end_line, start_line) pairs for every place this row's wording sits.

    Both ends, because stored text is wrong at either end in practice: it can
    open with the parent heading (City of Sydney) or the previous clause's tail
    (Marrickville), and run on into later clauses (Canterbury-Bankstown). Every
    occurrence, because councils restate objectives in a chapter summary
    (Woollahra), and per site (Leichhardt part G). The first line is our own
    ``# code title`` preamble line, not the council's text, so it is dropped.
    """
    full = text or ""
    body = full
    if body.lstrip().startswith("#"):          # "# G6.15 C1 <title>" is ours, not the council's
        rest = body.lstrip().split("\n", 1)
        body = rest[1] if len(rest) > 1 and rest[1].strip() else body
    words = _WORD.findall(body.lower())
    if len(words) < 6:                     # too short to locate -- use the title too
        words = _WORD.findall(full.lower())
    firsts, used = [], []
    for st in range(0, max(1, len(words) - 5)):
        if len(used) >= 3:
            break
        if used and st < used[-1] + 6:
            continue
        occ = [k - st for k in ch.index.get(tuple(words[st:st + 6]), [])
               if ch.lines[ch.token_line[k]].page not in ch.toc_pages and k - st >= 0]
        if occ:
            used.append(st)
            firsts += [k for k in occ if all(abs(k - f) > 3 for f in firsts)]
    # A place counts only if MOST of the rule's wording is there, not one phrase.
    # A single six-word match let a generic phrase repeated under another
    # heading anchor the rule there (cross-review, 2026-09-24). Samples found
    # nowhere in the document (extraction noise) are not held against anyone.
    samples = [(o, tuple(words[o:o + 6])) for o in range(0, max(1, len(words) - 5), 6)]
    located = [(o, w) for o, w in samples if ch.index.get(w)]

    def at_offset(first, o, k):
        # where word o of the rule should sit if the rule starts at token
        # `first`, with room for words the reader dropped or the page adds
        return abs(k - (first + o)) <= 15 + o // 10

    def coverage(first):
        hit = sum(1 for o, w in located if any(at_offset(first, o, k) for k in ch.index[w]))
        return hit / len(located) if located else 1.0

    firsts = [f for f in firsts if coverage(f) >= 0.5]
    # The hint only ORDERS the tries. The AI reader restarts its page count per
    # chunk, so a stored page can point at the wrong copy of wording a council
    # repeats per site (Leichhardt G6.15 C1 was rejected that way).
    if page_hint:
        firsts.sort(key=lambda k: ch.lines[ch.token_line[k]].page != page_hint)
    firsts = firsts[:12]
    out = []
    last = len(ch.token_line) - 1
    for first in firsts:
        out.append((ch.token_line[min(first + 5, last)], ch.token_line[first]))
        for st in range(len(words) - 6, -1, -1):
            occ = [k for k in ch.index.get(tuple(words[st:st + 6]), [])
                   if first <= k and at_offset(first, st, k)]
            if occ:
                # The copy at the expected place, not the first one in range:
                # closing words can recur in the next rule (Ashfield E2 C53/C54).
                k = min(occ, key=lambda k: abs(k - (first + st)))
                out.append((ch.token_line[min(k + 5, last)], ch.token_line[first]))
                break
    return out


def prove_citation(ref_number: str | None, text: str | None, ch: ChapterLines,
                   page_hint: int | None = None, page_proven: bool = False) -> dict:
    """-> {"status": proven | imprecise | not_proven | unjudged | text_not_found, "detail"}.

    imprecise: every piece is the council's and above the rule, but a more
    specific printed heading sits between -- true, too coarse to find the rule.
    """
    sections, item, why = split_ref(ref_number)
    bare = False
    if why == "bare integer section (not discriminating)":
        # Judged only against "Section N" / "Part N" / "Chapter N" headings.
        groups = code_groups(ref_number)
        if len(groups) > 1 and groups[-1][0]:
            item, groups = groups[-1], groups[:-1]
        sections, bare = [g for g in groups if len(g[1]) == 1][:1], True
        if not any(render(g).lower() in ch.keyword_heads for g in sections):
            return {"status": "unjudged", "detail": why}
    elif why:
        return {"status": "unjudged", "detail": why}
    names = [render(g).lower() for g in sections]
    # "G6 G6.15": the first token only names the parent of the second.
    sections = [g for g, n in zip(sections, names)
                if not any(o != n and o.startswith(n + ".") for o in names)]
    anchors = _anchors(ch, text, page_hint)
    if not anchors:
        return {"status": "text_not_found", "detail": "the rule's wording is not in its source"}
    # The same wording printed in several places (Parramatta repeats "Provisions" per
    # heritage area): judge the copy on the rule's own page when it has one. Any copy
    # proving let 7.10.3.4 stand for a rule printed under 7.10.4.4 (2026-10-30).
    # Only a page proven to hold the rule (page_check on_page/moved) narrows the search;
    # an unchecked stored page is the AI reader's chunk start and only orders it.
    if page_hint and page_proven:
        here = [(e, s) for e, s in anchors if ch.lines[s].page <= page_hint <= ch.lines[e].page]
        anchors = here or anchors
    item_code = render(item).lower() if item else None
    worst = coarse = None
    whole = {}
    for end, start in anchors:
        whole[start] = max(whole.get(start, end), end)
    for end, start in anchors:
        verdicts = [_prove_group(ch, end, start, g, item_code, bare, whole[start])
                    for g in sections]
        # The PDF's own bookmarks, when it has working ones, must agree: a "D5.6
        # development controls" line inside D5.1.5's chapter guide is a summary entry,
        # not the heading (Woollahra D5/D6, 2026-10-30).
        page = ch.lines[start].page
        verdicts = ["not_nearest:outside its bookmarked pages"
                    if (v == "proven" or v.startswith("imprecise"))
                    and outline_allows(ch, render(g).lower(), page) is False else v
                    for g, v in zip(sections, verdicts)]
        if all(v == "proven" for v in verdicts):
            return {"status": "proven", "detail": None}
        if coarse is None and all(v == "proven" or v.startswith("imprecise") for v in verdicts):
            coarse = verdicts
        if worst is None:
            worst = verdicts
    if coarse is not None:
        return {"status": "imprecise",
                "detail": "; ".join(f"{render(g)}: {v}" for g, v in zip(sections, coarse)
                                    if v != "proven")}
    failed = [f"{render(g)}: {v}" for g, v in zip(sections, worst) if v != "proven"]
    return {"status": "not_proven", "detail": "; ".join(failed)}


_BEST = {"proven": 3, "imprecise": 2}


def prove_citation_any(ref_number, text, readings, page_hint=None, page_proven=False) -> dict:
    """Proven if proven under ANY reading order (see both_orders). Otherwise the
    first reading's verdict, so the report names a real reason."""
    verdicts = [prove_citation(ref_number, text, ch, page_hint, page_proven) for ch in readings]
    best = max(verdicts, key=lambda v: _BEST.get(v["status"], 0))
    if best["status"] in _BEST:
        return best
    return verdicts[0]


# -- a label is proven only when EVERY piece of it was judged ---------------------

_SUB_ITEM = re.compile(r"\(\s*([A-Za-z0-9]{1,4})\s*\)")
_SUB_ITEM_OPEN = re.compile(r"(?:^|[\s_])([A-Za-z]{1,4})\)")


def unjudged_pieces(ref_number: str | None) -> list[str]:
    """The pieces of a label that prove_citation never checks. [] = every piece is judged.

    split_ref keeps the section codes and one item label and drops the rest: a bare
    number after a section ("B7 5. Table 1": "5" and "1"), a table or control number
    ("6.1.2.3 Control 4"), and every bracketed sub-item ("4.1.2(1)", "3_5_3_2 f)").
    The verdict then covers "B7" while the reader sees all of it: on 843 served setback
    rows a label shifted by one ("Table 1" -> "Table 2", "Control 4" -> "Control 5")
    still proved 60 times in 115 (2026-09-26). A label is only as proven as its
    least-checked piece.
    """
    tail = (ref_number or "").split("#")[-1].split("__")[-1]
    tail = re.sub(r"\.pdf$", "", tail, flags=re.I)
    subs = _SUB_ITEM.findall(tail) + _SUB_ITEM_OPEN.findall(tail)
    groups = code_groups(tail)
    sections, item, why = split_ref(tail)
    if why == "bare integer section (not discriminating)":
        # prove_citation judges the first bare number against "Section N" headings.
        gs = groups[:-1] if (len(groups) > 1 and groups[-1][0]) else groups
        sections, why = [g for g in gs if len(g[1]) == 1][:1], None
    judged = [] if why else sections + ([item] if item else [])
    names = [render(g).lower() for g in judged]
    # A piece naming only the parent of a judged one ("16" of "16.1") adds nothing unchecked.
    left = [render(g) for g in groups if g not in judged
            and not any(n.startswith(render(g).lower() + ".") for n in names)]
    return left + subs


def prove_label(ref_number, text, readings, page_hint=None, page_proven=False) -> dict:
    """prove_citation_any, with a verdict of 'partial' when the page proves some pieces
    of the label but the label also carries pieces nothing checked. 'partial' is not
    shown: a reader cannot tell the checked pieces from the unchecked ones."""
    verdict = prove_citation_any(ref_number, text, readings, page_hint, page_proven)
    if verdict["status"] in _BEST:
        left = unjudged_pieces(ref_number)
        if left:
            return {"status": "partial", "detail": f"not checked: {' '.join(left)}"}
    return verdict
