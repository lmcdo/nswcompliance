"""'as-of-right' is a verdict (no approval needed); the liability scanner must catch it in prose
and leave the field name alone. Origin: page check C5 found it on 18 of 19 assessment pages."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import liability_language_check as llc  # noqa: E402


@pytest.mark.parametrize("text", [
    "dwelling house — as-of-right yield, subject to a development application.",
    "1 as-of-right (subject to a DA)",
    "dwellings as of right",
    "The As-Of-Right residential baseline",
])
def test_prose_is_flagged(text):
    assert llc.FLAGGED_TERMS.search(text)


@pytest.mark.parametrize("text", [
    "{humanizeForm(result.as_of_right_form)} — subject to a development application.",
    "result.as_of_right_dwellings = result.realistic_dwellings",
    "the right of way",
])
def test_identifiers_and_other_words_pass(text):
    assert not llc.FLAGGED_TERMS.search(text)


def test_scan_reports_the_line():
    hits = llc.scan_lines("Card.tsx", [(7, "  <span>1</span> as-of-right (subject to a DA),")])
    assert len(hits) == 1
