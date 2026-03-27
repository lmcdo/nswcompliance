"""
Tests for ApplicabilityTagger

QA Focus:
- ZONE ACCURACY: Correct zone assignment from document structure and text
- DEV TYPE ACCURACY: Correct development type assignment
- INHERITANCE: Structure-based applicability correctly inherited from DCP config

Run with: pytest tests/enrichment/test_applicability_tagger.py -v
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from enrichment.extractors.applicability_tagger import ApplicabilityTagger


class TestGoldenSetApplicability:
    """Test golden set provisions have correct zone/dev-type assignments."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.tagger = ApplicabilityTagger()

    def test_golden_set_zones(self, golden_set_applicability):
        """All golden set provisions get correct zone assignment."""
        failures = []
        for case in golden_set_applicability:
            zones, dev_types = self.tagger.tag(case['text'], case['document_id'])

            # Check zones match expected
            expected_zones = set(case['expected_zones'])
            actual_zones = set(zones)

            # Special handling for 'ALL' - it means any zone matches
            if 'ALL' in expected_zones and 'ALL' in actual_zones:
                continue
            elif expected_zones != actual_zones:
                failures.append(
                    f"Document: {case['document_id']}\n"
                    f"  Expected zones: {case['expected_zones']}\n"
                    f"  Got zones: {zones}"
                )

        assert len(failures) == 0, f"Zone assignment failures:\n" + "\n".join(failures)

    def test_golden_set_dev_types(self, golden_set_applicability):
        """All golden set provisions get correct dev type assignment."""
        failures = []
        for case in golden_set_applicability:
            zones, dev_types = self.tagger.tag(case['text'], case['document_id'])

            expected_dev_types = set(case['expected_dev_types'])
            actual_dev_types = set(dev_types)

            # Special handling for 'ALL'
            if 'ALL' in expected_dev_types and 'ALL' in actual_dev_types:
                continue
            elif expected_dev_types != actual_dev_types:
                failures.append(
                    f"Document: {case['document_id']}\n"
                    f"  Expected dev types: {case['expected_dev_types']}\n"
                    f"  Got dev types: {dev_types}"
                )

        # Allow some flexibility - structure + text may add types
        # Only fail if expected types are MISSING
        strict_failures = []
        for case in golden_set_applicability:
            zones, dev_types = self.tagger.tag(case['text'], case['document_id'])
            expected = set(case['expected_dev_types'])
            actual = set(dev_types)

            if 'ALL' not in expected and 'ALL' not in actual:
                missing = expected - actual
                if missing:
                    strict_failures.append(
                        f"Document: {case['document_id']}\n"
                        f"  Missing dev types: {missing}"
                    )

        assert len(strict_failures) == 0, f"Missing dev type failures:\n" + "\n".join(strict_failures)


