"""Control labels a council printed as pictures, named without reading pixels.

Leichhardt DCP 2013 prints "C1", "C2" ... "O1" beside each control as a tiny  # noqa: zone-codes
image, not text. The text layer holds only a tab where the label sits, so the
citation proof saw no label and refused 146 correct citations in one chapter
(part-c-s1, 2026-09-25) -- C1.6 C9 is printed as C9 on page 20.

How a picture gets its name, deterministically:

* The glyph lives in the image's soft mask; the base image is the same black
  box for every label. So a label is fingerprinted by its MASK pixels.
* Under a printed "Controls" heading the labels run C1, C2, C3 ... in order, and
  under "Objectives" O1, O2 ... A section heading ends the run.
* Every mask must get ONE name across the whole document. If the same picture
  would be C3 in one place and C5 in another, the counting is wrong somewhere
  and the document gets no picture labels at all -- the proof then refuses as
  it did before, which is the safe direction.
* A picture outside a counted run is named from what its mask was called
  inside one; a mask never seen in a run stays unnamed.

PyMuPDF's get_image_rects / get_image_info match images by their base pixels,
so every label on a page reports the same image. Placements are paired with
their own image by draw order instead.

prior-art-checked: reuse not viable because no module in scripts/ services/ src/
enrichment/ reads PDF images or soft masks (grep get_images|smask: only
measure_climate_reference_availability.py, which counts figures); the other
hits are UI form labels and pip's vendored IDNA/encoding label tables.
"""
from __future__ import annotations

import hashlib
import re

#: Printed block headings that start a numbered run, and the run's letter.
RUN_HEADINGS = {"objectives": "o", "controls": "c"}
#: A numbered section heading ("c1.14", "c1.8.16 site access") ends a run.
_SECTION_HEADING = re.compile(r"^[a-z]{0,3}\d+(?:\.\d+)+(?:\s|$)")
#: A label picture: one text line high, in the left margin.
MAX_LABEL_HEIGHT = 16.0
MARGIN_SHARE = 0.2
_DRAW = re.compile(rb"/([A-Za-z0-9_.\-]+)\s+Do(?![A-Za-z])")


def name_labels(events: list[tuple[int, float, str, str]]) -> list[tuple[int, float, str]]:
    """Name label pictures from their order. Pure, so it can be tested.

    `events` are (page, y, kind, value) in reading order: kind "t" is a text
    line (value = its lower-case text), kind "p" a label picture (value = its
    mask fingerprint). Returns (page, y, label) for every picture that can be
    named, or [] when any mask would get two names.
    """
    run, count = None, 0
    names: dict[str, set[str]] = {}
    for _page, _y, kind, value in events:
        if kind == "t":
            text = value.strip()
            if text in RUN_HEADINGS:
                run, count = RUN_HEADINGS[text], 0
            elif _SECTION_HEADING.match(text):
                run, count = None, 0
        elif run:
            count += 1
            names.setdefault(value, set()).add(f"{run}{count}")
    if any(len(v) > 1 for v in names.values()):
        return []
    known = {mask: next(iter(v)) for mask, v in names.items()}
    return [(page, y, known[value]) for page, y, kind, value in events
            if kind == "p" and value in known]


def page_label_pictures(doc, page, mask_cache: dict) -> list[tuple[float, float, str]]:
    """(y, x, mask fingerprint) for each label picture drawn on `page`."""
    masks = {im[7]: im[1] for im in page.get_images(full=True)}
    try:
        drawn = [n.decode() for n in _DRAW.findall(page.read_contents())]
    except Exception:
        return []
    info = page.get_image_info()
    # Images inside form objects are drawn without a page-level Do: the pairing
    # would shift, so such a page contributes no labels rather than wrong ones.
    if len(drawn) != len(info):
        return []
    out = []
    limit = page.rect.width * MARGIN_SHARE
    for name, placed in zip(drawn, info):
        x0, y0, x1, y1 = placed["bbox"]
        smask = masks.get(name)
        if not smask or x1 > limit or (y1 - y0) > MAX_LABEL_HEIGHT:
            continue
        if smask not in mask_cache:
            import fitz
            mask_cache[smask] = hashlib.md5(fitz.Pixmap(doc, smask).samples).hexdigest()
        out.append((y0, x0, mask_cache[smask]))
    return out


#: A label picture's top sits up to ~3.2pt below its text line's (Leichhardt:
#: text 90.8, picture 94.0); the next line is ~13.8pt down. Half a label high.
ROW_TOLERANCE = 6.0


def merge_labels(raw: list, pictures: list[tuple], make_line) -> list:
    """Put each named label picture into the reading as a line of its own,
    just before the text it sits beside (the line on its row, else the first
    line below it). Native order is not top-to-bottom -- Leichhardt draws the
    footer first -- so the position is found per page, not by a running y.
    `make_line(page, y, x, text)` builds a line of the caller's type."""
    if not pictures:
        return raw
    events = sorted([(ln.page, ln.y, "t", ln.text) for ln in raw]
                    + [(p, y, "p", m) for p, y, _x, m in pictures], key=lambda e: (e[0], e[1]))
    x_of = {(p, y): x for p, y, x, _m in pictures}
    before: dict[int, list] = {}      # raw index -> labels to put ahead of it
    after: dict[int, list] = {}       # ... or after it, below a page's last line
    for p, y, label in name_labels(events):
        on_page = [i for i, ln in enumerate(raw) if ln.page == p]
        row = [i for i in on_page if abs(raw[i].y - y) <= ROW_TOLERANCE]
        below = [i for i in on_page if raw[i].y > y]
        at = (min(row, key=lambda i: abs(raw[i].y - y)) if row
              else min(below, key=lambda i: raw[i].y) if below else None)
        # On a row, take the row's y: a picture's top sits a few points below
        # the text's, and top-to-bottom order would put the label after the
        # line it labels -- making the PREVIOUS label look like this rule's.
        line = make_line(p, raw[at].y if row else y, x_of[(p, y)], label)
        if at is not None:
            before.setdefault(at, []).append(line)
        elif on_page:
            after.setdefault(max(on_page), []).append(line)
    out = []
    for i, ln in enumerate(raw):
        out += before.get(i, [])
        out.append(ln)
        out += after.get(i, [])
    return out
