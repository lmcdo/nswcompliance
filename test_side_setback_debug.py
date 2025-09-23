#!/usr/bin/env python3
"""
Debug side setback extraction from KG relationships
"""

import sqlite3
import re

def test_measurement_extraction():
 print("TESTING MEASUREMENT EXTRACTION PATTERNS")
 print("=" * 60)
 
 # Test cases from actual KG data
 test_texts = [
 "Be setback 1 metre from the southern boundary; 1 metre from the eastern boundary",
 "Minimum side setback is 0.9 metres",
 "Federation and Inter-War period dwellings have 2-4 metre setbacks",
 "Have approximately a 15 metre envelope depth",
 "Ramps must be setback a minimum of 4.5m from the property boundary"
 ]
 
 for text in test_texts:
 print(f"Text: {text}")
 
 # Test universal measurement pattern
 measurementPattern = r'(\d+(?:\.\d+)?)\s*(?:millimetres?|millimeters?|mm|metres?|meters?|m(?!\w)|centimetres?|centimeters?|cm)'
 matches = re.findall(measurementPattern, text, re.IGNORECASE)
 print(f" Measurements found: {matches}")
 
 # Test boundary type detection
 text_lower = text.lower()
 boundary_types = []
 
 # Front indicators
 if any(indicator in text_lower for indicator in ['front', 'street', 'road', 'frontage', 'facade']):
 boundary_types.append('front')
 
 # Rear indicators 
 if any(indicator in text_lower for indicator in ['rear', 'back']):
 boundary_types.append('rear')
 
 # Side indicators
 side_indicators = [
 'side', 'lateral', 'boundary', 'boundaries',
 'southern', 'northern', 'eastern', 'western',
 'north', 'south', 'east', 'west',
 'left', 'right', 'adjacent'
 ]
 if any(indicator in text_lower for indicator in side_indicators):
 boundary_types.append('side')
 
 if not boundary_types:
 boundary_types.append('general')
 
 print(f" Boundary types detected: {boundary_types}")
 
 # Show what would be extracted
 for match in matches:
 value = float(match)
 if 0.1 <= value <= 50: # Reasonable setback range
 for boundary_type in boundary_types:
 print(f" -> Would extract: {boundary_type} = {value}m")
 
 print()

def check_actual_kg_data():
 print("CHECKING ACTUAL KG DATA FOR SIDE SETBACKS")
 print("=" * 60)
 
 conn = sqlite3.connect('nsw_planning.db')
 
 # Query for ALL setback relationships with numbers - no hardcoding
 cursor = conn.execute('''
 SELECT subject_text, object_text, document_id, confidence_score
 FROM kg_relationships 
 WHERE (
 (subject_text LIKE '%setback%' OR object_text LIKE '%setback%')
 AND (
 subject_text GLOB '*[0-9]*' OR object_text GLOB '*[0-9]*'
 )
 )
 AND confidence_score >= 0.7
 ORDER BY confidence_score DESC
 LIMIT 15
 ''')
 
 relationships = cursor.fetchall()
 print(f"Found {len(relationships)} setback relationships with numbers")
 
 for i, rel in enumerate(relationships, 1):
 combined_text = rel[0] + ' ' + rel[1]
 print(f"\n{i}. Combined text: {combined_text[:120]}...")
 
 # Test measurement extraction on this real data
 measurementPattern = r'(\d+(?:\.\d+)?)\s*(?:millimetres?|millimeters?|mm|metres?|meters?|m(?!\w)|centimetres?|centimeters?|cm)'
 matches = re.findall(measurementPattern, combined_text, re.IGNORECASE)
 
 if matches:
 print(f" Measurements: {matches}")
 
 # Test boundary detection
 text_lower = combined_text.lower()
 boundary_types = []
 
 if any(word in text_lower for word in ['front', 'street', 'road', 'frontage']):
 boundary_types.append('front')
 if any(word in text_lower for word in ['rear', 'back']):
 boundary_types.append('rear')
 if any(word in text_lower for word in ['side', 'boundary', 'southern', 'northern', 'eastern', 'western', 'south', 'north', 'east', 'west']):
 boundary_types.append('side')
 
 if not boundary_types:
 boundary_types.append('general')
 
 print(f" Boundary types: {boundary_types}")
 print(f" Document: {rel[2]}, Score: {rel[3]}")
 
 # Show extractions
 for match in matches:
 value = float(match)
 if 0.1 <= value <= 50:
 for bt in boundary_types:
 print(f" -> EXTRACT: {bt} = {value}m")
 else:
 print(f" No measurements found")
 
 conn.close()

if __name__ == "__main__":
 test_measurement_extraction()
 print()
 check_actual_kg_data()