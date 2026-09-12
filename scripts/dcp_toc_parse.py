#!/usr/bin/env python3
# prior-art-checked: the shipped contents parser is dcp_extract_changed.parse_toc_entries
# (_TOC_LINE_RE). It is NOT reused here and NOT edited here, deliberately -- see
# "WHY THIS IS NOT parse_toc_entries" below. Other neighbours opened, not guessed
# from their names: ai_extractor.toc_codes_from_pdf is a thin wrapper over that same
# parser (repointed at this module in the same change, because it feeds a GUARD and
# never extraction); dcp_table_of_contents is a static one-off import from 2026-03-21,
# 1,309 rows, no live writer, so it is an input at best and not a parser. DB sweep:
# no table holds a parsed contents list per chapter. Frontend sweep (app/**,
# components/, hooks/): no contents-page parsing anywhere.
"""Read a DCP chapter's contents page, or say honestly that you could not.

WHY THIS EXISTS
---------------
``coverage_gap()`` in scripts/ai_extractor.py has been the completeness check
since 2026-07-01 (#627) and has never been able to fire. Its regex matches 0 of
10 real Waverley contents lines, and with fewer than COVERAGE_MIN_TOC parsed
codes it returns ``(0.0, [])`` -- a clean pass. For two and a half months a check
reported "all present" every single time it failed to read the document.

So the rule this module is built on is the opposite one: **a page that cannot be
read is never a pass.**

WHY THIS IS NOT parse_toc_entries
---------------------------------
``dcp_extract_changed._TOC_LINE_RE`` is not only a diagnostic. For the councils
in ``TOC_DRIVEN_COUNCILS`` (woollahra, leichhardt) it drives EXTRACTION --
parse_toc_entries feeds build_toc_ranges feeds extract_by_page_ranges. Widening
that regex changes what those councils extract.

The standing rule for this repair is "nothing gets re-extracted until its chapter
has a measured state", and the measurement is what this module is for. A parser
that both measures and changes what it measures cannot establish a baseline.
Repointing the extraction path at this parser is Phase C work, done per council
after its chapters are measured -- not here.

WHAT THE DOCUMENTS ACTUALLY LOOK LIKE
-------------------------------------
Sampled 2026-09-12 across the 113 chapters the previous sweep could not read.
Six shapes, and two of them are 73 of the 113 on their own:

  waverley       ``B16 Inter-War Buildings 143``        code, title, page
  leichhardt     ``1.1 Name of the Plan ......... 3``   dot leaders
  ashfield       ``1 Site and Context Analysis``        no page number
  ku_ring_gai    ``14A.1 St Ives Local Centre Context`` TRAILING letter in the code
    (34 chapters) the old regex reads "14", demands a space, finds "A", gives up
  canterbury_bankstown
    (39 chapters) ``Section 1 - Introduction ........`` PREFIX WORD, en dash, and
                  leaders that run off the line with NO page number
  leichhardt     ``G13.1 Relationship to other plans``  and ``4.1. Desired ...``
                                                        (a trailing dot on the code)

And three shapes that are not a parser problem at all, which is why the residue
is reason-coded rather than lumped into one "unreadable" bucket:

  ashfield chapter-b   a real contents page listing titles and page numbers and
                       NO CODES -- a code-vs-code comparison cannot run on it
  covers, maps, scans  no contents page exists; nothing is wrong
  ku_ring_gai part 24  a TWO-COLUMN contents page: one physical line carries half
                       of two entries. Still unread, and still reported as unread.

THE CONFUSABLE NEGATIVE IS THE POINT
------------------------------------
Every loosening above raises the chance body prose reads as a contents page, and
a fabricated contents list produces a fabricated INCOMPLETE -- a worse failure
than the one being fixed, because it looks like a finding.

  ``2.1 Development must maintain significant views to the place of heritage.``

has the same shape as a contents entry. Three defences, all tested in
tests/test_dcp_toc_parse.py:

  1. a contents title is a NOUN PHRASE; a control is a SENTENCE. Sentences end in
     terminal punctuation and run long. Both are rejected.
  2. entries carrying dot leaders or a page number skip test 1 -- those markers
     appear on contents pages and nowhere else.
  3. the page-level density gate, two-tier: a page that announces itself with a
     CONTENTS heading passes on fewer entries; a page that does not must show more.

Run this file directly to execute the same fixtures the test suite uses::

    python scripts/dcp_toc_parse.py
"""
from __future__ import annotations

import re

# ── one entry line ───────────────────────────────────────────────────────────
# Optional prefix word: "Section 1 - ...", "Part 5 ...", "APPENDIX F ...".
PREFIX_WORD = r"(?:(?:Section|Part|Chapter|Appendix|Division|Volume)\s+)?"
# The code. Covers  B16 · 1.1 · 14A.1 · 24D.2 · G13.1 · A10 · 4_1a_2 · 9.48
# Leading letters, digits, OPTIONAL trailing letters, then dotted or underscored
# segments that may themselves carry a trailing letter.
CODE = r"([A-Z]{0,2}\d{1,3}[A-Za-z]{0,2}(?:[._]\d{1,3}[A-Za-z]{0,2})*)"
# A code may be followed by a dot or colon: "4.1. Desired Future Character".
CODE_TAIL = r"[.:]?"
# Separator: whitespace, or a dash in whitespace ("Section 1 - Introduction").
SEP = r"(?:\s+[-‐-―]\s+|\s+)"
# Title, then optional dot leaders, then an optional page number. The page number
# is optional because canterbury_bankstown's leaders run off the end of the line.
TITLE_TAIL = r"([A-Za-z(][^\t]{2,120}?)(?:[\s.·]{2,}(\d{1,4})?)?\s*$"

