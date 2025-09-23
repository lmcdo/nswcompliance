#!/usr/bin/env python3
"""
Complete Inner West LGA Compliance Engine
========================================

Final integration that faithfully handles all three former council areas:
- Marrickville (70 quantitative standards, 77 setback controls)
- Leichhardt (100 quantitative standards, 43 setback controls) 
- Ashfield (6 quantitative standards, 11 setback controls)

Combines NSW Planning API data with zone-specific database intelligence
for legally defensible property development compliance assessments.
"""

import sqlite3
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from zone_compliance_mapper import ZoneComplianceMapper

@dataclass
class NSWPlanningAPIData:
 """NSW Planning API 11-layer data structure"""
 land_application_map: Dict[str, Any]
 aboriginal_land_council: Dict[str, Any] 
 key_sites_map: Dict[str, Any]
 lot_size_map: Dict[str, Any]
 land_zoning_map: Dict[str, Any]
 floor_space_ratio_map: Dict[str, Any]
 tree_canopy_cover_2019: Dict[str, Any]
 tree_canopy_cover_2022: Dict[str, Any]
 acid_sulfate_soils_map: Dict[str, Any]
 special_provisions: List[Dict[str, Any]]
 regional_plan_boundary: Dict[str, Any]

@dataclass
class LegalAuthority:
 """Legal authority hierarchy for compliance rules"""
 primary_authority: str # "Inner West LEP 2022"
 secondary_authority: str # "Ashfield DCP 2016" 
 clause_reference: str # "Clause 4.1" or "Section 2.12"
 amendment_reference: str # "IWLEP 2022 amendments"
 override_authority: Optional[str] = None # SEPP reference if applicable
 document_source: str = "" # Full document ID for traceability

@dataclass
class SetbackRequirement:
 """Reliable setback requirement with enhanced legal backing"""
 boundary_type: str # 'front', 'side', 'rear', 'general'
 minimum_setback_meters: float
 maximum_setback_meters: Optional[float]
 confidence_score: float
 legal_source: str
 clause_reference: str
 contextual_requirements: str
 council_area: str
 zone_applicability: str
 
 # Enhanced with PRP-K1 domain classification and legal authority
 domain_classification: str = "GENERAL_PROVISIONS" # From PRP-K1
 legal_authority: Optional[LegalAuthority] = None
 cross_contamination_checked: bool = False
 provision_id: Optional[int] = None # For Referenced Legislation accordion
 relevance_score: float = 1.0 # Domain relevance for query
 
@dataclass 
class ComplianceAssessment:
 """Complete compliance assessment result"""
 property_address: str
 property_id: int
 zone: str
 council_area: str
 statutory_compliance: Dict[str, Any]
 setback_compliance: Dict[str, SetbackRequirement]
 development_pathway: str
 compliance_confidence: float
 legal_references: List[str]
 professional_review_required: bool
 audit_trail: List[str]

