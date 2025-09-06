#!/usr/bin/env python3
"""
Semantic processing script for Inner West Council DCPs
Uses improved text analysis without requiring external API keys
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any
import re

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.models import (
    FormerCouncilArea, 
    ProcessedCouncilArea, 
    SetbackRules, 
    InnerWestSetbacks,
    SetbackRule
)
from src.processing.simple_pdf_processor import SimplePDFProcessor  
from src.utils import DocumentFinder

class SemanticSetbackExtractor:
    """Enhanced semantic extractor for setback rules"""
    
    def __init__(self):
        # More precise regex patterns with context validation
        self.patterns = {
            "rear": [
                # "minimum rear setback of X metres"
                r'minimum\s+rear\s+setback\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
                # "rear setback...X metres" with distance validation
                r'rear\s+setback\s+(?:of\s+|is\s+|shall\s+be\s+)?(\d+(?:\.\d+)?)\s*m(?:etres?)?\s*(?:minimum|min)?',
                # "X metre rear setback"
                r'(\d+(?:\.\d+)?)\s*m(?:etre?)?\s+rear\s+setback'
            ],
            "side": [
                # "minimum side setback of X metres"
                r'minimum\s+side\s+setback\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
                # "side setback of X metres"
                r'side\s+setback\s+(?:of\s+|is\s+|shall\s+be\s+)?(\d+(?:\.\d+)?)\s*m(?:etres?)?\s*(?:minimum|min)?',
                # "X metre side setback"
                r'(\d+(?:\.\d+)?)\s*m(?:etre?)?\s+side\s+setback'
            ],
            "front": [
                # "minimum front setback of X metres"
                r'minimum\s+front\s+setback\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
                # "front setback of X metres"
                r'front\s+setback\s+(?:of\s+|is\s+|shall\s+be\s+)?(\d+(?:\.\d+)?)\s*m(?:etres?)?\s*(?:minimum|min)?',
                # "X metre front setback"
                r'(\d+(?:\.\d+)?)\s*m(?:etre?)?\s+front\s+setback'
            ]
        }
        
        # Invalid ranges - filter out unrealistic values
        self.valid_ranges = {
            "rear": (0.5, 10.0),    # 0.5m to 10m is realistic for rear setbacks
            "side": (0.5, 5.0),     # 0.5m to 5m is realistic for side setbacks  
            "front": (0.0, 20.0)    # 0m to 20m is realistic for front setbacks
        }
    
    def extract_semantic_rules(self, text_chunks: List[str], area: FormerCouncilArea, file_path: str) -> Dict[str, Any]:
        """
        Extract setback rules using semantic text analysis
        """
        # Combine chunks but maintain context
        full_text = ' '.join(text_chunks)
        
        # Find sentences that contain setback information
        setback_sentences = self._find_setback_sentences(full_text)
        
        # Extract rules from these sentences
        extracted_rules = {}
        for setback_type in ["rear", "side", "front"]:
            rule = self._extract_setback_type_semantic(setback_sentences, setback_type, area, file_path)
            if rule:
                extracted_rules[setback_type] = rule
        
        return extracted_rules
    
    def _find_setback_sentences(self, text: str) -> List[str]:
        """Find sentences that likely contain setback information"""
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        
        setback_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Skip very short sentences
                continue
            
            # Check if sentence contains setback-related terms
            setback_terms = ['setback', 'setbacks', 'building line', 'boundary']
            distance_terms = ['metre', 'meter', 'm ', 'minimum', 'maximum']
            
            has_setback = any(term in sentence.lower() for term in setback_terms)
            has_distance = any(term in sentence.lower() for term in distance_terms)
            
            if has_setback and has_distance:
                setback_sentences.append(sentence)
        
        return setback_sentences
    
    def _extract_setback_type_semantic(self, sentences: List[str], setback_type: str, area: FormerCouncilArea, source_file: str) -> Dict[str, Any]:
        """Extract specific setback type with semantic validation"""
        
        best_match = None
        best_confidence = 0
        
        for sentence in sentences:
            # Check if this sentence is about the setback type we want
            if setback_type.lower() not in sentence.lower():
                continue
            
            # Try all patterns for this setback type
            for pattern in self.patterns[setback_type]:
                matches = re.finditer(pattern, sentence.lower())
                
                for match in matches:
                    try:
                        value = float(match.group(1))
                        
                        # Validate the value is in a reasonable range
                        min_val, max_val = self.valid_ranges[setback_type]
                        if not (min_val <= value <= max_val):
                            continue  # Skip unrealistic values
                        
                        # Calculate confidence based on context
                        confidence = self._calculate_context_confidence(sentence, setback_type, value)
                        
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_match = {
                                "value": value,
                                "sentence": sentence,
                                "confidence": confidence,
                                "pattern": pattern
                            }
                    
                    except (ValueError, IndexError):
                        continue
        
        if best_match and best_confidence > 0.5:  # Only return if we're confident
            return self._create_setback_rule(best_match, setback_type, area, source_file)
        
        return None
    
    def _calculate_context_confidence(self, sentence: str, setback_type: str, value: float) -> float:
        """Calculate confidence based on sentence context"""
        confidence = 0.5  # Base confidence
        
        sentence_lower = sentence.lower()
        
        # Boost confidence for explicit minimum language
        if any(term in sentence_lower for term in ['minimum', 'min', 'shall be', 'must be']):
            confidence += 0.2
        
        # Boost confidence for specific setback type mention
        if f"{setback_type} setback" in sentence_lower:
            confidence += 0.2
        
        # Boost confidence for metre/meter spelling out
        if any(term in sentence_lower for term in ['metre', 'metres', 'meter', 'meters']):
            confidence += 0.1
        
        # Reduce confidence for vague language
        if any(term in sentence_lower for term in ['approximately', 'around', 'about', 'generally']):
            confidence -= 0.2
        
        # Reduce confidence for very high values that might be addresses/lot sizes
        if setback_type in ['front', 'side'] and value > 10:
            confidence -= 0.3
        elif setback_type == 'rear' and value > 6:
            confidence -= 0.2
        
        return min(1.0, max(0.0, confidence))
    
    def _create_setback_rule(self, match_data: Dict, setback_type: str, area: FormerCouncilArea, source_file: str) -> Dict[str, Any]:
        """Create a standardized setback rule from match data"""
        
        rule = {
            "source_sentence": match_data["sentence"].strip(),
            "extraction_confidence": match_data["confidence"],
            "source_file": os.path.basename(source_file),
            "former_council_area": area.value,
            "extraction_method": "semantic_regex"
        }
        
        # Set the appropriate field based on setback type
        if setback_type == "front":
            rule["min_distance"] = match_data["value"]
        else:
            rule["distance"] = match_data["value"]
        
        # Generate source reference
        rule["source"] = f"{area.value} DCP - Semantic Extraction"
        
        return rule

def main():
    """Main processing function with semantic extraction"""
    print("NSW Development Compliance MVP - Semantic Processing")
    print("=" * 60)
    
    # Initialize processors
    print("\nInitializing processors...")
    pdf_processor = SimplePDFProcessor(chunk_size=800, chunk_overlap=100)
    semantic_extractor = SemanticSetbackExtractor()
    doc_finder = DocumentFinder("docs/dcps/INNERWEST/")
    
    results = {}
    processing_stats = {
        "total_files_processed": 0,
        "successful_extractions": 0,
        "failed_extractions": 0,
        "semantic_extractions": 0
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
                    
                    # Extract with semantic processing
                    print("   Extracting rules with semantic processing...")
                    semantic_rules = semantic_extractor.extract_semantic_rules(chunks, area, file_path)
                    
                    # Collect rules from this document
                    rules_found = []
                    for rule_type, rule in semantic_rules.items():
                        if rule:
                            all_extracted_rules[rule_type].append(rule)
                            rules_found.append(rule_type)
                    
                    if rules_found:
                        processing_stats["successful_extractions"] += 1
                        processing_stats["semantic_extractions"] += 1
                        print(f"   Success: Semantic extraction found {', '.join(rules_found)}")
                        
                        # Show extracted values
                        for rule_type in rules_found:
                            rule = semantic_rules[rule_type]
                            distance = rule.get('distance', rule.get('min_distance'))
                            confidence = rule.get('extraction_confidence', 0)
                            print(f"     {rule_type.title()}: {distance}m (confidence: {confidence:.2f})")
                    else:
                        print("   Warning: No setback rules found")
                        processing_stats["failed_extractions"] += 1
                    
                    processed_files.append(os.path.basename(file_path))
                    
                except Exception as e:
                    print(f"   Error processing {os.path.basename(file_path)}: {e}")
                    processing_stats["failed_extractions"] += 1
                    continue
            
            # Consolidate rules (select the best example of each type)
            final_setback_rules = {}
            for rule_type, rule_list in all_extracted_rules.items():
                if rule_list:
                    # Sort by confidence and select the best
                    best_rule = max(rule_list, key=lambda r: r.get('extraction_confidence', 0.5))
                    
                    # Convert to SetbackRule object
                    setback_rule_data = {}
                    if 'distance' in best_rule:
                        setback_rule_data['distance'] = best_rule['distance']
                    if 'min_distance' in best_rule:
                        setback_rule_data['min_distance'] = best_rule['min_distance']
                    if 'height_limit' in best_rule:
                        setback_rule_data['height_limit'] = best_rule['height_limit']
                    
                    setback_rule_data['source'] = best_rule.get('source', f'{area.value} DCP')
                    setback_rule_data['source_file'] = best_rule.get('source_file', 'Unknown')
                    
                    final_setback_rules[rule_type] = SetbackRule(**setback_rule_data)
                else:
                    final_setback_rules[rule_type] = None
            
            # Calculate overall extraction confidence
            if any(final_setback_rules.values()):
                confidence_values = []
                for rule_list in all_extracted_rules.values():
                    if rule_list:
                        best = max(rule_list, key=lambda r: r.get('extraction_confidence', 0.5))
                        confidence_values.append(best.get('extraction_confidence', 0.5))
                
                avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.5
                
                # Create processed area data
                results[area.value] = ProcessedCouncilArea(
                    name=area,
                    dcp_version=f"{area.value} DCP {doc_finder.get_dcp_year(area)}",
                    processed_files=processed_files,
                    setbacks=SetbackRules(**final_setback_rules),
                    extraction_confidence=avg_confidence
                )
                
                print(f"SUCCESS {area.value}: {len([r for r in final_setback_rules.values() if r])} setback rules extracted (confidence: {avg_confidence:.2f})")
                
                # Show final extracted rules
                for rule_type, rule in final_setback_rules.items():
                    if rule:
                        distance = getattr(rule, 'distance', getattr(rule, 'min_distance', None))
                        height = getattr(rule, 'height_limit', None)
                        print(f"     {rule_type.title()}: {distance}m distance, {height or 'N/A'}m height")
            else:
                print(f"WARNING {area.value}: No setback rules extracted from any documents")
        
        except Exception as e:
            print(f"ERROR: Failed to process {area.value}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Generate final output
    print(f"\n{'='*20} Processing Summary {'='*20}")
    print(f"   Files processed: {processing_stats['total_files_processed']}")
    print(f"   Successful extractions: {processing_stats['successful_extractions']}")
    print(f"   Semantic extractions: {processing_stats['semantic_extractions']}")
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
                "semantic_extractions": processing_stats["semantic_extractions"],
                "processing_method": "Semantic Text Analysis"
            }
        )
        
        # Ensure output directory exists
        output_dir = "public/regulatory-data"
        os.makedirs(output_dir, exist_ok=True)
        
        # Save semantic output
        semantic_path = os.path.join(output_dir, "inner-west-setbacks-semantic.json")
        with open(semantic_path, "w", encoding="utf-8") as f:
            json.dump(final_output.model_dump(), f, indent=2, ensure_ascii=False)
        
        # Update the main API output file
        api_path = os.path.join(output_dir, "inner-west-setbacks.json")
        with open(api_path, "w", encoding="utf-8") as f:
            json.dump(final_output.to_api_format(), f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*20} Output Files {'='*20}")
        print(f"Semantic output: {semantic_path}")
        print(f"API output: {api_path}")
        print(f"Average confidence: {avg_confidence:.2f}")
        
        return True
    else:
        print("\nERROR: No setback rules extracted from any documents!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)