#!/usr/bin/env python3
"""
Main processing script for Inner West Council DCPs
Processes all 3 former council areas and generates structured JSON output
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict

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

def main():
    """Main processing function"""
    print("NSW Development Compliance MVP - Processing Inner West DCPs")
    print("=" * 60)
    
    # Initialize processors
    print("Initializing processors...")
    pdf_processor = SimplePDFProcessor(chunk_size=500, chunk_overlap=50)
    schema_extractor = SchemaExtractor()
    doc_finder = DocumentFinder("docs/dcps/INNERWEST/")
    
    results = {}
    processing_stats = {
        "total_files_processed": 0,
        "successful_extractions": 0,
        "failed_extractions": 0
    }
    
    # Process each former council area
    for area in [FormerCouncilArea.ASHFIELD, FormerCouncilArea.LEICHHARDT, FormerCouncilArea.MARRICKVILLE]:
        print(f"\nProcessing {area.value} DCP documents...")
        
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
                    
                    # Extract structured data using regex patterns
                    print("   Extracting setback rules...")
                    rules = schema_extractor.extract_setback_rules(chunks, area, file_path)
                    
                    # Collect rules from this document
                    rules_found = []
                    for rule_type, rule in rules.items():
                        if rule:
                            all_extracted_rules[rule_type].append(rule)
                            rules_found.append(rule_type)
                    
                    if rules_found:
                        print(f"   Success: Extracted {', '.join(rules_found)}")
                        processing_stats["successful_extractions"] += 1
                    else:
                        print("   Warning: No setback rules found")
                        processing_stats["failed_extractions"] += 1
                    
                    processed_files.append(os.path.basename(file_path))
                    
                except Exception as e:
                    print(f"   Error processing {os.path.basename(file_path)}: {e}")
                    processing_stats["failed_extractions"] += 1
                    continue
            
            # Consolidate rules (take the best example of each type)
            final_rules = {}
            for rule_type, rule_list in all_extracted_rules.items():
                if rule_list:
                    # For now, take the first good rule found
                    # In production, we'd have logic to choose the best/most complete rule
                    final_rules[rule_type] = rule_list[0]
                else:
                    final_rules[rule_type] = None
            
            # Calculate extraction confidence
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
                
                print(f"Success {area.value}: {len([r for r in final_rules.values() if r])} setback rules extracted (confidence: {confidence:.2f})")
            else:
                print(f"Warning {area.value}: No setback rules extracted from any documents")
        
        except Exception as e:
            print(f"Error: Failed to process {area.value}: {e}")
            continue
    
    # Generate final output
    print(f"\nProcessing Summary:")
    print(f"   Files processed: {processing_stats['total_files_processed']}")
    print(f"   Successful extractions: {processing_stats['successful_extractions']}")
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
                "successful_extractions": processing_stats["successful_extractions"]
            }
        )
        
        # Ensure output directory exists
        output_dir = "public/regulatory-data"
        os.makedirs(output_dir, exist_ok=True)
        
        # Save detailed output
        detailed_path = os.path.join(output_dir, "inner-west-setbacks-detailed.json")
        with open(detailed_path, "w", encoding="utf-8") as f:
            json.dump(final_output.model_dump(), f, indent=2, ensure_ascii=False)
        
        # Save API-compatible output
        api_path = os.path.join(output_dir, "inner-west-setbacks.json")
        with open(api_path, "w", encoding="utf-8") as f:
            json.dump(final_output.to_api_format(), f, indent=2, ensure_ascii=False)
        
        print(f"\nProcessing complete!")
        print(f"Detailed output: {detailed_path}")
        print(f"API output: {api_path}")
        print(f"Average confidence: {avg_confidence:.2f}")
        
        # Print summary of extracted rules
        print(f"\nExtracted Rules Summary:")
        for area_name, area_data in results.items():
            print(f"   {area_name}:")
            setbacks = area_data.setbacks
            if setbacks.rear:
                print(f"     Rear: {setbacks.rear.distance or 'N/A'}m distance, {setbacks.rear.height_limit or 'N/A'}m height")
            if setbacks.side:
                print(f"     Side: {setbacks.side.height_limit or 'N/A'}m height limit")
            if setbacks.front:
                print(f"     Front: {setbacks.front.min_distance or 'N/A'}m minimum")
        
        return True
    else:
        print("\nNo setback rules extracted from any documents!")
        print("Check that PDF files exist in docs/dcps/INNERWEST/ and are readable.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)