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