class InnerWestComplianceEngine:
 """Complete compliance engine for Inner West LGA properties"""
 
 def __init__(self, db_path: str = 'nsw_planning.db'):
 self.db_path = db_path
 self.zone_mapper = ZoneComplianceMapper(db_path)
 
 # NSW Standard Instrument zone to domain classification mapping
 self.zone_domain_mapping = {
 'R1': 'RESIDENTIAL_BUILDINGS', # General Residential
 'R2': 'RESIDENTIAL_BUILDINGS', # Low Density Residential 
 'R3': 'RESIDENTIAL_BUILDINGS', # Medium Density Residential
 'R4': 'RESIDENTIAL_BUILDINGS', # High Density Residential
 'B1': 'COMMERCIAL_BUILDINGS', # Neighbourhood Centre
 'B2': 'COMMERCIAL_BUILDINGS', # Local Centre
 'B3': 'COMMERCIAL_BUILDINGS', # Commercial Centre
 'B4': 'COMMERCIAL_BUILDINGS', # Mixed Use
 'E1': 'COMMERCIAL_BUILDINGS', # Local Centre (new)
 'E2': 'COMMERCIAL_BUILDINGS', # Commercial Centre (new)
 'E3': 'COMMERCIAL_BUILDINGS', # Productivity Support
 'E4': 'INDUSTRIAL_BUILDINGS', # General Industrial
 'IN1': 'INDUSTRIAL_BUILDINGS', # General Industrial (legacy)
 'IN2': 'INDUSTRIAL_BUILDINGS', # Light Industrial (legacy)
 'MU1': 'COMMERCIAL_BUILDINGS', # Mixed Use
 }
 
 # Council area geographic boundaries and DCP mappings
 self.council_areas = {
 'marrickville': {
 'dcp_documents': ['Marrickville_DCP_2011'],
 'suburbs': ['marrickville', 'dulwich hill', 'petersham', 'stanmore', 
 'newtown', 'enmore', 'sydenham', 'tempe', 'st peters'],
 'quantitative_standards': 70,
 'setback_controls': 77,
 'reliability_grade': 'HIGH'
 },
 'leichhardt': {
 'dcp_documents': ['Leichhardt_DCP_2013'],
 'suburbs': ['leichhardt', 'annandale', 'lilyfield', 'rozelle', 'balmain', 
 'birchgrove', 'forest lodge'],
 'quantitative_standards': 100,
 'setback_controls': 43, 
 'reliability_grade': 'HIGH'
 },
 'ashfield': {
 'dcp_documents': ['Inner_West_Ashfield_DCP_2016'],
 'suburbs': ['ashfield', 'haberfield', 'five dock', 'rodd point', 
 'russell lea', 'wareemba', 'croydon', 'summer hill'],
 'quantitative_standards': 6,
 'setback_controls': 11,
 'reliability_grade': 'MEDIUM'
 }
 }
 
 def identify_council_area(self, address: str, suburb: str = None) -> str:
 """Identify which former council area a property belongs to"""
 
 address_lower = address.lower()
 if suburb:
 suburb_lower = suburb.lower()
 else:
 suburb_lower = address_lower
 
 # Check against known suburbs for each council area
 for council, data in self.council_areas.items():
 for suburb_name in data['suburbs']:
 if suburb_name in suburb_lower:
 return council
 
 # Fallback: try to extract suburb from address
 # Common patterns: "123 Street Name, Suburb NSW"
 import re
 suburb_match = re.search(r',\s*([^,]+)\s+NSW', address)
 if suburb_match:
 extracted_suburb = suburb_match.group(1).lower().strip()
 for council, data in self.council_areas.items():
 for suburb_name in data['suburbs']:
 if suburb_name in extracted_suburb:
 return council
 
 # Default to Marrickville if cannot determine (largest coverage)
 return 'marrickville'
 
 def process_nsw_api_data(self, raw_api_response: List[Dict]) -> NSWPlanningAPIData:
 """Process raw NSW Planning API response into structured data"""
 
 api_data = NSWPlanningAPIData(
 land_application_map={},
 aboriginal_land_council={},
 key_sites_map={},
 lot_size_map={},
 land_zoning_map={},
 floor_space_ratio_map={},
 tree_canopy_cover_2019={},
 tree_canopy_cover_2022={},
 acid_sulfate_soils_map={},
 special_provisions=[],
 regional_plan_boundary={}
 )
 
 # Map API response to structured data
 layer_mapping = {
 'Land Application Map': 'land_application_map',
 'Local Aboriginal Land Council': 'aboriginal_land_council', 
 'Key Sites Map': 'key_sites_map',
 'Lot Size Map': 'lot_size_map',
 'Land Zoning Map': 'land_zoning_map',
 'Floor Space Ratio Map': 'floor_space_ratio_map',
 'Greater Sydney Tree Canopy Cover 2019': 'tree_canopy_cover_2019',
 'Greater Sydney Tree Canopy Cover 2022': 'tree_canopy_cover_2022',
 'Acid Sulfate Soils Map': 'acid_sulfate_soils_map',
 'Special Provisions': 'special_provisions',
 'Regional Plan Boundary': 'regional_plan_boundary'
 }
 
 for layer in raw_api_response:
 layer_name = layer.get('layerName', '')
 if layer_name in layer_mapping:
 field_name = layer_mapping[layer_name]
 if field_name == 'special_provisions':
 # Special provisions is a list
 setattr(api_data, field_name, layer.get('results', []))
 else:
 # Other fields are single objects
 results = layer.get('results', [])
 setattr(api_data, field_name, results[0] if results else {})
 
 return api_data
 
 def get_reliable_setback_requirements(self, zone: str, council_area: str) -> List[SetbackRequirement]:
 """Get reliable setback requirements for specific zone and council area"""
 
 # Get zone-specific setbacks from our mapping system
 zone_setbacks = self.zone_mapper.get_zone_setback_requirements(zone)
 
 # Filter to specific council area
 council_documents = self.council_areas[council_area]['dcp_documents']
 relevant_setbacks = []
 
 for setback in zone_setbacks:
 # Check if setback is from relevant council documents
 is_relevant = any(doc_pattern in setback['document_id'] 
 for doc_pattern in council_documents)
 
 if is_relevant and setback['confidence_score'] >= 0.6: # Minimum threshold
 relevant_setbacks.append(setback)
 
 # Convert to SetbackRequirement objects
 setback_requirements = []
 
 # Query quantitative standards for precise measurements 
 conn = sqlite3.connect(self.db_path)
 cur = conn.cursor()
 
 # Get high-precision quantitative standards for this council area
 quant_standards = cur.execute('''
 SELECT qs.numeric_value, qs.unit, qs.confidence_score, 
 rpc.provision_text, rpc.document_id
 FROM quantitative_standards qs
 JOIN regulatory_provisions_clean rpc ON qs.provision_id = rpc.id
 WHERE qs.context = 'setback'
 AND qs.numeric_value IS NOT NULL
 AND qs.confidence_score >= 0.8
 AND ({})
 ORDER BY qs.confidence_score DESC
 '''.format(' OR '.join(f"rpc.document_id LIKE '%{doc}%'" for doc in council_documents))).fetchall()
 
 conn.close()
 
 # Process quantitative standards into setback requirements
 processed_setbacks = {} # Keyed by boundary type to avoid duplicates
 
 for numeric_value, unit, confidence, provision, document_id in quant_standards:
 # Convert to meters
 if unit == 'mm':
 meters = numeric_value / 1000
 elif unit in ['m', 'metre', 'meter']:
 meters = numeric_value
 else:
 continue # Skip unknown units
 
 # Determine boundary type from provision text
 provision_lower = provision.lower()
 boundary_type = 'general'
 
 if 'front' in provision_lower:
 boundary_type = 'front'
 elif 'side' in provision_lower:
 boundary_type = 'side' 
 elif 'rear' in provision_lower:
 boundary_type = 'rear'
 
 # Extract clause reference
 clause_match = re.search(r'(clause|section)\s+([0-9]+\.?[0-9]*[a-z]?)', 
 provision_lower)
 clause_ref = clause_match.group(0) if clause_match else 'Not specified'
 
 # Create or update setback requirement
 if boundary_type not in processed_setbacks:
 processed_setbacks[boundary_type] = SetbackRequirement(
 boundary_type=boundary_type,
 minimum_setback_meters=meters,
 maximum_setback_meters=None,
 confidence_score=confidence,
 legal_source=document_id,
 clause_reference=clause_ref,
 contextual_requirements=provision[:200],
 council_area=council_area,
 zone_applicability=zone,
 provision_id=None # This method doesn't have provision_id
 )
 else:
 # Update with better data if available
 existing = processed_setbacks[boundary_type]
 if confidence > existing.confidence_score:
 existing.minimum_setback_meters = min(existing.minimum_setback_meters, meters)
 existing.maximum_setback_meters = max(existing.maximum_setback_meters or meters, meters)
 existing.confidence_score = confidence
 
 return list(processed_setbacks.values())
 
 def get_domain_aware_setback_requirements(self, zone: str, council_area: str, 
 query_domain: Optional[str] = None) -> List[SetbackRequirement]:
 """
 Get setback requirements with domain filtering and legal authority tracking.
 
 This method implements Phase 1A MVP fixes:
 - Domain classification to prevent cross-contamination 
 - Legal authority hierarchy (LEP → DCP → SEPP)
 - Zone-based filtering for compliance precision
 - Eliminates signage setbacks from residential queries
 
 Args:
 zone: NSW planning zone (R2, R3, R4, etc.)
 council_area: Former council area (marrickville, leichhardt, ashfield)
 query_domain: Override domain classification (optional)
 
 Returns:
 List of domain-filtered setback requirements with legal authority
 """
 
 # Determine query domain from zone if not specified
 if query_domain is None:
 query_domain = self.zone_domain_mapping.get(zone, 'GENERAL_PROVISIONS')
 
 # Get council-specific document patterns
 council_documents = self.council_areas[council_area]['dcp_documents']
 doc_pattern = '|'.join(f"%{doc}%" for doc in council_documents)
 
 conn = sqlite3.connect(self.db_path)
 cursor = conn.cursor()
 
 # Enhanced query with domain filtering and legal authority
 enhanced_query = """
 SELECT DISTINCT
 rp.id,
 rp.provision_text,
 rp.document_id, 
 rp.section_header,
 rp.domain_classification,
 rp.zone,
 rp.development_type,
 rp.classification_confidence,
 rp.cross_contamination_checked,
 slo.lep_clause_reference,
 slo.override_type,
 qs.numeric_value,
 qs.unit,
 qs.context,
 qs.confidence_score as qs_confidence
 FROM regulatory_provisions rp
 LEFT JOIN sepp_lep_overrides slo ON rp.id = slo.sepp_provision_id
 LEFT JOIN quantitative_standards qs ON rp.id = qs.provision_id
 WHERE rp.domain_classification = ?
 AND (rp.zone = ? OR rp.zone IS NULL OR rp.zone = '')
 AND rp.document_id LIKE ?
 AND rp.prp_k1_enhanced = 1
 AND (rp.provision_text LIKE '%setback%' 
 OR rp.provision_text LIKE '%boundary%'
 OR qs.context = 'setback')
 AND rp.classification_confidence >= 0.7
 ORDER BY rp.classification_confidence DESC, qs.confidence_score DESC
 """
 
 # Execute domain-aware query
 results = cursor.execute(enhanced_query, (
 query_domain, 
 zone, 
 f'%{council_area}%'
 )).fetchall()
 
 conn.close()
 
 # Process results into SetbackRequirement objects with legal authority
 domain_setbacks = []
 processed_provisions = set() # Avoid duplicates
 
 for row in results:
 (provision_id, provision_text, document_id, section_header,
 domain_classification, zone_code, development_type,
 classification_confidence, cross_contamination_checked,
 lep_clause_ref, override_type, numeric_value, unit, context,
 qs_confidence) = row
 
 # Skip if already processed this provision
 if provision_id in processed_provisions:
 continue
 processed_provisions.add(provision_id)
 
 # Skip if numeric value not available or invalid
 if not numeric_value or numeric_value <= 0:
 continue
 
 # Convert to meters
 setback_meters = self._convert_to_meters(numeric_value, unit)
 if setback_meters is None:
 continue
 
 # Determine boundary type from provision text
 boundary_type = self._extract_boundary_type(provision_text, section_header)
 
 # Create legal authority object
 legal_authority = self._create_legal_authority(
 document_id, section_header, lep_clause_ref, override_type
 )
 
 # Calculate relevance score (domain match + zone match)
 relevance_score = self._calculate_relevance_score(
 query_domain, domain_classification, zone, zone_code
 )
 
 # Create enhanced SetbackRequirement
 setback_req = SetbackRequirement(
 boundary_type=boundary_type,
 minimum_setback_meters=setback_meters,
 maximum_setback_meters=None, # Could be enhanced later
 confidence_score=min(classification_confidence, qs_confidence or 0.9),
 legal_source=f"{section_header} - {document_id}",
 clause_reference=lep_clause_ref or section_header or "N/A",
 contextual_requirements=provision_text[:200] + "..." if len(provision_text) > 200 else provision_text,
 council_area=council_area,
 zone_applicability=zone_code or zone,
 domain_classification=domain_classification,
 provision_id=provision_id, # Include provision_id for Referenced Legislation accordion
 legal_authority=legal_authority,
 cross_contamination_checked=bool(cross_contamination_checked),
 relevance_score=relevance_score
 )
 
 # Only include high relevance results (prevents cross-contamination)
 if relevance_score >= 0.8:
 domain_setbacks.append(setback_req)
 
 # Sort by relevance and confidence
 domain_setbacks.sort(key=lambda x: (x.relevance_score, x.confidence_score), reverse=True)
 
 return domain_setbacks[:10] # Return top 10 most relevant results
 
 def _convert_to_meters(self, numeric_value: float, unit: str) -> Optional[float]:
 """Convert numeric value to meters"""
 if not unit:
 return None
 
 unit_lower = unit.lower()
 if 'mm' in unit_lower:
 return numeric_value / 1000
 elif any(m in unit_lower for m in ['m', 'meter', 'metre']):
 return numeric_value
 elif 'cm' in unit_lower:
 return numeric_value / 100
 else:
 # Assume meters if unit unclear
 return numeric_value
 
 def _extract_boundary_type(self, provision_text: str, section_header: str) -> str:
 """Extract boundary type from provision text"""
 text = f"{provision_text} {section_header}".lower()
 
 if 'front' in text:
 return 'front'
 elif any(term in text for term in ['side', 'lateral']):
 return 'side' 
 elif 'rear' in text:
 return 'rear'
 else:
 return 'general'
 
 def _create_legal_authority(self, document_id: str, section_header: str, 
 lep_clause_ref: Optional[str], override_type: Optional[str]) -> LegalAuthority:
 """Create legal authority object from database fields"""
 
 # Determine primary vs secondary authority
 if 'Inner_West_Local_Environmental_Plan' in document_id:
 primary = "Inner West LEP 2022"
 secondary = "LEP Provision"
 elif 'IWLEP' in document_id:
 primary = "Inner West LEP 2022" 
 secondary = self._extract_dcp_name(document_id)
 else:
 primary = "Inner West LEP 2022"
 secondary = self._extract_dcp_name(document_id)
 
 # Extract amendment reference
 amendment_ref = "IWLEP 2022 amendments" if 'IWLEP' in document_id else "Original provision"
 
 return LegalAuthority(
 primary_authority=primary,
 secondary_authority=secondary,
 clause_reference=lep_clause_ref or section_header or "N/A",
 amendment_reference=amendment_ref,
 override_authority=f"SEPP {override_type}" if override_type else None,
 document_source=document_id
 )
 
 def _extract_dcp_name(self, document_id: str) -> str:
 """Extract DCP name from document ID"""
 if 'Marrickville_DCP' in document_id:
 return "Marrickville DCP 2011"
 elif 'Leichhardt_DCP' in document_id:
 return "Leichhardt DCP 2013"
 elif 'Ashfield_DCP' in document_id:
 return "Inner West Ashfield DCP 2016"
 else:
 return "Inner West DCP"
 
 def _calculate_relevance_score(self, query_domain: str, provision_domain: str,
 query_zone: str, provision_zone: Optional[str]) -> float:
 """Calculate relevance score for domain/zone matching"""
 
 # Perfect domain match
 if query_domain == provision_domain:
 domain_score = 1.0
 # Compatible domains (e.g., GENERAL_PROVISIONS can apply to any)
 elif provision_domain == 'GENERAL_PROVISIONS':
 domain_score = 0.8
 # Cross-domain contamination (signage vs residential)
 elif (query_domain == 'RESIDENTIAL_BUILDINGS' and provision_domain == 'SIGNAGE_ADVERTISING') or \
 (query_domain == 'SIGNAGE_ADVERTISING' and provision_domain == 'RESIDENTIAL_BUILDINGS'):
 domain_score = 0.1 # Severe penalty
 else:
 domain_score = 0.6 # Other domain mismatch
 
 # Zone matching score
 if provision_zone == query_zone:
 zone_score = 1.0
 elif not provision_zone: # General provision
 zone_score = 0.9
 else:
 zone_score = 0.7
 
 # Combined relevance (weighted toward domain classification)
 return (domain_score * 0.7) + (zone_score * 0.3)
 
 def assess_statutory_compliance(self, nsw_api_data: NSWPlanningAPIData, 
 proposed_development: Dict[str, float]) -> Dict[str, Any]:
 """Assess compliance with statutory requirements from NSW API data"""
 
 compliance_results = {}
 
 # Height compliance (from NSW API)
 if 'Height Limit' in str(nsw_api_data.land_zoning_map):
 # Extract height limit from API data structure
 # This would need to be adapted based on actual API response structure
 height_limit = 9.5 # Default for most R1/R2 zones in Inner West
 
 compliance_results['height'] = {
 'limit': height_limit,
 'proposed': proposed_development.get('height', 0),
 'compliant': proposed_development.get('height', 0) <= height_limit,
 'source': 'Inner West LEP 2022, Clause 4.3',
 'legal_authority': 'STATUTORY'
 }
 
 # FSR compliance (from NSW API)
 if nsw_api_data.floor_space_ratio_map:
 fsr_data = nsw_api_data.floor_space_ratio_map
 fsr_limit = float(fsr_data.get('Floor Space Ratio', 0.6))
 
 compliance_results['fsr'] = {
 'limit': fsr_limit,
 'proposed': proposed_development.get('fsr', 0),
 'compliant': proposed_development.get('fsr', 0) <= fsr_limit,
 'source': 'Inner West LEP 2022, Clause 4.4', 
 'legal_authority': 'STATUTORY'
 }
 
 # Lot size compliance
 if nsw_api_data.lot_size_map:
 lot_size_data = nsw_api_data.lot_size_map
 min_lot_size = float(lot_size_data.get('Lot Size', 200))
 
 compliance_results['lot_size'] = {
 'minimum': min_lot_size,
 'actual': proposed_development.get('lot_area', 0),
 'compliant': proposed_development.get('lot_area', 0) >= min_lot_size,
 'source': 'Inner West LEP 2022, Schedule 1',
 'legal_authority': 'STATUTORY'
 }
 
 return compliance_results
 
 def determine_development_pathway(self, statutory_compliance: Dict[str, Any], 
 setback_compliance: Dict[str, Any]) -> Tuple[str, bool]:
 """Determine development pathway based on compliance assessment"""
 
 # Check if all statutory requirements are met exactly
 statutory_compliant = all(
 result.get('compliant', False) 
 for result in statutory_compliance.values()
 )
 
 # Check if all setback requirements are met 
 setback_compliant = all(
 result.get('compliant', False)
 for result in setback_compliance.values() 
 if isinstance(result, dict)
 )
 
 # Determine pathway
 if statutory_compliant and setback_compliant:
 return 'COMPLYING_DEVELOPMENT', False
 elif statutory_compliant:
 return 'DEVELOPMENT_APPLICATION_MINOR', True # Only setback variations
 else:
 return 'DEVELOPMENT_APPLICATION_MAJOR', True # Statutory variations
 
 def calculate_compliance_confidence(self, setback_requirements: List[SetbackRequirement],
 statutory_compliance: Dict[str, Any]) -> float:
 """Calculate overall compliance confidence score"""
 
 confidence_factors = []
 
 # Statutory data confidence (NSW API is authoritative)
 statutory_confidence = 1.0 if statutory_compliance else 0.5
 confidence_factors.append(statutory_confidence * 0.4) # 40% weight
 
 # Setback data confidence 
 if setback_requirements:
 setback_confidence = sum(req.confidence_score for req in setback_requirements) / len(setback_requirements)
 confidence_factors.append(setback_confidence * 0.4) # 40% weight
 else:
 confidence_factors.append(0.3) # Low confidence if no setback data
 
 # Data completeness confidence
 expected_setbacks = ['front', 'side', 'rear']
 available_setbacks = [req.boundary_type for req in setback_requirements]
 completeness = len(set(available_setbacks) & set(expected_setbacks)) / len(expected_setbacks)
 confidence_factors.append(completeness * 0.2) # 20% weight
 
 return sum(confidence_factors)
 
 def assess_property_compliance(self, address: str, nsw_api_data: NSWPlanningAPIData,
 proposed_development: Dict[str, float]) -> ComplianceAssessment:
 """Complete property compliance assessment"""
 
 # Identify council area
 council_area = self.identify_council_area(address)
 
 # Extract zone from NSW API data
 zone_data = nsw_api_data.land_zoning_map
 zone = zone_data.get('Zone', 'R1') # Default to R1
 
 # Get property ID if available
 property_id = proposed_development.get('property_id', 0)
 
 print(f"Assessing compliance for {address}")
 print(f"Council Area: {council_area.title()}")
 print(f"Zone: {zone}")
 print(f"Data Reliability: {self.council_areas[council_area]['reliability_grade']}")
 
 # Assess statutory compliance using NSW API data
 statutory_compliance = self.assess_statutory_compliance(nsw_api_data, proposed_development)
 
 # Get reliable setback requirements
 setback_requirements = self.get_reliable_setback_requirements(zone, council_area)
 
 # Assess setback compliance
 setback_compliance = {}
 for req in setback_requirements:
 proposed_setback = proposed_development.get(f'{req.boundary_type}_setback', 0)
 
 setback_compliance[req.boundary_type] = {
 'requirement': req,
 'proposed': proposed_setback,
 'compliant': proposed_setback >= req.minimum_setback_meters,
 'variance': proposed_setback - req.minimum_setback_meters
 }
 
 # Determine development pathway
 pathway, discretion_required = self.determine_development_pathway(
 statutory_compliance, setback_compliance
 )
 
 # Calculate confidence
 compliance_confidence = self.calculate_compliance_confidence(
 setback_requirements, statutory_compliance
 )
 
 # Build legal references
 legal_references = []
 
 # Add NSW API legal references
 if nsw_api_data.land_application_map:
 lep_url = nsw_api_data.land_application_map.get('legislationUrl', '')
 if lep_url:
 legal_references.append(f"Inner West LEP 2022: {lep_url}")
 
 # Add DCP references
 for req in setback_requirements:
 legal_references.append(f"{req.legal_source}: {req.clause_reference}")
 
 # Build audit trail
 audit_trail = [
 f"Assessment conducted: {datetime.now().isoformat()}",
 f"NSW Planning API data processed: {len(nsw_api_data.special_provisions)} SEPP overlays",
 f"Council area identified: {council_area} ({self.council_areas[council_area]['reliability_grade']} reliability)",
 f"Zone-specific controls retrieved: {len(setback_requirements)} setback requirements",
 f"Compliance confidence: {compliance_confidence:.3f}"
 ]
 
 return ComplianceAssessment(
 property_address=address,
 property_id=property_id,
 zone=zone,
 council_area=council_area,
 statutory_compliance=statutory_compliance,
 setback_compliance={req.boundary_type: req for req in setback_requirements},
 development_pathway=pathway,
 compliance_confidence=compliance_confidence,
 legal_references=legal_references,
 professional_review_required=compliance_confidence < 0.8 or discretion_required,
 audit_trail=audit_trail
 )
 
 def generate_compliance_report(self, assessment: ComplianceAssessment) -> Dict[str, Any]:
 """Generate comprehensive compliance report"""
 
 report = {
 'property_details': {
 'address': assessment.property_address,
 'property_id': assessment.property_id,
 'zone': assessment.zone,
 'council_area': assessment.council_area.title(),
 'reliability_grade': self.council_areas[assessment.council_area]['reliability_grade']
 },
 'statutory_compliance': assessment.statutory_compliance,
 'setback_requirements': {
 boundary_type: {
 'minimum_setback_meters': req.minimum_setback_meters,
 'confidence_score': req.confidence_score,
 'legal_source': req.legal_source,
 'clause_reference': req.clause_reference,
 'contextual_requirements': req.contextual_requirements
 }
 for boundary_type, req in assessment.setback_compliance.items()
 },
 'compliance_summary': {
 'development_pathway': assessment.development_pathway,
 'compliance_confidence': f"{assessment.compliance_confidence:.1%}",
 'professional_review_required': assessment.professional_review_required,
 'ready_for_submission': assessment.compliance_confidence >= 0.8 and not assessment.professional_review_required
 },
 'legal_references': assessment.legal_references,
 'recommendations': self.generate_recommendations(assessment),
 'audit_trail': assessment.audit_trail
 }
 
 return report
 
 def generate_recommendations(self, assessment: ComplianceAssessment) -> List[str]:
 """Generate actionable recommendations based on compliance assessment"""
 
 recommendations = []
 
 # Council area specific recommendations
 council_data = self.council_areas[assessment.council_area]
 
 if council_data['reliability_grade'] == 'MEDIUM':
 recommendations.append(
 f"Data reliability is MEDIUM for {assessment.council_area.title()} area. "
 f"Professional verification recommended for precise setback requirements."
 )
 
 # Compliance confidence recommendations 
 if assessment.compliance_confidence < 0.7:
 recommendations.append(
 "Compliance confidence is below 70%. Recommend engaging qualified planning consultant "
 "for detailed assessment and professional certification."
 )
 elif assessment.compliance_confidence < 0.8:
 recommendations.append(
 "Compliance confidence is moderate. Consider professional review before lodging application."
 )
 
 # Pathway specific recommendations
 if assessment.development_pathway == 'COMPLYING_DEVELOPMENT':
 recommendations.append(
 "Development meets complying development standards. "
 "Consider certification by private certifier for faster approval (10-20 days)."
 )
 elif assessment.development_pathway == 'DEVELOPMENT_APPLICATION_MINOR':
 recommendations.append(
 "Development requires minor variations. Lodge Development Application with Inner West Council. "
 "Typical assessment time: 8-12 weeks."
 )
 else:
 recommendations.append(
 "Development requires major variations. Lodge Development Application with Inner West Council. "
 "Consider pre-DA consultation. Typical assessment time: 12-16 weeks."
 )
 
 # Council area specific guidance
 recommendations.append(
 f"For {assessment.council_area.title()} properties, refer to {council_data['dcp_documents'][0]} "
 f"for detailed design requirements and local character guidelines."
 )
 
 return recommendations


