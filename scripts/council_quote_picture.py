"""Prove a rule printed INSIDE A PICTURE by reading the picture (OCR): council_quote.chapter calls this for a rule the
text-layer check left unconfirmed.

prior-art-checked: council_quote proves text against the PDF's text layer only, and words drawn in a picture (a
precinct plan's notes, a setback diagram's dimensions, a table saved as an image) are not in it. The Hornsby pilot
(2026-10-12) found 41 such rules in 60 pages; 72 waiting rules sat on picture pages on 2026-10-13.

Strict, because the site then says the words are the council's (cross-review 2026-10-14):
  - only the PICTURES are read, each on its own -- never the page's ordinary text beside a logo;
  - the whole rule must appear IN ORDER as one unbroken stretch of one picture's text: every word (short ones too --
    "no", "not", "if", "or") and every number and symbol (< > <= >= % + - and the like), spacing and case ignored.
  - OCR often DROPS the spaces in a picture's text ("Onpropertiesthatadjointherailway", Hornsby 2026-10-28: 32 of 67
    unproven picture rules). A dropped space is allowed; an ADDED one is not: every space the OCR read inside the
    matched stretch must fall on one of the rule's own word boundaries, so "no tin" still never proves "not in".
Anything less leaves the rule unconfirmed. The quote is the rule's own text, which the picture prints word for word.
"""
from __future__ import annotations

import re

MIN_WORDS = 4          # fewer words than this is too little to prove anything
OCR_DPI = 300
MIN_SCORE = 0.6        # OCR lines read below this confidence are not used
MIN_PICTURE_PT = 40    # a picture smaller than this (points, either side) is an icon or logo: not read
_cache: dict[tuple[str, int], list[str] | None] = {}
_SYMBOLS = str.maketrans({"≤": "<=", "≥": ">=", "–": "-", "—": "-", "²": "2", "³": "3"})


def norm(s: str) -> str:
    """Words, numbers and the symbols that change a rule's meaning, in order, one space apart, case dropped. Word
    boundaries are kept, so "not in" never matches "no tin"."""
    toks = re.findall(r"[a-z]+|\d+(?:\.\d+)?|[<>=%+\-/]", (s or "").translate(_SYMBOLS).lower())
    return " " + " ".join(toks) + " "


def picture_texts(pdf_path: str, page: int, ocr=None) -> list[str] | None:
    """The OCR text of each picture on a page, one string per picture (lines in reading order), or None when the page
    has no picture worth reading. Cached per (pdf, page). `ocr(png) -> [(box, text, score)]` is injectable for tests;
    by default RapidOCR, and None when it is not installed (the proof is then skipped)."""
    key = (pdf_path, page)
    if key in _cache:
        return _cache[key]
    import fitz
    texts = None
    with fitz.open(pdf_path) as doc:
        if 1 <= page <= doc.page_count:
            pg = doc[page - 1]
            rects = [r for info in pg.get_image_info() for r in [fitz.Rect(info["bbox"])]
                     if r.width >= MIN_PICTURE_PT and r.height >= MIN_PICTURE_PT]
            if rects:
                if ocr is None:
                    try:
                        from rapidocr_onnxruntime import RapidOCR
                    except ImportError:
                        _cache[key] = None
                        return None
                    engine = RapidOCR()
                    ocr = lambda png: engine(png)[0] or []   # noqa: E731
                texts = []
                for r in rects:
                    png = pg.get_pixmap(dpi=OCR_DPI, clip=r).tobytes("png")
                    lines = [(box, text) for box, text, score in ocr(png) if float(score) >= MIN_SCORE]
                    # reading order: top to bottom, then left to right (box is four corner points, or None in tests)
                    lines.sort(key=lambda bt: (round(bt[0][0][1] / 10), bt[0][0][0]) if bt[0] else 0)
                    texts.append(" ".join(t for _b, t in lines))
    _cache[key] = texts
    return texts


def _glued_match(rule: str, text: str) -> bool:
    """The rule's tokens appear in order in `text` with OCR spaces possibly missing, but no OCR space falls inside one
    of the rule's tokens."""
    rt, tt = rule.split(), text.split()
    if not rt:
        return False
    target = "".join(rt)
    rule_cuts, n = set(), 0
    for t in rt[:-1]:
        n += len(t)
        rule_cuts.add(n)
    glued, text_cuts = "", []
    for t in tt:
        glued += t
        text_cuts.append(len(glued))
    start = glued.find(target)
    while start != -1:
        end = start + len(target)
        if all(c - start in rule_cuts for c in text_cuts if start < c < end):
            # the stretch must also begin and end on OCR token edges: no rule word cut out of a longer OCR word
            if (start == 0 or start in text_cuts) and end in text_cuts:
                return True
        start = glued.find(target, start + 1)
    return False


def prove(body: str, pdf_path: str, page: int | None, ocr=None) -> dict | None:
    """{'quote', 'quote_page'} when the whole rule is printed, in order, inside one picture on its page or the page
    either side; else None."""
    if not page:
        return None
    if len(re.findall(r"[A-Za-z]+", body or "")) < MIN_WORDS:
        return None
    q = norm(body)
    for p in (page, page - 1, page + 1):
        if p < 1:
            continue
        for text in picture_texts(pdf_path, p, ocr) or []:
            if q.strip() and (q in norm(text) or _glued_match(q, norm(text))):
                return {"quote": body.strip(), "quote_page": p}
    return None
