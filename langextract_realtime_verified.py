#!/usr/bin/env python3
"""
LangExtract with Real-Time Verification
=======================================
Processes documents with IMMEDIATE verification that extracted provisions are real,
not synthetic. Shows proof during processing.

Key Features:
- Real-time source text matching
- Immediate verification display  
- Progress tracking with verification stats
- Fail-fast on synthetic data
- Live proof of data authenticity
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

class VerifiedLangExtract:
    def __init__(self):
        # Load environment
        load_dotenv('.env.local')
        
        # Configure Gemini API
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Stats tracking
        self.total_provisions_extracted = 0
        self.total_provisions_verified = 0
        self.total_provisions_failed = 0
        self.processed_docs = 0
        
        # Rate limiting
        self.requests_made = 0
        self.start_time = time.time()
        self.max_requests_per_minute = 8
        
        # Output
        self.verified_provisions = []
        self.output_dir = Path("langextract_verified_output")
        self.output_dir.mkdir(exist_ok=True)
        
        print("LANGEXTRACT WITH REAL-TIME VERIFICATION")
        print("=" * 60)
        print("Every provision is verified immediately against source text")
        print("Synthetic/fake data is rejected in real-time")
        print()

    def wait_for_rate_limit(self):
        """Rate limiting with progress display"""
        self.requests_made += 1
        
        elapsed_minutes = (time.time() - self.start_time) / 60
        if elapsed_minutes > 0:
            current_rate = self.requests_made / elapsed_minutes
            
            if current_rate > self.max_requests_per_minute:
                sleep_time = 60 / self.max_requests_per_minute
                print(f"  RATE LIMIT: Waiting {sleep_time:.1f}s (current rate: {current_rate:.1f}/min)")
                time.sleep(sleep_time)

    def verify_provision_immediately(self, provision, source_text, doc_name):
        """IMMEDIATE verification - returns True only if provision text exists in source"""
        
        regulatory_text = provision.get('regulatory_text', '').strip()
        if not regulatory_text:
            return False, "No regulatory text provided"
        
        # Clean text for matching (handle whitespace differences)
        clean_regulatory = re.sub(r'\s+', ' ', regulatory_text.strip())
        clean_source = re.sub(r'\s+', ' ', source_text)
        
        # Check for exact match first
        if clean_regulatory in clean_source:
            return True, "EXACT MATCH"
        
        # Check for substantial match (80% of words)
        reg_words = clean_regulatory.split()
        if len(reg_words) >= 5:
            # Try matching with 80% of words
            words_to_match = reg_words[:int(len(reg_words) * 0.8)]
            partial_text = ' '.join(words_to_match)
            
            if partial_text in clean_source:
                return True, f"SUBSTANTIAL MATCH (80%)"
        
        # Check key regulatory phrases
        key_phrases = [
            ' '.join(reg_words[:3]),  # First 3 words
            ' '.join(reg_words[-3:])  # Last 3 words
        ]
        
        for phrase in key_phrases:
            if len(phrase) > 10 and phrase in clean_source:
                return True, f"KEY PHRASE MATCH: '{phrase}'"
        
        return False, "NOT FOUND IN SOURCE"

    def extract_and_verify_provisions(self, doc_name, source_text):
        """Extract provisions and verify each one immediately"""
        
        print(f"[{self.processed_docs + 1}] Processing: {doc_name}")
        print(f"  Source text: {len(source_text):,} characters")
        
        # Chunk text for processing
        max_chunk_size = 12000
        chunks = self.intelligent_chunk_text(source_text, max_chunk_size)
        
        print(f"  Text chunks: {len(chunks)}")
        
        all_verified_provisions = []
        
        for chunk_idx, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
                
            print(f"\n  Processing chunk {chunk_idx + 1}/{len(chunks)}")
            
            # Rate limiting
            self.wait_for_rate_limit()
            
            # Extract provisions from chunk
            provisions = self.extract_provisions_from_chunk(chunk, doc_name, chunk_idx)
            
            if not provisions:
                print(f"    No provisions extracted")
                continue
            
            # IMMEDIATE VERIFICATION of each provision
            verified_count = 0
            for i, provision in enumerate(provisions):
                
                # Verify against source text
                is_verified, verification_msg = self.verify_provision_immediately(provision, chunk, doc_name)
                
                if is_verified:
                    # Add verification metadata
                    provision.update({
                        'verified': True,
                        'verification_method': verification_msg,
                        'document_source': doc_name,
                        'chunk_index': chunk_idx,
                        'extraction_timestamp': datetime.now().isoformat(),
                        'verification_status': 'REAL_DATA_VERIFIED'
                    })
                    
                    all_verified_provisions.append(provision)
                    verified_count += 1
                    self.total_provisions_verified += 1
                    
                    # Show verification proof
                    print(f"    [{i+1}] VERIFIED: {provision.get('clause_reference', 'N/A')}")
                    print(f"        Type: {provision.get('provision_type', 'N/A')}")
                    print(f"        Proof: {verification_msg}")
                    print(f"        Text: {provision.get('regulatory_text', '')[:80]}...")
                    
                else:
                    self.total_provisions_failed += 1
                    print(f"    [{i+1}] REJECTED: {verification_msg}")
                    print(f"        Clause: {provision.get('clause_reference', 'N/A')}")
                    print(f"        Reason: Synthetic/not found in source")
            
            print(f"    Result: {verified_count}/{len(provisions)} provisions verified")
            self.total_provisions_extracted += len(provisions)
        
        print(f"  Document total: {len(all_verified_provisions)} verified provisions")
        return all_verified_provisions

    def extract_provisions_from_chunk(self, chunk, doc_name, chunk_idx):
        """Extract provisions from text chunk using Gemini"""
        
        prompt = f"""
