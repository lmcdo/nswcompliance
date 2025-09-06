#!/usr/bin/env python3
"""
Real Document Processing for LightRAG Integration
Processes actual PDF documents and extracts compliance rules
"""

import os
import json
import asyncio
from pathlib import Path
from datetime import datetime
import subprocess
import sys

# Set OpenAI API key from environment
OPENAI_API_KEY = "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"
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

def extract_text_from_pdfs():
    """Extract text from PDF documents using existing text chunks"""
    
    # Check if we have existing text chunks
    temp_dirs = [d for d in Path('.').glob('temp_extraction_*')]
    if not temp_dirs:
        print("No text chunks found. Need to extract text from PDFs first.")
        return None
    
    print(f"Found existing text extractions: {[d.name for d in temp_dirs]}")
    
    # Combine text from all chunks for each area
    extracted_texts = {}
    
    for temp_dir in temp_dirs:
        area = temp_dir.name.replace('temp_extraction_', '')
        chunks = []
        
        for chunk_file in temp_dir.glob('chunk_*.txt'):
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        chunks.append(content)
            except Exception as e:
                print(f"Failed to read {chunk_file}: {e}")
        
        if chunks:
            extracted_texts[area] = '\n\n'.join(chunks)
            print(f"Extracted {len(chunks)} chunks for {area} ({len(extracted_texts[area])} chars)")
    
    return extracted_texts

