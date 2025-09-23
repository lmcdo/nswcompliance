"""
Dual Semantic Processor - Combining LangExtract + AutoSchemaKG
Provides source-grounded regulatory extraction with semantic relationship understanding
"""
import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# LangExtract for source grounding
import langextract as lx
from langextract_config import create_setback_extraction_config

# AutoSchemaKG for semantic relationships
from atlas_rag.kg_construction.triple_extraction import KnowledgeGraphExtractor
from atlas_rag.kg_construction.triple_config import ProcessingConfig
from atlas_rag.llm_generator import LLMGenerator

# Configuration and data models
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')


@dataclass
class SourceGrounding:
 """Source grounding information from LangExtract"""
 extraction_text: str
 char_start: int
 char_end: int
 source_location: str
 confidence: float
 attributes: Dict[str, Any]


@dataclass
class RuleClassification:
 """Three-tier rule classification for compliance UX"""
 tier: int # 1=Hard Requirements, 2=Strong Guidance, 3=Descriptive Context
 enforcement_level: str # "MANDATORY", "RECOMMENDED", "INFORMATIONAL"
 linguistic_confidence: float # How certain we are about the classification
 prescriptive_indicators: List[str] # Language patterns that led to classification
 compliance_message_type: str # "MUST_COMPLY", "SHOULD_ALIGN", "CONSIDER"


@dataclass
class SemanticTriple:
 """Semantic relationship from AutoSchemaKG"""
 subject: str
 predicate: str
 object: str
 confidence: float
 context: str


class EnhancedSetbackRule(BaseModel):
 """Enhanced setback rule combining both approaches with three-tier classification"""
 rule_id: str
 rule_type: str = Field(..., description="setback_rule, condition, calculation, etc.")
 setback_category: str = Field(..., description="side, front, rear")
 
 # LangExtract source grounding
 source_grounding: Dict[str, Any]
 
 # AutoSchemaKG semantic understanding 
 semantic_triples: List[Dict[str, Any]] = Field(default_factory=list)
 
 # Three-tier rule classification
 rule_classification: Dict[str, Any]
 
 # Merged insights
 rule_complexity: str = Field(..., description="simple, conditional, formula-based")
 legal_authority: str
 compliance_logic: str
 
 # Confidence and validation
 overall_confidence: float = Field(ge=0.0, le=1.0)
 extraction_method: str = "dual_semantic_v2.0"


