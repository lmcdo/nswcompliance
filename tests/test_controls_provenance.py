"""Every dcp_setback_controls row must carry a provenance state — and the check
that asserts it must be able to go red.

WHY THESE TESTS LOOK LIKE THIS
------------------------------
The failure this guards against is not a wrong number, it is a row nobody can
account for. So the tests that matter most are the ones proving the classifier
REACHES the failing state: a check which cannot fail is not a check, which is the
lesson DQ-30's invalid "0% drift" self-comparison taught.

Mutation notes — each of these breaks a plausible wrong implementation:
  * ``classify_rows`` returning [] fails test_every_row_gets_exactly_one_state.
  * Treating a missing source_text as traceable fails the unverifiable tests.
  * Grepping source instead of parsing it fails test_a_literal_in_a_comment_...
  * Trusting extraction_method fails test_a_manual_label_does_not_block_...
"""
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.validate_controls_provenance import (  # noqa: E402
    MIN_LITERAL_CHARS,
    STATE_REPRODUCIBLE,
    STATE_TRACEABLE,
    STATE_UNVERIFIABLE,
    STATES,
    classify_rows,
    harvest_committed_literals,
    label_reality_mismatches,
)

LONG = "Minimum 35% of site area as landscaped area (Ashfield DCP 2016 DS18.5)"
assert len(LONG) >= MIN_LITERAL_CHARS, "fixture must exceed the attribution floor"


class TestTheCheckCanFail:
    """The whole point. If none of these can go red, the gate is decorative."""

    def test_a_row_with_no_source_text_and_no_ref_is_unverifiable(self):
        out = classify_rows([{"id": 1, "source_text": None, "section_ref": None}], {})
        assert out[0]["state"] == STATE_UNVERIFIABLE
        assert "source_text" in out[0]["evidence"]

    def test_a_row_with_a_ref_but_no_source_text_is_unverifiable(self):
        """A clause number alone cannot be re-checked — there is nothing to compare."""
        out = classify_rows([{"id": 2, "source_text": "", "section_ref": "part-c-s1"}], {})
        assert out[0]["state"] == STATE_UNVERIFIABLE

    def test_a_row_with_source_text_but_no_ref_is_unverifiable(self):
        out = classify_rows([{"id": 3, "source_text": LONG, "section_ref": None}], {})
        assert out[0]["state"] == STATE_UNVERIFIABLE

    def test_whitespace_is_not_provenance(self):
        """'   ' is falsy-in-spirit but truthy in Python — the trap this closes."""
        out = classify_rows(
            [{"id": 4, "source_text": "   ", "section_ref": "\t\n"}], {})
        assert out[0]["state"] == STATE_UNVERIFIABLE


class TestTheThreeStates:
    def test_a_committed_literal_makes_a_row_reproducible(self):
        out = classify_rows([{"id": 5, "source_text": LONG, "section_ref": None}],
                            {LONG: {"scripts/insert_inner_west_landscaping.py"}})
        assert out[0]["state"] == STATE_REPRODUCIBLE
        assert out[0]["evidence"] == "scripts/insert_inner_west_landscaping.py"

    def test_source_text_plus_ref_without_a_literal_is_traceable(self):
        out = classify_rows(
            [{"id": 6, "source_text": LONG, "section_ref": "f-dwelling-houses"}], {})
        assert out[0]["state"] == STATE_TRACEABLE
        assert out[0]["evidence"] == "f-dwelling-houses"

    def test_reproducible_outranks_traceable(self):
        """A row with both must report the stronger state, not the first one matched."""
        out = classify_rows([{"id": 7, "source_text": LONG, "section_ref": "x-1"}],
                            {LONG: {"scripts/insert_solar_access_hours.py"}})
        assert out[0]["state"] == STATE_REPRODUCIBLE

    def test_surrounding_whitespace_still_matches_a_literal(self):
        out = classify_rows([{"id": 8, "source_text": f"  {LONG}  ",
                              "section_ref": None}], {LONG: {"scripts/x.py"}})
        assert out[0]["state"] == STATE_REPRODUCIBLE

    def test_every_row_gets_exactly_one_state(self):
        rows = [
            {"id": 9, "source_text": LONG, "section_ref": "a"},
            {"id": 10, "source_text": None, "section_ref": None},
            {"id": 11, "source_text": LONG, "section_ref": None},
        ]
        out = classify_rows(rows, {LONG: {"scripts/x.py"}})
        assert len(out) == len(rows)
        assert [r["id"] for r in out] == [9, 10, 11]
        assert all(r["state"] in STATES for r in out)


