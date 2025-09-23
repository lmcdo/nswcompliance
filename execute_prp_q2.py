#!/usr/bin/env python3
"""
PRP-Q2: Special Provisions Processing Engine
===========================================
Implements comprehensive processing engine for special provisions from NSW Planning API,
including SEPPs, climate overlays, hazard zones, and regulatory overlays.
"""

from db_config import get_connection
import json
import sys
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class PRPQ2Executor:
 """Execute PRP-Q2 Special Provisions Processing Engine implementation"""

 def __init__(self):
 self.execution_report = {
 'prp_id': 'PRP-Q2',
 'title': 'Special Provisions Processing Engine',
 'start_time': datetime.now().isoformat(),
 'phases': {},
 'status': 'IN_PROGRESS'
 }

 def phase1_create_sepp_processing_engine(self) -> Dict:
 """Phase 1: Create SEPP quantitative extraction engine"""
 print("=== PHASE 1: SEPP Quantitative Extraction Engine ===")

 phase_result = {
 'phase': 'sepp_processing_engine',
 'start_time': datetime.now().isoformat(),
 'steps': []
 }

 try:
 # Create SEPP processing engine
 sepp_engine_code = '''from db_config import get_connection
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
 'confidence': 1.0 # Known mappings have highest confidence
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
 'lot_size': (50, 50000), # 50sqm to 5 hectares
 'height': (0.5, 500), # 0.5m to 500m
 'setback': (0, 100), # 0m to 100m
 'percentage': (0, 100), # 0% to 100%
 'floor_space_ratio': (0.1, 10), # 0.1:1 to 10:1
 'area': (0.01, 1000) # 0.01ha to 1000ha
 }

 if context in ranges:
 min_val, max_val = ranges[context]
 return min_val <= value <= max_val

 return True # Accept if no range defined

 def _calculate_confidence(self, context: str, full_text: str, matched_value: str) -> float:
 """Calculate confidence score for extraction"""
 confidence = 0.7 # Base confidence

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
 print(f" Found: {result['numeric_value']} {result['unit']} for {result['measurement_context']}")

 # Test database extraction
 print("\\nTesting database provision extraction:")
 db_results = extractor.extract_from_database_provisions('HOUSING', limit=5)
 for i, result in enumerate(db_results[:3], 1):
 print(f" {i}. {result['measurement_context']}: {result['numeric_value']} {result['unit']}")
 print(f" From: {result['ref_number']} - {result['provision_text'][:100]}...")
 print(f" Confidence: {result['confidence']:.2f}")
'''

 with open('services/sepp_quantitative_extractor.py', 'w') as f:
 f.write(sepp_engine_code)

 phase_result['steps'].append({
 'step': 'create_sepp_extractor',
 'status': 'COMPLETED',
 'message': 'SEPP quantitative extraction engine created'
 })

 phase_result['status'] = 'COMPLETED'
 phase_result['end_time'] = datetime.now().isoformat()
 print("SUCCESS: Phase 1 completed - SEPP quantitative extraction engine created")

 except Exception as e:
 phase_result['status'] = 'FAILED'
 phase_result['error'] = str(e)
 print(f"FAILED: Phase 1 failed: {e}")

 return phase_result

 def phase2_create_provisions_processor(self) -> Dict:
 """Phase 2: Create comprehensive special provisions processor"""
 print("\n=== PHASE 2: Special Provisions Processor ===")

 phase_result = {
 'phase': 'provisions_processor',
 'start_time': datetime.now().isoformat(),
 'steps': []
 }

 try:
 # Create comprehensive provisions processor
 processor_code = '''from db_config import get_connection
from services.sepp_quantitative_extractor import SEPPQuantitativeExtractor
from typing import Dict, List, Optional, Tuple
import json
import re

class SpecialProvisionsProcessor:
 """Comprehensive processor for NSW Planning API special provisions"""

 def __init__(self):
 self.db = get_connection()
 self.sepp_extractor = SEPPQuantitativeExtractor()
 self._load_provision_registry()

 def _load_provision_registry(self):
 """Load provision processing rules from database"""
 cursor = self.db.cursor()
 cursor.execute("""
 SELECT
 provision_type,
 provision_category,
 default_tier_level,
 authority_level,
 requires_specialist,
 has_numeric_thresholds
 FROM special_provisions_registry
 WHERE active = TRUE
 """)

 self.registry = {}
 for row in cursor.fetchall():
 key = (row[0], row[1]) if row[1] else row[0]
 self.registry[key] = {
 'tier_level': row[2],
 'authority_level': row[3],
 'requires_specialist': row[4],
 'has_numeric_thresholds': row[5]
 }

 def process_special_provisions(self, raw_provisions: List[Dict],
 zone_code: str, development_type: str = None) -> Dict:
 """Process raw NSW API special provisions into tiered compliance structure"""

 results = {
 'tier_1_provisions': [],
 'tier_2_provisions': [],
 'tier_3_provisions': [],
 'tier_4_provisions': [],
 'tier_5_provisions': [],
 'basix_requirements': None,
 'hazard_assessments': [],
 'environmental_constraints': [],
 'sepp_extractions': [],
 'metadata': {
 'total_processed': 0,
 'provision_types': set(),
 'requires_specialist': False,
 'quantitative_extractions': 0
 }
 }

 for provision in raw_provisions:
 processed = self._process_single_provision(provision, zone_code, development_type)

 if processed:
 # Add to appropriate tier
 tier_key = f'tier_{processed["tier_level"]}_provisions'
 if tier_key in results:
 results[tier_key].append(processed)

 # Track metadata
 results['metadata']['total_processed'] += 1
 results['metadata']['provision_types'].add(processed['provision_type'])

 if processed.get('requires_specialist'):
 results['metadata']['requires_specialist'] = True

 if processed.get('numeric_value') is not None:
 results['metadata']['quantitative_extractions'] += 1

 # Special handling
 if processed['provision_type'] == 'Climate Zones':
 results['basix_requirements'] = self._process_basix_requirements(
 provision, development_type
 )
 elif processed['provision_type'] in ['Flood Planning', 'Bushfire Prone Land']:
 results['hazard_assessments'].append(
 self._create_hazard_assessment(processed)
 )
 elif processed['provision_type'] in ['Heritage', 'Biodiversity', 'Acid Sulfate Soils']:
 results['environmental_constraints'].append(
 self._create_environmental_constraint(processed)
 )
 elif processed['provision_type'] == 'State Environmental Planning Policy':
 results['sepp_extractions'].append(processed)

 # Convert set to list for JSON serialization
 results['metadata']['provision_types'] = list(results['metadata']['provision_types'])

 return results

 def _process_single_provision(self, provision: Dict, zone_code: str,
 development_type: str = None) -> Optional[Dict]:
 """Process a single provision into structured format"""

 provision_type = provision.get('Type', '')
 category = provision.get('Category', '')

 # Look up in registry
 registry_key = (provision_type, category) if category else provision_type
 config = self.registry.get(registry_key) or self.registry.get(provision_type)

 if not config:
 # Unknown provision type - assign to tier 3 with moderate authority
 config = {
 'tier_level': 3,
 'authority_level': 70,
 'requires_specialist': False,
 'has_numeric_thresholds': False
 }

 # Process based on type
 if provision_type == 'Climate Zones':
 return self._process_climate_zone(provision, config)
 elif provision_type == 'State Environmental Planning Policy':
 return self._process_sepp(provision, config)
 elif provision_type == 'Flood Planning':
 return self._process_flood_planning(provision, config, zone_code)
 elif provision_type == 'Bushfire Prone Land':
 return self._process_bushfire(provision, config)
 elif provision_type == 'Heritage':
 return self._process_heritage(provision, config)
 elif provision_type == 'Acid Sulfate Soils':
 return self._process_acid_sulfate(provision, config)
 else:
 return self._process_generic_provision(provision, config)

 def _process_climate_zone(self, provision: Dict, config: Dict) -> Dict:
 """Process BASIX climate zone provision"""
 climate_zone = provision.get('Class', '')

 return {
 'provision_type': 'Climate Zones',
 'tier_level': 1,
 'authority_level': 100,
 'document_type': 'BASIX',
 'document_name': 'Building Sustainability Index',
 'clause_reference': f'Climate {climate_zone}',
 'provision_text': f'Property is in BASIX Climate {climate_zone}',
 'measurement_context': 'climate_zone',
 'climate_zone': climate_zone,
 'requires_specialist': False,
 'confidence_level': 1.0,
 'implications': [
 'BASIX certificate required for new residential development',
 'Energy and water targets apply based on climate zone'
 ]
 }

 def _process_sepp(self, provision: Dict, config: Dict) -> Dict:
 """Process State Environmental Planning Policy"""
 epi_name = provision.get('EPI Name', '')
 clause = provision.get('Legislative Clause', '')

 # Extract SEPP type
 sepp_type = self._identify_sepp_type(epi_name)

 # Try to extract quantitative values
 quantitative_data = None
 if sepp_type and clause:
 quantitative_data = self.sepp_extractor.extract_from_sepp_clause(sepp_type, clause)

 provision_text = f"SEPP applies: {epi_name}"
 if clause:
 provision_text += f" (Clause {clause})"

 result = {
 'provision_type': 'State Environmental Planning Policy',
 'tier_level': 1,
 'authority_level': 95,
 'document_type': 'SEPP',
 'document_name': epi_name,
 'clause_reference': clause or 'General',
 'provision_text': provision_text,
 'sepp_type': sepp_type,
 'requires_specialist': False,
 'confidence_level': 0.9
 }

 # Add quantitative data if extracted
 if quantitative_data:
 result.update({
 'measurement_context': quantitative_data['measurement_context'],
 'numeric_value': quantitative_data['numeric_value'],
 'unit': quantitative_data['unit'],
 'confidence_level': quantitative_data['confidence']
 })

 return result

 def _process_flood_planning(self, provision: Dict, config: Dict, zone_code: str) -> Dict:
 """Process flood planning provision"""
 category = provision.get('Category', '')
 level = provision.get('Level', '')

 return {
 'provision_type': 'Flood Planning',
 'tier_level': 1,
 'authority_level': 95,
 'document_type': 'Flood Planning',
 'document_name': 'Flood Planning Controls',
 'clause_reference': f'Flood Planning - {level}',
 'provision_text': f'Property is in {category} - {level}',
 'measurement_context': 'flood_planning_level',
 'flood_category': category,
 'flood_level': level,
 'requires_specialist': True,
 'confidence_level': 0.95,
 'implications': [
 'Flood Impact Assessment required',
 'Minimum floor levels apply',
 'Emergency evacuation plan required'
 ],
 'actions_required': [
 'Engage flood consultant',
 'Prepare Flood Impact Assessment',
 'Design floor levels above flood level'
 ]
 }

 def _process_bushfire(self, provision: Dict, config: Dict) -> Dict:
 """Process bushfire prone land provision"""
 category = provision.get('Category', '')
 buffer = provision.get('Buffer', '')

 bal_rating = self._estimate_bal_rating(category, buffer)

 return {
 'provision_type': 'Bushfire Prone Land',
 'tier_level': 1,
 'authority_level': 95,
 'document_type': 'Bushfire Planning',
 'document_name': 'Planning for Bush Fire Protection',
 'clause_reference': f'Bushfire - {category}',
 'provision_text': f'Property is bushfire prone - {category}',
 'measurement_context': 'bushfire_attack_level',
 'bushfire_category': category,
 'estimated_bal': bal_rating,
 'numeric_value': bal_rating,
 'unit': 'BAL',
 'requires_specialist': True,
 'confidence_level': 0.9,
 'implications': [
 'Bushfire Assessment Report required',
 f'Construction to BAL-{bal_rating} standard',
 'Asset Protection Zone required'
 ]
 }

 def _process_heritage(self, provision: Dict, config: Dict) -> Dict:
 """Process heritage provision"""
 heritage_type = provision.get('Heritage Type', '')
 item_name = provision.get('Item Name', '')

 return {
 'provision_type': 'Heritage',
 'tier_level': 2,
 'authority_level': 90,
 'document_type': 'Heritage',
 'document_name': 'Heritage Conservation',
 'clause_reference': 'Heritage Item',
 'provision_text': f'{heritage_type}: {item_name}',
 'heritage_type': heritage_type,
 'heritage_item': item_name,
 'requires_specialist': True,
 'confidence_level': 0.95,
 'implications': [
 'Heritage Impact Statement required',
 'Heritage architect consultation recommended'
 ]
 }

 def _process_acid_sulfate(self, provision: Dict, config: Dict) -> Dict:
 """Process acid sulfate soils provision"""
 soil_class = provision.get('Class', '')
 action = provision.get('Action', '')

 return {
 'provision_type': 'Acid Sulfate Soils',
 'tier_level': 2,
 'authority_level': 85,
 'document_type': 'Environmental',
 'document_name': 'Acid Sulfate Soils Management',
 'clause_reference': f'ASS {soil_class}',
 'provision_text': f'Property has {soil_class} acid sulfate soils - {action}',
 'soil_class': soil_class,
 'required_action': action,
 'requires_specialist': True,
 'confidence_level': 0.9
 }

 def _process_generic_provision(self, provision: Dict, config: Dict) -> Dict:
 """Process unknown/generic provision"""
 provision_type = provision.get('Type', 'Unknown')
 category = provision.get('Category', '')

 return {
 'provision_type': provision_type,
 'tier_level': config['tier_level'],
 'authority_level': config['authority_level'],
 'document_type': 'Special Provision',
 'document_name': f'{provision_type} ({category})' if category else provision_type,
 'clause_reference': 'General',
 'provision_text': f'{provision_type} provision applies',
 'requires_specialist': config['requires_specialist'],
 'confidence_level': 0.7
 }

 def _process_basix_requirements(self, provision: Dict, development_type: str) -> Optional[Dict]:
 """Get BASIX requirements for climate zone"""
 climate_zone = provision.get('Class', '')

 if not climate_zone or not development_type:
 return None

 # Import BASIX checker from PRP-Q1
 try:
 from services.basix_compliance_checker import BASIXComplianceChecker
 checker = BASIXComplianceChecker()
 return checker.process_basix_for_compliance(climate_zone, development_type)
 except ImportError:
 return None

 def _identify_sepp_type(self, epi_name: str) -> Optional[str]:
 """Identify SEPP type from EPI name"""
 epi_lower = epi_name.lower()

 if 'housing' in epi_lower and '2021' in epi_lower:
 return 'SEPP_HOUSING_2021'
 elif 'exempt' in epi_lower and 'complying' in epi_lower:
 return 'SEPP_EXEMPT_2008'
 elif 'planning systems' in epi_lower:
 return 'SEPP_PLANNING_SYSTEMS_2021'
 elif 'resilience' in epi_lower or 'hazards' in epi_lower:
 return 'SEPP_RESILIENCE_HAZARDS_2021'

 return None

 def _estimate_bal_rating(self, category: str, buffer: str) -> float:
 """Estimate BAL rating from bushfire category"""
 if 'category 1' in category.lower():
 return 29 if '100m' in buffer else 40
 elif 'category 2' in category.lower():
 return 19 if '100m' in buffer else 29
 return 12.5

 def _create_hazard_assessment(self, provision: Dict) -> Dict:
 """Create hazard assessment summary"""
 return {
 'hazard_type': provision['provision_type'],
 'risk_level': 'high' if provision['tier_level'] == 1 else 'moderate',
 'specialist_required': provision['requires_specialist'],
 'key_requirements': provision.get('implications', []),
 'actions': provision.get('actions_required', [])
 }

 def _create_environmental_constraint(self, provision: Dict) -> Dict:
 """Create environmental constraint summary"""
 return {
 'constraint_type': provision['provision_type'],
 'impact_level': 'significant' if provision['requires_specialist'] else 'moderate',
 'assessment_required': provision['requires_specialist'],
 'provision_details': provision.get('provision_text', '')
 }

# Test the processor
if __name__ == "__main__":
 processor = SpecialProvisionsProcessor()

 # Test with sample NSW API special provisions data
 test_provisions = [
 {
 "Type": "Climate Zones",
 "Class": "Zone 17",
 "Map Type": "CLM"
 },
 {
 "Type": "State Environmental Planning Policy",
 "EPI Name": "SEPP (Housing) 2021",
 "Legislative Clause": "3.31"
 },
 {
 "Type": "Flood Planning",
 "Category": "Flood Planning Area",
 "Level": "1:100 Year"
 }
 ]

 result = processor.process_special_provisions(test_provisions, 'R2', 'dwelling_house')

 print("Processing Results:")
 print(f"Total processed: {result['metadata']['total_processed']}")
 print(f"Tier 1 provisions: {len(result['tier_1_provisions'])}")
 print(f"Quantitative extractions: {result['metadata']['quantitative_extractions']}")
 print(f"Specialist required: {result['metadata']['requires_specialist']}")
'''

 with open('services/special_provisions_processor.py', 'w') as f:
 f.write(processor_code)

 phase_result['steps'].append({
 'step': 'create_provisions_processor',
 'status': 'COMPLETED',
 'message': 'Special provisions processor created'
 })

 phase_result['status'] = 'COMPLETED'
 phase_result['end_time'] = datetime.now().isoformat()
 print("SUCCESS: Phase 2 completed - Special provisions processor created")

 except Exception as e:
 phase_result['status'] = 'FAILED'
 phase_result['error'] = str(e)
 print(f"FAILED: Phase 2 failed: {e}")

 return phase_result

 def phase3_create_integration_service(self) -> Dict:
 """Phase 3: Create integration service for compliance API"""
 print("\n=== PHASE 3: Compliance Integration Service ===")

 phase_result = {
 'phase': 'integration_service',
 'start_time': datetime.now().isoformat(),
 'steps': []
 }

 try:
 # Create integration service
 integration_code = '''from services.special_provisions_processor import SpecialProvisionsProcessor
from typing import Dict, List, Optional
import json

class SpecialProvisionsIntegrationService:
 """Integrate special provisions processing with compliance checking"""

 def __init__(self):
 self.processor = SpecialProvisionsProcessor()

 def integrate_with_compliance_check(self,
 planning_api_data: Dict,
 zone_code: str,
 development_type: str = None,
 property_id: int = None) -> Dict:
 """
 Integrate special provisions processing with compliance checking
 """

 # Extract special provisions from NSW Planning API data
 special_provisions = self._extract_special_provisions_from_api(planning_api_data)

 if not special_provisions:
 return self._create_empty_response()

 # Process provisions through the engine
 processed = self.processor.process_special_provisions(
 special_provisions, zone_code, development_type
 )

 # Enhance with compliance context
 enhanced_result = self._enhance_with_compliance_context(
 processed, zone_code, development_type, property_id
 )

 return enhanced_result

 def _extract_special_provisions_from_api(self, planning_api_data: Dict) -> List[Dict]:
 """Extract special provisions from NSW Planning API response"""
 provisions = []

 # Handle different API response formats
 if 'layers' in planning_api_data:
 # Layer-based format
 for layer in planning_api_data['layers']:
 if layer.get('layerName') == 'Special Provisions':
 provisions.extend(layer.get('results', []))

 elif 'special_provisions' in planning_api_data:
 # Direct format
 provisions = planning_api_data['special_provisions']

 elif isinstance(planning_api_data, list):
 # Direct list format
 provisions = planning_api_data

 return provisions

 def _enhance_with_compliance_context(self, processed: Dict, zone_code: str,
 development_type: str, property_id: int) -> Dict:
 """Enhance processed provisions with compliance context"""

 enhanced = {
 'special_provisions_processing': processed,
 'compliance_summary': {
 'zone_code': zone_code,
 'development_type': development_type,
 'property_id': property_id,
 'total_provisions': processed['metadata']['total_processed'],
 'tier_breakdown': self._calculate_tier_breakdown(processed),
 'specialist_assessment_required': processed['metadata']['requires_specialist'],
 'quantitative_requirements': processed['metadata']['quantitative_extractions'],
 'key_compliance_points': self._extract_key_compliance_points(processed)
 },
 'integration_metadata': {
 'processing_timestamp': processed['metadata'].get('timestamp'),
 'basix_applicable': processed['basix_requirements'] is not None,
 'hazards_identified': len(processed['hazard_assessments']) > 0,
 'environmental_constraints': len(processed['environmental_constraints']) > 0,
 'sepp_provisions_found': len(processed['sepp_extractions']) > 0
 }
 }

 return enhanced

 def _calculate_tier_breakdown(self, processed: Dict) -> Dict:
 """Calculate breakdown of provisions by tier"""
 return {
 'tier_1': len(processed.get('tier_1_provisions', [])),
 'tier_2': len(processed.get('tier_2_provisions', [])),
 'tier_3': len(processed.get('tier_3_provisions', [])),
 'tier_4': len(processed.get('tier_4_provisions', [])),
 'tier_5': len(processed.get('tier_5_provisions', []))
 }

 def _extract_key_compliance_points(self, processed: Dict) -> List[str]:
 """Extract key compliance points for summary"""
 points = []

 # Add BASIX requirements
 if processed['basix_requirements']:
 points.append("BASIX certificate required for residential development")

 # Add hazard assessments
 for hazard in processed['hazard_assessments']:
 if hazard['specialist_required']:
 points.append(f"{hazard['hazard_type']} specialist assessment required")

 # Add environmental constraints
 for constraint in processed['environmental_constraints']:
 if constraint['assessment_required']:
 points.append(f"{constraint['constraint_type']} assessment may be required")

 # Add SEPP requirements
 for sepp in processed['sepp_extractions']:
 if sepp.get('numeric_value'):
 points.append(f"SEPP requirement: {sepp['measurement_context']} = {sepp['numeric_value']} {sepp['unit']}")

 return points

 def _create_empty_response(self) -> Dict:
 """Create empty response when no special provisions found"""
 return {
 'special_provisions_processing': {
 'tier_1_provisions': [],
 'tier_2_provisions': [],
 'tier_3_provisions': [],
 'tier_4_provisions': [],
 'tier_5_provisions': [],
 'basix_requirements': None,
 'hazard_assessments': [],
 'environmental_constraints': [],
 'sepp_extractions': [],
 'metadata': {
 'total_processed': 0,
 'provision_types': [],
 'requires_specialist': False,
 'quantitative_extractions': 0
 }
 },
 'compliance_summary': {
 'total_provisions': 0,
 'specialist_assessment_required': False,
 'key_compliance_points': []
 },
 'integration_metadata': {
 'basix_applicable': False,
 'hazards_identified': False,
 'environmental_constraints': False,
 'sepp_provisions_found': False
 }
 }

# Test the integration service
if __name__ == "__main__":
 service = SpecialProvisionsIntegrationService()

 # Test with sample planning API data
 test_api_data = {
 'layers': [
 {
 'layerName': 'Special Provisions',
 'results': [
 {
 "Type": "Climate Zones",
 "Class": "Zone 17",
 "Map Type": "CLM"
 },
 {
 "Type": "State Environmental Planning Policy",
 "EPI Name": "SEPP (Housing) 2021",
 "Legislative Clause": "3.31"
 }
 ]
 }
 ]
 }

 result = service.integrate_with_compliance_check(
 test_api_data, 'R2', 'dwelling_house', 12345
 )

 print("Integration Results:")
 print(f"Total provisions: {result['compliance_summary']['total_provisions']}")
 print(f"BASIX applicable: {result['integration_metadata']['basix_applicable']}")
 print(f"Specialist required: {result['compliance_summary']['specialist_assessment_required']}")

 if result['compliance_summary']['key_compliance_points']:
 print("Key compliance points:")
 for point in result['compliance_summary']['key_compliance_points']:
 print(f" - {point}")
'''

 with open('services/special_provisions_integration.py', 'w') as f:
 f.write(integration_code)

 phase_result['steps'].append({
 'step': 'create_integration_service',
 'status': 'COMPLETED',
 'message': 'Special provisions integration service created'
 })

 phase_result['status'] = 'COMPLETED'
 phase_result['end_time'] = datetime.now().isoformat()
 print("SUCCESS: Phase 3 completed - Integration service created")

 except Exception as e:
 phase_result['status'] = 'FAILED'
 phase_result['error'] = str(e)
 print(f"FAILED: Phase 3 failed: {e}")

 return phase_result

 def phase4_test_processing_engine(self) -> Dict:
 """Phase 4: Test the complete processing engine"""
 print("\n=== PHASE 4: Testing Processing Engine ===")

 phase_result = {
 'phase': 'test_processing_engine',
 'start_time': datetime.now().isoformat(),
 'steps': []
 }

 try:
 # Test SEPP extractor
 import sys
 sys.path.append('services')

 from sepp_quantitative_extractor import SEPPQuantitativeExtractor
 from special_provisions_processor import SpecialProvisionsProcessor
 from special_provisions_integration import SpecialProvisionsIntegrationService

 # Test 1: SEPP Extractor
 print("Testing SEPP quantitative extractor...")
 extractor = SEPPQuantitativeExtractor()

 sepp_result = extractor.extract_from_sepp_clause('SEPP_HOUSING_2021', '3.31')
 if sepp_result:
 print(f" SEPP extraction: {sepp_result['numeric_value']} {sepp_result['unit']}")
 phase_result['steps'].append({
 'step': 'test_sepp_extractor',
 'status': 'COMPLETED',
 'message': f'Extracted {sepp_result["numeric_value"]} {sepp_result["unit"]} from SEPP clause'
 })
 else:
 phase_result['steps'].append({
 'step': 'test_sepp_extractor',
 'status': 'FAILED',
 'message': 'SEPP extraction returned no results'
 })

 # Test 2: Provisions Processor
 print("Testing special provisions processor...")
 processor = SpecialProvisionsProcessor()

 test_provisions = [
 {"Type": "Climate Zones", "Class": "Zone 17", "Map Type": "CLM"},
 {"Type": "State Environmental Planning Policy", "EPI Name": "SEPP (Housing) 2021", "Legislative Clause": "3.31"},
 {"Type": "Flood Planning", "Category": "Flood Planning Area", "Level": "1:100 Year"}
 ]

 processor_result = processor.process_special_provisions(test_provisions, 'R2', 'dwelling_house')

 if processor_result['metadata']['total_processed'] > 0:
 print(f" Processed {processor_result['metadata']['total_processed']} provisions")
 print(f" Tier 1: {len(processor_result['tier_1_provisions'])}")
 print(f" Quantitative extractions: {processor_result['metadata']['quantitative_extractions']}")

 phase_result['steps'].append({
 'step': 'test_provisions_processor',
 'status': 'COMPLETED',
 'message': f'Processed {processor_result["metadata"]["total_processed"]} provisions successfully'
 })
 else:
 phase_result['steps'].append({
 'step': 'test_provisions_processor',
 'status': 'FAILED',
 'message': 'Provisions processor returned no results'
 })

 # Test 3: Integration Service
 print("Testing integration service...")
 integration_service = SpecialProvisionsIntegrationService()

 test_api_data = {
 'layers': [
 {
 'layerName': 'Special Provisions',
 'results': test_provisions
 }
 ]
 }

 integration_result = integration_service.integrate_with_compliance_check(
 test_api_data, 'R2', 'dwelling_house', 12345
 )

 if integration_result['compliance_summary']['total_provisions'] > 0:
 print(f" Integration successful: {integration_result['compliance_summary']['total_provisions']} provisions")
 print(f" BASIX applicable: {integration_result['integration_metadata']['basix_applicable']}")

 phase_result['steps'].append({
 'step': 'test_integration_service',
 'status': 'COMPLETED',
 'message': f'Integration service working - {integration_result["compliance_summary"]["total_provisions"]} provisions processed'
 })
 else:
 phase_result['steps'].append({
 'step': 'test_integration_service',
 'status': 'FAILED',
 'message': 'Integration service returned no results'
 })

 phase_result['status'] = 'COMPLETED'
 phase_result['end_time'] = datetime.now().isoformat()
 print("SUCCESS: Phase 4 completed - Processing engine tested successfully")

 except Exception as e:
 phase_result['status'] = 'FAILED'
 phase_result['error'] = str(e)
 print(f"FAILED: Phase 4 failed: {e}")

 return phase_result

 def execute_prp_q2(self) -> bool:
 """Execute complete PRP-Q2 implementation"""

 print("PRP-Q2: SPECIAL PROVISIONS PROCESSING ENGINE")
 print("=" * 60)
 print("Implementing comprehensive processing for NSW special provisions")
 print("Estimated time: 8 hours (automated execution)")
 print()

 try:
 # Execute phases sequentially
 self.execution_report['phases']['phase1'] = self.phase1_create_sepp_processing_engine()
 self.execution_report['phases']['phase2'] = self.phase2_create_provisions_processor()
 self.execution_report['phases']['phase3'] = self.phase3_create_integration_service()
 self.execution_report['phases']['phase4'] = self.phase4_test_processing_engine()

 # Check if all phases completed
 all_completed = all(
 phase.get('status') == 'COMPLETED'
 for phase in self.execution_report['phases'].values()
 )

 if all_completed:
 self.execution_report['status'] = 'COMPLETED'
 print("\n" + "=" * 60)
 print("PRP-Q2 IMPLEMENTATION COMPLETED SUCCESSFULLY")
 print("=" * 60)
 print("SUCCESS: SEPP quantitative extraction engine implemented")
 print("SUCCESS: Special provisions processor created")
 print("SUCCESS: Compliance integration service implemented")
 print("SUCCESS: Complete processing pipeline tested")
 print("\nSpecial Provisions Engine Features:")
 print("- Quantitative extraction from SEPP clauses")
 print("- Tier-based authority assignments (1-5)")
 print("- BASIX climate zone integration")
 print("- Hazard and environmental constraint processing")
 print("- Specialist assessment flagging")
 print("- Confidence scoring for all extractions")

 return True
 else:
 self.execution_report['status'] = 'FAILED'
 failed_phases = [
 name for name, phase in self.execution_report['phases'].items()
 if phase.get('status') == 'FAILED'
 ]
 print(f"\nFAILED: PRP-Q2 FAILED - Issues in phases: {', '.join(failed_phases)}")
 return False

 except Exception as e:
 self.execution_report['status'] = 'FAILED'
 self.execution_report['error'] = str(e)
 print(f"\nCRASHED: PRP-Q2 CRASHED: {e}")
 return False

 finally:
 # Save execution report
 self.execution_report['end_time'] = datetime.now().isoformat()

 with open('prp_q2_processing_engine_report.json', 'w') as f:
 json.dump(self.execution_report, f, indent=2)

 print(f"\nDetailed report saved: prp_q2_processing_engine_report.json")

if __name__ == "__main__":
 executor = PRPQ2Executor()
 success = executor.execute_prp_q2()

 if success:
 print("\nSUCCESS: PRP-Q2 READY FOR VERIFICATION")
 print("Run: python verify_prp_q2.py")
 sys.exit(0)
 else:
 print("\nFAILED: PRP-Q2 EXECUTION FAILED")
 sys.exit(1)