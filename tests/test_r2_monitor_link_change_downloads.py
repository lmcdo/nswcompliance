"""A chapter whose link changes is downloaded on the next check, never passed as 'unchanged' on a HEAD.

Known-wrong case (run 7, 2026-10-24): Woollahra rows 233, 234, 410 were re-pointed at the DCP 2015 chapters;
their url_last_downloaded was recent and the server sends no tag, so decide_fetch returned untagged_recent and
the new file was never compared.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verifyops_record import decide_fetch  # noqa: E402

NOW = datetime(2026, 10, 24, 7, 16, tzinfo=timezone.utc)
SRC = (ROOT / "scripts" / "r2_monitor.py").read_text(encoding="utf-8").replace("\r\n", "\n")


def _fetch(**kw):
    base = dict(force=False, stored_hash="h", stored_etag=None, head_etag=None, stored_len=None, head_len=None,
                last_downloaded=NOW - timedelta(days=1), now=NOW, spot=False)
    base.update(kw)
    return decide_fetch(**base)


def test_known_wrong_recent_download_skips():
    assert _fetch() == (False, "untagged_recent")


def test_cleared_fields_force_a_download():
    assert _fetch(stored_etag=None, last_downloaded=None) == (True, "untagged_weekly")


def test_both_link_writes_clear_tag_and_last_download():
    assert SRC.count("url_etag = NULL, \"\n                            \"url_last_downloaded = NULL WHERE council = %s AND chapter_key = %s\"") == 1
    assert SRC.count("SET council_url = %s, url_etag = NULL, url_last_downloaded = NULL \"\n"
                     "                            \"WHERE council = %s AND chapter_key = %s AND council_url != %s\"") == 1
    assert "ch[\"url_last_downloaded\"] = None" in SRC and "ch[\"url_etag\"] = None" in SRC
    assert "SET council_url = %s WHERE" not in SRC
