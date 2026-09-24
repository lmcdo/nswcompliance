"""A fabricated citation walked through the gate built to catch fabrication.

Found 2026-09-23. A Canterbury-Bankstown provision in the review queue carried:

    https://www.epa.ny.gov.gov.uk/.../varricool/fgpl502-resource-recovery...
    https://www.pernitchlq.nsw.gov.au/...
    SLR Ref No: 628.18852.9021-4-8-8.8000

The council's own PDF carries `https://www.epa.nsw.gov.au/-/media/epa/` and
`https://www.penrithcity.nsw.gov.au/images/`. Neither invented domain exists,
and the SLR reference appears nowhere in the source at all. The reader took real
URLs and COMPLETED them into plausible-looking inventions -- which is where an
LLM fabricates: filling a gap in a damaged scan with something shaped right.

WHY THE GATE MISSED IT
----------------------
It checks numbers and it checks words. A URL is neither. `_content_words` is
`[a-z]{4,}`, which shreds `epa.ny.gov.gov.uk` into fragments that match ordinary
prose, and the digits inside a reference code look like any other number. So the
one failure mode this project treats as unacceptable -- inventing data -- passed
a gate whose entire purpose is to catch it.

MUTATION NOTE. The confusable negatives are what make this safe to ship as a
FLAG. PDF extraction damages URLs constantly: a line wrap truncates the host, a
path loses a segment, a closing bracket runs into the address. None of those is
an invention, and a check that flagged them would be deleted within a week for
crying wolf. Each has a test below that must NOT fire.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from dcp_fidelity_gate import _urls_not_in_source  # noqa: E402

#: What the council's chapter actually cites, from the real PDF.
SOURCE = (
    "Refer to Page 69 https://www.epa.nsw.gov.au/-/media/epa/corporate-site/"
    "resource-recovery.pdf. Automated waste collection systems are described at "
    "https://www.penrithcity.nsw.gov.au/images/documents/building-development/ "
    "and https://assets.sustainability.vic.gov.au/susvic/Guide-Waste.pdf"
)


class TestItCatchesTheInvention:
    def test_both_fabricated_hosts_are_reported(self):
        """The real row, verbatim. Two invented domains built out of two real
        ones: epa.nsw.gov.au -> epa.ny.gov.gov.uk, penrithcity -> pernitchlq."""
        got = _urls_not_in_source(
            "Refer to Page 69 https://www.epa.ny.gov.gov.uk/-/media/epa/"
            "corporate-site/eservices/varricool/fgpl502-resource-recovery.pdf. "
            "See also https://www.pernitchlq.nsw.gov.au/documents/waste.pdf",
            SOURCE)
        assert got == ["www.epa.ny.gov.gov.uk", "www.pernitchlq.nsw.gov.au"]

    def test_a_host_from_another_organisation_entirely(self):
        """The harm is citing somebody else. `gpo.gov.uk` is a British
        government domain in an Australian council's DCP."""
        got = _urls_not_in_source(
            "Refer to https://www.gpo.gov.uk/~/media/gpo/events/review.pdf", SOURCE)
        assert got == ["www.gpo.gov.uk"]


class TestItStaysSilentOnDAMAGE:
    """Extraction mangles URLs constantly. Damage is not invention, and a check
    that cannot tell them apart gets switched off."""

    def test_a_faithful_citation_passes(self):
        assert _urls_not_in_source(
            "Refer to https://www.epa.nsw.gov.au/-/media/epa/x.pdf", SOURCE) == []

    def test_a_host_truncated_by_a_line_wrap_passes(self):
        """`https://www.penrithcity.nsw.gov.` -- the wrap ate `au/...`. A broken
        link, not a different source."""
        assert _urls_not_in_source("see https://www.penrithcity.nsw.gov.", SOURCE) == []

    def test_a_damaged_PATH_on_a_real_host_passes(self):
        """Matching on host is the whole design: the path is where extraction
        damage is most common and least consequential."""
        assert _urls_not_in_source(
            "see https://www.epa.nsw.gov.au/TOTALLY/different/path.pdf", SOURCE) == []

    def test_a_trailing_bracket_is_not_part_of_the_host(self):
        """`doc_claims._URL_RE` is `https?://\\S+`, which would swallow the `)`
        into the domain and report a false invention. That is exactly why this
        does not reuse it."""
        assert _urls_not_in_source(
            "see (https://www.epa.nsw.gov.au/x.pdf) for detail", SOURCE) == []

    def test_a_row_with_no_urls_produces_nothing(self):
        assert _urls_not_in_source(
            "The minimum front setback is 4.5 metres.", SOURCE) == []

    def test_a_chapter_that_cites_nothing_accuses_nothing(self):
        """No source URLs means no basis for comparison. Reporting every URL as
        invented because the source text was empty would fire hardest on the
        chapters whose text extraction failed -- the rows already in trouble."""
        assert _urls_not_in_source("see https://www.anything.com/x", "") == []


class TestTheGateReportsIt:
    def test_the_reason_names_the_host_and_says_what_it_means(self):
        """A reviewer meeting this row needs to know it is not a number to
        check. The detail string has to say the citation is not the council's."""
        import dcp_fidelity_gate as gate
        import inspect

        src = inspect.getsource(gate)
        assert "_urls_not_in_source(own, whole_chapter)" in src, (
            "the check must run on the COUNCIL's own text and the WHOLE chapter")
        assert "URL not in source" in src
        assert "invented_urls" in src.split("if absent or ground_ratio")[1][:400], (
            "an invented URL must take the row to flagged, not merely be printed")

    @pytest.mark.parametrize("host", ["www.epa.nsw.gov.au", "assets.sustainability.vic.gov.au"])
    def test_every_host_the_source_carries_is_accepted(self, host):
        assert _urls_not_in_source("see https://%s/a/b.pdf" % host, SOURCE) == []
