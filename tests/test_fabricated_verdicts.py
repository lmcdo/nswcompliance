"""A verdict must be backed by data the emitter actually has.

DQ-36. The provisions PDF printed, for every property:

    Transport Oriented Development: ✗ Not applicable - Property not within 400m
    of metro station or 800m of strategic centre

The component receives no TOD data, so nothing could ever have changed that line.
This is not a data-quality bug — it is a conclusion that was never computed, which
is the one failure a retrieval system does not have.

Two things are pinned here:
  1. the lint that finds the class (including against its own founding case), and
  2. the worst live instance the sweep turned up — a PostGIS outage rendering as
     "No constraints identified for this property" on a paid conveyancing report.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lint_fabricated_verdicts import (  # noqa: E402
    _HONEST,
    _SITE_CLAIM,
    _VERDICT,
    scan_file,
)


def _write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


class TestFindsTheFoundingCase:
    """If it cannot catch DQ-36 itself, it is worthless."""

    def test_the_actual_tod_line_is_fabricated(self, tmp_path):
        p = _write(tmp_path, "C.tsx", """
export function C() {
  return (
    <View>
      <Text style={styles.tableCellValue}>✗ Not applicable - Property not within 400m of metro station or 800m of strategic centre</Text>
    </View>
  );
}
""")
        states = [f["state"] for f in scan_file(p)]
        assert "FABRICATED" in states

    def test_a_verdict_computed_from_data_is_not_flagged(self, tmp_path):
        p = _write(tmp_path, "D.tsx", """
export function D({ inCatchment }) {
  return <Text>{inCatchment ? `Within a TOD catchment` : `Outside the TOD catchment for this property`}</Text>;
}
""")
        assert [f for f in scan_file(p) if f["state"] == "FABRICATED"] == []

    def test_an_honest_not_assessed_is_never_a_finding(self, tmp_path):
        p = _write(tmp_path, "E.tsx", """
<Text>Not assessed in this report - confirm this property against the Portal maps</Text>
""")
        assert scan_file(p) == []


class TestDoesNotCryWolf:
    def test_a_scope_statement_about_a_rule_is_not_a_site_claim(self, tmp_path):
        # "Applies to development over $30M CIV" describes the rule, not the site.
        p = _write(tmp_path, "F.tsx", """
<Text>Depends on the proposal - Applies to development over $30M CIV or State significant development</Text>
""")
        assert [f for f in scan_file(p) if f["state"] == "FABRICATED"] == []

    def test_a_python_if_guarded_verdict_is_not_fabricated(self, tmp_path):
        # The strata blocks in the conveyancing report are guarded by `if is_strata:`
        # three lines up, through a dict literal. A TypeScript-only branch pattern
        # reported all three as fabricated.
        p = _write(tmp_path, "g.py", '''
def build(is_strata):
    results = []
    if is_strata:
        results.append({
            "question": "Secondary dwelling (granny flat)",
            "answer": "Not applicable - strata lot",
        })
    return results
''')
        assert [f for f in scan_file(p) if f["state"] == "FABRICATED"] == []

    def test_an_annotated_escape_clears_a_finding(self, tmp_path):
        p = _write(tmp_path, "H.tsx", """
{/* verdict-ok: advice about other addresses, asserts nothing about this site */}
<Text>✗ Not applicable - Property not within 400m of metro station</Text>
""")
        assert scan_file(p) == []

    def test_a_bare_escape_with_no_reason_does_not_clear(self, tmp_path):
        p = _write(tmp_path, "I.tsx", """
{/* verdict-ok: */}
<Text>✗ Not applicable - Property not within 400m of metro station</Text>
""")
        assert [f for f in scan_file(p) if f["state"] == "FABRICATED"] != []


class TestClassifierParts:
    @pytest.mark.parametrize("s", ["✗ Not applicable", "Does not apply", "Eligible",
                                   "None identified", "No constraints"])
    def test_verdict_words(self, s):
        assert _VERDICT.search(s)

    @pytest.mark.parametrize("s", ["this property", "the site", "within 400m", "the lot"])
    def test_site_cues(self, s):
        assert _SITE_CLAIM.search(s)

    @pytest.mark.parametrize("s", ["not assessed", "data unavailable", "unknown"])
    def test_honest_wording_is_recognised(self, s):
        assert _HONEST.search(s)


class TestConveyancingConstraintScreen:
    """The worst live instance: an outage rendered as a clean bill of health."""

    SRC = (ROOT / "scripts" / "generate_conveyancing_report.py").read_text(encoding="utf-8")

    def test_no_longer_claims_no_constraints_purely_from_an_empty_list(self):
        # `get_unique_overlays` returns ([], set(), {}) on ANY exception, so an empty
        # `flagged` list alone cannot distinguish "unconstrained" from "query failed".
        bad = re.search(
            r"if flagged else\s*[\"']\s*No constraints identified for this property",
            self.SRC,
        )
        assert bad is None, "empty `flagged` is again treated as proof of no constraints"

    def test_distinguishes_a_screen_that_did_not_run(self):
        assert "_screen_ran = bool(covered_layers)" in self.SRC
        assert "Constraint screening did not complete" in self.SRC

    def test_says_plainly_that_incomplete_is_not_a_finding_of_unconstrained(self):
        assert "not a finding that" in self.SRC
        assert "the property is unconstrained" in self.SRC
