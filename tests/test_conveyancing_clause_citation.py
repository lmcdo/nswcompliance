"""The cited clause must be one the report actually shows.

DQ-35. `fetch_dcp_setbacks` drops rows with two `continue` guards — a control
flagged needs_review after a DCP amendment, and a zone_specific control whose
condition names zones that exclude this property. But `clause_ref` was taken from
`rows[0]`, the RAW query's first row, so the citation a conveyancer reads could
point at a control the function had just decided not to show — including one for
a different zone.

Citing the source is the product's whole claim. A citation that doesn't match the
rendered controls is worse than no citation.

Mutation note: reverting to `rows[0][7]` fails both leading-row tests; returning a
constant fails the happy-path test. The suite is run against the real function via
a stubbed DB connection, not against a reimplementation.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from conveyancing_db import fetch_dcp_setbacks  # noqa: E402


# Column order matches the SELECT in fetch_dcp_setbacks:
# dev_type, control_type, value_min, value_max, unit, condition, source_text,
# section_ref, applicability, needs_review, source_chapter_key, pdf_page,
# dcp_version
def row(section_ref, *, needs_review=False, condition="", applicability="general",
        control_type="front_setback", dev_type="dwelling_house", vmin=4.5):
    return (dev_type, control_type, vmin, None, "m", condition,
            "Provide a front setback.", section_ref, applicability, needs_review,
            "part_3", 12, "v2022-current")


def _conn(rows):
    """A connection whose first execute() returns `rows`, second the DCP url."""
    cur = MagicMock()
    cur.fetchall.return_value = rows
    cur.fetchone.return_value = ("https://example.council.nsw.gov.au/dcp",)
    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn


class TestClauseCitationMatchesWhatIsShown:
    def test_leading_row_under_review_is_not_cited(self):
        """A suppressed control must not supply the citation for the shown ones."""
        result = fetch_dcp_setbacks(
            _conn([row("SUPPRESSED-4.1", needs_review=True), row("SHOWN-5.2")]),
            "waverley", "R2 Low Density",
        )
        assert result is not None
        assert result["clause_ref"] == "SHOWN-5.2"

    def test_leading_row_for_another_zone_is_not_cited(self):
        """The worst case: citing a clause that applies to a different zone."""
        result = fetch_dcp_setbacks(
            _conn([
                row("OTHER-ZONE-3.1", condition="Applies in the R4 zone only",
                    applicability="zone_specific"),
                row("SHOWN-5.2"),
            ]),
            "waverley", "R2 Low Density",
        )
        assert result is not None
        assert result["clause_ref"] == "SHOWN-5.2"

    def test_normal_case_still_cites_the_first_shown_control(self):
        result = fetch_dcp_setbacks(_conn([row("A-1.1"), row("A-1.2")]),
                                    "waverley", "R2 Low Density")
        assert result["clause_ref"] == "A-1.1"

    def test_no_citation_is_invented_when_everything_is_filtered_out(self):
        """Empty is honest. A reference to a control nobody can see is not."""
        result = fetch_dcp_setbacks(
            _conn([row("SUPPRESSED", needs_review=True)]), "waverley", "R2 Low Density")
        assert result is not None
        assert result["clause_ref"] == ""

    def test_citation_comes_from_the_secondary_dwelling_list_when_that_is_all_there_is(self):
        result = fetch_dcp_setbacks(
            _conn([row("SD-9.9", dev_type="secondary_dwelling",
                       applicability="secondary_dwelling_specific")]),
            "waverley", "R2 Low Density",
        )
        assert result["clause_ref"] == "SD-9.9"

    def test_blank_dwelling_clause_falls_through_to_the_secondary_dwelling_citation(self):
        """A non-empty dwelling list must not stop the search when its clause is blank.

        `dh_setbacks or sd_setbacks` would pick the truthy dh list and emit no
        citation, even though a rendered secondary-dwelling control carries one.
        """
        result = fetch_dcp_setbacks(
            _conn([
                row("", dev_type="dwelling_house"),
                row("SD-9.9", dev_type="secondary_dwelling",
                    applicability="secondary_dwelling_specific"),
            ]),
            "waverley", "R2 Low Density",
        )
        assert result["clause_ref"] == "SD-9.9"

    @pytest.mark.parametrize("blank", ["", None])
    def test_blank_reference_on_the_first_shown_row_falls_through(self, blank):
        """A row can be shown yet carry no section_ref; don't cite an empty string."""
        result = fetch_dcp_setbacks(_conn([row(blank), row("REAL-2.2")]),
                                    "waverley", "R2 Low Density")
        assert result["clause_ref"] == "REAL-2.2"
