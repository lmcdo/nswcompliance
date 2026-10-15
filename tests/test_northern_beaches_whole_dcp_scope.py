"""Warringah DCP 2011 — one document, scoped by the Part code in each rule's ref.

The whole DCP is stored as ONE document, so there is no per-chapter document_id
and `chapter_topics` cannot express it. That looked like a reason to split the
PDF and re-extract.

It was not. The Part is already in every rule's own section reference --
`# G9.1.5.1.14 C2 Signage`, `# E11 C1 Flood Prone Land` -- and the EXISTING  # noqa: zone-codes (Warringah DCP PART letters, not NSW zone codes)
`parts` path (Woollahra's, Waverley's) reads that code out of the text and
strips it progressively, G9.1 -> G9 -> G. Measured 2026-09-23:
`_extract_section_code` reads a code on 1,560 of 1,602 served rows, and the
config took rows applying to every development type from 1,535 to 237.

Re-extracting to recover structure the data already held would have risked what
`dcp_commit_approved`'s section-loss guard exists to catch. This needed no new
code, no registry rows, and no change to any provision's provenance.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from enrichment.config import COUNCIL_CONFIGS  # noqa: E402
from enrichment.extractors.applicability_tagger import ApplicabilityTagger  # noqa: E402

DOC = "Warringah_DCP_2011__warringah_dcp_2011_full"


@pytest.fixture(scope="module")
def tagger():
    return ApplicabilityTagger()


class TestThePartCodeIsReadFromTheRule:
    @pytest.mark.parametrize("heading,expect", [
        ("# G9.1.5.1.14 C2 Signage must not protrude above the roof", "G9"),
        ("# G3 C27 Soil and Water Management All development must", "G3"),
        ("# G10.2 R4 Sloping sites On sloping sites each dwelling", "G10"),
        ("# E11 C1 Flood Prone Land - Control 1 Development must", "E11"),
        ("# D23 O4 Signs - Objective 4 To ensure the provision", "D23"),
    ])
    def test_the_code_survives_the_progressive_strip(self, tagger, heading, expect):
        code = ApplicabilityTagger._extract_section_code(heading)
        assert code and code.split(".")[0] == expect


class TestPartGIsPlaceScoped:
    """Section A.6: "Part G applies controls to special areas of Warringah e.g.
    parts of Dee Why, Warringah Mall" and "where there is inconsistency with
    Parts C, D and E, the requirements of Part G will prevail." The G-series are
    named places -- Belrose Corridor, Freshwater Village, Dee Why RSL Club,
    Narrabeen, Frenchs Forest Town Centre -- so every development inside one is
    bound by it. ALL is an assertion here, not a fallthrough."""

    @pytest.mark.parametrize("part", ["G1", "G3", "G5", "G9", "G10"])
    def test_a_g_part_binds_every_development_in_its_area(self, tagger, part):
        _z, _d, prov = tagger.tag_with_provenance(
            f"# {part}.2 C4 A control about built form.", DOC)
        assert prov["dev_type_source"] == "config_all"

    def test_it_is_marked_precinct_specific(self, tagger):
        got = tagger._get_config_driven(DOC, "# G5.1 O3 Built Form in Freshwater")
        assert got["is_precinct_specific"] is True


class TestTheOtherParts:
    def test_e11_is_a_flood_site_condition_not_a_development_type(self, tagger):
        """Part E11 Flood Prone Land binds whatever is proposed on land the
        flood maps cover. Matched before the letter-only fallback to "E"."""
        got = tagger._get_config_driven(DOC, "# E11 C1 Flood Prone Land - Control 1")
        assert got["site_conditions"] == ["flood"]
        assert got["dev_type_source"] == "config_all"

    @pytest.mark.parametrize("part", ["C1", "D2", "E7"])
    def test_the_built_form_parts_bind_all_development(self, tagger, part):
        _z, _d, prov = tagger.tag_with_provenance(f"# {part} C3 A control.", DOC)
        assert prov["dev_type_source"] == "config_all"

    def test_part_f_decides_NEITHER_key(self, tagger):
        """A.6 says Part F "covers development and activities in certain zones
        and sensitive areas" without listing them. Declaring ALL would assert a
        universality the plan itself qualifies; naming zones would invent a
        list."""
        got = tagger._get_config_driven(DOC, "# F1 C10 Local and Neighbourhood Centres")
        assert got["zone_source"] == "config_declined"
        assert got["dev_type_source"] == "config_declined"


class TestItRefusesToGuess:
    def test_a_bare_numeric_code_stays_unmatched(self, tagger):
        """110 served rows carry a code belonging to no Part letter in this
        plan's structure (`# 5.4.7 C9 Basement entries`). Guessing a Part for
        them to improve the number is what DQ-33 exists to refuse, so they stay
        unmatched and keep being counted."""
        assert tagger._get_config_driven(DOC, "# 5.4.7 C9 Basement entries") is None

    def test_a_row_with_no_code_stays_unmatched(self, tagger):
        assert tagger._get_config_driven(DOC, "No heading at all here.") is None

    def test_both_registry_spellings_reach_the_config(self):
        """The document_id says Warringah; the council slug says
        northern_beaches. Registering only one leaves the other unreachable."""
        assert "warringah" in COUNCIL_CONFIGS
        assert "northern_beaches" in COUNCIL_CONFIGS

    def test_no_part_entry_is_an_empty_dict(self):
        """`_resolve` opens with `if not entry: return ['ALL'], 'no_config'`, so
        an entry declaring neither key is falsy and collapses back to the state
        this config exists to clear. Part F is one `layer` line away from it."""
        from enrichment.config.northern_beaches_config import NORTHERN_BEACHES_CONFIG
        for part, entry in NORTHERN_BEACHES_CONFIG["parts"].items():
            assert entry, f"Part {part} is an empty dict -> no_config"
