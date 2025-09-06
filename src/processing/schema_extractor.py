"""
Schema-based extractor for regulatory setback rules
Uses regex patterns to extract structured data from regulatory text chunks
"""

import re
import json
import os
from typing import List, Dict, Optional, Tuple
from ..models import FormerCouncilArea, SetbackRule, SetbackRules

class SchemaExtractor:
    """Extract structured setback rules from regulatory text using regex patterns"""
    
    def __init__(self, schema_path: Optional[str] = None):
        """Initialize with regex patterns for setback extraction"""
        
        # Regex patterns for different setback types
        # Based on common NSW DCP language patterns
        self.patterns = {
            "rear": {
                # "within X metres...must not exceed Y metres"
                "distance_height": r'within\s*(\d+(?:\.\d+)?)\s*m(?:etres?)?.*?(?:must\s*not\s*exceed|maximum.*?height)\s*(\d+(?:\.\d+)?)\s*m(?:etres?)?',
                # "rear setback of X metres"  
                "distance_only": r'rear\s*setback.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
                # "minimum rear setback X metres"
                "minimum": r'minimum\s*rear\s*setback\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*m(?:etres?)?'
            },
            "side": {
                # "side setback...must not exceed X metres height"
                "height_limit": r'side\s*setback.*?(?:must\s*not\s*exceed|maximum.*?height)\s*(\d+(?:\.\d+)?)\s*m(?:etres?)?',
                # "side setback of X metres"
                "distance": r'side\s*setback.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?'
            },
            "front": {
                # "front setback of X metres"
                "distance": r'front\s*setback.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
                # "minimum front setback X metres"
                "minimum": r'minimum\s*front\s*setback\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*m(?:etres?)?'
            }
        }
        
        # DCP version patterns for source attribution
        self.version_patterns = {
            FormerCouncilArea.ASHFIELD: r'Ashfield\s*DCP\s*(?:20)?(\d{2})',
            FormerCouncilArea.LEICHHARDT: r'Leichhardt\s*DCP\s*(?:20)?(\d{2})', 
            FormerCouncilArea.MARRICKVILLE: r'Marrickville\s*DCP\s*(?:20)?(\d{2})'
        }
    
    def extract_setback_rules(self, text_chunks: List[str], area: FormerCouncilArea, source_file: str) -> Dict[str, Optional[SetbackRule]]:
        """
        Extract setback rules from text chunks for a specific council area
        
        Args:
            text_chunks: List of text chunks from RAG processor
            area: Former council area being processed
            source_file: Source file path for attribution
            
        Returns:
            Dictionary with rear, side, front setback rules
        """
        extracted_rules = {
            "rear": None,
            "side": None,
            "front": None
        }
        
        # Combine all chunks for processing
        full_text = ' '.join(text_chunks)
        
        # Extract each type of setback
        for setback_type in ["rear", "side", "front"]:
            rule = self._extract_setback_type(full_text, setback_type, area, source_file)
            if rule:
                extracted_rules[setback_type] = rule
        
        return extracted_rules
    
    def _extract_setback_type(self, text: str, setback_type: str, area: FormerCouncilArea, source_file: str) -> Optional[SetbackRule]:
        """Extract a specific type of setback rule"""
        patterns = self.patterns.get(setback_type, {})
        text_lower = text.lower()
        
        rule_data = {}
        source_context = ""
        
        # Try each pattern for this setback type
        for pattern_name, pattern in patterns.items():
            matches = re.finditer(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                # Extract numerical values
                if pattern_name == "distance_height" and setback_type == "rear":
                    rule_data["distance"] = float(match.group(1))
                    rule_data["height_limit"] = float(match.group(2))
                elif pattern_name in ["distance_only", "distance", "minimum"]:
                    if setback_type == "front":
                        rule_data["min_distance"] = float(match.group(1))
                    else:
                        rule_data["distance"] = float(match.group(1))
                elif pattern_name == "height_limit":
                    rule_data["height_limit"] = float(match.group(1))
                
                # Capture surrounding context for source attribution
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                source_context = text[start:end].strip()
                break
            
            if rule_data:
                break
        
        if not rule_data:
            return None
        
        # Generate source attribution
        source_ref = self._generate_source_reference(source_context, area, source_file)
        
        return SetbackRule(
            **rule_data,
            source=source_ref,
            source_file=os.path.basename(source_file)
        )
    
    def _generate_source_reference(self, context: str, area: FormerCouncilArea, source_file: str) -> str:
        """Generate source reference from context and file information"""
        
        # Try to identify DCP version from filename or context
        filename = os.path.basename(source_file)
        
        # Extract year from filename patterns
        year_match = re.search(r'20(\d{2})', filename)
        year = f"20{year_match.group(1)}" if year_match else "2014"  # Default fallback
        
        # Extract chapter/section from filename
        chapter_match = re.search(r'Chapter\s*([A-H])', filename, re.IGNORECASE)
        part_match = re.search(r'Part\s*([A-G])', filename, re.IGNORECASE)
        section_match = re.search(r'Section\s*(\d+)', filename, re.IGNORECASE)
        
        if chapter_match:
            section_ref = f"Chapter {chapter_match.group(1)}"
        elif part_match:
            section_ref = f"Part {part_match.group(1)}"
            if section_match:
                section_ref += f" Section {section_match.group(1)}"
        else:
            section_ref = "Section X.X"  # Generic fallback
        
        return f"{area.value} DCP {year} {section_ref}"
    
    def calculate_confidence(self, extracted_rules: Dict[str, Optional[SetbackRule]]) -> float:
        """
        Calculate extraction confidence score based on completeness and quality
        
        Args:
            extracted_rules: Dictionary of extracted rules
            
        Returns:
            Confidence score between 0 and 1
        """
        total_possible = 3  # rear, side, front
        extracted_count = sum(1 for rule in extracted_rules.values() if rule is not None)
        
        # Base confidence on extraction completeness
        base_confidence = extracted_count / total_possible
        
        # Boost confidence if we have specific numeric values
        quality_bonus = 0
        for rule in extracted_rules.values():
            if rule:
                has_distance = rule.distance is not None or rule.min_distance is not None
                has_height = rule.height_limit is not None
                
                if has_distance and has_height:
                    quality_bonus += 0.1  # Best case - both values
                elif has_distance or has_height:
                    quality_bonus += 0.05  # Good case - one value
        
        return min(1.0, base_confidence + quality_bonus)