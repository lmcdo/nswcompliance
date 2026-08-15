"""A fetch failure must never be recorded as an amendment.

WHY THIS EXISTS
---------------
hornsby's part3-residential chapter sits in the registry with
url_content_length = 1 and check_failures = 0. The monitor downloaded one byte,
called the check SUCCESSFUL, hashed it, and stamped url_last_changed. DQ-70
then reads that chapter as "the source was amended since we extracted", which
makes 32 served provisions look stale when the truth is that the document
cannot be fetched at all.

The two need opposite remedies. An amendment wants re-extraction; a dead URL
wants the URL fixed. Re-extracting on this signal would replace 32 live
controls with nothing.

download_pdf() already refused a non-PDF *Content-Type*, added after "HTML
error pages hashed as changes". A header is not a body, and this response
passed that guard.

No network here: _assert_pdf_body is a pure function over bytes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

r2_monitor = pytest.importorskip(
    "r2_monitor", reason="r2_monitor imports boto3/requests; skip where absent")

_assert_pdf_body = r2_monitor._assert_pdf_body
MIN_PDF_BYTES = r2_monitor.MIN_PDF_BYTES


def _real_pdf(size: int = 5000) -> bytes:
    """A body that looks like a PDF and is comfortably above the floor."""
    return b"%PDF-1.7\n" + b"0" * (size - 9)


# --------------------------------------------------------------------------
# the regression this exists for
# --------------------------------------------------------------------------

def test_one_byte_response_is_rejected():
    """The exact hornsby case: one byte, accepted today, must now raise."""
    with pytest.raises(RuntimeError, match="not a PDF"):
        _assert_pdf_body(b"1", "https://example.invalid/part3.pdf")


def test_empty_response_is_rejected():
    with pytest.raises(RuntimeError, match="not a PDF"):
        _assert_pdf_body(b"", "https://example.invalid/part3.pdf")


def test_html_error_page_is_rejected_even_with_a_pdf_content_type():
    """The header guard cannot see this; the body guard must."""
    with pytest.raises(RuntimeError, match="not a PDF"):
        _assert_pdf_body(b"<!DOCTYPE html><title>404 Not Found</title>" + b"x" * 4000,
                         "https://example.invalid/part3.pdf")


def test_truncated_pdf_is_rejected():
    """Starts correctly and is still useless -- why the length floor exists."""
    with pytest.raises(RuntimeError, match="implausibly small"):
        _assert_pdf_body(b"%PDF-1.7\n" + b"0" * 50,
                         "https://example.invalid/part3.pdf")


# --------------------------------------------------------------------------
# it must not reject real documents
# --------------------------------------------------------------------------

def test_a_real_pdf_passes():
    _assert_pdf_body(_real_pdf(), "https://example.invalid/ok.pdf")


def test_leading_whitespace_is_tolerated():
    """Some servers prepend a newline; that is not a failure."""
    _assert_pdf_body(b"\r\n" + _real_pdf(), "https://example.invalid/ok.pdf")


def test_the_smallest_genuine_chapter_would_pass():
    """277,208 bytes is the smallest real chapter in the registry today.

    Anchors the floor to measured data: if someone later raises MIN_PDF_BYTES
    toward a real document's size, this fails.
    """
    _assert_pdf_body(_real_pdf(277_208), "https://example.invalid/leichhardt.pdf")
    assert MIN_PDF_BYTES < 277_208


def test_floor_is_above_a_bare_header():
    """A file containing only '%PDF-' must not squeak through."""
    assert MIN_PDF_BYTES > len(b"%PDF-1.7\n")


# --------------------------------------------------------------------------
# guard the guard
# --------------------------------------------------------------------------

def test_rejection_is_a_RuntimeError_so_the_monitor_does_not_retry():
    """The loop re-raises RuntimeError rather than retrying.

    Retrying a server that is answering promptly and correctly-shaped would
    just burn the retry budget; the response is not going to change.
    """
    with pytest.raises(RuntimeError):
        _assert_pdf_body(b"1", "https://example.invalid/x.pdf")


def test_message_names_the_url_so_a_failure_is_actionable():
    url = "https://hornsby.example.invalid/part3-residential.pdf"
    with pytest.raises(RuntimeError) as exc:
        _assert_pdf_body(b"1", url)
    assert url in str(exc.value)


# --------------------------------------------------------------------------
# the range-request fallback: report the DOCUMENT's size, not the range's
# --------------------------------------------------------------------------
#
# head_request() falls back to 'GET Range: bytes=0-0' when a server answers
# HEAD with 405. It used to store that response's Content-Length, which is 1 by
# definition - we asked for one byte. That put url_content_length = 1 on a 14 MB
# chapter and made it look like a failed fetch, which in turn made me diagnose a
# working document as unfetchable. The size lives in Content-Range.

# Plain dicts, not requests' CaseInsensitiveDict: conftest_mocks.py stubs
# `requests` so pure-logic tests run without native deps, and the stub has no
# .structures. _range_total only calls .get(), so a dict exercises the parsing
# faithfully. Case-insensitivity is requests' responsibility, not this
# function's - in production it always receives a real CaseInsensitiveDict.
_range_total = r2_monitor._range_total


def test_range_response_reports_the_document_size_not_the_range():
    """The exact regression: 206 with Content-Length 1."""
    headers = {"Content-Length": "1", "Content-Range": "bytes 0-0/14117244"}
    assert _range_total(headers) == "14117244"


def test_server_that_ignores_range_is_unaffected():
    """A plain 200 has no Content-Range; behaviour must be exactly as before."""
    assert _range_total({"Content-Length": "14117244"}) == "14117244"


def test_unparseable_content_range_falls_back_rather_than_raising():
    """'bytes */*' is legal and carries no total. Falling back beats crashing."""
    assert _range_total({"Content-Length": "1", "Content-Range": "bytes */*"}) == "1"


def test_absent_headers_return_none_not_zero():
    """None means 'unknown'. Zero would be a size, and a wrong one."""
    assert _range_total({}) is None
