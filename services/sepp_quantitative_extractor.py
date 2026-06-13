from db_config import get_connection
from typing import Dict, List, Optional, Tuple
import re
import json

class SEPPQuantitativeExtractor:
    """Extract quantitative requirements from SEPP provisions.

    Regulatory values (lot sizes, heights, floor areas) are NEVER hardcoded
    here — they are read live from the authoritative ``housing_sepp_standards``
    table, which carries ``source_clause``, ``legislation_url`` and
    ``effective_date`` for provenance. SEPPs are amended regularly, so any
    embedded numeric table would be wrong within months (see CLAUDE.md
    "Regulatory Data — NEVER Hardcode"). When no standard is on file for a
    clause, lookups return ``None`` so callers surface the absence rather than
    a stale approximation.
    """

    # Regex patterns for quantitative extraction
    EXTRACTION_PATTERNS = {
        'lot_size': r'(\d+(?:\.\d+)?)\s*(?:square\s*metres?|sqm|m�|m2)',
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
        """Look up an authoritative SEPP standard for a clause from the DB.

        Reads ``housing_sepp_standards`` (NOT a hardcoded table) and returns the
        most recently effective standard whose ``source_clause`` matches the
        requested clause. Returns ``None`` when the clause has no standard on
        file or the DB is unavailable — never a fabricated regulatory value.

        Args:
            sepp_type: SEPP identifier (e.g. ``SEPP_HOUSING_2021``). Used to
                scope the lookup to the matching ``source_document``.
            clause: Legislative clause reference as it appears in the provision
                (e.g. ``53(1)(b)``).

        Returns:
            Dict with ``measurement_context``, ``numeric_value``, ``unit``,
            ``confidence`` plus provenance (``source_clause``,
            ``legislation_url``, ``effective_date``), or ``None``.
        """
        if not clause:
            return None

        # Map the SEPP identifier to the document name stored on each row so a
        # clause from one SEPP cannot match an identically-numbered clause in
        # another. Unknown identifiers fall through to a clause-only match.
        doc_filter = None
        if sepp_type and 'HOUSING' in sepp_type.upper():
            doc_filter = '%(Housing)%'
        elif sepp_type and ('EXEMPT' in sepp_type.upper() or 'CODES' in sepp_type.upper()):
            doc_filter = '%(Exempt and Complying Development Codes)%'

        try:
            cursor = self.db.cursor()
            if doc_filter:
                cursor.execute(
                    """
                    SELECT standard_type, numeric_value, unit, source_clause,
                           source_document, legislation_url, effective_date
                    FROM housing_sepp_standards
                    WHERE source_clause = %s
                      AND source_document ILIKE %s
                    ORDER BY effective_date DESC NULLS LAST
                    LIMIT 1
                    """,
                    (clause, doc_filter),
                )
            else:
                cursor.execute(
                    """
                    SELECT standard_type, numeric_value, unit, source_clause,
                           source_document, legislation_url, effective_date
                    FROM housing_sepp_standards
                    WHERE source_clause = %s
                    ORDER BY effective_date DESC NULLS LAST
                    LIMIT 1
                    """,
                    (clause,),
                )
            row = cursor.fetchone()
            cursor.close()
        except Exception:
            # DB unavailable — do not substitute an approximation.
            return None

        if not row:
            return None

        standard_type, numeric_value, unit, source_clause, source_document, legislation_url, effective_date = row
        return {
            'measurement_context': standard_type,
            'numeric_value': float(numeric_value) if numeric_value is not None else None,
            'unit': unit,
            'provision_text': source_document,
            'source_clause': source_clause,
            'legislation_url': legislation_url,
            'effective_date': effective_date.isoformat() if effective_date else None,
            'confidence': 1.0,  # Authoritative DB value
        }

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

    # Look up an authoritative SEPP standard by clause (value comes from the DB)
    print("Looking up SEPP Housing 2021 clause 53(1)(b) (min lot for secondary dwelling):")
    result = extractor.extract_from_sepp_clause('SEPP_HOUSING_2021', '53(1)(b)')
    if result:
        print(f"  Found: {result['numeric_value']} {result['unit']} for {result['measurement_context']}")
        print(f"  Source: {result['source_clause']} — {result['legislation_url']} (effective {result['effective_date']})")
    else:
        print("  No standard on file for that clause (or DB unavailable).")

    # Test database extraction
    print("\nTesting database provision extraction:")
    db_results = extractor.extract_from_database_provisions('HOUSING', limit=5)
    for i, result in enumerate(db_results[:3], 1):
        print(f"  {i}. {result['measurement_context']}: {result['numeric_value']} {result['unit']}")
        print(f"     From: {result['ref_number']} - {result['provision_text'][:100]}...")
        print(f"     Confidence: {result['confidence']:.2f}")
