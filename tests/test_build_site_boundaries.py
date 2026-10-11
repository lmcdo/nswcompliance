"""Single-site outlines from the chapter's own Lot/DP list (DQ-143)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_site_boundaries as b  # noqa: E402

SITES = json.loads((Path(__file__).resolve().parents[1] / "data" / "site_chapters" / "lot_sites.json")
                   .read_text(encoding="utf-8"))["sites"]


def test_ranges_expand():
    assert b.parse_lots("Lot 6-9, DP79950") == ["6//DP79950", "7//DP79950", "8//DP79950", "9//DP79950"]


def test_letter_lots_joined_by_and_are_all_read():
    assert b.parse_lots("Lots A and B, DP 355656") == ["A//DP355656", "B//DP355656"]


def test_table_text_between_lots_is_ignored():
    # 445 Canterbury Rd p4 Table 1: the PDF runs the site-area cell into the lot list.
    lots = b.parse_lots(next(s for s in SITES if s["precinct_id"] == "11.12")["lots_verbatim"])
    assert len(lots) == 9 and "3//DP337683" in lots and "B//DP391661" in lots


def test_a_neighbouring_lot_is_not_a_site_lot():
    # Boorea names Lot 26 DP 13586 only as the boundary it must set back FROM; it is not listed.
    assert all("13586" not in s["lots_verbatim"] for s in SITES)


def test_leichhardt_lists_twenty_four_lots():
    lots = b.parse_lots(next(s for s in SITES if s["council"] == "leichhardt")["lots_verbatim"])
    assert len(lots) == 24 and lots[0] == "6//DP79950" and lots[-1] == "9//DP666322"


def test_copy_check_ignores_layout_not_words():
    assert b._norm("Lot 3 DP 214260 • Lot 2") == b._norm("Lot 3\nDP 214260 Lot 2")
    assert b._norm("Lot 3 DP 214260") != b._norm("Lot 8 DP 214260")


def test_copy_check_keeps_the_separators_that_change_meaning():
    # cross-review 2026-10-12: 'Lot 1-2' and 'Lot 12' must not compare equal
    assert b._norm("Lot 1-2 DP 214260") != b._norm("Lot 12 DP 214260")
    assert b._norm("Lots A and B, DP 355656") == b._norm("Lots A and B,\nDP 355656")