ENTRY = re.compile("^" + PREFIX_WORD + CODE + CODE_TAIL + SEP + TITLE_TAIL)

# An entry with a page number but NO code: "Active Street Frontages 4".
TITLE_ONLY = re.compile(r"^([A-Z][A-Za-z(][^\t]{3,90}?)\s+(\d{1,4})\s*$")

CONTENTS_HEADING = re.compile(
    r"^\s*(table of contents|contents|general contents|index)\s*$", re.I)

# A line that is only a number or a page label is furniture, not an entry.
FURNITURE = re.compile(r"^(p\s*[\d-]+|page\s*\d+|\d{1,4})\s*$", re.I)

MIN_ENTRIES_HEADED = 3      # a page that says "CONTENTS" needs fewer entries
MIN_ENTRIES_BARE = 5        # a page that does not must show more
MIN_DENSITY_HEADED = 0.25
MIN_DENSITY_BARE = 0.45
MIN_TOTAL = 4               # fewer codes than this across the document -> not read

# Telling a contents entry from a numbered control. Measured against the real
# samples: the longest genuine contents title found was 9 words / 61 chars.
TITLE_MAX_WORDS = 10
TITLE_MAX_CHARS = 75
SENTENCE_END = (".", ":", ";", ",")

# The four statuses. Only READ produces codes that can be compared; the other
# three each mean "this signal did not measure this chapter", kept apart so the
# residue stays legible instead of collapsing into one undifferentiated unknown.
READ = "READ"
TITLES_ONLY = "TITLES_ONLY"
NO_CONTENTS = "NO_CONTENTS"
UNREADABLE = "UNREADABLE"


def entry_strength(title: str, page: int | None, raw_line: str) -> str | None:
    """STRONG (leaders or a page number, unambiguous), WEAK, or None to reject.

    The terminal-punctuation test is applied to the RAW LINE as well as to the
    captured title. Whether a trailing "." lands inside the title group or outside
    it depends on how many characters the optional leader group consumes, which is
    a detail of TITLE_TAIL rather than a fact about the document -- so relying on
    the title alone makes this guard hostage to a future regex tweak. A sentence
    is a sentence either way.
    """
    if page is not None or ".." in raw_line:
        return "STRONG"
    t = title.strip()
    if t.endswith(SENTENCE_END) or raw_line.strip().endswith(SENTENCE_END):
        return None
    if len(t) > TITLE_MAX_CHARS or len(t.split()) > TITLE_MAX_WORDS:
        return None
    return "WEAK"


def page_entries(text: str):
    """-> (coded_entries, titles_with_pages, density, has_contents_heading)."""
    lines = [l.strip() for l in (text or "").split("\n") if len(l.strip()) > 2]
    if not lines:
        return [], [], 0.0, False
    has_heading = any(CONTENTS_HEADING.match(l) for l in lines)
    coded, titled = [], []
    for line in lines:
        if FURNITURE.match(line):
            continue
        m = ENTRY.match(line)
        if m:
            page = int(m.group(3)) if m.group(3) else None
            if entry_strength(m.group(2), page, line):
                coded.append((m.group(1), m.group(2).strip(), page))
            continue
        t = TITLE_ONLY.match(line)
        if t:
            titled.append((t.group(1).strip(), int(t.group(2))))
    density = (len(coded) + len(titled)) / len(lines)
    return coded, titled, density, has_heading


def looks_like_contents(coded, titled, density: float, has_heading: bool) -> bool:
    n = len(coded) + len(titled)
    if has_heading:
        return n >= MIN_ENTRIES_HEADED and density >= MIN_DENSITY_HEADED
    return n >= MIN_ENTRIES_BARE and density >= MIN_DENSITY_BARE


def parse_contents(page_texts: list[str], max_scan: int = 14):
    """-> ``(status, codes, entries)``.

    ``status`` is READ / TITLES_ONLY / NO_CONTENTS / UNREADABLE. UNREADABLE means
    a contents page announced itself and we still could not read it -- the only
    one of the three non-READ statuses that is a defect in THIS file, and the
    only one that should shrink as this parser improves.
    """
    harvested: list[tuple[str, str, int | None]] = []
    harvested_titles: list[tuple[str, int]] = []
    saw_any_text = False
    saw_contents_page = False
    for txt in page_texts[:max_scan]:
        if (txt or "").strip():
            saw_any_text = True
        coded, titled, density, heading = page_entries(txt)
        if heading:
            saw_contents_page = True
        if looks_like_contents(coded, titled, density, heading):
            saw_contents_page = True
            harvested.extend(coded)
            harvested_titles.extend(titled)

    seen: set[str] = set()
    entries: list[tuple[str, str, int | None]] = []
    for code, title, page in harvested:
        if code not in seen:
            seen.add(code)
            entries.append((code, title, page))

    if len(entries) >= MIN_TOTAL:
        return READ, {c for c, _, _ in entries}, entries
    if len(harvested_titles) >= MIN_ENTRIES_HEADED:
        return TITLES_ONLY, set(), [(None, t, p) for t, p in harvested_titles]
    if not saw_any_text:
        return NO_CONTENTS, set(), []
    if saw_contents_page:
        return UNREADABLE, set(), []
    return NO_CONTENTS, set(), []


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tests.fixtures.dcp_toc_samples import CASES

    fails = 0
    for label, txt, expect in CASES:
        status, codes, _entries = parse_contents([txt])
        ok = status == expect
        fails += 0 if ok else 1
        print(("PASS      " if ok else "**FAIL**  ") + label.ljust(48) +
              "-> " + status.ljust(13) + str(len(codes)) + " codes" +
              ("" if ok else "   (expected " + expect + ")"))
    print()
    print("FAILURES: " + str(fails))
    sys.exit(1 if fails else 0)
