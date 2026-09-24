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

import collections
import re
from dataclasses import dataclass, field

# -- the ref's code ------------------------------------------------------------

_HEAD = re.compile(r"^([A-Za-z]{1,3})?(\d+[A-Za-z]?)$")
_CONT = re.compile(r"^\d+[A-Za-z]?$")


def code_groups(ref_number: str | None) -> list[tuple[str, list[str]]]:
    """Split a ref tail into (letter_prefix, [numeric parts]) groups, in order."""
    tail = (ref_number or "").split("__")[-1]
    tail = re.sub(r"\([^)]*\)", " ", tail)          # "(a)" sub-clauses: not a code
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
CODE_AT_START = re.compile(
    r"^(?:(?:part|section|chapter)\s+)?((?:[a-z]{1,3})?\d+[a-z]?(?:\.\d+[a-z]?)*)(?![\d.]*\d)")
#: A contents-page line: title, leaders or space, page number.
_TOC_LINE = re.compile(r"(\.{3,}|\s)\d{1,4}\s*$")
#: A page number in the top/bottom margin. Harmless as text, but "1" at the
#: foot of a page starts with a code and was taken as the heading "1".
_PAGE_NUMBER = re.compile(r"^(?:page\s+)?\d{1,4}$|^\d+(?:\.\d+)*\s*[-–]\s*\d+$")
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
    full_text: str = ""

    @classmethod
    def build(cls, raw: list[Line], page_width: float | None = None) -> "ChapterLines":
        by_page = collections.defaultdict(list)
        for ln in raw:
            by_page[ln.page].append(ln)
        toc = set()
        for page, pl in by_page.items():
            hits = sum(1 for x in pl if _TOC_LINE.search(x.text) and len(x.text) > 12)
            if pl and hits / len(pl) > 0.4:
                toc.add(page)
        # Running headers/footers repeat; a code line is kept even when it
        # repeats (a section named in every footer is still its heading).
        # ...but ONLY in the top and bottom margins. A council repeats real
        # control wording per site -- Leichhardt prints "Buildings are to be
        # designed in accordance with the desired future character statement"
        # under many sites -- and a repetition rule alone deleted the very line
        # being cited.
        bottom = max((x.y for x in raw), default=0.0)

        def in_margin(ln):
            return ln.y < 0.08 * bottom or ln.y > 0.92 * bottom

        rep = collections.Counter(x.text for x in raw if in_margin(x))
        furniture = {t for t, n in rep.items() if n >= 3 and not CODE_AT_START.match(t)}
        kept = []
        for page in sorted(by_page):
            for ln in sorted(by_page[page], key=lambda x: (x.y, x.x)):
                if in_margin(ln) and (ln.text in furniture or _PAGE_NUMBER.match(ln.text)):
                    continue
                kept.append(ln)
        out = cls(kept, toc, page_width=page_width)
        heads = collections.defaultdict(list)
        for i, ln in enumerate(kept):
            m = CODE_AT_START.match(ln.text)
            if m:
                heads[m.group(1)].append(i)
        out.heads_at = dict(heads)
        out.full_text = "\n".join(ln.text for ln in kept)
        for i, ln in enumerate(kept):
            for w in _WORD.findall(ln.text):
                out.tokens.append(w)
                out.token_line.append(i)
        idx = collections.defaultdict(list)
        for k in range(len(out.tokens) - 5):
            idx[tuple(out.tokens[k:k + 6])].append(k)
        out.index = idx
        return out


def load_lines(pdf_path: str) -> ChapterLines:
    """Read a PDF's lines with PyMuPDF (already a dependency) -- geometry the
    flattened page strings the gate grades words against do not keep."""
    import fitz
    raw = []
    width = None
    with fitz.open(pdf_path) as doc:
        for pno, page in enumerate(doc, 1):
            width = width or page.rect.width
            for block in page.get_text("dict")["blocks"]:
                for ln in block.get("lines", []):
                    t = " ".join(s["text"] for s in ln["spans"]).strip().lower()
                    if t:
                        raw.append(Line(pno, ln["bbox"][1], ln["bbox"][0], t))
    return ChapterLines.build(raw, page_width=width)


# -- proof -------------------------------------------------------------------------

_RANK = {"absent": 0, "cross_ref_only": 1, "not_nearest": 2, "ancestor_missing": 3,
         "item_missing": 4, "item_format": 5}


def _starts(text: str, code: str) -> bool:
    m = CODE_AT_START.match(text)
    return bool(m) and m.group(1) == code


def _shape(code: str) -> tuple[str, int]:
    m = re.match(r"([a-z]*)(.*)", code)
    return m.group(1), m.group(2).count(".")


#: "0.5 metre freeboard", "2.4m", "1.5 car space": a measurement, not a heading.
_MEASURE = re.compile(r"^[a-z]*\d+(?:\.\d+)*\s*(?:m\b|mm\b|m2\b|m\u00b2|metres?\b|%|car\b|spaces?\b|per\b|x\b)")


