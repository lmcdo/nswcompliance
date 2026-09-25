#!/usr/bin/env python3
"""
Layer + Topic Tagger for 4-Layer Model

Assigns provisions to one of 4 layers based on document_id:
- generic: Part 2 (Marrickville), Section 1 (Leichhardt), Chapter F (Ashfield) - ALWAYS apply
- use_specific: Part 4 (Marrickville), Section 3 (Leichhardt) - Zone-filtered
- condition: Part 8 (Marrickville), Chapter E1 (Ashfield) - Heritage/flood filtered
- precinct: Part 9 (Marrickville), Section 2 (Leichhardt), Chapter D (Ashfield) - Location-filtered

Also extracts topic from section numbers or markers.

Config-driven path: Waverley and all new LGAs are handled by _tag_from_config(),
driven by enrichment/config/COUNCIL_CONFIGS. Inner West councils (marrickville,
leichhardt, ashfield) keep dedicated _tag_x() methods because their document_ids
encode structural info directly rather than via provision_text headings.
"""
import re
import sys
import os
from typing import Tuple, Optional

# Import config-driven registry (enrichment package must be on sys.path)
try:
    from enrichment.config import COUNCIL_CONFIGS
except ImportError:
    # Fallback: empty registry if enrichment package not on path
    COUNCIL_CONFIGS: dict = {}


