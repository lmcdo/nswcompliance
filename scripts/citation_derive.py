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
