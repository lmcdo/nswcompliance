#!/usr/bin/env python3
"""
Unified Document Processor - Orchestrates LangExtract + AutoSchemaKG + LightRAG
Processes all documents in /docs/ folder for complete semantic understanding
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
from datetime import datetime

# LangExtract for source grounding
import langextract as lx

# AutoSchemaKG for semantic relationships
from atlas_rag.kg_construction.triple_extraction import KnowledgeGraphExtractor
from atlas_rag.kg_construction.triple_config import ProcessingConfig
from atlas_rag.llm_generator import LLMGenerator

# LightRAG for multimodal processing
from lightrag import LightRAG, QueryParam
from lightrag.llm import gpt_4o_mini_complete

# Import existing components - create inline since files may not exist yet
# from examples.regulatory_engine.langextract_config import create_setback_extraction_config
# from examples.regulatory_engine.dual_semantic_processor import (
#     SourceGrounding, 
#     RuleClassification,
#     EnhancedSetbackRule
# )

# Define classes inline for now
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
    tier: int  # 1=Hard Requirements, 2=Strong Guidance, 3=Descriptive Context
    enforcement_level: str  # "MANDATORY", "RECOMMENDED", "INFORMATIONAL"
    linguistic_confidence: float  # How certain we are about the classification
    prescriptive_indicators: List[str]  # Language patterns that led to classification
    compliance_message_type: str  # "MUST_COMPLY", "SHOULD_ALIGN", "CONSIDER"

@dataclass
class EnhancedSetbackRule:
    """Enhanced setback rule with complete semantic grounding"""
    rule_id: str
    rule_text: str
    rule_type: str
    measurements: List[Dict[str, Any]]
    rule_classification: RuleClassification
    source_grounding: SourceGrounding
    semantic_triples: List[Tuple]
    visual_context: Dict[str, Any]
    overall_confidence: float
    rule_complexity: str

def create_setback_extraction_config():
    """Create LangExtract configuration for setback extraction"""
    return {
        'extraction_type': 'setback_rules',
        'fields': ['setback', 'boundary', 'distance', 'height'],
        'confidence_threshold': 0.8
    }

# Configuration
from dotenv import load_dotenv
load_dotenv('.env.local')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class UnifiedExtractionResult:
    """Combined output from all three semantic processors"""
    area: str
    document_path: str
    
    # LangExtract outputs
    source_groundings: List[SourceGrounding]
    
    # AutoSchemaKG outputs  
    knowledge_triples: List[Tuple[str, str, str]]
    concept_hierarchy: Dict[str, List[str]]
    
    # LightRAG outputs
    multimodal_context: Dict[str, Any]  # Tables, diagrams, maps
    graph_relationships: List[Dict[str, Any]]
    
    # Combined semantic rules
    enhanced_rules: List[EnhancedSetbackRule]
    
    # Metadata
    processing_metadata: Dict[str, Any]


class UnifiedDocumentProcessor:
    """Orchestrates all three semantic processors for complete document understanding"""
    
    def __init__(self):
        self.setup_processors()
        self.docs_path = Path("docs")
        self.output_path = Path("public/regulatory-data/unified")
        self.output_path.mkdir(parents=True, exist_ok=True)
        
    def setup_processors(self):
        """Initialize all three semantic processors"""
        
        # 1. Setup LangExtract
        logger.info("Initializing LangExtract...")
        self.langextract_config = create_setback_extraction_config()
        
        # 2. Setup AutoSchemaKG
        logger.info("Initializing AutoSchemaKG...")
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.kg_generator = LLMGenerator(client=client, model_name="gpt-4o-mini")
        
        self.kg_config = ProcessingConfig(
            model_path="gpt-4o-mini",
            data_directory="temp_extraction",
            filename_pattern="chunk_*.txt",
            batch_size_triple=8,
            batch_size_concept=16,
            output_directory="temp_kg_output",
            max_new_tokens=2048,
            max_workers=3,
            remove_doc_spaces=True
        )
        
        # 3. Setup LightRAG
        logger.info("Initializing LightRAG...")
        self.lightrag = LightRAG(
            working_dir="./lightrag_storage",
            llm_model_func=gpt_4o_mini_complete,
            embed_model="text-embedding-3-small"
        )
        
    async def process_all_documents(self):
        """Process all documents in /docs/ folder"""
        
        results = {}
        
        # Process DCPs
        dcp_path = self.docs_path / "dcps" / "INNERWEST"
        for area in ["Ashfield", "Leichhardt", "Marrickville"]:
            logger.info(f"Processing {area} documents...")
            area_results = await self.process_area_documents(area, dcp_path)
            results[area] = area_results
            
        # Process LEP
        lep_path = self.docs_path / "lep"
        logger.info("Processing LEP documents...")
        lep_results = await self.process_lep_documents(lep_path)
        results["LEP"] = lep_results
        
        # Process SEPPs
        sepp_path = self.docs_path / "sepps"
        logger.info("Processing SEPP documents...")
        sepp_results = await self.process_sepp_documents(sepp_path)
        results["SEPPs"] = sepp_results
        
        # Save unified results
        self.save_unified_results(results)
        
        return results
    
    async def process_area_documents(self, area: str, base_path: Path) -> UnifiedExtractionResult:
        """Process all documents for a specific council area"""
        
        # Find area-specific PDFs
        area_path = base_path / area.lower() if area != "Ashfield" else base_path
        pdf_files = list(area_path.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDFs found for {area}")
            return None
            
        logger.info(f"Found {len(pdf_files)} PDFs for {area}")
        
        # Process each PDF through all three pipelines
        all_extractions = []
        
        for pdf_file in pdf_files:
            extraction = await self.process_single_document(pdf_file, area)
            all_extractions.append(extraction)
            
        # Merge extractions for the area
        unified_result = self.merge_area_extractions(area, all_extractions)
        
        return unified_result
    
    async def process_single_document(self, pdf_path: Path, area: str) -> UnifiedExtractionResult:
        """Process a single PDF through all three semantic processors"""
        
        logger.info(f"Processing {pdf_path.name}...")
        
        # 1. LangExtract - Source grounding
        source_groundings = await self.extract_source_groundings(pdf_path)
        
        # 2. AutoSchemaKG - Knowledge graph
        knowledge_triples, concepts = await self.extract_knowledge_graph(pdf_path)
        
        # 3. LightRAG - Multimodal processing
        multimodal_context = await self.extract_multimodal_context(pdf_path)
        
        # 4. Combine all three outputs
        enhanced_rules = self.combine_semantic_outputs(
            source_groundings,
            knowledge_triples,
            multimodal_context,
            area
        )
        
        return UnifiedExtractionResult(
            area=area,
            document_path=str(pdf_path),
            source_groundings=source_groundings,
            knowledge_triples=knowledge_triples,
            concept_hierarchy=concepts,
            multimodal_context=multimodal_context,
            graph_relationships=self.extract_graph_relationships(multimodal_context),
            enhanced_rules=enhanced_rules,
            processing_metadata={
                'timestamp': datetime.now().isoformat(),
                'processors_used': ['LangExtract', 'AutoSchemaKG', 'LightRAG'],
                'document_name': pdf_path.name,
                'file_size': pdf_path.stat().st_size
            }
        )
    
    async def extract_source_groundings(self, pdf_path: Path) -> List[SourceGrounding]:
        """Use LangExtract to get source-grounded text with citations"""
        
        try:
            # Read PDF content
            with open(pdf_path, 'rb') as f:
                pdf_content = f.read()
            
            # Extract with LangExtract
            extractions = lx.extract(
                pdf_content,
                config=self.langextract_config,
                return_sources=True
            )
            
            # Convert to SourceGrounding objects
            groundings = []
            for extraction in extractions:
                grounding = SourceGrounding(
                    extraction_text=extraction['text'],
                    char_start=extraction.get('char_start', 0),
                    char_end=extraction.get('char_end', 0),
                    source_location=f"Page {extraction.get('page', 'Unknown')}",
                    confidence=extraction.get('confidence', 0.8),
                    attributes=extraction.get('attributes', {})
                )
                groundings.append(grounding)
                
            logger.info(f"Extracted {len(groundings)} source groundings from {pdf_path.name}")
            return groundings
            
        except Exception as e:
            logger.error(f"LangExtract failed for {pdf_path.name}: {e}")
            return []
    
    async def extract_knowledge_graph(self, pdf_path: Path) -> Tuple[List, Dict]:
        """Use AutoSchemaKG to extract knowledge triples"""
        
        try:
            # Check if text chunks exist
            area_name = pdf_path.parent.name
            chunk_dir = Path(f"temp_extraction_{area_name}")
            
            if not chunk_dir.exists():
                logger.warning(f"No text chunks found for {area_name}, skipping KG extraction")
                return [], {}
            
            # Run AutoSchemaKG extraction
            kg_extractor = KnowledgeGraphExtractor(
                model=self.kg_generator,
                config=self.kg_config
            )
            
            # Extract triples
            kg_extractor.run_extraction()
            
            # Convert to triples list
            triples = []
            with open(f"temp_kg_output/kg_extraction/triples.json", 'r') as f:
                kg_data = json.load(f)
                for triple in kg_data.get('triples', []):
                    triples.append((
                        triple['subject'],
                        triple['predicate'],
                        triple['object']
                    ))
            
            # Extract concepts
            concepts = kg_data.get('concepts', {})
            
            logger.info(f"Extracted {len(triples)} knowledge triples from {pdf_path.name}")
            return triples, concepts
            
        except Exception as e:
            logger.error(f"AutoSchemaKG failed for {pdf_path.name}: {e}")
            return [], {}
    
    async def extract_multimodal_context(self, pdf_path: Path) -> Dict[str, Any]:
        """Use LightRAG to process multimodal content"""
        
        try:
            # Insert document into LightRAG
            with open(pdf_path, 'rb') as f:
                await self.lightrag.ainsert(f.read())
            
            # Query for different types of content
            queries = [
                "What tables are present in this document?",
                "What diagrams or maps show spatial requirements?",
                "What are the setback requirements with visual references?",
                "What zoning maps or overlays are shown?"
            ]
            
            multimodal_context = {}
            
            for query in queries:
                response = await self.lightrag.aquery(
                    query,
                    param=QueryParam(mode="hybrid", only_need_context=False)
                )
                
                # Parse response for specific content types
                if "table" in query.lower():
                    multimodal_context['tables'] = self.parse_table_content(response)
                elif "diagram" in query.lower() or "map" in query.lower():
                    multimodal_context['visual_elements'] = self.parse_visual_content(response)
                elif "setback" in query.lower():
                    multimodal_context['setback_visuals'] = response
                elif "zoning" in query.lower():
                    multimodal_context['zoning_maps'] = response
            
            logger.info(f"Extracted multimodal context from {pdf_path.name}")
            return multimodal_context
            
        except Exception as e:
            logger.error(f"LightRAG failed for {pdf_path.name}: {e}")
            return {}
    
    def combine_semantic_outputs(
        self,
        source_groundings: List[SourceGrounding],
        knowledge_triples: List[Tuple],
        multimodal_context: Dict[str, Any],
        area: str
    ) -> List[EnhancedSetbackRule]:
        """Combine outputs from all three processors into enhanced rules"""
        
        enhanced_rules = []
        
        # Group related information
        for grounding in source_groundings:
            # Find related triples
            related_triples = self.find_related_triples(
                grounding.extraction_text,
                knowledge_triples
            )
            
            # Find related visual context
            related_visuals = self.find_related_visuals(
                grounding.extraction_text,
                multimodal_context
            )
            
            # Create enhanced rule if this is a setback rule
            if self.is_setback_rule(grounding.extraction_text):
                rule = self.create_enhanced_rule(
                    grounding,
                    related_triples,
                    related_visuals,
                    area
                )
                enhanced_rules.append(rule)
        
        logger.info(f"Created {len(enhanced_rules)} enhanced rules for {area}")
        return enhanced_rules
    
    def find_related_triples(self, text: str, triples: List[Tuple]) -> List[Tuple]:
        """Find knowledge triples related to the given text"""
        related = []
        text_lower = text.lower()
        
        for triple in triples:
            # Check if any part of the triple relates to the text
            if any(str(part).lower() in text_lower for part in triple):
                related.append(triple)
                
        return related
    
    def find_related_visuals(self, text: str, multimodal_context: Dict) -> Dict:
        """Find visual elements related to the given text"""
        related = {}
        text_lower = text.lower()
        
        # Check tables
        if 'tables' in multimodal_context:
            for table in multimodal_context['tables']:
                if any(keyword in text_lower for keyword in ['table', 'schedule', 'matrix']):
                    related['tables'] = table
                    
        # Check visual elements
        if 'visual_elements' in multimodal_context:
            if any(keyword in text_lower for keyword in ['diagram', 'figure', 'map']):
                related['visuals'] = multimodal_context['visual_elements']
                
        return related
    
    def is_setback_rule(self, text: str) -> bool:
        """Check if text contains setback rule information"""
        setback_keywords = [
            'setback', 'boundary', 'distance', 'separation',
            'front', 'side', 'rear', 'building line'
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in setback_keywords)
    
    def create_enhanced_rule(
        self,
        grounding: SourceGrounding,
        triples: List[Tuple],
        visuals: Dict,
        area: str
    ) -> EnhancedSetbackRule:
        """Create an enhanced rule combining all semantic sources"""
        
        # Extract measurements from text
        measurements = self.extract_measurements(grounding.extraction_text)
        
        # Determine rule type
        rule_type = self.determine_rule_type(grounding.extraction_text)
        
        # Classify rule tier
        classification = self.classify_rule_tier(grounding.extraction_text)
        
        # Generate rule ID
        rule_id = f"{area.upper()}_{rule_type.upper()}_{hash(grounding.extraction_text) % 1000:03d}"
        
        return EnhancedSetbackRule(
            rule_id=rule_id,
            rule_text=grounding.extraction_text,
            rule_type=rule_type,
            measurements=measurements,
            rule_classification=classification,
            source_grounding=grounding,
            semantic_triples=triples,
            visual_context=visuals,
            overall_confidence=self.calculate_confidence(grounding, triples, visuals),
            rule_complexity=self.determine_complexity(grounding.extraction_text)
        )
    
    def extract_measurements(self, text: str) -> List[Dict]:
        """Extract numerical measurements from text"""
        import re
        measurements = []
        
        # Pattern for measurements (e.g., "0.9m", "6 metres")
        pattern = r'(\d+\.?\d*)\s*(m|metres?|meters?)'
        matches = re.finditer(pattern, text, re.IGNORECASE)
        
        for match in matches:
            measurements.append({
                'value': float(match.group(1)),
                'unit': 'metres',
                'context': text[max(0, match.start()-20):min(len(text), match.end()+20)]
            })
            
        return measurements
    
    def determine_rule_type(self, text: str) -> str:
        """Determine the type of setback rule"""
        text_lower = text.lower()
        
        if 'front' in text_lower:
            return 'front_setback'
        elif 'side' in text_lower:
            return 'side_setback'
        elif 'rear' in text_lower:
            return 'rear_setback'
        else:
            return 'general_setback'
    
    def classify_rule_tier(self, text: str) -> RuleClassification:
        """Classify rule into three-tier system"""
        text_lower = text.lower()
        
        # Tier 1: Mandatory
        if any(word in text_lower for word in ['must', 'shall', 'required', 'mandatory']):
            return RuleClassification(
                tier=1,
                enforcement_level="MANDATORY",
                linguistic_confidence=0.95,
                prescriptive_indicators=['must', 'shall'],
                compliance_message_type="MUST_COMPLY"
            )
        
        # Tier 2: Recommended
        elif any(word in text_lower for word in ['should', 'recommended', 'preferred']):
            return RuleClassification(
                tier=2,
                enforcement_level="RECOMMENDED",
                linguistic_confidence=0.85,
                prescriptive_indicators=['should', 'recommended'],
                compliance_message_type="SHOULD_ALIGN"
            )
        
        # Tier 3: Informational
        else:
            return RuleClassification(
                tier=3,
                enforcement_level="INFORMATIONAL",
                linguistic_confidence=0.75,
                prescriptive_indicators=[],
                compliance_message_type="CONSIDER"
            )
    
    def calculate_confidence(self, grounding, triples, visuals) -> float:
        """Calculate overall confidence based on all sources"""
        confidence = grounding.confidence
        
        # Boost confidence if we have supporting evidence
        if triples:
            confidence += 0.05
        if visuals:
            confidence += 0.05
            
        return min(confidence, 1.0)
    
    def determine_complexity(self, text: str) -> str:
        """Determine rule complexity"""
        if 'or' in text.lower() and 'whichever' in text.lower():
            return 'CONDITIONAL'
        elif 'and' in text.lower():
            return 'COMPOUND'
        else:
            return 'SIMPLE'
    
    def parse_table_content(self, response: str) -> List[Dict]:
        """Parse table content from LightRAG response"""
        # Simplified parsing - would need more sophisticated logic
        tables = []
        if 'table' in response.lower():
            tables.append({
                'content': response,
                'type': 'regulatory_table'
            })
        return tables
    
    def parse_visual_content(self, response: str) -> Dict:
        """Parse visual content from LightRAG response"""
        return {
            'description': response,
            'type': 'diagram_or_map'
        }
    
    def extract_graph_relationships(self, multimodal_context: Dict) -> List[Dict]:
        """Extract graph relationships from multimodal context"""
        relationships = []
        
        # Extract relationships from visual elements
        if 'visual_elements' in multimodal_context:
            relationships.append({
                'type': 'spatial_relationship',
                'content': multimodal_context['visual_elements']
            })
            
        return relationships
    
    def merge_area_extractions(self, area: str, extractions: List[UnifiedExtractionResult]) -> UnifiedExtractionResult:
        """Merge multiple document extractions for an area"""
        
        if not extractions:
            return None
            
        # Combine all extractions
        merged = UnifiedExtractionResult(
            area=area,
            document_path=f"Multiple documents for {area}",
            source_groundings=[],
            knowledge_triples=[],
            concept_hierarchy={},
            multimodal_context={},
            graph_relationships=[],
            enhanced_rules=[],
            processing_metadata={
                'timestamp': datetime.now().isoformat(),
                'documents_processed': len(extractions)
            }
        )
        
        # Merge all fields
        for extraction in extractions:
            if extraction:
                merged.source_groundings.extend(extraction.source_groundings)
                merged.knowledge_triples.extend(extraction.knowledge_triples)
                merged.concept_hierarchy.update(extraction.concept_hierarchy)
                merged.multimodal_context.update(extraction.multimodal_context)
                merged.graph_relationships.extend(extraction.graph_relationships)
                merged.enhanced_rules.extend(extraction.enhanced_rules)
        
        return merged
    
    async def process_lep_documents(self, lep_path: Path) -> UnifiedExtractionResult:
        """Process LEP documents"""
        pdf_files = list(lep_path.glob("*.pdf"))
        
        if not pdf_files:
            return None
            
        # Process LEP as single entity
        extraction = await self.process_single_document(pdf_files[0], "LEP")
        return extraction
    
    async def process_sepp_documents(self, sepp_path: Path) -> Dict[str, UnifiedExtractionResult]:
        """Process SEPP documents"""
        results = {}
        
        for pdf_file in sepp_path.glob("*.pdf"):
            sepp_name = pdf_file.stem
            extraction = await self.process_single_document(pdf_file, f"SEPP_{sepp_name}")
            results[sepp_name] = extraction
            
        return results
    
    def save_unified_results(self, results: Dict):
        """Save all results to structured JSON files"""
        
        # Save main unified extraction
        output_file = self.output_path / "unified_extraction.json"
        
        # Convert dataclasses to dict for JSON serialization
        json_results = {}
        for key, value in results.items():
            if isinstance(value, UnifiedExtractionResult):
                json_results[key] = asdict(value)
            elif isinstance(value, dict):
                json_results[key] = {
                    k: asdict(v) if isinstance(v, UnifiedExtractionResult) else v
                    for k, v in value.items()
                }
            else:
                json_results[key] = value
        
        with open(output_file, 'w') as f:
            json.dump(json_results, f, indent=2, default=str)
        
        logger.info(f"Saved unified results to {output_file}")
        
        # Also save area-specific files for easier access
        for area in ["Ashfield", "Leichhardt", "Marrickville"]:
            if area in results and results[area]:
                area_file = self.output_path / f"{area.lower()}_unified.json"
                with open(area_file, 'w') as f:
                    json.dump(asdict(results[area]), f, indent=2, default=str)
                logger.info(f"Saved {area} results to {area_file}")


async def main():
    """Main processing function"""
    processor = UnifiedDocumentProcessor()
    
    logger.info("Starting unified document processing...")
    logger.info("This will process all documents through LangExtract + AutoSchemaKG + LightRAG")
    
    results = await processor.process_all_documents()
    
    logger.info("Processing complete!")
    logger.info(f"Processed {len(results)} document groups")
    
    # Print summary
    for key, value in results.items():
        if isinstance(value, UnifiedExtractionResult):
            logger.info(f"  {key}: {len(value.enhanced_rules)} rules extracted")
        elif isinstance(value, dict):
            logger.info(f"  {key}: {len(value)} sub-documents processed")


if __name__ == "__main__":
    asyncio.run(main())