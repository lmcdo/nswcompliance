"""Prove a rule printed INSIDE A PICTURE by reading the picture (OCR): council_quote.chapter calls this for a rule the
text-layer check left unconfirmed.

prior-art-checked: council_quote proves text against the PDF's text layer only, and words drawn in a picture (a
precinct plan's notes, a setback diagram's dimensions, a table saved as an image) are not in it. The Hornsby pilot
(2026-10-12) found 41 such rules in 60 pages; 72 waiting rules sat on picture pages on 2026-10-13.

Strict, because the site then says the words are the council's: the rule counts as printed when EVERY word of three or
more letters and EVERY number in it is found in the OCR of one page -- its stored page or the page either side -- and
that page holds a picture. One missing word or number and it stays unconfirmed. The quote is the rule's own text, each of
whose words was read in the picture.
"""
from __future__ import annotations

import re

MIN_WORDS = 4          # fewer words than this is too little to prove anything
OCR_DPI = 300
MIN_SCORE = 0.6        # OCR confidence below this is not counted as read
_cache: dict[tuple[str, int], set[str] | None] = {}


def _tokens(s: str) -> list[str]:
    s = (s or "").lower().replace("²", "2").replace("³", "3")
    # numbers apart from their units: "9m" is the number 9 and the unit m, so the number is always checked
    return re.findall(r"\d+(?:\.\d+)?|[a-z]+", s)


def page_words(pdf_path: str, page: int, ocr=None) -> set[str] | None:
    """OCR words of one page when it holds a picture, else None. Cached per (pdf, page). `ocr(png) -> [(box, text,
    score)]` is injectable for tests; by default RapidOCR, and None when it is not installed (the proof is skipped)."""
    key = (pdf_path, page)
    if key in _cache:
        return _cache[key]
    import fitz
    words = None
    with fitz.open(pdf_path) as doc:
        if 1 <= page <= doc.page_count and doc[page - 1].get_images():
            if ocr is None:
                try:
                    from rapidocr_onnxruntime import RapidOCR
                except ImportError:
                    _cache[key] = None
                    return None
                engine = RapidOCR()
                ocr = lambda png: engine(png)[0] or []   # noqa: E731
            png = doc[page - 1].get_pixmap(dpi=OCR_DPI).tobytes("png")
            words = {t for _box, text, score in ocr(png) if float(score) >= MIN_SCORE for t in _tokens(text)}
    _cache[key] = words
    return words


def prove(body: str, pdf_path: str, page: int | None, ocr=None) -> dict | None:
    """{'quote', 'quote_page'} when every word (3+ letters) and number of `body` is read in a picture page, else None."""
    if not page:
        return None
    toks = _tokens(body)
    words = [t for t in toks if len(t) >= 3 and not t.replace(".", "").isdigit()]
    nums = {t for t in toks if t.replace(".", "").isdigit()}
    if len(words) < MIN_WORDS:
        return None
    for p in (page, page - 1, page + 1):
        if p < 1:
            continue
        have = page_words(pdf_path, p, ocr)
        if have and all(w in have for w in words) and nums <= have:
            return {"quote": body.strip(), "quote_page": p}
    return None
