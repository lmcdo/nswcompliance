"""DQ-79: a server's reported size below MIN_PDF_BYTES is not the document's size.

Real rows (dcp_chapter_registry, read 2026-10-23):
  766 ku_ring_gai/section-b-part-14e-lindfield-local-centre: url_content_length = 1 after force run 3
      recorded unchanged_hash -- the download passed _assert_pdf_body, so the 1 came from HEAD.
  257 ku_ring_gai/section-a-part-8-mixed-use: url_content_length = 1 on 2026-09-01; a live
      head_request that day read 11,022,088 bytes.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

# r2_monitor reads these at import; nothing here touches R2 or the database.
for _k in ("R2_ACCOUNT_ID", "R2_BUCKET_NAME", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "DATABASE_URL"):
    os.environ.setdefault(_k, "unused-in-this-test")

import r2_monitor as m  # noqa: E402


def test_ku_ring_gai_one_byte_is_unknown():
    # Known-wrong case: the value stored on rows 766 and 257.
    assert m.plausible_size("1") is None
    assert m.plausible_size(1) is None


def test_real_size_is_kept():
    assert m.plausible_size("11022088") == 11022088


@pytest.mark.parametrize("v, want", [("999", None), ("1000", 1000), (str(m.MIN_PDF_BYTES), m.MIN_PDF_BYTES)])
def test_floor_is_min_pdf_bytes(v, want):
    assert m.plausible_size(v) == want


@pytest.mark.parametrize("v", [None, "", "abc", "0", "-5"])
def test_missing_or_garbage_is_unknown(v):
    assert m.plausible_size(v) is None


def test_both_writers_use_it():
    # Each place that turns a server's size into url_content_length must go through plausible_size.
    src = (ROOT / "scripts" / "r2_monitor.py").read_text(encoding="utf-8")
    assert 'remote_len = plausible_size(head.get("content_length"))' in src
    assert 'remote_len = plausible_size(resp_headers.get("Content-Length"))' in src
    assert not re.search(r"remote_len = int\(", src)
    assert "new_len = int(" not in src
    assert src.count("new_len = remote_len if remote_len else len(content)") == 2
