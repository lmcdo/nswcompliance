#!/usr/bin/env python3
"""
Numeric Value Extractor for Provisions

Extracts quantitative values from provision text using regex patterns.
This is Phase 1 of the enrichment pipeline - free, instant, handles ~80% of cases.

Supports:
- Setbacks (front, side, rear)
- Heights (storeys, metres)
- FSR (floor space ratio)
- Lot dimensions (area, width, depth)
- Percentages (landscaping, site coverage)
- Distances and dimensions
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ExtractedValue:
    """A single extracted numeric value."""
    value_type: str  # setback, height, fsr, lot_area, percentage, etc.
    value_min: Optional[float] = None
    value_max: Optional[float] = None
    value_exact: Optional[float] = None
    unit: Optional[str] = None  # m, m2, storeys, %, :1
    context: Optional[str] = None  # front, side, rear, etc.
    raw_match: Optional[str] = None  # The original matched text

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {k: v for k, v in asdict(self).items() if v is not None}


class NumericExtractor:
    """
    Extract numeric values from provision text.

    Usage:
        extractor = NumericExtractor()
        result = extractor.extract("Buildings must be setback minimum 6m from front boundary")
        # result.has_numeric = True
        # result.values = [ExtractedValue(value_type='setback', value_min=6.0, unit='m', context='front')]
    """

    # Regex patterns for different value types
    PATTERNS = {
        # Setbacks - various formats
        'setback_minimum': [
            r'(?:minimum|min\.?)\s+(?:of\s+)?(?:setback\s+(?:of\s+)?)?(\d+\.?\d*)\s*(mm|metres?|m)\s*(?:from\s+(?:the\s+)?(\w+)\s+boundary)?',
            r'setback\s+(?:of\s+)?(?:at\s+least\s+|minimum\s+)?(\d+\.?\d*)\s*(mm|metres?|m)\s*(?:from\s+(?:the\s+)?(\w+))?',
            r'(\w+)\s+setback\s+(?:of\s+)?(?:minimum\s+|at\s+least\s+)?(\d+\.?\d*)\s*(mm|metres?|m)',
            r'setback\s+(?:a\s+)?minimum\s+(?:of\s+)?(\d+\.?\d*)\s*(mm|metres?|m)',
            r'(?:the\s+)?(\w+)\s+setback\s+(?:must\s+be\s+)?(?:a\s+)?minimum\s+(?:of\s+)?(\d+\.?\d*)\s*(mm|metres?|m)',
            r'setback\s+must\s+be\s+(?:a\s+)?minimum\s+(?:of\s+)?(\d+\.?\d*)\s*(mm|metres?|m)',
            # NSW DCP prose: "a minimum of X metres side setback"
            r'minimum\s+of\s+(\d+\.?\d*)\s*(mm|metres?|m)\s+(\w+)\s+setback',
        ],
        'setback_maximum': [
            r'(?:maximum|max\.?)\s+setback\s+(?:of\s+)?(\d+\.?\d*)\s*(mm|metres?|m)',
            r'setback\s+(?:of\s+)?(?:no\s+more\s+than|maximum)\s+(\d+\.?\d*)\s*(mm|metres?|m)',
        ],
        'setback_range': [
            r'setback\s+(?:of\s+)?(\d+\.?\d*)\s*(?:to|-)\s*(\d+\.?\d*)\s*(mm|metres?|m)',
        ],
        # Separation distance — NSW DCP: "minimum separation distance of X metres"
        'separation_min': [
            r'minimum\s+separation\s+distance\s+of\s+(\d+\.?\d*)\s*(mm|metres?|m)',
            r'separation\s+distance\s+(?:of\s+)?(?:at\s+least\s+|minimum\s+)?(\d+\.?\d*)\s*(mm|metres?|m)',
            r'(?:minimum|min\.?)\s+(?:of\s+)?(\d+\.?\d*)\s*(mm|metres?|m)\s+separation',
        ],

        # Heights
        'height_max': [
            r'(?:maximum|max\.?)\s+(?:building\s+)?height\s+(?:of\s+)?(\d+\.?\d*)\s*(mm|metres?|m|storeys?)',
            r'height\s+(?:limit|must\s+not\s+exceed)\s+(?:of\s+)?(\d+\.?\d*)\s*(mm|metres?|m|storeys?)',
            r'(?:not\s+exceed|no\s+more\s+than)\s+(\d+\.?\d*)\s*(mm|metres?|m|storeys?)\s+(?:in\s+)?height',
            r'(\d+\.?\d*)\s*(mm|metres?|m|storeys?)\s+(?:maximum\s+)?height',
            # NSW DCP: "limited to maximum X storeys"
            r'limited\s+to\s+(?:a\s+)?maximum\s+(\d+\.?\d*)\s*(storeys?|mm|metres?|m)',
        ],
        'height_min': [
            r'(?:minimum|min\.?)\s+(?:building\s+)?height\s+(?:of\s+)?(\d+\.?\d*)\s*(mm|metres?|m|storeys?)',
        ],

        # FSR (Floor Space Ratio)
        'fsr': [
            r'(?:FSR|floor\s+space\s+ratio)\s+(?:of\s+)?(\d+\.?\d*)\s*:\s*1',
            r'(?:FSR|floor\s+space\s+ratio)\s+(?:of\s+)?(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*:\s*1\s+(?:FSR|floor\s+space\s+ratio)',
            r'(?:maximum|max\.?)\s+FSR\s+(?:of\s+)?(\d+\.?\d*)',
        ],

        # Lot dimensions
        'lot_area_min': [
            r'(?:minimum|min\.?)\s+(?:lot|site)\s+(?:size|area)\s+(?:of\s+)?(\d+\.?\d*)\s*(m2|m²|sqm|square\s+metres?)',
            r'(?:lot|site)\s+(?:size|area)\s+(?:of\s+)?(?:at\s+least\s+|minimum\s+)?(\d+\.?\d*)\s*(m2|m²|sqm)',
        ],
        'lot_width_min': [
            r'(?:minimum|min\.?)\s+(?:lot|site|frontage)\s+width\s+(?:of\s+)?(\d+\.?\d*)\s*(mm|metres?|m)',
            r'(?:lot|frontage)\s+width\s+(?:of\s+)?(?:at\s+least\s+|minimum\s+)?(\d+\.?\d*)\s*(mm|metres?|m)',
        ],

        # Percentages
        'site_coverage': [
            r'(?:maximum|max\.?)\s+(?:site\s+)?coverage\s+(?:of\s+)?(\d+\.?\d*)\s*%',
            r'(?:site\s+)?coverage\s+(?:must\s+)?(?:not\s+exceed|maximum)\s+(\d+\.?\d*)\s*%',
        ],
        'landscaping': [
            r'(?:minimum|min\.?)\s+(\d+\.?\d*)\s*%\s+(?:of\s+(?:the\s+)?(?:site|lot))?\s*(?:landscap|soft)',
            r'landscap\w*\s+(?:area\s+)?(?:of\s+)?(?:at\s+least\s+|minimum\s+)?(\d+\.?\d*)\s*%',
            r'(\d+\.?\d*)\s*%\s+(?:of\s+(?:the\s+)?(?:site|lot)\s+)?(?:must\s+be\s+)?landscap',
        ],
        'deep_soil': [
            r'(?:minimum|min\.?)\s+(\d+\.?\d*)\s*%\s+deep\s+soil',
            r'deep\s+soil\s+(?:zone\s+)?(?:of\s+)?(?:at\s+least\s+|minimum\s+)?(\d+\.?\d*)\s*%',
        ],

        # Parking
        'parking_spaces': [
            r'(\d+)\s+(?:car\s+)?parking\s+space',
            r'parking\s+(?:spaces?\s+)?(?:of\s+)?(\d+)',
            r'(\d+)\s+space(?:s)?\s+per\s+(?:dwelling|unit)',
        ],

        # Generic dimensions
        'dimension': [
            r'(\d+\.?\d*)\s*(m|metres?|mm|millimetres?)\s+(?:wide|width|long|length|deep|depth)',
            r'(?:width|length|depth)\s+(?:of\s+)?(\d+\.?\d*)\s*(m|metres?|mm)',
        ],
    }

    # Context patterns for setbacks
    SETBACK_CONTEXTS = {
        'front': r'\b(front|street|primary)\b',
        'side': r'\b(side|lateral)\b',
        'rear': r'\b(rear|back)\b',
        'secondary': r'\b(secondary|corner)\b',
    }

    def __init__(self):
        """Initialize the extractor with compiled patterns."""
        self.compiled_patterns: Dict[str, List[re.Pattern]] = {}
        for value_type, patterns in self.PATTERNS.items():
            self.compiled_patterns[value_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

        self.context_patterns = {
            ctx: re.compile(p, re.IGNORECASE)
            for ctx, p in self.SETBACK_CONTEXTS.items()
        }

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extract all numeric values from provision text.

        Args:
            text: The provision text to analyze

        Returns:
            Dictionary with:
                - has_numeric: bool
                - values: List of extracted values as dicts
                - value_count: int
        """
        if not text:
            return {"has_numeric": False, "values": [], "value_count": 0}

        values: List[ExtractedValue] = []

        for value_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    extracted = self._process_match(value_type, match, text)
                    if extracted:
                        extracted = self._convert_mm_to_m(extracted)
                        values.append(extracted)

        # Deduplicate based on value and type
        unique_values = self._deduplicate(values)

        return {
            "has_numeric": len(unique_values) > 0,
            "values": [v.to_dict() for v in unique_values],
            "value_count": len(unique_values)
        }

    def _process_match(self, value_type: str, match: re.Match, full_text: str) -> Optional[ExtractedValue]:
        """Process a regex match into an ExtractedValue."""
        groups = match.groups()

        if not groups or not groups[0]:
            return None

        try:
            # Base value type without min/max/range/minimum/maximum suffix
            base_type = value_type
            for suffix in ['_minimum', '_maximum', '_min', '_max', '_range']:
                base_type = base_type.replace(suffix, '')

            # Handle different pattern structures
            if value_type.endswith('_range') and len(groups) >= 2:
                # Range pattern: (min, max, unit)
                return ExtractedValue(
                    value_type=base_type,
                    value_min=float(groups[0]),
                    value_max=float(groups[1]),
                    unit=self._normalize_unit(groups[2] if len(groups) > 2 else None),
                    context=self._detect_context(value_type, match, full_text),
                    raw_match=match.group(0)
                )
            elif value_type.endswith('_min'):
                return ExtractedValue(
                    value_type=base_type,
                    value_min=float(groups[0]),
                    unit=self._normalize_unit(groups[1] if len(groups) > 1 else None),
                    context=self._detect_context(value_type, match, full_text),
                    raw_match=match.group(0)
                )
            elif value_type.endswith('_max'):
                return ExtractedValue(
                    value_type=base_type,
                    value_max=float(groups[0]),
                    unit=self._normalize_unit(groups[1] if len(groups) > 1 else None),
                    context=self._detect_context(value_type, match, full_text),
                    raw_match=match.group(0)
                )
            else:
                # Check if the pattern captured context (like front/side/rear)
                context = None
                if 'setback' in value_type:
                    # Some setback patterns capture context in group 3
                    if len(groups) >= 3 and groups[2]:
                        context = groups[2].lower()
                    elif len(groups) >= 1 and groups[0] and not groups[0].replace('.', '').isdigit():
                        # First group might be context (e.g., "front setback of 6m")
                        context = groups[0].lower()
                        # Shift to get the actual number
                        if len(groups) >= 2:
                            return ExtractedValue(
                                value_type=base_type,
                                value_exact=float(groups[1]),
                                unit=self._normalize_unit(groups[2] if len(groups) > 2 else None),
                                context=context,
                                raw_match=match.group(0)
                            )

                return ExtractedValue(
                    value_type=base_type,
                    value_exact=float(groups[0]),
                    unit=self._normalize_unit(groups[1] if len(groups) > 1 else None),
                    context=context or self._detect_context(value_type, match, full_text),
                    raw_match=match.group(0)
                )

        except (ValueError, IndexError):
            return None

    @staticmethod
    def _convert_mm_to_m(ev: 'ExtractedValue') -> 'ExtractedValue':
        """Convert millimetre values to metres for consistency."""
        if ev.unit != 'mm':
            return ev
        if ev.value_min is not None:
            ev.value_min = ev.value_min / 1000.0
        if ev.value_max is not None:
            ev.value_max = ev.value_max / 1000.0
        if ev.value_exact is not None:
            ev.value_exact = ev.value_exact / 1000.0
        ev.unit = 'm'
        return ev

    def _normalize_unit(self, unit: Optional[str]) -> Optional[str]:
        """Normalize unit strings to standard forms."""
        if not unit:
            return None

        unit = unit.lower().strip()

        # Normalize variations
        if unit in ('m', 'metre', 'metres', 'meter', 'meters'):
            return 'm'
        if unit in ('m2', 'm²', 'sqm', 'square metres', 'square meters'):
            return 'm2'
        if unit in ('mm', 'millimetre', 'millimetres', 'millimeter', 'millimeters'):
            return 'mm'
        if unit in ('storey', 'storeys', 'story', 'stories'):
            return 'storeys'
        if unit == '%':
            return '%'

        return unit

    def _detect_context(self, value_type: str, match: re.Match, full_text: str) -> Optional[str]:
        """Detect context (front/side/rear) from surrounding text."""
        if 'setback' not in value_type:
            return None

        # Check within a window around the match
        start = max(0, match.start() - 50)
        end = min(len(full_text), match.end() + 50)
        window = full_text[start:end].lower()

        for context, pattern in self.context_patterns.items():
            if pattern.search(window):
                return context

        return None

    def _deduplicate(self, values: List[ExtractedValue]) -> List[ExtractedValue]:
        """Remove duplicate values based on type and value."""
        seen = set()
        unique = []

        for v in values:
            # Create a key for deduplication
            key = (
                v.value_type,
                v.value_min,
                v.value_max,
                v.value_exact,
                v.context
            )

            if key not in seen:
                seen.add(key)
                unique.append(v)

        return unique


