"""The version check reuses dcp_quote_status.classify; these pin what it must say for an older file."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import dcp_quote_status as q  # noqa: E402

QUOTE = "Side setbacks to external walls should be a minimum of 900mm."


def test_same_words_same_page_is_verbatim():
    assert q.classify(QUOTE, ["intro", "text " + QUOTE + " more"], 2) == "verbatim"


def test_repaginated_older_file_is_wrong_page_not_verbatim():
    assert q.classify(QUOTE, ["x " + QUOTE, "other"], 2) == "wrong_page"


def test_reworded_older_file_is_not_found():
    assert q.classify(QUOTE, ["Side setbacks should be at least 1.2 m."], 1) == "not_found"


def test_unreadable_or_empty_source_is_no_source_never_a_pass():
    assert q.classify(QUOTE, None, 1) == "no_source"
    assert q.classify(QUOTE, ["", ""], 1) == "no_source"
    assert q.classify("", ["text"], 1) == "no_source"


def test_served_file_filed_under_another_chapter_is_added_to_the_chapter():
    import dcp_quote_version_check as v

    assert "r.r2_current_path" in v.SERVED_SQL and "r.chapter_key" in v.SERVED_SQL.split("FROM")[0]
    assert "v.chapter_key" not in v.SERVED_SQL   # joined on the file, not on the ledger's chapter name
