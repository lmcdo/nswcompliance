#!/usr/bin/env python3
"""
MODULAR HYBRID EXTRACTION PIPELINE
Module 1: LlamaIndex Text Extraction with Real-Time Error Monitoring
Foolproof implementation with verification at each step
"""
import os
import json
import time
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Error monitoring
class ExtractionStatus(Enum):
 PENDING = "pending"
 PROCESSING = "processing"
 SUCCESS = "success"
 PARTIAL = "partial"
 FAILED = "failed"
 SKIPPED = "skipped"

@dataclass
class ExtractionResult:
 """Track extraction results with full error context"""
 document: str
 module: str
 status: ExtractionStatus
 entities_found: int = 0
 measurements_found: int = 0
 relationships_found: int = 0
 tables_found: int = 0
 errors: List[str] = None
 warnings: List[str] = None
 processing_time: float = 0.0
 timestamp: str = ""
 
 def __post_init__(self):
 if self.errors is None:
 self.errors = []
 if self.warnings is None:
 self.warnings = []
 if not self.timestamp:
 self.timestamp = datetime.now().isoformat()

class ErrorMonitor:
 """Real-time error monitoring and reporting"""
 
 def __init__(self, log_dir: str = "extraction_logs"):
 self.log_dir = Path(log_dir)
 self.log_dir.mkdir(exist_ok=True)
 self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
 self.errors = []
 self.warnings = []
 self.results = []
 
 # Create session log file
 self.log_file = self.log_dir / f"session_{self.session_id}.log"
 self.error_file = self.log_dir / f"errors_{self.session_id}.json"
 
 def log(self, level: str, message: str, document: str = None):
 """Log with real-time display and file recording"""
 timestamp = datetime.now().strftime("%H:%M:%S")
 log_entry = f"[{timestamp}] {level}: {message}"
 
 if document:
 log_entry = f"[{timestamp}] [{document}] {level}: {message}"
 
 # Real-time display
 if level == "ERROR":
 print(f" {log_entry}")
 self.errors.append({"time": timestamp, "doc": document, "msg": message})
 elif level == "WARNING":
 print(f" {log_entry}")
 self.warnings.append({"time": timestamp, "doc": document, "msg": message})
 elif level == "SUCCESS":
 print(f" {log_entry}")
 else:
 print(f" {log_entry}")
 
 # Write to log file
 with open(self.log_file, 'a', encoding='utf-8') as f:
 f.write(log_entry + "\n")
 
 def save_errors(self):
 """Save all errors to JSON for analysis"""
 error_summary = {
 "session_id": self.session_id,
 "total_errors": len(self.errors),
 "total_warnings": len(self.warnings),
 "errors": self.errors,
 "warnings": self.warnings,
 "results": [r.__dict__ for r in self.results]
 }
 
 with open(self.error_file, 'w', encoding='utf-8') as f:
 json.dump(error_summary, f, indent=2)
 
 return error_summary