def extract_context_around_match(text, match_pos, context_chars=150):
    """Extract context around a matched position for better regulatory text"""
    start = max(0, match_pos - context_chars)
    end = min(len(text), match_pos + context_chars)
    context = text[start:end].strip()
    
    # Clean up the context
    context = ' '.join(context.split())  # Normalize whitespace
    
    # Try to end at sentence boundary
    sentence_endings = ['. ', '.\n', '; ']
    for ending in sentence_endings:
        if ending in context[context_chars//2:]:
            pos = context.find(ending, context_chars//2)
            if pos > 0:
                context = context[:pos + 1]
                break
    
    return context

def extract_setback_rules_from_text(text, area):
    """Extract setback rules from text using pattern matching with improved context"""
    
    # Simple pattern matching for setbacks
    rules = []
    
    # Look for setback patterns in text
    import re
    
    # More comprehensive patterns with context capture
    side_patterns = [
        r'(side.*?setback.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?)',
        r'((\d+(?:\.\d+)?)\s*m(?:etres?).*?side.*?setback)',
        r'(side.*?(\d+(?:\.\d+)?)\s*metres?)'
    ]
    
    # Pattern for rear setbacks  
    rear_patterns = [
        r'rear.*setback.*?(\d+(?:\.\d+)?)\s*m',
        r'(\d+(?:\.\d+)?)\s*m.*rear.*setback',
        r'rear.*(\d+(?:\.\d+)?)\s*metres'
    ]
    
    # Pattern for front setbacks
    front_patterns = [
        r'front.*setback.*?(\d+(?:\.\d+)?)\s*m',
        r'(\d+(?:\.\d+)?)\s*m.*front.*setback',
        r'front.*(\d+(?:\.\d+)?)\s*metres'
    ]
    
    # Extract side setback rules
    side_values = set()  # Track unique values to avoid duplicates
    for pattern in side_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
            try:
                # Get the numeric value (could be in different groups)
                if isinstance(match.groups()[1], str) and match.groups()[1].replace('.','').isdigit():
                    value = float(match.groups()[1])
                elif isinstance(match.groups()[0], str) and match.groups()[0].replace('.','').isdigit():
                    value = float(match.groups()[0])
                else:
                    continue
                    
                if value in side_values or value < 0.1 or value > 50:  # Skip unreasonable values
                    continue
                    
                side_values.add(value)
                
                # Extract better context around the match
                match_text = extract_context_around_match(text, match.start())
                
                rule = {
                    "rule_id": f"{area.upper()}_SIDE_SETBACK_{value:g}M",
                    "rule_text": f"Side setbacks shall be {value}m minimum as per {area} DCP requirements.",
                    "rule_type": "side_setback",
                    "measurements": [{
                        "measurement_type": "side_setback",
                        "value": value,
                        "unit": "metres",
                        "context": f"extracted from {area} DCP section",
                        "confidence": 0.80
                    }],
                    "rule_classification": {
                        "tier": 1,
                        "enforcement_level": "MANDATORY",
                        "linguistic_confidence": 0.80,
                        "compliance_message_type": "MUST_COMPLY"
                    },
                    "source_grounding": {
                        "extraction_text": match_text,
                        "source_location": f"{area} DCP Setbacks",
                        "confidence": 0.80
                    },
                    "overall_confidence": 0.80,
                    "rule_complexity": "SIMPLE"
                }
                rules.append(rule)
                
                if len(side_values) >= 2:  # Limit to 2 side setback rules max
                    break
            except (ValueError, IndexError):
                continue
        if len(side_values) >= 2:
            break
    
    # Extract rear setback rules
    for pattern in rear_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                value = float(match)
                rule = {
                    "rule_id": f"{area.upper()}_REAR_SETBACK_EXTRACTED",
                    "rule_text": f"Rear setbacks shall be {value}m minimum for dwelling houses.",
                    "rule_type": "rear_setback", 
                    "measurements": [{
                        "measurement_type": "rear_setback",
                        "value": value,
                        "unit": "metres",
                        "context": "minimum requirement extracted from text",
                        "confidence": 0.75
                    }],
                    "rule_classification": {
                        "tier": 1,
                        "enforcement_level": "MANDATORY",
                        "linguistic_confidence": 0.75,
                        "compliance_message_type": "MUST_COMPLY"
                    },
                    "source_grounding": {
                        "extraction_text": f"Rear setback requirement found: {value}m",
                        "source_location": f"{area} DCP",
                        "confidence": 0.75
                    },
                    "overall_confidence": 0.75,
                    "rule_complexity": "SIMPLE"
                }
                rules.append(rule)
                break
            except ValueError:
                continue
                
    # Extract front setback rules
    for pattern in front_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                value = float(match)
                rule = {
                    "rule_id": f"{area.upper()}_FRONT_SETBACK_EXTRACTED",
                    "rule_text": f"Front setbacks shall be {value}m minimum or align with streetscape.",
                    "rule_type": "front_setback",
                    "measurements": [{
                        "measurement_type": "front_setback",
                        "value": value,
                        "unit": "metres", 
                        "context": "minimum requirement or streetscape alignment",
                        "confidence": 0.70
                    }],
                    "rule_classification": {
                        "tier": 1,
                        "enforcement_level": "MANDATORY",
                        "linguistic_confidence": 0.70,
                        "compliance_message_type": "MUST_COMPLY"
                    },
                    "source_grounding": {
                        "extraction_text": f"Front setback requirement found: {value}m",
                        "source_location": f"{area} DCP",
                        "confidence": 0.70
                    },
                    "overall_confidence": 0.70,
                    "rule_complexity": "CONDITIONAL"
                }
                rules.append(rule)
                break
            except ValueError:
                continue
    
    return rules

def process_real_documents():
    """Process real documents and create semantic rules"""
    
    print("Processing Real Documents with Pattern Extraction")
    print("=" * 60)
    
    # Extract text from PDFs
    extracted_texts = extract_text_from_pdfs()
    if not extracted_texts:
        print("No extracted texts available")
        return
    
    # Create output directories
    unified_dir = Path("public/regulatory-data/unified")
    unified_dir.mkdir(parents=True, exist_ok=True)
    
    cache_dir = Path("public/regulatory-data/cache") 
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each area
    unified_data = {}
    
    for area, text in extracted_texts.items():
        print(f"\nProcessing {area}...")
        
        # Extract rules from text
        extracted_rules = extract_setback_rules_from_text(text, area)
        
        print(f"  Found {len(extracted_rules)} setback rules")
        for rule in extracted_rules:
            print(f"    - {rule['rule_type']}: {rule['measurements'][0]['value']}m")
        
        # Build area data structure
        area_data = {
            "area": area,
            "document_path": f"docs/dcps/INNERWEST/{area}/",
            "source_groundings": [rule["source_grounding"] for rule in extracted_rules],
            "knowledge_triples": [
                [rule['rule_type'], "has_minimum_distance", f"{rule['measurements'][0]['value']}m"]
                for rule in extracted_rules
            ],
            "concept_hierarchy": {
                "setbacks": [rule['rule_type'] for rule in extracted_rules],
                "zones": ["R2", "residential_low_density"],
                "development_types": ["dwelling_house", "secondary_dwelling"]
            },
            "enhanced_rules": extracted_rules,
            "processing_metadata": {
                "timestamp": datetime.now().isoformat(),
                "processors_used": ["PatternExtraction", "RealDocuments"],
                "documents_processed": len(text.split('\n\n')),
                "extraction_method": "real_document_pattern_extraction"
            }
        }
        
        unified_data[area] = area_data
        
        # Save area-specific file
        area_file = unified_dir / f"{area.lower()}_unified.json"
        with open(area_file, 'w') as f:
            json.dump(area_data, f, indent=2, default=str)
        print(f"  Saved: {area_file}")
    
    # Save master unified file
    unified_file = unified_dir / "unified_extraction.json"
    with open(unified_file, 'w') as f:
        json.dump(unified_data, f, indent=2, default=str)
    print(f"\nSaved master file: {unified_file}")
    
    # Create cache files
    print("\nBuilding cache files...")
    rule_index = {}
    area_index = {}
    
    for area_name, area_data in unified_data.items():
        for rule in area_data.get("enhanced_rules", []):
            rule_index[rule["rule_id"]] = {
                **rule,
                "area": area_name
            }
        
        area_index[area_name] = {
            "rules": area_data.get("enhanced_rules", []),
            "total_rules": len(area_data.get("enhanced_rules", []))
        }
    
    # Save cache files
    cache_files = {
        "rule_index": rule_index,
        "area_index": area_index,
        "master_index": {
            "created_at": datetime.now().isoformat(),
            "version": "1.0.0-real",
            "total_rules": len(rule_index),
            "total_areas": len(area_index)
        }
    }
    
    for name, data in cache_files.items():
        cache_file = cache_dir / f"{name}.json"
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"  Created cache: {cache_file}")
    
    print(f"\nReal document processing complete!")
    print(f"Areas processed: {list(unified_data.keys())}")
    print(f"Total rules extracted: {sum(len(area.get('enhanced_rules', [])) for area in unified_data.values())}")
    
    return unified_data

if __name__ == "__main__":
    process_real_documents()