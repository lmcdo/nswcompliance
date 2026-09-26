"""A rule's page link must open the page the rule is on; its label must be the printed number.

Measured 2026-09-26 over all 237 served chapter PDFs (17,489 rules): 45% of links
opened the first page of the AI reader's 12-page chunk, not the rule's page. Each
test pins one rule of scripts/rule_page_locator.py with the confusable case that
would break it. Footer lines are copied from the real PDFs (woollahra B4, ku-ring-gai
14D, city of sydney s4, cumberland part B, hornsby part 1).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import rule_page_locator as L  # noqa: E402

RULE = ("# C3 Front setbacks\nBuildings are to be set back from the front boundary "
        "consistent with the prevailing setback of adjoining dwellings in the street.")
FILLER = "landscaped area provisions apply to the rear of the site and include deep soil planting zones"


def _pages(**by_page):
    base = {p: FILLER for p in range(1, 13)}
    base.update({int(k[1:]): v for k, v in by_page.items()})
    return L.Pages(base)


# -- locating ------------------------------------------------------------------------

def test_a_rule_on_its_stored_page_stays():
    body = L.rule_body(RULE)
    assert L.locate(RULE, _pages(p1=body), stored=1) == (1, "on_page")


def test_a_rule_stored_at_the_chunk_start_moves_to_its_own_page():
    body = L.rule_body(RULE)
    assert L.locate(RULE, _pages(p5=body), stored=1, window=range(1, 13)) == (5, "moved")


def test_the_same_wording_on_two_pages_is_not_guessed():
    body = L.rule_body(RULE)
    assert L.locate(RULE, _pages(p4=body, p9=body), stored=1) == (None, "unresolved")


def test_a_window_settles_a_repeat_when_only_one_copy_is_in_the_chunk():
    body = L.rule_body(RULE)
    pages = L.Pages({**{p: FILLER for p in range(1, 30)}, 4: body, 20: body})
    assert L.locate(RULE, pages, stored=1, window=range(1, 13)) == (4, "moved")


def test_the_same_words_scrambled_are_not_enough_to_move_a_link():
    """80% of the words but no 8-word run in order: a bag of common words."""
    scrambled = " ".join(reversed(L.tokens(L.rule_body(RULE))))
    assert L.locate(RULE, _pages(p6=scrambled), stored=1) == (None, "unresolved")


def test_the_two_methods_disagreeing_is_not_a_move():
    body = L.rule_body(RULE)
    assert L.locate(RULE, _pages(p5=body), stored=1, anchor_pages={8}) == (None, "unresolved")


def test_a_rule_running_over_a_page_break_is_on_its_first_page():
    t = L.tokens(L.rule_body(RULE))
    half = len(t) // 2
    pages = _pages(p7=" ".join(t[:half]), p8=" ".join(t[half:]))
    assert L.locate(RULE, pages, stored=7) == (7, "on_page")
    assert L.locate(RULE, pages, stored=1) == (7, "moved")


def test_wording_nowhere_in_the_document_is_not_found():
    assert L.locate(RULE, _pages(), stored=1) == (None, "not_found")


def test_a_two_word_rule_is_too_short_to_locate():
    assert L.locate("# C1 Objectives\nSee above.", _pages(), stored=1) == (None, "too_short")


def test_our_own_heading_line_is_not_the_councils_text():
    """The '# code title' line is ours; matching it would locate our words, not theirs."""
    only_heading = "c3 front setbacks " + FILLER
    assert L.locate(RULE, _pages(p3=only_heading), stored=1) == (None, "not_found")


# -- batch size ----------------------------------------------------------------------

def test_chunk_size_is_read_from_the_stored_pages():
    assert L.batch_size([1, 13, 25, 13, 1, 37]) == 12
    assert L.batch_size([1, 31, 61, 91, 1]) == 30


def test_pages_that_are_not_chunk_starts_give_no_window():
    assert L.batch_size([3, 8, 14, 22, 5, 41]) is None
    assert L.batch_size([]) is None


# -- printed page numbers ------------------------------------------------------------

def _footers(fmt, first, n, extra=()):
    return {p: [fmt.format(first + i), *extra] for i, p in enumerate(range(5, 5 + n))}


def test_plain_and_dashed_and_lettered_page_numbers_are_read_as_printed():
    assert L.printed_labels(_footers("{}", 21, 3))[6] == "22"
    assert L.printed_labels(_footers("p 14-{}", 117, 3))[5] == "14-117"          # ku-ring-gai
    assert L.printed_labels(_footers("4.1-{}", 2, 3))[7] == "4.1-4"              # city of sydney
    assert L.printed_labels(_footers("Page B{} of B54", 5, 3))[5] == "B5"        # cumberland
    assert L.printed_labels(_footers("  B4 pg.{}", 3, 3))[6] == "4"         # woollahra


def test_a_year_date_or_chapter_code_repeated_on_every_page_is_not_a_page_number():
    extra = ("Woollahra Development Control Plan 2015", "24 February 2026", "B4 | Housing")
    labels = L.printed_labels(_footers("  B4 pg.{}", 3, 3, extra))
    assert labels == {5: "3", 6: "4", 7: "5"}


def test_a_page_with_no_neighbour_agreeing_gets_no_label():
    assert L.printed_labels({5: ["12"], 9: ["40"]}) == {}


def test_two_counting_tokens_on_one_page_give_no_label():
    """A section-page AND a document-page both counting: which one is 'the' page? Neither."""
    m = {p: [f"{p + 10}", f"s-{p}"] for p in range(5, 8)}
    assert L.printed_labels(m) == {}


def test_a_blank_page_between_does_not_break_the_count():
    m = {5: ["21"], 6: [], 7: ["23"]}
    assert L.printed_labels(m) == {5: "21", 7: "23"}


def test_an_anchor_outside_the_chunk_does_not_block_the_page_inside_it():
    body = L.rule_body(RULE)
    pages = L.Pages({**{p: FILLER for p in range(1, 30)}, 5: body})
    assert L.locate(RULE, pages, stored=1, window=range(1, 13), anchor_pages={20}) == (5, "moved")


def test_a_repeated_rule_already_on_its_stored_copy_stays():
    body = L.rule_body(RULE)
    assert L.locate(RULE, _pages(p4=body, p9=body), stored=9) == (9, "on_page")


def test_disagreement_is_unresolved_even_when_the_anchor_page_shows_the_opening():
    t = L.tokens(L.rule_body(RULE))
    opening = " ".join(t[:9])                   # the first words only: not most of the rule
    pages = _pages(p5=L.rule_body(RULE), p8=opening)
    assert L.locate(RULE, pages, stored=1, anchor_pages={8}) == (None, "unresolved")


def test_the_heading_line_is_dropped_but_a_heading_only_rule_is_kept():
    assert L.rule_body("# C3 Front setbacks\nBuildings are set back.") == "Buildings are set back."
    assert L.rule_body("# C3 Front setbacks") == "# C3 Front setbacks"


def test_a_header_printing_two_years_is_not_a_page_count():
    """Hornsby prints '2024' and '...AMENDED ON 23 JUNE 2025' on every page: read across
    neighbours, 2024 -> 2025 counts by one. A page number is never the same on the next page."""
    head = ["HORNSBY DEVELOPMENT CONTROL PLAN 2024  |  GENERAL", "THIS PART WAS LAST AMENDED ON 23 JUNE 2025"]
    m = {p: [*head, f"1-{p}"] for p in range(10, 13)}
    assert L.printed_labels(m) == {10: "1-10", 11: "1-11", 12: "1-12"}


def test_a_spaced_page_number_is_read_whole():
    """Penrith: 'D2 Residential Development          D2 - 10'. '10' alone is not what is printed."""
    m = {p: ["Penrith Development Control Plan 2014", f"D2 Residential Development        D2 - {p}"]
         for p in range(10, 13)}
    assert L.printed_labels(m) == {10: "D2-10", 11: "D2-11", 12: "D2-12"}


def test_a_numbered_requirement_at_the_foot_of_a_page_is_not_a_page_number():
    """Northern Beaches (our render of the council's web page, no printed page numbers):
    requirement 28 sat at the foot of PDF page 117, 29 at the next -- counting, but body text."""
    m = {116: ["27. All development must incorporate soil conservation measures to minimise soil erosion"],
         117: ["28. A Soil and Water Management Plan, prepared in accordance with Managing Urban Stormwater"],
         118: ["29. Stockpiles are to be located clear of drainage lines, gutters and the road reserve"]}
    assert L.printed_labels(m) == {}


def test_a_long_running_footer_with_the_number_at_its_end_still_counts():
    m = {p: [f"Campbelltown (Sustainable City) Development Control Plan 2015  Effective:11/03/16  Page {p + 62}"]
         for p in range(20, 23)}
    assert L.printed_labels(m) == {20: "82", 21: "83", 22: "84"}


def test_scattered_counting_headings_in_a_document_without_page_numbers_give_no_labels():
    """Northern Beaches' render: short headings '10.4' then '10.5' on two neighbouring pages
    among 20 pages with nothing else. A real footer is on most pages; this is not one."""
    m = {p: ["Warringah Development Control Plan"] for p in range(1, 21)}
    m[7], m[8] = ["10.4"], ["10.5"]
    assert L.printed_labels(m) == {}


def test_a_stored_page_with_the_same_words_in_another_order_does_not_hold_the_rule():
    """Cross-review 2026-09-26: 80% of the rule's words on the chunk-start page, but not the rule."""
    scrambled = " ".join(reversed(L.tokens(L.rule_body(RULE))))
    assert L.locate(RULE, _pages(p1=scrambled), stored=1) == (None, "unresolved")
    assert L.locate(RULE, _pages(p1=scrambled, p5=L.rule_body(RULE)), stored=1) == (5, "moved")
