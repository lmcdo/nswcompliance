"""The four per-chapter signals, the three-state scoring, and the ratchet.

The property under test throughout is the one the previous check failed: a signal
that did not run must never read as a signal that found nothing. Every "cannot
judge" path is asserted explicitly, and the mutation tests at the bottom check
that a gutted implementation would not pass.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dcp_chapter_measure import (  # noqa: E402
    CAPTURE_FLOOR, CAPTURE_MIN_PDF_CHARS, RATCHET_KEYS, capture_ratio,
    attribution_collapse, chapter_is_ok, compare_codes, dominant_prefix,
    leading_code, numbering_gaps,
    ratchet, score_all, score_chapter, summarise,
)


class TestLeadingCode:
    def test_pulls_the_code_off_a_section_header(self):
        assert leading_code("B16 Inter-War Buildings") == "B16"
        assert leading_code("4.1.12 Roof details") == "4.1.12"
        assert leading_code("14A.2 Public Domain") == "14A.2"

    def test_null_and_blank_headers_return_None_not_a_crash(self):
        # 36 of 12,124 live rows carry a NULL section_header (measured 2026-09-12)
        # and this is called on every row.
        assert leading_code(None) is None
        assert leading_code("") is None
        assert leading_code("   ") is None

    def test_a_header_with_no_code_returns_None(self):
        assert leading_code("Introduction") is None


class TestCompareCodes:
    def test_absent_sections_are_INCOMPLETE(self):
        verdict, missing = compare_codes(
            {"B1", "B2", "B15", "B16", "F1"}, {"B1", "B2", "B16"})  # noqa: zone-codes  (DCP Part codes, not NSW zone codes)
        assert verdict == "INCOMPLETE"
        assert set(missing) == {"B15", "F1"}

    def test_everything_served_is_OK(self):
        verdict, missing = compare_codes({"B1", "B2"}, {"B1", "B2", "B3"})  # noqa: zone-codes  (DCP Part codes, not NSW zone codes)
        assert verdict == "OK" and missing == []

    def test_a_deeper_stored_code_covers_a_shallower_listed_one(self):
        # marrickville stores 4.1.12 where the contents lists 4.1.
        verdict, _ = compare_codes({"4.1", "4.2"}, {"4.1.12", "4.2.3"})
        assert verdict == "OK"

    def test_ashfield_prefix_mismatch_is_NOT_reported_as_missing(self):
        # The known false positive: contents says "10", we store "A10". Reporting
        # this as "15 of 15 sections missing" is the failure this exists to stop.
        listed = {str(i) for i in range(1, 16)}
        stored = {"A" + str(i) for i in range(1, 16)}
        verdict, missing = compare_codes(listed, stored)
        assert verdict == "OK", "missing=" + str(missing)

    def test_total_mismatch_on_a_big_chapter_is_VOCAB_MISMATCH_not_a_finding(self):
        listed = {"1.1", "1.2", "1.3", "2.1", "2.2", "2.3",
                  "3.1", "3.2", "3.3", "4.1", "4.2"}
        stored = {"part_12_signage", "part_13_trees", "part_15_contamination"}
        verdict, _ = compare_codes(listed, stored)
        assert verdict == "VOCAB_MISMATCH"

    def test_but_a_small_chapter_missing_everything_IS_reported(self):
        # Below SUSPICIOUS_MIN_CODES the vocabulary escape must not apply, or a
        # genuinely empty small chapter would be excused.
        verdict, missing = compare_codes({"1", "2", "3"}, {"99"})
        assert verdict == "INCOMPLETE" and len(missing) == 3

    def test_no_stored_codes_is_its_own_verdict(self):
        verdict, missing = compare_codes({"1", "2"}, set())
        assert verdict == "NO_STORED_CODES" and missing == ["1", "2"]

    def test_no_contents_is_its_own_verdict(self):
        verdict, _ = compare_codes(set(), {"1", "2"})
        assert verdict == "NO_CONTENTS"

    def test_dominant_prefix_needs_near_unanimity(self):
        assert dominant_prefix({"A1", "A2", "A3", "A4", "A5"}) == "A"
        assert dominant_prefix({"A1", "B2", "C3", "D4", "E5"}) is None  # noqa: zone-codes  (DCP Part codes, not NSW zone codes)


class TestNumberingGaps:
    def test_a_hole_is_found(self):
        verdict, gaps = numbering_gaps({"1.1", "1.2", "1.5"})
        assert verdict == "GAPS"
        assert any("3,4" in g["detail"] for g in gaps)

    def test_starting_late_is_found(self):
        # marrickville part4-s1 stores only 4.1.12.x and nothing before it.
        verdict, gaps = numbering_gaps({"4.1.12", "4.1.13"})
        assert verdict == "GAPS"
        assert any(g["kind"] == "starts_late" for g in gaps)

    def test_a_complete_run_has_no_gaps(self):
        verdict, gaps = numbering_gaps({"1", "2", "3", "4"})
        assert verdict == "NO_GAPS" and gaps == []

    def test_one_code_is_TOO_FEW_CODES_not_NO_GAPS(self):
        # One number can neither agree nor disagree with itself. A check that
        # cannot fail must not report a pass.
        assert numbering_gaps({"4.1.12"})[0] == "TOO_FEW_CODES"
        assert numbering_gaps(set())[0] == "TOO_FEW_CODES"

    def test_non_numeric_codes_do_not_raise(self):
        verdict, _ = numbering_gaps({"part_a", "intro", "preamble"})
        assert verdict == "TOO_FEW_CODES"

    def test_lettered_levels_are_kept_apart(self):
        # A1,A2 and B1,B2 are two complete runs, not one run with holes.
        assert numbering_gaps({"A1", "A2", "B1", "B2"})[0] == "NO_GAPS"  # noqa: zone-codes  (DCP Part codes, not NSW zone codes)

    def test_a_level_a_SIBLING_chapter_owns_is_not_judged(self):
        # THE FABRICATED-FINDING CASE. leichhardt/part-c-s1-general holds C1.x and
        # C6.x; C2-C5 live in other leichhardt chapters. Judged alone it reports
        # "holes 2,3,4,5" -- sections that exist, in a sibling. Measured
        # 2026-09-12: marrickville's top-level code 2 appears in 22 chapters,
        # canterbury_bankstown's 10 in 10. Without this the signal fabricates.
        own = {"C1.0", "C1.1", "C6.5"}
        verdict, gaps = numbering_gaps(own)
        assert verdict == "GAPS"                          # judged alone: a hole
        assert any(g["level"] == "C" and "2,3,4,5" in g["detail"] for g in gaps)

        siblings = {"C2.1", "C3.1", "C4.1", "C5.1"}  # noqa: zone-codes  (DCP Part codes, not NSW zone codes)
        verdict, gaps = numbering_gaps(own, siblings)
        # Level C is skipped because a sibling owns C2-C5. Level C1 is still this
        # chapter's own and is still judged -- sibling awareness suppresses the
        # fabricated finding WITHOUT silencing the signal everywhere.
        assert verdict == "NO_GAPS"
        assert not any(g["level"] == "C" for g in gaps)

    def test_a_level_this_chapter_owns_outright_is_still_judged(self):
        # The other direction: sibling awareness must not silence a real hole.
        own = {"2.10.1", "2.10.2", "2.10.9"}
        siblings = {"2.11.1", "2.12.1"}      # siblings own 2.11/2.12, not 2.10
        verdict, gaps = numbering_gaps(own, siblings)
        assert verdict == "GAPS"
        assert any("3,4,5" in g["detail"] for g in gaps)

    def test_shared_numbering_is_not_counted_as_a_signal_that_ran(self):
        # SHARED_NUMBERING means "could not judge", so it must not make a chapter
        # look measured or known-good on its own.
        # Every judgeable level is shared: C is the only level with two numbers,
        # and a sibling owns part of it.
        raw = {"council": "x", "chapter": "y", "live_rows": 5,
               "contents_status": "NO_CONTENTS", "listed_codes": [],
               "stored_codes": ["C1.0", "C6.5"], "stored_chars": 0,
               "pdf_text_chars": 10, "header": {"verdict": "NO_HEADER_TRUTH"}}
        s = score_chapter(raw, {"C2.1", "C3.1"})  # noqa: zone-codes  (DCP Part codes, not NSW zone codes)
        assert s["gap_verdict"] == "SHARED_NUMBERING"
        assert s["measured"] is False


class TestScoreAllSuppliesSiblings:
    def test_siblings_come_from_the_same_council_only(self):
        raw = [
            {"council": "leichhardt", "chapter": "c1", "live_rows": 5,
             "contents_status": "NO_CONTENTS", "listed_codes": [],
             "stored_codes": ["C1.0", "C6.5"], "stored_chars": 0,
             "pdf_text_chars": 10, "header": {"verdict": "NO_HEADER_TRUTH"}},
            {"council": "leichhardt", "chapter": "c2", "live_rows": 5,
             "contents_status": "NO_CONTENTS", "listed_codes": [],
             "stored_codes": ["C2.1", "C3.1", "C4.1", "C5.1"], "stored_chars": 0,  # noqa: zone-codes  (DCP Part codes, not NSW zone codes)
             "pdf_text_chars": 10, "header": {"verdict": "NO_HEADER_TRUTH"}},
            {"council": "waverley", "chapter": "w1", "live_rows": 5,
             "contents_status": "NO_CONTENTS", "listed_codes": [],
             "stored_codes": ["C9.1"], "stored_chars": 0,
             "pdf_text_chars": 10, "header": {"verdict": "NO_HEADER_TRUTH"}},
        ]
        scored = {c["chapter"]: c for c in score_all(raw)}
        # c1's "holes" at C2-C5 are held by its sibling c2 -> level C not judged.
        # waverley's C9.1 is a DIFFERENT council and must not count as a sibling.
        assert scored["c1"]["gap_verdict"] == "SHARED_NUMBERING"

    def test_a_chapter_does_not_count_as_its_own_sibling(self):
        # If own codes leaked into the sibling set, EVERY level would look shared
        # and signal 2 would never judge anything again -- a check that cannot
        # fail, which is the failure mode this whole file is about.
        raw = [{"council": "x", "chapter": "only", "live_rows": 5,
                "contents_status": "NO_CONTENTS", "listed_codes": [],
                "stored_codes": ["2.10.1", "2.10.2", "2.10.9"],
                "stored_chars": 0, "pdf_text_chars": 10,
                "header": {"verdict": "NO_HEADER_TRUTH"}}]
        assert score_all(raw)[0]["gap_verdict"] == "GAPS"


class TestCaptureRatio:
    def test_a_hollow_chapter_is_flagged(self):
        verdict, ratio = capture_ratio(stored_chars=500, pdf_text_chars=200_000)
        assert verdict == "HOLLOW"
        assert ratio < CAPTURE_FLOOR

    def test_a_captured_chapter_is_not(self):
        verdict, _ = capture_ratio(stored_chars=40_000, pdf_text_chars=200_000)
        assert verdict == "CAPTURED"

    def test_a_document_with_almost_no_text_is_NO_TEXT_not_HOLLOW(self):
        # A cover page or a map. Calling it hollow would be a finding about a
        # document that has nothing to extract.
        verdict, ratio = capture_ratio(0, CAPTURE_MIN_PDF_CHARS - 1)
        assert verdict == "NO_TEXT" and ratio is None

    def test_zero_stored_chars_on_a_real_document_is_NO_ROWS(self):
        verdict, ratio = capture_ratio(0, 100_000)
        assert verdict == "NO_ROWS" and ratio == 0.0

    def test_storing_more_than_the_document_holds_is_its_own_anomaly(self):
        # marrickville/part2-s10-parking: 100,968 stored chars against 50,860 in
        # the PDF, 54 rows, all distinct text and distinct refs -- so not simple
        # duplication. "We stored plenty" must not read as "we stored the right
        # thing".
        verdict, ratio = capture_ratio(100_968, 50_860)
        assert verdict == "OVER_CAPTURED"
        assert ratio > 1

    def test_a_slight_overshoot_is_still_normal(self):
        # Some readers emit table text twice; the threshold sits above that noise
        # rather than at exactly 1.0, or every table-heavy chapter would flag.
        assert capture_ratio(105_000, 100_000)[0] == "CAPTURED"


class TestAttributionCollapse:
    """Marrickville's dominant cause, and invisible to every other signal."""

    def test_the_stormwater_shape_is_COLLAPSED(self):
        # marrickville/part2-s25-stormwater: 40 rows, 19 listed sections, and
        # every row stamped "2.25 Stormwater Management" with a control marker.
        # The 19 sub-sections are collapsed into their parent and none can be
        # retrieved -- while the text itself is all present (capture 1.0).
        listed = ["2.25.1", "2.25.2", "2.25.3"] + [
            "2.25.3." + str(i) for i in range(1, 17)]
        verdict, ratio = attribution_collapse(listed, {"2.25"}, live_rows=40)
        assert verdict == "COLLAPSED"
        assert ratio < 0.1

    def test_a_healthy_chapter_is_ATTRIBUTED(self):
        # marrickville/part2-s10-parking: 19 listed, 17 distinct stored.
        listed = [str(i) for i in range(1, 20)]
        stored = {str(i) for i in range(1, 18)}
        verdict, ratio = attribution_collapse(listed, stored, live_rows=54)
        assert verdict == "ATTRIBUTED" and ratio > 0.8

    def test_no_parseable_codes_is_NOT_reported_as_collapse(self):
        # woollahra (24 chapters, 547 rows) carries no parseable code at all.
        # That is a different defect, and folding it in reported 98 collapsed
        # chapters where there are 59.
        listed = [str(i) for i in range(1, 20)]
        assert attribution_collapse(listed, set(), live_rows=40)[0] == "NO_STORED_CODES"

    def test_a_chapter_too_small_to_judge_says_so(self):
        # Three listed sections and one stored code is not evidence of collapse.
        assert attribution_collapse(["1", "2", "3"], {"1"}, 40)[0] == "TOO_FEW_LISTED"
        assert attribution_collapse([str(i) for i in range(9)], {"1"}, 2)[0] == "TOO_FEW_ROWS"

    def test_the_verdict_is_not_constant(self):
        # Mutation guard: a function returning one value always would pass the
        # positive or the negative above, never both.
        listed = [str(i) for i in range(1, 21)]
        assert attribution_collapse(listed, {"1"}, 40)[0] == "COLLAPSED"
        assert attribution_collapse(listed, set(listed), 40)[0] == "ATTRIBUTED"


