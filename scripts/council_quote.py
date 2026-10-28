"""Copy each served council DCP rule's quote from the council's own PDF. Dry run only.

prior-art-checked: nothing copies a council's text back out of its PDF.
`dcp_fidelity_gate.ground_row` checks a row's words and numbers are printed;
`citation_proof` proves its clause number; `dcp_page_repair` / `rule_page_locator`
find its page. All three compare lowercased tokens and write no text. The
full-quote probe (~/.claude/plans/ce-council-words-probes/full_quote_probe.py)
measured the gap this closes: 4,552 of 19,627 served quotes are not printed word
for word (plan: ~/.claude/plans/ce-council-words-PLAN-2026-10-12.md).

THE STATES (per rule)
---------------------
exact          the whole stored quote is printed, in order (spacing, punctuation and
               line breaks ignored). The council's text over that span is copied,
               with its own casing and punctuation.
recovered      the quote is not printed whole, but its opening and closing words are,
               close together: the council's text between them is copied. Or only
               the opening is printed, at a label ("(b)", "C3", "2.1"): copied from
               that label to the next label of the same kind.
not_a_control  map labels, a figure caption or a contents page, not a rule.
unconfirmed    none of the above; `reason` says why. Numbers from these are never used.

Matching runs on the cached lowercase lines (citation_proof cache) in both reading
orders. The cache is lowercased, so each line's original text is re-read from the
same PDF with PyMuPDF and joined back by position (page, y, x).

Usage:
    python scripts/council_quote.py --dry-run [--council waverley [--chapter k]] [--ids 1,2] [--out f.json]
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

CACHE = Path(os.environ.get("TEMP", "/tmp")) / "dq111_lines"
ALNUM = set("abcdefghijklmnopqrstuvwxyz0123456789")
MIN_CHARS = 25          # a shorter quote matches by chance; exact only on its own page or once
ANCHOR = 6              # words in an opening/closing anchor
ANCHOR_SLIDE = 25       # anchors may start this many words into the quote (a running header first)
SPAN_MIN, SPAN_MAX = 0.5, 2.0   # copied span length vs stored quote length
MIN_OVERLAP = 0.6       # share of the stored quote's words the copied text must hold
LABEL_LINES = 40        # a label-bounded copy stops after this many lines...
LABEL_PAGES = 1         # ...or this many page breaks
DOUBLED_MIN_CHARS = 20
DOUBLED_MIN_PAIRS = 50   # a short or table-heavy chapter with one repeated sentence is not a doubled layer
DOUBLED_SHARE = 0.15   # a chapter where this share of lines repeat the line before is a doubled text layer
REPEATED = 5           # a line printed on this many pages is a running header/footer at a copy's edge
LABEL_WORDS = 4         # a drawing's label is a short line: "Rear boundary", "3 / 8m", ">400m²"
OVERSIZED = 4500        # a stored quote this long is several controls: flag for splitting. 2500 hid 43 rows
# printed word for word or recovered, all under 4,100 chars (2026-10-29).
PIECE_PAGES = 1         # a multi-line rule's lines (lead-in, item) lie within this many pages of the first
KNOWN = (126292, 87150, 95878, 105200, 130236, 150954)

_WORD = re.compile(r"[a-z0-9]+")
#: Typesetting ligatures PDFs print as one character: "speciﬁcations" is "specifications".
LIGATURES = str.maketrans({"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi",
                           "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st"})
#: A unit's superscript: a reader writes "m²" where the text layer holds "m2" (Hornsby pilot,
#: 2026-10-12: 17 of 61 misses were tables and "m²"), and norm() would drop "²" altogether.
#: Only after "m": a superscript elsewhere is a footnote mark, and "24³" must never read as "243".
UNIT_SUP = {"²": "2", "³": "3"}
_UNIT_SUP = re.compile(r"(?<=[mM])[²³]")
_NUM = re.compile(r"\d+(?:\.\d+)?")
_FIGURE = re.compile(r"^\s*(?:figure|fig\.|map|diagram)\s*\d", re.I)
#: A rule whose own code names a figure, map or diagram (as a reader codes a drawing's labels).
_FIGURE_CODE = re.compile(r"^\s*(?:figure|fig\.|map|diagram)\b", re.I)
#: Positive sign of a sentence, so of a possible rule: a verb of state or obligation, or a full stop
#: ending a word. Labels ("Street tree", "6m setback", "Building line") carry neither.
_SENTENCE = re.compile(r"\b(?:is|are|be|been|was|were|will|may|can|cannot|not|no|prohibited|permitted|"
                       r"required|encouraged|discouraged|avoid|provide|provided|ensure|retain|maintain|"
                       r"allowed|need|needs|apply|applies)\b|[a-z]\.(?:\s|$)")
#: A line that is only a list label: "3.", "(b)", "g)", "C.04".
_BARE_LABEL = re.compile(r"^\(?(?:[a-z]|\d{1,2}|[ivx]{1,4}|[A-Z]\.?\d{1,3})[.)]?$", re.I)
#: A line that begins with a list label and then words: "5. Rear setbacks:", "ii. chimneys and antennas", "(b) Fences".
_LABELLED = re.compile(r"^\(?(?:[a-z]|\d{1,2}|[ivx]{1,4})[.)]\s+[A-Za-z]")
#: How a sentence, a lead-in or a list item ends: "... the development.", "... the following:", "...; and".
_PIECE_END = re.compile(r"(?:[.:;?!)][\"'”’]?|;\s*(?:and|or))\s*$", re.I)
# A letter list label printed alone on its line ("a.", "(b)", "iv)"). The reader often drops it when it
# joins the label to the words beside it ("Height Sites with ..." for "Height / a. / Sites with ...").
# Never a number, punctuated or not: "3" or "3." alone can be a table value (cross-review, #1519).
_LIST_LABEL = re.compile(r"^(?:\((?:[a-z]|[ivx]{1,4})\)|(?:[a-z]|[ivx]{1,4})[.)])$", re.I)
# A lone letter is a list label only when the label before or after it in the same list is printed
# nearby: a map key's "(x)" (City of Sydney Section 6, "brackets indicate additional height") or a
# flood category "A." has no neighbour, so it is never skipped (cross-review, #1519).
LABEL_NEAR = 40
_ROMAN = "i ii iii iv v vi vii viii ix x xi xii xiii xiv xv xvi xvii xviii xix xx".split()


def _label_keys(t: str) -> set[tuple[str, str, int]]:
    """(wrapping, numbering, position) readings of a list-label line; "i)" is both letter 9 and roman 1."""
    s = t.strip().lower()
    wrap, core = ("()", s[1:-1]) if s.startswith("(") else (s[-1], s[:-1])
    keys = {(wrap, "roman", _ROMAN.index(core) + 1)} if core in _ROMAN else set()
    if len(core) == 1:
        keys.add((wrap, "letter", ord(core) - 96))
    return keys


def list_label_lines(text: list[str]) -> set[int]:
    """Indexes of lone list-label lines with a neighbour label of the same list within LABEL_NEAR lines."""
    labels = {i: _label_keys(t) for i, t in enumerate(text) if _LIST_LABEL.match(t.strip())}
    out = set()
    for i, keys in labels.items():
        near = [labels[j] for j in range(max(0, i - LABEL_NEAR), i + LABEL_NEAR + 1) if j != i and j in labels]
        if any((w, n, p + d) in other for w, n, p in keys for d in (-1, 1) for other in near):
            out.add(i)
    return out
_LEGEND = re.compile(r"legend\s*[:.\-–—]?")
_RULE_WORDS = re.compile(r"\b(?:must|shall|should|are to|is to|to be|maximum|minimum|min\.|max\.)\b")
# A contents page: section numbers with a dot ("3.2.1", "D5.4.6") before a title, or titles ending in page numbers
# after dot leaders or a pipe ("Setbacks ....... 46", "3.1.2 Setbacks | 3-9"). Hornsby Part 3 page 2 was stored as
# rules and proven, because its words ARE in the PDF (2026-10-28: 38 such rows, 17 shown).
_CONTENTS_NUM = re.compile(r"^(?:[a-z]{0,2}\d+(?:\.\d+)+\.?|part \d+|appendix \d+|schedule \d+)(?:\s*\|)?\s+[a-z(]")
_CONTENTS_PAGE = re.compile(r"(?:\.{4,}|…{2,}|�{3,})\s*[a-z]?[\d-]+\s*$")
_CONTENTS_PIPE = re.compile(r"^[a-z]{0,2}\d+(?:\.\d+)+\s.*\|\s*\d+-\d+\s*$")
#: A label at a line start, by kind. Kinds must match for a label to end a copy.
_LABELS = (
    ("paren_alpha", re.compile(r"^\(([a-z])\)")),
    ("paren_roman", re.compile(r"^\(((?:i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii))\)")),
    ("paren_num", re.compile(r"^\((\d{1,2})\)")),
    ("alpha_dot", re.compile(r"^([a-z])[.)]\s")),
    ("num_dot", re.compile(r"^(\d{1,2})[.)]\s")),
    ("code", re.compile(r"^([a-z]{1,3}\d+[a-z]?)(?![\w.])")),
    ("dotted", re.compile(r"^(\d+(?:\.\d+)+)(?![\d.]*\d)")),
)


def norm(s: str | None) -> str:
    s = _UNIT_SUP.sub(lambda m: UNIT_SUP[m.group(0)], (s or "").translate(LIGATURES))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def label_kind(text: str) -> tuple[str, str] | None:
    """(kind, depth key) of a label opening this line, else None. Roman before alpha: "(i)"."""
    t = text.strip().lower()
    for kind, rx in (_LABELS[1], _LABELS[0]) + _LABELS[2:]:
        m = rx.match(t)
        if m:
            key = m.group(1)
            if kind == "code":
                key = re.match(r"[a-z]+", key).group(0)      # C3 and C4 are one kind; O1 another  # noqa: zone-codes (DCP control labels)
            elif kind == "dotted":
                key = str(key.count("."))                    # 2.1 and 2.2 are one depth
            else:
                key = ""
            return kind, key
    return None


# -- the council's lines, with their own casing ----------------------------------

def cased_text(pdf_path: str) -> dict:
    """(page, y, x, lowercased text) -> the line as printed. Same join as read_raw_lines."""
    import fitz
    out = {}
    with fitz.open(pdf_path) as doc:
        for pno, page in enumerate(doc, 1):
            for block in page.get_text("dict")["blocks"]:
                for ln in block.get("lines") or []:
                    t = " ".join(s["text"] for s in ln["spans"]).strip()
                    if t:
                        out[(pno, ln["bbox"][1], ln["bbox"][0], t.lower())] = t
    return out


def load_chapter(r2_path: str):
    """Both readings (citation_proof.ChapterLines) and the cased-text map for one chapter PDF."""
    import citation_proof as cp
    import dq_probe_section_code_not_in_source as probe
    local = CACHE / "pdf" / (probe._cache_file(CACHE, r2_path).stem + ".pdf")
    if not local.exists():
        import dcp_page_repair as dpr
        local.parent.mkdir(parents=True, exist_ok=True)
        dpr._s3().download_file(os.environ["R2_BUCKET_NAME"], r2_path, str(local))
    lf = probe._cache_file(CACHE, r2_path)
    if not lf.exists():
        lines, width = cp.read_raw_lines(str(local))
        lf.write_text(json.dumps({"width": width, "lines": [[x.page, x.y, x.x, x.text] for x in lines]}),
                      encoding="utf-8")
    data = json.loads(lf.read_text(encoding="utf-8"))
    readings = cp.both_orders([cp.Line(*x) for x in data["lines"]], data["width"])
    return readings, cased_text(str(local))


def doubled_lines(lines) -> set[int]:
    """Indexes of lines that repeat the line just before them, when the whole chapter is printed that way.
    Measured 2026-10-29 over every chapter with an unproven shown rule (lines of 20+ characters): the
    doubled chapter 0.33, the next highest 0.04. Counting short lines too, a Wollongong plant table scored 0.23.
    Campbelltown's text layer holds every line twice ("a)	The location of" then "The location of"), so
    no rule could be matched in one piece (2026-10-29: 4 of 5 sampled Campbelltown refusals). A chapter
    with only the odd repeat keeps it: there it may be the council's own wording."""
    out, long_lines, long_doubled = set(), 0, 0
    for i in range(1, len(lines)):
        a, b = norm(lines[i - 1].text), norm(lines[i].text)
        # Only sentence-length lines decide it: a table's short cells ("Y", "Y") repeat for real.
        long_lines += len(b) >= DOUBLED_MIN_CHARS
        if b and lines[i].page == lines[i - 1].page and a.endswith(b):
            out.add(i)
            long_doubled += len(b) >= DOUBLED_MIN_CHARS
    doubled = long_doubled >= DOUBLED_MIN_PAIRS and long_doubled >= DOUBLED_SHARE * long_lines
    return out if doubled else set()


