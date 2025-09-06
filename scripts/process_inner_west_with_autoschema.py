#!/usr/bin/env python3
"""
Enhanced processing script for Inner West Council DCPs using RAG-Anything + AutoSchemaKG
Combines semantic understanding with structured extraction for proper regulatory rule processing
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.models import (
    FormerCouncilArea, 
    ProcessedCouncilArea, 
    SetbackRules, 
    InnerWestSetbacks
)
from src.processing.simple_pdf_processor import SimplePDFProcessor  
from src.processing.schema_extractor import SchemaExtractor
from src.utils import DocumentFinder

try:
    from atlas_rag.kg_construction.triple_extraction import KnowledgeGraphExtractor
    from atlas_rag.kg_construction.triple_config import ProcessingConfig
    from atlas_rag.llm_generator import LLMGenerator
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    AUTOSCHEMA_AVAILABLE = True
except ImportError as e:
    print(f"Warning: AutoSchemaKG (atlas_rag) not available: {e}")
    AUTOSCHEMA_AVAILABLE = False

def extract_with_autoschema(text_chunks: List[str], area: FormerCouncilArea, file_path: str) -> Dict[str, Any]:
    """
    Use AutoSchemaKG KnowledgeGraphExtractor for enhanced semantic extraction of regulatory rules
    """
    if not AUTOSCHEMA_AVAILABLE:
        return {}
    
    try:
        # Initialize OpenAI client and LLM Generator
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key or api_key == 'your_openai_api_key_here':
            print("   Warning: OpenAI API key not configured, skipping AutoSchemaKG extraction")
            return {}
        
        # Set up OpenAI client
        client = OpenAI(api_key=api_key)
        model_name = "gpt-3.5-turbo"
        
        # Initialize LLM Generator
        triple_generator = LLMGenerator(client, model_name=model_name)
        
        # Create a temporary directory for processing
        temp_output_dir = f"temp_extraction_{area.value}"
        os.makedirs(temp_output_dir, exist_ok=True)
        
        # Write text chunks to temporary files for processing
        temp_files = []
        for i, chunk in enumerate(text_chunks):
            if len(chunk.strip()) < 100:  # Skip very short chunks
                continue
            
            temp_file = os.path.join(temp_output_dir, f"chunk_{i}.txt")
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(chunk)
            temp_files.append(temp_file)
        
        if not temp_files:
            print("   Warning: No suitable text chunks for AutoSchemaKG processing")
            return {}
        
        # Configure AutoSchemaKG processing
        kg_extraction_config = ProcessingConfig(
            model_path=model_name,
            data_directory=temp_output_dir,
            filename_pattern="*.txt",
            batch_size_triple=2,  # Small batch for regulatory text
            batch_size_concept=8,
            output_directory=f"{temp_output_dir}/output",
            max_new_tokens=1024,
            max_workers=1,  # Single worker for consistent processing
            remove_entity_metadata=False
        )
        
        # Initialize KnowledgeGraphExtractor
        kg_extractor = KnowledgeGraphExtractor(
            triple_generator=triple_generator,
            config=kg_extraction_config
        )
        
        print(f"   Running AutoSchemaKG extraction on {len(temp_files)} chunks...")
        
        # Run knowledge graph extraction
        extracted_triples = kg_extractor.extract_triples()
        
        # Process the extracted triples to find setback rules
        setback_rules = {}
        
        if extracted_triples:
            # Look for setback-related triples
            for triple in extracted_triples:
                if isinstance(triple, dict):
                    subject = triple.get('subject', '').lower()
                    predicate = triple.get('predicate', '').lower()
                    obj = triple.get('object', '').lower()
                    
                    # Look for setback relationships
                    if any(setback_term in subject for setback_term in ['rear', 'side', 'front', 'setback']):
                        if any(distance_term in predicate for distance_term in ['distance', 'minimum', 'requirement']):
                            # Try to extract numeric value from object
                            import re
                            numbers = re.findall(r'\d+(?:\.\d+)?', obj)
                            if numbers:
                                value = float(numbers[0])
                                
                                # Determine setback type
                                if 'rear' in subject:
                                    setback_type = 'rear'
                                elif 'side' in subject:
                                    setback_type = 'side'
                                elif 'front' in subject:
                                    setback_type = 'front'
                                else:
                                    continue
                                
                                if setback_type not in setback_rules:
                                    setback_rules[setback_type] = {
                                        'distance': value if setback_type != 'front' else None,
                                        'min_distance': value if setback_type == 'front' else None,
                                        'source_triple': f"{subject} -> {predicate} -> {obj}",
                                        'extraction_confidence': 0.8,
                                        'source_file': os.path.basename(file_path),
                                        'former_council_area': area.value,
                                        'extraction_method': 'autoschema_kg'
                                    }
        
        # Clean up temporary files
        import shutil
        try:
            shutil.rmtree(temp_output_dir)
        except:
            pass  # Ignore cleanup errors
        
        print(f"   AutoSchemaKG extracted {len(setback_rules)} setback rule types")
        return setback_rules
        
    except Exception as e:
        print(f"   Error in AutoSchemaKG processing: {e}")
        import traceback
        traceback.print_exc()
        return {}

def convert_autoschema_rule(autoschema_rule: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert LLM-extracted rule to our standard format
    """
    rule = {
        "distance": autoschema_rule.get('distance'),
        "height_limit": autoschema_rule.get('height_limit'),
        "min_distance": autoschema_rule.get('min_distance'),
        "source": autoschema_rule.get('source_section', 'LLM Extracted'),
        "source_file": autoschema_rule.get('source_file', 'Unknown File'),
        "applicable_zones": autoschema_rule.get('applicable_zones'),
        "conditions": autoschema_rule.get('conditions'),
        "extraction_confidence": autoschema_rule.get('extraction_confidence', 0.7)
    }
    
    # Clean up None values and ensure proper types
    cleaned_rule = {}
    for k, v in rule.items():
        if v is not None:
            # Convert string numbers to float for distance values
            if k in ['distance', 'height_limit', 'min_distance'] and isinstance(v, str):
                try:
                    cleaned_rule[k] = float(v)
                except ValueError:
                    pass
            else:
                cleaned_rule[k] = v
    
    return cleaned_rule

