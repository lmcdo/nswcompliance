#!/usr/bin/env python3
"""
Test LangExtract on Single Document with Real-Time Verification
==============================================================
Test the LangExtract methodology on ONE document to verify it works
before running on all 127 documents.
"""

import google.generativeai as genai
import json
import os
import re
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

def test_single_document_extraction():
    """Test LangExtract on one document with immediate verification"""
    
    print("TESTING LANGEXTRACT ON SINGLE DOCUMENT")
    print("=" * 50)
    print("This tests the methodology before running on all documents")
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
    
    # Get a sample document
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT pdf_name, full_text, char_count 
        FROM documents 
        WHERE char_count > 5000 AND char_count < 20000
        AND full_text LIKE '%setback%'
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
    
    # Take a manageable chunk (first 10,000 chars)
    test_chunk = full_text[:10000]
    
    # LangExtract prompt
    prompt = f"""
LANGEXTRACT REGULATORY PROVISION EXTRACTION - TEST

Extract specific regulatory provisions from this NSW planning document text.

CRITICAL REQUIREMENTS:
1. Extract ONLY actual regulatory clauses, controls, and requirements
2. Include exact clause numbers/references if present
3. Include specific measurements, setbacks, heights, ratios
4. Focus on actionable development controls
5. Return structured JSON format

Document: {pdf_name}
Text Chunk: TEST SAMPLE

TEXT TO ANALYZE:
{test_chunk}

OUTPUT FORMAT (JSON only):
{{
  "provisions": [
    {{
      "clause_reference": "Clause X.X.X or Section X.X",
      "provision_type": "height_limit|setback|fsr|parking|heritage|etc",
      "regulatory_text": "exact text from document",
      "specific_requirements": ["requirement 1", "requirement 2"],
      "measurements": "specific measurements if any",
      "applies_to": "what this applies to",
      "source_context": "surrounding context"
    }}
  ]
}}

Extract provisions now:"""
    
    print("CALLING GEMINI API...")
    print()
    
    try:
        # Generate with Gemini
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=2048,
                temperature=0.1,
                candidate_count=1
            )
        )
        
        if not response.text:
            print("ERROR: Empty response from API")
            return False
        
        print("GEMINI RESPONSE RECEIVED:")
        print("-" * 30)
        print(response.text[:500] + "...")
        print()
        
        # Clean and parse JSON
        json_text = clean_gemini_json_response(response.text)
        
        try:
            data = json.loads(json_text)
            
            if "provisions" not in data:
                print("ERROR: No 'provisions' key in response")
                return False
            
            provisions = data["provisions"]
            print(f"EXTRACTED {len(provisions)} PROVISIONS")
            print()
            
            # Verify each provision
            for i, prov in enumerate(provisions):
                print(f"PROVISION #{i+1} VERIFICATION:")
                print(f"  Clause: {prov.get('clause_reference', 'N/A')}")
                print(f"  Type: {prov.get('provision_type', 'N/A')}")  
                print(f"  Text: {prov.get('regulatory_text', 'N/A')[:100]}...")
                
                # IMMEDIATE VERIFICATION
                regulatory_text = prov.get('regulatory_text', '').strip()
                if regulatory_text and regulatory_text in test_chunk:
                    print(f"  VERIFIED: Text found in source")
                    
                    # Show context
                    pos = test_chunk.find(regulatory_text)
                    start = max(0, pos - 100)
                    end = min(len(test_chunk), pos + len(regulatory_text) + 100)
                    context = test_chunk[start:end]
                    
                    print(f"  SOURCE CONTEXT:")
                    print(f"  '{context}'")
                else:
                    print(f"  WARNING: Text not found in source - possible synthetic")
                
                print()
            
            # Save test result
            test_result = {
                "test_document": pdf_name,
                "test_timestamp": datetime.now().isoformat(),
                "provisions_extracted": len(provisions),
                "provisions": provisions,
                "source_chunk_size": len(test_chunk)
            }
            
            with open("langextract_single_test_result.json", "w", encoding="utf-8") as f:
                json.dump(test_result, f, indent=2, ensure_ascii=False)
            
            print("TEST COMPLETE!")
            print(f"Result saved to: langextract_single_test_result.json")
            print()
            print("If provisions are verified, the methodology works correctly.")
            print("If provisions are NOT verified, do NOT run on all documents.")
            
            return True
            
        except json.JSONDecodeError as e:
            print(f"ERROR: JSON parse failed: {e}")
            print("Raw response:")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"ERROR: API call failed: {e}")
        return False

def clean_gemini_json_response(raw_response: str) -> str:
    """Clean Gemini response to valid JSON"""
    
    # Remove markdown wrapper
    if '```json' in raw_response:
        match = re.search(r'```json\s*\n(.*?)\n```', raw_response, re.DOTALL)
        if match:
            json_content = match.group(1)
        else:
            json_content = raw_response
    else:
        json_content = raw_response
    
    # Extract JSON object
    json_content = json_content.strip()
    if '{' in json_content and '}' in json_content:
        start = json_content.find('{')
        end = json_content.rfind('}') + 1
        json_content = json_content[start:end]
    
    # Fix common issues
    json_content = re.sub(r',\s*}', '}', json_content)
    json_content = re.sub(r',\s*]', ']', json_content)
    
    return json_content

if __name__ == "__main__":
    success = test_single_document_extraction()
    if success:
        print("\n[SUCCESS] Single document test completed")
    else:
        print("\n[FAILED] Single document test failed")