class Stream:
    """One reading as a normalized character stream; each character knows its line and offset."""

    def __init__(self, ch, cased: dict, skip_labels: bool = False):
        doubled = doubled_lines(ch.lines)
        self.lines = [ln for i, ln in enumerate(ch.lines) if i not in doubled]
        self.text = [cased.get((ln.page, ln.y, ln.x, ln.text), ln.text).translate(LIGATURES)
                     for ln in self.lines]
        self.cased_share = sum(1 for ln in self.lines if (ln.page, ln.y, ln.x, ln.text) in cased) / max(1, len(self.lines))
        # Lines whose printed casing was not re-read. A picture label named by OCR ("c3") has no
        # text layer and is short; anything longer must not be passed off as the council's text.
        self.uncased = {i for i, ln in enumerate(self.lines)
                        if (ln.page, ln.y, ln.x, ln.text) not in cased and len(norm(ln.text)) > 4}
        buf, self.at = [], []
        skip = list_label_lines(self.text) if skip_labels else set()
        for i, t in enumerate(self.text):
            if i in skip:
                continue     # the label line stays in copy(): only the search skips it
            for p, c in enumerate(t):
                if c in UNIT_SUP and p and t[p - 1] in "mM":     # the copy keeps the council's "m²"
                    c = UNIT_SUP[c]
                for c2 in c.lower():
                    if c2 in ALNUM:
                        buf.append(c2)
                        self.at.append((i, p))
        self.s = "".join(buf)
        # A running header/footer/banner: the same line at the same spot on REPEATED+ pages.
        # Position matters: Leichhardt repeats real control wording per site, at varying heights.
        spot = collections.defaultdict(set)
        for ln in self.lines:
            spot[(ln.text, round(ln.y / 5), round(ln.x / 5))].add(ln.page)
        self.repeated = {k[0] for k, ps in spot.items()
                         if len(ps) >= REPEATED and not label_kind(k[0])}   # "(a)" sits at one spot too
        # Numbers in the lines the reading dropped (page margins, page numbers): "2012", "2.9-7".
        kept = {(ln.page, ln.y, ln.x, ln.text) for ln in ch.lines}
        self.margin_nums = collections.defaultdict(set)
        self.furniture_words = collections.defaultdict(set)   # margins + running headers, per page
        for key in cased:
            if key not in kept:
                self.margin_nums[key[0]].update(_NUM.findall(key[3]))
                self.furniture_words[key[0]].update(_WORD.findall(key[3].translate(LIGATURES)))
        for ln in self.lines:
            if ln.text in self.repeated:
                self.furniture_words[ln.page].update(_WORD.findall(ln.text.translate(LIGATURES)))

    def casing_unread(self, k0: int, k1: int) -> bool:
        return any(i in self.uncased for i in range(self.at[k0][0], self.at[k1][0] + 1))

    def furniture(self, pages) -> set:
        return set().union(*(self.furniture_words[p] for p in pages))

    def page(self, k: int) -> int:
        return self.lines[self.at[k][0]].page

    def find_all(self, q: str, cap: int = 60) -> list[int]:
        out, k = [], self.s.find(q)
        while k != -1 and len(out) < cap:
            out.append(k)
            k = self.s.find(q, k + 1)
        return out

    def copy(self, k0: int, k1: int) -> str:
        """The council's text from stream char k0 to k1 inclusive, lines joined by newlines.
        A running header or footer (a line printed on REPEATED+ pages) is trimmed from either
        end -- Ashfield prints its chapter banner sideways mid-page, beyond any margin."""
        (i0, p0), (i1, p1) = self.at[k0], self.at[k1]
        first, last = self.text[i0], self.text[i1]
        while p0 > 0 and first[p0 - 1] in "(\"'“‘[":
            p0 -= 1
        while p1 + 1 < len(last) and (last[p1 + 1] in ".;:)%\"'”’]" or last[p1 + 1].isalpha()):
            p1 += 1
        if i0 == i1:
            return first[p0:p1 + 1]
        parts = [(i0, first[p0:])] + [(i, self.text[i]) for i in range(i0 + 1, i1)] + [(i1, last[:p1 + 1])]
        while len(parts) > 1 and self.lines[parts[0][0]].text in self.repeated:
            parts.pop(0)
        while len(parts) > 1 and self.lines[parts[-1][0]].text in self.repeated:
            parts.pop()
        return "\n".join(t for _i, t in parts)

    def copy_from_label(self, k0: int) -> tuple[str, int] | None:
        """From the label opening k0's line (or the label line just above) to before the next
        label of the same kind. None when no label is there."""
        i0 = self.at[k0][0]
        start = None
        for i in (i0, i0 - 1):
            if i >= 0 and (lk := label_kind(self.text[i])):
                start = i
                break
        if start is None:
            return None
        end, breaks, bounded = start, 0, start + 1 >= len(self.text)
        for i in range(start + 1, min(len(self.text), start + LABEL_LINES)):
            if self.lines[i].page != self.lines[i - 1].page:
                breaks += 1
                if breaks > LABEL_PAGES:
                    break
            if label_kind(self.text[i]) == lk or self.lines[i].text.startswith(("figure ", "table ")):
                bounded = True
                break
            end = i
        else:
            bounded = end == len(self.text) - 1          # ran out of document, not out of cap
        # Stopped by the line or page cap, not by the council's next label: the copy may be cut short.
        if not bounded or any(i in self.uncased for i in range(start, end + 1)):
            return None
        return "\n".join(self.text[start:end + 1]), self.lines[start].page


