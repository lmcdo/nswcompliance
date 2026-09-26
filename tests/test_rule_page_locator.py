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

def _doc(**by_page):
    base = {p: FILLER for p in range(1, 13)}
    base.update({int(k[1:]): v for k, v in by_page.items()})
    return L.Doc(base)


BODY = L.rule_body(RULE)


def test_a_rule_on_its_stored_page_stays():
    assert L.locate(RULE, [_doc(p1=BODY)], stored=1) == (1, "on_page")


def test_a_rule_stored_at_the_chunk_start_moves_to_its_own_page():
    assert L.locate(RULE, [_doc(p5=BODY)], stored=1, window=range(1, 13)) == (5, "moved")


def test_a_rule_is_not_also_on_the_pages_either_side_of_it():
    """The first version tested each page joined to the next, so a rule on page 21 also
    'matched' pages 20 and 22 and looked printed three times: 1,262 rules wrongly unresolved."""
    assert L.locate(RULE, [_doc(p6=BODY)], stored=1) == (6, "moved")


def test_a_rule_really_printed_twice_is_not_guessed():
    assert L.locate(RULE, [_doc(p4=BODY, p9=BODY)], stored=1) == (None, "unresolved")


def test_the_chunk_settles_a_real_repeat_when_only_one_copy_is_in_it():
    doc = L.Doc({**{p: FILLER for p in range(1, 30)}, 4: BODY, 20: BODY})
    assert L.locate(RULE, [doc], stored=1, window=range(1, 13)) == (4, "moved")


def test_a_repeated_rule_already_on_one_of_its_copies_stays():
    assert L.locate(RULE, [_doc(p4=BODY, p9=BODY)], stored=9) == (9, "on_page")


def test_a_generic_opening_printed_elsewhere_does_not_make_a_rule_repeated():
    """Only the opening words on page 3; the whole rule on page 8: page 8, not a tie."""
    opening = " ".join(L.tokens(BODY)[:9])
    assert L.locate(RULE, [_doc(p3=opening, p8=BODY)], stored=1) == (8, "moved")


def test_the_same_words_scrambled_are_not_the_rule():
    scrambled = " ".join(reversed(L.tokens(BODY)))
    assert L.locate(RULE, [_doc(p1=scrambled)], stored=1) == (None, "not_found")
    assert L.locate(RULE, [_doc(p1=scrambled, p5=BODY)], stored=1) == (5, "moved")


def test_a_rule_running_over_a_page_break_is_on_the_page_it_starts():
    t = L.tokens(BODY)
    half = len(t) // 2
    doc = _doc(p7=FILLER + " " + " ".join(t[:half]), p8=" ".join(t[half:]) + " " + FILLER)
    assert L.locate(RULE, [doc], stored=7) == (7, "on_page")
    assert L.locate(RULE, [doc], stored=1) == (7, "moved")


def test_a_two_column_page_is_found_in_the_reading_order_that_keeps_it_whole():
    """Top-to-bottom interleaves two columns; the PDF's own order keeps the rule intact."""
    t = L.tokens(BODY)
    interleaved = " ".join(w for pair in zip(t, ["col"] * len(t)) for w in pair)
    top_down, own_order = _doc(p5=interleaved), _doc(p5=BODY)
    assert L.locate(RULE, [top_down], stored=1) == (None, "not_found")
    assert L.locate(RULE, [top_down, own_order], stored=1) == (5, "moved")


def test_a_rule_with_words_dropped_by_the_reader_is_still_found():
    t = L.tokens(BODY)
    damaged = " ".join(w for i, w in enumerate(t) if i != 10)
    assert L.locate(RULE, [_doc(p6=damaged)], stored=1) == (6, "moved")