def extract_numeric_values(text: str) -> Dict[str, Any]:
    """
    Convenience function to extract numeric values from text.

    Args:
        text: The provision text to analyze

    Returns:
        Dictionary with has_numeric, values, value_count
    """
    extractor = NumericExtractor()
    return extractor.extract(text)


# CLI for testing
if __name__ == "__main__":
    import sys

    test_texts = [
        "Buildings must be setback a minimum of 6 metres from the front boundary.",
        "Maximum building height of 9m or 2 storeys.",
        "FSR 0.5:1 applies to residential development.",
        "Minimum lot size of 450m2 with frontage width of 12m.",
        "Site coverage must not exceed 60%. Minimum 30% landscaping required.",
        "Front setback minimum 6m, side setback 0.9m.",
        "Deep soil zone of at least 15% of site area.",
        "The rear setback must be a minimum of 8 metres.",
        "Height limit 8.5m. Maximum 2 storeys.",
    ]

    extractor = NumericExtractor()

    for text in test_texts:
        print(f"\n{'='*60}")
        print(f"TEXT: {text}")
        result = extractor.extract(text)
        print(f"HAS NUMERIC: {result['has_numeric']}")
        print(f"VALUES ({result['value_count']}):")
        for v in result['values']:
            print(f"  - {v}")
