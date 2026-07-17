#!/usr/bin/env python3
"""
OpenAI Semantic Rule Processor
Direct OpenAI API usage for semantic rule extraction from compliance documents
"""

import os
import json
import openai
from pathlib import Path
from datetime import datetime

# OpenAI API key comes from the environment (.env), never hardcoded. The previous
# hardcoded key was committed to the repo and has been rotated.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

class OpenAISemanticProcessor:
    def __init__(self):
        if not OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Export it or add it to .env before running."
            )
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
    def extract_semantic_rules(self, text, area):
        """Extract semantic rules using OpenAI GPT-4o-mini"""
        
        extraction_prompt = f"""
You are a planning compliance expert analyzing {area} DCP (Development Control Plan) documents.

Extract specific setback rules from this text:

{text}

Rules to find:
1. Side setbacks (minimum distances from side boundaries)
2. Rear setbacks (minimum distances from rear boundaries)  
3. Front setbacks (minimum distances from front boundaries)

For each rule found, provide:
- Exact measurement in metres
- Rule text (quote from document)
- Confidence level (0.0-1.0)
- Context/conditions

Format response as JSON array:
[
  {{
    "rule_type": "side_setback" | "rear_setback" | "front_setback",
    "value": <numeric_metres>,
    "rule_text": "<exact quoted text>",
    "confidence": <0.0-1.0>,
    "context": "<conditions/zone/development type>",
    "source_section": "<section reference if available>"
  }}
]

Only include rules with clear numeric measurements. Return empty array [] if no clear rules found.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": extraction_prompt}],
                max_tokens=2000,
                temperature=0.1
            )
            
            result = response.choices[0].message.content.strip()
            
            # Handle markdown code blocks
            if result.startswith('```json'):
                result = result[7:]  # Remove ```json
            if result.endswith('```'):
                result = result[:-3]  # Remove ```
            result = result.strip()
            
            # Parse JSON response
            if result.startswith('[') and result.endswith(']'):
                rules_data = json.loads(result)
                return self.format_rules(rules_data, area)
            else:
                print(f"Non-JSON response from OpenAI: {result[:200]}...")
                return []
                
        except json.JSONDecodeError as e:
            print(f"Failed to parse OpenAI JSON response: {e}")
            print(f"Response was: {result[:500]}...")
            return []
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return []
    
    def format_rules(self, rules_data, area):
        """Format OpenAI extracted rules into our standard format"""
        formatted_rules = []
        
        for rule_data in rules_data:
            if not rule_data.get('rule_type') or not rule_data.get('value'):
                continue
                
            try:
                rule = {
                    "rule_id": f"{area.upper()}_{rule_data['rule_type'].upper()}_SEMANTIC",
                    "rule_text": rule_data.get('rule_text', f"{rule_data['rule_type']} requirement"),
                    "rule_type": rule_data['rule_type'],
                    "measurements": [{
                        "measurement_type": rule_data['rule_type'],
                        "value": float(rule_data['value']),
                        "unit": "metres",
                        "context": rule_data.get('context', 'semantic extraction'),
                        "confidence": rule_data.get('confidence', 0.8)
                    }],
                    "rule_classification": {
                        "tier": 1,
                        "enforcement_level": "MANDATORY",
                        "linguistic_confidence": rule_data.get('confidence', 0.8),
                        "compliance_message_type": "MUST_COMPLY"
                    },
                    "source_grounding": {
                        "extraction_text": rule_data.get('rule_text', '')[:200],
                        "source_location": rule_data.get('source_section', f"{area} DCP"),
                        "confidence": rule_data.get('confidence', 0.8)
                    },
                    "overall_confidence": rule_data.get('confidence', 0.8),
                    "rule_complexity": "SEMANTIC_EXTRACTED"
                }
                formatted_rules.append(rule)
                
            except Exception as e:
                print(f"Failed to format rule: {e}")
                continue
        
        return formatted_rules

def process_all_areas():
    """Process all areas with OpenAI semantic extraction"""
    print("OpenAI Semantic Rule Extraction")
    print("=" * 50)
    
    processor = OpenAISemanticProcessor()
    areas = ['Ashfield', 'Leichhardt', 'Marrickville']
    
    # Create output directories
    unified_dir = Path("public/regulatory-data/unified")
    unified_dir.mkdir(parents=True, exist_ok=True)
    
    unified_data = {}
    
    for area in areas:
        print(f"\nProcessing {area} with OpenAI semantic extraction...")
        
        # Load text chunks
        temp_dir = Path(f"temp_extraction_{area}")
        if not temp_dir.exists():
            print(f"No text chunks for {area}")
            continue
            
        # Combine all chunks for the area
        full_text = ""
        chunk_count = 0
        for chunk_file in temp_dir.glob('chunk_*.txt'):
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        full_text += content + "\\n\\n"
                        chunk_count += 1
            except Exception as e:
                print(f"Failed to read {chunk_file}: {e}")
        
        if not full_text:
            print(f"No content for {area}")
            continue
            
        print(f"Loaded {chunk_count} chunks ({len(full_text)} chars)")
        
        # Extract rules using OpenAI
        print("Extracting rules with OpenAI...")
        rules = processor.extract_semantic_rules(full_text, area)
        
        if rules:
            print(f"Extracted {len(rules)} semantic rules:")
            for rule in rules:
                print(f"  - {rule['rule_type']}: {rule['measurements'][0]['value']}m")
            
            # Build area data
            area_data = {
                "area": area,
                "document_path": f"docs/dcps/INNERWEST/{area}/",
                "source_groundings": [rule["source_grounding"] for rule in rules],
                "knowledge_triples": [
                    [rule['rule_type'], "has_minimum_distance", f"{rule['measurements'][0]['value']}m"]
                    for rule in rules
                ],
                "enhanced_rules": rules,
                "processing_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "processors_used": ["OpenAI-GPT-4o-mini"],
                    "extraction_method": "openai_semantic_extraction",
                    "documents_processed": chunk_count,
                    "total_chars": len(full_text)
                }
            }
            
            unified_data[area] = area_data
            
            # Save area file
            area_file = unified_dir / f"{area.lower()}_unified.json"
            with open(area_file, 'w') as f:
                json.dump(area_data, f, indent=2, default=str)
            print(f"Saved: {area_file}")
        else:
            print(f"No rules extracted for {area}")
    
    # Save master file
    if unified_data:
        unified_file = unified_dir / "unified_extraction.json"
        with open(unified_file, 'w') as f:
            json.dump(unified_data, f, indent=2, default=str)
        print(f"\\nSaved master file: {unified_file}")
        
        total_rules = sum(len(area.get('enhanced_rules', [])) for area in unified_data.values())
        print(f"Total semantic rules extracted: {total_rules}")
        
        for area_name, area_data in unified_data.items():
            rules = area_data.get('enhanced_rules', [])
            print(f"{area_name}: {len(rules)} rules")
    
    return unified_data

if __name__ == "__main__":
    process_all_areas()