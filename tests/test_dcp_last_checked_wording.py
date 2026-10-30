"""The council rules page states only what was checked and when (offer agreed with the user 2026-10-24).

Known-wrong text it replaces: "the twice-monthly check" (the check has run daily since #1457) and a
35-day stale point (the agreed offer says "Not recently checked" after 30 days).
"""
import re
from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "frontend-nextjs" / "components" / "compliance"
       / "ProvisionsByTocStructure.tsx").read_text(encoding="utf-8")
_START = SRC.index("*/}", SRC.index("DCP currency status")) + 3  # after the developer comment
BLOCK = SRC[_START:SRC.index("Structured DCP controls")]


def test_last_checked_line_names_what_was_checked():
    assert "Last checked against the council&apos;s published PDF: {verifiedDateLabel}" in BLOCK


def test_not_recently_checked_after_30_days():
    assert "> 30 * 24 * 60 * 60 * 1000" in SRC
    assert "35 * 24" not in SRC
    assert BLOCK.count("Not recently checked.") == 2          # with and without a last date
    assert "Check the council&apos;s own DCP page before relying on these rules." in BLOCK


def test_old_wrong_text_is_gone():
    assert "twice-monthly" not in SRC
    assert "Currency data overdue" not in SRC


def test_no_promise_words_in_the_currency_block():
    # Liability language (.claude/rules/pre-pr-review.md): the block may state facts, not guarantees.
    words = (r"\b(safe|feasible|compliant|should|recommend|suitable|adequate|sufficient|approved|guaranteed|"
             r"certified|confirmed|verified|ensure|assure|accurate|definitive|comprehensive|reliable|current)\b")
    text = re.sub(r"\{[^}]*\}|className=\"[^\"]*\"|//[^\n]*", " ", BLOCK)
    assert re.findall(words, text, flags=re.I) == []


def test_a_malformed_date_counts_as_no_date():
    assert "!Number.isNaN(new Date(v).getTime())" in SRC
