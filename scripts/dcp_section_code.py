#!/usr/bin/env python3
# prior-art-checked: no existing helper recovers a section code from ref_number.
# Neighbours opened, not guessed from their names:
#   dcp_commit_approved._section_header_from_text  reads the code off the FIRST LINE
#       of the reviewed provision text. When that line carries no code, it returns a
#       codeless header -- which is the defect. This module is what it falls back to,
#       so the two share one definition instead of drifting apart.
#   dcp_chapter_measure.leading_code               reads a code already PRESENT on a
#       header. Opposite direction: that asks "is there a code", this asks "what
#       should the code have been". Kept separate deliberately; merging them would
#       make the measurement depend on the repair and stop it being able to fail.
#   derive_precinct_keys.py                        recovers a different key from
#       different source text.
"""Recover a provision's section code from its ref_number.

WHY THIS EXISTS
---------------
Measured 2026-09-12 across the 12,124 live DCP rows: 3,501 carry a section_header
with no section code in it at all -- "Residential parking generation rates",
"Local Character and Streetscape", "LEGISLATIVE BACKGROUND". A provision with no
code cannot be looked up by section, which is how the product is asked for it.

The code was never lost. It is sitting in ref_number:

    section_header  "Residential parking generation rates"   ref  E1_4_2
    section_header  "Local Character and Streetscape"        ref  4a_1
    section_header  "LEGISLATIVE BACKGROUND"                 ref  1_1

2,330 of those rows can be repaired from stored data with no model call, restoring
2,260 distinct addressable sections. (An earlier claim that ref_number "holds only
the document id" came from truncating output at 26 characters.)

WHAT IT WILL NOT DO
-------------------
Return a code it cannot read off the row. 291 rows are legitimately not a numbered
section (preamble, intro, cover) and 880 carry no code in ref_number either
(ashfield 747). Both get None. Inventing a section number would fabricate a
regulatory reference, which is a worse failure than an unaddressable row -- see
.claude/rules/regulatory-data.md.

This does NOT address collapsed attribution (4,445 rows, marrickville's dominant
defect). There, ref_number carries the SAME collapsed parent code the header does
(2_25_C11 for a row that belongs to 2.25.3.4), so there is nothing to recover and
only a re-extraction fixes it.
"""
from __future__ import annotations

import re

# A section code already at the head of a label. If this matches, hands off.
HAS_CODE = re.compile(r"^[A-Z]{0,2}\d{1,3}[A-Za-z]{0,2}(?:[._]\d{1,3}[A-Za-z]{0,2})*(\s|$)")
# A ref_number tail that IS a section code: E1_4_2, 4a_1, 1_1, 24c_5, A10.
REF_CODE = re.compile(r"^([A-Za-z]{0,3}\d{1,3}[a-z]?(?:_\d{1,3}[a-z]?)*)$")
# Tails that are legitimately not a numbered section.
NON_SECTION = re.compile(
    r"^(preamble|intro|introduction|cover|toc|contents|document)", re.I)


def ref_tail(ref_number: str | None, document_id: str | None) -> str:
    """The part of ref_number after the document id -- where the code lives."""
    if not ref_number:
        return ""
    tail = str(ref_number)
    if document_id and tail.startswith(str(document_id)):
        tail = tail[len(str(document_id)):].lstrip("_")
    return tail.split("__")[0].strip()


def section_code(ref_number: str | None, document_id: str | None) -> str | None:
    """The section code this row should carry, or None when it cannot be known."""
    seg = ref_tail(ref_number, document_id)
    if not seg or NON_SECTION.match(seg):
        return None
    m = REF_CODE.match(seg)
    if not m:
        return None
    code = m.group(1).replace("_", ".")
    # A code with NO structure -- bare digits, no letter and no dotted part -- is
    # refused outright. Measured 2026-09-12: 69 of 2,328 candidate repairs land
    # here, and every sampled one is a fragment of body text rather than a
    # heading:
    #     "December 2025 31 December 2026"                 -> 31
    #     "June. Where existing development currently r..." -> 21
    #     "STC (Sound Transmission Class) in accordance"    -> 45
    # Stamping those would fabricate a reference to a clause that does not
    # exist, which .claude/rules/regulatory-data.md forbids outright and which is
    # a worse outcome than the unaddressable row it replaces. Losing 3% of the
    # repairs is the cheap side of that trade.
    if code.isdigit():
        return None
    return code


def repaired_header(section_header: str | None, ref_number: str | None,
                    document_id: str | None) -> str | None:
    """The section_header this row should carry, or None to leave it alone.

    None means "no change": either the header already carries a code, or no code
    can be recovered. This only ever ADDS a code where there is none -- it never
    rewrites one that exists, because a stored code came from the document and a
    recovered one is an inference.
    """
    head = (section_header or "").strip()
    if head and HAS_CODE.match(head):
        return None
    code = section_code(ref_number, document_id)
    if code is None:
        return None
    return code + " " + head if head else code
