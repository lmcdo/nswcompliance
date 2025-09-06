"""
Universal Regulatory Engine - Query processed data for ANY Inner West property

Replaces hardcoded assumptions with dynamic queries to existing LightRAG/AutoSchemaKG data.
Works for ANY zone (R1/R2/R3/R4/B1/B2/IN1/etc.) and development type.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class RegulatoryFramework:
    """Discovered regulatory framework for a property"""
    applicable_dcp: str
    applicable_sections: List[str]
    development_type: str
    setback_controls: Dict[str, Any]
    confidence_score: float
    discovery_source: str

class UniversalRegulatoryEngine:
    """
    Universal rules engine that works for ANY Inner West property by querying
    existing processed regulatory data instead of hardcoding assumptions.
    """
    
    def __init__(self):
        """Initialize connections to existing processed data sources"""
        self.lightrag = None  # Will connect to existing LightRAG system
        self.autoschemakg = None  # Will connect to existing AutoSchemaKG data
        self._initialize_data_connections()
    
    def _initialize_data_connections(self):
        """Connect to existing processed regulatory data"""
        try:
            # Import existing query system
            from scripts.validated_nsw_query import query_validated_processor
            self.query_processor = query_validated_processor
            logger.info("Connected to existing LightRAG query system")
        except ImportError as e:
            logger.error(f"Failed to connect to LightRAG system: {e}")
            self.query_processor = None
    
    def discover_regulatory_framework(self, property_data) -> RegulatoryFramework:
        """
        Discover applicable regulatory framework for ANY property by querying
        existing processed regulatory data dynamically.
        """
        logger.info(f"Discovering regulatory framework for {property_data.zone} property at {property_data.address}")
        
        # Step 1: Discover applicable DCP from processed documents
        applicable_dcp = self._discover_applicable_dcp(property_data)
        
        # Step 2: Discover applicable sections from processed relationships
        applicable_sections = self._discover_applicable_sections(property_data)
        
        # Step 3: Infer development type from property characteristics  
        development_type = self._infer_development_type(property_data)
        
        # Step 4: Extract setback controls from discovered sections
        setback_controls = self._extract_setback_controls(property_data, applicable_sections)
        
        # Step 5: Calculate confidence based on data availability
        confidence = self._calculate_confidence(property_data, applicable_sections, setback_controls)
        
        framework = RegulatoryFramework(
            applicable_dcp=applicable_dcp,
            applicable_sections=applicable_sections,
            development_type=development_type,
            setback_controls=setback_controls,
            confidence_score=confidence,
            discovery_source="LightRAG/AutoSchemaKG processed data"
        )
        
        logger.info(f"Discovered framework: DCP={applicable_dcp}, Sections={applicable_sections}, Type={development_type}, Confidence={confidence}")
        return framework
    
    def _discover_applicable_dcp(self, property_data) -> str:
        """Query processed data to discover which DCP applies to this property"""
        if not self.query_processor:
            return "Unknown DCP - query system unavailable"
            
        # Query existing processed regulatory data
        query = f"DCP development control plan {property_data.lga} {getattr(property_data, 'suburb', '')} regulatory authority"
        
        try:
            result = self.query_processor(query)
            if result and "ERROR" not in result.upper():
                # Parse DCP name from processed regulatory documents
                dcp_name = self._extract_dcp_name_from_result(result)
                if dcp_name:
                    logger.debug(f"Discovered DCP from processed data: {dcp_name}")
                    return dcp_name
        except Exception as e:
            logger.warning(f"Failed to query for applicable DCP: {e}")
        
        # Fallback to property data if available
        if hasattr(property_data, 'lga_name') and 'INNER WEST' in str(property_data.lga_name):
            return "Inner West DCP (inferred from LGA)"
        
        return "Unknown DCP"
    
    def _discover_applicable_sections(self, property_data) -> List[str]:
        """Query for EXACT authoritative sections using precise governance language from Clause 4.3.3"""
        if not self.query_processor:
            return ["Unknown sections - query system unavailable"]
        
        # Use the EXACT authoritative language from boarding house clause 4.3.3
        # "assessed in accordance with the relevant controls in Section X"
        authority_query = f"{property_data.zone} zone assessed in accordance relevant controls Section"
        
        applicable_sections = []
        
        try:
            result = self.query_processor(authority_query)
            if result and "ERROR" not in result.upper():
                # Extract sections using the exact "assessed in accordance with" pattern
                sections = self._extract_authoritative_sections_only(result, property_data)
                applicable_sections.extend(sections)
                
            # If no results, try broader boarding house clause query
            if not applicable_sections:
                boarding_house_query = f"boarding house {property_data.zone} zone assessed accordance Section"
                result = self.query_processor(boarding_house_query)
                if result:
                    sections = self._extract_authoritative_sections_only(result, property_data)
                    applicable_sections.extend(sections)
                    
        except Exception as e:
            logger.warning(f"Failed to query for authoritative sections: {e}")
        
        # Remove duplicates and return only authoritative sections
        return list(set(applicable_sections)) if applicable_sections else ["Unknown sections"]
    
    def _infer_development_type(self, property_data) -> str:
        """Infer development type from property characteristics using processed examples"""
        if not self.query_processor:
            return "Unknown development type"
        
        # Build characteristics query from property data
        characteristics = []
        if hasattr(property_data, 'land_area') and property_data.land_area:
            area_value = property_data.land_area.split()[0] if isinstance(property_data.land_area, str) else str(property_data.land_area)
            characteristics.append(f"{area_value} square metres")
        
        if hasattr(property_data, 'fsr_limit') and property_data.fsr_limit:
            characteristics.append(f"FSR {property_data.fsr_limit}")
            
        if hasattr(property_data, 'height_limit') and property_data.height_limit:
            characteristics.append(f"height {property_data.height_limit}")
        
        # Query for similar development examples from processed data
        dev_query = f"{property_data.zone} zone development type {' '.join(characteristics)}"
        
        try:
            result = self.query_processor(dev_query)
            if result and "ERROR" not in result.upper():
                # Infer development type from processed examples
                dev_type = self._infer_type_from_result(result, property_data)
                if dev_type:
                    return dev_type
        except Exception as e:
            logger.warning(f"Failed to infer development type: {e}")
        
        # Fallback inference from zone if query fails
        return self._fallback_development_type(property_data)
    
    def _extract_setback_controls(self, property_data, applicable_sections: List[str]) -> Dict[str, Any]:
        """Extract setback values from processed clauses for discovered sections"""
        if not self.query_processor or not applicable_sections:
            return {"error": "No setback controls available"}
        
        setback_controls = {}
        
        for section in applicable_sections:
            if section == "Unknown sections":
                continue
                
            # Query for setback values in this section
            setback_query = f"setback requirements {section} {property_data.zone} metres distance front side rear"
            
            try:
                result = self.query_processor(setback_query)
                if result and "ERROR" not in result.upper():
                    # Extract setback values from processed clauses
                    setbacks = self._extract_setback_values_from_result(result)
                    if setbacks:
                        setback_controls[section] = setbacks
                        
            except Exception as e:
                logger.warning(f"Failed to extract setbacks for section {section}: {e}")
        
        # If no section-specific setbacks found, try general query
        if not setback_controls:
            general_query = f"{property_data.zone} setback requirements metres front side rear"
            try:
                result = self.query_processor(general_query)
                if result:
                    setbacks = self._extract_setback_values_from_result(result)
                    if setbacks:
                        setback_controls["general"] = setbacks
            except Exception as e:
                logger.warning(f"Failed to extract general setbacks: {e}")
        
        return setback_controls if setback_controls else {"error": "No setback controls found"}
    
    def _calculate_confidence(self, property_data, sections: List[str], setback_controls: Dict[str, Any]) -> float:
        """Calculate confidence score based on data availability and quality"""
        confidence = 1.0
        
        # Reduce confidence for missing or unknown data
        if not sections or sections == ["Unknown sections"]:
            confidence *= 0.3
        elif any("unknown" in str(s).lower() for s in sections):
            confidence *= 0.6
            
        if not setback_controls or "error" in setback_controls:
            confidence *= 0.4
        elif not setback_controls or len(setback_controls) == 0:
            confidence *= 0.5
            
        # Reduce confidence for limited property data
        if not hasattr(property_data, 'land_area') or not property_data.land_area:
            confidence *= 0.8
            
        if not hasattr(property_data, 'fsr_limit') or not property_data.fsr_limit:
            confidence *= 0.9
        
        return max(confidence, 0.1)  # Minimum 10% confidence
    
    # Helper methods for parsing query results
    
    def _extract_dcp_name_from_result(self, result: str) -> Optional[str]:
        """Extract DCP name from query result"""
        result_lower = result.lower()
        
        # Look for DCP names in the processed data
        if "marrickville dcp" in result_lower:
            return "Marrickville DCP 2011"
        elif "ashfield dcp" in result_lower:
            return "Ashfield DCP 2016"  
        elif "leichhardt dcp" in result_lower:
            return "Leichhardt DCP"
        elif "inner west" in result_lower and "dcp" in result_lower:
            return "Inner West DCP"
        
        return None
    
    def _extract_authoritative_sections_only(self, result: str, property_data) -> List[str]:
        """Extract ONLY the section that specifically applies to the target zone (prevents cross-contamination)"""
        import re
        
        # Use zone-specific extraction to prevent cross-contamination
        target_zone = property_data.zone
        sections = self._extract_zone_specific_section_only(result, target_zone)
        
        if sections and sections[0] != 'Unknown section':
            logger.debug(f"Zone-specific extraction: {target_zone} → {sections[0]}")
            return sections
        
        # Fallback: try general authoritative pattern (but still filter by zone)
        result_lower = result.lower()
        authoritative_pattern = r'assessed\s+in\s+accordance\s+with.*?section\s+(\d+\.?\d*)'
        matches = re.findall(authoritative_pattern, result_lower)
        
        if matches:
            # Only return the section if it's contextually related to this specific zone
            for section_num in matches:
                section_context_start = max(0, result_lower.find(f"section {section_num}") - 200)
                section_context_end = min(len(result_lower), result_lower.find(f"section {section_num}") + 100)
                context = result_lower[section_context_start:section_context_end]
                
                # Check if this specific zone is mentioned near this section
                if target_zone.lower() in context:
                    logger.debug(f"Context-filtered extraction: {target_zone} → Section {section_num}")
                    return [f"Section {section_num}"]
        
        return ['Unknown section']
    
    def _extract_zone_specific_section_only(self, result: str, target_zone: str) -> List[str]:
        """Extract ONLY the section that specifically applies to the target zone from clause 4.3.3"""
        import re
        
        result_lower = result.lower()
        target_zone_lower = target_zone.lower()
        
        # Pattern: "R2...assessed in accordance with...Section X"
        zone_section_pattern = rf'{target_zone_lower}.*?assessed.*?accordance.*?section\s+(\d+\.?\d*)'
        matches = re.findall(zone_section_pattern, result_lower, re.IGNORECASE | re.DOTALL)
        
        if matches:
            # Return only the first match (the primary section for this zone)
            section_num = matches[0]
            logger.debug(f"Direct zone pattern match: {target_zone} → Section {section_num}")
            return [f"Section {section_num}"]
        
        # Fallback: use the known mappings from clause 4.3.3 if we have the boarding house clause
        if 'boarding house' in result_lower and target_zone_lower in result_lower:
            zone_mappings = {
                'r2': '4.1',   # R2 → Section 4.1
                'r1': '4.2',   # R1 → Section 4.2  
                'r3': '4.2',   # R3 → Section 4.2
                'r4': '4.2',   # R4 → Section 4.2
                'b1': '5',     # B1 → Section 5
                'b2': '5',     # B2 → Section 5
                'b4': '5'      # B4 → Section 5
            }
            
            if target_zone_lower in zone_mappings:
                section_num = zone_mappings[target_zone_lower]
                logger.debug(f"Fallback zone mapping: {target_zone} → Section {section_num}")
                return [f"Section {section_num}"]
        
        return ['Unknown section']
    
    def _extract_governing_sections_only(self, result: str, property_data, dev_type: str) -> List[str]:
        """Extract only sections that have direct regulatory authority over this development type"""
        sections = []
        result_lower = result.lower()
        
        import re
        
        # Look for authoritative regulatory relationships, not just mentions
        # Pattern: "X zone is regulated by Section Y" or "Section Y governs X development"
        governing_patterns = [
            r'section\s+(\d+\.\d+)\s+(?:governs?|regulates?|controls?|applies?\s+to)',
            r'(?:governed|regulated|controlled)\s+by\s+section\s+(\d+\.\d+)',
            r'section\s+(\d+\.\d+)\s+relating\s+to\s+' + dev_type.replace('_', '\s+'),
            r'development.*?assessed.*?section\s+(\d+\.\d+)'
        ]
        
        for pattern in governing_patterns:
            matches = re.findall(pattern, result_lower)
            sections.extend([f"Section {s}" for s in matches])
        
        # NO HARDCODED SECTION NUMBERS - let the data tell us what sections apply
        # Look for any regulatory authority relationships in the result
        # The processed data should contain the actual regulatory mappings
        
        # Extract sections only when there's clear regulatory authority language
        if any(authority_word in result_lower for authority_word in ["governed", "regulated", "controlled", "assessed", "applies to"]):
            # Find any section numbers mentioned in authoritative context
            all_section_patterns = re.findall(r'section\s+(\d+\.\d+)', result_lower)
            
            # Only include if the section is specifically tied to this development type
            for section_num in all_section_patterns:
                section_context_start = max(0, result_lower.find(f"section {section_num}") - 100)
                section_context_end = min(len(result_lower), result_lower.find(f"section {section_num}") + 200)
                context = result_lower[section_context_start:section_context_end]
                
                # Check if this section is specifically for this development type
                if (dev_type.replace('_', ' ') in context or 
                    property_data.zone.lower() in context or
                    any(auth_word in context for auth_word in ["governs", "regulates", "controls", "assessed"])):
                    sections.append(f"Section {section_num}")
            
        return sections

    def _extract_sections_from_result(self, result: str, property_data) -> List[str]:
        """Legacy method - extract any section mentions (less precise)"""
        sections = []
        result_lower = result.lower()
        
        import re
        
        # Pattern for section numbers like "4.1", "4.2", "5.0", etc.
        section_patterns = re.findall(r'section\s+(\d+\.\d+)', result_lower)
        sections.extend([f"Section {s}" for s in section_patterns])
        
        # Look for descriptive section names (but these might not be governing)
        if "low density residential" in result_lower:
            sections.append("Low Density Residential") 
        if "multi dwelling" in result_lower:
            sections.append("Multi Dwelling Housing")
        if "commercial" in result_lower:
            sections.append("Commercial Development")
        if "industrial" in result_lower:
            sections.append("Industrial Development")
        if "heritage" in result_lower:
            sections.append("Heritage Conservation")
            
        return sections
    
    def _infer_type_from_result(self, result: str, property_data) -> Optional[str]:
        """Infer development type from query result"""
        result_lower = result.lower()
        
        # Infer from processed regulatory text
        if "single dwelling" in result_lower or "detached house" in result_lower:
            return "single_dwelling"
        elif "multi dwelling" in result_lower or "townhouse" in result_lower:
            return "multi_dwelling"
        elif "residential flat" in result_lower or "apartment" in result_lower:
            return "residential_flat_building"
        elif "commercial" in result_lower:
            return "commercial"
        elif "industrial" in result_lower:
            return "industrial"
        elif "mixed use" in result_lower:
            return "mixed_use"
            
        return None
    
    def _extract_setback_values_from_result(self, result: str) -> Optional[Dict[str, float]]:
        """Extract setback distances from query result"""
        import re
        
        setbacks = {}
        
        # Look for setback patterns like "front setback 3 metres", "6m setback", etc.
        front_pattern = re.search(r'front.*?setback.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?', result.lower())
        if front_pattern:
            setbacks['front'] = float(front_pattern.group(1))
            
        side_pattern = re.search(r'side.*?setback.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?', result.lower())
        if side_pattern:
            setbacks['side'] = float(side_pattern.group(1))
            
        rear_pattern = re.search(r'rear.*?setback.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?', result.lower())
        if rear_pattern:
            setbacks['rear'] = float(rear_pattern.group(1))
        
        # General setback pattern
        if not setbacks:
            general_pattern = re.findall(r'(\d+(?:\.\d+)?)\s*m(?:etres?)?\s*setback', result.lower())
            if general_pattern:
                # Use first found setback as general setback
                setbacks['general'] = float(general_pattern[0])
        
        return setbacks if setbacks else None
    
    def _fallback_development_type(self, property_data) -> str:
        """Fallback development type inference based on zone"""
        zone = property_data.zone
        
        if zone == 'R2':
            return "low_density_residential"
        elif zone in ['R1', 'R3', 'R4']:
            return "multi_dwelling_residential"
        elif zone.startswith('B'):
            return "commercial"
        elif zone.startswith('IN'):
            return "industrial"
        else:
            return "unknown_development_type"