# -- one rule ---------------------------------------------------------------------

def overlap(stored: str, copied: str) -> float:
    a = collections.Counter(_WORD.findall(stored.lower()))
    b = collections.Counter(_WORD.findall(copied.lower()))
    return sum((a & b).values()) / max(1, sum(a.values()))


def missing_numbers(stored: str, copied: str) -> list[str]:
    have = set(_NUM.findall(copied))
    return sorted({n for n in _NUM.findall(stored) if n not in have})


def is_map_labels(body: str) -> bool:
    toks = _WORD.findall(body.lower())
    return len(toks) >= 20 and sum(1 for t in toks if len(t) == 1 and t.isalpha()) / len(toks) >= 0.3


def figure_kind(body: str) -> str | None:
    """A figure's legend or a bare caption is not a rule. A rule that merely STARTS with a figure
    title ("Figure 4d: Parking ... 4.4 Where a setback applies, buildings are to ...") still is."""
    if not _FIGURE.match(body):
        return None
    lines = [ln.strip().lower() for ln in body.strip().splitlines() if ln.strip()]
    # Anything after the title that reads as a rule -- a numbered or labelled line, or rule wording --
    # makes it a rule, however short ("Figure 4d: Parking / 4.4 Garages are to be set back 1m"),
    # even under a legend.
    if any(label_kind(ln) or _RULE_WORDS.search(ln) for ln in lines[1:]):
        return None
    if any(_LEGEND.fullmatch(ln) for ln in lines[:4]):
        return "figure_legend"
    return "figure_caption" if len(_WORD.findall(body.lower())) <= 25 else None


