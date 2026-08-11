"""The ALL in v2_applicable_zones must say WHY it is ALL.

95.6% of served provisions carry ALL for both zones and dev types (production,
2026-08-01). Until now that value could not be distinguished between "a config
decided this applies everywhere" and "nothing matched, so we defaulted" — which
made almost the entire served corpus unauditable.

These tests pin the distinction. Mutation note: a `_resolve` hardwired to return
`'config_all'` fails every defaulted case; one hardwired to `'no_config'` fails
every asserted case; and returning the tuple in the wrong order fails the
vocabulary assertions. There is no constant that satisfies the file.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from enrichment.extractors.applicability_tagger import (  # noqa: E402
    APPLICABILITY_SOURCES,
    TRUSTED_ALL_SOURCES,
    ApplicabilityTagger,
)


@pytest.fixture(scope="module")
def tagger():
    return ApplicabilityTagger()


class TestResolveDistinguishesAssertionFromDefault:
    """The core of the fix: four outcomes that used to be one."""

    def test_specific_list_is_an_assertion(self):
        v, s = ApplicabilityTagger._resolve({'applicable_zones': ['R2', 'R3']}, 'applicable_zones')  # noqa: zone-codes - parser fixture, not a regulatory lookup
        assert v == ['R2', 'R3'] and s == 'config_specific'  # noqa: zone-codes - parser fixture, not a regulatory lookup

    def test_explicit_all_is_an_assertion_not_a_default(self):
        v, s = ApplicabilityTagger._resolve({'applicable_zones': ['ALL']}, 'applicable_zones')
        assert v == ['ALL'] and s == 'config_all'
        assert s in TRUSTED_ALL_SOURCES

    def test_entry_matched_but_key_absent_is_config_silent(self):
        # `.get(key, ['ALL'])` used to invent this value. Nobody decided it.
        v, s = ApplicabilityTagger._resolve({'site_conditions': None}, 'applicable_zones')
        assert v == ['ALL'] and s == 'config_silent'
        assert s not in TRUSTED_ALL_SOURCES

    def test_key_present_but_none_is_config_silent(self):
        v, s = ApplicabilityTagger._resolve({'applicable_zones': None}, 'applicable_zones')
        assert v == ['ALL'] and s == 'config_silent'

    def test_key_present_but_empty_is_config_silent(self):
        # An empty list says nothing; it must not read as an assertion.
        v, s = ApplicabilityTagger._resolve({'applicable_zones': []}, 'applicable_zones')
        assert v == ['ALL'] and s == 'config_silent'

    def test_no_entry_at_all_is_no_config(self):
        for empty in (None, {}):
            v, s = ApplicabilityTagger._resolve(empty, 'applicable_zones')
            assert v == ['ALL'] and s == 'no_config'
        assert 'no_config' not in TRUSTED_ALL_SOURCES

    def test_all_four_outcomes_are_actually_different(self):
        seen = {
            ApplicabilityTagger._resolve({'applicable_zones': ['R2']}, 'applicable_zones')[1],
            ApplicabilityTagger._resolve({'applicable_zones': ['ALL']}, 'applicable_zones')[1],
            ApplicabilityTagger._resolve({'other': 1}, 'applicable_zones')[1],
            ApplicabilityTagger._resolve(None, 'applicable_zones')[1],
        }
        assert len(seen) == 4, f"outcomes collapsed to {seen}"


class TestTagWithProvenance:
    def test_vocabulary_is_closed(self, tagger):
        for text, doc in [("x", None), ("R2 zones apply.", None),
                          ("Setback 6m.", "Marrickville__DCP__2011__-__4.1__Low__Density__Residential__Development"),
                          ("y", "Inner West Ashfield DCP 2016 - Chapter A - Miscellaneous"),
                          ("z", "Unknown_Council_DCP_2020_Part_3")]:
            _, _, prov = tagger.tag_with_provenance(text, doc)
            assert prov['zone_source'] in APPLICABILITY_SOURCES
            assert prov['dev_type_source'] in APPLICABILITY_SOURCES

    def test_structural_config_reports_config_specific(self, tagger):
        zones, _, prov = tagger.tag_with_provenance(
            "Setback minimum 6m.",
            "Marrickville__DCP__2011__-__4.1__Low__Density__Residential__Development")
        assert zones == ['R2'] and prov['zone_source'] == 'config_specific'

    def test_no_document_id_is_not_dressed_up_as_a_decision(self, tagger):
        zones, dev, prov = tagger.tag_with_provenance("Development must maintain character.", None)
        assert zones == ['ALL'] and dev == ['ALL']
        assert prov['zone_source'] == 'no_document_id'
        assert prov['zone_source'] not in TRUSTED_ALL_SOURCES

    def test_text_derived_zones_are_labelled_as_regex(self, tagger):
        zones, _, prov = tagger.tag_with_provenance("This applies to R2 and R3 zones.", None)  # noqa: zone-codes - parser fixture, not a regulatory lookup
        assert zones == ['R2', 'R3'] and prov['zone_source'] == 'text_regex'  # noqa: zone-codes - parser fixture, not a regulatory lookup

    def test_unrecognised_council_is_no_config_not_silence(self, tagger):
        _, _, prov = tagger.tag_with_provenance("General control.", "Some_Council_DCP_2021_Part_4")
        assert prov['zone_source'] in ('no_config', 'text_regex')

    def test_validity_gate_rejection_is_distinct_from_never_found(self, tagger):
        """A code found then rejected must not look like a code never found.

        Conflating them hides that a bad zone code was caught — the DQ-30 signal.
        """
        zones, _, prov = tagger.tag_with_provenance(
            "This applies to R2 and R3 zones.", None, valid_zones={'E1', 'MU1'})  # noqa: zone-codes - parser fixture, not a regulatory lookup
        assert zones == ['ALL']
        assert prov['zone_source'] == 'filtered_to_all'
        assert prov['zone_source'] not in TRUSTED_ALL_SOURCES

    def test_valid_zones_keeps_codes_that_do_exist(self, tagger):
        zones, _, prov = tagger.tag_with_provenance(
            "This applies to R2 and R3 zones.", None, valid_zones={'R2'})  # noqa: zone-codes - parser fixture, not a regulatory lookup
        assert zones == ['R2'] and prov['zone_source'] == 'text_regex'


class TestEveryMarrickvillePartStaysReachable:
    """Regression guard: a dedented fallback return silently killed Parts 1 and 3.

    While adding provenance, a blanket string replace matched an 8-space `return`
    INSIDE a 12-space line, dedenting it to method level. Every branch below it
    became unreachable, so Marrickville Part 1 and Part 3 documents silently fell
    through to no_config/ALL. The full suite — 3,332 tests — stayed green, because
    nothing exercised those two parts. A GPT-5.6 cross-review caught it.

    These assert reachability by source, not by value: Part 1 legitimately resolves
    to ALL, so asserting `zones == ['ALL']` would have passed while broken. Only
    the source distinguishes "Part 1 says everywhere" from "we never got there" —
    which is the entire point of this PR, applied to itself.
    """

    PART_DOCS = [
        ("Part 1", "Marrickville__DCP__2011__-__1__0__Introduction"),
        ("Part 3", "Marrickville__DCP__2011__-__3__0__Subdivision"),
        ("Part 4.1", "Marrickville__DCP__2011__-__4.1__Low__Density__Residential__Development"),
        ("Part 5", "Marrickville__DCP__2011__-__5__0__Commercial"),
        ("Part 6", "Marrickville__DCP__2011__-__6__0__Industrial"),
    ]

    @pytest.mark.parametrize("label,doc_id", PART_DOCS)
    def test_part_is_reached_by_its_own_config_entry(self, tagger, label, doc_id):
        _, _, prov = tagger.tag_with_provenance("Control text.", doc_id)
        assert prov['zone_source'] != 'no_config', (
            f"{label} fell through to no_config — its branch is unreachable"
        )

    def test_unenumerated_part_2_subsection_still_falls_through(self, tagger):
        """The fallback itself must keep working, not just the branches after it."""
        _, _, prov = tagger.tag_with_provenance(
            "Control.", "Marrickville__DCP__2011__-__2__99__Nonexistent")
        assert prov['zone_source'] in ('no_config', 'config_silent')


class TestBackwardCompatibility:
    """Every existing caller uses the two-value tag(); it must not change."""

    def test_tag_still_returns_exactly_two_values(self, tagger):
        result = tagger.tag("Development must maintain character.", None)
        assert isinstance(result, tuple) and len(result) == 2

    def test_tag_and_tag_with_provenance_agree_on_values(self, tagger):
        for text, doc in [("Setback 6m.", "Marrickville__DCP__2011__-__4.1__Low__Density__Residential__Development"),
                          ("R2 zones apply.", None),
                          ("General.", "Inner West Ashfield DCP 2016 - Chapter E1 - Heritage")]:
            z1, d1 = tagger.tag(text, doc)
            z2, d2, _ = tagger.tag_with_provenance(text, doc)
            assert (z1, d1) == (z2, d2)


class TestMigrationMatchesCode:
    """The CHECK constraint and the Python vocabulary must not drift."""

    def test_every_source_appears_in_the_migration(self):
        sql = (Path(__file__).resolve().parent.parent
               / "migrations" / "062_applicability_provenance.sql").read_text(encoding="utf-8")
        for source in APPLICABILITY_SOURCES:
            assert f"'{source}'" in sql, f"{source} missing from the CHECK constraint"

    def test_migration_is_additive_only(self):
        sql = (Path(__file__).resolve().parent.parent
               / "migrations" / "062_applicability_provenance.sql").read_text(encoding="utf-8").upper()
        for forbidden in ("DROP TABLE", "DROP COLUMN", "TRUNCATE", "DELETE FROM", "CASCADE"):
            assert forbidden not in sql, f"migration contains {forbidden}"

    def test_migration_does_not_backfill(self):
        """Inventing a source for old rows would fabricate the very fact recorded."""
        sql = (Path(__file__).resolve().parent.parent
               / "migrations" / "062_applicability_provenance.sql").read_text(encoding="utf-8").upper()
        assert "UPDATE REGULATORY_PROVISIONS" not in sql
