"""Mapping a chapter to the config part that decides whether users ever see it.

The matching rule is load-bearing: get it wrong and a chapter is reported as
in-scope that the app gates differently, or dropped from a coverage number that
is then quoted at someone.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dcp_inscope_status import chapter_part, classify  # noqa: E402


class TestChapterToPart:
    def test_each_council_uses_its_own_convention(self):
        # Four different shapes, all real, all from the live configs.
        assert chapter_part("marrickville", "part2-s10-parking",
                            ["Part 1", "Part 2"]) == "Part 2"
        assert chapter_part("ashfield", "chapter-a-miscellaneous",
                            ["Chapter A", "Chapter B"]) == "Chapter A"
        assert chapter_part("leichhardt", "part-c-s1-general",
                            ["Part B", "Part C"]) == "Part C"
        assert chapter_part("woollahra", "chapter-e1-parking-access",
                            ["A1", "E1", "E2"]) == "E1"  # noqa: zone-codes  (woollahra DCP chapter keys, not NSW zones)

    def test_the_LONGEST_key_wins(self):
        # ku_ring_gai has both part_4_dwelling_houses and
        # part_4_1_secondary_dwellings. Shortest-first would file the secondary
        # dwellings chapter under dwelling houses and report it as in a scope
        # tier the app does not actually put it in.
        keys = ["part_4_dwelling_houses", "part_4_1_secondary_dwellings"]
        assert chapter_part("ku_ring_gai",
                            "section-a-part-4-1-secondary-dwellings",
                            keys) == "part_4_1_secondary_dwellings"
        assert chapter_part("ku_ring_gai", "section-a-part-4-dwelling-houses",
                            keys) == "part_4_dwelling_houses"

    def test_a_chapter_in_no_configured_part_returns_None(self):
        # None is the honest answer, and the caller reports it rather than
        # guessing a part for it.
        assert chapter_part("marrickville", "part6-industrial",
                            ["Part 1", "Part 2", "Part 3", "Part 7"]) is None

    def test_an_empty_scope_list_matches_nothing(self):
        assert chapter_part("x", "part2-s10-parking", []) is None

    def test_a_blank_key_is_ignored_not_matched_to_everything(self):
        # "" is a prefix of every string. Without the guard it would claim every
        # chapter and report a council as fully in scope.
        assert chapter_part("x", "part2-s10-parking", ["", "Part 2"]) == "Part 2"
        assert chapter_part("x", "anything-at-all", [""]) is None


class TestClassify:
    def _row(self, **kw):
        base = dict(measured=True, contents="OK", header="CONSISTENT",
                    attribution="ATTRIBUTED", live_rows=10, missing=0)
        base.update(kw)
        return ("c", "k", base["measured"], base["contents"], base["header"],
                base["attribution"], base["live_rows"], base["missing"])

    def test_no_rows_beats_every_other_verdict(self):
        assert classify(self._row(live_rows=0, contents="OK")) == "NOTHING"

    def test_collapsed_and_mislabelled_both_read_as_filed_wrong(self):
        assert classify(self._row(attribution="COLLAPSED")) == "FILED_WRONG"
        assert classify(self._row(header="MISLABELLED")) == "FILED_WRONG"

    def test_incomplete_is_partial(self):
        assert classify(self._row(contents="INCOMPLETE")) == "PARTIAL"

    def test_only_a_contents_check_that_PASSED_is_good(self):
        assert classify(self._row()) == "GOOD"

    def test_anything_unjudged_is_UNVERIFIED_not_good(self):
        # The rule the whole repair exists for: not-checked is never clean.
        for verdict in ("NOT_MEASURED:NO_CONTENTS", "NOT_MEASURED:UNREADABLE",
                        "VOCAB_MISMATCH", "NOT_MEASURED:NO_STORED_CODES"):
            assert classify(self._row(contents=verdict)) == "UNVERIFIED", verdict
