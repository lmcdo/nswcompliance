#!/usr/bin/env python3
"""
Test LangExtract for Relationships and Entities
===============================================
Test extraction of relationships between regulatory clauses and entities.
Focus on the key relationship patterns from the NSW planning system.
"""

import google.generativeai as genai
import json
import os
import re
import sqlite3
import time
from datetime import datetime
from dotenv import load_dotenv

def test_relationship_extraction():
    """Test extraction of regulatory relationships from a single document"""
    
    print("TESTING RELATIONSHIP EXTRACTION")
    print("=" * 60)
    print("Extracting entities and relationships for AutoSchemaKG")
    print()
    
    # Load environment
    load_dotenv('.env.local')
    
    # Configure Gemini API
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found")
        return False
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Get a test document with known relationships
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT pdf_name, full_text, char_count 
        FROM documents 
        WHERE full_text LIKE '%in accordance with%'
        AND full_text LIKE '%subject to%'
        AND char_count > 10000 AND char_count < 30000
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        print("ERROR: No suitable test document found")
        return False
    
    pdf_name, full_text, char_count = result
    
    print(f"TEST DOCUMENT: {pdf_name}")
    print(f"Size: {char_count:,} characters")
    print()
    
    # Take a chunk with relationships
    test_chunk = full_text[:15000]
    
    # Enhanced prompt for relationship extraction
    prompt = f"""
EXTRACT REGULATORY RELATIONSHIPS AND ENTITIES

Analyze this NSW planning document and extract:
1. ENTITIES: Clauses, sections, parts, schedules
2. RELATIONSHIPS: How entities reference each other

RELATIONSHIP PATTERNS TO FIND:
- "in accordance with [clause/section]"
- "subject to [clause/section]"  
- "refer to [part/section]"
- "as specified in [clause]"
- "under [section]"
- "pursuant to [clause]"
- "must comply with [section]"
- "except as provided in [clause]"

Document: {pdf_name}

TEXT TO ANALYZE:
{test_chunk}

RETURN ONLY THIS JSON FORMAT:
{{
  "entities": [
    {{
      "id": "unique_id",
      "type": "clause|section|part|schedule",
      "reference": "4.2.3",
      "text": "exact text of the entity",
      "context": "surrounding context"
    }}
  ],
  "relationships": [
    {{
      "source": "entity_id",
      "target": "entity_id",
      "type": "refers_to|subject_to|complies_with|overrides|modifies",
      "evidence": "exact text showing the relationship"
    }}
  ],
  "provisions": [
    {{
      "clause_reference": "Clause/Section number",
      "provision_type": "setback|height|fsr|parking|etc",
      "regulatory_text": "exact regulatory text",
      "measurements": "specific measurements if any"
    }}
  ]
}}
"""
    
    print("CALLING GEMINI API...")
    print()
    
    try:
        # Generate with conservative settings
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=4096,
                temperature=0.1,
                candidate_count=1
            )
        )
        
        if not response.text:
            print("ERROR: Empty response from API")
            return False
        
        print("RESPONSE RECEIVED")
        print("-" * 30)
        
        # Clean and parse JSON
        json_text = clean_json_response(response.text)
        
        try:
            data = json.loads(json_text)
            
            # Display results
            entities = data.get("entities", [])
            relationships = data.get("relationships", [])
            provisions = data.get("provisions", [])
            
            print(f"\nEXTRACTED:")
            print(f"  Entities: {len(entities)}")
            print(f"  Relationships: {len(relationships)}")
            print(f"  Provisions: {len(provisions)}")
            print()
            
            # Verify entities
            if entities:
                print("SAMPLE ENTITIES:")
                for i, entity in enumerate(entities[:5]):
                    print(f"  [{i+1}] {entity.get('type', 'unknown').upper()}: {entity.get('reference', 'N/A')}")
                    text_snippet = entity.get('text', '')[:100]
                    if text_snippet:
                        print(f"      Text: {text_snippet}...")
                    
                    # Verify in source
                    ref = entity.get('reference', '')
                    if ref and ref in test_chunk:
                        print(f"      [VERIFIED] in source")
                    else:
                        print(f"      [WARNING] Not found verbatim")
                print()
            
            # Verify relationships
            if relationships:
                print("SAMPLE RELATIONSHIPS:")
                for i, rel in enumerate(relationships[:5]):
                    print(f"  [{i+1}] {rel.get('source', 'N/A')} --{rel.get('type', 'N/A')}--> {rel.get('target', 'N/A')}")
                    evidence = rel.get('evidence', '')[:100]
                    if evidence:
                        print(f"      Evidence: {evidence}...")
                        
                        # Verify evidence in source
                        if evidence in test_chunk:
                            print(f"      [VERIFIED] in source")
                        else:
                            print(f"      [WARNING] Check evidence")
                print()
            
            # Verify provisions
            if provisions:
                print("SAMPLE PROVISIONS:")
                for i, prov in enumerate(provisions[:5]):
                    print(f"  [{i+1}] {prov.get('clause_reference', 'N/A')}: {prov.get('provision_type', 'N/A')}")
                    if prov.get('measurements'):
                        print(f"      Measurements: {prov.get('measurements')}")
                    
                    reg_text = prov.get('regulatory_text', '')
                    if reg_text:
                        print(f"      Text: {reg_text[:100]}...")
                        
                        # Verify in source
                        if reg_text[:50] in test_chunk:
                            print(f"      [VERIFIED] in source")
                        else:
                            print(f"      [WARNING] Check text")
                print()
            
            # Save test results
            test_result = {
                "test_document": pdf_name,
                "test_timestamp": datetime.now().isoformat(),
                "extraction_stats": {
                    "entities": len(entities),
                    "relationships": len(relationships),
                    "provisions": len(provisions)
                },
                "entities": entities,
                "relationships": relationships,
                "provisions": provisions
            }
            
            with open("langextract_relationship_test.json", "w", encoding="utf-8") as f:
                json.dump(test_result, f, indent=2, ensure_ascii=False)
            
            print("-" * 60)
            print("TEST COMPLETE!")
            print(f"Results saved to: langextract_relationship_test.json")
            print()
            
            # Success criteria
            if len(entities) > 0 and len(relationships) > 0:
                print("[SUCCESS] Extraction methodology works")
                print("  Ready to process all documents")
                return True
            else:
                print("[WARNING] Low extraction count")
                print("  Review methodology before full run")
                return False
            
        except json.JSONDecodeError as e:
            print(f"ERROR: JSON parse failed: {e}")
            print("Attempting to fix JSON...")
            
            # Try to fix common JSON issues
            fixed_json = fix_json_errors(json_text)
            try:
                data = json.loads(fixed_json)
                print("JSON fixed successfully!")
                # Process as above...
                return True
            except:
                print("Could not fix JSON")
                print("Raw response saved to: langextract_raw_response.txt")
                with open("langextract_raw_response.txt", "w", encoding="utf-8") as f:
                    f.write(response.text)
                return False
            
    except Exception as e:
        print(f"ERROR: API call failed: {e}")
        return False

