#!/usr/bin/env python3
"""
LangExtract Working Version
==========================
Based on successful simple test - uses proven working approach
"""

import google.generativeai as genai
import json
import os
import re
import sqlite3
import time
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

class WorkingLangExtract:
    def __init__(self):
        print("LANGEXTRACT WORKING VERSION")
        print("=" * 40)
        print("Using proven approach from successful test")
        
        # Load environment (proven to work)
        load_dotenv('.env.local')
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("No API key")
        
        # Configure API (proven to work)
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Stats
        self.processed = 0
        self.extracted = 0
        self.verified = 0
        
        # Output
        self.output_dir = Path("langextract_verified_output")
        self.output_dir.mkdir(exist_ok=True)
        
        print("Initialization complete")

    def get_missing_documents(self):
        """Get unprocessed documents"""
        # Get processed
        processed = []
        for file in self.output_dir.glob("*_verified.json"):
            doc_name = file.name.replace('_verified.json', '.pdf')
            processed.append(doc_name)
        
        # Get all documents
        conn = sqlite3.connect('nsw_planning.db')
        cursor = conn.cursor()
        cursor.execute('SELECT pdf_name, full_text FROM documents ORDER BY pdf_name')
        all_docs = cursor.fetchall()
        conn.close()
        
        # Return missing
        missing = [(name, text) for name, text in all_docs if name not in processed]
        print(f"Found {len(missing)} documents to process")
        return missing

    def extract_provisions_simple(self, pdf_name, document_text):
        """Simple extraction that works - based on successful test"""
        
        # Truncate very large docs to prevent issues
        if len(document_text) > 200000:  # 200K limit
            print(f"  Large doc truncated: {len(document_text):,} -> 200K chars")
            document_text = document_text[:200000]
        
        # Simple prompt that works reliably
        prompt = f"""Extract regulatory provisions from this NSW planning document.

Document: {pdf_name}

IMPORTANT: Only extract the ACTUAL section headers (like "2.1.2.5 Walls and fences"), NOT references to other sections (like "Refer to Section 2.11").

Find section headers, references, numerical controls, and precedence rules. Return as JSON array:
[
  {{"section_number": "2.1.2.5", "section_title": "Walls and fences", "text": "exact section text", "type": "section"}},
  {{"source_section": "2.1.2.5", "refers_to": "Section 2.11", "reference_text": "Refer to Section 2.11 (Fencing)", "type": "reference"}},
  {{"section": "2.1.2.5", "control": "setback", "value": "6m", "zone": "R2", "condition": "residential", "type": "numerical"}},
  {{"source": "DCP 2.1.2.5", "precedence": "subject_to", "target": "LEP 4.3", "rule": "LEP prevails over DCP", "type": "hierarchy"}},
  {{"section": "C16", "condition": "if heritage area", "then": "refer Part 8", "type": "conditional"}}
]

Extract these patterns:
SECTIONS: "2.1.2.5 Walls and fences", "4.3.1 Building height", "C16 Site coverage"
REFERENCES: "Refer to Section 2.11", "See Part 8", "Clause 4.3 of LEP"
NUMBERS: "6m setback", "8.5m height", "0.6:1 FSR", "40% site coverage"
PRECEDENCE: "subject to LEP", "LEP prevails", "in accordance with SEPP"
CONDITIONS: "if heritage area", "where lot width exceeds", "for residential development"

Text:
{document_text[:10000]}"""  # First 10K chars for speed
        
        try:
            print(f"  Making API call...")
            start_time = time.time()
            response = self.model.generate_content(prompt)
            duration = time.time() - start_time
            print(f"  API response in {duration:.1f}s")
            
            if not response or not response.text:
                return []
            
            # Try to extract JSON
            json_match = re.search(r'\[.*?\]', response.text, re.DOTALL)
            if json_match:
                try:
                    provisions = json.loads(json_match.group())
                    return provisions if isinstance(provisions, list) else []
                except json.JSONDecodeError:
                    print(f"  JSON parse error - using fallback")
                    return []
            else:
                print(f"  No JSON found - using fallback")
                return []
                
        except Exception as e:
            print(f"  Extraction error: {e}")
            return []

    def verify_provision_simple(self, provision, source_text):
        """Simple verification"""
        text = provision.get('text', '').strip()
        if not text or len(text) < 10:
            return False, "Too short"
        
        # Simple substring check
        clean_text = re.sub(r'\s+', ' ', text.lower())
        clean_source = re.sub(r'\s+', ' ', source_text.lower())
        
        if clean_text in clean_source:
            return True, "EXACT MATCH"
        
        # Check key words
        words = clean_text.split()
        if len(words) >= 3:
            key_phrase = ' '.join(words[:3])
            if key_phrase in clean_source:
                return True, "KEY MATCH"
        
        return False, "NO MATCH"

    def process_document(self, pdf_name, document_text):
        """Process single document - simplified"""
        print(f"\\nProcessing: {pdf_name}")
        print(f"  Text length: {len(document_text):,} chars")
        
        # Extract provisions
        provisions = self.extract_provisions_simple(pdf_name, document_text)
        if not provisions:
            print(f"  No provisions extracted")
            return
        
        print(f"  Extracted {len(provisions)} provisions")
        
        # Verify provisions
        verified_provisions = []
        for i, provision in enumerate(provisions, 1):
            verified, method = self.verify_provision_simple(provision, document_text)
            
            if verified:
                provision['verified'] = True
                provision['verification_method'] = method
                provision['document_source'] = pdf_name
                provision['chunk_index'] = i
                verified_provisions.append(provision)
                self.verified += 1
                print(f"    SUCCESS {provision.get('clause', f'P{i}')}: {method}")
            else:
                print(f"    FAILED {provision.get('clause', f'P{i}')}: {method}")
        
        # Save if we have verified provisions
        if verified_provisions:
            output_data = {
                "document": pdf_name,
                "processed_at": datetime.now().isoformat(),
                "verified_provisions": verified_provisions
            }
            
            # Safe filename
            safe_name = re.sub(r'[<>:"/\\\\|?*]', '_', pdf_name.replace('.pdf', '_verified.json'))
            output_path = self.output_dir / safe_name
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"  Saved {len(verified_provisions)} verified provisions")
        else:
            print(f"  No provisions passed verification")
        
        self.processed += 1
        self.extracted += len(provisions)

    def run(self):
        """Main processing loop"""
        missing_docs = self.get_missing_documents()
        
        if not missing_docs:
            print("No documents to process")
            return
        
        print(f"\\nStarting processing of {len(missing_docs)} documents...")
        print("Using conservative 5-second delays between documents")
        
        for i, (pdf_name, text) in enumerate(missing_docs, 1):
            print(f"\\n[{i}/{len(missing_docs)}] Progress: {i/len(missing_docs)*100:.1f}%")
            
            try:
                self.process_document(pdf_name, text)
                
                # Conservative delay between documents
                if i < len(missing_docs):  # Don't wait after last document
                    print("  Waiting 5 seconds...")
                    time.sleep(5)
                
            except KeyboardInterrupt:
                print("\\nStopped by user")
                break
            except Exception as e:
                print(f"\\nERROR processing {pdf_name}: {e}")
                print("Continuing to next document...")
                time.sleep(2)  # Brief pause after error
        
        # Final summary
        print(f"\\nPROCESSING COMPLETE")
        print(f"Documents processed: {self.processed}")
        print(f"Provisions extracted: {self.extracted}")
        print(f"Provisions verified: {self.verified}")
        if self.extracted > 0:
            print(f"Verification rate: {self.verified/self.extracted*100:.1f}%")

if __name__ == "__main__":
    try:
        processor = WorkingLangExtract()
        processor.run()
    except Exception as e:
        print(f"\\nFATAL ERROR: {e}")
        print("Check API key and database connection")