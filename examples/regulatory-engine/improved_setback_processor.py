"""
Improved setback processor using AutoSchemaKG for complete rule extraction
Replaces basic regex patterns with schema-based knowledge graph extraction
Configurable patterns and no hardcoded values
"""
import os
import json
import re
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict
from raganything import RAGAnything
from pydantic import BaseModel, Field
from pathlib import Path


@dataclass
class SetbackCondition:
    """Represents a condition that affects setback requirements"""
    condition_type: str  # "building_height", "lot_width", "adjoining_use", "building_type"
    operator: str  # "greater_than", "less_than", "equal_to", "adjacent_to"
    value: Optional[Union[float, str]] = None
    unit: Optional[str] = None


@dataclass
class SetbackCalculation:
    """Represents how a setback distance is calculated"""
    calculation_type: str  # "fixed", "percentage", "formula", "minimum_of", "maximum_of"
    base_value: Optional[float] = None
    percentage: Optional[float] = None
    formula: Optional[str] = None
    alternatives: Optional[List['SetbackCalculation']] = None
    unit: str = "m"


class SetbackRule(BaseModel):
    """Comprehensive setback rule schema using Pydantic for validation"""
    rule_id: str
    setback_type: str = Field(..., description="front, side, rear")
    distance: Optional[SetbackCalculation] = None
    conditions: List[SetbackCondition] = Field(default_factory=list)
    exceptions: List[str] = Field(default_factory=list)
    zone_applicability: List[str] = Field(default_factory=list)
    building_types: List[str] = Field(default_factory=list)
    source_text: str
    source_reference: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    
    class Config:
        arbitrary_types_allowed = True