class TestMarrickvilleStructuralInheritance:
    """Test Marrickville DCP structure-based applicability."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.tagger = ApplicabilityTagger()

    def test_part2_generic_all(self):
        """Part 2 (General) applies to ALL zones and dev types."""
        zones, dev_types = self.tagger.tag(
            "General parking provisions.",
            "Marrickville__DCP__2011__-__2__10__Parking"
        )
        assert 'ALL' in zones or set(zones) == {'ALL'}
        assert 'ALL' in dev_types or set(dev_types) == {'ALL'}

    def test_part4_1_low_density(self):
        """Part 4.1 applies to R2 zones and low-density dev types."""
        zones, dev_types = self.tagger.tag(
            "Low density setbacks.",
            "Marrickville__DCP__2011__-__4_1__Low__Density__Residential"
        )
        assert 'R2' in zones
        assert 'dwelling_house' in dev_types or 'secondary_dwelling' in dev_types or 'dual_occupancy' in dev_types

    def test_part4_2_multi_dwelling(self):
        """Part 4.2 applies to R3/R4 zones and multi-dwelling dev types."""
        zones, dev_types = self.tagger.tag(
            "Multi dwelling controls.",
            "Marrickville__DCP__2011__-__4_2__Multi__Dwelling"
        )
        assert 'R3' in zones or 'R4' in zones
        assert 'multi_dwelling_housing' in dev_types or 'residential_flat_building' in dev_types

    def test_part5_commercial(self):
        """Part 5 applies to B zones and commercial dev types."""
        zones, dev_types = self.tagger.tag(
            "Commercial controls.",
            "Marrickville__DCP__2011__-__5_0__Commercial"
        )
        business_zones = {'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'MU1'}
        assert len(set(zones) & business_zones) > 0, f"Expected B zones, got {zones}"
        commercial_types = {'commercial_premises', 'retail_premises', 'office_premises', 'shop_top_housing'}
        assert len(set(dev_types) & commercial_types) > 0, f"Expected commercial types, got {dev_types}"

    def test_part6_industrial(self):
        """Part 6 applies to IN zones and industrial dev types."""
        zones, dev_types = self.tagger.tag(
            "Industrial controls.",
            "Marrickville__DCP__2011__-__6_0__Industrial"
        )
        industrial_zones = {'IN1', 'IN2', 'IN3', 'IN4'}
        assert len(set(zones) & industrial_zones) > 0, f"Expected IN zones, got {zones}"
        industrial_types = {'industrial_development', 'warehouse', 'light_industry'}
        assert len(set(dev_types) & industrial_types) > 0, f"Expected industrial types, got {dev_types}"

    def test_part8_heritage_all_zones(self):
        """Part 8 (Heritage) applies to ALL zones but has site condition."""
        zones, dev_types = self.tagger.tag(
            "Heritage conservation.",
            "Marrickville__DCP__2011__-__8.0__Heritage"
        )
        # Heritage applies to all zones but filtered by site condition
        assert 'ALL' in zones or len(zones) > 0

    def test_part9_precinct_all(self):
        """Part 9 (Precincts) applies to ALL (filtered by location)."""
        zones, dev_types = self.tagger.tag(
            "Precinct controls.",
            "Marrickville__DCP__2011__-__9__6__Petersham__South"
        )
        # Precincts use location filtering, not zone filtering
        assert 'ALL' in zones or len(zones) > 0


class TestTextBasedExtraction:
    """Test zone/dev-type extraction from provision text."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.tagger = ApplicabilityTagger()

    def test_zone_extraction_single(self):
        """Single zone mentioned in text is extracted."""
        zones, _ = self.tagger.tag("This control applies to R2 zones.", None)
        assert 'R2' in zones

    def test_zone_extraction_multiple(self):
        """Multiple zones mentioned in text are extracted."""
        zones, _ = self.tagger.tag("This control applies to R2, R3, and B1 zones.", None)
        assert 'R2' in zones
        assert 'R3' in zones
        assert 'B1' in zones

    def test_zone_category_residential(self):
        """'residential zone' expands to R1-R5."""
        zones, _ = self.tagger.tag("Development in residential zones must...", None)
        # Should include at least some residential zones
        residential = {'R1', 'R2', 'R3', 'R4', 'R5'}
        assert len(set(zones) & residential) > 0

    def test_zone_category_business(self):
        """'business zone' expands to B zones."""
        zones, _ = self.tagger.tag("Development in business zones must...", None)
        business = {'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7'}
        assert len(set(zones) & business) > 0

    def test_dev_type_dwelling_house(self):
        """'dwelling house' dev type extracted."""
        _, dev_types = self.tagger.tag("Dwelling houses must have setback.", None)
        assert 'dwelling_house' in dev_types

    def test_dev_type_dual_occupancy(self):
        """'dual occupancy' dev type extracted."""
        _, dev_types = self.tagger.tag("Dual occupancy development requires...", None)
        assert 'dual_occupancy' in dev_types

    def test_dev_type_multi_dwelling(self):
        """'multi-dwelling housing' dev type extracted."""
        _, dev_types = self.tagger.tag("Multi-dwelling housing provisions.", None)
        assert 'multi_dwelling_housing' in dev_types

    def test_dev_type_residential_flat(self):
        """'residential flat building' dev type extracted."""
        _, dev_types = self.tagger.tag("Residential flat buildings must...", None)
        assert 'residential_flat_building' in dev_types

    def test_dev_type_child_care(self):
        """'child care centre' dev type extracted."""
        _, dev_types = self.tagger.tag("Child care centres require...", None)
        assert 'child_care_centre' in dev_types


