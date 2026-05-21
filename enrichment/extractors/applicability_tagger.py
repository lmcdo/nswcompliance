#!/usr/bin/env python3
"""
Applicability Tagger

Tags provisions with:
- v2_applicable_zones: Which zones the provision applies to (R2, R3, B1, etc.)
- v2_applicable_dev_types: Which development types (dwelling_house, dual_occupancy, etc.)

Uses DCP-specific configuration to accurately reflect each council's document structure:
- Ashfield: Chapter-based organization (A-F)
- Leichhardt: Part-based organization (A-G)
- Marrickville: Part-based with explicit zone/dev type sections (1-9)

The key insight: document structure determines applicability more reliably than text parsing.
A provision in "Part 4.1 Low Density Residential" APPLIES to low density residential
even if the text doesn't explicitly mention "R2" or "dwelling house".
"""

import re
from typing import List, Tuple, Optional, Set, Dict, Any

# Import DCP configs
from enrichment.config.ashfield_config import ASHFIELD_CONFIG
from enrichment.config.leichhardt_config import LEICHHARDT_CONFIG
from enrichment.config.marrickville_config import MARRICKVILLE_CONFIG
from enrichment.config import COUNCIL_CONFIGS


class ApplicabilityTagger:
    """
    Tag provisions with applicable zones and development types.

    Uses council-specific DCP configuration for accurate inheritance.

    Usage:
        tagger = ApplicabilityTagger()
        zones, dev_types = tagger.tag(text, document_id)
    """

    # Zone patterns - NSW standard zones (for text-based extraction)
    ZONE_PATTERNS = {
        'R1': r'\bR1\b', 'R2': r'\bR2\b', 'R3': r'\bR3\b', 'R4': r'\bR4\b', 'R5': r'\bR5\b',
        'B1': r'\bB1\b', 'B2': r'\bB2\b', 'B3': r'\bB3\b', 'B4': r'\bB4\b',
        'B5': r'\bB5\b', 'B6': r'\bB6\b', 'B7': r'\bB7\b',
        'IN1': r'\bIN1\b', 'IN2': r'\bIN2\b', 'IN3': r'\bIN3\b', 'IN4': r'\bIN4\b',
        'MU1': r'\bMU1\b',
        'SP1': r'\bSP1\b', 'SP2': r'\bSP2\b', 'SP3': r'\bSP3\b',
        'RE1': r'\bRE1\b', 'RE2': r'\bRE2\b',
        'E1': r'\bE1\b', 'E2': r'\bE2\b', 'E3': r'\bE3\b', 'E4': r'\bE4\b',
    }

    # Zone category patterns
    ZONE_CATEGORY_PATTERNS = {
        'residential': (r'\bresidential\s+zone', ['R1', 'R2', 'R3', 'R4', 'R5']),
        'low_density': (r'\blow\s+density', ['R2']),
        'medium_density': (r'\bmedium\s+density', ['R3']),
        'high_density': (r'\bhigh\s+density', ['R4']),
        'business': (r'\bbusiness\s+zone', ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7']),
        'industrial': (r'\bindustrial\s+zone', ['IN1', 'IN2', 'IN3', 'IN4']),
    }

    # Development type patterns (for text-based extraction)
    DEV_TYPE_PATTERNS = {
        'dwelling_house': [r'\bdwelling\s+house', r'\bsingle\s+dwelling', r'\bdetached\s+dwelling'],
        'secondary_dwelling': [r'\bsecondary\s+dwelling', r'\bgranny\s+flat', r'\bancillary\s+dwelling'],
        'dual_occupancy': [r'\bdual\s+occupanc'],
        'multi_dwelling_housing': [r'\bmulti[\s-]?dwelling', r'\bmultiple\s+dwelling', r'\btownhouse'],
        'residential_flat_building': [r'\bresidential\s+flat', r'\bapartment', r'\bRFB'],
        'boarding_house': [r'\bboarding\s+house'],
        'shop_top_housing': [r'\bshop[\s-]?top\s+housing'],
        'commercial_premises': [r'\bcommercial\s+premises', r'\bcommercial\s+development'],
        'retail_premises': [r'\bretail\s+premises', r'\bshop\b'],
        'office_premises': [r'\boffice\s+premises', r'\bcommercial\s+office'],
        'industrial_development': [r'\bindustrial\s+development', r'\bindustrial\s+premises'],
        'warehouse': [r'\bwarehouse', r'\bstorage\s+premises'],
        'light_industry': [r'\blight\s+industr'],
        'child_care_centre': [r'\bchild\s*care', r'\bchild[\s-]?minding'],
        'food_and_drink_premises': [r'\bfood\s+and\s+drink', r'\brestaurant', r'\bcafe\b'],
        'sex_services_premises': [r'\bsex\s+services', r'\badult\s+premises'],
    }

    def __init__(self):
        """Initialize with compiled patterns and DCP configs."""
        self.zone_patterns = {
            zone: re.compile(pattern, re.IGNORECASE)
            for zone, pattern in self.ZONE_PATTERNS.items()
        }

        self.zone_category_patterns = {
            cat: (re.compile(pattern, re.IGNORECASE), zones)
            for cat, (pattern, zones) in self.ZONE_CATEGORY_PATTERNS.items()
        }

        self.dev_type_patterns = {
            dev_type: [re.compile(p, re.IGNORECASE) for p in patterns]
            for dev_type, patterns in self.DEV_TYPE_PATTERNS.items()
        }

        # DCP configs indexed by detection patterns
        self.dcp_configs = {
            'ashfield': ASHFIELD_CONFIG,
            'leichhardt': LEICHHARDT_CONFIG,
            'marrickville': MARRICKVILLE_CONFIG,
        }

    def _detect_council(self, document_id: str) -> Optional[str]:
        """Detect which council's DCP this document belongs to."""
        if not document_id:
            return None

        doc_lower = document_id.lower()

        if 'ashfield' in doc_lower:
            return 'ashfield'
        elif 'leichhardt' in doc_lower:
            return 'leichhardt'
        elif 'marrickville' in doc_lower:
            return 'marrickville'

        return None

    def _get_ashfield_config(self, document_id: str) -> Dict[str, Any]:
        """Get applicability config for Ashfield DCP provision."""
        config = ASHFIELD_CONFIG

        # Normalize document_id for matching
        doc = document_id.replace('_', ' ').replace('  ', ' ')

        # Check Chapter F parts first (most specific)
        if 'Chapter F' in doc or 'Chapter_F' in document_id:
            for part_key, part_config in config.get('chapter_f_parts', {}).items():
                # Match Part_X patterns
                part_num = part_key.replace('Part_', '')
                if f'Part_{part_num}' in document_id or f'Part {part_num}' in doc:
                    return {
                        'applicable_zones': part_config.get('applicable_zones', ['ALL']),
                        'applicable_dev_types': part_config.get('applicable_dev_types', ['ALL']),
                        'site_conditions': None,
                    }

        # Check main chapters - use regex for better matching
        chapter_patterns = [
            ('Chapter E1', 'Chapter E1'),
            ('Chapter_E1', 'Chapter E1'),
            ('Chapter A', 'Chapter A'),
            ('Chapter_A', 'Chapter A'),
            ('Chapter B', 'Chapter B'),
            ('Chapter_B', 'Chapter B'),
            ('Chapter C', 'Chapter C'),
            ('Chapter_C', 'Chapter C'),
            ('Chapter D', 'Chapter D'),
            ('Chapter_D', 'Chapter D'),
            ('Chapter F', 'Chapter F'),
            ('Chapter_F', 'Chapter F'),
        ]

        for pattern, chapter_key in chapter_patterns:
            if pattern in document_id or pattern in doc:
                chapter_config = config.get('chapters', {}).get(chapter_key, {})
                if chapter_config:
                    return {
                        'applicable_zones': chapter_config.get('applicable_zones', ['ALL']),
                        'applicable_dev_types': chapter_config.get('applicable_dev_types', ['ALL']),
                        'site_conditions': chapter_config.get('site_conditions'),
                        'is_precinct_specific': chapter_config.get('is_precinct_specific', False),
                    }

        return {'applicable_zones': ['ALL'], 'applicable_dev_types': ['ALL'], 'site_conditions': None}

    def _get_leichhardt_config(self, document_id: str) -> Dict[str, Any]:
        """Get applicability config for Leichhardt DCP provision."""
        config = LEICHHARDT_CONFIG

        # Normalize for matching
        doc = document_id.replace('_', ' ').replace('  ', ' ')

        # Check for Distinctive Neighbourhoods (Part C Section 2)
        if 'Section_2' in document_id or 'Section 2' in doc or 'C2_2' in document_id:
            return {
                'applicable_zones': ['ALL'],
                'applicable_dev_types': ['ALL'],
                'site_conditions': None,
                'is_precinct_specific': True,
            }

        # Check for Part G (Neighbourhoods)
        if 'Part G' in doc or 'Part_G' in document_id:
            return {
                'applicable_zones': ['ALL'],
                'applicable_dev_types': ['ALL'],
                'site_conditions': None,
                'is_precinct_specific': True,
            }

        # Check main parts
        for part_key, part_config in config.get('parts', {}).items():
            # Match "Part X" patterns
            part_pattern = part_key.replace(' ', '_')
            if part_pattern in document_id or part_key in doc:
                return {
                    'applicable_zones': part_config.get('applicable_zones', ['ALL']),
                    'applicable_dev_types': part_config.get('applicable_dev_types', ['ALL']),
                    'site_conditions': part_config.get('site_conditions'),
                    'is_precinct_specific': part_config.get('is_precinct_specific', False),
                }

        return {'applicable_zones': ['ALL'], 'applicable_dev_types': ['ALL'], 'site_conditions': None}

    def _get_marrickville_config(self, document_id: str) -> Dict[str, Any]:
        """Get applicability config for Marrickville DCP provision."""
        config = MARRICKVILLE_CONFIG

        # Normalize for matching
        doc = document_id.replace('__', '_').replace('_', ' ')

        # Check for Part 9.x precincts FIRST (most specific)
        # Match patterns like 9_6, 9.6, 9__6
        precinct_match = re.search(r'[_\-]9[_\.](\d+)[_\-]', document_id)
        if precinct_match:
            precinct_num = precinct_match.group(1)
            precinct_key = f'9_{precinct_num}'
            if precinct_key in config.get('precincts', {}):
                defaults = config.get('precinct_defaults', {})
                return {
                    'applicable_zones': defaults.get('applicable_zones', ['ALL']),
                    'applicable_dev_types': defaults.get('applicable_dev_types', ['ALL']),
                    'site_conditions': defaults.get('site_conditions'),
                    'is_precinct_specific': True,
                }

        # Also check for "Precinct" keyword with number
        if 'Precinct' in document_id:
            defaults = config.get('precinct_defaults', {})
            return {
                'applicable_zones': defaults.get('applicable_zones', ['ALL']),
                'applicable_dev_types': defaults.get('applicable_dev_types', ['ALL']),
                'site_conditions': defaults.get('site_conditions'),
                'is_precinct_specific': True,
            }

        # Check for Heritage (Part 8) - before other matches
        if '8.0' in document_id or '__8__' in document_id or '_8_' in document_id:
            heritage_config = config.get('parts', {}).get('8', {})
            return {
                'applicable_zones': ['ALL'],
                'applicable_dev_types': ['ALL'],
                'site_conditions': ['heritage'],
                'is_precinct_specific': False,
            }
        if 'Heritage' in document_id:
            return {
                'applicable_zones': ['ALL'],
                'applicable_dev_types': ['ALL'],
                'site_conditions': ['heritage'],
                'is_precinct_specific': False,
            }

        # Check for specific development type sections BEFORE generic matching
        # Part 4.1 - Low Density Residential
        if '4.1' in document_id or '__4_1__' in document_id or '_4_1_' in document_id or 'Low_Density' in document_id or 'Low__Density' in document_id:
            return {
                'applicable_zones': ['R2'],
                'applicable_dev_types': ['dwelling_house', 'secondary_dwelling', 'dual_occupancy'],
                'site_conditions': None,
            }

        # Part 4.2 - Multi Dwelling Housing
        if '4.2' in document_id or '__4_2__' in document_id or '_4_2_' in document_id or 'Multi_Dwelling' in document_id or 'Multi__Dwelling' in document_id:
            return {
                'applicable_zones': ['R3', 'R4'],
                'applicable_dev_types': ['multi_dwelling_housing', 'residential_flat_building', 'attached_dwelling'],
                'site_conditions': None,
            }

        # Part 4.3 - Boarding Houses
        if '4.3' in document_id or '__4_3__' in document_id or '_4_3_' in document_id or 'Boarding' in document_id:
            return {
                'applicable_zones': ['ALL'],
                'applicable_dev_types': ['boarding_house'],
                'site_conditions': None,
            }

        # Part 5 - Commercial and Mixed Use
        if '5_0' in document_id or '__5__0__' in document_id or '5.0' in document_id:
            return {
                'applicable_zones': ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'MU1'],
                'applicable_dev_types': ['commercial_premises', 'retail_premises', 'office_premises', 'shop_top_housing'],
                'site_conditions': None,
            }
        # Also match "Commercial" but NOT "Commercial_Precinct" (which is Part 9)
        if 'Commercial' in document_id and 'Precinct' not in document_id:
            return {
                'applicable_zones': ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'MU1'],
                'applicable_dev_types': ['commercial_premises', 'retail_premises', 'office_premises', 'shop_top_housing'],
                'site_conditions': None,
            }

        # Part 6 - Industrial Development
        if '6_0' in document_id or '__6__0__' in document_id or '6.0' in document_id:
            return {
                'applicable_zones': ['IN1', 'IN2', 'IN3', 'IN4'],
                'applicable_dev_types': ['industrial_development', 'warehouse', 'light_industry'],
                'site_conditions': None,
            }
        # Also match "Industrial" but NOT "Industrial_Precinct" (which is Part 9)
        if 'Industrial' in document_id and 'Precinct' not in document_id:
            return {
                'applicable_zones': ['IN1', 'IN2', 'IN3', 'IN4'],
                'applicable_dev_types': ['industrial_development', 'warehouse', 'light_industry'],
                'site_conditions': None,
            }

        # Part 7.1 - Childcare
        if '7.1' in document_id or '7_1' in document_id or 'childcare' in document_id.lower():
            return {
                'applicable_zones': ['ALL'],
                'applicable_dev_types': ['child_care_centre', 'centre_based_childcare'],
                'site_conditions': None,
            }

        # Part 7.3 - Sex Industry
        if '7.3' in document_id or 'Sex' in document_id:
            return {
                'applicable_zones': ['B3', 'B4', 'IN1', 'IN2'],
                'applicable_dev_types': ['sex_services_premises', 'restricted_premises'],
                'site_conditions': None,
            }

        # Part 2.x - General Controls (apply to ALL)
        if re.search(r'[_\-]2[_\.](\d+)[_\-]', document_id) or '__2__' in document_id:
            return {
                'applicable_zones': ['ALL'],
                'applicable_dev_types': ['ALL'],
                'site_conditions': None,
            }

        # Part 1 - Statutory (apply to ALL)
        if '__1__' in document_id or '_1_' in document_id:
            return {
                'applicable_zones': ['ALL'],
                'applicable_dev_types': ['ALL'],
                'site_conditions': None,
            }

        # Part 3 - Subdivision
        if '__3__' in document_id or '_3_' in document_id or 'Subdivision' in document_id:
            return {
                'applicable_zones': ['ALL'],
                'applicable_dev_types': ['subdivision'],
                'site_conditions': None,
            }

        return {'applicable_zones': ['ALL'], 'applicable_dev_types': ['ALL'], 'site_conditions': None}

    def _get_config_driven(self, document_id: str, text: str) -> Optional[Dict[str, Any]]:
        """Get applicability from COUNCIL_CONFIGS (woollahra, waverley, etc.).

        Uses the same section-code extraction as LayerTopicTagger._tag_from_config().
        Returns None if no config matches (falls through to text extraction).
        """
        doc_lower = document_id.lower()
        config = None
        for council_key, cfg in COUNCIL_CONFIGS.items():
            if council_key in doc_lower:
                config = cfg
                break
        if not config:
            return None

        parts = config.get("parts", {})
        chapter_topics = config.get("chapter_topics")

        # chapter_topics path (City of Sydney, Ku-ring-gai)
        if chapter_topics:
            for chapter_key, entry in chapter_topics.items():
                if chapter_key in doc_lower:
                    return {
                        'applicable_zones': entry.get('applicable_zones', ['ALL']),
                        'applicable_dev_types': entry.get('applicable_dev_types', ['ALL']),
                        'site_conditions': entry.get('site_conditions'),
                    }
            return None

        # parts path (Woollahra, Waverley) — extract section code from heading
        section_code = self._extract_section_code(text)
        if not section_code:
            # Fallback: extract chapter code from document_id for preamble provisions
            # e.g. "Woollahra_DCP_2015__chapter_b1_residential_precincts" → "B1"
            doc_match = re.search(r'chapter_([a-z]\d+)', doc_lower)
            if doc_match:
                section_code = doc_match.group(1).upper()
            else:
                return None

        entry = parts.get(section_code)

        # Progressive strip: "C1.2" → "C1" → "C"
        if not entry:
            code = section_code
            while code and not entry:
                shorter = re.sub(r'\.?\d+$', '', code)
                if shorter == code:
                    break
                code = shorter
                entry = parts.get(code)

        # Letter-only prefix
        if not entry and section_code[0].isalpha():
            entry = parts.get(section_code[0])

        if entry:
            return {
                'applicable_zones': entry.get('applicable_zones', ['ALL']),
                'applicable_dev_types': entry.get('applicable_dev_types', ['ALL']),
                'site_conditions': entry.get('site_conditions'),
            }

        return None

    @staticmethod
    def _extract_section_code(text: str) -> Optional[str]:
        """Extract section code from markdown heading (e.g. '# B3.1 Site Coverage' → 'B3.1')."""
        match = re.match(r'^#\s+([A-Z]?\d+(?:\.\d+)*)', (text or '').strip())
        return match.group(1) if match else None

    def _extract_zones_from_text(self, text: str) -> Set[str]:
        """Extract explicit zone mentions from provision text."""
        zones = set()

        for zone, pattern in self.zone_patterns.items():
            if pattern.search(text):
                zones.add(zone)

        for cat, (pattern, category_zones) in self.zone_category_patterns.items():
            if pattern.search(text):
                zones.update(category_zones)

        return zones

    def _extract_dev_types_from_text(self, text: str) -> Set[str]:
        """Extract explicit development type mentions from provision text."""
        dev_types = set()

        for dev_type, patterns in self.dev_type_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    dev_types.add(dev_type)
                    break

        return dev_types

    def tag(self, text: str, document_id: str = None) -> Tuple[List[str], List[str]]:
        """
        Tag provision with applicable zones and development types.

        Strategy:
        1. Detect which council's DCP this is from
        2. Get structural applicability from DCP config (most reliable)
        3. Extract any additional specific mentions from text
        4. Combine results, preferring structural inheritance

        Args:
            text: The provision text
            document_id: Document identifier for structure-based inheritance

        Returns:
            Tuple of (zones, dev_types) where each is a list of applicable values
        """
        zones: Set[str] = set()
        dev_types: Set[str] = set()
        config = None

        # 1. Get structural config based on document_id
        if document_id:
            council = self._detect_council(document_id)

            if council == 'ashfield':
                config = self._get_ashfield_config(document_id)
            elif council == 'leichhardt':
                config = self._get_leichhardt_config(document_id)
            elif council == 'marrickville':
                config = self._get_marrickville_config(document_id)
            else:
                # Config-driven path: woollahra, waverley, city_of_sydney, ku_ring_gai
                config = self._get_config_driven(document_id, text)

            if config:
                struct_zones = config.get('applicable_zones', ['ALL'])
                struct_dev_types = config.get('applicable_dev_types', ['ALL'])

                # Use structural config as base
                if struct_zones != ['ALL']:
                    zones.update(struct_zones)
                if struct_dev_types != ['ALL']:
                    dev_types.update(struct_dev_types)

        # 2. Extract from text (supplement structural config)
        # Skip text extraction for config-driven councils — the config is
        # authoritative, and text regex produces false positives (e.g. matching
        # DCP chapter codes "B3", "E1" as zone codes).
        if text and not config:
            text_zones = self._extract_zones_from_text(text)
            text_dev_types = self._extract_dev_types_from_text(text)

            if text_zones:
                zones.update(text_zones)
            if text_dev_types:
                dev_types.update(text_dev_types)

        # 3. Default to ALL if nothing specific found
        if not zones:
            zones.add('ALL')
        if not dev_types:
            dev_types.add('ALL')

        return sorted(list(zones)), sorted(list(dev_types))