def contents_kind(body: str) -> str | None:
    """A contents page is not a rule, though every word of it is in the PDF. Five or more lines, and either three or
    more (and 40%+) end in a page number, or 60%+ start with a dotted section number and none reads as a rule. A table
    of numbers ("9.0 - < 11.0 | 1.1") is not a title, so a setback table stays a rule."""
    lines = [ln.strip().lower() for ln in (body or "").splitlines() if ln.strip()]
    if lines and lines[0] in ("contents", "table of contents"):
        lines = lines[1:]
    if len(lines) < 5:
        return None
    # A line with rule wording ("Maximum height .... 9") is a standard, not a title, whatever its dots
    paged = sum(1 for ln in lines if (_CONTENTS_PAGE.search(ln) or _CONTENTS_PIPE.match(ln))
                and not _RULE_WORDS.search(ln))
    if paged >= 3 and paged / len(lines) >= 0.4:
        return "contents_page"
    # A title carries no value: "3.1 Building height 9 metres" is a control, "3.1.2 Setbacks" a title
    # and is short: "3.1 Locate parking behind the building line on corner sites" is a command
    numbered = sum(1 for ln in lines if _CONTENTS_NUM.match(ln) and not re.search(r"\d", _CONTENTS_NUM.sub("", ln))
                   and len(ln.split()) <= 8)
    if numbered / len(lines) >= 0.6 and not any(_RULE_WORDS.search(ln) for ln in lines):
        return "contents_page"
    return None


