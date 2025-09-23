#!/usr/bin/env python3
"""
Enhanced Multimodal Extraction
==============================
Integrates LangExtract with RAG-Anything visual data to capture:
1. Non-clause regulatory text 
2. Visual diagrams and tables
3. Contextual information
4. Policy intent and character descriptions
"""

import json
import google.generativeai as genai
import os
import sqlite3
from dotenv import load_dotenv
from pathlib import Path

class EnhancedMultimodalExtraction:
 def __init__(self):
 load_dotenv('.env.local')
 api_key = os.getenv('GEMINI_API_KEY')
 genai.configure(api_key=api_key)
 self.model = genai.GenerativeModel('gemini-1.5-flash')
 
 # Load RAG-Anything visual data
 try:
 with open('unified_multimodal_relationships.json', 'r', encoding='utf-8', errors='ignore') as f:
 self.visual_data = json.load(f)
 print(f"Loaded visual data: {self.visual_data.get('statistics', {}).get('total_images', 0)} images")
 except:
 self.visual_data = {}
 print("No visual data available")

 def extract_comprehensive_content(self, doc_id, pdf_name, full_text):
 """Extract ALL content including non-clause text and visual elements"""
 
 # Get visual elements for this document
 visual_elements = self.get_visual_elements_for_doc(doc_id)
 
 prompt = f"""
COMPREHENSIVE REGULATORY CONTENT EXTRACTION

Document: {pdf_name}
Extract ALL regulatory content including formal clauses AND informal regulatory guidance.

EXTRACT THESE CATEGORIES:

1. FORMAL ENTITIES (as before):
 - Clauses, sections, zones, development standards, SEPPs, etc.

2. CONTEXTUAL INFORMATION (NEW):
 - Area character descriptions
 - Policy intent statements 
 - Design principles and guidance
 - Assessment considerations
 - Implementation notes

3. INFORMAL REGULATORY TEXT (NEW):
 - "Development should..." statements
 - "Buildings must respond to..." guidance
 - "Council will consider..." discretions
 - Character preservation objectives

4. MEASUREMENT CONTEXT (NEW):
 - References to tables or diagrams
 - Calculation methods
 - Measurement instructions
 - "As shown in Figure X" references

TEXT TO ANALYZE:
{full_text[:8000]}

VISUAL ELEMENTS AVAILABLE: {len(visual_elements)} elements

RETURN JSON:
{{
 "formal_entities": [
 {{
 "type": "zone|clause|sepp|standard",
 "reference": "exact reference",
 "text": "formal regulatory text",
 "category": "specific category"
 }}
 ],
 "contextual_information": [
 {{
 "type": "character_description|policy_intent|design_principle|assessment_guidance",
 "text": "descriptive or guidance text",
 "applies_to": "what area/situation this applies to",
 "regulatory_relevance": "how this informs formal controls"
 }}
 ],
 "informal_regulatory": [
 {{
 "type": "guidance|should_statement|discretion|objective",
 "text": "informal regulatory guidance",
 "strength": "should|must|may|preferred",
 "applies_to": "scope of application"
 }}
 ],
 "visual_references": [
 {{
 "text_reference": "As shown in Table 3",
 "description": "what the reference is about",
 "regulatory_significance": "why this visual element matters"
 }}
 ],
 "relationships": [
 {{
 "source": "entity A",
 "target": "entity B", 
 "type": "relationship type",
 "evidence": "supporting text"
 }}
 ]
}}
"""
 
 try:
 response = self.model.generate_content(prompt)
 
 if response and response.text:
 json_text = self.clean_json_response(response.text)
 data = json.loads(json_text)
 
 # Enhance with visual data
 enhanced_data = self.enhance_with_visual_data(data, visual_elements, doc_id)
 
 return enhanced_data
 
 except Exception as e:
 print(f"Extraction error: {e}")
 return {
 "formal_entities": [],
 "contextual_information": [],
 "informal_regulatory": [],
 "visual_references": [],
 "relationships": []
 }

 def get_visual_elements_for_doc(self, doc_id):
 """Get visual elements (images, tables) for this document"""
 visual_elements = []
 
 # Look for this document in RAG-Anything data
 if self.visual_data and 'documents' in self.visual_data:
 doc_data = self.visual_data['documents'].get(doc_id, {})
 content_sequence = doc_data.get('content_sequence', [])
 
 for item in content_sequence:
 if item.get('type') in ['image', 'table', 'diagram']:
 visual_elements.append({
 'type': item.get('type'),
 'description': item.get('text', ''),
 'page': item.get('page_idx', 0)
 })
 
 return visual_elements

 def enhance_with_visual_data(self, extracted_data, visual_elements, doc_id):
 """Enhance extracted data with visual element connections"""
 
 enhanced_data = extracted_data.copy()
 enhanced_data['visual_elements'] = []
 
 # Connect visual elements to regulatory content
 for visual in visual_elements:
 # Look for connections between visual elements and extracted entities
 connections = []
 
 for entity in extracted_data.get('formal_entities', []):
 entity_ref = entity.get('reference', '')
 # Simple matching - could be enhanced with more sophisticated NLP
 if entity_ref and (entity_ref in visual.get('description', '') or 
 any(word in visual.get('description', '').lower() 
 for word in entity_ref.lower().split())):
 connections.append(entity_ref)
 
 enhanced_data['visual_elements'].append({
 'type': visual.get('type'),
 'description': visual.get('description'),
 'page': visual.get('page', 0),
 'regulatory_connections': connections,
 'potential_measurements': self.extract_measurements_from_visual(visual)
 })
 
 return enhanced_data

 def extract_measurements_from_visual(self, visual_element):
 """Extract potential measurements from visual element descriptions"""
 import re
 
 description = visual_element.get('description', '')
 measurements = []
 
 # Look for common measurement patterns
 patterns = [
 r'(\d+(?:\.\d+)?)\s*m(?:etres?)?', # metres
 r'(\d+(?:\.\d+)?)\s*%', # percentages
 r'(\d+)\s*storeys?', # storeys
 r'(\d+(?:\.\d+)?)\s*spaces?', # parking spaces
 r'ratio\s*:?\s*(\d+(?:\.\d+)?)', # ratios
 ]
 
 for pattern in patterns:
 matches = re.findall(pattern, description, re.IGNORECASE)
 measurements.extend(matches)
 
 return measurements

 def clean_json_response(self, raw_response):
 """Clean JSON response (same as before)"""
 import re
 
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
 
 json_content = re.sub(r',\s*}', '}', json_content)
 json_content = re.sub(r',\s*]', ']', json_content)
 
 return json_content

