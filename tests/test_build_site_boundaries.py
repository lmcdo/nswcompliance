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
    assert b._norm("Lot 1/2 DP 214260") != b._norm("Lot 12 DP 214260")
    assert b._norm("Lots A and B, DP 355656") == b._norm("Lots A and B,\nDP 355656")


# --- Leichhardt Part G wording (council PDF pages 31, 65, 105, 116, 139, 2026-11-04) ---
# The cadastre writes a lot with a section as lot/section/DPnnn ('3/D/DP119'); without one,
# lot//DPnnn. Before this, a section lot was dropped without any message: the pattern
# needed "Lot N, DP" and a section word in between matched nothing.

def test_section_letter_is_part_of_the_lot_id():
    # G6 p31
    text = "Lot 3 Sec D DP 119 , Lot 2 DP 234045 and Lot 1 DP 540118"
    assert b.parse_lots(text) == ["3/D/DP119", "2//DP234045", "1//DP540118"]


def test_section_number_written_in_full():
    # G9 p105
    text = "Lot 1 DP 1119151, Lot 3 Section 3 DP 328, Lot 4 Section 3 DP 328"
    assert b.parse_lots(text) == ["1//DP1119151", "3/3/DP328", "4/3/DP328"]


def test_one_section_covers_every_lot_named_before_it():
    # G7 p65: "Lots 1, 2 and 3 in Sec 13 DP 638"
    assert b.parse_lots("Lots 1, 2 and 3 in Sec 13 DP 638") == ["1/13/DP638", "2/13/DP638", "3/13/DP638"]


def test_to_makes_a_range_and_is_not_a_lot():
    # G7 p65: "Lots 58 and 67 to 78 DP 4844"
    lots = b.parse_lots("Lots 58 and 67 to 78 DP 4844")
    assert lots[0] == "58//DP4844" and lots[1] == "67//DP4844" and lots[-1] == "78//DP4844"
    assert len(lots) == 13


def test_en_dash_range():
    # G12 p139: "Lots 2–4, DP 1257743"
    assert b.parse_lots("Lots 2–4, DP 1257743, Lots 1 and 2, DP 529451") == [
        "2//DP1257743", "3//DP1257743", "4//DP1257743", "1//DP529451", "2//DP529451"]


def test_a_section_does_not_leak_to_the_next_lot():
    text = "Lot 25 Sec 1 DP 328, Lot A DP 377714"
    assert b.parse_lots(text) == ["25/1/DP328", "A//DP377714"]