def are_labels(body: str) -> bool:
    """A drawing's labels, by their shape: two or more lines, each of LABEL_WORDS words or fewer,
    and no rule wording or sign of a sentence anywhere. Hornsby Figure 3.1-f, as read:
    "Rear boundary / 3 / 8m / Secondary boundary / Dwelling 1". A one-line instruction
    ("Locate vehicle access on Smith Street") is not labels, whatever its verb."""
    lines = [ln for ln in body.lower().splitlines() if ln.strip()]
    return (len(lines) >= 2 and all(len(_WORD.findall(ln)) <= LABEL_WORDS for ln in lines)
            and not _RULE_WORDS.search(body.lower()) and not _SENTENCE.search(body.lower()))


def prove_pieces(body: str, streams: list[Stream], cqt, page: int | None = None) -> dict | None:
    """{'quote', 'quote_page'} when every line of a multi-line rule is printed whole, in order, close together.

    The section reader stores a list item with its lead-in ("C.09 A carwash bay must be provided in accordance
    with the following:" / "g) Approval must be obtained ..."): both printed word for word, items (a)-(f) between
    them. Not one run of text, so the whole-quote match misses it and the anchors find no end (Parramatta
    2026-10-15: 193 of 272 unconfirmed). Each prose line must be printed whole in ONE reading, after the line
    before it, within PIECE_PAGES of the first; a "cell | cell" line must be a proven table row on a page in that
    window. The quote is the council's own text of each line; nothing between them is copied or claimed.

    Two guards from the 2026-10-15 dry run (255 passes, eye-checked): the first line must sit on the stored page
    or the one before it (a lead-in turns the page) -- short generic lines matched 61 pages away; and every prose
    line must be MIN_CHARS long or a bare label ("3.") -- old two-column rows hold fragments ("Village.",
    "retained and conserved.") that are each printed but are not one of the council's sentences."""
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    prose = [ln for ln in lines if "|" not in ln]
    # A line that starts with its own list label is one of the council's items, not a two-column fragment: a
    # labelled lead-in may be short ("5. Rear setbacks:") and the last labelled item may end without a full stop
    # ("ii. chimneys and antennas"). Penrith 2026-10-28: 27 shown rules hidden behind a plan link by these guards.
    short_ok = {i for i, ln in enumerate(prose) if _LABELLED.match(ln) and ln.endswith(":")}
    open_ok = {len(prose) - 1} if prose and _LABELLED.match(prose[-1]) else set()
    if (not page or len(lines) < 2 or not prose or "|" in lines[0]
            or any(len(norm(ln)) < MIN_CHARS and not _BARE_LABEL.match(ln) and i not in short_ok
                   for i, ln in enumerate(prose))
            # a fragment stops mid-sentence ("To improve the image, quality and amenity of", Ashfield 123339)
            or any(not _BARE_LABEL.match(ln) and not _PIECE_END.search(ln) and i not in open_ok
                   for i, ln in enumerate(prose))):
        return None
    for st in streams:
        for k0 in st.find_all(norm(lines[0])):
            out, end, p0 = [], -1, st.page(k0)
            if p0 not in (page, page - 1):
                continue
            for ln in lines:
                if "|" in ln:
                    row = next((r for p in range(p0, p0 + PIECE_PAGES + 1)
                                if (r := cqt._prove_row(cqt._cells(ln), st, p, norm))), None)
                    if row is None:
                        break
                    out.append(row)
                    continue
                q = norm(ln)
                k = k0 if not out else next((h for h in st.find_all(q, cap=200) if h > end), None)
                if not q or k is None:
                    break
                e = k + len(q) - 1
                if st.page(e) - p0 > PIECE_PAGES or st.casing_unread(k, e):
                    break
                # a relaxed line must stay in its own list: no other lead-in ("...:") printed between it and the
                # line before (cross-review 2026-10-28: "ii. chimneys and antennas" of a LATER list on the page)
                if out and (short_ok or open_ok) and end + 1 < k and re.search(r":\s*$", st.copy(end + 1, k - 1), re.M):
                    break
                out.append(st.copy(k, e))
                end = e
            else:
                return {"quote": "\n".join(out), "quote_page": p0}
    return None


