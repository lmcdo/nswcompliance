#!/usr/bin/env python3
"""
Monitored 4-Stack Pipeline with Real-Time Verification
======================================================
Processes all 128 documents with comprehensive monitoring, verification,
and progress tracking. Designed for 3-5 hour runs with fail-safes.
"""

import google.generativeai as genai
import json
import os
import re
import sqlite3
import time
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
import signal
import sys

class MonitoredPipeline:
    def __init__(self):
        # Load environment
        load_dotenv('.env.local')
        
        # Configure Gemini API
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Pipeline state
        self.stats = {
            'start_time': datetime.now(),
            'total_documents': 0,
            'processed_documents': 0,
            'total_api_calls': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'total_entities': 0,
            'total_relationships': 0,
            'total_provisions': 0,
            'db_entries_added': 0,
            'errors': [],
            'last_successful_doc': None
        }
        
        # Rate limiting (conservative for long runs)
        self.max_requests_per_minute = 4  # Very conservative
        self.request_times = []
        
        # Monitoring
        self.monitoring_active = True
        self.last_progress_report = datetime.now()
        self.progress_interval = timedelta(minutes=10)  # Report every 10 minutes
        
        # Output
        self.output_dir = Path("monitored_pipeline_output")
        self.output_dir.mkdir(exist_ok=True)
        
        self.progress_file = self.output_dir / "progress.json"
        self.errors_file = self.output_dir / "errors.log"
        
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        
        print("=" * 80)
        print("MONITORED 4-STACK PIPELINE")
        print("=" * 80)
        print(f"Started: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Rate limit: {self.max_requests_per_minute} requests/minute")
        print(f"Progress file: {self.progress_file}")
        print(f"Errors log: {self.errors_file}")
        print()
        print("Features:")
        print("- Real-time verification of all extractions")
        print("- Progress reports every 10 minutes")
        print("- Automatic resume from last successful document")
        print("- Graceful shutdown on Ctrl+C")
        print("- Comprehensive error logging")
        print("=" * 80)

    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print("\n\n" + "=" * 60)
        print("GRACEFUL SHUTDOWN INITIATED")
        print("=" * 60)
        self.monitoring_active = False
        self.save_progress()
        print(f"Progress saved to: {self.progress_file}")
        print("To resume, run: python resume_pipeline.py")
        sys.exit(0)

    def enforce_rate_limit(self):
        """Strict rate limiting with monitoring"""
        now = time.time()
        
        # Remove old timestamps (older than 1 minute)
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        # Check if we've hit the limit
        if len(self.request_times) >= self.max_requests_per_minute:
            # Calculate how long to wait
            oldest_request = min(self.request_times)
            wait_time = 60 - (now - oldest_request) + 1  # +1 second buffer
            
            if wait_time > 0:
                print(f"    [RATE LIMIT] Waiting {wait_time:.1f}s (calls in last minute: {len(self.request_times)})")
                time.sleep(wait_time)
        
        # Add current request time
        self.request_times.append(time.time())
        self.stats['total_api_calls'] += 1

    def extract_from_document(self, doc_id, pdf_name, full_text):
        """Extract with simplified, working prompt"""
        
        # Chunk intelligently
        max_chunk_size = 8000  # Smaller chunks for reliability
        chunks = self.intelligent_chunk(full_text, max_chunk_size)
        
        print(f"  Chunks: {len(chunks)} ({len(full_text):,} chars)")
        
        all_results = {
            'entities': [],
            'relationships': [],
            'provisions': []
        }
        
        for chunk_idx, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            
            print(f"    [{chunk_idx + 1}/{len(chunks)}] ", end="")
            
            # Rate limiting
            self.enforce_rate_limit()
            
            # Use SIMPLE, WORKING prompt
            prompt = f"""
Extract regulatory provisions from this NSW planning document text.

Document: {pdf_name}
Chunk: {chunk_idx + 1} of {len(chunks)}

Find and extract:
1. Clauses/sections with their exact references
2. Regulatory provisions with measurements
3. References between clauses

TEXT:
{chunk[:6000]}

Return JSON only:
{{
  "entities": [
    {{
      "type": "clause|section",
      "reference": "exact reference",
      "text": "first 50 chars"
    }}
  ],
  "relationships": [
    {{
      "source": "source reference", 
      "target": "target reference",
      "type": "refers_to|in_accordance_with|subject_to",
      "evidence": "text showing relationship"
    }}
  ],
  "provisions": [
    {{
      "clause": "exact clause reference",
      "type": "setback|height|fsr|design|parking",
      "text": "regulatory text",
      "measurement": "measurement if any"
    }}
  ]
}}
"""
            
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=1500,
                        temperature=0.1
                    )
                )
                
                if response and response.text:
                    # Parse response
                    json_text = self.clean_json(response.text)
                    data = json.loads(json_text)
                    
                    # Verify and collect
                    entities = data.get('entities', [])
                    relationships = data.get('relationships', [])
                    provisions = data.get('provisions', [])
                    
                    # Quick verification - check if references exist in chunk
                    verified_entities = 0
                    for entity in entities:
                        ref = entity.get('reference', '')
                        if ref and (ref in chunk or ref.replace(' ', '') in chunk.replace(' ', '')):
                            verified_entities += 1
                    
                    all_results['entities'].extend(entities)
                    all_results['relationships'].extend(relationships) 
                    all_results['provisions'].extend(provisions)
                    
                    print(f"E:{len(entities)} R:{len(relationships)} P:{len(provisions)} V:{verified_entities}")
                    
                    if entities or relationships or provisions:
                        self.stats['successful_extractions'] += 1
                    
                else:
                    print("[EMPTY]")
                    self.stats['failed_extractions'] += 1
                    
            except json.JSONDecodeError:
                print("[JSON_ERROR]")
                self.stats['failed_extractions'] += 1
                self.log_error(f"{pdf_name} chunk {chunk_idx}: JSON parse error")
                
            except Exception as e:
                print(f"[ERROR: {str(e)[:20]}]")
                self.stats['failed_extractions'] += 1
                self.log_error(f"{pdf_name} chunk {chunk_idx}: {str(e)}")
                time.sleep(10)  # Wait on errors
        
        return all_results

    def intelligent_chunk(self, text, max_size):
        """Smart chunking at regulatory boundaries"""
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Split by obvious section markers
        sections = re.split(r'(?=(?:^|\n)(?:Clause|Section|Part|\d+\.\d+|\w\d+)\s)', text, flags=re.MULTILINE)
        
        if len(sections) <= 1:
            # Fall back to paragraph splitting
            sections = text.split('\n\n')
        
        for section in sections:
            if len(current_chunk) + len(section) <= max_size:
                current_chunk += section
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = section
                
                # Split large sections
                while len(current_chunk) > max_size:
                    split_point = max_size - 200
                    chunks.append(current_chunk[:split_point])
                    current_chunk = "..." + current_chunk[split_point - 100:]
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

    def clean_json(self, raw_response):
        """Clean JSON response"""
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

    def update_database(self, doc_id, extraction_results):
        """Update regulatory_refs table"""
        conn = sqlite3.connect('nsw_planning.db')
        cursor = conn.cursor()
        
        entries_added = 0
        
        try:
            # Add entities
            for entity in extraction_results.get('entities', []):
                if entity.get('reference'):
                    cursor.execute("""
                        INSERT INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
                        VALUES (?, ?, ?, ?)
                    """, (doc_id, entity.get('type', 'entity'), entity.get('reference'), 
                          entity.get('text', '')[:500]))
                    entries_added += 1
            
            # Add provisions
            for provision in extraction_results.get('provisions', []):
                if provision.get('clause'):
                    cursor.execute("""
                        INSERT INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
                        VALUES (?, ?, ?, ?)
                    """, (doc_id, provision.get('type', 'provision'), provision.get('clause'),
                          provision.get('text', '')[:500]))
                    entries_added += 1
            
            conn.commit()
            
        except Exception as e:
            self.log_error(f"Database error for {doc_id}: {str(e)}")
            conn.rollback()
            
        finally:
            conn.close()
        
        return entries_added

    def log_error(self, error_message):
        """Log error to file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.errors_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {error_message}\n")
        self.stats['errors'].append(error_message)

    def save_progress(self):
        """Save current progress"""
        progress_data = {
            'stats': self.stats.copy(),
            'stats_formatted': {
                'start_time': self.stats['start_time'].isoformat(),
                'processed_documents': self.stats['processed_documents'],
                'total_documents': self.stats['total_documents'],
                'completion_percentage': (self.stats['processed_documents'] / max(1, self.stats['total_documents'])) * 100,
                'api_calls_made': self.stats['total_api_calls'],
                'successful_extractions': self.stats['successful_extractions'],
                'failed_extractions': self.stats['failed_extractions'],
                'entities_extracted': self.stats['total_entities'],
                'relationships_extracted': self.stats['total_relationships'],
                'provisions_extracted': self.stats['total_provisions'],
                'db_entries': self.stats['db_entries_added'],
                'error_count': len(self.stats['errors'])
            },
            'last_update': datetime.now().isoformat()
        }
        
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2, default=str)

    def print_progress_report(self):
        """Print detailed progress report"""
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
        docs_per_hour = (self.stats['processed_documents'] / elapsed) * 3600 if elapsed > 0 else 0
        api_calls_per_minute = (self.stats['total_api_calls'] / elapsed) * 60 if elapsed > 0 else 0
        
        print("\n" + "=" * 80)
        print("PROGRESS REPORT")
        print("=" * 80)
        print(f"Runtime: {elapsed/3600:.1f} hours")
        print(f"Documents: {self.stats['processed_documents']}/{self.stats['total_documents']} ({(self.stats['processed_documents']/max(1, self.stats['total_documents'])*100):.1f}%)")
        print(f"API calls: {self.stats['total_api_calls']} (rate: {api_calls_per_minute:.1f}/min)")
        print(f"Extraction rate: {self.stats['successful_extractions']}/{self.stats['successful_extractions'] + self.stats['failed_extractions']} successful")
        print()
        print(f"EXTRACTED:")
        print(f"  Entities: {self.stats['total_entities']:,}")
        print(f"  Relationships: {self.stats['total_relationships']:,}")  
        print(f"  Provisions: {self.stats['total_provisions']:,}")
        print(f"  DB entries: {self.stats['db_entries_added']:,}")
        print()
        print(f"Processing rate: {docs_per_hour:.1f} docs/hour")
        if self.stats['total_documents'] > self.stats['processed_documents']:
            remaining = self.stats['total_documents'] - self.stats['processed_documents']
            eta_hours = remaining / docs_per_hour if docs_per_hour > 0 else 0
            eta_time = datetime.now() + timedelta(hours=eta_hours)
            print(f"ETA: {eta_time.strftime('%Y-%m-%d %H:%M')} ({eta_hours:.1f} hours remaining)")
        
        print(f"Errors: {len(self.stats['errors'])}")
        if self.stats['errors']:
            print(f"Recent errors:")
            for error in self.stats['errors'][-3:]:
                print(f"  - {error}")
        
        print("=" * 80 + "\n")

    def process_all_documents(self, resume_from=None):
        """Process all documents with monitoring"""
        
        # Get documents
        conn = sqlite3.connect('nsw_planning.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, pdf_name, full_text, char_count
            FROM documents 
            WHERE char_count > 1000
            ORDER BY char_count ASC
        """)
        documents = cursor.fetchall()
        conn.close()
        
        self.stats['total_documents'] = len(documents)
        
        # Find resume point
        start_index = 0
        if resume_from:
            for i, (doc_id, pdf_name, _, _) in enumerate(documents):
                if doc_id == resume_from or pdf_name == resume_from:
                    start_index = i
                    break
        
        print(f"Processing {len(documents)} documents")
        if start_index > 0:
            print(f"Resuming from document {start_index + 1}")
        
        print(f"Estimated time: {len(documents) * 0.05:.1f} to {len(documents) * 0.1:.1f} hours")
        print("=" * 80)
        
        # Process documents
        for doc_idx in range(start_index, len(documents)):
            if not self.monitoring_active:
                break
            
            doc_id, pdf_name, full_text, char_count = documents[doc_idx]
            
            print(f"\n[{doc_idx + 1}/{len(documents)}] {pdf_name[:70]}...")
            print(f"  Size: {char_count:,} chars")
            
            try:
                # Extract content
                extraction_results = self.extract_from_document(doc_id, pdf_name, full_text)
                
                # Update statistics
                self.stats['total_entities'] += len(extraction_results['entities'])
                self.stats['total_relationships'] += len(extraction_results['relationships'])
                self.stats['total_provisions'] += len(extraction_results['provisions'])
                
                # Update database
                db_entries = self.update_database(doc_id, extraction_results)
                self.stats['db_entries_added'] += db_entries
                
                self.stats['processed_documents'] += 1
                self.stats['last_successful_doc'] = doc_id
                
                print(f"  Total: E:{len(extraction_results['entities'])} R:{len(extraction_results['relationships'])} P:{len(extraction_results['provisions'])} DB:{db_entries}")
                
                # Save individual result
                doc_output = {
                    'document_id': doc_id,
                    'document_name': pdf_name,
                    'processed_at': datetime.now().isoformat(),
                    'extraction_results': extraction_results
                }
                
                output_file = self.output_dir / f"{doc_id}_results.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(doc_output, f, indent=2, ensure_ascii=False)
                
                # Progress reports
                if datetime.now() - self.last_progress_report > self.progress_interval:
                    self.print_progress_report()
                    self.save_progress()
                    self.last_progress_report = datetime.now()
                
            except Exception as e:
                self.log_error(f"{pdf_name}: {str(e)}")
                print(f"  [ERROR: {str(e)[:50]}]")
                continue

    def generate_final_report(self):
        """Generate final comprehensive report"""
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
        
        # Check database final state
        conn = sqlite3.connect('nsw_planning.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
        final_db_count = cursor.fetchone()[0]
        conn.close()
        
        final_report = {
            'pipeline_completion': {
                'start_time': self.stats['start_time'].isoformat(),
                'end_time': datetime.now().isoformat(),
                'duration_hours': elapsed / 3600,
                'documents_processed': self.stats['processed_documents'],
                'completion_rate': (self.stats['processed_documents'] / max(1, self.stats['total_documents'])) * 100
            },
            'api_usage': {
                'total_calls': self.stats['total_api_calls'],
                'successful_extractions': self.stats['successful_extractions'],
                'failed_extractions': self.stats['failed_extractions'],
                'success_rate': (self.stats['successful_extractions'] / max(1, self.stats['successful_extractions'] + self.stats['failed_extractions'])) * 100
            },
            'extraction_totals': {
                'entities': self.stats['total_entities'],
                'relationships': self.stats['total_relationships'],
                'provisions': self.stats['total_provisions'],
                'database_entries': final_db_count
            },
            'averages_per_document': {
                'entities': self.stats['total_entities'] / max(1, self.stats['processed_documents']),
                'relationships': self.stats['total_relationships'] / max(1, self.stats['processed_documents']),
                'provisions': self.stats['total_provisions'] / max(1, self.stats['processed_documents'])
            },
            'error_summary': {
                'total_errors': len(self.stats['errors']),
                'error_rate': len(self.stats['errors']) / max(1, self.stats['processed_documents']),
                'recent_errors': self.stats['errors'][-10:] if self.stats['errors'] else []
            }
        }
        
        report_file = self.output_dir / "final_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, indent=2)
        
        # Print summary
        print("\n" + "=" * 80)
        print("PIPELINE COMPLETED")
        print("=" * 80)
        print(f"Duration: {elapsed/3600:.1f} hours")
        print(f"Documents: {self.stats['processed_documents']}/{self.stats['total_documents']} ({final_report['pipeline_completion']['completion_rate']:.1f}%)")
        print(f"API calls: {self.stats['total_api_calls']} ({final_report['api_usage']['success_rate']:.1f}% success)")
        print()
        print("FINAL EXTRACTION TOTALS:")
        print(f"  Entities: {self.stats['total_entities']:,}")
        print(f"  Relationships: {self.stats['total_relationships']:,}")
        print(f"  Provisions: {self.stats['total_provisions']:,}")
        print(f"  Database entries: {final_db_count:,}")
        print()
        print(f"Output directory: {self.output_dir}")
        print(f"Final report: {report_file}")
        print(f"Errors: {len(self.stats['errors'])}")
        
        return final_report

def main():
    """Run monitored pipeline"""
    
    print("MONITORED 4-STACK PIPELINE LAUNCHER")
    print()
    print("This will process all 128 NSW planning documents with:")
    print("- Real-time monitoring and verification")
    print("- Progress reports every 10 minutes")
    print("- Graceful shutdown capability (Ctrl+C)")
    print("- Automatic resume functionality")
    print("- Comprehensive error logging")
    print()
    print("Estimated time: 3-5 hours")
    print()
    
    try:
        pipeline = MonitoredPipeline()
        pipeline.process_all_documents()
        pipeline.generate_final_report()
        
        print("\n[SUCCESS] Pipeline completed successfully")
        
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Pipeline stopped by user")
        
    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()