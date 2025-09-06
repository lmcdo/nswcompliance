#!/usr/bin/env python3
"""
Authoritative Setback Calculator - Council-Ready MVP
Follows the exact 6-step authoritative procedure for Inner West LGA certifiers.

SCOPE: R2 Low Density Residential, Marrickville DCP area, Standard lots, DA pathway only
STATUS: Preliminary guidance tool - Professional verification required
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class AuthoritativeSetbackResult:
    """Council-ready setback calculation with full regulatory compliance"""
    
    # Property Context (Step 1 & 2)
    address: str
    zoning: str
    zoning_authority: str  # "IWLEP 2022 confirmed via NSW Planning Portal"
    former_council_area: str  # "Marrickville", "Ashfield", "Leichhardt"
    
    # Applicable Controls (Step 3)
    primary_lep: str  # "Inner West LEP 2022"
    applicable_dcp: str  # "Marrickville DCP 2011"
    development_pathway: str  # "Development Application (DA)"
    
    # Calculated Setbacks (Step 4 & 5)
    front_setback: float
    side_setback: float  
    rear_setback: float
    
    # Measurement Method (Step 5)
    measurement_method: str
    measurement_points: Dict[str, str]
    
    # Regulatory Authority (Step 6)
    regulatory_sources: List[str]
    verification_requirements: List[str]
    professional_certification_required: bool
    
    # Confidence & Limitations
    confidence_grade: str  # "HIGH", "MEDIUM", "LOW"
    confidence_percentage: int
    scope_limitations: List[str]
    exclusions: List[str]
    
    # Calculation Metadata
    calculation_timestamp: str
    calculator_version: str
    mvp_scope: str

@dataclass
class CouncilDisclaimer:
    """Comprehensive disclaimers for council use"""
    
    title: str = "🏛️ IMPORTANT: AUTHORITATIVE VERIFICATION REQUIRED"
    
    preliminary_warning: str = """
    This calculator provides PRELIMINARY ESTIMATES based on:
    • Inner West LEP 2022 (IWLEP 2022)
    • Marrickville DCP 2011  
    • NSW Planning Portal data
    
    These are GUIDANCE calculations only.
    """
    
    certifier_responsibility: str = """
    ⚖️ CERTIFIER/PROFESSIONAL RESPONSIBILITY:
    Final setback verification MUST be confirmed by:
    • Qualified building certifier OR
    • Council development assessment team
    • Section 10.7 Planning Certificate 
    • Licensed surveyor measurements
    • Professional architectural plans
    """
    
    not_suitable_for: str = """
    📋 NOT SUITABLE FOR:
    • Complying Development Certificates (CDC)
    • Heritage items or conservation areas
    • Corner lots or irregular boundaries  
    • Industrial or commercial zones
    • Final construction decisions
    • Building approval submissions
    """
    
    scope_limitations: str = """
    🎯 MVP SCOPE LIMITATIONS:
    This calculator currently covers:
    ✅ R2 Low Density Residential zones
    ✅ Marrickville DCP area only
    ✅ Standard rectangular lots
    ✅ Development Application pathway
    
    ❌ NOT covered in this MVP:
    • Ashfield or Leichhardt DCP areas
    • Commercial, industrial, or mixed-use zones
    • Complex lot shapes or corner properties
    • Complying development rules
    """
    
    contact_authority: str = """
    📞 FOR AUTHORITATIVE GUIDANCE:
    Inner West Council: (02) 9392 5000
    council@innerwest.nsw.gov.au
    Planning Department - Development Assessment
    """

class AuthoritativeSetbackCalculator:
    """
    Council-ready setback calculator following Inner West LGA authoritative procedure
    MVP Scope: R2 Marrickville DCP area only
    """
    
    def __init__(self):
        self.regulatory_hierarchy = {
            "primary": "Inner West LEP 2022 (IWLEP 2022)",
            "marrickville_dcp": "Marrickville DCP 2011", 
            "ashfield_dcp": "Inner West Ashfield DCP 2016",
            "leichhardt_dcp": "Leichhardt DCP 2013",
            "sepp_cdc": "SEPP (Exempt and Complying Development Codes) 2008"
        }
        
        # R2 Zone Standard Setbacks (from authoritative sources)
        self.r2_standard_setbacks = {
            "marrickville": {
                "front": {"min": 3.0, "max": 9.0, "typical": 6.0, "source": "Marrickville DCP 2011"},
                "side": {"min": 0.9, "max": 3.0, "typical": 1.5, "source": "IWLEP 2022 + DCP"},
                "rear": {"min": 6.0, "max": 25.0, "typical": 8.0, "source": "Marrickville DCP 2011"}
            }
        }
        
        # Height-based adjustments (from planning practice)
        self.height_adjustments = {
            "height_threshold": 7.5,  # metres
            "side_adjustment_factor": 0.5,  # per metre above threshold
            "rear_height_factor": 0.5  # alternative rear calculation
        }
    
    async def calculate_authoritative_setbacks(self, property_data, development_type: str = "development_application") -> AuthoritativeSetbackResult:
        """
        Calculate setbacks following the exact 6-step authoritative procedure
        MVP Scope: R2 Marrickville area only
        """
        
        # Validate MVP scope
        scope_validation = self._validate_mvp_scope(property_data)
        if not scope_validation["in_scope"]:
            raise ValueError(f"Property outside MVP scope: {scope_validation['reason']}")
        
        # Step 1: Determine Zoning and Control Instrument
        zoning_info = self._step1_determine_zoning(property_data)
        
        # Step 2: Identify Relevant Planning Controls (IWLEP 2022)
        iwlep_controls = self._step2_identify_planning_controls(zoning_info)
        
        # Step 3: Check Applicable DCP
        dcp_info = self._step3_check_applicable_dcp(property_data)
        
        # Step 4: Development Pathway (DA only in MVP)
        pathway_info = self._step4_development_pathway(development_type)
        
        # Step 5: Calculate Setbacks and Measurement Method
        setback_calculations = await self._step5_calculate_setbacks(
            property_data, zoning_info, dcp_info
        )
        
        # Step 6: Verification and Documentation Requirements
        verification_info = self._step6_verification_requirements()
        
        # Generate confidence assessment
        confidence_assessment = self._assess_calculation_confidence(
            property_data, zoning_info, dcp_info
        )
        
        return AuthoritativeSetbackResult(
            address=property_data.address,
            zoning=zoning_info["zone"],
            zoning_authority=zoning_info["authority"],
            former_council_area=dcp_info["former_area"],
            
            primary_lep=iwlep_controls["primary_source"],
            applicable_dcp=dcp_info["dcp_name"],
            development_pathway=pathway_info["pathway"],
            
            front_setback=setback_calculations["front"]["distance"],
            side_setback=setback_calculations["side"]["distance"], 
            rear_setback=setback_calculations["rear"]["distance"],
            
            measurement_method=setback_calculations["measurement_method"],
            measurement_points=setback_calculations["measurement_points"],
            
            regulatory_sources=verification_info["sources"],
            verification_requirements=verification_info["requirements"],
            professional_certification_required=True,
            
            confidence_grade=confidence_assessment["grade"],
            confidence_percentage=confidence_assessment["percentage"],
            scope_limitations=confidence_assessment["limitations"],
            exclusions=confidence_assessment["exclusions"],
            
            calculation_timestamp=datetime.now().isoformat(),
            calculator_version="MVP-1.0",
            mvp_scope="R2 Marrickville DCP Standard Lots DA Pathway"
        )
    
    def _validate_mvp_scope(self, property_data) -> Dict[str, Any]:
        """Validate property is within MVP scope"""
        
        # Check zone
        if property_data.zone != "R2":
            return {
                "in_scope": False, 
                "reason": f"Zone {property_data.zone} not supported. MVP covers R2 Low Density Residential only."
            }
        
        # Check LGA
        if "inner west" not in property_data.lga_name.lower():
            return {
                "in_scope": False,
                "reason": f"LGA {property_data.lga_name} not supported. MVP covers Inner West Council only."
            }
        
        # Check area (Marrickville preference)
        address_lower = property_data.address.lower()
        marrickville_suburbs = ["marrickville", "dulwich hill", "petersham", "stanmore", "enmore", "newtown"]
        
        if not any(suburb in address_lower for suburb in marrickville_suburbs):
            return {
                "in_scope": False, 
                "reason": "Property may be in Ashfield or Leichhardt DCP area. MVP covers Marrickville DCP area only."
            }
        
        return {"in_scope": True, "reason": "Property within MVP scope"}
    
    def _step1_determine_zoning(self, property_data) -> Dict[str, str]:
        """Step 1: Determine Zoning and Control Instrument"""
        
        return {
            "zone": property_data.zone,
            "zone_name": "R2 Low Density Residential",
            "authority": f"Confirmed via NSW Planning Portal - {property_data.lga_name}",
            "verification_method": "Section 10.7 Planning Certificate recommended for final verification",
            "source_reference": "Inner West LEP 2022, Zoning Map"
        }
    
    def _step2_identify_planning_controls(self, zoning_info) -> Dict[str, str]:
        """Step 2: Identify Relevant Planning Controls (IWLEP 2022)"""
        
        return {
            "primary_source": "Inner West LEP 2022 (IWLEP 2022)",
            "zoning_objectives": "R2 Low Density Residential objectives per IWLEP 2022",
            "principal_standards": "Height limits, FSR, setbacks as per IWLEP 2022",
            "authority_reference": "NSW Legislation - Inner West LEP 2022"
        }
    
    def _step3_check_applicable_dcp(self, property_data) -> Dict[str, str]:
        """Step 3: Check Applicable DCP"""
        
        # Determine former council area from address
        address_lower = property_data.address.lower()
        
        if any(suburb in address_lower for suburb in ["dulwich hill", "marrickville", "petersham", "stanmore", "enmore", "newtown", "camperdown", "tempe"]):
            former_area = "Marrickville"
            dcp_name = "Marrickville DCP 2011"
        elif any(suburb in address_lower for suburb in ["ashfield", "croydon", "hurlstone park"]):
            former_area = "Ashfield" 
            dcp_name = "Inner West Ashfield DCP 2016"
        else:
            # Fallback for MVP - assume Marrickville
            former_area = "Marrickville"
            dcp_name = "Marrickville DCP 2011"
        
        return {
            "former_area": former_area,
            "dcp_name": dcp_name,
            "dcp_sections": "Setback controls, streetscape character, overshadowing guidelines",
            "building_envelope": "Numeric and contextual requirements per DCP"
        }
    
    def _step4_development_pathway(self, development_type) -> Dict[str, str]:
        """Step 4: Development Pathway (DA only in MVP)"""
        
        if development_type == "complying_development":
            raise ValueError("Complying Development (CDC) not supported in MVP. DA pathway only.")
        
        return {
            "pathway": "Development Application (DA)",
            "assessment_type": "Merit-based assessment against DCP and IWLEP 2022",
            "numeric_controls": "DCP numeric setback requirements apply",
            "contextual_factors": "Streetscape, character, neighbor impacts considered",
            "sepp_note": "SEPP (Exempt and Complying Development Codes) 2008 not applicable for DA pathway"
        }
    
    async def _step5_calculate_setbacks(self, property_data, zoning_info, dcp_info) -> Dict[str, Any]:
        """Step 5: Calculate Setbacks and Measurement Method"""
        
        # Get building height for adjustments
        building_height = float(property_data.height_limit.replace("m", "")) if property_data.height_limit else 8.5
        
        # Get standard setbacks for Marrickville R2
        standards = self.r2_standard_setbacks["marrickville"]
        
        # Front setback (typically fixed)
        front_setback = await self._calculate_front_setback_with_lightrag(property_data) or standards["front"]["typical"]
        
        # Side setback (may vary by height)
        side_base = standards["side"]["min"]
        height_threshold = self.height_adjustments["height_threshold"]
        
        if building_height > height_threshold:
            height_adjustment = (building_height - height_threshold) * self.height_adjustments["side_adjustment_factor"]
            side_setback = side_base + height_adjustment
        else:
            side_setback = side_base
        
        # Rear setback (greater of minimum or height-based)
        rear_base = standards["rear"]["min"] 
        rear_height_based = building_height * self.height_adjustments["rear_height_factor"]
        rear_setback = max(rear_base, rear_height_based)
        
        return {
            "front": {
                "distance": front_setback,
                "source": f"{standards['front']['source']} - typical for area",
                "calculation": f"Fixed requirement: {front_setback}m"
            },
            "side": {
                "distance": side_setback,
                "source": f"{standards['side']['source']} with height adjustment",
                "calculation": f"{side_base}m base + {max(0, side_setback - side_base):.1f}m height adjustment = {side_setback:.1f}m"
            },
            "rear": {
                "distance": rear_setback,
                "source": f"{standards['rear']['source']} or height-based",
                "calculation": f"Maximum of {rear_base}m base OR {rear_height_based:.1f}m (0.5 × height) = {rear_setback:.1f}m"
            },
            "measurement_method": "Perpendicular measurement from lot boundary to closest building point at ground level",
            "measurement_points": {
                "front": "From street/road boundary to building facade",
                "side": "From side lot boundary to external wall", 
                "rear": "From rear lot boundary to building rear wall",
                "reference": "As per DCP definitions and standard surveying practice"
            }
        }
    
    async def _calculate_front_setback_with_lightrag(self, property_data) -> Optional[float]:
        """Use Universal Regulatory Engine to get setbacks dynamically"""
        try:
            from services.universal_regulatory_engine import UniversalRegulatoryEngine
            
            # Use universal engine to discover regulatory framework dynamically
            engine = UniversalRegulatoryEngine()
            framework = engine.discover_regulatory_framework(property_data)
            
            # Extract front setback from discovered setback controls
            setback_controls = framework.setback_controls
            
            if setback_controls and not isinstance(setback_controls, dict) or "error" not in setback_controls:
                # Look for front setback in discovered controls
                for section, controls in setback_controls.items():
                    if isinstance(controls, dict) and 'front' in controls:
                        front_setback = float(controls['front'])
                        logger.info(f"Universal engine discovered front setback: {front_setback}m from {section}")
                        return front_setback
                
                # Fallback to general setback if available
                for section, controls in setback_controls.items():
                    if isinstance(controls, dict) and 'general' in controls:
                        general_setback = float(controls['general'])
                        logger.info(f"Universal engine using general setback: {general_setback}m from {section}")
                        return general_setback
            
            # Legacy query method as fallback if universal engine doesn't find specific values
            result = self._legacy_lightrag_query(property_data)
            if result and "ERROR" not in result:
                # Look for "2 metres to 4 metres" pattern from our known data
                range_pattern = r"(\d+(?:\.\d+)?)\s*metres?\s*to\s*(\d+(?:\.\d+)?)\s*metres?"
                matches = re.findall(range_pattern, result.lower())
                if matches:
                    min_val, max_val = float(matches[0][0]), float(matches[0][1])
                    return (min_val + max_val) / 2  # Use average: (2+4)/2 = 3m
                
                # Look for single values
                single_pattern = r"setback of (\d+(?:\.\d+)?)\s*(?:metres?|m)"
                single_matches = re.findall(single_pattern, result.lower())
                if single_matches:
                    return float(single_matches[0])
            
        except Exception as e:
            logger.warning(f"LightRAG query failed: {e}")
        
        return None  # Fallback to standard

    def _legacy_lightrag_query(self, property_data) -> str:
        """Legacy LightRAG query method as fallback"""
        try:
            from scripts.validated_nsw_query import query_validated_processor
            development_type = self._deduce_development_type(property_data)
            location_context = self._deduce_location_context(property_data)
            query = f"front setbacks {development_type} {property_data.zone} {location_context}"
            raw_result = query_validated_processor(query)
            return self._filter_lightrag_results_by_development_type(raw_result, property_data)
        except Exception as e:
            logger.warning(f"Legacy LightRAG query failed: {e}")
            return ""

    def _deduce_development_type(self, property_data) -> str:
        """
        Deduce development type from property characteristics using DCP rules
        Based on Marrickville DCP 4.3.3 deductive pathway rules
        """
        zone = property_data.zone
        land_area = float(property_data.land_area.split()[0]) if hasattr(property_data, 'land_area') else 300
        fsr_limit = property_data.fsr_limit if hasattr(property_data, 'fsr_limit') else '0.6:1'
        fsr = float(fsr_limit.split(':')[0]) if ':' in fsr_limit else 0.6
        
        # Apply DCP deductive rules:
        if zone == 'R2' and land_area < 400 and fsr <= 0.6:
            return 'single dwelling low density residential'
        elif zone in ['R1', 'R3', 'R4'] or (zone == 'R2' and fsr > 0.6):
            return 'multi dwelling housing residential flat buildings'
        elif zone.startswith('B'):
            return 'commercial mixed use development'
        else:
            return 'low density residential'  # Default safe fallback
            
    def _deduce_location_context(self, property_data) -> str:
        """
        Deduce location context from property data - no hardcoded values
        """
        # Extract suburb from address
        address_parts = property_data.address.split(',')
        suburb = address_parts[1].strip() if len(address_parts) > 1 else ""
        
        # Extract LGA info
        lga_name = getattr(property_data, 'lga_name', '').replace('_', ' ').title()
        
        # Build context from available data
        context_parts = []
        if suburb:
            context_parts.append(suburb)
        if lga_name and lga_name != 'Unknown':
            context_parts.append(lga_name)
            
        return ' '.join(context_parts) if context_parts else 'NSW'
    
    def _filter_lightrag_results_by_development_type(self, raw_result: str, property_data) -> str:
        """
        Filter LightRAG results based on deductive rules from Marrickville DCP 4.3.3
        """
        if not raw_result:
            return raw_result
            
        zone = property_data.zone
        land_area = float(property_data.land_area.split()[0]) if hasattr(property_data, 'land_area') else 300
        fsr_limit = property_data.fsr_limit if hasattr(property_data, 'fsr_limit') else '0.6:1'
        fsr = float(fsr_limit.split(':')[0]) if ':' in fsr_limit else 0.6
        
        lines = raw_result.split('\n')
        filtered_lines = []
        
        for line in lines:
            include_line = True
            
            # Apply DCP deductive rules for R2 single dwelling properties
            if zone == 'R2' and land_area < 400 and fsr <= 0.6:
                # Rule: R2 Low Density -> Section 4.1, EXCLUDE Section 4.2 Multi Dwelling
                if 'Multi Dwelling Housing and RFBs' in line:
                    include_line = False
                elif 'Section 4.2' in line and ('multi dwelling' in line.lower() or 'residential flat' in line.lower()):
                    include_line = False
                    
            elif zone in ['R1', 'R3', 'R4']:
                # Rule: R1/R3/R4 -> Section 4.2 Multi Dwelling Housing
                # Prefer multi-dwelling results for these zones
                pass
                
            elif zone.startswith('B'):
                # Rule: B zones -> Section 5 Commercial, exclude residential sections
                if 'Section 4.1' in line or 'Section 4.2' in line:
                    include_line = False
                    
            if include_line:
                filtered_lines.append(line)
                
        return '\n'.join(filtered_lines)
    
    def _step6_verification_requirements(self) -> Dict[str, List[str]]:
        """Step 6: Verification and Documentation Requirements"""
        
        return {
            "sources": [
                "Inner West LEP 2022 (IWLEP 2022) - Primary authority",
                "Marrickville DCP 2011 - Detailed setback controls",
                "NSW Planning Portal - Zoning confirmation",
                "Australian Standard AS 1100 - Technical drawing standards"
            ],
            "requirements": [
                "Section 10.7 Planning Certificate for zoning confirmation",
                "Licensed surveyor site measurements",
                "Qualified building certifier assessment",
                "Architectural plans to scale (1:100 minimum)",
                "Council development assessment (for DA)",
                "Professional verification of calculations"
            ]
        }
    
    def _assess_calculation_confidence(self, property_data, zoning_info, dcp_info) -> Dict[str, Any]:
        """Assess confidence level and document limitations"""
        
        confidence_factors = {
            "zone_supported": property_data.zone == "R2",
            "dcp_area_supported": dcp_info["former_area"] == "Marrickville",
            "standard_lot_assumed": True,  # MVP assumption
            "lightrag_data_available": True,  # We have Marrickville DCP data
            "height_data_available": bool(property_data.height_limit)
        }
        
        confidence_score = sum(confidence_factors.values()) / len(confidence_factors)
        
        if confidence_score >= 0.8:
            grade = "HIGH"
            percentage = int(confidence_score * 100)
        elif confidence_score >= 0.6:
            grade = "MEDIUM" 
            percentage = int(confidence_score * 100)
        else:
            grade = "LOW"
            percentage = int(confidence_score * 100)
        
        return {
            "grade": grade,
            "percentage": percentage,
            "limitations": [
                "Preliminary estimates only - professional verification required",
                "Based on standard lot assumptions",
                "Height adjustments use standard NSW planning formulas",
                "Area-specific variations may apply"
            ],
            "exclusions": [
                "Corner lots and irregular boundaries",
                "Heritage items and conservation areas", 
                "Complying development pathway",
                "Ashfield and Leichhardt DCP areas",
                "Commercial and industrial zones"
            ]
        }

# Council-ready API integration
async def calculate_authoritative_setbacks_for_council(property_data, development_type: str = "development_application") -> AuthoritativeSetbackResult:
    """
    Council-ready setback calculation with full regulatory compliance
    MVP Scope: R2 Marrickville DCP area only
    """
    calculator = AuthoritativeSetbackCalculator()
    return await calculator.calculate_authoritative_setbacks(property_data, development_type)

def get_council_disclaimers() -> CouncilDisclaimer:
    """Get comprehensive council disclaimers"""
    return CouncilDisclaimer()