def judge(row: dict, streams: list[Stream]) -> dict:
    import rule_page_locator as rpl
    body = rpl.rule_body(row["provision_text"])
    q = norm(body)
    out = {"id": row["id"], "council": row["source_council"], "stored_page": row["pdf_page"],
           "page_check": row["page_check"], "needs_split": len(body) > OVERSIZED}
    if contents_kind(body):
        return {**out, "status": "not_a_control", "reason": "contents_page"}
    if is_map_labels(body) or figure_kind(body):
        return {**out, "status": "not_a_control", "reason": "map_labels" if is_map_labels(body) else figure_kind(body)}
    # A drawing's labels, coded as the figure they sit in ("Figure 3.2", "Map 1"), with no rule
    # wording: Hornsby pilot 2026-10-12, 12 of 61 misses. A coded figure that reads as a sentence
    # ("must", "is prohibited", a full stop) stays a rule and is judged as one.
    if _FIGURE_CODE.match(str(row.get("code") or "")) and are_labels(body):
        return {**out, "status": "not_a_control", "reason": "figure_labels"}
    if len(body) > OVERSIZED:      # several controls in one row: the brief refuses it until split
        return {**out, "status": "unconfirmed", "reason": "oversized"}
    if not any(st.s for st in streams):
        return {**out, "status": "unconfirmed", "reason": "no_text_in_pdf"}

    # exact: the whole quote printed in order
    places = [(st, k) for st in streams for k in st.find_all(q)] if q else []
    pages = {st.page(k) for st, k in places}
    if places and (len(q) >= MIN_CHARS or len(pages) == 1 or row["pdf_page"] in pages):
        st, k = next(((s, k) for s, k in places if s.page(k) == row["pdf_page"]), places[0])
        if st.casing_unread(k, k + len(q) - 1):
            return {**out, "status": "unconfirmed", "reason": "casing_unread"}
        text = st.copy(k, k + len(q) - 1)
        return {**out, "status": "exact", "reason": "one_place" if len(pages) == 1 else f"places:{len(pages)}",
                "quote_page": st.page(k), "quote": text}
    # a table row written "cell | cell": proven cell by cell on one printed row (scripts/council_quote_table.py)
    import council_quote_table as cqt
    table = cqt.prove_rows(body, streams, row["pdf_page"], norm)
    if table:
        return {**out, "status": "exact", "reason": "table_rows", **table}
    pieces = prove_pieces(body, streams, cqt, row["pdf_page"])
    if pieces:
        return {**out, "status": "exact", "reason": "pieces", **pieces}
    if len(q) < MIN_CHARS:
        return {**out, "status": "unconfirmed", "reason": "too_short" if not places else "too_short_many_places"}

    # recovered: opening and closing words printed close together
    toks = rpl.tokens(body)
    if len(toks) < ANCHOR + 1:
        return {**out, "status": "unconfirmed", "reason": "not_found_short"}
    best = None
    for st in streams:
        starts = None
        for j in range(0, min(ANCHOR_SLIDE, len(toks) - ANCHOR) + 1):
            hits = st.find_all("".join(toks[j:j + ANCHOR]))
            if hits:
                starts = (j, hits)
                break
        if not starts:
            continue
        ends = None
        for j in range(len(toks) - ANCHOR, max(len(toks) - ANCHOR - ANCHOR_SLIDE, starts[0]) - 1, -1):
            a = "".join(toks[j:j + ANCHOR])
            hits = st.find_all(a)
            if hits:
                ends = (j, [h + len(a) - 1 for h in hits])
                break
        for s in starts[1]:
            for e in (ends[1] if ends else []):
                span = e - s + 1
                if not (SPAN_MIN * len(q) <= span <= SPAN_MAX * len(q)) or st.page(e) - st.page(s) > 2:
                    continue
                score = (st.page(s) != row["pdf_page"], abs(span - len(q)))
                if best is None or score < best[0]:
                    best = (score, st, s, e, starts[0], len(toks) - ANCHOR - ends[0])
    if best:
        _sc, st, s, e, head_cut, tail_cut = best
        if st.casing_unread(s, e):
            return {**out, "status": "unconfirmed", "reason": "casing_unread"}
        text = st.copy(s, e)
        ov = overlap(body, text)
        # Words cut from either end must be page furniture: a cut footer ("Sydney DCP 2012 2.9-7")
        # or banner is fine; a cut table row ("Capacity: 300") or opening sentence is not.
        pages = range(st.page(s) - 1, st.page(e) + 2)
        furniture = st.furniture(pages)
        cut = toks[:head_cut] + (toks[len(toks) - tail_cut:] if tail_cut else [])
        real = [t for t in cut if t not in furniture]
        if real:
            lost = sorted({t for t in real if any(c.isdigit() for c in t)})
            return {**out, "status": "unconfirmed", "reason": "values_cut" if lost else "words_cut",
                    "lost_numbers": lost, "cut_words": real[:12]}
        if ov >= MIN_OVERLAP:
            return {**out, "status": "recovered", "reason": "anchors", "quote_page": st.page(s),
                    "quote": text, "overlap": round(ov, 3), "head_cut_words": head_cut,
                    "tail_cut_words": tail_cut,
                    # the complete council text between two printed anchors lacks these: the stored
                    # row's numbers, not the council's. Phase C uses only numbers in the quote.
                    "missing_numbers": [n for n in missing_numbers(body, text)
                                        if not any(n in st.margin_nums[p] for p in pages)]}
        return {**out, "status": "unconfirmed", "reason": "low_overlap", "overlap": round(ov, 3)}

    # recovered: opening only, bounded by the council's own labels
    for st in streams:
        hits = st.find_all("".join(toks[:ANCHOR]))
        hits.sort(key=lambda k: st.page(k) != row["pdf_page"])
        for k in hits:
            got = st.copy_from_label(k)
            if got:
                text, page = got
                ov = overlap(body, text)
                near = range(page - 1, page + 3)
                gone = [n for n in missing_numbers(body, text) if not any(n in st.margin_nums[p] for p in near)]
                if gone:   # a label-bounded copy can stop short of a value: never recovered then
                    return {**out, "status": "unconfirmed", "reason": "values_missing", "lost_numbers": gone}
                if ov >= MIN_OVERLAP and len(norm(text)) <= SPAN_MAX * len(q):
                    return {**out, "status": "recovered", "reason": "label_bounded", "quote_page": page,
                            "quote": text, "overlap": round(ov, 3), "missing_numbers": []}
    found = sum(1 for st in streams for _ in st.find_all("".join(toks[:ANCHOR]), cap=1))
    return {**out, "status": "unconfirmed", "reason": "opening_found_no_bound" if found else "not_found"}