class LayerTopicTagger:
    """Tags provisions with DCP layer and topic based on document_id."""

    # Marrickville Part 2 sections -> topics
    MARRICKVILLE_PART2_TOPICS = {
        '2.1': 'general',
        '2.2': 'general',
        '2.3': 'site_analysis',
        '2.4': 'building_design',
        '2.5': 'setbacks',
        '2.6': 'privacy',
        '2.7': 'solar',
        '2.8': 'views',
        '2.9': 'fencing',
        '2.10': 'parking',
        '2.11': 'access',
        '2.12': 'safety',
        '2.13': 'signage',
        '2.14': 'environmental',
        '2.15': 'contamination',
        '2.16': 'stormwater',
        '2.17': 'wsud',
        '2.18': 'landscaping',
        '2.19': 'trees',
        '2.20': 'infrastructure',
        '2.21': 'waste',
    }

    # Leichhardt C markers -> topics
    LEICHHARDT_C_TOPICS = {
        'C1': 'site_analysis',
        'C2': 'heritage',
        'C3': 'parking',
        'C4': 'building_form',
        'C5': 'roofing',
        'C6': 'landscaping',
        'C7': 'fencing',
        'C8': 'setbacks',
        'C9': 'trees',
        'C10': 'trees',
        'C11': 'trees',
        'C12': 'flooding',
        'C13': 'contamination',
        'C14': 'parking',
        'C15': 'parking',
        'C16': 'parking',
        'C17': 'parking',
        'C18': 'bicycle_parking',
        'C19': 'bicycle_parking',
        'C20': 'bicycle_parking',
        'C21': 'bicycle_parking',
        'C22': 'access',
        'C23': 'landscaping',
        'C24': 'building_design',
        'C25': 'building_design',
        'C26': 'open_space',
        'C27': 'building_design',
        'C28': 'building_design',
        'C29': 'privacy',
        'C30': 'solar',
        'C31': 'views',
        'C32': 'setbacks',
        'C33': 'height',
        'C34': 'building_form',
        'C35': 'building_form',
        'C36': 'safety',
        'C37': 'heritage',
        'C38': 'signage',
        'C39': 'signage',
        'C40': 'advertising',
        'C41': 'advertising',
        'C42': 'advertising',
        'C43': 'vehicle_access',
        'C44': 'vehicle_access',
        'C45': 'vehicle_access',
        'C46': 'vehicle_access',
        'C47': 'vehicle_access',
        'C48': 'vehicle_access',
        'C49': 'vehicle_access',
        'C50': 'vehicle_access',
        'C51': 'vehicle_access',
        'C52': 'vehicle_access',
        'C53': 'vehicle_access',
        'C54': 'vehicle_access',
        'C55': 'vehicle_access',
    }

    # Waverley DCP 2022 Part B section codes -> topics
    WAVERLEY_PART_B_TOPICS = {
        'B1':  'waste',
        'B2':  'sustainability',
        'B3':  'landscaping',
        'B4':  'coastal',
        'B5':  'water',
        'B6':  'accessibility',
        'B7':  'transport',
        'B8':  'heritage',
        'B9':  'safety',
        'B10': 'public_art',
        'B11': 'design_excellence',
        'B12': 'subdivision',
        'B13': 'excavation',
        'B14': 'signage',
        'B15': 'public_domain',
        'B16': 'inter_war_buildings',
        'B17': 'social_impact',
    }

    # Topic keywords for fallback matching (expanded for better accuracy)
    # Note: Order matters - more specific patterns should come first in each regex
    TOPIC_KEYWORDS = {
        'setbacks': r'\bsetback|boundary\s+distance|front\s+yard|rear\s+yard|side\s+yard|building\s+line|rear\s+boundary|side\s+boundary',
        'height': r'\bbuilding\s+height|maximum\s+height|height\s+limit|height\b|storey|floor\s+level',
        'parking': r'\bparking\s+space|car\s*space|off-street\s+parking|parking\b|garage\b|vehicle\s+space',
        'solar': r'\bsolar\s+access|overshadow|sunlight|daylight|northern\s+aspect',
        'privacy': r'\bvisual\s+privacy|privacy\s+screen|privacy\b|overlooking|window\s+separation',
        'landscaping': r'\blandscape\s+plan|soft\s+landscap|deep\s+soil|landscap|garden\b|planting\b',
        'heritage': r'\bheritage\s+conservation|heritage\s+item|heritage\b|HCA\b|contributory|historic',
        'trees': r'\bsignificant\s+tree|tree\s+preservation|tree\b|canopy\b|arborist',
        'fencing': r'\bfront\s+fence|boundary\s+fence|fenc|fence\b',
        'access': r'\bpedestrian\s+access|universal\s+access|disability\s+access|access\b|entry\b|driveway\b',
        'stormwater': r'\bstormwater\s+management|on-site\s+detention|stormwater\b|drainage\b|runoff\b|OSD\b|WSUD\b',
        'waste': r'\bwaste\s+management|bin\s+storage|waste\b|garbage\b|recycling\b|refuse\b',
        'signage': r'\bsignage\b|sign\b',
        'building_form': r'\bbuilt\s+form|bulk\s+and\s+scale|streetscape|bulk\b|scale\b|massing\b',
        'building_design': r'\bfacade\s+articulation|architectural|facade\b|articulation\b|materials\b',
        'open_space': r'\bprivate\s+open\s+space|communal\s+open\s+space|open\s+space|courtyard\b',
        'flooding': r'\bflood\s+planning|flood\s+prone|flood\s+level|flood\b|inundation\b',
        'contamination': r'\bsite\s+contamination|site\s+audit|contaminat|remediat|hazardous',
        'safety': r'\bcrime\s+prevention|CPTED\b|safety\b|surveillance\b|security\b',
        'roofing': r'\broof\s+form|roof\b|pitch\b|eaves\b',
        'views': r'\bview\s+sharing|view\s+corridor|view\b|outlook\b|vista\b',
        'residential': r'\bresidential\b|dwelling\b|apartment\b|house\b|housing\b',
        'commercial': r'\bcommercial\b|retail\b|shop\b|business\s+premises',
        'industrial': r'\bindustrial\b|warehouse\b|factory\b|manufacturing\b',
        'precinct': r'\bprecinct\b|town\s+centre|neighbourhood\b|urban\s+village',
        'density': r'\bdensity\b|lot\s+size|minimum\s+lot|subdivision\s+pattern',
        'environmental': r'\benvironmental\b|ecology\b|habitat\b|biodiversity\b',
        'sustainability': r'\bsustainab|BASIX\b|green\s+star|energy\s+efficien',
        'general': r'\bobjective\b|aim\b|purpose\b|principle\b|guideline\s+applies',
    }

    def tag(self, document_id: str, provision_text: str = '') -> Tuple[str, str, Optional[str]]:
        """
        Tag a provision with layer, part, and topic.

        Args:
            document_id: The document_id from regulatory_provisions
            provision_text: The provision text (for topic extraction)

        Returns:
            Tuple of (layer, part, topic)
        """
        doc_lower = (document_id or '').lower()

        # Inner West councils: dedicated methods (document_id encodes structure)
        if 'marrickville' in doc_lower:
            return self._tag_marrickville(document_id, provision_text)
        elif 'leichhardt' in doc_lower:
            return self._tag_leichhardt(document_id, provision_text)
        elif 'ashfield' in doc_lower:
            return self._tag_ashfield(document_id, provision_text)

        # Config-driven path: Waverley and new LGAs (COUNCIL_CONFIGS registry)
        for council_key, config in COUNCIL_CONFIGS.items():
            if council_key in doc_lower:
                return self._tag_from_config(config, document_id, provision_text)

        # Unknown council - try to infer from text
        return self._tag_unknown(document_id, provision_text)

    def _tag_marrickville(self, document_id: str, provision_text: str) -> Tuple[str, str, Optional[str]]:
        """Tag Marrickville provision."""
        doc = document_id or ''

        # Part 8 / 8.0 - Heritage (condition) - check first as it's most specific
        if '8.0' in doc or '8_0' in doc or 'Heritage' in doc:
            return ('condition', 'Part 8', 'heritage')

        # Part 4.1 - Low Density Residential (use-specific)
        if '4.1' in doc or '4_1' in doc or '4__1' in doc or 'Low_Density' in doc or 'Low__Density' in doc:
            topic = self._extract_topic_from_text(provision_text)
            return ('use_specific', 'Part 4.1', topic)

        # Part 4.2 - Multi-dwelling (use-specific)
        if '4.2' in doc or '4_2' in doc or '4__2' in doc or 'Multi_Dwelling' in doc:
            topic = self._extract_topic_from_text(provision_text)
            return ('use_specific', 'Part 4.2', topic)

        # Part 9 - Precincts (location-filtered) - check BEFORE Part 5/6 since precinct names may include "Commercial" or "Industrial"
        # Use patterns with leading delimiter to avoid matching section numbers like "19" or "29"
        if '_9_' in doc or '_9.' in doc or '_9__' in doc or '-9_' in doc or '-9__' in doc or 'Precinct' in doc:
            topic = self._extract_topic_from_text(provision_text)
            return ('precinct', 'Part 9', topic)

        # Part 5 - Commercial (use-specific)
        if '5_0' in doc or '5.0' in doc or '5__0' in doc or 'Commercial' in doc:
            topic = self._extract_topic_from_text(provision_text)
            return ('use_specific', 'Part 5', topic)

        # Part 6 - Industrial (use-specific)
        if '6_0' in doc or '6.0' in doc or '6__0' in doc or 'Industrial' in doc:
            topic = self._extract_topic_from_text(provision_text)
            return ('use_specific', 'Part 6', topic)

        # Part 2 - Generic (always apply) - check last as fallback
        # Must have "2_" after a dash or underscore to avoid matching "2011"
        if '__2_' in doc or '-_2_' in doc or '__2__' in doc or '_-_2' in doc:
            # First try to get topic from section number in document_id
            topic = self._extract_marrickville_part2_topic_from_docid(doc)
            if not topic:
                # Fall back to keyword matching
                topic = self._extract_topic_from_text(provision_text)
            return ('generic', 'Part 2', topic)

        # Default to generic
        topic = self._extract_topic_from_text(provision_text)
        return ('generic', 'unknown', topic)

    def _tag_leichhardt(self, document_id: str, provision_text: str) -> Tuple[str, str, Optional[str]]:
        """Tag Leichhardt provision."""
        doc = document_id or ''

        # Part G - Site-specific (precinct) - check first, "Part G Section" pattern
        if 'Part G' in doc or 'Part_G' in doc:
            topic = self._extract_topic_from_text(provision_text)
            return ('precinct', 'Part G', topic)

        # Part F - Food (use-specific)
        if 'Part F' in doc or 'Part_F' in doc:
            return ('use_specific', 'Part F', 'food_premises')

        # Part E - Water (generic)
        if 'Part E' in doc or 'Part_E' in doc:
            return ('generic', 'Part E', 'water')

        # Part D - Energy & Waste (generic)
        # Note: Part D has two sections - Energy (pages 2-5) and Waste (pages 6-15)
        # Use keyword matching to determine which section, defaulting to 'energy'
        if 'Part D' in doc or 'Part_D' in doc:
            topic = self._extract_topic_from_text(provision_text)
            # Default to energy if no keywords match (Section 1 is energy)
            if not topic:
                topic = 'energy'
            return ('generic', 'Part D', topic)

        # Part C Section 1 - General (generic, always apply)
        # Pattern: "Part C Place Section 1"
        # FIX DQ-13: Added keyword fallback - many provisions don't start with C marker
        if 'Section 1' in doc or 'Section_1' in doc:
            topic = self._extract_leichhardt_c_topic(provision_text) or self._extract_topic_from_text(provision_text)
            return ('generic', 'Part C Section 1', topic)

        # Part C Section 2 - Neighbourhoods (precinct)
        if 'Section 2' in doc or 'Section_2' in doc or 'Neighbourhood' in doc:
            topic = self._extract_topic_from_text(provision_text)
            return ('precinct', 'Part C Section 2', topic)

        # Part C Section 3 - Residential (use-specific)
        if 'Section 3' in doc or 'Section_3' in doc:
            topic = self._extract_topic_from_text(provision_text)
            return ('use_specific', 'Part C Section 3', topic)

        # Part C Section 4 - Non-Residential (use-specific)
        if 'Section 4' in doc or 'Section_4' in doc:
            topic = self._extract_topic_from_text(provision_text)
            return ('use_specific', 'Part C Section 4', topic)

        # Default - try to determine from text
        topic = self._extract_leichhardt_c_topic(provision_text) or self._extract_topic_from_text(provision_text)
        return ('generic', 'unknown', topic)

    def _tag_ashfield(self, document_id: str, provision_text: str) -> Tuple[str, str, Optional[str]]:
        """Tag Ashfield provision."""
        doc = document_id or ''
        doc_lower = doc.lower()

        # Chapter E1 - Heritage (condition)
        if 'chapter e1' in doc_lower or 'chapter_e1' in doc_lower or ('e1' in doc_lower and 'heritage' in doc_lower):
            return ('condition', 'Chapter E1', 'heritage')

        # Chapter E2 - Haberfield Neighbourhood (precinct)
        if 'chapter e2' in doc_lower or 'chapter_e2' in doc_lower or 'haberfield' in doc_lower:
            topic = self._extract_topic_from_text(provision_text) or 'general'
            return ('precinct', 'Chapter E2', topic)

        # Chapter D - Precincts (location-filtered)
        if 'chapter d' in doc_lower or 'chapter_d' in doc_lower or 'precinct' in doc_lower:
            topic = self._extract_topic_from_text(provision_text) or 'general'
            return ('precinct', 'Chapter D', topic)

        # Chapter F - Development Category (use_specific for Parts 1-7, generic for 8-10)
        if 'chapter f' in doc_lower or 'chapter_f' in doc_lower or 'development category' in doc_lower:
            import re
            combined = doc + ' ' + (provision_text[:500] if provision_text else '')
            part_match = re.search(r'Part[_\s]?(\d+)', combined, re.IGNORECASE)

            if part_match:
                part_num = int(part_match.group(1))
                topic = self._extract_topic_from_text(provision_text) or 'general'
                if part_num <= 7:
                    return ('use_specific', f'Chapter F Part {part_num}', topic)
                else:
                    return ('generic', f'Chapter F Part {part_num}', topic)

            topic = self._extract_topic_from_text(provision_text) or 'general'
            return ('generic', 'Chapter F', topic)

        # Chapter B - Public Domain (generic)
        if 'chapter b' in doc_lower or 'chapter_b' in doc_lower or 'public_domain' in doc_lower:
            topic = self._extract_topic_from_text(provision_text) or 'general'
            return ('generic', 'Chapter B', topic)

        # Chapter A - Miscellaneous (generic)
        if 'chapter a' in doc_lower or 'chapter_a' in doc_lower:
            topic = self._extract_topic_from_text(provision_text) or 'general'
            return ('generic', 'Chapter A', topic)

        # Chapter C - Sustainability (generic)
        if 'chapter c' in doc_lower or 'chapter_c' in doc_lower or 'sustainability' in doc_lower:
            topic = self._extract_topic_from_text(provision_text) or 'general'
            return ('generic', 'Chapter C', topic)

        # Default
        topic = self._extract_topic_from_text(provision_text) or 'general'
        return ('generic', 'unknown', topic)

    def _extract_section_code(self, provision_text: str) -> Optional[str]:
        """
        Extract section code from the markdown heading in provision_text.

        build_provision_text() injects: "# {section_number} {section_title}\\n\\n..."
        e.g. "# B8 Heritage\\n\\n..." → "B8"
             "# C1.2 Character\\n\\n..." → "C1.2"
             "# 4.1.5 Setbacks\\n\\n..." → "4.1.5"

        Returns None if no heading found (e.g. preamble provisions).
        """
        match = re.match(r'^#\s+([A-Z]?\d+(?:\.\d+)*)', (provision_text or '').strip())
        return match.group(1) if match else None

    @staticmethod
    def _entry_layer(entry: dict) -> str:
        """An entry's layer, or the one its other keys imply.

        45 config entries carry no "layer" -- every Canterbury-Bankstown precinct
        chapter among them -- and `entry["layer"]` raised on each of their rows.
        The enrichment loop then refetched the same failing rows forever and
        tagged nothing else (2026-09-25: 500 rows retried seven times, every chapter
        committed since went live untagged). Derived from what the entry states,
        never guessed: a precinct-scoped entry is `precinct`, one gated on a site
        condition is `condition`, anything else `generic`.
        """
        if entry.get("layer"):
            return entry["layer"]
        if entry.get("is_precinct_specific"):
            return "precinct"
        if entry.get("site_conditions"):
            return "condition"
        return "generic"

    def _tag_from_config(
        self, config: dict, document_id: str, provision_text: str
    ) -> Tuple[str, str, Optional[str]]:
        """
        Config-driven tagging for Waverley and new LGAs.

        Handles two config patterns:
        1. `parts` dict (keyed by section code prefix): Woollahra, Waverley
           - Extracts section code from provision_text heading
           - Exact match first (e.g. "C1"), then letter-prefix match (e.g. "C")
           - Special: if config has `part_b_topics`, look up canonical topic for B-sections

        2. `chapter_topics` dict (keyed by chapter_key slug): City of Sydney, Ku-ring-gai
           - Extracts chapter key from document_id (document_id encodes chapter key)
           - Matches normalised document_id against chapter_topics keys
        """
        # ── chapter_topics path (topic encoded in document_id / chapter key) ──────
        chapter_topics = config.get("chapter_topics")
        if chapter_topics:
            doc_lower = document_id.lower()
            for chapter_key, entry in chapter_topics.items():
                if chapter_key in doc_lower:
                    layer = self._entry_layer(entry)
                    topic = entry.get("topic") or self._extract_topic_from_text(provision_text)
                    return (layer, chapter_key, topic)
            # No chapter key matched — fall through to keyword fallback
            topic = self._extract_topic_from_text(provision_text)
            return ('generic', 'unknown', topic or 'general')

        # ── parts path (topic encoded in section heading prefix) ─────────────────
        parts = config.get("parts", {})
        section_code = self._extract_section_code(provision_text)

        if section_code:
            # 1. Exact match (e.g. "B8", "C1")
            entry = parts.get(section_code)

            # 2. If no exact match, try progressively shorter prefixes:
            #    "C1.2" → "C1" → "C"
            if not entry:
                code = section_code
                while code and not entry:
                    # Strip trailing digits (and optional dot before them)
                    shorter = re.sub(r'\.?\d+$', '', code)
                    if shorter == code:
                        break
                    code = shorter
                    entry = parts.get(code)

            # 3. Letter-only prefix (e.g. "B" from "B8")
            if not entry and section_code and section_code[0].isalpha():
                entry = parts.get(section_code[0])

            if entry:
                layer = self._entry_layer(entry)
                # Prefer explicit topic; fall back to part_b_topics lookup; then keyword
                topic = entry.get("topic")
                if not topic:
                    part_b_topics = config.get("part_b_topics", {})
                    topic = part_b_topics.get(section_code)
                if not topic:
                    topic = self._extract_topic_from_text(provision_text)
                return (layer, section_code, topic or 'general')

        # No section code or no match — keyword-only fallback
        topic = self._extract_topic_from_text(provision_text)
        return ('generic', 'unknown', topic or 'general')

    def _tag_unknown(self, document_id: str, provision_text: str) -> Tuple[str, str, Optional[str]]:
        """Tag unknown council provision."""
        topic = self._extract_topic_from_text(provision_text)
        return ('generic', 'unknown', topic)

    def _extract_part_number(self, doc: str, *patterns: str) -> str:
        """Extract part number like 'Part 2.6' from document_id."""
        for pattern in patterns:
            if pattern in doc:
                # Try to find section number after the pattern
                match = re.search(rf'{re.escape(pattern)}[\._\-\s]*(\d+(?:\.\d+)?)', doc)
                if match:
                    return f"{pattern.replace('_', ' ')} {match.group(1)}"
                return pattern.replace('_', ' ')
        return 'unknown'

    def _get_marrickville_part2_topic(self, part: str) -> Optional[str]:
        """Get topic for Marrickville Part 2 section."""
        # Extract section number like "2.6" from "Part 2 2.6" or "Part_2_2.6"
        match = re.search(r'2\.(\d+)', part)
        if match:
            section = f"2.{match.group(1)}"
            return self.MARRICKVILLE_PART2_TOPICS.get(section)
        return None

    def _extract_marrickville_part2_topic_from_docid(self, document_id: str) -> Optional[str]:
        """
        Extract topic from Marrickville Part 2 document_id.

        Examples:
        - "Marrickville__DCP__2011__-__2__10__Parking" -> '2.10' -> 'parking'
        - "Marrickville_DCP_2011_-_2_6_Privacy" -> '2.6' -> 'privacy'
        """
        if not document_id:
            return None

        # Pattern to match section number like "2_10" or "2__10" after DCP year
        # Looking for patterns like: __2__10__ or _2_10_ (section 2.10)
        match = re.search(r'[_-]+2[_-]+(\d+)[_-]', document_id)
        if match:
            section_num = match.group(1)
            section = f"2.{section_num}"
            return self.MARRICKVILLE_PART2_TOPICS.get(section)
        return None

    def _extract_leichhardt_c_topic(self, text: str) -> Optional[str]:
        """
        Extract topic from Leichhardt C marker in text.

        Improved to handle markers after common prefixes (bullets, numbers).
        """
        if not text:
            return None

        text = text.strip()

        # Pattern 1: Exact start (e.g., "C3 Parking...")
        match = re.match(r'^(C\d+)\b', text)
        if match:
            return self.LEICHHARDT_C_TOPICS.get(match.group(1))

        # Pattern 2: After bullet or letter prefix (e.g., "a) C14 ..." or "• C3 ...")
        match = re.match(r'^[\s•\-\*\(\)a-z0-9\.]+\s*(C\d+)\b', text, re.IGNORECASE)
        if match:
            return self.LEICHHARDT_C_TOPICS.get(match.group(1).upper())

        # Pattern 3: First line contains C marker (e.g., "Note: C3 applies...")
        first_line = text.split('\n')[0]
        match = re.search(r'\b(C\d+)\b', first_line)
        if match:
            return self.LEICHHARDT_C_TOPICS.get(match.group(1).upper())

        return None

    def _extract_topic_from_text(self, text: str) -> Optional[str]:
        """
        Extract topic using weighted keyword matching.

        Counts keyword matches for each topic and returns the topic
        with the most matches. This is more accurate than earliest-match
        for provisions that mention multiple topics.
        """
        if not text:
            return None

        text_lower = text.lower()
        scores = {}

        for topic, pattern in self.TOPIC_KEYWORDS.items():
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                scores[topic] = len(matches)

        if not scores:
            return None

        # Return topic with highest score
        best_topic = max(scores.items(), key=lambda x: x[1])[0]
        return best_topic
