"""Every page pdfplumber parses must be released once we are done with it.

WHY. The nightly extraction batch was OOM-killed (exit -9) three runs running.
The registered diagnosis blamed one 139MB chapter and proposed splitting large
PDFs into chunks. Measured, that was not the mechanism. pdfplumber caches each
page's parsed objects for the lifetime of the PDF object and nothing dropped
them, so memory climbed across the WHOLE batch, not just on the big file:

    three chapters, one process, before   peak 1,361 MB, 628 MB still resident
    three chapters, one process, after    peak   443 MB, 134 MB still resident

and on the 139MB chapter alone, 1,358 MB -> 440 MB with byte-identical output
(65 sections, same sha256 over sections and over tables).

The fix is chosen precisely because it cannot change a result: releasing a
cache discards only what pdfplumber rebuilds from the same bytes. A chunked
split has to decide where to cut, and a clause straddling that cut is a real
correctness risk -- the same shape of bug this pipeline has already shipped
one level down, in the fidelity checker.

These tests assert the release actually happens on every page, which is the
part that silently stops being true when someone adds a page loop.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

pdfplumber = pytest.importorskip("pdfplumber")


def _extractor_module():
    import scripts.dcp_extract_changed as m
    return m


class _Bare:
    """A page object with neither cache API. Must not raise."""


class _Spy:
    def __init__(self):
        self.flushed = 0
        self.textmap_cleared = 0

        class _TM:
            def cache_clear(inner):  # noqa: N805 - mimics functools.lru_cache
                self.textmap_cleared += 1

        self.get_textmap = _TM()

    def flush_cache(self):
        self.flushed += 1


class _Exploding:
    def flush_cache(self):
        raise RuntimeError("pdfplumber internals changed")

    class get_textmap:  # noqa: N801
        @staticmethod
        def cache_clear():
            raise RuntimeError("also gone")


def test_release_calls_both_caches():
    """Both, not one. Measured separately on the real 139MB chapter:
    flush_cache alone 626 MB, textmap alone 1,325 MB, both 426 MB, against
    1,356 MB with neither. Dropping either call gives most of the memory back.
    """
    m = _extractor_module()
    spy = _Spy()
    m._release_page(spy)
    assert spy.flushed == 1
    assert spy.textmap_cleared == 1


def test_release_is_best_effort_on_a_page_without_the_api():
    """A pdfplumber upgrade that renames a cache must not break extraction.

    The fallback for a failed release is using more memory, which is strictly
    better than an extraction that raises. This is the confusable negative: a
    release helper that propagates is worse than no release helper.
    """
    m = _extractor_module()
    m._release_page(_Bare())        # no attributes at all
    m._release_page(_Exploding())   # attributes that raise


def test_every_page_that_is_READ_is_also_released(tmp_path):
    """The property that matters, stated so it can actually fail.

    The first version of this counted calls to the release helper and asserted
    the count was at least the page count. It passed with the release deleted
    from the main extraction loop -- two code paths touch each page here, so
    one release per page survived and the >= held. A test that survives the
    deletion of the thing it tests is worse than no test, so it was found by
    deleting that line and re-running, not by reading it.

    What is asserted instead is the invariant itself: any page pdfplumber
    parsed text out of must have had its cache dropped. That is refactor-proof
    -- move the loops, merge them, add one -- and it fails the moment a page is
    read and left holding its objects, which is the actual defect.
    """
    pytest.importorskip("reportlab")
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    pdf_path = tmp_path / "sample.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    for n in range(1, 6):
        c.drawString(72, 720, f"1.{n} Heading {n}")
        c.drawString(72, 700, f"Controls C1. Body text for page {n}.")
        c.showPage()
    c.save()

    from pdfplumber.page import Page

    read: set[int] = set()
    flushed: set[int] = set()
    real_text, real_flush = Page.extract_text, Page.flush_cache

    def spy_text(self, *a, **kw):
        read.add(id(self))
        return real_text(self, *a, **kw)

    def spy_flush(self, *a, **kw):
        flushed.add(id(self))
        return real_flush(self, *a, **kw)

    m = _extractor_module()
    Page.extract_text, Page.flush_cache = spy_text, spy_flush
    try:
        sections = m.DCPExtractor(str(pdf_path), "ashfield").extract()
    finally:
        Page.extract_text, Page.flush_cache = real_text, real_flush

    assert sections, "extraction returned nothing, so the assertion proves nothing"
    assert read, "no page was read, so the assertion proves nothing"
    leaked = read - flushed
    assert not leaked, (
        f"{len(leaked)} of {len(read)} pages were read and never released -- "
        f"a page loop is holding its parsed objects for the life of the document"
    )


def test_extraction_still_returns_the_same_shape(tmp_path):
    """Releasing a cache must not change what comes out.

    A shape check here, not an equality check: the byte-for-byte proof needs
    real council PDFs and was run against three of them (canterbury_bankstown
    chapter-7-6, woollahra chapter-d5, ashfield chapter-a), identical sha256
    over both sections and tables in every case. This guards the contract in
    CI, where those files are not available.
    """
    reportlab = pytest.importorskip("reportlab")
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    pdf_path = tmp_path / "shape.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    c.drawString(72, 720, "1.1 Building Height")
    c.drawString(72, 700, "Controls C1. Maximum height is 8.5 metres.")
    c.showPage()
    c.save()

    m = _extractor_module()
    sections = m.DCPExtractor(str(pdf_path), "ashfield").extract()
    assert isinstance(sections, list) and sections
    for s in sections:
        assert "content" in s and "section_number" in s
        assert isinstance(s.get("tables", []), list)