def judge_twice(row: dict, streams: list[Stream], unlabelled: list[Stream]) -> dict:
    """judge() as printed; only a rule not proven that way is judged again with lone list-label
    lines skipped, so no verdict reached as printed can change."""
    res = judge(row, streams)
    if res["status"] == "unconfirmed" and res["reason"] != "oversized":
        res2 = judge(row, unlabelled)
        if res2["status"] != "unconfirmed":
            return {**res2, "reason": f"{res2['reason']}+label_skipped"}
    return res


def chapter(args) -> tuple[list[dict], str | None]:
    r2_path, rows = args
    from dotenv import load_dotenv
    load_dotenv(ROOT.parents[2] / ".env" if (ROOT.parents[2] / ".env").exists() else ROOT / ".env")
    try:
        readings, cased = load_chapter(r2_path)
    except Exception as e:  # noqa: BLE001 -- one bad PDF must not stop the fleet
        return [{"id": r["id"], "council": r["source_council"], "stored_page": r["pdf_page"],
                 "page_check": r["page_check"], "needs_split": False, "status": "unconfirmed",
                 "reason": "pdf_unreadable", "source_path": r2_path,
                 "text_md5": hashlib.md5((r["provision_text"] or "").encode("utf-8")).hexdigest()}
                for r in rows], f"{r2_path}: {e}"[:200]
    streams = [Stream(ch, cased) for ch in readings]
    # The same readings with lone list-label lines skipped, tried only when the rule is not proven
    # as printed: rows whose text lost a label line (Hornsby 2026-10-27: 32 of 56 hidden rows).
    # Mixed in with the first, they changed 3 already-proven rows' anchors.
    unlabelled = [Stream(ch, cased, skip_labels=True) for ch in readings]
    note = None
    if min(st.cased_share for st in streams) < 0.9:
        note = f"{r2_path}: only {min(st.cased_share for st in streams):.0%} of lines re-read with casing"
    out = []
    import council_quote_picture as cqp
    import dq_probe_section_code_not_in_source as probe
    import rule_page_locator as rpl
    pdf = str(CACHE / "pdf" / (probe._cache_file(CACHE, r2_path).stem + ".pdf"))
    for r in rows:
        res = judge_twice(r, streams, unlabelled)
        if res["status"] == "unconfirmed" and res["reason"] != "oversized":
            # printed inside a picture: the whole rule, in order, in one picture's OCR text (council_quote_picture.py) --
            # the stored rule was read from that picture by another reader, so two independent readings agree
            pic = cqp.prove(rpl.rule_body(r["provision_text"]), pdf, r["pdf_page"])
            if pic:
                res = {**res, "status": "recovered", "reason": "picture_ocr", **pic}
        res["source_path"] = r2_path
        res["text_md5"] = hashlib.md5((r["provision_text"] or "").encode("utf-8")).hexdigest()
        out.append(res)
    return out, note