class TestTheLabelIsNeverTrusted:
    """extraction_method is what a writer claimed; the state is what can be proved."""

    def test_a_manual_label_does_not_block_reproducible(self):
        out = classify_rows(
            [{"id": 12, "source_text": LONG, "section_ref": None,
              "extraction_method": "manual"}], {LONG: {"scripts/x.py"}})
        assert out[0]["state"] == STATE_REPRODUCIBLE

    def test_a_pipeline_label_does_not_confer_reproducible(self):
        out = classify_rows(
            [{"id": 13, "source_text": LONG, "section_ref": "a",
              "extraction_method": "text_extraction"}], {})
        assert out[0]["state"] == STATE_TRACEABLE

    def test_mismatches_are_counted_in_both_directions(self):
        classified = [
            {"claimed_method": "text_extraction", "state": STATE_TRACEABLE},
            {"claimed_method": "mistral_ocr", "state": STATE_UNVERIFIABLE},
            {"claimed_method": "manual", "state": STATE_REPRODUCIBLE},
            {"claimed_method": "manual_curation", "state": STATE_REPRODUCIBLE},
            {"claimed_method": "text_extraction", "state": STATE_REPRODUCIBLE},
        ]
        counts = label_reality_mismatches(classified)
        assert counts["labelled_pipeline_but_no_committed_literal"] == 2
        assert counts["labelled_manual_but_a_script_regenerates_it"] == 2

    def test_a_null_method_is_not_a_mismatch(self):
        assert label_reality_mismatches(
            [{"claimed_method": None, "state": STATE_TRACEABLE}]) == {}


class TestHarvestUsesTheASTNotTheText:
    """Attribution must come from real string literals, never from prose."""

    def _write(self, tmp_path: Path, name: str, body: str) -> Path:
        (tmp_path / "scripts").mkdir(exist_ok=True)
        path = tmp_path / "scripts" / name
        path.write_text(textwrap.dedent(body), encoding="utf-8")
        return path

    def test_a_real_literal_is_harvested(self, tmp_path):
        self._write(tmp_path, "insert_probe.py", f'''
            """writes dcp_setback_controls"""
            ROWS = [{{"source_text": "{LONG}"}}]
        ''')
        got = harvest_committed_literals(str(tmp_path))
        assert LONG in got and "scripts/insert_probe.py" in got[LONG]

    def test_a_literal_in_a_comment_is_not_harvested(self, tmp_path):
        """A regex over source would attribute this row to a file that only
        mentions the text — inventing provenance out of a comment."""
        self._write(tmp_path, "insert_probe.py", f'''
            """writes dcp_setback_controls"""
            # {LONG}
            ROWS = []
        ''')
        assert LONG not in harvest_committed_literals(str(tmp_path))

    def test_a_file_that_does_not_write_the_table_is_skipped(self, tmp_path):
        self._write(tmp_path, "insert_probe.py", f'''
            """unrelated helper"""
            ROWS = [{{"source_text": "{LONG}"}}]
        ''')
        assert LONG not in harvest_committed_literals(str(tmp_path))

    def test_a_short_literal_is_below_the_attribution_floor(self, tmp_path):
        short = "Table 4"
        assert len(short) < MIN_LITERAL_CHARS
        self._write(tmp_path, "insert_probe.py", f'''
            """writes dcp_setback_controls"""
            ROWS = [{{"section_ref": "{short}"}}]
        ''')
        assert short not in harvest_committed_literals(str(tmp_path))

    def test_a_syntax_error_does_not_abort_the_harvest(self, tmp_path):
        """One unparseable file must not silently zero out attribution for all."""
        self._write(tmp_path, "insert_broken.py", '''
            """writes dcp_setback_controls"""
            def oops(  :
        ''')
        self._write(tmp_path, "insert_ok.py", f'''
            """writes dcp_setback_controls"""
            ROWS = [{{"source_text": "{LONG}"}}]
        ''')
        assert LONG in harvest_committed_literals(str(tmp_path))

    def test_an_empty_tree_harvests_nothing(self, tmp_path):
        """Drives the exit-2 path: no writers found means nothing was verified."""
        assert harvest_committed_literals(str(tmp_path)) == {}