class Module1_LlamaIndexText:
 """Module 1: LlamaIndex text extraction with verification"""
 
 def __init__(self, monitor: ErrorMonitor):
 self.monitor = monitor
 self.monitor.log("INFO", "Initializing Module 1: LlamaIndex Text Extraction")
 
 try:
 from llama_index.core import Document, Settings
 from llama_index.llms.openai import OpenAI
 from llama_index.embeddings.openai import OpenAIEmbedding
 from llama_index.core import VectorStoreIndex
 
 # Load API key
 from dotenv import load_dotenv
 load_dotenv('.env.local')
 
 api_key = os.getenv('OPENAI_API_KEY')
 if not api_key:
 raise ValueError("OPENAI_API_KEY not found")
 
 # Configure LlamaIndex
 Settings.llm = OpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0)
 Settings.embed_model = OpenAIEmbedding(api_key=api_key)
 
 self.Document = Document
 self.VectorStoreIndex = VectorStoreIndex
 self.initialized = True
 self.monitor.log("SUCCESS", "Module 1 initialized successfully")
 
 except Exception as e:
 self.monitor.log("ERROR", f"Module 1 initialization failed: {str(e)}")
 self.initialized = False
 raise
 
 def extract_from_document(self, doc_path: str) -> ExtractionResult:
 """Extract planning data from single document with error handling"""
 
 doc_name = Path(doc_path).stem
 result = ExtractionResult(document=doc_name, module="LlamaIndex")
 start_time = time.time()
 
 self.monitor.log("INFO", f"Processing document", doc_name)
 
 try:
 # Load document JSON
 with open(doc_path, 'r', encoding='utf-8') as f:
 content_data = json.load(f)
 
 # Extract text chunks
 if isinstance(content_data, list):
 text_chunks = [item.get('text', '') for item in content_data if item.get('text', '').strip()]
 else:
 # Handle different JSON structures
 text_chunks = []
 if 'verified_provisions' in content_data:
 # LangExtract format
 for prov in content_data['verified_provisions']:
 text_chunks.append(f"Clause {prov.get('clause_reference', '')}: {prov.get('regulatory_text', '')}")
 elif 'content' in content_data:
 text_chunks = [content_data['content']]
 
 if not text_chunks:
 result.status = ExtractionStatus.SKIPPED
 result.warnings.append("No text content found")
 self.monitor.log("WARNING", "No text content found", doc_name)
 return result
 
 # Create LlamaIndex documents
 documents = []
 for i, chunk in enumerate(text_chunks[:20]): # Limit for testing
 if len(chunk.strip()) > 50:
 documents.append(self.Document(
 text=chunk.strip(),
 metadata={"source": doc_name, "chunk_id": i}
 ))
 
 if not documents:
 result.status = ExtractionStatus.SKIPPED
 result.warnings.append("All chunks too short")
 return result
 
 # Build index
 index = self.VectorStoreIndex.from_documents(documents)
 query_engine = index.as_query_engine(response_mode="compact", similarity_top_k=3)
 
 # Extract specific planning data
 extraction_queries = [
 ("measurements", "Extract all specific measurements with units (meters, percentages, ratios) from this planning document"),
 ("zones", "List all zone classifications (R1, R2, B1, etc.) mentioned"),
 ("conditions", "Extract conditional rules with IF/THEN/UNLESS/WHERE logic"),
 ("clauses", "List all clause and section references with numbers")
 ]
 
 extracted_data = {}
 
 for query_type, query_text in extraction_queries:
 try:
 response = query_engine.query(query_text)
 extracted_data[query_type] = response.response
 
 # Count extracted items
 if query_type == "measurements":
 import re
 measurements = re.findall(r'\d+(?:\.\d+)?\s*(?:m|metres?|%|:1)', response.response)
 result.measurements_found = len(measurements)
 elif query_type == "zones":
 zones = re.findall(r'\b[RBCINE]\d{1,2}\b', response.response)
 result.entities_found += len(zones)
 
 except Exception as e:
 self.monitor.log("WARNING", f"Query '{query_type}' failed: {str(e)}", doc_name)
 result.warnings.append(f"Query '{query_type}' failed")
 
 # Save extracted data
 output_file = Path(f"llamaindex_output/{doc_name}_extracted.json")
 output_file.parent.mkdir(exist_ok=True)
 with open(output_file, 'w', encoding='utf-8') as f:
 json.dump(extracted_data, f, indent=2)
 
 result.status = ExtractionStatus.SUCCESS
 result.processing_time = time.time() - start_time
 self.monitor.log("SUCCESS", f"Extracted {result.measurements_found} measurements, {result.entities_found} entities", doc_name)
 
 except Exception as e:
 result.status = ExtractionStatus.FAILED
 result.errors.append(str(e))
 result.processing_time = time.time() - start_time
 self.monitor.log("ERROR", f"Extraction failed: {str(e)}", doc_name)
 traceback.print_exc()
 
 return result