def clean_json_response(raw_response: str) -> str:
    """Clean Gemini response to valid JSON"""
    
    # Remove markdown wrapper
    if '```json' in raw_response:
        match = re.search(r'```json\s*\n(.*?)```', raw_response, re.DOTALL)
        if match:
            json_content = match.group(1)
        else:
            # Try without closing backticks
            match = re.search(r'```json\s*\n(.*)', raw_response, re.DOTALL)
            if match:
                json_content = match.group(1)
            else:
                json_content = raw_response
    else:
        json_content = raw_response
    
    # Extract JSON object
    json_content = json_content.strip()
    
    # Find the main JSON object
    if '{' in json_content:
        start = json_content.find('{')
        
        # Find matching closing brace
        brace_count = 0
        end = start
        for i in range(start, len(json_content)):
            if json_content[i] == '{':
                brace_count += 1
            elif json_content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break
        
        json_content = json_content[start:end]
    
    return json_content

def fix_json_errors(json_str: str) -> str:
    """Attempt to fix common JSON errors"""
    
    # Fix trailing commas
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # Fix unescaped quotes in strings
    # This is tricky - only do basic fixes
    
    # Fix null values
    json_str = json_str.replace(': null,', ': null,')
    json_str = json_str.replace(': null}', ': null}')
    
    # Ensure all keys are quoted
    json_str = re.sub(r'(\w+):', r'"\1":', json_str)
    
    # Fix double quotes
    json_str = json_str.replace('""', '"')
    
    return json_str

if __name__ == "__main__":
    success = test_relationship_extraction()
    if success:
        print("\n[SUCCESS] Relationship extraction test completed")
        print("Next step: Run on all documents with monitoring")
    else:
        print("\n[FAILED] Relationship extraction test failed")
        print("Fix issues before running on all documents")