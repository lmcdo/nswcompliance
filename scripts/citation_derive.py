"""Read the citation a council printed above a rule, and accept it only if it PROVES.

prior-art-checked: the proof is scripts/citation_proof.py and is reused, not
copied -- every citation derived here must pass prove_citation_any before it is
offered. scripts/dcp_section_code.py recovers a code from ref_number (the
opposite direction: from our data, not from the page) and
dcp_commit_approved._section_header_from_text reads the code off the stored
text; neither reads the source page.

WHY
---
DQ-111 found 5,167 served rules whose clause number is not proven on the
council's page. Re-reading a whole chapter with the model to fix a handful of
numbers is waste; the page already says what the number is. Measured
2026-09-24: 1,749 rules can be corrected this way, deterministically.

WHAT IT WILL NOT DO
-------------------
* Offer a citation that does not prove on the page.
* Choose between two places. If the rule's wording sits under more than one
  section, or more than one label proves, it returns nothing -- a re-read or a
  person decides. (728 + 93 rules on 2026-09-24.)
* Trade a label away. If the stored citation had an item label, a derived one
  without a label is refused, because it is coarser than what is printed.
* Use an item label as a section. A chapter's label letters (O, C, R...) are
  measured from the chapter itself, never listed.
* Emit a council's own non-letter labels ("7.", "b)") -- the proof cannot yet
  verify those, so those rules wait (477 on 2026-09-24).
"""
from __future__ import annotations

import collections
import re

import citation_proof as cp

#: The rule's own label at the start of its first line: a lettered code (c3,
#: o1, r2, pc1) or a council-style label ("7.", "b)", "(iii)").
_LABEL = re.compile(r"^(?:([a-z]{1,3}\d{1,3}[a-z]?)\b|\(?([a-z]|[ivx]{1,4}|\d{1,2})[.)]\s)")
_LETTERED = re.compile(r"^[a-z]{1,3}\d")


def label_families(ch: cp.ChapterLines, min_uses: int = 5) -> set[str]:
    """Letter families this chapter uses as ITEM labels: lettered, undotted codes
    at a line start, used at least `min_uses` times. Measured, never listed."""
    c = collections.Counter()
    for ln in ch.lines:
        m = cp.CODE_AT_START.match(ln.text)
        if m and "." not in m.group(1):
            fam = re.match(r"[a-z]*", m.group(1)).group(0)
            if fam:
                c[fam] += 1
    return {f for f, n in c.items() if n >= min_uses}


def _candidates(ch: cp.ChapterLines, text: str, hint, families: set[str]):
    """(section, label) read off the page above each place the rule's wording sits."""
    out = []
    L = ch.lines
    for _end, start in cp._anchors(ch, text, hint):
        label, from_line = None, start
        for i in range(start, max(-1, start - 3), -1):
            m = _LABEL.match(L[i].text)
            if m:
                label, from_line = (m.group(1) or m.group(2)), i
                break
        section = None
        # A rule with no label of its own must start right under its heading.
        # One that starts mid-section has spilled over from the rule before it
        # (Woollahra B1.1.5's stored text opens with B1.1.4's last lines), so the
        # heading above its start is the WRONG rule's heading.
        reach = 400 if label else 3
        for i in range(from_line - 1, max(-1, from_line - reach - 1), -1):
            ln = L[i]
            if ln.page in ch.toc_pages or not cp._heading_like(ln, ch.page_width):
                continue
            k = cp._KEYWORD_HEAD.match(ln.text)
            if k:
                section = k.group(1)
                break
            m = cp.CODE_AT_START.match(ln.text)
            if not m:
                continue
            code = m.group(1)
            fam = re.match(r"[a-z]*", code).group(0)
            if fam in families and "." not in code:
                continue                      # an item label (O2, C11), never a section
            if "." in code or fam:
                section = code
                break
        if section:
            out.append((section, label))
    return out


def places(ch: cp.ChapterLines, text: str, hint) -> list[int]:
    """The lines where the rule's wording starts, starts within a few lines merged
    (a line the PDF draws twice, or a start the reader shifted, is one place)."""
    out: list[int] = []
    for s in sorted({start for _end, start in cp._anchors(ch, text, hint)}):
        if not out or s - out[-1] > 8 or ch.lines[s].page != ch.lines[out[-1]].page:
            out.append(s)
    return out


def printed_section(ref_number: str | None, readings) -> str | None:
    """The stored citation's own section (lower case), if a line of the chapter
    outside its contents pages opens with it; else None."""
    sections = cp.split_ref(ref_number)[0]
    if not sections:
        return None
    leaf = cp.render(sections[-1]).lower()
    for ch in readings:
        for i in ch.heads_at.get(leaf, []) + ch.keyword_heads.get(leaf, []):
            if ch.lines[i].page not in ch.toc_pages:
                return leaf
    return None


def stored_label_beside(ref_number: str | None, text: str, readings, hint) -> str | None:
    """The stored item label (lower case) if it is printed within three lines above
    where the rule's wording starts, in either reading; else None."""
    item = cp.split_ref(ref_number)[1]
    if not item:
        return None
    want = cp.render(item).lower()
    for ch in readings:
        for _end, start in cp._anchors(ch, text, hint):
            for i in range(start, max(-1, start - 4), -1):
                m = _LABEL.match(ch.lines[i].text)
                if m and (m.group(1) or m.group(2)) == want:
                    return want
    return None


