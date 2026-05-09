#!/usr/bin/env python3
"""
Tests for NumericExtractor

Run with: pytest enrichment/tests/test_numeric_extractor.py -v
"""

import pytest
from enrichment.extractors.numeric_extractor import NumericExtractor, extract_numeric_values


@pytest.fixture
def extractor():
    """Create extractor instance."""
    return NumericExtractor()


class TestSetbackExtraction:
    """Test setback value extraction."""

    def test_front_setback_minimum(self, extractor):
        """Test extraction of front setback minimum."""
        text = "Buildings must be setback a minimum of 6 metres from the front boundary."
        result = extractor.extract(text)

        assert result["has_numeric"] is True
        assert result["value_count"] >= 1

        setback = next((v for v in result["values"] if v["value_type"] == "setback"), None)
        assert setback is not None
        assert setback.get("value_exact") == 6.0 or setback.get("value_min") == 6.0
        assert setback["unit"] == "m"
        assert setback["context"] == "front"

    def test_rear_setback(self, extractor):
        """Test extraction of rear setback."""
        text = "The rear setback must be a minimum of 8 metres."
        result = extractor.extract(text)

        assert result["has_numeric"] is True
        setback = next((v for v in result["values"] if v["value_type"] == "setback"), None)
        assert setback is not None
        assert setback.get("value_exact") == 8.0 or setback.get("value_min") == 8.0
        assert setback["context"] == "rear"

    def test_multiple_setbacks(self, extractor):
        """Test extraction of multiple setbacks in one provision."""
        text = "Front setback minimum 6m, side setback 0.9m."
        result = extractor.extract(text)

        assert result["has_numeric"] is True
        assert result["value_count"] >= 2


class TestHeightExtraction:
    """Test height value extraction."""

    def test_maximum_height_metres(self, extractor):
        """Test extraction of maximum height in metres."""
        text = "Maximum building height of 9m."
        result = extractor.extract(text)

        assert result["has_numeric"] is True
        height = next((v for v in result["values"] if v["value_type"] == "height"), None)
        assert height is not None
        assert height["value_max"] == 9.0
        assert height["unit"] == "m"

    def test_height_limit(self, extractor):
        """Test extraction of height limit."""
        text = "Height limit 8.5m."
        result = extractor.extract(text)

        assert result["has_numeric"] is True
        height = next((v for v in result["values"] if v["value_type"] == "height"), None)
        assert height is not None
        assert height["value_max"] == 8.5


class TestFSRExtraction:
    """Test FSR value extraction."""

    def test_fsr_ratio_format(self, extractor):
        """Test extraction of FSR in ratio format."""
        text = "FSR 0.5:1 applies to residential development."
        result = extractor.extract(text)

        assert result["has_numeric"] is True
        fsr = next((v for v in result["values"] if v["value_type"] == "fsr"), None)
        assert fsr is not None
        assert fsr["value_exact"] == 0.5

    def test_fsr_maximum(self, extractor):
        """Test extraction of maximum FSR."""
        text = "Maximum FSR of 0.65"
        result = extractor.extract(text)

        assert result["has_numeric"] is True
        fsr = next((v for v in result["values"] if v["value_type"] == "fsr"), None)
        assert fsr is not None


class TestLotDimensionExtraction:
    """Test lot dimension extraction."""

    def test_minimum_lot_size(self, extractor):
        """Test extraction of minimum lot size."""
        text = "Minimum lot size of 450m2."
        result = extractor.extract(text)

        assert result["has_numeric"] is True
        lot_area = next((v for v in result["values"] if v["value_type"] == "lot_area"), None)
        assert lot_area is not None
        assert lot_area["value_min"] == 450.0
        assert lot_area["unit"] == "m2"

    def test_frontage_width(self, extractor):
        """Test extraction of frontage width."""
        text = "Minimum frontage width of 12m."
        result = extractor.extract(text)

        assert result["has_numeric"] is True
        lot_width = next((v for v in result["values"] if v["value_type"] == "lot_width"), None)
        assert lot_width is not None
        assert lot_width["value_min"] == 12.0


class TestPercentageExtraction:
    """Test percentage value extraction."""

    def test_site_coverage(self, extractor):
        """Test extraction of site coverage percentage."""
        text = "Site coverage must not exceed 60%."
        result = extractor.extract(text)

        assert result["has_numeric"] is True
        coverage = next((v for v in result["values"] if v["value_type"] == "site_coverage"), None)
        assert coverage is not None
        assert coverage["value_exact"] == 60.0

    def test_landscaping_percentage(self, extractor):
        """Test extraction of landscaping percentage."""
        text = "Minimum 30% landscaping required."
        result = extractor.extract(text)

        assert result["has_numeric"] is True
        landscaping = next((v for v in result["values"] if v["value_type"] == "landscaping"), None)
        assert landscaping is not None
        assert landscaping["value_exact"] == 30.0

    def test_deep_soil(self, extractor):
        """Test extraction of deep soil percentage."""
        text = "Deep soil zone of at least 15% of site area."
        result = extractor.extract(text)

        assert result["has_numeric"] is True
        deep_soil = next((v for v in result["values"] if v["value_type"] == "deep_soil"), None)
        assert deep_soil is not None
        assert deep_soil["value_exact"] == 15.0


class TestEdgeCases:
    """Test edge cases and failure scenarios."""

    def test_empty_text(self, extractor):
        """Test extraction from empty text."""
        result = extractor.extract("")
        assert result["has_numeric"] is False
        assert result["values"] == []
        assert result["value_count"] == 0

    def test_no_numeric_values(self, extractor):
        """Test extraction from text without numeric values."""
        text = "Development must maintain the character of the streetscape."
        result = extractor.extract(text)
        assert result["has_numeric"] is False

    def test_decimal_values(self, extractor):
        """Test extraction of decimal values."""
        text = "FSR 0.65:1"
        result = extractor.extract(text)
        assert result["has_numeric"] is True
        fsr = next((v for v in result["values"] if v["value_type"] == "fsr"), None)
        assert fsr is not None
        assert fsr["value_exact"] == 0.65

    def test_none_text(self, extractor):
        """Test extraction from None."""
        result = extractor.extract(None)
        assert result["has_numeric"] is False


class TestConvenienceFunction:
    """Test the convenience function."""

    def test_extract_numeric_values(self):
        """Test the module-level convenience function."""
        result = extract_numeric_values("Maximum height 9m.")
        assert result["has_numeric"] is True
        assert result["value_count"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
