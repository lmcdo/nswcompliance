#!/usr/bin/env python3
"""
Marker Extractor for Leichhardt C markers and Ashfield PC/DS markers.

Extracts control markers from provision text:
- Leichhardt: C1, C2, C3, ... C55 (topic-based control numbers)
- Ashfield: PC (Performance Criteria), DS (Design Solutions), C/O controls
"""
import re
from typing import Tuple, Optional, List


class MarkerExtractor:
    """Extracts control markers from provision text."""

    # Leichhardt C markers -> topics (from web research)
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

    # Ashfield marker types and their display behavior
    ASHFIELD_MARKER_TYPES = {
        'DS': {'type': 'control', 'display': 'cdc_quantitative'},
        'PC': {'type': 'objective', 'display': 'da_variation'},
        'C': {'type': 'control', 'display': 'da'},
        'O': {'type': 'objective', 'display': 'da'},
    }

    def extract_leichhardt_marker(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract C marker from Leichhardt provision text.

        Returns:
            Tuple of (marker, topic) e.g., ('C15', 'parking')
        """
        if not text:
            return None, None

        # Look for C marker at start of text (e.g., "C15.1", "C3", "C1.2.3")
        match = re.match(r'^(C\d+)(?:\.\d+)*\b', text.strip())
        if match:
            marker = match.group(1)
            topic = self.LEICHHARDT_C_TOPICS.get(marker)
            return marker, topic

        # Also check for C marker anywhere in first 50 chars (sometimes preceded by number)
        match = re.search(r'\b(C\d+)(?:\.\d+)*\b', text[:50])
        if match:
            marker = match.group(1)
            topic = self.LEICHHARDT_C_TOPICS.get(marker)
            return marker, topic

        return None, None

    def extract_ashfield_marker(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extract PC/DS/C/O marker from Ashfield provision text.

        Returns:
            Tuple of (marker, marker_type, display_behavior)
            e.g., ('DS1.2', 'control', 'cdc_quantitative')
        """
        if not text:
            return None, None, None

        text_stripped = text.strip()

        # Check for DS (Design Solution) - e.g., "DS1", "DS1.2", "DS 1.2"
        match = re.match(r'^(DS\s*\d+(?:\.\d+)?)\b', text_stripped, re.IGNORECASE)
        if match:
            marker = match.group(1).replace(' ', '')
            info = self.ASHFIELD_MARKER_TYPES['DS']
            return marker, info['type'], info['display']

        # Check for PC (Performance Criteria) - e.g., "PC1", "PC 1.2"
        match = re.match(r'^(PC\s*\d+(?:\.\d+)?)\b', text_stripped, re.IGNORECASE)
        if match:
            marker = match.group(1).replace(' ', '')
            info = self.ASHFIELD_MARKER_TYPES['PC']
            return marker, info['type'], info['display']

        # Check for standalone C (Control) at start - e.g., "C1", "C1.2"
        # But NOT if it looks like Leichhardt (C followed by large number)
        match = re.match(r'^(C\d+(?:\.\d+)?)\b', text_stripped)
        if match:
            marker = match.group(1)
            # If marker number is > 10, it's probably Leichhardt style
            num_match = re.match(r'C(\d+)', marker)
            if num_match and int(num_match.group(1)) <= 10:
                info = self.ASHFIELD_MARKER_TYPES['C']
                return marker, info['type'], info['display']

        # Check for O (Objective) at start - e.g., "O1", "O1.2"
        match = re.match(r'^(O\d+(?:\.\d+)?)\b', text_stripped)
        if match:
            marker = match.group(1)
            info = self.ASHFIELD_MARKER_TYPES['O']
            return marker, info['type'], info['display']

        return None, None, None

    def extract(self, document_id: str, text: str) -> dict:
        """
        Extract markers based on council.

        Returns dict with:
            - marker: The extracted marker (e.g., 'C15', 'DS1.2', 'PC3')
            - marker_type: 'control' or 'objective'
            - topic: Topic derived from marker (Leichhardt only)
            - display: Display behavior (Ashfield only)
        """
        result = {
            'marker': None,
            'marker_type': None,
            'topic': None,
            'display': None,
        }

        doc_lower = (document_id or '').lower()

        if 'leichhardt' in doc_lower:
            marker, topic = self.extract_leichhardt_marker(text)
            if marker:
                result['marker'] = marker
                result['topic'] = topic
                result['marker_type'] = 'control'

        elif 'ashfield' in doc_lower:
            marker, marker_type, display = self.extract_ashfield_marker(text)
            if marker:
                result['marker'] = marker
                result['marker_type'] = marker_type
                result['display'] = display

        return result
