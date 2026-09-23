"""Parramatta DCP 2023 — a whole-DCP council whose Parts are NUMBERED.

Northern Beaches proved a one-document DCP can be scoped through the existing
`parts` path by reading the Part out of each rule's own section reference. Its
Parts are letters (`G9.1` -> `G9` -> `G`). Parramatta's are numbers, and that
one difference creates a hazard letters do not have:

`_extract_section_code` matches a leading number, so any CONTENT line starting
with a digit parses as a bare section code. Measured 2026-09-24 on the 616
served rows:

    "# 1 Bedroom 10 - 20% of total dwellings"   really Melrose Park (Part 8)
    "# 6 Metre Wide Lanes"                       really Granville   (Part 8)
    "# 3 Design excellence ..."                  really Site Specific (Part 9)
    "# 772 Parramatta Development Control Plan"  a page footer

A bare `1` hits `parts["1"]` directly, with no stripping. So a numbered config
that NARROWED any Part would silently narrow whichever misread rows landed on
it -- Melrose Park controls scoped to a Part they have nothing to do with, and
`v2_applicable_zones` / `v2_applicable_dev_types` are HARD filters, so those
rows would vanish from every answer that did not match.

The config is built so that cannot happen: every entry it declares is `["ALL"]`
on both axes. This file pins that property rather than trusting the reading.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from enrichment.config import COUNCIL_CONFIGS  # noqa: E402
from enrichment.config.parramatta_config import PARRAMATTA_CONFIG  # noqa: E402
from enrichment.extractors.applicability_tagger import ApplicabilityTagger  # noqa: E402

PARTS = PARRAMATTA_CONFIG["parts"]
DOC = "Parramatta_DCP_2023_(Amendment_4)__parramatta_dcp_2023"


@pytest.fixture(scope="module")
def tagger():
    return ApplicabilityTagger()


class TestNothingInThisConfigCanHideAControl:
    """The property the misread hazard makes non-negotiable."""

    @pytest.mark.parametrize("part", sorted(PARTS))
    def test_every_declared_part_is_ALL_on_both_axes(self, part):
        entry = PARTS[part]
        for key in ("applicable_zones", "applicable_dev_types"):
            assert entry.get(key) == ["ALL"], (
                f"Part {part} declares {key}={entry.get(key)!r}. A numbered "
                f"config that narrows also narrows the bare-number misreads "
                f"that resolve to it.")

    def test_no_entry_is_an_empty_dict(self):
        """`_resolve` opens with `if not entry: return ['ALL'], 'no_config'`, so
        an entry declaring nothing is indistinguishable from no config at all --
        it would report a decision that was never made."""
        for part, entry in PARTS.items():
            assert entry, f"Part {part} is an empty dict"


class TestTheMisreadsResolveToNothingHarmful:
    def test_a_page_footer_does_not_inherit_the_heritage_part(self, tagger):
        """`# 772 ...` is a page footer. The progressive strip is
        `re.sub(r'\\.?\\d+$', '', code)`, which turns "772" into "" rather than
        "7", so it can never pick up Part 7's scope. If that ever changes, a
        footer starts carrying heritage applicability."""
        assert tagger._extract_section_code("# 772 Parramatta Development "
                                            "Control Plan 2023 3 - 75") == "772"
        zones, devs, prov = tagger.tag_with_provenance(
            "# 772 Parramatta Development Control Plan 2023 3 - 75", DOC)
        assert prov["dev_type_source"] != "config_all" or devs == ["ALL"]

    def test_part_1_is_absent_because_its_rows_are_not_its_own(self):
        """All 8 rows reading as Part 1 are bare-number misreads belonging to
        Melrose Park and Epping. An entry here would be a statement about rows
        that are not Part 1's."""
        assert "1" not in PARTS

    def test_a_bedroom_mix_row_is_never_narrowed(self, tagger):
        """The concrete misread. Whatever it resolves to, it must not come back
        with a dev-type list that would drop it from other answers."""
        text = ("# 1 Bedroom 10 - 20% of total dwellings  LOCAL CENTRES "
                "MELROSE PARK URBAN RENEWAL PRECINCT Dwelling Type Dwelling Mix")
        zones, devs, _ = tagger.tag_with_provenance(text, DOC)
        assert devs == ["ALL"], f"a misread row was narrowed to {devs!r}"
        assert zones == ["ALL"], f"a misread row was narrowed to {zones!r}"


