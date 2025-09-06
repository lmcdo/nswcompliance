#!/usr/bin/env python3
"""
Fix Precise Citations - Extract exact regulatory text with measurements
"""

import os
import json
import openai
from pathlib import Path
from datetime import datetime

# Set OpenAI API key
OPENAI_API_KEY = "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"
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

class PreciseCitationExtractor:
    def __init__(self):
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
    def extract_precise_rules(self, document_text, area):
        """Extract rules with PRECISE citations that contain the actual measurements"""
        
        precise_extraction_prompt = f"""
You are analyzing {area} Council DCP documents. Your task is to find the EXACT sentences that contain specific setback measurements.

Document text:
{document_text[:12000]}

CRITICAL REQUIREMENTS:
1. Find sentences that contain EXACT numeric measurements for setbacks
2. Extract the COMPLETE sentence that contains the measurement
3. Include the clause/section reference if available in nearby text
4. Only include rules where you can find the specific measurement in the text

For each measurement found, provide:
- The EXACT sentence containing the measurement
- The numeric value in metres
- The rule type (side_setback, rear_setback, front_setback)
- The section/clause reference if found nearby

Format as JSON:
[
  {{
    "rule_type": "side_setback|rear_setback|front_setback",
    "measurement_value": <number_in_metres>,
    "exact_regulatory_sentence": "<complete sentence with measurement>",
    "section_clause": "<section/clause if found>",
    "confidence": 0.9,
    "context_before": "<sentence before for context>",
    "context_after": "<sentence after for context>"
  }}
]

EXAMPLES of what to look for:
- "Side setbacks shall be 0.9m minimum"
- "A minimum rear setback of 6 metres is required"  
- "Front setbacks must be at least 4.5m from the street boundary"

Do NOT include:
- Generic statements without measurements
- Sentences that just reference other clauses
- Incomplete sentence fragments

Return empty array [] if no precise measurements found.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system", 
                    "content": "You are a regulatory text analyst. Extract only sentences that contain specific numeric measurements."
                }, {
                    "role": "user", 
                    "content": precise_extraction_prompt
                }],
                max_tokens=2500,
                temperature=0.0  # Use 0.0 for maximum precision
            )
            
            result = response.choices[0].message.content.strip()
            
            # Handle markdown
            if result.startswith('```json'):
                result = result[7:]
            if result.endswith('```'):
                result = result[:-3]
            result = result.strip()
            
            print(f"OpenAI response for {area}: {result[:500]}...")
            
            if result.startswith('[') and result.endswith(']'):
                rules_data = json.loads(result)
                return self.format_precise_rules(rules_data, area)
            else:
                print(f"Non-JSON response: {result}")
                return []
                
        except Exception as e:
            print(f"API error for {area}: {e}")
            return []
    
    def format_precise_rules(self, rules_data, area):
        """Format rules with precise citations"""
        formatted_rules = []
        
        for rule_data in rules_data:
            if not rule_data.get('rule_type') or not rule_data.get('measurement_value'):
                continue
                
            # Build complete regulatory citation
            exact_sentence = rule_data.get('exact_regulatory_sentence', '')
            context_before = rule_data.get('context_before', '')
            context_after = rule_data.get('context_after', '')
            
            # Create full citation with context
            full_citation = ""
            if context_before:
                full_citation += context_before + " "
            full_citation += exact_sentence
            if context_after:
                full_citation += " " + context_after
            
            rule = {
                "rule_id": f"{area.upper()}_{rule_data['rule_type'].upper()}_PRECISE",
                "rule_text": exact_sentence,
                "rule_type": rule_data['rule_type'],
                "measurements": [{
                    "measurement_type": rule_data['rule_type'],
                    "value": float(rule_data['measurement_value']),
                    "unit": "metres",
                    "context": "precise extraction from document",
                    "confidence": rule_data.get('confidence', 0.9)
                }],
                "rule_classification": {
                    "tier": 1,
                    "enforcement_level": "MANDATORY",
                    "linguistic_confidence": rule_data.get('confidence', 0.9),
                    "compliance_message_type": "MUST_COMPLY"
                },
                "source_grounding": {
                    "extraction_text": full_citation,  # Complete citation with context
                    "source_location": rule_data.get('section_clause', f"{area} DCP"),
                    "confidence": rule_data.get('confidence', 0.9),
                    "exact_sentence": exact_sentence,  # The precise rule sentence
                    "measurement_context": full_citation  # Full context
                },
                "overall_confidence": rule_data.get('confidence', 0.9),
                "rule_complexity": "PRECISE_MEASUREMENT_EXTRACTED"
            }
            formatted_rules.append(rule)
        
        return formatted_rules

def process_areas_with_precise_citations():
    """Process areas with precise citation extraction"""
    print("PRECISE CITATION EXTRACTION")
    print("=" * 50)
    
    extractor = PreciseCitationExtractor()
    areas = ['Leichhardt', 'Ashfield']
    
    # Create output directories
    unified_dir = Path("public/regulatory-data/unified")
    unified_dir.mkdir(parents=True, exist_ok=True)
    
    unified_data = {}
    
    for area in areas:
        print(f"\nExtracting precise citations for {area}...")
        
        # Load document chunks
        temp_dir = Path(f"temp_extraction_{area}")
        if not temp_dir.exists():
            print(f"No chunks for {area}")
            continue
            
        # Combine text
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
            continue
            
        print(f"Processing {len(full_text)} characters from {chunk_count} chunks")
        
        # Extract precise rules
        rules = extractor.extract_precise_rules(full_text, area)
        
        if rules:
            print(f"Found {len(rules)} precise rules:")
            for rule in rules:
                print(f"  - {rule['rule_type']}: {rule['measurements'][0]['value']}m")
                print(f"    Citation: '{rule['source_grounding']['exact_sentence'][:80]}...'")
            
            # Save area data
            area_data = {
                "area": area,
                "document_path": f"docs/dcps/INNERWEST/{area}/",
                "enhanced_rules": rules,
                "processing_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "processors_used": ["OpenAI-GPT-4o-mini-PRECISE"],
                    "extraction_method": "precise_citation_extraction",
                    "documents_processed": chunk_count
                }
            }
            
            unified_data[area] = area_data
            
            # Save area file
            area_file = unified_dir / f"{area.lower()}_unified.json"
            with open(area_file, 'w') as f:
                json.dump(area_data, f, indent=2, default=str)
            print(f"Saved: {area_file}")
        else:
            print(f"No precise rules found for {area}")
    
    # Save master file
    if unified_data:
        unified_file = unified_dir / "unified_extraction.json"
        with open(unified_file, 'w') as f:
            json.dump(unified_data, f, indent=2, default=str)
        
        print(f"\\nSaved master: {unified_file}")
        
        total_rules = sum(len(area.get('enhanced_rules', [])) for area in unified_data.values())
        print(f"Total precise rules: {total_rules}")
        
        # Show examples
        print("\\nPRECISE CITATION EXAMPLES:")
        for area_name, area_data in unified_data.items():
            for rule in area_data.get('enhanced_rules', [])[:2]:  # Show first 2
                print(f"{area_name} - {rule['rule_type']}: {rule['measurements'][0]['value']}m")
                print(f"  Exact text: '{rule['source_grounding']['exact_sentence']}'")
                print(f"  Full context: '{rule['source_grounding']['extraction_text'][:150]}...'")
    
    return unified_data

if __name__ == "__main__":
    process_areas_with_precise_citations()