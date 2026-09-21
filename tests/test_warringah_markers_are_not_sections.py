"""Warringah's objective and requirement markers were being read as section headings.

Warringah DCP 2011 writes its objectives and requirements as numbered sentences inside a
section:

    O1  To establish a safe internal access road network that serves the development
    R2  Dwellings with a street frontage to have a front door directly visible from the
        street.

The default `SECTION_RE` allows an optional `[A-Z]` before the digits, so both match as
section headings. Each one then becomes a provision citing a clause number the document
has no section for — the same defect class as the ref slug served as a citation (#1153).

**Measured on the 124-row 2026-09-20 re-read:** 14 rows were keyed off a marker —
O1, O4, O5, O8, O16, O21, O24, O26, O27, R2, R10, R11, R13, R23 — about one row in nine.
The auto-rejected `R2` row also blocked the whole chapter from committing, and its text is
real control wording ("front door directly visible from the street", façade articulation,
side setbacks) that appears nowhere else in the batch, so neither approving it nor dropping
it was right. The reader had to stop producing it.

The letter is restricted to A-H because that is what this plan uses for its parts: the same
batch carries A, B, C, D, E, F, G and H and nothing else. It stays OPTIONAL, because
Warringah also has genuinely numbered parts — "12 Key Sites", "14 Residential Flat
Buildings" — and requiring a letter would lose them.

Same remedy as Woollahra's override for O1/C1 (2026-05) and Marrickville's for C8/O9, and
scoped to one council for the same reason: another plan may use O or R as a real part letter.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ.setdefault("DATABASE_URL", "postgresql:///test")
for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
    os.environ.setdefault(_k, "test")

_STUBS = ("boto3", "botocore", "psycopg2", "dotenv", "enrichment", "enrichment.pipeline")
_saved = {k: sys.modules.get(k) for k in _STUBS}
for _k in _STUBS:
    sys.modules[_k] = MagicMock()
sys.modules["dotenv"].load_dotenv = MagicMock()
try:
    import dcp_extract_changed as dx  # noqa: E402
finally:
    for _k, _v in _saved.items():
        if _v is None:
            sys.modules.pop(_k, None)
        else:
            sys.modules[_k] = _v

RX = dx.COUNCIL_SECTION_RE_OVERRIDES["northern_beaches"]


class TestTheMarkersAreRejected:
    """Every one of these was a real row in the 2026-09-20 batch."""

    @pytest.mark.parametrize("line", [
        "O1 To establish a safe internal access road network that serves the development",
        "O4 Some objective wording",
        "O16 Another objective",
        "O27 Yet another objective",
        "R2 Dwellings with a street frontage to have a front door directly visible",
        "R10 A requirement",
        "R13 A requirement",
        "R23 A requirement",
    ])
    def test_an_objective_or_requirement_marker_is_not_a_section(self, line):
        assert RX.match(line) is None, (
            f"{line.split()[0]} is a clause marker; filing it as a section cites a "
            f"clause the document has no section for")


class TestTheRealSectionsStillMatch:
    """The confusable negative, and the one that matters most: a fix that quietly
    dropped real parts would be far worse than the defect."""

    @pytest.mark.parametrize("line,code", [
        ("A1 General", "A1"),
        ("B4 Something", "B4"),
        ("C3 Parking Facilities", "C3"),
        ("D21 Provision and Location of Utility Services", "D21"),
        ("E11 Flood Prone Land", "E11"),
        ("F4 SP2 Infrastructure Zone", "F4"),
        ("G10 Low and Mid-Rise Housing", "G10"),
        ("H1 Appendices", "H1"),
    ])
    def test_a_lettered_part_matches(self, line, code):
        m = RX.match(line)
        assert m and m.group(1) == code

    @pytest.mark.parametrize("line,code", [
        ("12 Key Sites Applies to Land", "12"),
        ("14 Residential Flat Buildings", "14"),
    ])
    def test_a_numbered_part_still_matches(self, line, code):
        """Warringah numbers some parts. The letter must stay optional or these are
        lost, and they carry real controls."""
        m = RX.match(line)
        assert m and m.group(1) == code, (
            "a genuine numbered part stopped matching -- the letter must stay optional")

    def test_part_g10_specifically(self):
        """Part G10 (Low and Mid-Rise Housing) commenced 15 September 2025 and is the
        amendment the plan-in-force hold exists for. Losing it would hide the very thing
        we are re-reading this chapter to capture."""
        assert RX.match("G10 Low and Mid-Rise Housing")


class TestTheOverrideIsScopedToThisCouncil:
    def test_other_councils_are_untouched(self):
        """O and R may be real part letters in another plan. This is one council's
        document convention, not a general rule."""
        assert dx.COUNCIL_SECTION_RE_OVERRIDES["northern_beaches"] is RX
        for other in ("marrickville", "woollahra", "ku_ring_gai"):
            assert dx.COUNCIL_SECTION_RE_OVERRIDES[other] is not RX

    def test_the_default_pattern_still_admits_markers(self):
        """The premise. If the default ever stops matching O1, this override is no
        longer doing anything and the file should be re-read rather than trusted."""
        assert dx.DCPExtractor.SECTION_RE.match("O1 To establish a safe internal road"), (
            "the default no longer admits a marker; re-read why this override exists")

    def test_two_group_contract(self):
        """Override patterns must expose exactly (code, title) -- the extractor reads
        them through _match_groups, which assumes two groups for an override."""
        m = RX.match("C3 Parking Facilities")
        assert m.groups() == ("C3", "Parking Facilities")
