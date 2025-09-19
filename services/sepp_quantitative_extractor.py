from db_config import get_connection
from typing import Dict, List, Optional, Tuple
import re
import json

class SEPPQuantitativeExtractor:
    """Extract quantitative requirements from SEPP provisions"""

    # Known SEPP clause mappings with quantitative values
    SEPP_MAPPINGS = {
        'SEPP_HOUSING_2021': {
            '3.31': {
                'title': 'Low-rise housing diversity',
                'min_lot_size': 450,
                'unit': 'sqm',
                'context': 'minimum_lot_size'
            },
            '3.32': {
                'title': 'Manor houses',
                'min_lot_size': 600,
                'unit': 'sqm',
                'context': 'minimum_lot_size'
            },
            '3.33': {
                'title': 'Terraces',
                'min_lot_size': 300,
                'unit': 'sqm',
                'context': 'minimum_lot_size'
            }
        },
        'SEPP_EXEMPT_2008': {
            '2.1': {
                'title': 'General development requirements',
                'max_height': 3,
                'unit': 'm',
                'context': 'maximum_height'
            }
        }
    }

    # Regex patterns for quantitative extraction
    EXTRACTION_PATTERNS = {
        'lot_size': r'(\d+(?:\.\d+)?)\s*(?:square\s*metres?|sqm|m²|m2)',
        'height': r'(\d+(?:\.\d+)?)\s*(?:metres?|m)\s*(?:high|height|above|maximum)',
        'setback': r'(\d+(?:\.\d+)?)\s*(?:metres?|m)\s*(?:setback|from)',
        'percentage': r'(\d+(?:\.\d+)?)\s*(?:%|percent|per\s*cent)',
        'floor_space_ratio': r'(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)',
        'area': r'(\d+(?:\.\d+)?)\s*(?:hectares?|ha)'
    }

    def __init__(self):
        self.db = get_connection()

    def extract_from_provision_text(self, provision_text: str) -> List[Dict]:
        """Extract quantitative values from provision text using regex patterns"""
        extractions = []

        for context, pattern in self.EXTRACTION_PATTERNS.items():
            matches = re.findall(pattern, provision_text, re.IGNORECASE)

            for match in matches:
                if isinstance(match, tuple):
                    # Handle ratio matches (FSR)
                    if context == 'floor_space_ratio' and len(match) == 2:
                        value = f"{match[0]}:{match[1]}"
                        numeric_value = float(match[0]) / float(match[1]) if match[1] != '0' else float(match[0])
                    else:
                        numeric_value = float(match[0]) if match[0] else None
                        value = match[0]
                else:
                    numeric_value = float(match)
                    value = match

                if numeric_value is not None:
                    # Determine unit based on context
                    unit = self._get_unit_for_context(context)

                    # Validate range to avoid outliers
                    if self._validate_value_range(context, numeric_value):
                        extractions.append({
                            'measurement_context': context,
                            'numeric_value': numeric_value,
                            'unit': unit,
                            'raw_match': value,
                            'confidence': self._calculate_confidence(context, provision_text, value)
                        })

        return extractions

    def extract_from_sepp_clause(self, sepp_type: str, clause: str) -> Optional[Dict]:
        """Extract known quantitative values from SEPP clause mappings"""

        if sepp_type in self.SEPP_MAPPINGS and clause in self.SEPP_MAPPINGS[sepp_type]:
            clause_data = self.SEPP_MAPPINGS[sepp_type][clause]

            # Convert to standard format
            if 'min_lot_size' in clause_data:
                return {
                    'measurement_context': 'minimum_lot_size',
                    'numeric_value': clause_data['min_lot_size'],
                    'unit': clause_data['unit'],
                    'provision_text': clause_data['title'],
                    'confidence': 1.0  # Known mappings have highest confidence
                }
            elif 'max_height' in clause_data:
                return {
                    'measurement_context': 'maximum_height',
                    'numeric_value': clause_data['max_height'],
                    'unit': clause_data['unit'],
                    'provision_text': clause_data['title'],
                    'confidence': 1.0
                }

        return None

    def extract_from_database_provisions(self, sepp_type: str, limit: int = 50) -> List[Dict]:
        """Extract quantitative values from SEPP provisions in database"""
        cursor = self.db.cursor()

        # Get SEPP provisions containing quantitative data
        cursor.execute("""
            SELECT provision_text, ref_number, section_header
            FROM sepp_provisions
            WHERE provision_text ~ %s
            AND (ref_number ILIKE %s OR section_header ILIKE %s)
            LIMIT %s
        """, (
            r'[0-9]+\.?[0-9]*\s*(m|sqm|%|metres|square|ratio|height|width|setback)',
            f'%{sepp_type.split("_")[1] if "_" in sepp_type else sepp_type}%',
            f'%{sepp_type.split("_")[1] if "_" in sepp_type else sepp_type}%',
            limit
        ))

        database_extractions = []
        for provision_text, ref_number, section_header in cursor.fetchall():
            extractions = self.extract_from_provision_text(provision_text)

            for extraction in extractions:
                database_extractions.append({
                    **extraction,
                    'source': 'database_provision',
                    'ref_number': ref_number,
                    'section_header': section_header,
                    'provision_text': provision_text[:200] + '...' if len(provision_text) > 200 else provision_text
                })

        return database_extractions

    def _get_unit_for_context(self, context: str) -> str:
        """Get standard unit for measurement context"""
        unit_map = {
            'lot_size': 'sqm',
            'height': 'm',
            'setback': 'm',
            'percentage': '%',
            'floor_space_ratio': 'ratio',
            'area': 'ha'
        }
        return unit_map.get(context, 'unit')

    def _validate_value_range(self, context: str, value: float) -> bool:
        """Validate that extracted value is within reasonable range"""
        ranges = {
            'lot_size': (50, 50000),      # 50sqm to 5 hectares
            'height': (0.5, 500),         # 0.5m to 500m
            'setback': (0, 100),          # 0m to 100m
            'percentage': (0, 100),       # 0% to 100%
            'floor_space_ratio': (0.1, 10), # 0.1:1 to 10:1
            'area': (0.01, 1000)          # 0.01ha to 1000ha
        }

        if context in ranges:
            min_val, max_val = ranges[context]
            return min_val <= value <= max_val

        return True  # Accept if no range defined

    def _calculate_confidence(self, context: str, full_text: str, matched_value: str) -> float:
        """Calculate confidence score for extraction"""
        confidence = 0.7  # Base confidence

        # Higher confidence for explicit unit matches
        unit_indicators = {
            'lot_size': ['lot size', 'site area', 'land area'],
            'height': ['height', 'high', 'above ground'],
            'setback': ['setback', 'from boundary', 'from edge'],
            'percentage': ['percent', '%', 'proportion']
        }

        if context in unit_indicators:
            for indicator in unit_indicators[context]:
                if indicator.lower() in full_text.lower():
                    confidence += 0.1
                    break

        # Higher confidence for specific value formats
        if re.search(r'minimum|maximum|at least|no more than', full_text, re.IGNORECASE):
            confidence += 0.1

        return min(confidence, 1.0)

# Test the extractor
if __name__ == "__main__":
    extractor = SEPPQuantitativeExtractor()

    # Test known SEPP clause
    print("Testing SEPP Housing 2021 clause 3.31:")
    result = extractor.extract_from_sepp_clause('SEPP_HOUSING_2021', '3.31')
    if result:
        print(f"  Found: {result['numeric_value']} {result['unit']} for {result['measurement_context']}")

    # Test database extraction
    print("\nTesting database provision extraction:")
    db_results = extractor.extract_from_database_provisions('HOUSING', limit=5)
    for i, result in enumerate(db_results[:3], 1):
        print(f"  {i}. {result['measurement_context']}: {result['numeric_value']} {result['unit']}")
        print(f"     From: {result['ref_number']} - {result['provision_text'][:100]}...")
        print(f"     Confidence: {result['confidence']:.2f}")