def report(res: list[dict]) -> None:
    c = collections.Counter(r["status"] for r in res)
    print(f"rules: {len(res)}")
    for k in ("exact", "recovered", "not_a_control", "unconfirmed"):
        print(f"  {k:14s} {c.get(k, 0):6d}")
        for (s, why), n in sorted(collections.Counter((r["status"], r["reason"]) for r in res
                                                      if r["status"] == k).items(), key=lambda x: -x[1]):
            print(f"      {why:26s} {n:6d}")
    rec = [r for r in res if r["status"] == "recovered"]
    print(f"  recovered with a stored number not in the council's text: "
          f"{sum(1 for r in rec if r.get('missing_numbers'))}")
    print(f"  quote page differs from stored page (exact+recovered): "
          f"{sum(1 for r in res if r.get('quote_page') not in (None, r['stored_page']))}")
    print(f"  oversized (>{OVERSIZED} chars, several controls): {sum(1 for r in res if r['needs_split'])}")
    print("by council (unconfirmed / total):")
    tot = collections.Counter(r["council"] for r in res)
    unc = collections.Counter(r["council"] for r in res if r["status"] == "unconfirmed")
    for k, n in sorted(tot.items(), key=lambda x: -unc[x[0]])[:12]:
        print(f"  {k:22s} {unc[k]:5d} / {n}")
    for r in res:
        if r["id"] in KNOWN:
            print(f"--- known {r['id']} {r['council']}: {r['status']} ({r['reason']}) "
                  f"page {r.get('quote_page')} (stored {r['stored_page']}) overlap {r.get('overlap')} "
                  f"missing {r.get('missing_numbers')} split {r['needs_split']}")
            if r.get("quote"):
                print("    " + r["quote"][:500].replace("\n", "\n    "))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="judge and report; write nothing")
    mode.add_argument("--apply", action="store_true", help="also store each verdict (migration 111)")
    ap.add_argument("--council")
    ap.add_argument("--chapter", help="one chapter_key (needs --council): the publish step runs this per chapter")
    ap.add_argument("--ids", help="comma-separated rule ids")
    ap.add_argument("--unchecked", action="store_true",
                    help="only rules with no verdict, plus unproven rules not re-checked for a week (council_quote_db.UNCHECKED_SQL)")
    ap.add_argument("--out", default=str(Path(os.environ.get("CLAUDE_JOB_DIR", ROOT)) / "tmp" / "council_quote_dryrun.json"))
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    from dotenv import load_dotenv
    load_dotenv(ROOT.parents[2] / ".env" if (ROOT.parents[2] / ".env").exists() else ROOT / ".env")
    ids = [int(x) for x in a.ids.split(",")] if a.ids else None
    if a.chapter is not None and (not a.chapter.strip() or not a.council):
        ap.error("--chapter needs a chapter_key and --council")   # a blank one would widen to the council
    import council_quote_db as store
    rows = store.fetch(a.council, ids, a.chapter, unchecked=a.unchecked)
    if a.unchecked:
        print(f"unchecked rules selected: {len(rows)}")
        if not rows:
            return 0
    by = collections.defaultdict(list)
    for r in rows:
        by[r["r2_current_path"]].append(r)
    res = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for out, note in ex.map(chapter, list(by.items())):
            if note:
                print("NOTE", note)
            res += out
    report(res)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res), encoding="utf-8")
    print(f"written: {a.out}")
    if a.apply:
        n = store.write(res)
        unread = sum(1 for r in res if r["reason"] == "pdf_unreadable")
        print(f"stored: {n} of {len(res)} rules ({unread} not judged: PDF unreadable, left as stored)")
        return 0 if n == len(res) - unread and not unread else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