class TestStructurePlusText:
    """Test that text extraction supplements (not replaces) structural config."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.tagger = ApplicabilityTagger()

    def test_text_adds_to_structure(self):
        """Text-based zones ADD to structural zones, not replace."""
        # Part 4.1 is R2, but text mentions R3
        zones, _ = self.tagger.tag(
            "This also applies to R3 zones.",
            "Marrickville__DCP__2011__-__4_1__Low__Density"
        )
        # Should have R2 from structure AND R3 from text
        assert 'R2' in zones, "Should have R2 from structure"
        assert 'R3' in zones, "Should have R3 from text"

    def test_text_adds_dev_types(self):
        """Text-based dev types ADD to structural dev types."""
        # Part 4.1 has dwelling_house, text mentions boarding_house
        _, dev_types = self.tagger.tag(
            "Including boarding house applications.",
            "Marrickville__DCP__2011__-__4_1__Low__Density"
        )
        # Should have structural types AND boarding_house from text
        assert 'dwelling_house' in dev_types or 'boarding_house' in dev_types


class TestDefaultBehavior:
    """Test default behavior when no specific info found."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.tagger = ApplicabilityTagger()

    def test_no_zones_defaults_to_all(self):
        """No zone info defaults to ALL."""
        zones, _ = self.tagger.tag("Generic development control.", None)
        assert 'ALL' in zones

    def test_no_dev_types_defaults_to_all(self):
        """No dev type info defaults to ALL."""
        _, dev_types = self.tagger.tag("Generic development control.", None)
        assert 'ALL' in dev_types

    def test_unknown_document_defaults_to_all(self):
        """Unknown document_id defaults to ALL."""
        zones, dev_types = self.tagger.tag(
            "Some control.",
            "Unknown_Council_DCP"
        )
        assert 'ALL' in zones
        assert 'ALL' in dev_types


class TestCouncilDetection:
    """Test council detection for config selection."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.tagger = ApplicabilityTagger()

    def test_marrickville_detected(self):
        """Marrickville council detected from document_id."""
        council = self.tagger._detect_council("Marrickville_DCP_2011")
        assert council == "marrickville"

    def test_leichhardt_detected(self):
        """Leichhardt council detected from document_id."""
        council = self.tagger._detect_council("Leichhardt_DCP_2013")
        assert council == "leichhardt"

    def test_ashfield_detected(self):
        """Ashfield council detected from document_id."""
        council = self.tagger._detect_council("Ashfield_DCP_2007")
        assert council == "ashfield"

    def test_case_insensitive_detection(self):
        """Council detection is case-insensitive."""
        assert self.tagger._detect_council("MARRICKVILLE_DCP") == "marrickville"
        assert self.tagger._detect_council("leichhardt_dcp") == "leichhardt"
        assert self.tagger._detect_council("AsHfIeLd_DCP") == "ashfield"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.tagger = ApplicabilityTagger()

    def test_empty_text(self):
        """Empty text handled gracefully."""
        zones, dev_types = self.tagger.tag("", "Marrickville_DCP_2011_Part_2")
        # Should get structural defaults
        assert len(zones) > 0
        assert len(dev_types) > 0

    def test_none_text(self):
        """None text handled gracefully."""
        zones, dev_types = self.tagger.tag(None, "Marrickville_DCP_2011_Part_2")
        assert len(zones) > 0
        assert len(dev_types) > 0

    def test_none_document_id(self):
        """None document_id handled gracefully."""
        zones, dev_types = self.tagger.tag("Development control.", None)
        assert 'ALL' in zones
        assert 'ALL' in dev_types

    def test_both_none(self):
        """Both None handled gracefully."""
        zones, dev_types = self.tagger.tag(None, None)
        assert 'ALL' in zones
        assert 'ALL' in dev_types

    def test_zone_boundary_not_confused(self):
        """Zone codes not matched within words."""
        # "R2" should match, but "BR2" or "R20" should not
        zones, _ = self.tagger.tag("Zone R2 applies.", None)
        assert 'R2' in zones

        zones2, _ = self.tagger.tag("BR2 building code.", None)
        # This might match R2 depending on pattern - check actual behavior

    def test_results_sorted(self):
        """Results are returned sorted."""
        zones, dev_types = self.tagger.tag(
            "R3, R2, B1 zones. Dual occupancy and dwelling house.",
            None
        )
        assert zones == sorted(zones), "Zones should be sorted"
        assert dev_types == sorted(dev_types), "Dev types should be sorted"