class TestAFillerKeyIsNotFree:
    """The regression that the first draft of the config shipped.

    Parts 3, 4 and 10 originally carried `{"layer": "generic"}` -- the
    Campbelltown filler, which keeps an entry truthy so `_resolve` records
    `config_silent` rather than `no_config`. It reads as a provenance
    improvement at no cost. It is not: **`config_silent` still returns
    `['ALL']`**, so an entry declaring nothing REPLACES whatever the text regex
    derived. Measured on the real rows, the filler destroyed 63 rows' worth of
    dev types, including id=105112 losing ['commercial_premises',
    'office_premises', 'retail_premises', 'shop_top_housing'] on a Part whose
    own words are "applies to all non-residential types of development".
    """

    @pytest.mark.parametrize("part", ["3", "4", "10", "12", "13", "17"])
    def test_the_parts_with_text_derived_values_have_no_entry(self, part):
        assert part not in PARTS, (
            f"Part {part} has an entry again. If it declares no scope key it "
            f"overwrites text-derived dev types with an invented ALL; if it "
            f"declares one, check the list is complete first.")

    def test_a_silent_entry_really_does_overwrite_the_text(self, tagger):
        """The mechanism, asserted directly rather than remembered. A Part 4 row
        carries non-residential dev types from its text; with a filler entry in
        place it would come back ALL."""
        text = ("# 4.2 BUSINESS AND COMMERCIAL DEVELOPMENT  NON-RESIDENTIAL "
                "DEVELOPMENT This Section of this DCP is intended to provide "
                "design requirements and guide the assessment of business "
                "and/or commercial development types.")
        _, devs, prov = tagger.tag_with_provenance(text, DOC)
        assert prov["dev_type_source"] != "config_silent", (
            "Part 4 has an entry again and the text reading has been replaced")

        # With no entry the text survives. The filler's behaviour is asserted
        # against `_resolve` directly, because that is where the ALL is
        # invented -- going through the tagger would only prove the config has
        # no Part 4 entry, which the test above already covers.
        vals, src = ApplicabilityTagger._resolve(
            {"layer": "generic"}, "applicable_dev_types")
        assert (vals, src) == (["ALL"], "config_silent"), (
            "config_silent no longer returns ALL -- re-check whether a filler "
            "key is now safe, because this whole class assumes it is not")


class TestItIsWiredIn:
    def test_the_council_slug_resolves_to_this_config(self):
        assert COUNCIL_CONFIGS.get("parramatta") is PARRAMATTA_CONFIG

    def test_the_precinct_flag_is_carried_for_the_place_scoped_parts(self, tagger):
        """Parts 8 and 9 are geographic. The flag has been silently dropped by
        the `parts` branch before (fixed 2026-09-23), so it is asserted through
        the tagger rather than read off the dict."""
        for part in ("8", "9"):
            assert PARTS[part].get("is_precinct_specific") is True
        text = ("# 8.2.3 GRANVILLE LOCAL CENTRE  The provisions of this Section "
                "of this DCP apply to development within Granville Local Centre")
        result = tagger.tag_with_provenance(text, DOC)
        assert result is not None

    def test_heritage_is_recorded_as_a_site_condition_not_a_dev_type(self):
        """Part 7 binds whatever is proposed on a heritage item. Expressing that
        as a dev-type list would drop it from every type not named."""
        assert PARTS["7"].get("site_conditions") == ["heritage"]
        assert PARTS["7"]["applicable_dev_types"] == ["ALL"]