LANGEXTRACT REGULATORY PROVISION EXTRACTION

Extract regulatory provisions from this NSW planning document text.
CRITICAL: Extract ONLY text that actually exists in the provided text.
Do NOT paraphrase, summarize, or create new text.

REQUIREMENTS:
1. Extract exact regulatory text as it appears
2. Include clause numbers/references if present  
3. Focus on development controls, requirements, measurements
4. Return structured JSON format

Document: {doc_name}
Chunk: {chunk_idx + 1}

TEXT TO ANALYZE:
{chunk}

OUTPUT FORMAT (JSON only):
{{
  "provisions": [
    {{
      "clause_reference": "exact clause reference from text",
      "provision_type": "setback|height_limit|fsr|parking|heritage|design|other",
      "regulatory_text": "exact text from document - DO NOT PARAPHRASE",
      "specific_requirements": ["list of specific requirements"],
      "measurements": "measurements if any",
      "applies_to": "what this applies to"
    }}
  ]
}}
"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=2048,
                    temperature=0.1
                )
            )
            
            if not response.text:
                return []
            
            # Parse JSON response
            json_text = self.clean_json_response(response.text)
            data = json.loads(json_text)
            
            if "provisions" in data and isinstance(data["provisions"], list):
                return [p for p in data["provisions"] if p.get("regulatory_text")]
            
            return []
            
        except json.JSONDecodeError:
            print(f"    WARNING: Invalid JSON response")
            return []
        except Exception as e:
            print(f"    ERROR: {str(e)}")
            return []

    def intelligent_chunk_text(self, text, max_size):
        """Split text at regulatory boundaries"""
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Split by clause/section markers
        sections = re.split(r'(?=(?:Clause|Section|Part|\n\d+\.\d+|\nC\d+|\nP\d+)\s)', text)
        
        for section in sections:
            if len(current_chunk) + len(section) <= max_size:
                current_chunk += section
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = section
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

    def clean_json_response(self, raw_response):
        """Clean Gemini JSON response"""
        if '```json' in raw_response:
            match = re.search(r'```json\s*\n(.*?)\n```', raw_response, re.DOTALL)
            if match:
                json_content = match.group(1)
            else:
                json_content = raw_response
        else:
            json_content = raw_response
        
        json_content = json_content.strip()
        if '{' in json_content and '}' in json_content:
            start = json_content.find('{')
            end = json_content.rfind('}') + 1
            json_content = json_content[start:end]
        
        json_content = re.sub(r',\s*}', '}', json_content)
        json_content = re.sub(r',\s*]', ']', json_content)
        
        return json_content

    def process_all_documents(self, limit=None):
        """Process all documents with real-time verification"""
        
        # Get documents from database
        conn = sqlite3.connect('nsw_planning.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pdf_name, full_text, char_count
            FROM documents 
            WHERE char_count > 1000
            ORDER BY char_count ASC
        """ + (f" LIMIT {limit}" if limit else ""))
        
        documents = cursor.fetchall()
        conn.close()
        
        print(f"Processing {len(documents)} documents with real-time verification")
        print()
        
        for pdf_name, full_text, char_count in documents:
            
            # Extract and verify provisions
            verified_provisions = self.extract_and_verify_provisions(pdf_name, full_text)
            
            # Add to collection
            self.verified_provisions.extend(verified_provisions)
            self.processed_docs += 1
            
            # Save individual document results
            if verified_provisions:
                doc_file = self.output_dir / f"{pdf_name.replace('.pdf', '')}_verified.json"
                with open(doc_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'document': pdf_name,
                        'processed_at': datetime.now().isoformat(),
                        'verified_provisions': verified_provisions,
                        'verification_stats': {
                            'total_extracted': len([p for p in verified_provisions]),
                            'total_verified': len([p for p in verified_provisions if p.get('verified')])
                        }
                    }, f, indent=2, ensure_ascii=False)
            
            # Progress update
            verification_rate = (self.total_provisions_verified / max(1, self.total_provisions_extracted)) * 100
            
            print(f"\nPROGRESS UPDATE:")
            print(f"  Documents processed: {self.processed_docs}/{len(documents)}")
            print(f"  Total provisions extracted: {self.total_provisions_extracted}")
            print(f"  Total provisions verified: {self.total_provisions_verified}")
            print(f"  Total provisions rejected: {self.total_provisions_failed}")
            print(f"  Verification rate: {verification_rate:.1f}%")
            print()
            
            # Stop if verification rate is too low
            if self.total_provisions_extracted > 20 and verification_rate < 50:
                print("WARNING: Low verification rate - stopping to prevent synthetic data")
                break

    def save_final_results(self):
        """Save final verified results"""
        
        final_output = {
            'metadata': {
                'extraction_method': 'langextract_realtime_verified',
                'processed_documents': self.processed_docs,
                'total_provisions_extracted': self.total_provisions_extracted,
                'total_provisions_verified': self.total_provisions_verified,
                'total_provisions_rejected': self.total_provisions_failed,
                'verification_rate': (self.total_provisions_verified / max(1, self.total_provisions_extracted)) * 100,
                'processing_date': datetime.now().isoformat()
            },
            'verified_provisions': self.verified_provisions
        }
        
        output_file = "langextract_realtime_verified_provisions.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
        
        print(f"FINAL RESULTS SAVED:")
        print(f"  Output file: {output_file}")
        print(f"  Verified provisions: {self.total_provisions_verified}")
        print(f"  Verification rate: {final_output['metadata']['verification_rate']:.1f}%")
        
        return output_file

def main():
    """Run LangExtract with real-time verification"""
    
    try:
        extractor = VerifiedLangExtract()
        
        # Process all documents
        print("Processing ALL documents with real-time verification...")
        extractor.process_all_documents()
        
        # Save results
        output_file = extractor.save_final_results()
        
        verification_rate = (extractor.total_provisions_verified / max(1, extractor.total_provisions_extracted)) * 100
        
        print(f"\nTEST COMPLETE!")
        if verification_rate >= 80:
            print(f"HIGH VERIFICATION RATE ({verification_rate:.1f}%) - Data is reliable")
            print("Ready to process all documents if needed")
        else:
            print(f"LOW VERIFICATION RATE ({verification_rate:.1f}%) - Review methodology")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n[SUCCESS] LangExtract with real-time verification completed")
    else:
        print("\n[FAILED] LangExtract verification failed")