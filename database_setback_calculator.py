#!/usr/bin/env python3
"""
Direct Database Setback Calculator
Queries the enhanced nsw_planning.db directly for real setback values
"""

from db_config import get_connection  # Unified PostgreSQL connection
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class DatabaseSetbackCalculator:
    """Calculate setbacks directly from enhanced database"""
    
    def __init__(self, get_connection()):
        self.db_path = db_path
    
    def get_setbacks_for_property(self, property_data) -> Dict[str, Any]:
        """Get real setbacks from database for a property"""
        
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Get zone from property data - default to R2 if not available
            zone = getattr(property_data, 'zone', 'R2')
            if hasattr(property_data, 'planning_controls'):
                for control in property_data.planning_controls:
                    if control.get('layerName') == 'Land Zoning Map':
                        zone_result = control.get('results', [])
                        if zone_result:
                            zone = zone_result[0].get('Zone', 'R2')
                            break
            
            # Query database for setback controls
            setback_query = """
                SELECT dc.control_type, dc.control_subtype, dc.value_numeric, dc.value_text, dc.unit,
                       rp.document_id, rp.section_header, rp.provision_text
                FROM development_controls dc
                JOIN regulatory_provisions rp ON dc.provision_id = rp.id
                WHERE dc.control_type = 'setback' 
                  AND (rp.zone = ? OR dc.zone_applicable = ? OR rp.zone IS NULL)
                ORDER BY dc.value_numeric DESC
            """
            
            setback_results = cur.execute(setback_query, (zone, zone)).fetchall()
            
            if not setback_results:
                logger.warning(f"No setback data found for zone {zone}, trying general search")
                # Fallback: search without zone filtering
                setback_results = cur.execute("""
                    SELECT dc.control_type, dc.control_subtype, dc.value_numeric, dc.value_text, dc.unit,
                           rp.document_id, rp.section_header, rp.provision_text
                    FROM development_controls dc
                    JOIN regulatory_provisions rp ON dc.provision_id = rp.id
                    WHERE dc.control_type = 'setback'
                    ORDER BY dc.value_numeric DESC
                    LIMIT 10
                """).fetchall()
            
            # Process results to extract front, side, rear setbacks
            setbacks = {
                'front': {'value': 6.0, 'source': 'FALLBACK', 'confidence': 'LOW'},
                'side': {'value': 1.5, 'source': 'FALLBACK', 'confidence': 'LOW'},
                'rear': {'value': 6.0, 'source': 'FALLBACK', 'confidence': 'LOW'}
            }
            
            confidence = 'MEDIUM' if setback_results else 'LOW'
            
            # Categorize setbacks by looking at context
            for control_type, subtype, numeric, text, unit, doc, section, provision in setback_results:
                value = numeric or 0.0
                source = f"{doc} - {section}"
                
                # Try to determine if it's front, side, or rear from context
                text_lower = (text or '').lower()
                provision_lower = (provision or '').lower()
                section_lower = (section or '').lower()
                
                # Front setback detection
                if any(word in text_lower + provision_lower + section_lower 
                       for word in ['front', 'street', 'primary']):
                    if value > 0:
                        setbacks['front'] = {
                            'value': value, 
                            'source': source, 
                            'confidence': confidence,
                            'text': text
                        }
                
                # Side setback detection  
                elif any(word in text_lower + provision_lower + section_lower 
                         for word in ['side', 'lateral']):
                    if value > 0:
                        setbacks['side'] = {
                            'value': value,
                            'source': source,
                            'confidence': confidence, 
                            'text': text
                        }
                
                # Rear setback detection
                elif any(word in text_lower + provision_lower + section_lower 
                         for word in ['rear', 'back']):
                    if value > 0:
                        setbacks['rear'] = {
                            'value': value,
                            'source': source,
                            'confidence': confidence,
                            'text': text
                        }
                
                # General setback - apply to all if no specific ones found
                else:
                    if value > 0 and setbacks['front']['confidence'] == 'LOW':
                        # Apply general setback to all positions
                        for position in ['front', 'side', 'rear']:
                            if setbacks[position]['confidence'] == 'LOW':
                                setbacks[position] = {
                                    'value': value,
                                    'source': f"{source} (general)",
                                    'confidence': confidence,
                                    'text': text
                                }
            
            conn.close()
            
            logger.info(f"Found setbacks - Front: {setbacks['front']['value']}m, Side: {setbacks['side']['value']}m, Rear: {setbacks['rear']['value']}m")
            return setbacks
            
        except Exception as e:
            logger.error(f"Database setback query failed: {e}")
            # Return fallback values
            return {
                'front': {'value': 6.0, 'source': 'ERROR FALLBACK', 'confidence': 'LOW'},
                'side': {'value': 1.5, 'source': 'ERROR FALLBACK', 'confidence': 'LOW'}, 
                'rear': {'value': 6.0, 'source': 'ERROR FALLBACK', 'confidence': 'LOW'}
            }


def test_database_calculator():
    """Test the database calculator"""
    print("Testing Database Setback Calculator")
    
    # Mock property data
    class MockProperty:
        def __init__(self):
            self.zone = 'R2'
            self.address = '34 Pile Street, Dulwich Hill'
    
    calc = DatabaseSetbackCalculator()
    property_data = MockProperty()
    
    setbacks = calc.get_setbacks_for_property(property_data)
    
    print(f"Front: {setbacks['front']['value']}m from {setbacks['front']['source']} ({setbacks['front']['confidence']})")
    print(f"Side: {setbacks['side']['value']}m from {setbacks['side']['source']} ({setbacks['side']['confidence']})")
    print(f"Rear: {setbacks['rear']['value']}m from {setbacks['rear']['source']} ({setbacks['rear']['confidence']})")


if __name__ == "__main__":
    test_database_calculator()