#!/usr/bin/env python3
"""
Simple JSON Test
===============
"""

import google.generativeai as genai
import json
import os
import re
import sqlite3
from dotenv import load_dotenv

def test_simple_json():
    """Test with the actual failing document"""
    
    print("SIMPLE JSON TEST")
    print("=" * 30)
    
    # Setup
    load_dotenv('.env.local')
    api_key = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Get a document that SHOULD have content
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, pdf_name, full_text 
        FROM documents 
        WHERE full_text LIKE '%setback%' 
        AND full_text LIKE '%clause%'
        AND char_count > 10000
        LIMIT 1
    """)
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        print("Specific failing document not found")
        return False
    
    doc_id, pdf_name, full_text = result
    chunk = full_text[:6000]
    
    print(f"Testing EXACT failing document: {pdf_name}")
    print(f"Chunk: {len(chunk)} chars")
    print()
    
    # Simple prompt
    prompt = f"""
Extract regulatory provisions from this NSW planning document text.

TEXT:
{chunk}

Return JSON:
{{
  "entities": [
    {{"type": "clause", "reference": "4.2.3", "text": "sample"}}
  ],
  "relationships": [
    {{"source": "A", "target": "B", "type": "refers_to", "evidence": "text"}}
  ],
  "provisions": [
    {{"clause": "4.2.3", "type": "setback", "text": "text", "measurement": "6m"}}
  ]
}}
"""
    
    try:
        response = model.generate_content(prompt)
        
        if response and response.text:
            print("RAW RESPONSE:")
            print(response.text[:300] + "...")
            print()
            
            # Test the EXACT cleaning function from the pipeline
            cleaned = clean_json_pipeline(response.text)
            
            try:
                data = json.loads(cleaned)
                print("PARSING SUCCESS")
                print(f"Entities: {len(data.get('entities', []))}")
                print(f"Relationships: {len(data.get('relationships', []))}")  
                print(f"Provisions: {len(data.get('provisions', []))}")
                return True
                
            except json.JSONDecodeError as e:
                print(f"PARSING FAILED: {e}")
                print("Cleaned JSON:")
                print(cleaned[:200] + "...")
                
                # Show the exact error location
                if hasattr(e, 'pos') and e.pos:
                    start = max(0, e.pos - 20)
                    end = min(len(cleaned), e.pos + 20)
                    error_area = cleaned[start:end]
                    print(f"Error around position {e.pos}: '{error_area}'")
                
                return False
        else:
            print("EMPTY RESPONSE")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def clean_json_pipeline(raw_response):
    """EXACT same function as in monitored pipeline"""
    # Remove markdown
    if '```json' in raw_response:
        match = re.search(r'```json\s*\n(.*?)```', raw_response, re.DOTALL)
        if match:
            json_content = match.group(1)
        else:
            match = re.search(r'```json\s*\n(.*)', raw_response, re.DOTALL) 
            json_content = match.group(1) if match else raw_response
    else:
        json_content = raw_response
    
    json_content = json_content.strip()
    
    # Extract JSON object
    if '{' in json_content:
        start = json_content.find('{')
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
    
    # Fix common issues
    json_content = re.sub(r',\s*}', '}', json_content)
    json_content = re.sub(r',\s*]', ']', json_content)
    
    return json_content

if __name__ == "__main__":
    success = test_simple_json()
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")