class AutoSchemaKGSetbackExtractor:
    """
    Advanced setback extractor using AutoSchemaKG knowledge graph capabilities
    Configurable patterns loaded from external JSON configuration
    """
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50, 
                 patterns_file: Optional[str] = None):
        self.rag = RAGAnything()  # Initialize RAGAnything
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.patterns_file = patterns_file or self._get_default_patterns_file()
        self.patterns_config = self._load_patterns_config()
    
    def _get_default_patterns_file(self) -> str:
        """Get the default patterns file path"""
        current_dir = Path(__file__).parent
        return str(current_dir / "setback_patterns.json")
    
    def _load_patterns_config(self) -> Dict[str, Any]:
        """Load configurable patterns from JSON file"""
        try:
            with open(self.patterns_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Patterns configuration file not found: {self.patterns_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in patterns file {self.patterns_file}: {e}")
    
    def extract_structured_setbacks(self, dcp_text: str, area: str) -> Dict[str, List[SetbackRule]]:
        """
        Extract structured setback rules using AutoSchemaKG knowledge graph
        """
        # Chunk the text for better processing
        chunks = self._chunk_text(dcp_text)
        
        extracted_rules = {
            "side": [],
            "front": [],
            "rear": []
        }
        
        for chunk_idx, chunk in enumerate(chunks):
            # Use AutoSchemaKG for semantic extraction of each setback type
            for setback_type in ["side", "front", "rear"]:
                rules = self._extract_setback_rules_with_autoschemakg(chunk, area, chunk_idx, setback_type)
                extracted_rules[setback_type].extend(rules)
        
        return extracted_rules
    
    def _chunk_text(self, text: str) -> List[str]:
        """
        Simple text chunking implementation
        """
        if not text:
            return []
        
        # Split by sentences and group into chunks
        sentences = text.replace('\n', ' ').split('.')
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # If adding this sentence would exceed chunk size, start a new chunk
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += f". {sentence}" if current_chunk else sentence
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _extract_setback_rules_with_autoschemakg(self, chunk: str, area: str, chunk_idx: int, setback_type: str) -> List[SetbackRule]:
        """
        Use AutoSchemaKG's semantic capabilities to extract complex setback rules
        This goes beyond regex to understand rule semantics and relationships
        """
        try:
            from autoschemakg import AutoSchemaKG
        except ImportError:
            raise ImportError("AutoSchemaKG not installed. Run: pip install git+https://github.com/HKUST-KnowComp/AutoSchemaKG.git")
        
        # Initialize AutoSchemaKG with setback-specific schema
        schema_kg = AutoSchemaKG()
        
        # Define setback rule schema for knowledge graph
        setback_schema = {
            "entities": [
                {"name": "distance", "type": "numerical", "unit": ["m", "metres", "meters"]},
                {"name": "setback_type", "type": "categorical", "values": ["side", "front", "rear"]},
                {"name": "building_type", "type": "categorical", "values": ["dwelling", "house", "commercial", "industrial"]},
                {"name": "condition", "type": "conditional", "relationships": ["when", "if", "unless", "except"]},
                {"name": "calculation", "type": "formula", "operators": ["minimum", "maximum", "times", "percentage"]},
                {"name": "zone", "type": "categorical", "values": ["residential", "commercial", "industrial"]},
                {"name": "use_type", "type": "categorical", "values": ["driveway", "access", "landscaping", "building"]}
            ],
            "relationships": [
                {"name": "applies_to", "source": "setback_rule", "target": "building_type"},
                {"name": "conditional_on", "source": "setback_rule", "target": "condition"},
                {"name": "calculated_as", "source": "distance", "target": "calculation"},
                {"name": "minimum_of", "source": "calculation", "target": "distance"},
                {"name": "maximum_of", "source": "calculation", "target": "distance"},
                {"name": "adjacent_to", "source": "building", "target": "zone"}
            ]
        }
        
        # Extract entities and relationships using AutoSchemaKG
        extracted_knowledge = schema_kg.extract_schema_from_text(
            text=chunk,
            schema=setback_schema,
            domain="planning_regulations"
        )
        
        rules = []
        
        # Process extracted knowledge into structured rules
        for extraction in extracted_knowledge.get("rule_extractions", []):
            # AutoSchemaKG identifies semantic relationships
            if self._is_setback_rule(extraction, setback_type):
                rule = self._create_rule_from_extraction(extraction, area, chunk_idx, chunk)
                if rule:
                    rules.append(rule)
        
        # Fallback to pattern-based extraction if AutoSchemaKG finds nothing
        if not rules:
            rules = self._fallback_pattern_extraction(chunk, area, chunk_idx, setback_type)
        
        return rules
    
    def _is_setback_rule(self, extraction: Dict[str, Any], target_setback_type: str) -> bool:
        """
        Determine if extraction represents a setback rule of the target type
        """
        entities = extraction.get("entities", [])
        
        # Check if we have both setback type and distance
        has_setback_type = any(
            entity.get("type") == "setback_type" and 
            target_setback_type.lower() in entity.get("value", "").lower()
            for entity in entities
        )
        
        has_distance = any(
            entity.get("type") == "distance" and 
            entity.get("numerical_value") is not None
            for entity in entities
        )
        
        return has_setback_type and has_distance
    
    def _create_rule_from_extraction(self, extraction: Dict[str, Any], area: str, 
                                   chunk_idx: int, source_chunk: str) -> Optional[SetbackRule]:
        """
        Create a SetbackRule from AutoSchemaKG extraction
        """
        entities = extraction.get("entities", [])
        relationships = extraction.get("relationships", [])
        
        # Extract basic components
        setback_type = self._find_entity_value(entities, "setback_type")
        distance_entity = self._find_entity(entities, "distance")
        
        if not setback_type or not distance_entity:
            return None
        
        # Build distance calculation
        distance_calc = self._build_distance_calculation(distance_entity, entities, relationships)
        
        # Extract conditions
        conditions = self._extract_conditions(entities, relationships)
        
        # Build rule
        rule = SetbackRule(
            rule_id=f"{area}_{setback_type}_{chunk_idx}_{extraction.get('start_pos', 0)}",
            setback_type=setback_type,
            distance=distance_calc,
            conditions=conditions,
            source_text=extraction.get("matched_text", source_chunk[:100]),
            source_reference=f"{area} DCP 2014 Chunk {chunk_idx}",
            confidence_score=extraction.get("confidence", 0.7)
        )
        
        return rule
    
    def _build_distance_calculation(self, distance_entity: Dict, entities: List[Dict], 
                                  relationships: List[Dict]) -> SetbackCalculation:
        """
        Build SetbackCalculation from extracted entities and relationships
        """
        base_value = distance_entity.get("numerical_value")
        unit = distance_entity.get("unit", "m")
        
        # Check for calculation relationships
        calc_relationships = [
            rel for rel in relationships 
            if rel.get("relationship") in ["calculated_as", "minimum_of", "maximum_of"]
        ]
        
        if calc_relationships:
            # Complex calculation
            calc_type = calc_relationships[0].get("relationship")
            if calc_type == "minimum_of":
                return SetbackCalculation(
                    calculation_type="minimum_of",
                    base_value=base_value,
                    unit=unit
                )
            elif calc_type == "maximum_of":
                return SetbackCalculation(
                    calculation_type="maximum_of", 
                    base_value=base_value,
                    unit=unit
                )
            else:
                # Formula-based calculation
                formula_entity = self._find_entity(entities, "calculation")
                if formula_entity:
                    return SetbackCalculation(
                        calculation_type="formula",
                        formula=formula_entity.get("value"),
                        unit=unit
                    )
        
        # Simple fixed calculation
        return SetbackCalculation(
            calculation_type="fixed",
            base_value=base_value,
            unit=unit
        )
    
    def _extract_conditions(self, entities: List[Dict], relationships: List[Dict]) -> List[SetbackCondition]:
        """
        Extract conditions from AutoSchemaKG analysis
        """
        conditions = []
        
        # Find conditional relationships
        conditional_rels = [
            rel for rel in relationships
            if rel.get("relationship") in ["conditional_on", "applies_to", "adjacent_to"]
        ]
        
        for rel in conditional_rels:
            condition_type = rel.get("relationship")
            target_entity = rel.get("target_entity")
            
            if target_entity:
                condition = SetbackCondition(
                    condition_type=condition_type,
                    operator="equal_to",
                    value=target_entity.get("value")
                )
                conditions.append(condition)
        
        return conditions
    
    def _find_entity(self, entities: List[Dict], entity_type: str) -> Optional[Dict]:
        """Find first entity of specified type"""
        for entity in entities:
            if entity.get("type") == entity_type:
                return entity
        return None
    
    def _find_entity_value(self, entities: List[Dict], entity_type: str) -> Optional[str]:
        """Find value of first entity of specified type"""
        entity = self._find_entity(entities, entity_type)
        return entity.get("value") if entity else None
    
    def _fallback_pattern_extraction(self, chunk: str, area: str, chunk_idx: int, setback_type: str) -> List[SetbackRule]:
        """
        Fallback to pattern-based extraction when AutoSchemaKG doesn't find semantic structures
        """
        patterns_config = self.patterns_config.get("setback_patterns", {}).get(setback_type, {})
        rules = []
        
        for pattern_category, patterns in patterns_config.items():
            for pattern_def in patterns:
                pattern = pattern_def.get("pattern")
                confidence = pattern_def.get("confidence", 0.5)
                extraction_rules = pattern_def.get("extraction_rules", {})
                
                matches = re.finditer(pattern, chunk, re.IGNORECASE)
                for match in matches:
                    rule = self._create_rule_from_pattern_match(
                        match, pattern_def, area, chunk_idx, setback_type, confidence
                    )
                    if rule:
                        rules.append(rule)
        
        return rules
    
    def _create_rule_from_pattern_match(self, match, pattern_def: Dict, area: str, 
                                      chunk_idx: int, setback_type: str, confidence: float) -> Optional[SetbackRule]:
        """
        Create SetbackRule from regex pattern match using extraction rules
        """
        extraction_rules = pattern_def.get("extraction_rules", {})
        groups = match.groupdict()
        
        # Extract distance
        distance_field = extraction_rules.get("distance_field")
        distance = None
        if distance_field and distance_field in groups:
            try:
                distance = float(groups[distance_field])
            except (ValueError, TypeError):
                return None
        
        # Extract unit
        unit_field = extraction_rules.get("unit_field", "unit")
        unit = groups.get(unit_field, "m")
        
        # Build calculation
        calc_type = extraction_rules.get("calculation_type", "fixed")
        distance_calc = SetbackCalculation(
            calculation_type=calc_type,
            base_value=distance,
            unit=unit
        )
        
        # Extract conditions if present
        conditions = []
        condition_field = extraction_rules.get("condition_field")
        condition_type = extraction_rules.get("condition_type")
        if condition_field and condition_type and condition_field in groups:
            conditions.append(SetbackCondition(
                condition_type=condition_type,
                operator="equal_to",
                value=groups[condition_field]
            ))
        
        rule = SetbackRule(
            rule_id=f"{area}_{setback_type}_pattern_{chunk_idx}_{match.start()}",
            setback_type=setback_type,
            distance=distance_calc,
            conditions=conditions,
            source_text=match.group(0),
            source_reference=f"{area} DCP 2014 Chunk {chunk_idx}",
            confidence_score=confidence
        )
        
        return rule
    
    def validate_and_score_rules(self, rules: Dict[str, List[SetbackRule]]) -> Dict[str, List[SetbackRule]]:
        """
        Validate extracted rules and assign confidence scores
        """
        validated_rules = {}
        
        for setback_type, rule_list in rules.items():
            validated_list = []
            for rule in rule_list:
                # Validate rule completeness
                if rule.distance and rule.source_text:
                    # Boost confidence for rules with conditions
                    if rule.conditions:
                        rule.confidence_score = min(rule.confidence_score + 0.1, 1.0)
                    
                    # Reduce confidence for very short source text (likely incomplete)
                    if len(rule.source_text) < 20:
                        rule.confidence_score = max(rule.confidence_score - 0.2, 0.1)
                    
                    validated_list.append(rule)
            
            validated_rules[setback_type] = validated_list
        
        return validated_rules


def extract_setback_rules(area: str, dcp_text: str) -> Dict[str, Any]:
    """
    Main function to extract setback rules using improved AutoSchemaKG approach
    Replaces the simple regex-based extraction in the original file
    """
    extractor = AutoSchemaKGSetbackExtractor()
    
    # Extract structured rules
    raw_rules = extractor.extract_structured_setbacks(dcp_text, area)
    
    # Validate and score rules
    validated_rules = extractor.validate_and_score_rules(raw_rules)
    
    # Convert to serializable format
    serialized_rules = {}
    for setback_type, rules in validated_rules.items():
        serialized_rules[setback_type] = [
            {
                "rule_id": rule.rule_id,
                "distance": asdict(rule.distance) if rule.distance else None,
                "conditions": [asdict(cond) for cond in rule.conditions],
                "exceptions": rule.exceptions,
                "source_text": rule.source_text,
                "source_reference": rule.source_reference,
                "confidence_score": rule.confidence_score
            }
            for rule in rules
        ]
    
    return {
        "area": area,
        "extraction_method": "AutoSchemaKG_v2",
        "rules": serialized_rules,
        "total_rules_extracted": sum(len(rules) for rules in validated_rules.values()),
        "high_confidence_rules": sum(
            1 for rules in validated_rules.values() 
            for rule in rules if rule.confidence_score >= 0.8
        )
    }


def process_inner_west_setbacks_improved():
    """
    Process setback rules for all 3 Inner West DCPs using improved extraction
    """
    areas = ["Ashfield", "Leichhardt", "Marrickville"]
    results = {}
    
    for area in areas:
        # For MVP, use extracted text chunks instead of PDF
        chunks_dir = f"temp_extraction_{area}"
        if not os.path.exists(chunks_dir):
            print(f"Warning: No extracted text found for {area}")
            continue
        
        # Combine all chunks for the area
        dcp_text = ""
        for filename in sorted(os.listdir(chunks_dir)):
            if filename.endswith('.txt'):
                with open(os.path.join(chunks_dir, filename), 'r', encoding='utf-8') as f:
                    dcp_text += f.read() + "\n\n"
        
        if dcp_text.strip():
            # Extract setback rules using improved method
            results[area] = extract_setback_rules(area, dcp_text)
            print(f"✓ Extracted {results[area]['total_rules_extracted']} rules for {area}")
            print(f"  - {results[area]['high_confidence_rules']} high-confidence rules")
        else:
            print(f"No text content found for {area}")
    
    # Save comprehensive results
    output_path = 'public/regulatory-data/inner-west_setbacks_improved.json'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "lga": "INNER WEST COUNCIL",
            "extraction_date": "2025-01-24",
            "extraction_method": "AutoSchemaKG_v2_improved",
            "areas": results,
            "summary": {
                "total_areas": len(results),
                "total_rules": sum(area_data['total_rules_extracted'] for area_data in results.values()),
                "high_confidence_rules": sum(area_data['high_confidence_rules'] for area_data in results.values())
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Improved setback rules processed and saved to {output_path}")
    return results


if __name__ == "__main__":
    # Process Inner West Council's 3 DCPs with improved AutoSchemaKG extraction
    results = process_inner_west_setbacks_improved()
    
    # Display summary
    total_rules = sum(area_data['total_rules_extracted'] for area_data in results.values())
    high_confidence = sum(area_data['high_confidence_rules'] for area_data in results.values())
    
    print(f"\n📊 EXTRACTION SUMMARY:")
    print(f"Total Rules Extracted: {total_rules}")
    print(f"High Confidence Rules: {high_confidence}")
    print(f"Confidence Rate: {high_confidence/total_rules*100:.1f}%" if total_rules > 0 else "N/A")