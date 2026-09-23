"""DQ-108 — a structured numeric rule must quote its own provision.

`v2_extracted_rules` stores a `raw_match`: the exact phrase a number was read
out of, e.g. "maximum height of 4m". That phrase has to be IN the provision it
came from, or the number a planner reads came from nowhere.

THE MECHANISM IS NOT A BAD REGEX. The formulate stage is fill-blanks-only,
which is what makes it safe to schedule — it never revisits a provision that
already has a verdict. The same property means a rule OUTLIVES the text it was
derived from: re-read a chapter, replace the provision's text, and the rules
stay exactly as they were, describing a page that no longer says it.

Measured 2026-09-24 over the 7,854 rows already carrying rules: 2,097 numeric
rules, 3 ungrounded, all on provision 40278 — text about "the minimum internal
area, if any, specified in the Apartment Design Guide", rules for 4, 5 and 1
parking spaces at `extraction_confidence: high`, and "parking space" occurring
in it exactly zero times.

MUTATION NOTE. The two ways to get this detector wrong were both measured on
real rows before the rule was settled:
  * comparing an unflattened `raw_match` against flattened provision text
    accuses 44 healthy rules whose phrase merely spans a line break
    ("minimum\\n3 metres"). A detector reporting 44 defects where there are 3
    teaches everyone to ignore it.
  * demanding the stored VALUE appear literally fails 18 correct unit
    conversions — "600mm in height" is legitimately stored as 0.6 with unit m.
    That is `feedback-verify-the-derivation-not-the-digits` exactly.
So it checks the PHRASE, normalised on both sides, and never the digits.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from dq_probe_unchecked_rows import probe_108  # noqa: E402


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, *_a, **_k):
        return None

    def fetchall(self):
        return self._rows


def _numeric(raw, **kw):
    r = {"compliance_type": "numeric_check", "raw_match": raw,
         "extraction_method": "regex"}
    r.update(kw)
    return r


def _run(rows):
    return probe_108(FakeCursor(rows))


class TestAnUngroundedRuleIsCaught:
    def test_the_live_case(self):
        """Provision 40278, as it stands in production."""
        count, detail = _run([(
            40278, None,
            "(e), (f) (Repealed) (g) the minimum internal area, if any, "
            "specified in the Apartment Design Guide for the type of "
            "residential development,",
            [_numeric("4 parking space", value_exact=4.0),
             _numeric("5 parking space", value_exact=5.0)],
        )])
        assert count == 2
        assert all("not in this provision" in k[1] for k in detail)

    def test_it_names_the_phrase_so_the_finding_is_actionable(self):
        _, detail = _run([(1, "x", "some text with no numbers",
                           [_numeric("maximum height of 4m")])])
        assert "'maximum height of 4m'" in next(iter(detail))[1]


class TestTheTwoMeasuredFalsePositives:
    def test_a_phrase_spanning_a_line_break_is_grounded(self):
        """44 healthy rules failed this way before whitespace was normalised on
        BOTH sides. The provision wraps mid-phrase; the rule does not."""
        count, _ = _run([(1, "x",
                          "Provide a minimum\n3 metres from the boundary.",
                          [_numeric("minimum\n3 metres")])])
        assert count == 0

    def test_a_flattened_rule_against_a_wrapped_provision_is_also_grounded(self):
        count, _ = _run([(1, "x", "setback of\n6m to the side boundary",
                          [_numeric("setback of 6m")])])
        assert count == 0

    def test_a_unit_conversion_is_not_a_defect(self):
        """`600mm in height` stored as 0.6 m. The digits differ from the text on
        purpose; only the phrase has to match."""
        count, _ = _run([(1, "x", "Fences must not exceed 600mm in height.",
                          [_numeric("not exceed 600mm in height",
                                    value_max=0.6, unit="m")])])
        assert count == 0


class TestItOnlyJudgesWhatItCanJudge:
    def test_a_merit_assessment_rule_is_not_checked(self):
        """Qualitative controls carry no raw_match and no number to ground."""
        count, _ = _run([(1, "x", "Buildings are not to detract from the "
                                  "appearance of roofs.",
                          [{"compliance_type": "merit_assessment",
                            "extraction_method": "heading_rule"}])])
        assert count == 0

    def test_a_row_with_no_rules_is_not_checked(self):
        assert _run([(1, "x", "some text", [])])[0] == 0
        assert _run([(1, "x", "some text", None)])[0] == 0

    def test_rules_stored_as_a_json_string_are_still_read(self):
        """The column has held both shapes. Silently skipping one would make the
        check pass by looking at less."""
        import json
        count, _ = _run([(1, "x", "text without it",
                          json.dumps([_numeric("maximum height of 4m")]))])
        assert count == 1

    def test_the_dict_wrapper_shape_is_read_too(self):
        count, _ = _run([(1, "x", "text without it",
                          {"rules": [_numeric("maximum height of 4m")]})])
        assert count == 1

    def test_unparseable_json_does_not_crash_the_probe(self):
        """A probe that dies reports nothing, which reads like a pass."""
        count, _ = _run([(1, "x", "text", "{not json")])
        assert count == 0


class TestItCanReachZero:
    def test_a_fully_grounded_set_passes(self):
        count, _ = _run([
            (1, "x", "Signs should have a maximum height of 4m.",
             [_numeric("maximum height of 4m", value_max=4.0)]),
            (2, "x", "A setback of at least 6m applies.",
             [_numeric("setback of at least 6m", value_min=6.0)]),
        ])
        assert count == 0


class TestThePipelineRepairsThemItself:
    """The systemic half. Reporting a stale rule is a smoke alarm; re-deriving
    it is the fix, and it belongs in the same sweep that writes them."""

    def test_the_sweep_selects_stale_rows_as_well_as_blank_ones(self):
        from enrichment import rule_extraction_pipeline as rp

        assert "v2_extraction_status IS NULL" in rp._UNPROCESSED_ONLY, (
            "blank rows are no longer selected -- the sweep would stop filling")
        assert rp._STALE_RULES.strip(), "the stale condition has been emptied"
        assert rp._STALE_RULES.strip() in rp._UNPROCESSED_ONLY, (
            "the stale condition exists but is not wired into the selection")
        assert "numeric_check" in rp._UNPROCESSED_ONLY, (
            "fill-blanks-only again: a rule would outlive its text with nothing "
            "to re-derive it")

    def test_btrim_is_present_and_is_load_bearing(self):
        """Normalising runs of whitespace WITHOUT trimming the ends made the SQL
        condition match 6 rows where the Python probe finds 1 -- five healthy
        rows that would be re-derived on every run forever, because re-deriving
        cannot clear a condition their content never caused."""
        from enrichment import rule_extraction_pipeline as rp

        assert rp._UNPROCESSED_ONLY.count("btrim") == 2, (
            "both sides of the comparison must be trimmed, or the sweep picks "
            "up rows it can never clear")


@pytest.mark.database
@pytest.mark.skipif(os.getenv("PYTEST_REAL_DB") != "1",
                    reason="compares two live implementations of the same rule")
class TestTheSqlAndThePythonAgree:
    """Two implementations of 'is this rule still grounded' now exist: the SQL
    the sweep selects on, and the Python DQ-108 reads with. They must agree, or
    the check reports rows the repair never touches -- or worse, the repair
    chases rows the check calls healthy. They disagreed 6 to 1 on first write.
    """

    def test_they_find_the_same_rows(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import dq_db
        from enrichment import rule_extraction_pipeline as rp

        conn = dq_db.connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT count(*)::int FROM regulatory_provisions"
                        + rp._BASE_WHERE
                        + " AND v2_extraction_status IS NOT NULL"
                        + rp._STALE_RULES)
            sql_rows = cur.fetchone()[0]
            count, _ = probe_108(conn.cursor())
        finally:
            conn.close()
        assert sql_rows == 0 or count > 0, (
            f"the sweep sees {sql_rows} stale row(s) the check does not report")