def main():
    """Enhanced main processing function with AutoSchemaKG integration"""
    print("NSW Development Compliance MVP - Enhanced Processing with AutoSchemaKG")
    print("=" * 70)
    
    if AUTOSCHEMA_AVAILABLE:
        print("SUCCESS: AutoSchemaKG available - using semantic extraction")
    else:
        print("WARNING: AutoSchemaKG not available - using basic extraction only")
    
    # Initialize processors
    print("\nInitializing processors...")
    pdf_processor = SimplePDFProcessor(chunk_size=800, chunk_overlap=100)
    schema_extractor = SchemaExtractor()
    doc_finder = DocumentFinder("docs/dcps/INNERWEST/")
    
    results = {}
    processing_stats = {
        "total_files_processed": 0,
        "successful_extractions": 0,
        "failed_extractions": 0,
        "autoschema_extractions": 0
    }
    
    # Process each former council area
    for area in [FormerCouncilArea.ASHFIELD, FormerCouncilArea.LEICHHARDT, FormerCouncilArea.MARRICKVILLE]:
        print(f"\n{'='*20} Processing {area.value} {'='*20}")
        
        try:
            # Find relevant documents for this area
            dcp_files = doc_finder.get_setback_documents(area)
            
            if not dcp_files:
                print(f"Warning: No documents found for {area.value}")
                continue
            
            print(f"Found {len(dcp_files)} documents to process:")
            for file_path in dcp_files:
                print(f"   - {os.path.basename(file_path)}")
            
            processed_files = []
            all_extracted_rules = {"rear": [], "side": [], "front": []}
            
            # Process each document
            for file_path in dcp_files:
                print(f"\n   Processing: {os.path.basename(file_path)}")
                processing_stats["total_files_processed"] += 1
                
                try:
                    # Extract text using PyMuPDF
                    print("   Extracting text...")
                    text = pdf_processor.extract_text_from_pdf(file_path)
                    
                    if not text:
                        print(f"   Warning: No text extracted from {os.path.basename(file_path)}")
                        processing_stats["failed_extractions"] += 1
                        continue
                    
                    print(f"   Success: Extracted {len(text)} characters")
                    
                    # Chunk text for processing
                    print("   Chunking text for regulatory content...")
                    chunks = pdf_processor.chunk_regulatory_text(text)
                    print(f"   Success: Found {len(chunks)} regulatory chunks")
                    
                    if not chunks:
                        print("   Warning: No regulatory chunks found")
                        processing_stats["failed_extractions"] += 1
                        continue
                    
                    # Try AutoSchemaKG first if available
                    autoschema_rules = {}
                    if AUTOSCHEMA_AVAILABLE:
                        print("   Extracting rules with AutoSchemaKG semantic processing...")
                        autoschema_rules = extract_with_autoschema(chunks, area, file_path)
                        
                        if autoschema_rules:
                            processing_stats["autoschema_extractions"] += 1
                            print(f"   Success: AutoSchemaKG extracted {len(autoschema_rules)} rule types")
                    
                    # Fallback to regex extraction for any missing rules
                    print("   Extracting additional rules with regex patterns...")
                    regex_rules = schema_extractor.extract_setback_rules(chunks, area, file_path)
                    
                    # Combine results, preferring AutoSchemaKG when available
                    combined_rules = {}
                    for rule_type in ["rear", "side", "front"]:
                        if rule_type in autoschema_rules:
                            combined_rules[rule_type] = autoschema_rules[rule_type]
                        elif regex_rules.get(rule_type):
                            combined_rules[rule_type] = regex_rules[rule_type]
                        else:
                            combined_rules[rule_type] = None
                    
                    # Collect rules from this document
                    rules_found = []
                    for rule_type, rule in combined_rules.items():
                        if rule:
                            all_extracted_rules[rule_type].append(rule)
                            rules_found.append(rule_type)
                    
                    if rules_found:
                        extraction_method = "AutoSchemaKG + Regex" if autoschema_rules else "Regex only"
                        print(f"   Success: {extraction_method} extracted {', '.join(rules_found)}")
                        processing_stats["successful_extractions"] += 1
                    else:
                        print("   Warning: No setback rules found")
                        processing_stats["failed_extractions"] += 1
                    
                    processed_files.append(os.path.basename(file_path))
                    
                except Exception as e:
                    print(f"   Error processing {os.path.basename(file_path)}: {e}")
                    processing_stats["failed_extractions"] += 1
                    continue
            
            # Consolidate rules (select the best example of each type)
            final_rules = {}
            for rule_type, rule_list in all_extracted_rules.items():
                if rule_list:
                    # Sort by extraction confidence and completeness
                    def get_rule_score(rule):
                        if isinstance(rule, dict):
                            return (
                                rule.get('extraction_confidence', 0.5),
                                bool(rule.get('distance')),
                                bool(rule.get('min_distance')),
                                bool(rule.get('height_limit'))
                            )
                        else:
                            # Handle SetbackRule objects
                            return (
                                0.5,  # Default confidence for regex-extracted rules
                                bool(getattr(rule, 'distance', None)),
                                bool(getattr(rule, 'min_distance', None)),
                                bool(getattr(rule, 'height_limit', None))
                            )
                    
                    best_rule = max(rule_list, key=get_rule_score)
                    final_rules[rule_type] = best_rule
                else:
                    final_rules[rule_type] = None
            
            # Calculate overall extraction confidence
            confidence = schema_extractor.calculate_confidence(final_rules)
            
            # Create processed area data
            if any(final_rules.values()):
                results[area.value] = ProcessedCouncilArea(
                    name=area,
                    dcp_version=f"{area.value} DCP {doc_finder.get_dcp_year(area)}",
                    processed_files=processed_files,
                    setbacks=SetbackRules(**final_rules),
                    extraction_confidence=confidence
                )
                
                print(f"SUCCESS {area.value}: {len([r for r in final_rules.values() if r])} setback rules extracted (confidence: {confidence:.2f})")
                
                # Show what was extracted
                for rule_type, rule in final_rules.items():
                    if rule:
                        distance = rule.get('distance', 'N/A')
                        min_distance = rule.get('min_distance', 'N/A')
                        height = rule.get('height_limit', 'N/A')
                        print(f"     {rule_type.title()}: {distance}m distance, {min_distance}m min, {height}m height")
            else:
                print(f"WARNING {area.value}: No setback rules extracted from any documents")
        
        except Exception as e:
            print(f"ERROR: Failed to process {area.value}: {e}")
            continue
    
    # Generate final output
    print(f"\n{'='*20} Processing Summary {'='*20}")
    print(f"   Files processed: {processing_stats['total_files_processed']}")
    print(f"   Successful extractions: {processing_stats['successful_extractions']}")
    print(f"   AutoSchemaKG extractions: {processing_stats['autoschema_extractions']}")
    print(f"   Failed extractions: {processing_stats['failed_extractions']}")
    print(f"   Council areas with data: {len(results)}")
    
    if results:
        # Create final output structure
        avg_confidence = sum(r.extraction_confidence for r in results.values()) / len(results)
        
        final_output = InnerWestSetbacks(
            areas=results,
            processing_metadata={
                "total_areas_processed": len(results),
                "processing_timestamp": datetime.now().isoformat(),
                "avg_confidence": avg_confidence,
                "total_files_processed": processing_stats["total_files_processed"],
                "successful_extractions": processing_stats["successful_extractions"],
                "autoschema_extractions": processing_stats["autoschema_extractions"],
                "processing_method": "RAG-Anything + AutoSchemaKG" if AUTOSCHEMA_AVAILABLE else "RAG-Anything only"
            }
        )
        
        # Ensure output directory exists
        output_dir = "public/regulatory-data"
        os.makedirs(output_dir, exist_ok=True)
        
        # Save enhanced output
        enhanced_path = os.path.join(output_dir, "inner-west-setbacks-enhanced.json")
        with open(enhanced_path, "w", encoding="utf-8") as f:
            json.dump(final_output.model_dump(), f, indent=2, ensure_ascii=False)
        
        # Update the main API output file
        api_path = os.path.join(output_dir, "inner-west-setbacks.json")
        with open(api_path, "w", encoding="utf-8") as f:
            json.dump(final_output.to_api_format(), f, indent=2, ensure_ascii=False)
        
        # Also create detailed output for development
        detailed_path = os.path.join(output_dir, "inner-west-setbacks-detailed.json")
        with open(detailed_path, "w", encoding="utf-8") as f:
            json.dump(final_output.model_dump(), f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*20} Output Files {'='*20}")
        print(f"Enhanced output: {enhanced_path}")
        print(f"API output: {api_path}")
        print(f"Detailed output: {detailed_path}")
        print(f"Average confidence: {avg_confidence:.2f}")
        
        return True
    else:
        print("\nERROR: No setback rules extracted from any documents!")
        print("Check that PDF files exist in docs/dcps/INNERWEST/ and are readable.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)