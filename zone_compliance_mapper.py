#!/usr/bin/env python3
"""
Zone-Specific Compliance Mapping System
======================================

Uses KG relationships to map zones to their specific compliance requirements.
Based on discovered relationship patterns where:
- R2 zone → Section 4.1 controls (low density residential)
- R1, R3, R4 zones → Section 4.2 + 4.1 controls (multi-density residential) 
- B1, B2 zones → Section 4.2 + 4.3 controls (commercial)
- IN2 zone → Section 6 controls (industrial)
"""

import sqlite3
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import logging

class ZoneComplianceMapper:
    """Maps zones to their specific compliance requirements using KG relationships"""
    
    def __init__(self, db_path: str = 'nsw_planning.db'):
        self.db_path = db_path
        self.zone_section_map = {}
        self.section_controls_map = {}
        self._initialize_mappings()
    
    def _initialize_mappings(self):
        """Build zone-to-section and section-to-controls mappings from KG data"""
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Define the discovered zone-section mappings
        self.zone_section_map = {
            'R2': ['Section 4.1'],  # Low density residential
            'R1': ['Section 4.1', 'Section 4.2'],  # General residential
            'R3': ['Section 4.1', 'Section 4.2'],  # Medium density residential  
            'R4': ['Section 4.1', 'Section 4.2'],  # High density residential
            'B1': ['Section 4.2', 'Section 4.3'],  # Neighbourhood Centre
            'B2': ['Section 4.2', 'Section 4.3'],  # Local Centre
            'B4': ['Section 4.2', 'Section 4.3'],  # Mixed Use
            'IN1': ['Section 6'],  # General Industrial
            'IN2': ['Section 6'],  # Light Industrial
        }
        
        # Build section-to-controls mapping
        for section_num in ['4.1', '4.2', '4.3', '6']:
            # Query 1: Direct section references in provision text
            controls_direct = cur.execute('''
                SELECT DISTINCT dc.control_type, dc.provision_id, 
                       dc.value_text, dc.confidence_score,
                       rpc.provision_text, rpc.document_id
                FROM development_controls dc
                JOIN regulatory_provisions_clean rpc ON dc.provision_id = rpc.id
                WHERE rpc.provision_text LIKE ?
                OR rpc.document_id LIKE ?
                ORDER BY dc.confidence_score DESC
            ''', (f'%Section {section_num}%', f'%section_{section_num.replace(".", "_")}%')).fetchall()
            
            # Query 2: For Section 4.1, also include 'general' setback controls
            # that apply to R2 zone (discovered from KG relationships)
            controls_general = []
            if section_num == '4.1':
                controls_general = cur.execute('''
                    SELECT DISTINCT dc.control_type, dc.provision_id,
                           dc.value_text, dc.confidence_score,
                           rpc.provision_text, rpc.document_id
                    FROM development_controls dc
                    JOIN regulatory_provisions_clean rpc ON dc.provision_id = rpc.id
                    WHERE dc.zone_applicable = 'general'
                    AND dc.control_type = 'setback'
                    AND (rpc.document_id LIKE '%Marrickville_DCP%' 
                         OR rpc.document_id LIKE '%Inner_West%')
                    ORDER BY dc.confidence_score DESC
                    LIMIT 50
                ''').fetchall()
            
            # Combine both query results
            all_controls = list(controls_direct) + list(controls_general)
            self.section_controls_map[f'Section {section_num}'] = all_controls
        
        conn.close()
        
        logging.info(f"Initialized mappings for {len(self.zone_section_map)} zones")
        for zone, sections in self.zone_section_map.items():
            control_count = sum(len(self.section_controls_map.get(s, [])) for s in sections)
            logging.info(f"  {zone}: {len(sections)} sections, {control_count} total controls")
    
    def get_zone_controls(self, zone_code: str, control_type: Optional[str] = None) -> List[Dict]:
        """
        Get all controls applicable to a specific zone
        
        Args:
            zone_code: Zone code (e.g., 'R2', 'B1')
            control_type: Filter by control type (e.g., 'setback', 'height')
            
        Returns:
            List of control dictionaries with metadata
        """
        
        if zone_code not in self.zone_section_map:
            logging.warning(f"Zone {zone_code} not found in mapping")
            return []
        
        applicable_sections = self.zone_section_map[zone_code]
        all_controls = []
        
        for section in applicable_sections:
            section_controls = self.section_controls_map.get(section, [])
            
            for control_data in section_controls:
                (ctrl_type, provision_id, value_text, confidence,
                 provision_text, document_id) = control_data
                
                # Filter by control type if specified
                if control_type and control_type.lower() not in ctrl_type.lower():
                    continue
                
                control_dict = {
                    'zone': zone_code,
                    'applicable_section': section,
                    'control_type': ctrl_type,
                    'provision_id': provision_id,
                    'value_text': value_text,
                    'confidence_score': confidence,
                    'provision_text': provision_text,
                    'document_id': document_id,
                    'source': 'zone_kg_mapping'
                }
                all_controls.append(control_dict)
        
        # Sort by confidence score descending
        all_controls.sort(key=lambda x: x['confidence_score'], reverse=True)
        return all_controls
    
    def get_zone_setback_requirements(self, zone_code: str) -> List[Dict]:
        """Get setback requirements for a specific zone using KG relationships"""
        
        setback_controls = self.get_zone_controls(zone_code, 'setback')
        
        # Enhance with specific setback parsing
        enhanced_controls = []
        for control in setback_controls:
            
            # Extract numerical setback values
            import re
            value_text = control['value_text'] or ''
            provision_text = control['provision_text'] or ''
            
            # Look for setback measurements
            measurements = []
            text_to_search = f"{value_text} {provision_text}"
            
            # Pattern for setback measurements (e.g., "6 metres", "1.5m", "900mm")
            measurement_patterns = [
                r'(\d+(?:\.\d+)?)\s*(?:metre|meter|m)\b',
                r'(\d+)\s*mm\b',
                r'setback(?:s)?\s+of\s+(\d+(?:\.\d+)?)\s*(?:metre|meter|m)',
            ]
            
            for pattern in measurement_patterns:
                matches = re.findall(pattern, text_to_search, re.IGNORECASE)
                for match in matches:
                    try:
                        value = float(match)
                        if 'mm' in pattern:
                            value = value / 1000  # Convert mm to meters
                        measurements.append(value)
                    except ValueError:
                        continue
            
            control['setback_measurements'] = list(set(measurements))  # Remove duplicates
            control['has_measurements'] = len(measurements) > 0
            
            enhanced_controls.append(control)
        
        return enhanced_controls
    
    def analyze_zone_coverage(self) -> Dict:
        """Analyze coverage of all zones in the mapping"""
        
        coverage_report = {
            'zones_mapped': len(self.zone_section_map),
            'total_sections': len(self.section_controls_map),
            'zone_details': {}
        }
        
        for zone_code in self.zone_section_map:
            controls = self.get_zone_controls(zone_code)
            setback_controls = self.get_zone_controls(zone_code, 'setback')
            
            coverage_report['zone_details'][zone_code] = {
                'applicable_sections': self.zone_section_map[zone_code],
                'total_controls': len(controls),
                'setback_controls': len(setback_controls),
                'control_types': list(set(c['control_type'] for c in controls))
            }
        
        return coverage_report
    
    def debug_zone_query(self, zone_code: str) -> None:
        """Print detailed debug information for a zone query"""
        
        print(f"\n=== ZONE {zone_code} DEBUG QUERY ===")
        
        if zone_code not in self.zone_section_map:
            print(f"❌ Zone {zone_code} not found in mapping")
            return
        
        applicable_sections = self.zone_section_map[zone_code]
        print(f"✅ Applicable sections: {applicable_sections}")
        
        all_controls = self.get_zone_controls(zone_code)
        print(f"✅ Total controls found: {len(all_controls)}")
        
        # Group by control type
        by_type = defaultdict(list)
        for control in all_controls:
            by_type[control['control_type']].append(control)
        
        for control_type, controls in by_type.items():
            print(f"\n📋 {control_type.upper()} CONTROLS: {len(controls)}")
            for i, control in enumerate(controls[:3], 1):  # Show top 3
                print(f"   {i}. Section: {control['applicable_section']}")
                print(f"      Value: {control['value_text'][:80]}...")
                print(f"      Confidence: {control['confidence_score']}")
                print(f"      Source: {control['document_id'][:50]}...")
        
        # Specific setback analysis
        setback_controls = self.get_zone_setback_requirements(zone_code)
        if setback_controls:
            print(f"\n🏗️ SETBACK ANALYSIS:")
            measured_controls = [c for c in setback_controls if c['has_measurements']]
            print(f"   Controls with measurements: {len(measured_controls)}/{len(setback_controls)}")
            
            for control in measured_controls[:3]:
                print(f"   - Measurements: {control['setback_measurements']} meters")
                print(f"     Text: {control['value_text'][:60]}...")


def main():
    """Test the zone compliance mapping system"""
    
    logging.basicConfig(level=logging.INFO)
    mapper = ZoneComplianceMapper()
    
    # Test R2 zone (from our Dulwich Hill property)
    print("=== TESTING R2 ZONE COMPLIANCE MAPPING ===")
    mapper.debug_zone_query('R2')
    
    # Get coverage report
    coverage = mapper.analyze_zone_coverage()
    
    print(f"\n=== COVERAGE REPORT ===")
    print(f"Zones mapped: {coverage['zones_mapped']}")
    print(f"Sections available: {coverage['total_sections']}")
    
    print("\nZone summary:")
    for zone, details in coverage['zone_details'].items():
        print(f"{zone}: {details['total_controls']} controls, "
              f"{details['setback_controls']} setbacks, "
              f"types: {details['control_types'][:3]}...")


if __name__ == "__main__":
    main()