def test_part_of_the_rule_is_accepted_only_where_nothing_else_comes_close():
    """Stored text with map labels mixed in (City of Sydney): a third of it printed in one
    place, and nowhere else, is still that place. A fifth is not; two such places is a tie."""
    long_body = (BODY + " Garages and carports are to be located behind the building line and"
                 " must not dominate the street frontage of the dwelling or the lot.")
    rule = "# C3 Front setbacks\n" + long_body
    t = L.tokens(long_body)
    part = " ".join(t[: len(t) * 2 // 5])        # about two fifths of it, in order
    assert L.locate(rule, [_doc(p6=part)], stored=1) == (6, "moved")
    assert L.locate(rule, [_doc(p6=" ".join(t[:7]))], stored=1) == (None, "unresolved")
    assert L.locate(rule, [_doc(p2=part, p11=part)], stored=1) == (None, "unresolved")


def test_wording_nowhere_in_the_document_is_not_found():
    assert L.locate(RULE, [_doc()], stored=1) == (None, "not_found")


def test_a_two_word_rule_is_too_short_to_locate():
    assert L.locate("# C1 Objectives\nSee above.", [_doc()], stored=1) == (None, "too_short")


def test_our_own_heading_line_is_not_the_councils_text():
    only_heading = "c3 front setbacks " + FILLER
    assert L.locate(RULE, [_doc(p3=only_heading)], stored=1) == (None, "not_found")


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


def test_a_page_whose_footer_cannot_be_read_takes_its_number_from_the_run():
    """The offset is found once per document and applied to every page of the run: a blank
    page, or one whose footer is a picture, still gets its printed number."""
    m = {5: ["21"], 6: [], 7: ["23"], 8: ["24"], 9: ["25"]}
    assert L.printed_labels(m) == {5: "21", 6: "22", 7: "23", 8: "24", 9: "25"}


def test_most_pages_unreadable_still_get_the_documents_numbering():
    """Leichhardt Part C s1: page numbers read on 38 of 109 pages."""
    m = {p: [] for p in range(1, 41)}
    for p in range(3, 41):
        if p % 4 in (0, 1):                      # readable in pairs, a third of the pages
            m[p] = [f"PART C - {p + 60}"]
    got = L.printed_labels(m)
    assert got[4] == "64" and got[22] == "82" and got[37] == "97" and 40 not in got


def test_numbering_that_restarts_is_separate_runs_and_covers_are_left_alone():
    """City of Sydney restarts at each section ('4.1-1' ... '4.2-1'); pages 1-2 are covers."""
    m = {1: ["Sydney DCP 2012"], 2: ["Contents"]}
    m.update({p: [f"4.1-{p - 2}"] for p in range(3, 8)})
    m.update({p: [f"4.2-{p - 7}"] for p in range(8, 12)})
    got = L.printed_labels(m)
    assert 1 not in got and 2 not in got
    assert got[3] == "4.1-1" and got[7] == "4.1-5" and got[8] == "4.2-1" and got[11] == "4.2-4"


def test_the_numbering_runs_are_reported_for_the_chapter_record():
    runs = L.page_numbering({p: [f"Page B{p - 2} of B54"] for p in range(3, 9)})
    assert runs == [{"prefix": "B", "offset": -2, "first": 3, "last": 8, "seen": 6}]


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


def test_the_heading_line_is_dropped_but_a_heading_only_rule_is_kept():
    assert L.rule_body("# C3 Front setbacks\nBuildings are set back.") == "Buildings are set back."
    assert L.rule_body("# C3 Front setbacks") == "# C3 Front setbacks"


def test_the_better_reading_of_a_page_wins_whichever_order_they_come_in():
    t = L.tokens(BODY)
    half_read = " ".join(t[: len(t) // 3])            # this reading keeps only a third intact
    for docs in ([_doc(p5=BODY), _doc(p5=half_read)], [_doc(p5=half_read), _doc(p5=BODY)]):
        assert L.locate(RULE, docs, stored=1) == (5, "moved")


def test_a_link_to_the_second_page_of_a_rule_running_over_a_page_break_is_kept():
    """Both pages show the rule; moving the link by one page is churn (1,040 rows on a draft)."""
    t = L.tokens(BODY)
    half = len(t) // 2
    doc = _doc(p7=FILLER + " " + " ".join(t[:half]), p8=" ".join(t[half:]) + " " + FILLER)
    assert L.locate(RULE, [doc], stored=8) == (8, "on_page")


def test_a_rule_printed_under_several_headings_takes_the_copy_under_its_own():
    """Ashfield E1: the same objectives restated for each conservation area."""
    rule = "# E1 Heritage Objectives C4 Goodwin Avenue\n" + BODY  # noqa: zone-codes -- DCP clause labels, not zones
    doc = _doc(p3="C3 Service Avenue conservation area " + BODY, p7="C4 Goodwin Avenue conservation area " + BODY)  # noqa: zone-codes -- DCP clause labels, not zones
    assert L.locate(rule, [doc], stored=1) == (7, "moved")


def test_copies_under_equally_named_headings_are_not_guessed():
    rule = "# E1 Heritage Objectives C4 Goodwin Avenue\n" + BODY  # noqa: zone-codes -- DCP clause labels, not zones
    doc = _doc(p3="Goodwin Avenue " + BODY, p7="Goodwin Avenue " + BODY)
    assert L.locate(rule, [doc], stored=1) == (None, "unresolved")


def test_a_short_rule_printed_once_is_found_whole():
    """'To ensure the roof can be maintained.' -- shorter than a 6-word piece."""
    rule = "# C1.21.1 O8 Maintenance Accessibility\nTo ensure roofs are maintained."
    assert L.locate(rule, [_doc(p9="objectives o8 to ensure roofs are maintained o9")], stored=1) == (9, "moved")
    assert L.locate(rule, [_doc(p4="to ensure roofs are maintained", p9="to ensure roofs are maintained")],
                    stored=1) == (None, "unresolved")
    assert L.locate("# C1 O2\nSee above.", [_doc()], stored=1) == (None, "too_short")


def test_a_stored_page_holding_the_rule_is_not_left_for_a_near_identical_text_elsewhere():
    """Woollahra B1.11.1 'Vaucluse East' (page 41) and B1.10.1 'Vaucluse West' (page 38) share
    most of their wording; the West copy scored a little higher and the link was moved."""
    t = L.tokens(BODY)
    near = " ".join(t[:-7])                   # two thirds of it: strong, but below a tie
    assert L.locate(RULE, [_doc(p3=BODY, p8=near)], stored=8) == (8, "on_page")


def test_a_new_sections_unreadable_first_page_does_not_take_the_old_sections_count():
    """City of Sydney: page 85 prints '2.6-1'; carried on, '2.5' gave it '2.5-19'."""
    m = {p: [f"2.5-{p - 66}"] for p in range(80, 85)}
    m[85] = []                                   # first page of 2.6, footer unreadable
    m.update({p: [f"2.6-{p - 84}"] for p in range(86, 90)})
    got = L.printed_labels(m)
    assert 85 not in got and got[84] == "2.5-18" and got[86] == "2.6-2"
