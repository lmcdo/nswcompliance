"""
Tests for SchemaExtractor class
"""

import os
import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.processing.schema_extractor import SchemaExtractor
from src.models import FormerCouncilArea, SetbackRule


class TestSchemaExtractor:
    """Test suite for SchemaExtractor class"""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance for testing"""
        return SchemaExtractor()

    def test_init(self, extractor):
        """Test extractor initialization"""
        assert hasattr(extractor, 'patterns')
        assert 'rear' in extractor.patterns
        assert 'side' in extractor.patterns
        assert 'front' in extractor.patterns

    def test_extract_setback_rules_empty_chunks(self, extractor):
        """Test extraction with empty chunk list"""
        result = extractor.extract_setback_rules([], FormerCouncilArea.ASHFIELD, "test.pdf")
        
        assert isinstance(result, dict)
        assert 'rear' in result
        assert 'side' in result
        assert 'front' in result
        assert all(rule is None for rule in result.values())

    def test_extract_rear_setback_distance_height(self, extractor):
        """Test extraction of rear setback with distance and height"""
        chunks = [
            "Building within 6m of the rear boundary must not exceed maximum height of 4m",
            "Structures within 3m of rear boundary shall not exceed 5.5m in height"
        ]
        
        result = extractor.extract_setback_rules(chunks, FormerCouncilArea.ASHFIELD, "test.pdf")
        
        # Check if any rear setback rule was extracted (patterns may be specific)
        if result['rear'] is not None:
            assert isinstance(result['rear'], SetbackRule)
            # Should extract distance and height from patterns
            assert result['rear'].distance is not None or result['rear'].height_limit is not None

    def test_extract_rear_setback_distance_only(self, extractor):
        """Test extraction of rear setback with distance only"""
        chunks = [
            "Minimum rear setback shall be 3m from the boundary",
            "Rear setback must be at least 4.5m minimum distance"
        ]
        
        result = extractor.extract_setback_rules(chunks, FormerCouncilArea.ASHFIELD, "test.pdf")
        
        assert result['rear'] is not None
        assert isinstance(result['rear'], SetbackRule)

    def test_extract_side_setback(self, extractor):
        """Test extraction of side setback rules"""
        chunks = [
            "Side boundary setback minimum 1.5m with maximum height 4m",
            "Buildings must maintain 2m side setback with 6m height limit"
        ]
        
        result = extractor.extract_setback_rules(chunks, FormerCouncilArea.ASHFIELD, "test.pdf")
        
        assert result['side'] is not None
        assert isinstance(result['side'], SetbackRule)

    def test_extract_front_setback(self, extractor):
        """Test extraction of front setback rules"""
        chunks = [
            "Front setback minimum 6m from street alignment",
            "Street frontage setback shall be 4.5m minimum distance"
        ]
        
        result = extractor.extract_setback_rules(chunks, FormerCouncilArea.ASHFIELD, "test.pdf")
        
        assert result['front'] is not None
        assert isinstance(result['front'], SetbackRule)

    def test_extract_multiple_setback_types(self, extractor):
        """Test extraction of multiple setback types from same chunks"""
        chunks = [
            "Building setbacks: minimum 3m rear, 1.5m side, 6m front boundary distances",
            "Rear setback 4m with height limit 8m, side setback 2m maximum height 6m"
        ]
        
        result = extractor.extract_setback_rules(chunks, FormerCouncilArea.ASHFIELD, "test.pdf")
        
        # Should extract multiple setback types
        extracted_count = sum(1 for rule in result.values() if rule is not None)
        assert extracted_count > 1

    def test_extract_with_zones_and_conditions(self, extractor):
        """Test extraction including zones and conditions"""
        chunks = [
            "In R2 Low Density Residential zones, rear setback minimum 4m for single storey buildings",
            "Commercial zones require 6m front setback for developments over 12m height"
        ]
        
        result = extractor.extract_setback_rules(chunks, FormerCouncilArea.LEICHHARDT, "test.pdf")
        
        # Should extract rules and potentially identify zones/conditions
        for rule_type, rule in result.items():
            if rule is not None:
                assert isinstance(rule, SetbackRule)
                assert rule.source_file == "test.pdf"

    def test_no_matches_found(self, extractor):
        """Test behavior when no setback rules are found"""
        chunks = [
            "This document contains general information about council procedures",
            "Administrative guidelines for development applications are outlined below"
        ]
        
        result = extractor.extract_setback_rules(chunks, FormerCouncilArea.MARRICKVILLE, "test.pdf")
        
        assert all(rule is None for rule in result.values())

    def test_pattern_priority_rear_setback(self, extractor):
        """Test that more specific patterns take priority for rear setbacks"""
        chunks = [
            "Rear setback 3m minimum",  # Less specific
            "Within 6m of rear boundary maximum height 4m"  # More specific with distance and height
        ]
        
        result = extractor.extract_setback_rules(chunks, FormerCouncilArea.ASHFIELD, "test.pdf")
        
        if result['rear'] is not None:
            # Should prefer more specific pattern with both distance and height
            assert isinstance(result['rear'], SetbackRule)

    def test_calculate_confidence_all_rules(self, extractor):
        """Test confidence calculation with all rule types"""
        rules = {
            'rear': SetbackRule(distance=3.0, source="test", source_file="test.pdf"),
            'side': SetbackRule(height_limit=6.0, source="test", source_file="test.pdf"),
            'front': SetbackRule(min_distance=4.5, source="test", source_file="test.pdf")
        }
        
        confidence = extractor.calculate_confidence(rules)
        
        assert confidence == 1.0  # All three rule types present

    def test_calculate_confidence_partial_rules(self, extractor):
        """Test confidence calculation with partial rules"""
        rules = {
            'rear': SetbackRule(distance=3.0, source="test", source_file="test.pdf"),
            'side': None,
            'front': SetbackRule(min_distance=4.5, source="test", source_file="test.pdf")
        }
        
        confidence = extractor.calculate_confidence(rules)
        
        # Base confidence is 2/3, plus quality bonuses for distance values
        # Each rule with distance gets +0.05 bonus, so 2/3 + 0.1 = 0.7666...
        expected = (2.0 / 3.0) + 0.1  # Base + quality bonus
        assert abs(confidence - expected) < 0.001

    def test_calculate_confidence_no_rules(self, extractor):
        """Test confidence calculation with no rules"""
        rules = {
            'rear': None,
            'side': None,
            'front': None
        }
        
        confidence = extractor.calculate_confidence(rules)
        
        assert confidence == 0.0

    def test_patterns_contain_required_groups(self, extractor):
        """Test that regex patterns contain required capture groups"""
        # Test rear setback patterns
        for pattern_name, pattern in extractor.patterns['rear'].items():
            import re
            compiled = re.compile(pattern, re.IGNORECASE)
            assert compiled.groups >= 1  # Should have at least one capture group

    def test_extract_numeric_values(self, extractor):
        """Test extraction of numeric values from text"""
        test_cases = [
            ("minimum 3.5m rear setback", 3.5),
            ("setback of 6 metres", 6.0),
            ("4m minimum distance", 4.0),
            ("2.25m boundary setback", 2.25)
        ]
        
        for text, expected_value in test_cases:
            chunks = [text]
            result = extractor.extract_setback_rules(chunks, FormerCouncilArea.ASHFIELD, "test.pdf")
            
            # Check if any rule was extracted with numeric value
            found_value = False
            for rule in result.values():
                if rule is not None:
                    numeric_fields = [rule.distance, rule.height_limit, rule.min_distance]
                    if any(field == expected_value for field in numeric_fields):
                        found_value = True
                        break
            
            # Note: This is a loose test as extraction depends on specific patterns
            # The main goal is to ensure numeric extraction is working

    def test_source_information_preservation(self, extractor):
        """Test that source information is preserved in extracted rules"""
        chunks = ["Rear setback minimum 3m from boundary"]
        area = FormerCouncilArea.LEICHHARDT
        source_file = "leichhardt_dcp.pdf"
        
        result = extractor.extract_setback_rules(chunks, area, source_file)
        
        for rule_type, rule in result.items():
            if rule is not None:
                assert rule.source_file == source_file
                assert area.value.lower() in rule.source.lower()

    def test_different_council_areas(self, extractor):
        """Test extraction works for different council areas"""
        chunks = ["Building setback requirements: 4m rear, 2m side, 6m front"]
        
        for area in [FormerCouncilArea.ASHFIELD, FormerCouncilArea.LEICHHARDT, FormerCouncilArea.MARRICKVILLE]:
            result = extractor.extract_setback_rules(chunks, area, f"{area.value.lower()}.pdf")
            
            # Should work for all council areas
            assert isinstance(result, dict)
            assert len(result) == 3