def page_agrees(ref_number: str, text: str, readings, hint=None) -> bool:
    """A second, simpler reading of the page, independent of the proof: the label
    is printed within three lines above where the rule's words start, and the
    section is the nearest numbered heading above them. A fix is written only
    when this AND the proof agree (whole-fixer test, 2026-09-25)."""
    sections, item, _ = cp.split_ref(ref_number)
    if not sections:
        return False
    want = cp.render(sections[-1]).lower()
    lab = cp.render(item).lower() if item else None
    # A bare item label ("C12") is not a citation: its own line opens with it, so
    # it is its own "nearest heading" (the cheap reader drops the section this way).
    families = label_families(readings[0])
    if "." not in want and re.match(r"[a-z]*", want).group(0) in families:
        return False
    for ch in readings:
        for _end, s in cp._anchors(ch, text, hint):
            if lab and not any((m := _LABEL.match(ch.lines[i].text)) and (m.group(1) or m.group(2)) == lab
                               for i in range(s, max(-1, s - 4), -1)):
                continue
            for i in range(s - 1, max(-1, s - 600), -1):
                ln = ch.lines[i]
                if ln.page in ch.toc_pages or not cp._heading_like(ln, ch.page_width):
                    continue
                m = cp.CODE_AT_START.match(ln.text) or cp._KEYWORD_HEAD.match(ln.text)
                if m and ("." in m.group(1) or m.group(1) == want):
                    if m.group(1) == want:
                        return True
                    break
    return False


def leading(code: str | None) -> str:
    """The part of a code that names its chapter: "B3" of "B3.7.2", "9" of "9.2.5.1"."""
    m = re.match(r"([a-z]*\d+)", (code or "").lower())
    return m.group(1) if m else ""


def chapter_leading(proven_codes) -> str | None:
    """The leading part most of a chapter's PROVEN citations share, or None when
    no single one holds at least 60% -- measured from the chapter, never listed."""
    c = collections.Counter(leading(x) for x in proven_codes if leading(x))
    if not c:
        return None
    top, n = c.most_common(1)[0]
    return top if n >= 0.6 * sum(c.values()) else None


def printed_code(section: str, label: str | None) -> str:
    """How the council prints it, in the store's shape: upper-case letters, dots."""
    code = section.upper() if re.match(r"[a-z]", section) else section
    if label and _LETTERED.match(label):
        code += " " + label.upper()
    return code


def derive_citation(ref_number: str | None, text: str | None, readings, page_hint=None,
                    chapter_lead: str | None = None) -> dict:
    """-> {"status": derived | ambiguous | not_derivable | deferred, "code": str|None, "why": str}.

    `readings` are both line orders (citation_proof.both_orders). "deferred" is a
    citation the page supports but the proof cannot yet verify (a "7." label).
    """
    had_item = cp.split_ref(ref_number)[1] is not None
    # Wording printed in two places (a rule and its summary-table copy, Warringah
    # p119/p164) can only be placed by a person or a re-read: the copy with a
    # label is not the rule's own place just because the other copy has none.
    if any(len(places(ch, text or "", page_hint)) > 1 for ch in readings):
        return {"status": "ambiguous", "code": None,
                "why": "the wording is printed in more than one place"}
    families = getattr(readings[0], "_label_families", None)
    if families is None:                      # once per chapter, not per rule
        families = label_families(readings[0])
        readings[0]._label_families = families
    found = {}
    deferred = False
    for ch in readings:
        for section, label in _candidates(ch, text or "", page_hint, families):
            lab = label or ""
            if had_item != bool(lab):
                # Keep the citation's shape. Without a label it would be coarser;
                # with one the stored row never had, the text almost always opens
                # with the PREVIOUS section's last control (Woollahra C1.3.9 ->
                # "C1.3.8 C22"): the row spilled over, and a re-read fixes it.
                continue
            if lab and not _LETTERED.match(lab):
                deferred = True               # council's own "7." / "b)": proof cannot check it yet
                continue
            if chapter_lead and leading(section) != chapter_lead:
                continue                      # a fix never leaves the rule's own chapter (B3.7 -> E1)  # noqa: zone-codes -- DCP section keys, not zones
            found.setdefault(printed_code(section, lab), (section, lab))
    # The stored section, when the council prints it as a heading, stands: the fix
    # may change the label or move to a sub-section, never to another section.
    # Every wrong section the whole-fixer test found (2026-09-25) replaced a
    # printed stored section with a zone name ("B2 - Local Centre"), a
    # cross-reference ("section 3.3 for ...") or a sibling table code ("A2").
    kept = printed_section(ref_number, readings)
    if kept:
        found = {code: v for code, v in found.items()
                 if v[0] == kept or v[0].startswith(kept + ".")}
    # The stored label, when it is printed beside the rule, stands too: a column
    # printed alongside puts a second label next to the words (Canterbury-
    # Bankstown 2.2.5 "p4." beside "p1.", 2026-09-25).
    own = stored_label_beside(ref_number, text or "", readings, page_hint)
    if own:
        found = {code: v for code, v in found.items() if (v[1] or "").lower() == own}
    proven = {code: v for code, v in found.items()
              if cp.prove_citation_any(f"x__{code.replace('.', '_')}", text, readings,
                                       page_hint)["status"] == "proven"}
    if len(proven) > 1:
        why = ("the wording is printed under more than one section"
               if len({v[0] for v in proven.values()}) > 1 else "more than one label proves")
        return {"status": "ambiguous", "code": None, "why": why}
    if proven:
        return {"status": "derived", "code": next(iter(proven)), "why": "printed above the rule"}
    if deferred:
        return {"status": "deferred", "code": None,
                "why": "printed under the council's own label style, which the proof cannot yet check"}
    return {"status": "not_derivable", "code": None, "why": "no proven heading above the rule"}