def test_enhanced_extraction():
 """Test the enhanced multimodal extraction"""
 
 print("TESTING ENHANCED MULTIMODAL EXTRACTION")
 print("=" * 60)
 
 extractor = EnhancedMultimodalExtraction()
 
 # Get a test document
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 cursor.execute("""
 SELECT id, pdf_name, full_text
 FROM documents 
 WHERE char_count BETWEEN 10000 AND 30000
 AND full_text LIKE '%character%'
 LIMIT 1
 """)
 result = cursor.fetchone()
 conn.close()
 
 if result:
 doc_id, pdf_name, full_text = result
 print(f"Testing: {pdf_name}")
 
 extracted = extractor.extract_comprehensive_content(doc_id, pdf_name, full_text)
 
 print(f"\nRESULTS:")
 print(f"Formal entities: {len(extracted.get('formal_entities', []))}")
 print(f"Contextual info: {len(extracted.get('contextual_information', []))}")
 print(f"Informal regulatory: {len(extracted.get('informal_regulatory', []))}")
 print(f"Visual elements: {len(extracted.get('visual_elements', []))}")
 print(f"Relationships: {len(extracted.get('relationships', []))}")
 
 # Show samples
 if extracted.get('contextual_information'):
 print("\nSample contextual information:")
 for i, item in enumerate(extracted['contextual_information'][:3]):
 print(f" {i+1}. [{item.get('type')}] {item.get('text', '')[:80]}...")
 
 return True
 else:
 print("No test document found")
 return False

if __name__ == "__main__":
 success = test_enhanced_extraction()
 if success:
 print("\n[SUCCESS] Enhanced multimodal extraction working")
 else:
 print("\n[FAILED] Need to debug enhanced extraction")