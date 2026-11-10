"""add_new_chapter.py --from-file takes a hand-downloaded PDF for a council that blocks us (DQ-153)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

# The script reads its settings from the environment when imported; give it throwaway values
# so this test never needs, or touches, real credentials.
import os  # noqa: E402

for _k in ("R2_ACCOUNT_ID", "R2_BUCKET_NAME", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"):
    os.environ.setdefault(_k, "test-not-real")
os.environ.setdefault("DATABASE_URL", "postgresql://test-not-real")
import add_new_chapter  # noqa: E402


def test_reads_a_real_pdf_and_returns_no_http_headers(tmp_path):
    f = tmp_path / "d16.pdf"
    f.write_bytes(b"%PDF-1.7\nbody")
    data, headers = add_new_chapter.read_local_pdf(f)
    assert data == b"%PDF-1.7\nbody"
    assert headers == {}  # same shape as download_pdf; .get("ETag") is safe


def test_refuses_a_file_that_is_not_a_pdf(tmp_path):
    f = tmp_path / "page.pdf"
    f.write_bytes(b"<html>Access Denied</html>")  # what a blocked download often saves
    with pytest.raises(RuntimeError, match="Not a PDF"):
        add_new_chapter.read_local_pdf(f)


def test_refuses_a_missing_file(tmp_path):
    with pytest.raises(RuntimeError, match="File not found"):
        add_new_chapter.read_local_pdf(tmp_path / "nope.pdf")


def test_from_file_option_exists_and_skips_the_http_calls():
    src = (Path(add_new_chapter.__file__)).read_text(encoding="utf-8")
    assert '"--from-file"' in src
    # the only HTTP calls sit in the else branches
    assert "if args.from_file:" in src and src.count("if args.from_file:") == 2