class TestScoringIsThreeStateNotTwo:
    def _raw(self, **kw):
        base = {"council": "x", "chapter": "y", "live_rows": 10,
                "contents_status": "READ", "listed_codes": ["1", "2"],
                "stored_codes": ["1", "2"], "stored_chars": 40_000,
                "pdf_text_chars": 200_000, "pdf_pages": 50,
                "header": {"verdict": "CONSISTENT", "rows_checked": 20,
                           "rows_disagree": 0, "examples": []}}
        base.update(kw)
        return base

    def test_a_clean_chapter_is_measured_with_no_findings(self):
        s = score_chapter(self._raw())
        assert s["measured"] is True and s["findings"] == []
        assert s["signals_run"] == 4
        assert chapter_is_ok(s)

    def test_an_unreadable_contents_page_is_NOT_MEASURED_by_signal_one(self):
        s = score_chapter(self._raw(contents_status="UNREADABLE", listed_codes=[]))
        assert s["contents_verdict"] == "NOT_MEASURED:UNREADABLE"
        # but the other signals still ran, so the chapter is not unknown
        assert s["measured"] is True
        assert s["signals_run"] == 3

    def test_a_chapter_no_signal_could_judge_is_UNMEASURED(self):
        # No contents page, one section code, no header truth, no text. Every
        # signal abstains -- and the chapter must read as unknown, not clean.
        s = score_chapter(self._raw(
            contents_status="NO_CONTENTS", listed_codes=[],
            stored_codes=["4.1.12"], stored_chars=0, pdf_text_chars=10,
            header={"verdict": "NO_HEADER_TRUTH"}))
        assert s["measured"] is False
        assert s["signals_run"] == 0
        assert not chapter_is_ok(s)

    def test_an_unmeasured_chapter_is_never_OK_even_with_no_findings(self):
        s = score_chapter(self._raw(
            contents_status="NO_CONTENTS", listed_codes=[],
            stored_codes=["4.1.12"], stored_chars=0, pdf_text_chars=10,
            header={"verdict": "NO_HEADER_TRUTH"}))
        assert s["findings"] == []
        assert not chapter_is_ok(s), "silence from every signal read as agreement"

    def test_a_chapter_with_no_rows_is_never_OK(self):
        s = score_chapter(self._raw(live_rows=0, stored_codes=[], stored_chars=0))
        assert not chapter_is_ok(s)

    def test_a_chapter_serving_nothing_is_a_FINDING_not_a_quiet_pass(self):
        s = score_chapter(self._raw(live_rows=0, stored_codes=[], stored_chars=0))
        assert s["contents_verdict"] == "NO_ROWS"
        assert any(f.startswith("serves_nothing") for f in s["findings"])

    def test_rows_with_no_parseable_codes_are_NOT_MEASURED_not_OK(self):
        # THE WOOLLAHRA CASE, and the bug this test exists for. 26 of woollahra's
        # 27 chapters serve real rows -- 226 in chapter-e2 alone -- and not one
        # section_header begins with a code this comparison can read. An earlier
        # draft returned NO_ROWS, counted it as a signal that ran and found
        # nothing, and scored 25 woollahra chapters OK: an inability to judge
        # reported as a pass, which is the exact defect being repaired.
        s = score_chapter(self._raw(live_rows=226, stored_codes=[],
                                    listed_codes=["1", "2", "3", "4"],
                                    header={"verdict": "NO_HEADER_TRUTH"}))
        assert s["contents_verdict"] == "NOT_MEASURED:NO_STORED_CODES"
        assert not chapter_is_ok(s), "unkeyable rows scored as known-good"

    def test_unkeyable_rows_do_not_report_a_missing_count(self):
        # Reporting "4 of 4 sections missing" for a chapter we simply cannot key
        # would be a fabricated finding -- the other half of the same error.
        s = score_chapter(self._raw(live_rows=226, stored_codes=[],
                                    listed_codes=["1", "2", "3", "4"]))
        assert s["n_missing"] == 0 and s["missing_sample"] == []

    def test_titles_only_is_reason_coded_distinctly_from_unreadable(self):
        # Only UNREADABLE is a defect in the parser and only it should shrink as
        # the parser improves. Collapsing them would hide that.
        a = score_chapter(self._raw(contents_status="TITLES_ONLY", listed_codes=[]))
        b = score_chapter(self._raw(contents_status="UNREADABLE", listed_codes=[]))
        assert a["contents_verdict"] != b["contents_verdict"]

    def test_collapsed_attribution_becomes_a_finding_and_blocks_OK(self):
        listed = [str(i) for i in range(1, 21)]
        s = score_chapter(self._raw(listed_codes=listed, stored_codes=["1"],
                                    live_rows=40))
        assert s["attribution_verdict"] == "COLLAPSED"
        assert any(f.startswith("attribution_collapsed") for f in s["findings"])
        assert not chapter_is_ok(s)

    def test_mislabelled_rows_become_a_finding(self):
        s = score_chapter(self._raw(header={
            "verdict": "MISLABELLED", "rows_checked": 263, "rows_disagree": 54,
            "examples": []}))
        assert any(f.startswith("mislabelled:54/263") for f in s["findings"])
        assert not chapter_is_ok(s)