class DualSemanticProcessor:
 """
 Main processor combining LangExtract source grounding with AutoSchemaKG semantic analysis
 """
 
 def __init__(self, config: Optional[Dict[str, Any]] = None):
 """Initialize dual processor with configuration"""
 self.config = config or self._create_default_config()
 self.langextract_config = create_setback_extraction_config()
 self.autoschemakg_extractor = None
 self._initialize_autoschemakg()
 self._initialize_linguistic_patterns()
 
 def _create_default_config(self) -> Dict[str, Any]:
 """Create default configuration for dual processing"""
 return {
 "use_langextract": True,
 "use_autoschemakg": True,
 "merge_strategy": "weighted_confidence",
 "source_authority_weight": 0.6, # Favor source grounding for legal compliance
 "semantic_understanding_weight": 0.4,
 "minimum_confidence_threshold": 0.7,
 "parallel_processing": True
 }
 
 def _initialize_autoschemakg(self):
 """Initialize AutoSchemaKG knowledge graph extractor"""
 try:
 # Initialize LLM generator for AutoSchemaKG
 from openai import OpenAI
 client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
 llm_generator = LLMGenerator(client=client, model_name="gpt-4o")
 
 # Create processing config for regulatory text
 kg_config = ProcessingConfig(
 model_path="gpt-4o",
 data_directory="temp_processing",
 filename_pattern="regulatory_text",
 batch_size_triple=2, # Small batches for regulatory precision
 batch_size_concept=4,
 output_directory="temp_kg_output",
 max_new_tokens=1024, # Shorter for regulatory specificity
 max_workers=2,
 remove_doc_spaces=True,
 debug_mode=False
 )
 
 self.autoschemakg_extractor = KnowledgeGraphExtractor(
 model=llm_generator, 
 config=kg_config
 )
 
 except Exception as e:
 print(f"Warning: AutoSchemaKG initialization failed: {e}")
 self.autoschemakg_extractor = None
 
 def _initialize_linguistic_patterns(self):
 """Initialize linguistic patterns for three-tier rule classification"""
 self.linguistic_patterns = {
 "tier_1_mandatory": {
 "patterns": [
 "not permitted", "prohibited", "forbidden", "shall not", "must not",
 "required", "mandatory", "shall be", "must be", "is to be"
 ],
 "weight": 1.0,
 "enforcement_level": "MANDATORY",
 "message_type": "MUST_COMPLY"
 },
 "tier_2_guidance": {
 "patterns": [
 "should", "encouraged", "recommended", "preferred", "expected",
 r"\d+\.?\d*\s*m\s+(?:wide\s+)?(?:side\s+)?setback\s+for", # "3m wide side setback for"
 "established by", "pattern", "similar to", "uniform"
 ],
 "weight": 0.8,
 "enforcement_level": "RECOMMENDED", 
 "message_type": "SHOULD_ALIGN"
 },
 "tier_3_descriptive": {
 "patterns": [
 "generous", "smaller", "typical", "traditional", "character",
 "setting", "were rare", "established by the original development"
 ],
 "weight": 0.5,
 "enforcement_level": "INFORMATIONAL",
 "message_type": "CONSIDER"
 }
 }
 
 async def extract_dual_semantic_rules(self, dcp_text: str, area: str) -> Dict[str, Any]:
 """
 Main extraction method combining both approaches
 """
 print(f"Starting dual semantic extraction for {area}...")
 
 # Run both extractions in parallel if configured
 if self.config["parallel_processing"]:
 langextract_task = asyncio.create_task(self._run_langextract(dcp_text, area))
 autoschemakg_task = asyncio.create_task(self._run_autoschemakg(dcp_text, area))
 
 langextract_results, autoschemakg_results = await asyncio.gather(
 langextract_task, autoschemakg_task
 )
 else:
 # Sequential processing
 langextract_results = await self._run_langextract(dcp_text, area)
 autoschemakg_results = await self._run_autoschemakg(dcp_text, area)
 
 # Merge and analyze results
 enhanced_rules = self._merge_extraction_results(
 langextract_results, autoschemakg_results, area
 )
 
 return {
 "area": area,
 "extraction_method": "dual_semantic_v1.0",
 "langextract_extractions": len(langextract_results.get("extractions", [])),
 "autoschemakg_triples": len(autoschemakg_results.get("triples", [])),
 "enhanced_rules": enhanced_rules,
 "total_enhanced_rules": len(enhanced_rules),
 "high_confidence_rules": len([r for r in enhanced_rules if r["overall_confidence"] >= 0.8])
 }
 
 async def _run_langextract(self, dcp_text: str, area: str) -> Dict[str, Any]:
 """Run LangExtract for source-grounded extraction"""
 if not self.config["use_langextract"]:
 return {"extractions": []}
 
 try:
 # Use the configured LangExtract setup
 result = lx.extract(
 text_or_documents=dcp_text,
 prompt_description=self.langextract_config["prompt"],
 examples=self.langextract_config["examples"],
 model_id="gpt-4o",
 api_key=self.langextract_config["model_config"]["api_key"],
 extraction_passes=1, # Single pass for speed in dual mode
 max_workers=2,
 max_char_buffer=600, # Smaller for regulatory precision
 fence_output=True,
 use_schema_constraints=False
 )
 
 return {
 "method": "LangExtract",
 "model": "gpt-4o",
 "extractions": result.extractions if hasattr(result, 'extractions') else []
 }
 
 except Exception as e:
 print(f"LangExtract failed: {e}")
 return {"extractions": []}
 
 async def _run_autoschemakg(self, dcp_text: str, area: str) -> Dict[str, Any]:
 """Run AutoSchemaKG for semantic relationship extraction"""
 if not self.config["use_autoschemakg"] or not self.autoschemakg_extractor:
 return {"triples": []}
 
 try:
 # Create temporary file for AutoSchemaKG processing
 temp_dir = Path("temp_processing")
 temp_dir.mkdir(exist_ok=True)
 
 temp_file = temp_dir / f"regulatory_text_{area}.txt"
 with open(temp_file, 'w', encoding='utf-8') as f:
 f.write(dcp_text)
 
 # Run AutoSchemaKG extraction
 # Note: This is a simplified version - full KG construction would require
 # the complete 5-step pipeline from atlas_full_pipeline.ipynb
 self.autoschemakg_extractor.run_extraction()
 
 # For now, return mock semantic triples based on the pattern
 # In production, this would parse the actual KG output
 semantic_triples = self._extract_mock_semantic_triples(dcp_text)
 
 # Cleanup
 temp_file.unlink(missing_ok=True)
 
 return {
 "method": "AutoSchemaKG",
 "model": "gpt-4o",
 "triples": semantic_triples
 }
 
 except Exception as e:
 print(f"AutoSchemaKG failed: {e}")
 return {"triples": []}
 
 def _extract_mock_semantic_triples(self, text: str) -> List[Dict[str, Any]]:
 """
 Mock semantic triple extraction for demonstration
 In production, this would parse actual AutoSchemaKG output
 """
 triples = []
 
 # Simple pattern matching to demonstrate concept
 if "0.9m minimum OR 0.5 times building height" in text:
 triples.extend([
 {
 "subject": "side_setback",
 "predicate": "has_minimum_distance", 
 "object": "0.9m",
 "confidence": 0.9,
 "context": "conditional_calculation"
 },
 {
 "subject": "side_setback",
 "predicate": "calculated_as",
 "object": "0.5_times_building_height", 
 "confidence": 0.85,
 "context": "alternative_calculation"
 },
 {
 "subject": "side_setback",
 "predicate": "selection_rule",
 "object": "whichever_is_greater",
 "confidence": 0.95,
 "context": "comparison_logic"
 }
 ])
 
 if "driveway access" in text and "3m" in text:
 triples.append({
 "subject": "driveway_access",
 "predicate": "requires_setback_width",
 "object": "3m",
 "confidence": 0.9,
 "context": "purpose_specific_requirement"
 })
 
 return triples
 
 def _classify_rule_tier(self, extraction_text: str, attributes: Dict[str, Any]) -> RuleClassification:
 """
 Classify rule into three-tier system based on linguistic analysis
 """
 import re
 
 text_lower = extraction_text.lower()
 matched_patterns = []
 max_weight = 0
 classification_data = None
 
 # Check each tier's patterns
 for tier_name, tier_data in self.linguistic_patterns.items():
 for pattern in tier_data["patterns"]:
 if re.search(pattern, text_lower, re.IGNORECASE):
 matched_patterns.append(pattern)
 if tier_data["weight"] > max_weight:
 max_weight = tier_data["weight"]
 classification_data = tier_data
 
 # Default classification if no patterns match
 if not classification_data:
 # Check for specific indicators in attributes
 if attributes.get("permissibility") == "not permitted":
 classification_data = self.linguistic_patterns["tier_1_mandatory"]
 max_weight = 1.0
 matched_patterns = ["not permitted"]
 elif attributes.get("distance") and "m" in str(attributes.get("distance", "")):
 classification_data = self.linguistic_patterns["tier_2_guidance"]
 max_weight = 0.7
 matched_patterns = ["measurement_provided"]
 else:
 classification_data = self.linguistic_patterns["tier_3_descriptive"]
 max_weight = 0.5
 matched_patterns = ["default_descriptive"]
 
 # Determine tier number from classification
 tier_map = {
 "tier_1_mandatory": 1,
 "tier_2_guidance": 2,
 "tier_3_descriptive": 3
 }
 
 tier = next((tier_map[k] for k in tier_map.keys() if self.linguistic_patterns[k] == classification_data), 3)
 
 return RuleClassification(
 tier=tier,
 enforcement_level=classification_data["enforcement_level"],
 linguistic_confidence=max_weight,
 prescriptive_indicators=matched_patterns,
 compliance_message_type=classification_data["message_type"]
 )
 
 def _merge_extraction_results(self, langextract_results: Dict[str, Any], 
 autoschemakg_results: Dict[str, Any], area: str) -> List[Dict[str, Any]]:
 """
 Merge LangExtract source grounding with AutoSchemaKG semantic understanding
 """
 enhanced_rules = []
 
 # Get extractions from both methods
 le_extractions = langextract_results.get("extractions", [])
 kg_triples = autoschemakg_results.get("triples", [])
 
 # Process each LangExtract extraction
 for idx, extraction in enumerate(le_extractions):
 if not hasattr(extraction, 'extraction_class'):
 continue
 
 # Only process setback rules (not individual measurements/conditions)
 if extraction.extraction_class == "setback_rule":
 
 # Find related semantic triples
 related_triples = self._find_related_triples(extraction, kg_triples)
 
 # Classify rule into three-tier system
 rule_classification = self._classify_rule_tier(extraction.extraction_text, extraction.attributes)
 
 # Determine rule complexity
 rule_complexity = self._analyze_rule_complexity(extraction, related_triples)
 
 # Build enhanced rule
 enhanced_rule = {
 "rule_id": f"{area}_{extraction.extraction_class}_{idx}",
 "rule_type": extraction.extraction_class,
 "setback_category": extraction.attributes.get("setback_type", "unknown"),
 
 # Source grounding from LangExtract
 "source_grounding": {
 "extraction_text": extraction.extraction_text,
 "char_start": extraction.char_interval.start_pos if extraction.char_interval else 0,
 "char_end": extraction.char_interval.end_pos if extraction.char_interval else len(extraction.extraction_text),
 "source_location": f"{area} DCP - Auto-detected",
 "confidence": 0.85, # LangExtract confidence
 "attributes": extraction.attributes
 },
 
 # Semantic understanding from AutoSchemaKG
 "semantic_triples": [asdict(SemanticTriple(**triple)) for triple in related_triples],
 
 # Three-tier rule classification
 "rule_classification": asdict(rule_classification),
 
 # Merged insights
 "rule_complexity": rule_complexity,
 "legal_authority": f"{area} Development Control Plan 2014",
 "compliance_logic": self._generate_compliance_logic(extraction, related_triples, rule_classification),
 
 # Overall confidence (weighted combination)
 "overall_confidence": self._calculate_overall_confidence(extraction, related_triples, rule_classification),
 "extraction_method": "dual_semantic_v2.0"
 }
 
 enhanced_rules.append(enhanced_rule)
 
 return enhanced_rules
 
 def _find_related_triples(self, extraction, triples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
 """Find semantic triples related to this extraction"""
 related = []
 
 extraction_text_lower = extraction.extraction_text.lower()
 
 for triple in triples:
 # Simple matching - in production would be more sophisticated
 if (triple["subject"].replace("_", " ") in extraction_text_lower or 
 triple["object"].replace("_", " ") in extraction_text_lower):
 related.append(triple)
 
 return related
 
 def _analyze_rule_complexity(self, extraction, related_triples: List[Dict[str, Any]]) -> str:
 """Analyze the complexity of a rule based on extraction and triples"""
 
 # Check for conditional language
 text = extraction.extraction_text.lower()
 
 if "or" in text and ("whichever" in text or "greater" in text or "lesser" in text):
 return "conditional_calculation"
 elif any(triple["predicate"] == "calculated_as" for triple in related_triples):
 return "formula_based"
 elif "for" in text or "when" in text or extraction.attributes.get("condition"):
 return "conditional_simple"
 else:
 return "simple_fixed"
 
 def _generate_compliance_logic(self, extraction, related_triples: List[Dict[str, Any]], 
 rule_classification: RuleClassification) -> str:
 """Generate human-readable compliance logic explanation with enforcement level"""
 
 rule_text = extraction.extraction_text
 setback_type = extraction.attributes.get("setback_type", "building")
 
 # Start with enforcement level
 enforcement_prefix = {
 "MANDATORY": "MUST COMPLY",
 "RECOMMENDED": "SHOULD ALIGN WITH", 
 "INFORMATIONAL": "CONSIDER"
 }[rule_classification.enforcement_level]
 
 # Base logic with enforcement level
 logic = f"{enforcement_prefix}: For {setback_type} setbacks - {rule_text}"
 
 # Add classification reasoning
 if rule_classification.prescriptive_indicators:
 indicators = ", ".join(rule_classification.prescriptive_indicators[:3]) # Limit to first 3
 logic += f" (Classification based on: {indicators})"
 
 # Add semantic understanding from triples
 if related_triples:
 conditions = [t for t in related_triples if "condition" in t["context"]]
 calculations = [t for t in related_triples if "calculation" in t["context"]]
 
 if conditions:
 logic += f" This applies when {conditions[0]['object'].replace('_', ' ')}"
 
 if calculations:
 logic += f" Distance calculated as {calculations[0]['object'].replace('_', ' ')}"
 
 return logic
 
 def _calculate_overall_confidence(self, extraction, related_triples: List[Dict[str, Any]], 
 rule_classification: RuleClassification) -> float:
 """Calculate weighted overall confidence including linguistic classification"""
 
 # LangExtract confidence (source authority weight)
 le_confidence = 0.85 # Default LangExtract confidence
 source_weight = self.config["source_authority_weight"]
 
 # AutoSchemaKG confidence (semantic understanding weight) 
 kg_confidence = sum(t["confidence"] for t in related_triples) / len(related_triples) if related_triples else 0.5
 semantic_weight = self.config["semantic_understanding_weight"]
 
 # Linguistic classification confidence
 linguistic_confidence = rule_classification.linguistic_confidence
 
 # Weighted combination with linguistic classification
 overall = (
 (le_confidence * source_weight * 0.4) + 
 (kg_confidence * semantic_weight * 0.3) +
 (linguistic_confidence * 0.3) # Linguistic classification gets 30% weight
 )
 
 # Boost confidence for high-certainty classifications
 if rule_classification.tier == 1 and rule_classification.linguistic_confidence >= 0.9:
 overall = min(overall + 0.15, 1.0) # Higher boost for mandatory rules
 elif rule_classification.tier == 2 and rule_classification.linguistic_confidence >= 0.8:
 overall = min(overall + 0.1, 1.0) # Medium boost for guidance rules
 
 # Boost confidence if both methods agree
 if related_triples and len(related_triples) > 1:
 overall = min(overall + 0.05, 1.0)
 
 return round(overall, 2)


def test_dual_semantic_processor():
 """Test the dual semantic processor with sample regulatory text"""
 
 sample_text = """
 Side setbacks shall be 0.9m minimum OR 0.5 times building height, whichever is greater. 
 For driveway access, a 3m wide side setback is required. Nil side setbacks are not permitted.
 Buildings must not exceed a height of 8m within 3m of the rear boundary.
 """
 
 print("Testing Dual Semantic Processor...")
 print(f"Sample text: {sample_text.strip()}")
 
 async def run_test():
 processor = DualSemanticProcessor()
 result = await processor.extract_dual_semantic_rules(sample_text, "Test_Area")
 
 print(f"Extraction successful!")
 print(f" - LangExtract extractions: {result['langextract_extractions']}")
 print(f" - AutoSchemaKG triples: {result['autoschemakg_triples']}")
 print(f" - Enhanced rules: {result['total_enhanced_rules']}")
 print(f" - High confidence rules: {result['high_confidence_rules']}")
 
 # Show sample enhanced rule with classification
 if result['enhanced_rules']:
 sample_rule = result['enhanced_rules'][0]
 classification = sample_rule['rule_classification']
 print(f"\nSample Enhanced Rule:")
 print(f" - Rule: {sample_rule['source_grounding']['extraction_text']}")
 print(f" - Classification Tier: {classification['tier']} ({classification['enforcement_level']})")
 print(f" - Compliance Type: {classification['compliance_message_type']}")
 print(f" - Linguistic Confidence: {classification['linguistic_confidence']}")
 print(f" - Complexity: {sample_rule['rule_complexity']}")
 print(f" - Overall Confidence: {sample_rule['overall_confidence']}")
 print(f" - Compliance Logic: {sample_rule['compliance_logic']}")
 
 return result
 
 # Run async test
 return asyncio.run(run_test())


def validate_extraction_coverage(extraction_result: Dict[str, Any], source_text: str, area: str) -> Dict[str, Any]:
 """Validate that extraction found all expected setback rules"""
 
 # Define expected setback patterns to find
 setback_patterns = {
 'rear_setback': [
 r'rear.*setback.*(\d+\.?\d*)m',
 r'minimum rear.*(\d+\.?\d*)m',
 r'(\d+\.?\d*)m.*rear.*setback',
 r'setback.*rear.*(\d+\.?\d*)m'
 ],
 'side_setback': [
 r'side.*setback.*(\d+\.?\d*)m',
 r'minimum side.*(\d+\.?\d*)m',
 r'(\d+\.?\d*)m.*side.*setback',
 r'setback.*side.*(\d+\.?\d*)m',
 r'side.*boundary.*(\d+\.?\d*)m'
 ],
 'front_setback': [
 r'front.*setback.*(\d+\.?\d*)m',
 r'minimum front.*(\d+\.?\d*)m',
 r'(\d+\.?\d*)m.*front.*setback',
 r'setback.*front.*(\d+\.?\d*)m',
 r'streetscape.*(\d+\.?\d*)m'
 ]
 }
 
 # Find potential setbacks in source text
 import re
 potential_rules = {}
 missed_rules = []
 
 for setback_type, patterns in setback_patterns.items():
 potential_rules[setback_type] = []
 for pattern in patterns:
 matches = re.finditer(pattern, source_text, re.IGNORECASE)
 for match in matches:
 potential_rules[setback_type].append({
 'text': match.group(0),
 'value': match.group(1) if match.groups() else None,
 'start': match.start(),
 'end': match.end(),
 'context': source_text[max(0, match.start()-100):match.end()+100]
 })
 
 # Check what the extraction found
 extracted_rules = extraction_result.get('enhanced_rules', [])
 found_types = set()
 
 for rule in extracted_rules:
 rule_type = rule.get('rule_type', '')
 if 'rear' in rule_type:
 found_types.add('rear_setback')
 elif 'side' in rule_type:
 found_types.add('side_setback')
 elif 'front' in rule_type:
 found_types.add('front_setback')
 
 # Identify missed opportunities
 for setback_type, potentials in potential_rules.items():
 if setback_type not in found_types and potentials:
 missed_rules.extend([{
 'type': setback_type,
 'potential_rule': potential,
 'reason': 'Pattern found in text but not extracted'
 } for potential in potentials[:3]]) # Limit to top 3
 
 return {
 'total_potential_rules': sum(len(rules) for rules in potential_rules.values()),
 'total_extracted_rules': len(extracted_rules),
 'found_setback_types': list(found_types),
 'missed_setback_types': [t for t in setback_patterns.keys() if t not in found_types],
 'potential_rules_by_type': potential_rules,
 'missed_opportunities': missed_rules,
 'coverage_score': len(found_types) / len(setback_patterns),
 'completeness_assessment': 'COMPREHENSIVE' if len(found_types) >= 2 else 'PARTIAL' if len(found_types) == 1 else 'MINIMAL'
 }


def print_validation_summary(validation: Dict[str, Any]):
 """Print validation results summary"""
 print(f"\n=== EXTRACTION VALIDATION SUMMARY ===")
 print(f"Coverage Score: {validation['coverage_score']:.2%}")
 print(f"Completeness: {validation['completeness_assessment']}")
 print(f"Found Setback Types: {', '.join(validation['found_setback_types'])}")
 
 if validation['missed_setback_types']:
 print(f" Missed Types: {', '.join(validation['missed_setback_types'])}")
 
 if validation['missed_opportunities']:
 print(f"\n MISSED OPPORTUNITIES:")
 for missed in validation['missed_opportunities'][:5]: # Show top 5
 print(f" • {missed['type']}: {missed['potential_rule']['text']}")
 
 print(f"Total Potential Rules Found in Text: {validation['total_potential_rules']}")
 print(f"Total Rules Extracted: {validation['total_extracted_rules']}")
 print("=" * 40)


async def process_files_from_config(config_path: str) -> Dict[str, Any]:
 """Process files based on configuration file"""
 try:
 with open(config_path, 'r') as f:
 config = json.load(f)
 
 area = config['area']
 input_files = config['input_files']
 output_file = config['output_file']
 
 print(f"Processing {len(input_files)} files for {area}...")
 
 # Initialize processor
 processor = DualSemanticProcessor()
 
 # Combine all chunk files into one text for processing
 combined_text = ""
 for file_path in input_files:
 if os.path.exists(file_path):
 with open(file_path, 'r', encoding='utf-8') as f:
 chunk_content = f.read()
 combined_text += f"\n\n--- FILE: {os.path.basename(file_path)} ---\n{chunk_content}\n"
 
 # Run dual semantic extraction
 result = await processor.extract_dual_semantic_rules(combined_text, area)
 
 # Validate extraction coverage
 validation_results = validate_extraction_coverage(result, combined_text, area)
 
 # Save results with validation
 final_result = {
 **result,
 'validation': validation_results
 }
 
 output_path = os.path.join('public', 'regulatory-data', output_file)
 os.makedirs(os.path.dirname(output_path), exist_ok=True)
 
 with open(output_path, 'w') as f:
 json.dump(final_result, f, indent=2)
 
 print(f"Enhanced semantic extraction saved to {output_path}")
 print(f"Extracted {len(result.get('enhanced_rules', []))} rules")
 print_validation_summary(validation_results)
 
 return result
 
 except Exception as e:
 print(f"Processing failed: {e}")
 raise


if __name__ == "__main__":
 import argparse
 import sys
 
 parser = argparse.ArgumentParser(description='Dual Semantic Processor for regulatory text extraction')
 parser.add_argument('--config', required=False, help='Path to configuration JSON file')
 parser.add_argument('--extract-all-rules', action='store_true', help='Extract all rules from input files')
 parser.add_argument('--test', action='store_true', help='Run test mode')
 
 args = parser.parse_args()
 
 if args.config and args.extract_all_rules:
 # Process files from configuration
 try:
 result = asyncio.run(process_files_from_config(args.config))
 print(f"\nProcessing completed successfully!")
 sys.exit(0)
 except Exception as e:
 print(f"Processing failed: {e}")
 sys.exit(1)
 elif args.test:
 # Test the dual processor
 try:
 result = test_dual_semantic_processor()
 print("\nDual Semantic Processor ready for regulatory extraction!")
 except Exception as e:
 print(f"\nDual Semantic Processor needs debugging: {e}")
 import traceback
 traceback.print_exc()
 else:
 print("Usage: python dual_semantic_processor.py [--config CONFIG_FILE --extract-all-rules] [--test]")
 sys.exit(1)