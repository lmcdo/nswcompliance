"""Address-only single sites: number ranges and register addresses (DQ-143)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import site_addresses as sa  # noqa: E402


def test_same_parity_range_is_one_side_of_the_street():
    site, named = sa.parse_numbers("15-33")
    assert site == {str(n) for n in range(15, 34, 2)} and named == {"15", "33"}
    assert "16" not in site  # across the street


def test_mixed_parity_range_is_every_number():
    site, _ = sa.parse_numbers("20-21")
    assert site == {"20", "21"}


def test_list_with_single_and_range():
    site, named = sa.parse_numbers("22,30-40")
    assert site == {"22", "30", "32", "34", "36", "38", "40"} and named == {"22", "30", "40"}


def test_lettered_numbers_kept_exact():
    site, named = sa.parse_numbers("2,2A")
    assert site == named == {"2", "2A"}


def test_register_address_numbers():
    s, sub = "BRIGHTON AVENUE", "CROYDON PARK"
    assert sa._base_numbers("1/23-25 BRIGHTON AVENUE CROYDON PARK", s, sub) == ["23", "25"]
    assert sa._base_numbers("24A BRIGHTON AVENUE CROYDON PARK", s, sub) == ["24A"]
    assert sa._base_numbers("24 BRIGHTON STREET CROYDON PARK", s, sub) == []  # another street


def test_lettered_rule_only_when_chapter_names_plain_numbers():
    assert not sa._lettered({"15", "17"})
    assert sa._lettered({"2", "2A"})