class TestSummariseAndRatchet:
    def _scored(self, council, n_ok, n_incomplete, n_unmeasured):
        out = []
        for _ in range(n_ok):
            out.append({"council": council, "measured": True, "findings": [],
                        "live_rows": 5, "contents_verdict": "OK",
                        "gap_verdict": "NO_GAPS", "header_verdict": "CONSISTENT",
                        "capture_verdict": "CAPTURED", "n_missing": 0,
                        "header_rows_disagree": 0,
                        "attribution_verdict": "ATTRIBUTED"})
        for _ in range(n_incomplete):
            out.append({"council": council, "measured": True,
                        "findings": ["contents:2/5"], "live_rows": 5,
                        "contents_verdict": "INCOMPLETE", "gap_verdict": "NO_GAPS",
                        "header_verdict": "CONSISTENT", "capture_verdict": "CAPTURED",
                        "n_missing": 2, "header_rows_disagree": 0,
                        "attribution_verdict": "ATTRIBUTED"})
        for _ in range(n_unmeasured):
            out.append({"council": council, "measured": False, "findings": [],
                        "live_rows": 0,
                        "contents_verdict": "NOT_MEASURED:NO_CONTENTS",
                        "gap_verdict": "TOO_FEW_CODES",
                        "header_verdict": "NO_HEADER_TRUTH",
                        "capture_verdict": "NO_TEXT", "n_missing": 0,
                        "header_rows_disagree": 0,
                        "attribution_verdict": "TOO_FEW_LISTED"})
        return out

    def test_summarise_counts_not_ok_and_unmeasured(self):
        s = summarise(self._scored("waverley", n_ok=3, n_incomplete=2,
                                   n_unmeasured=1))
        c = s["per_council"]["waverley"]
        assert c["chapters"] == 6 and c["OK"] == 3
        assert c["NOT_OK"] == 3 and c["UNMEASURED"] == 1

    def test_a_rise_in_NOT_OK_is_a_regression(self):
        base = {"ratchet": {"per_council": {"waverley": {"NOT_OK": 2,
                                                         "UNMEASURED": 1}}}}
        now = summarise(self._scored("waverley", 2, 3, 1))   # NOT_OK 4
        reg, imp, nb = ratchet(now, base)
        assert any(r["key"] == "NOT_OK" and r["now"] == 4 for r in reg)

    def test_a_fall_is_an_improvement_and_does_not_fail(self):
        base = {"ratchet": {"per_council": {"waverley": {"NOT_OK": 5,
                                                         "UNMEASURED": 3}}}}
        now = summarise(self._scored("waverley", 5, 1, 0))   # NOT_OK 1
        reg, imp, nb = ratchet(now, base)
        assert not reg and imp

    def test_an_empty_baseline_is_NO_BASELINE_for_every_key_not_a_pass(self):
        # The first four-signal run. Nothing to compare against, and that must
        # not read as "fine" -- the floor is being set, not cleared.
        now = summarise(self._scored("waverley", 1, 1, 1))
        reg, imp, nb = ratchet(now, {"ratchet": {"per_council": {}}})
        assert not reg and not imp
        assert {r["key"] for r in nb} == set(RATCHET_KEYS)

    def test_a_council_absent_from_the_baseline_is_NO_BASELINE(self):
        base = {"ratchet": {"per_council": {"waverley": {"NOT_OK": 1,
                                                         "UNMEASURED": 0}}}}
        now = summarise(self._scored("newcouncil", 0, 4, 0))
        reg, imp, nb = ratchet(now, base)
        assert not reg and len(nb) == len(RATCHET_KEYS)


