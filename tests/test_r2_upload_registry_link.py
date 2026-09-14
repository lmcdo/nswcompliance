"""An upload moves a chapter's public PDF link together with its current copy.

prior-art-checked: tests for scripts/r2_upload_pdfs.upsert_registry; no existing test covers that
function (tests/test_reexport_advances_extraction_hash.py pins r2_monitor.py's own UPDATE, which already
writes both columns together).

On 2026-09-14, 15 active chapters' r2_public_pdf_url named an older version folder than r2_current_path.
The citation links read r2_public_pdf_url, so Waverley DCP 2022's link opened a 490-page copy while its
rules cite pages of the 448-page current one. upsert_registry moved r2_current_path alone.

r2_upload_pdfs imports boto3 and the council configs at module level, so the function and its base
constant are exec-extracted from the source and driven with a recording cursor.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = (ROOT / "scripts" / "r2_upload_pdfs.py").read_text(encoding="utf-8")


def _load_upsert():
    ns: dict = {}
    exec(re.search(r"^R2_PUBLIC_BASE = .+$", SOURCE, re.M).group(0), ns)
    start = SOURCE.index("def upsert_registry(")
    nxt = re.search(r"\n(?:def |class |# ─)", SOURCE[start + 10:])
    exec(SOURCE[start:start + 10 + nxt.start()], ns)
    return ns["upsert_registry"], ns["R2_PUBLIC_BASE"]


class _Cursor:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))


def _row(path):
    return {
        "council": "waverley", "dcp_name": "Waverley DCP 2022", "doc_type": "dcp",
        "chapter_key": "waverley-dcp-2022", "chapter_label": "Waverley DCP 2022", "sort_order": 1,
        "council_url": "https://www.waverley.nsw.gov.au/x.pdf", "council_page_url": None,
        "r2_current_path": path, "r2_version_label": "v1.1-2026-03-16",
        "content_hash": "h", "url_content_length": 1, "url_etag": None, "url_last_modified": None,
        "url_last_checked": None, "url_last_changed": None, "notes": None,
    }


def test_the_link_is_written_from_the_current_copy_on_insert_and_on_update():
    upsert, base = _load_upsert()
    cur = _Cursor()
    path = "source-pdfs/dcps/waverley/v1.1-2026-03-16/waverley-dcp-2022.pdf"
    upsert(cur, _row(path))
    (sql, params), = cur.calls
    assert params["r2_public_pdf_url"] == base + path
    condensed = re.sub(r"\s+", " ", sql)
    assert "r2_version_label, r2_public_pdf_url," in condensed
    assert "%(r2_public_pdf_url)s" in condensed
    assert "r2_public_pdf_url = EXCLUDED.r2_public_pdf_url" in condensed, (
        "a re-upload updates r2_current_path but not the link, which is how 15 links fell behind"
    )


def test_the_link_names_the_same_version_folder_as_the_current_copy():
    """Confusable case: an older link on the row passed in must not survive the upsert."""
    upsert, base = _load_upsert()
    cur = _Cursor()
    row = _row("source-pdfs/dcps/waverley/v1.1-2026-03-16/waverley-dcp-2022.pdf")
    row["r2_public_pdf_url"] = base + "source-pdfs/dcps/waverley/v1.0-baseline/waverley-dcp-2022.pdf"
    upsert(cur, row)
    link = cur.calls[0][1]["r2_public_pdf_url"]
    assert "/v1.1-2026-03-16/" in link and "/v1.0-baseline/" not in link


def test_no_current_copy_means_no_link():
    upsert, _ = _load_upsert()
    cur = _Cursor()
    upsert(cur, _row(None))
    assert cur.calls[0][1]["r2_public_pdf_url"] is None


def test_a_dry_run_writes_nothing():
    upsert, _ = _load_upsert()
    cur = _Cursor()
    upsert(cur, _row("source-pdfs/dcps/x/v1.0-baseline/y.pdf"), dry_run=True)
    assert cur.calls == []


def test_the_base_matches_the_one_the_change_monitor_uses():
    monitor = (ROOT / "scripts" / "r2_monitor.py").read_text(encoding="utf-8")
    m = re.search(r'^R2_PUBLIC_BASE\s*=\s*"([^"]+)"', monitor, re.M)
    _, base = _load_upsert()
    assert m and m.group(1) == base, "the uploader and the change monitor would write different links"