def _heading_like(line: Line, page_width: float | None) -> bool:
    """Can this line close a section? Not a long sentence, not a measurement, and
    not a navigation tab in the outer margin (Marrickville prints "8.5 HCA style
    sheets" at x=551 on every page of 8.4)."""
    return (len(line.text) < 90 and not _MEASURE.match(line.text)
            and (page_width is None or line.x < 0.75 * page_width))


def _ends_scope(other: str, leaf: str) -> bool:
    """Does a heading ``other``, printed between ``leaf`` and the rule, close leaf's scope?

    Same family (letter prefix) and either the same depth (8.2.39.6 after
    8.2.31.6), or shallower on the same first number without being leaf's own
    parent (8.2.39 after 8.2.31.6; G6.14 after G8.6.4 in the same prefix).
    A bare number or an undotted, unprefixed line is a list item, never a
    heading here: "2." inside a section must not end it, and neither must a
    table cell "1.5 car space per service room" under section 3.2.
    """
    if other == leaf or leaf.startswith(other + ".") or other.startswith(leaf + "."):
        return False
    fam_o, depth_o = _shape(other)
    fam_l, depth_l = _shape(leaf)
    if fam_o != fam_l or ("." not in other and not fam_o):
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


def _prove_group(ch: ChapterLines, end: int, start: int, group, item: str | None) -> str:
    L, toc = ch.lines, ch.toc_pages
    best = "absent"

    def keep(verdict):
        nonlocal best
        if _RANK[verdict.split(":")[0]] > _RANK[best.split(":")[0]]:
            best = verdict

    for pieces, numbered in _readings(group):
        leaf = pieces[-1]
        at = ch.heads_at.get(leaf, [])
        heads = [i for i in at if i <= end and L[i].page not in toc]
        # A heading set in a side column can sort just after the rule's first line.
        heads += [i for i in at if end < i < end + 12 and L[i].page == L[end].page]
        if not heads:
            if leaf in ch.full_text:
                keep("cross_ref_only")
            continue
        above = [i for i in heads if i <= end]
        h = max(above) if above else min(heads)   # below only for a side-column heading
        lo = min(h, start)
        between = [L[i].text for i in range(lo + 1, end + 1)
                   if L[i].page not in toc and _heading_like(L[i], ch.page_width)
                   and (m := CODE_AT_START.match(L[i].text)) and _ends_scope(m.group(1), leaf)]
        if between:
            keep("not_nearest:" + between[-1][:30])
            continue
        if not all(any(i <= end for i in ch.heads_at.get(a, [])) for a in pieces[:-1]):
            keep("ancestor_missing")
            continue
        hi = min(len(L), end + 3)
        if numbered and not any(re.match(r"^\(?" + re.escape(numbered) + r"[.)]\s", L[i].text)
                                for i in range(lo, hi)):
            keep("item_missing")
            continue
        if item:
            if any(_starts(L[i].text, item) or re.match("^" + re.escape(item) + r"[.)]", L[i].text)
                   for i in range(lo, hi)):
                return "proven"
            digits = re.sub(r"^[a-z]+", "", item)
            if digits and any(re.match(r"^\(?" + re.escape(digits) + r"[.)]\s", L[i].text)
                              for i in range(lo, hi)):
                keep("item_format")    # council prints "7." -- we store "C7"
                continue
            keep("item_missing")
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
                   if first <= k <= first + len(words) + 60]
            if occ:
                out.append((ch.token_line[min(occ[0] + 5, last)], ch.token_line[first]))
                break
    return out


def prove_citation(ref_number: str | None, text: str | None, ch: ChapterLines,
                   page_hint: int | None = None) -> dict:
    """-> {"status": proven | not_proven | unjudged | text_not_found, "detail": str|None}."""
    sections, item, why = split_ref(ref_number)
    if why:
        return {"status": "unjudged", "detail": why}
    names = [render(g).lower() for g in sections]
    # "G6 G6.15": the first token only names the parent of the second.
    sections = [g for g, n in zip(sections, names)
                if not any(o != n and o.startswith(n + ".") for o in names)]
    anchors = _anchors(ch, text, page_hint)
    if not anchors:
        return {"status": "text_not_found", "detail": "the rule's wording is not in its source"}
    item_code = render(item).lower() if item else None
    worst = None
    for end, start in anchors:
        verdicts = [_prove_group(ch, end, start, g, item_code) for g in sections]
        if all(v == "proven" for v in verdicts):
            return {"status": "proven", "detail": None}
        if worst is None:
            worst = verdicts
    failed = [f"{render(g)}: {v}" for g, v in zip(sections, worst) if v != "proven"]
    return {"status": "not_proven", "detail": "; ".join(failed)}