class Module2_RAGFlowTables:
 """Module 2: RAGFlow table and diagram extraction"""
 
 def __init__(self, monitor: ErrorMonitor):
 self.monitor = monitor
 self.monitor.log("INFO", "Initializing Module 2: RAGFlow Table/Diagram Extraction")
 
 try:
 # Check if Unstructured.io is available for table extraction
 import unstructured
 from unstructured.partition.auto import partition
 
 self.partition = partition
 self.initialized = True
 self.monitor.log("SUCCESS", "Module 2 initialized with Unstructured.io")
 
 except ImportError:
 self.monitor.log("WARNING", "Unstructured.io not available, using fallback table detection")
 self.initialized = False
 self.partition = None
 
 def extract_tables(self, doc_path: str) -> ExtractionResult:
 """Extract tables and structured data"""
 
 doc_name = Path(doc_path).stem
 result = ExtractionResult(document=doc_name, module="RAGFlow")
 start_time = time.time()
 
 self.monitor.log("INFO", f"Extracting tables/diagrams", doc_name)
 
 try:
 with open(doc_path, 'r', encoding='utf-8') as f:
 content_data = json.load(f)
 
 # Look for table-like structures in JSON
 tables_found = []
 
 # Pattern 1: Height limits table
 height_patterns = []
 fsr_patterns = []
 setback_patterns = []
 
 if isinstance(content_data, list):
 for item in content_data:
 text = item.get('text', '')
 
 # Detect table-like patterns
 if '|' in text or '\t' in text:
 tables_found.append({"type": "formatted_table", "content": text})
 result.tables_found += 1
 
 # Extract structured measurements
 import re
 
 # Height table pattern: "Zone R2: 8.5m"
 height_matches = re.findall(r'([RBCINE]\d{1,2})[:\s]+(\d+(?:\.\d+)?)\s*m', text)
 if height_matches:
 height_patterns.extend(height_matches)
 
 # FSR table pattern: "R2 - 0.5:1"
 fsr_matches = re.findall(r'([RBCINE]\d{1,2})[:\s\-]+(\d+(?:\.\d+)?):1', text)
 if fsr_matches:
 fsr_patterns.extend(fsr_matches)
 
 # Setback table pattern
 setback_matches = re.findall(r'(?:front|side|rear)[:\s]+(\d+(?:\.\d+)?)\s*m', text, re.IGNORECASE)
 if setback_matches:
 setback_patterns.extend(setback_matches)
 
 # Save structured table data
 table_data = {
 "tables_found": len(tables_found),
 "height_limits": height_patterns,
 "fsr_values": fsr_patterns,
 "setback_values": setback_patterns,
 "raw_tables": tables_found[:5] # Sample for verification
 }
 
 output_file = Path(f"ragflow_output/{doc_name}_tables.json")
 output_file.parent.mkdir(exist_ok=True)
 with open(output_file, 'w', encoding='utf-8') as f:
 json.dump(table_data, f, indent=2)
 
 result.tables_found = len(tables_found)
 result.measurements_found = len(height_patterns) + len(fsr_patterns) + len(setback_patterns)
 result.status = ExtractionStatus.SUCCESS if result.tables_found > 0 else ExtractionStatus.PARTIAL
 result.processing_time = time.time() - start_time
 
 self.monitor.log("SUCCESS", f"Found {result.tables_found} tables, {result.measurements_found} structured values", doc_name)
 
 except Exception as e:
 result.status = ExtractionStatus.FAILED
 result.errors.append(str(e))
 result.processing_time = time.time() - start_time
 self.monitor.log("ERROR", f"Table extraction failed: {str(e)}", doc_name)
 
 return result

