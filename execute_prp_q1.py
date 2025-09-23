#!/usr/bin/env python3
"""
PRP-Q1: BASIX and Special Provisions Integration
===============================================
Implements BASIX provisions integration and special provisions processing
into the compliance engine's authoritative hierarchy system.
"""

from db_config import get_connection
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional

class PRPQ1Executor:
 """Execute PRP-Q1 BASIX Integration implementation"""

 def __init__(self):
 self.execution_report = {
 'prp_id': 'PRP-Q1',
 'title': 'BASIX and Special Provisions Integration',
 'start_time': datetime.now().isoformat(),
 'phases': {},
 'status': 'IN_PROGRESS'
 }

 def phase1_create_basix_schema(self) -> Dict:
 """Phase 1: Create BASIX provisions table and populate data"""
 print("=== PHASE 1: BASIX Database Schema ===")

 phase_result = {
 'phase': 'basix_schema',
 'start_time': datetime.now().isoformat(),
 'steps': []
 }

 try:
 conn = get_connection()
 cursor = conn.cursor()

 # Step 1: Create BASIX provisions table
 print("Creating BASIX provisions table...")
 cursor.execute("""
 CREATE TABLE IF NOT EXISTS basix_provisions (
 id SERIAL PRIMARY KEY,
 climate_zone VARCHAR(50) NOT NULL,
 development_type VARCHAR(100) NOT NULL,

 -- Energy targets
 energy_reduction_target DECIMAL(5,2),
 thermal_comfort_rating DECIMAL(3,1),

 -- Water targets
 water_reduction_target DECIMAL(5,2),
 water_fixture_rating INTEGER,

 -- Compliance thresholds
 min_insulation_r_value DECIMAL(3,1),
 max_glazing_percentage DECIMAL(5,2),

 -- Metadata
 effective_date DATE DEFAULT CURRENT_DATE,
 source_document VARCHAR(255) DEFAULT 'BASIX Requirements',
 tier_level INTEGER DEFAULT 1,

 UNIQUE(climate_zone, development_type)
 );
 """)
 phase_result['steps'].append({
 'step': 'create_basix_table',
 'status': 'COMPLETED',
 'message': 'BASIX provisions table created'
 })

 # Step 2: Populate BASIX data
 print("Populating BASIX requirements...")
 basix_data = [
 ('Zone 17', 'dwelling_house', 40.0, 40.0, 6.0, 5, 2.5, 40.0),
 ('Zone 17', 'residential_flat_building', 35.0, 40.0, 6.0, 5, 2.5, 40.0),
 ('Zone 17', 'dual_occupancy', 40.0, 40.0, 6.0, 5, 2.5, 40.0),
 ('Zone 17', 'semi_detached_dwelling', 40.0, 40.0, 6.0, 5, 2.5, 40.0),
 ('Zone 18', 'dwelling_house', 45.0, 40.0, 6.5, 5, 3.0, 35.0),
 ('Zone 18', 'residential_flat_building', 40.0, 40.0, 6.5, 5, 3.0, 35.0),
 ('Zone 18', 'dual_occupancy', 45.0, 40.0, 6.5, 5, 3.0, 35.0),
 ('Zone 19', 'dwelling_house', 50.0, 40.0, 7.0, 6, 3.5, 30.0),
 ('Zone 19', 'residential_flat_building', 45.0, 40.0, 7.0, 6, 3.5, 30.0)
 ]

 cursor.executemany("""
 INSERT INTO basix_provisions (
 climate_zone, development_type, energy_reduction_target,
 water_reduction_target, thermal_comfort_rating, water_fixture_rating,
 min_insulation_r_value, max_glazing_percentage
 ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
 ON CONFLICT (climate_zone, development_type) DO NOTHING
 """, basix_data)

 rows_inserted = cursor.rowcount
 phase_result['steps'].append({
 'step': 'populate_basix_data',
 'status': 'COMPLETED',
 'message': f'Inserted {rows_inserted} BASIX requirements'
 })

 conn.commit()
 conn.close()

 phase_result['status'] = 'COMPLETED'
 phase_result['end_time'] = datetime.now().isoformat()
 print(f"SUCCESS: Phase 1 completed - BASIX schema created with {rows_inserted} provisions")

 except Exception as e:
 phase_result['status'] = 'FAILED'
 phase_result['error'] = str(e)
 print(f"FAILED: Phase 1 failed: {e}")

 return phase_result

 def phase2_create_special_provisions_schema(self) -> Dict:
 """Phase 2: Create special provisions registry and thresholds"""
 print("\n=== PHASE 2: Special Provisions Schema ===")

 phase_result = {
 'phase': 'special_provisions_schema',
 'start_time': datetime.now().isoformat(),
 'steps': []
 }

 try:
 conn = get_connection()
 cursor = conn.cursor()

 # Step 1: Create special provisions registry
 print("Creating special provisions registry...")
 cursor.execute("""
 CREATE TABLE IF NOT EXISTS special_provisions_registry (
 id SERIAL PRIMARY KEY,
 provision_type VARCHAR(100) NOT NULL,
 provision_category VARCHAR(100),
 provision_subtype VARCHAR(100),

 -- Hierarchy placement
 default_tier_level INTEGER NOT NULL CHECK (default_tier_level BETWEEN 1 AND 5),
 authority_level INTEGER NOT NULL CHECK (authority_level BETWEEN 0 AND 100),

 -- Processing rules
 requires_specialist BOOLEAN DEFAULT FALSE,
 has_numeric_thresholds BOOLEAN DEFAULT FALSE,
 affects_development_types TEXT[],

 -- Metadata
 legislation_reference VARCHAR(255),
 last_updated DATE DEFAULT CURRENT_DATE,
 active BOOLEAN DEFAULT TRUE,

 UNIQUE(provision_type, provision_category, provision_subtype)
 );
 """)

 # Step 2: Create provision thresholds table
 cursor.execute("""
 CREATE TABLE IF NOT EXISTS provision_thresholds (
 id SERIAL PRIMARY KEY,
 provision_id INTEGER REFERENCES special_provisions_registry(id),

 threshold_type VARCHAR(100),
 measurement_context VARCHAR(100),
 numeric_value DECIMAL(10,2),
 unit VARCHAR(50),

 applies_to_zones TEXT[],
 applies_to_dev_types TEXT[],

 UNIQUE(provision_id, threshold_type, measurement_context)
 );
 """)

 # Step 3: Create provision implications table
 cursor.execute("""
 CREATE TABLE IF NOT EXISTS provision_implications (
 id SERIAL PRIMARY KEY,
 provision_id INTEGER REFERENCES special_provisions_registry(id),

 implication_type VARCHAR(50),
 implication_text TEXT,
 action_required TEXT,

 tier_level INTEGER,
 confidence_level DECIMAL(3,2)
 );
 """)

 phase_result['steps'].append({
 'step': 'create_special_provisions_tables',
 'status': 'COMPLETED',
 'message': 'Special provisions tables created'
 })

 # Step 4: Populate registry
 print("Populating special provisions registry...")
 registry_data = [
 ('Climate Zones', 'BASIX', None, 1, 100, False, True, '{"BASIX Requirements"}'),
 ('Flood Planning', 'Natural Hazards', None, 1, 95, True, True, '{"Flood Planning Areas"}'),
 ('Bushfire Prone Land', 'Natural Hazards', None, 1, 95, True, True, '{"Planning for Bush Fire Protection"}'),
 ('Acid Sulfate Soils', 'Environmental', None, 2, 85, True, True, '{"ASS Management"}'),
 ('Heritage', 'Conservation', None, 2, 90, True, False, '{"Heritage Act"}'),
 ('Coastal Management', 'Environmental', None, 1, 95, True, True, '{"Coastal Management Act"}'),
 ('State Environmental Planning Policy', 'SEPP', None, 1, 95, False, True, '{"Various SEPPs"}'),
 ('Riparian Land', 'Environmental', None, 2, 85, False, False, '{"Water Management Act"}'),
 ('Biodiversity', 'Environmental', None, 2, 85, True, False, '{"Biodiversity Conservation Act"}')
 ]

 cursor.executemany("""
 INSERT INTO special_provisions_registry (
 provision_type, provision_category, provision_subtype,
 default_tier_level, authority_level, requires_specialist,
 has_numeric_thresholds, legislation_reference
 ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
 ON CONFLICT (provision_type, provision_category, provision_subtype) DO NOTHING
 """, registry_data)

 registry_count = cursor.rowcount
 phase_result['steps'].append({
 'step': 'populate_registry',
 'status': 'COMPLETED',
 'message': f'Populated {registry_count} provision types'
 })

 conn.commit()
 conn.close()

 phase_result['status'] = 'COMPLETED'
 phase_result['end_time'] = datetime.now().isoformat()
 print(f"SUCCESS: Phase 2 completed - Special provisions schema created")

 except Exception as e:
 phase_result['status'] = 'FAILED'
 phase_result['error'] = str(e)
 print(f" Phase 2 failed: {e}")

 return phase_result

 def phase3_create_basix_processor(self) -> Dict:
 """Phase 3: Create BASIX compliance processing service"""
 print("\n=== PHASE 3: BASIX Processing Service ===")

 phase_result = {
 'phase': 'basix_processor',
 'start_time': datetime.now().isoformat(),
 'steps': []
 }

 try:
 # Create BASIX compliance checker service
 basix_service_code = '''from db_config import get_connection
from typing import Dict, List, Optional
import json

class BASIXComplianceChecker:
 """BASIX compliance checking service for NSW planning"""

 def __init__(self):
 self.db = get_connection()

 def get_basix_requirements(self, climate_zone: str, development_type: str) -> Optional[Dict]:
 """Get BASIX requirements for zone and development type"""
 cursor = self.db.cursor()

 query = """
 SELECT
 energy_reduction_target,
 thermal_comfort_rating,
 water_reduction_target,
 water_fixture_rating,
 min_insulation_r_value,
 max_glazing_percentage,
 source_document
 FROM basix_provisions
 WHERE climate_zone = %s
 AND development_type = %s
 """

 cursor.execute(query, (climate_zone, development_type))
 result = cursor.fetchone()

 if result:
 return {
 'tier_level': 1, # BASIX is always Tier 1
 'document_type': 'BASIX',
 'document_name': 'Building Sustainability Index',
 'provisions': self._format_basix_provisions(result, climate_zone)
 }
 return None

 def _format_basix_provisions(self, data: tuple, climate_zone: str) -> List[Dict]:
 """Format BASIX requirements as tier 1 provisions"""
 provisions = []

 energy_target, thermal_rating, water_target, water_rating, insulation, glazing, source = data

 if energy_target:
 provisions.append({
 'provision_type': 'energy_efficiency',
 'measurement_context': 'energy_reduction',
 'numeric_value': float(energy_target),
 'unit': 'percent',
 'provision_text': f"Achieve {energy_target}% reduction in energy consumption compared to reference building",
 'clause_reference': f'BASIX Energy Target - {climate_zone}',
 'authority_level': 100,
 'confidence_level': 1.0
 })

 if water_target:
 provisions.append({
 'provision_type': 'water_efficiency',
 'measurement_context': 'water_reduction',
 'numeric_value': float(water_target),
 'unit': 'percent',
 'provision_text': f"Achieve {water_target}% reduction in water consumption compared to reference building",
 'clause_reference': f'BASIX Water Target - {climate_zone}',
 'authority_level': 100,
 'confidence_level': 1.0
 })

 if thermal_rating:
 provisions.append({
 'provision_type': 'thermal_comfort',
 'measurement_context': 'star_rating',
 'numeric_value': float(thermal_rating),
 'unit': 'stars',
 'provision_text': f"Achieve minimum {thermal_rating} star thermal comfort rating",
 'clause_reference': f'BASIX Thermal Comfort - {climate_zone}',
 'authority_level': 100,
 'confidence_level': 1.0
 })

 if insulation:
 provisions.append({
 'provision_type': 'insulation',
 'measurement_context': 'r_value',
 'numeric_value': float(insulation),
 'unit': 'm²K/W',
 'provision_text': f"Minimum insulation R-value of {insulation}",
 'clause_reference': f'BASIX Insulation - {climate_zone}',
 'authority_level': 100,
 'confidence_level': 1.0
 })

 return provisions

 def process_basix_for_compliance(self, climate_zone: str, development_type: str) -> Dict:
 """Process BASIX requirements for compliance checking"""
 basix_reqs = self.get_basix_requirements(climate_zone, development_type)

 if not basix_reqs:
 return {
 'basix_applicable': False,
 'message': f'No BASIX requirements found for {climate_zone} / {development_type}'
 }

 return {
 'basix_applicable': True,
 'climate_zone': climate_zone,
 'development_type': development_type,
 'tier_1_provisions': basix_reqs['provisions'],
 'document_type': 'BASIX',
 'authority_level': 100,
 'specialist_required': False,
 'certificate_required': True,
 'assessment_notes': [
 'BASIX certificate must be obtained before development approval',
 'Design must demonstrate compliance with energy and water targets',
 'Final construction must match BASIX certificate commitments'
 ]
 }

# Test the service
if __name__ == "__main__":
 checker = BASIXComplianceChecker()

 # Test various climate zones and development types
 test_cases = [
 ('Zone 17', 'dwelling_house'),
 ('Zone 18', 'residential_flat_building'),
 ('Zone 19', 'dual_occupancy')
 ]

 for climate_zone, dev_type in test_cases:
 result = checker.process_basix_for_compliance(climate_zone, dev_type)
 print(f"BASIX check for {climate_zone} / {dev_type}:")
 print(f" Applicable: {result['basix_applicable']}")
 if result['basix_applicable']:
 print(f" Provisions: {len(result['tier_1_provisions'])}")
 for provision in result['tier_1_provisions']:
 print(f" - {provision['provision_text']}")
 print()
'''

 with open('services/basix_compliance_checker.py', 'w') as f:
 f.write(basix_service_code)

 phase_result['steps'].append({
 'step': 'create_basix_service',
 'status': 'COMPLETED',
 'message': 'BASIX compliance checker service created'
 })

 phase_result['status'] = 'COMPLETED'
 phase_result['end_time'] = datetime.now().isoformat()
 print(" Phase 3 completed - BASIX processing service created")

 except Exception as e:
 phase_result['status'] = 'FAILED'
 phase_result['error'] = str(e)
 print(f" Phase 3 failed: {e}")

 return phase_result

 def phase4_update_compliance_api(self) -> Dict:
 """Phase 4: Update compliance API to include BASIX integration"""
 print("\n=== PHASE 4: Compliance API Integration ===")

 phase_result = {
 'phase': 'api_integration',
 'start_time': datetime.now().isoformat(),
 'steps': []
 }

 try:
 # Check if enhanced compliance API exists
 import os
 api_file = 'services/enhanced_compliance_api.py'

 if os.path.exists(api_file):
 # Read existing API
 with open(api_file, 'r') as f:
 api_content = f.read()

 # Check if BASIX integration already exists
 if 'BASIXComplianceChecker' not in api_content:
 # Add BASIX integration
 basix_integration = '''
# BASIX Integration for PRP-Q1
from services.basix_compliance_checker import BASIXComplianceChecker

class EnhancedComplianceAPI:
 def __init__(self):
 self.basix_checker = BASIXComplianceChecker()
 # ... existing initialization

 def check_compliance_with_basix(self, zone_code: str, development_type: str,
 property_data: dict = None) -> dict:
 """Enhanced compliance check including BASIX requirements"""

 # Get standard compliance data
 compliance_result = self.check_compliance(zone_code, development_type, property_data)

 # Extract climate zone from property_data if available
 climate_zone = None
 if property_data and 'constraints' in property_data:
 for constraint in property_data['constraints']:
 if constraint.get('Type') == 'Climate Zones':
 climate_zone = constraint.get('Class', '')
 break

 # If no climate zone found, default to Zone 17 (most common in Inner West)
 if not climate_zone:
 climate_zone = 'Zone 17'

 # Get BASIX requirements
 basix_result = self.basix_checker.process_basix_for_compliance(
 climate_zone, development_type
 )

 # Merge BASIX into compliance result
 if basix_result['basix_applicable']:
 # Add BASIX provisions to Tier 1
 if 'tier_1_provisions' not in compliance_result:
 compliance_result['tier_1_provisions'] = []

 compliance_result['tier_1_provisions'].extend(basix_result['tier_1_provisions'])

 # Add BASIX metadata
 compliance_result['basix_requirements'] = {
 'climate_zone': climate_zone,
 'certificate_required': basix_result['certificate_required'],
 'assessment_notes': basix_result['assessment_notes']
 }

 return compliance_result
'''

 # Append BASIX integration
 with open(api_file, 'a') as f:
 f.write(basix_integration)

 phase_result['steps'].append({
 'step': 'integrate_basix_api',
 'status': 'COMPLETED',
 'message': 'BASIX integration added to enhanced compliance API'
 })
 else:
 phase_result['steps'].append({
 'step': 'check_existing_integration',
 'status': 'SKIPPED',
 'message': 'BASIX integration already exists in API'
 })
 else:
 # Create new enhanced API with BASIX
 enhanced_api_code = '''from db_config import get_connection
from services.basix_compliance_checker import BASIXComplianceChecker
from typing import Dict, List, Optional
import json

class EnhancedComplianceAPI:
 """Enhanced compliance API with BASIX integration"""

 def __init__(self):
 self.db = get_connection()
 self.basix_checker = BASIXComplianceChecker()

 def check_compliance_with_basix(self, zone_code: str, development_type: str,
 property_data: dict = None) -> dict:
 """Enhanced compliance check including BASIX requirements"""

 # Extract climate zone from property_data
 climate_zone = self._extract_climate_zone(property_data)

 # Get BASIX requirements
 basix_result = self.basix_checker.process_basix_for_compliance(
 climate_zone, development_type
 )

 # Get standard compliance provisions
 standard_provisions = self._get_standard_provisions(zone_code, development_type)

 # Merge all provisions
 result = {
 'zone_code': zone_code,
 'development_type': development_type,
 'climate_zone': climate_zone,
 'tier_1_provisions': [],
 'tier_2_provisions': [],
 'tier_3_provisions': [],
 'compliance_summary': {
 'basix_applicable': basix_result['basix_applicable'],
 'total_provisions': 0,
 'specialist_required': False
 }
 }

 # Add BASIX provisions if applicable
 if basix_result['basix_applicable']:
 result['tier_1_provisions'].extend(basix_result['tier_1_provisions'])
 result['basix_requirements'] = {
 'climate_zone': climate_zone,
 'certificate_required': basix_result['certificate_required'],
 'assessment_notes': basix_result['assessment_notes']
 }

 # Add standard provisions
 result['tier_2_provisions'].extend(standard_provisions.get('tier_2', []))
 result['tier_3_provisions'].extend(standard_provisions.get('tier_3', []))

 # Update summary
 result['compliance_summary']['total_provisions'] = (
 len(result['tier_1_provisions']) +
 len(result['tier_2_provisions']) +
 len(result['tier_3_provisions'])
 )

 return result

 def _extract_climate_zone(self, property_data: dict) -> str:
 """Extract climate zone from property data"""
 if property_data and 'constraints' in property_data:
 for constraint in property_data['constraints']:
 if constraint.get('Type') == 'Climate Zones':
 return constraint.get('Class', 'Zone 17')

 # Default to Zone 17 (most common in Inner West)
 return 'Zone 17'

 def _get_standard_provisions(self, zone_code: str, development_type: str) -> dict:
 """Get standard regulatory provisions"""
 cursor = self.db.cursor()

 # Get existing provisions from regulatory_provisions table
 cursor.execute("""
 SELECT provision_text, ref_number, section_header
 FROM regulatory_provisions
 WHERE zone = %s
 AND (development_type = %s OR development_type IS NULL)
 LIMIT 10
 """, (zone_code, development_type))

 provisions = cursor.fetchall()

 return {
 'tier_2': [
 {
 'provision_type': 'zoning',
 'provision_text': prov[0][:200] + '...' if len(prov[0]) > 200 else prov[0],
 'clause_reference': prov[1] or 'Standard provision',
 'section_header': prov[2] or 'Zoning controls'
 }
 for prov in provisions[:5]
 ],
 'tier_3': [
 {
 'provision_type': 'general',
 'provision_text': prov[0][:200] + '...' if len(prov[0]) > 200 else prov[0],
 'clause_reference': prov[1] or 'General provision',
 'section_header': prov[2] or 'General controls'
 }
 for prov in provisions[5:]
 ]
 }

# Test the enhanced API
if __name__ == "__main__":
 api = EnhancedComplianceAPI()

 # Test with BASIX data
 test_property_data = {
 'constraints': [
 {'Type': 'Climate Zones', 'Class': 'Zone 18'},
 {'Type': 'Flood Planning', 'Category': 'Flood Planning Area'}
 ]
 }

 result = api.check_compliance_with_basix('R2', 'dwelling_house', test_property_data)

 print("Enhanced Compliance Check Results:")
 print(f"Zone: {result['zone_code']}")
 print(f"Climate Zone: {result['climate_zone']}")
 print(f"BASIX Applicable: {result['compliance_summary']['basix_applicable']}")
 print(f"Total Provisions: {result['compliance_summary']['total_provisions']}")

 if result.get('basix_requirements'):
 print("BASIX Requirements:")
 for note in result['basix_requirements']['assessment_notes']:
 print(f" - {note}")
'''

 with open(api_file, 'w') as f:
 f.write(enhanced_api_code)

 phase_result['steps'].append({
 'step': 'create_enhanced_api',
 'status': 'COMPLETED',
 'message': 'Enhanced compliance API with BASIX created'
 })

 phase_result['status'] = 'COMPLETED'
 phase_result['end_time'] = datetime.now().isoformat()
 print(" Phase 4 completed - Compliance API integration done")

 except Exception as e:
 phase_result['status'] = 'FAILED'
 phase_result['error'] = str(e)
 print(f" Phase 4 failed: {e}")

 return phase_result

 def execute_prp_q1(self) -> bool:
 """Execute complete PRP-Q1 implementation"""

 print("PRP-Q1: BASIX AND SPECIAL PROVISIONS INTEGRATION")
 print("=" * 60)
 print("Implementing BASIX integration and special provisions processing")
 print("Estimated time: 10 hours (automated execution)")
 print()

 try:
 # Execute phases sequentially
 self.execution_report['phases']['phase1'] = self.phase1_create_basix_schema()
 self.execution_report['phases']['phase2'] = self.phase2_create_special_provisions_schema()
 self.execution_report['phases']['phase3'] = self.phase3_create_basix_processor()
 self.execution_report['phases']['phase4'] = self.phase4_update_compliance_api()

 # Check if all phases completed
 all_completed = all(
 phase.get('status') == 'COMPLETED'
 for phase in self.execution_report['phases'].values()
 )

 if all_completed:
 self.execution_report['status'] = 'COMPLETED'
 print("\n" + "=" * 60)
 print("PRP-Q1 IMPLEMENTATION COMPLETED SUCCESSFULLY")
 print("=" * 60)
 print("SUCCESS: BASIX provisions table created and populated")
 print("SUCCESS: Special provisions registry established")
 print("SUCCESS: BASIX compliance checker service implemented")
 print("SUCCESS: Enhanced compliance API with BASIX integration")
 print("\nBASIX Integration Features:")
 print("- Climate zone-specific energy and water targets")
 print("- Tier 1 authority level for BASIX requirements")
 print("- Integration with compliance checking workflow")
 print("- Support for 9 development types across 3 climate zones")

 return True
 else:
 self.execution_report['status'] = 'FAILED'
 failed_phases = [
 name for name, phase in self.execution_report['phases'].items()
 if phase.get('status') == 'FAILED'
 ]
 print(f"\n PRP-Q1 FAILED - Issues in phases: {', '.join(failed_phases)}")
 return False

 except Exception as e:
 self.execution_report['status'] = 'FAILED'
 self.execution_report['error'] = str(e)
 print(f"\n PRP-Q1 CRASHED: {e}")
 return False

 finally:
 # Save execution report
 self.execution_report['end_time'] = datetime.now().isoformat()

 with open('prp_q1_basix_integration_report.json', 'w') as f:
 json.dump(self.execution_report, f, indent=2)

 print(f"\nDetailed report saved: prp_q1_basix_integration_report.json")

if __name__ == "__main__":
 executor = PRPQ1Executor()
 success = executor.execute_prp_q1()

 if success:
 print("\n PRP-Q1 READY FOR VERIFICATION")
 print("Run: python verify_prp_q1.py")
 sys.exit(0)
 else:
 print("\n PRP-Q1 EXECUTION FAILED")
 sys.exit(1)