class TestMutationResistance:
    """Would a gutted implementation still pass? These say no."""

    def test_compare_codes_does_not_always_return_OK(self):
        assert compare_codes({"1", "2", "3"}, {"1"})[0] == "INCOMPLETE"

    def test_compare_codes_does_not_always_return_INCOMPLETE(self):
        assert compare_codes({"1", "2"}, {"1", "2"})[0] == "OK"

    def test_numbering_gaps_does_not_always_find_gaps(self):
        assert numbering_gaps({"1", "2", "3"})[0] == "NO_GAPS"

    def test_numbering_gaps_is_not_a_no_op(self):
        assert numbering_gaps({"1", "5"})[0] == "GAPS"

    def test_chapter_is_ok_is_not_constant(self):
        good = {"measured": True, "findings": [], "live_rows": 1,
                "contents_verdict": "OK"}
        bad = {"measured": True, "findings": ["contents:1/2"], "live_rows": 1,
               "contents_verdict": "INCOMPLETE"}
        assert chapter_is_ok(good) and not chapter_is_ok(bad)

    def test_other_signals_alone_do_not_make_a_chapter_known_good(self):
        # Signals 2-4 are defect detectors, not completeness verifiers. A chapter
        # they are all silent about, that signal 1 could not judge, is UNKNOWN.
        quiet = {"measured": True, "findings": [], "live_rows": 100,
                 "contents_verdict": "NOT_MEASURED:NO_STORED_CODES"}
        assert not chapter_is_ok(quiet)
