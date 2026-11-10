"""add_new_chapter.py --from-file takes a hand-downloaded PDF for a council that blocks us (DQ-153)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

# The script reads its settings from the environment when imported; give it throwaway values
# so this test never needs, or touches, real credentials.
import os  # noqa: E402

_FAKE = {"R2_ACCOUNT_ID": "test-not-real", "R2_BUCKET_NAME": "test-not-real", "R2_ACCESS_KEY_ID": "test-not-real",
         "R2_SECRET_ACCESS_KEY": "test-not-real", "DATABASE_URL": "postgresql://test-not-real"}
_set_here = [k for k in _FAKE if k not in os.environ]
for _k in _set_here:
    os.environ[_k] = _FAKE[_k]
import add_new_chapter  # noqa: E402

for _k in _set_here:  # never leave a fake value behind for other tests (the real-database test reads these)
    os.environ.pop(_k, None)


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


# ---- the real database (opt-in: PYTEST_REAL_DB=1 DATABASE_URL=... pytest -m database) ----
import subprocess  # noqa: E402

_real_db = pytest.mark.skipif(os.getenv("PYTEST_REAL_DB") != "1", reason="set PYTEST_REAL_DB=1 to run against the real database")


@pytest.mark.database
@_real_db
def test_dry_run_with_a_file_reads_the_real_registry_and_writes_nothing(tmp_path):
    """Run the real script, dry run, against the live registry: it must use the file (no HTTP), find the key
    free, print the INSERT it would do, and leave the registry unchanged."""
    import dq_db

    key = "zz-dq153-test-not-real"
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.7\nhand downloaded")

    def count() -> int:
        conn = dq_db.connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM dcp_chapter_registry WHERE chapter_key = %s", (key,))
            return cur.fetchone()[0]
        finally:
            conn.close()

    assert count() == 0
    root = Path(add_new_chapter.__file__).resolve().parents[1]
    out = subprocess.run(
        [sys.executable, str(root / "scripts" / "add_new_chapter.py"), "--dry-run",
         "--council", "waverley", "--key", key, "--label", "DQ-153 test, not real",
         "--url", "https://example.invalid/blocked.pdf", "--from-file", str(pdf)],
        capture_output=True, text=True, cwd=root, env=os.environ.copy(), timeout=120,
    )
    assert out.returncode == 0, out.stdout + out.stderr
    assert "Skipping URL check" in out.stdout
    assert "Reading the PDF you downloaded" in out.stdout
    assert "Downloading PDF" not in out.stdout
    assert "[dry-run] would INSERT" in out.stdout
    assert count() == 0