def tag_applicability(text: str, document_id: str = None) -> Tuple[List[str], List[str]]:
    """Convenience function for tagging."""
    tagger = ApplicabilityTagger()
    return tagger.tag(text, document_id)


# CLI for testing
if __name__ == "__main__":
    test_cases = [
        # Ashfield - Heritage chapter
        ("Development in heritage conservation areas must...", "Inner West Ashfield DCP 2016 - Chapter E1 - Heritage"),
        # Ashfield - General chapter
        ("All development must comply with...", "Inner West Ashfield DCP 2016 - Chapter A - Miscellaneous"),

        # Marrickville - Low density residential
        ("Setback minimum 6m.", "Marrickville__DCP__2011__-__4.1__Low__Density__Residential__Development"),
        # Marrickville - Heritage
        ("Heritage items must be conserved.", "Marrickville__DCP__2011__-__8.0__Heritage"),
        # Marrickville - Precinct
        ("Development in this precinct...", "Marrickville__DCP__2011__-__9__6__Petersham__South__Precinct__6"),

        # Leichhardt - Energy
        ("Energy efficiency requirements.", "Leichhardt DCP 2013 - 9 - Part D Energy - with IWLEP 2022 amendments"),
        # Leichhardt - Neighbourhood
        ("This distinctive neighbourhood...", "Leichhardt_DCP_2013_Part_C_Section_2_C2_2_1_1_Young_Street_Distinctive_Neighbourhood"),

        # Text-based zone extraction
        ("This applies to R2 and R3 zones.", None),
        # Text-based dev type extraction
        ("Dwelling houses must have minimum setback.", None),

        # General (should return ALL)
        ("Development must maintain character.", None),
    ]

    tagger = ApplicabilityTagger()

    print("=== DCP-Aware Applicability Tagger Tests ===\n")
    for text, doc_id in test_cases:
        zones, dev_types = tagger.tag(text, doc_id)
        print(f"Zones: {zones}")
        print(f"Dev Types: {dev_types}")
        print(f"  Text: {text[:60]}...")
        if doc_id:
            print(f"  Doc: {doc_id[:60]}...")
        print()