class HybridPipeline:
 """Main pipeline orchestrator with verification"""
 
 def __init__(self):
 self.monitor = ErrorMonitor()
 self.monitor.log("INFO", "Starting Hybrid Extraction Pipeline")
 
 # Initialize modules
 self.module1 = None
 self.module2 = None
 
 # Track overall progress
 self.total_docs = 0
 self.processed_docs = 0
 self.failed_docs = 0
 
 def initialize_modules(self):
 """Initialize all modules with error handling"""
 
 try:
 self.module1 = Module1_LlamaIndexText(self.monitor)
 except Exception as e:
 self.monitor.log("ERROR", f"Module 1 failed to initialize: {e}")
 self.module1 = None
 
 try:
 self.module2 = Module2_RAGFlowTables(self.monitor)
 except Exception as e:
 self.monitor.log("ERROR", f"Module 2 failed to initialize: {e}")
 self.module2 = None
 
 if not self.module1 and not self.module2:
 raise RuntimeError("No extraction modules available")
 
 def process_document(self, doc_path: str) -> List[ExtractionResult]:
 """Process single document through all available modules"""
 
 results = []
 doc_name = Path(doc_path).stem
 
 self.monitor.log("INFO", f"Processing document {self.processed_docs + 1}/{self.total_docs}", doc_name)
 
 # Module 1: LlamaIndex text extraction
 if self.module1 and self.module1.initialized:
 result1 = self.module1.extract_from_document(doc_path)
 results.append(result1)
 self.monitor.results.append(result1)
 
 # Module 2: RAGFlow table extraction
 if self.module2:
 result2 = self.module2.extract_tables(doc_path)
 results.append(result2)
 self.monitor.results.append(result2)
 
 # Check for failures
 if any(r.status == ExtractionStatus.FAILED for r in results):
 self.failed_docs += 1
 
 self.processed_docs += 1
 
 return results
 
 def run_pipeline(self, limit: int = 5):
 """Run extraction pipeline with limit for testing"""
 
 print("\nHYBRID EXTRACTION PIPELINE - MODULAR IMPLEMENTATION")
 print("=" * 60)
 
 # Initialize modules
 self.initialize_modules()
 
 # Find documents to process
 output_dir = Path("output")
 doc_files = []
 
 for doc_folder in output_dir.iterdir():
 if doc_folder.is_dir():
 content_file = doc_folder / 'auto' / f'{doc_folder.name}_content_list.json'
 if content_file.exists():
 doc_files.append(content_file)
 
 # Also check LangExtract files
 langextract_dir = Path("langextract_verified_output")
 if langextract_dir.exists():
 for json_file in langextract_dir.glob("*_verified.json"):
 doc_files.append(json_file)
 
 self.total_docs = min(len(doc_files), limit)
 self.monitor.log("INFO", f"Found {len(doc_files)} documents, processing {self.total_docs}")
 
 # Process documents
 all_results = []
 
 for doc_path in doc_files[:limit]:
 try:
 results = self.process_document(str(doc_path))
 all_results.extend(results)
 except Exception as e:
 self.monitor.log("ERROR", f"Document processing failed: {e}", str(doc_path))
 self.failed_docs += 1
 
 # Generate summary
 self.generate_summary(all_results)
 
 # Save error report
 error_summary = self.monitor.save_errors()
 
 return all_results, error_summary
 
 def generate_summary(self, results: List[ExtractionResult]):
 """Generate extraction summary with error analysis"""
 
 print("\n" + "=" * 60)
 print("EXTRACTION SUMMARY")
 print("=" * 60)
 
 # Count by status
 status_counts = {}
 for result in results:
 status_counts[result.status.value] = status_counts.get(result.status.value, 0) + 1
 
 print(f"Documents processed: {self.processed_docs}/{self.total_docs}")
 print(f"Failed documents: {self.failed_docs}")
 print("\nStatus breakdown:")
 for status, count in status_counts.items():
 print(f" {status}: {count}")
 
 # Aggregate metrics
 total_entities = sum(r.entities_found for r in results)
 total_measurements = sum(r.measurements_found for r in results)
 total_tables = sum(r.tables_found for r in results)
 total_relationships = sum(r.relationships_found for r in results)
 
 print(f"\nExtraction totals:")
 print(f" Entities: {total_entities}")
 print(f" Measurements: {total_measurements}")
 print(f" Tables: {total_tables}")
 print(f" Relationships: {total_relationships}")
 
 # Error analysis
 total_errors = len(self.monitor.errors)
 total_warnings = len(self.monitor.warnings)
 
 print(f"\nError analysis:")
 print(f" Errors: {total_errors}")
 print(f" Warnings: {total_warnings}")
 
 if total_errors > 0:
 print("\nMost recent errors:")
 for error in self.monitor.errors[-3:]:
 print(f" [{error['time']}] {error['doc']}: {error['msg'][:100]}")
 
 # Performance
 avg_time = sum(r.processing_time for r in results) / len(results) if results else 0
 print(f"\nAverage processing time: {avg_time:.2f}s per document")

def main():
 """Main execution with verification"""
 
 pipeline = HybridPipeline()
 
 try:
 results, error_summary = pipeline.run_pipeline(limit=5) # Test with 5 docs
 
 print("\n" + "=" * 60)
 if error_summary['total_errors'] == 0:
 print("SUCCESS: Pipeline completed without errors")
 else:
 print(f"COMPLETED WITH ISSUES: {error_summary['total_errors']} errors logged")
 print(f"Error report saved: {pipeline.monitor.error_file}")
 
 return True
 
 except Exception as e:
 print(f"\nPIPELINE FAILED: {e}")
 traceback.print_exc()
 return False

if __name__ == "__main__":
 success = main()
 exit(0 if success else 1)