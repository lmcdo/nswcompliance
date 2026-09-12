"""Recovering a section code from ref_number — and refusing to invent one.

The positives are real (section_header, ref_number) pairs from live rows. The
refusals are the load-bearing half: this writes a REGULATORY REFERENCE onto a
provision, and a wrong one is worse than a missing one. .claude/rules/
regulatory-data.md is explicit that planning data is never guessed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dcp_section_code import (  # noqa: E402
    ref_tail, repaired_header, section_code,
)


class TestRefTail:
    def test_strips_the_document_id_prefix(self):
        # The real shape, from the corpus: the document id, then the segment
        # that carries the code.
        assert ref_tail("Sydney_DCP_2012__section_1_introduction__1_1",
                        "Sydney_DCP_2012") == "section_1_introduction"
        assert ref_tail("WDCP2015_E1_4_2", "WDCP2015") == "E1_4_2"

    def test_a_bare_ref_is_returned_whole(self):
        assert ref_tail("E1_4_2", None) == "E1_4_2"

    def test_null_ref_is_empty_not_a_crash(self):
        assert ref_tail(None, None) == ""
        assert ref_tail(None, "doc") == ""


class TestSectionCode:
    def test_real_shapes_recover(self):
        # Each pair observed on a live row 2026-09-12.
        assert section_code("E1_4_2", None) == "E1.4.2"     # woollahra
        assert section_code("4a_1", None) == "4a.1"         # ku_ring_gai
        assert section_code("1_1", None) == "1.1"           # parramatta
        assert section_code("D18", None) == "D18"           # northern_beaches

    def test_preamble_and_intro_are_NOT_given_a_code(self):
        # 291 rows are legitimately not a numbered section. Stamping one would
        # fabricate a reference to a clause that does not exist.
        for seg in ("preamble", "intro", "introduction", "cover", "contents",
                    "Document_Information"):
            assert section_code(seg, None) is None, seg

    def test_an_unparseable_ref_yields_None(self):
        # ashfield's 747 rows: the tail is not a code either. Reported, not guessed.
        assert section_code("2__part_10_introduction_of", None) is None
        assert section_code("some-slug-name", None) is None
        assert section_code("", None) is None
        assert section_code(None, None) is None

    def test_a_STRUCTURELESS_number_is_refused(self):
        # Measured 2026-09-12: 69 of 2,328 candidate repairs produce a bare
        # digit, and every sampled one came from body text, not a heading --
        # "December 2025 31 December 2026" -> 31, "STC (Sound Transmission
        # Class) in accordance" -> 45. Stamping those fabricates a reference to
        # a clause that does not exist.
        for seg in ("7", "21", "31", "45", "123"):
            assert section_code(seg, None) is None, seg

    def test_but_structure_of_any_kind_is_accepted(self):
        # Guards the other direction: refusing everything would make the repair
        # a no-op that still reports success.
        assert section_code("D18", None) == "D18"      # a letter
        assert section_code("1_1", None) == "1.1"      # a dotted part
        assert section_code("4a_1", None) == "4a.1"    # both


class TestRepairedHeader:
    def test_it_prepends_the_code_to_the_existing_title(self):
        assert repaired_header("Residential parking generation rates",
                               "E1_4_2", None) == "E1.4.2 Residential parking generation rates"

    def test_a_header_that_ALREADY_has_a_code_is_left_alone(self):
        # THE IMPORTANT REFUSAL. A stored code came from the document; a
        # recovered one is an inference. This must never overwrite the first
        # with the second.
        assert repaired_header("B16 Inter-War Buildings", "B17_1", None) is None
        assert repaired_header("2.25 Stormwater Management", "2_25_C11", None) is None
        assert repaired_header("4a.1 Local Character", "9z_9", None) is None

    def test_a_blank_header_still_gets_the_code_alone(self):
        assert repaired_header("", "E1_4_2", None) == "E1.4.2"
        assert repaired_header(None, "E1_4_2", None) == "E1.4.2"

    def test_no_recoverable_code_means_no_change(self):
        assert repaired_header("Some title", "preamble", None) is None
        assert repaired_header("Some title", None, None) is None

    def test_the_marrickville_collapsed_shape_is_NOT_repaired_here(self):
        # marrickville's rows already carry a code -- the WRONG one, the collapsed
        # parent. ref_number holds that same collapsed code, so there is nothing
        # to recover and this script correctly declines. Only a re-extraction
        # fixes it, and pretending otherwise would paper over the real defect.
        assert repaired_header("2.25 Stormwater Management -- C11 Redirection",
                               "2_25_C11", None) is None


class TestMutationResistance:
    def test_it_does_not_always_return_None(self):
        assert repaired_header("Title", "E1_4_2", None) is not None

    def test_it_does_not_always_return_a_change(self):
        assert repaired_header("B16 Inter-War Buildings", "B17_1", None) is None

    def test_the_code_is_actually_transcribed_not_fabricated(self):
        out = repaired_header("Tandem parking", "E1_9_3", None)
        assert out.startswith("E1.9.3 ")
        assert "Tandem parking" in out