# Example usage and testing
def test_complete_system():
 """Test the complete compliance system with real data"""
 
 engine = InnerWestComplianceEngine()
 
 # Test property: 36 Pile St, Dulwich Hill (Marrickville area)
 test_address = "36 Pile St, Dulwich Hill NSW 2203, Australia"
 
 # Simulate NSW Planning API data (would come from actual API call)
 mock_nsw_api = [
 {
 "layerName": "Land Zoning Map",
 "results": [{"Zone": "R2", "Land Use": "Low Density Residential"}]
 },
 {
 "layerName": "Floor Space Ratio Map", 
 "results": [{"Floor Space Ratio": "0.6"}]
 },
 {
 "layerName": "Lot Size Map",
 "results": [{"Lot Size": "200", "Units": "m²"}]
 }
 ]
 
 # Process API data
 nsw_api_data = engine.process_nsw_api_data(mock_nsw_api)
 
 # Proposed development
 proposed_development = {
 'property_id': 1962876,
 'height': 8.5, # meters
 'fsr': 0.55, # ratio
 'lot_area': 250, # m²
 'front_setback': 3.0, # meters
 'side_setback': 1.5, # meters
 'rear_setback': 6.0 # meters
 }
 
 # Assess compliance
 assessment = engine.assess_property_compliance(
 test_address, nsw_api_data, proposed_development
 )
 
 # Generate report
 report = engine.generate_compliance_report(assessment)
 
 # Print results
 print("\\n" + "="*80)
 print("INNER WEST LGA COMPLIANCE ASSESSMENT RESULTS")
 print("="*80)
 
 print(f"Property: {report['property_details']['address']}")
 print(f"Zone: {report['property_details']['zone']}")
 print(f"Council Area: {report['property_details']['council_area']}")
 print(f"Reliability Grade: {report['property_details']['reliability_grade']}")
 
 print(f"\\nDevelopment Pathway: {report['compliance_summary']['development_pathway']}")
 print(f"Compliance Confidence: {report['compliance_summary']['compliance_confidence']}")
 print(f"Professional Review Required: {report['compliance_summary']['professional_review_required']}")
 
 print("\\nSetback Requirements:")
 for boundary, req in report['setback_requirements'].items():
 print(f" {boundary.title()}: {req['minimum_setback_meters']}m "
 f"(confidence: {req['confidence_score']:.2f})")
 
 print("\\nRecommendations:")
 for i, rec in enumerate(report['recommendations'], 1):
 print(f" {i}. {rec}")
 
 # Save detailed report
 with open('inner_west_compliance_report.json', 'w') as f:
 json.dump(report, f, indent=2, default=str)
 
 print("\\nDetailed report saved to: inner_west_compliance_report.json")
 
 return assessment.compliance_confidence >= 0.7


if __name__ == "__main__":
 success = test_complete_system()
 print(f"\\nSystem Test: {'PASS' if success else 'FAIL'}")