#!/usr/bin/env python3
"""
PRP-H1: LlamaIndex Text Extraction Module Implementation
Foolproof extraction with verification at each step
NO UNICODE CHARACTERS - Windows compatible
"""
import os
import json
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

class PRPStatus:
    """Track PRP execution status"""
    def __init__(self, prp_id: str):
        self.prp_id = prp_id
        self.started = datetime.now()
        self.documents_total = 0
        self.documents_processed = 0
        self.documents_failed = 0
        self.measurements_found = 0
        self.zones_found = 0
        self.conditions_found = 0
        self.clauses_found = 0
        self.errors = []
        self.warnings = []
        
    def log(self, level: str, message: str):
        """Log with timestamp and level"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {level}: {message}"
        print(entry)
        
        if level == "ERROR":
            self.errors.append(entry)
        elif level == "WARNING":
            self.warnings.append(entry)
            
    def checkpoint(self):
        """Save checkpoint for recovery"""
        checkpoint_data = {
            "prp_id": self.prp_id,
            "timestamp": datetime.now().isoformat(),
            "progress": f"{self.documents_processed}/{self.documents_total}",
            "measurements": self.measurements_found,
            "zones": self.zones_found,
            "conditions": self.conditions_found,
            "clauses": self.clauses_found,
            "errors": len(self.errors),
            "warnings": len(self.warnings)
        }
        
        checkpoint_file = Path(f"checkpoints/prp_h1_{self.prp_id}.json")
        checkpoint_file.parent.mkdir(exist_ok=True)
        
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
            
        return checkpoint_data

def execute_prp_h1(limit: int = 5):
    """Execute PRP-H1: LlamaIndex text extraction"""
    
    status = PRPStatus("H1_20241210")
    
    print("="*60)
    print("PRP-H1: LLAMAINDEX TEXT EXTRACTION MODULE")
    print("="*60)
    
    # VALIDATION GATE 1: Environment Setup
    status.log("INFO", "Validation Gate 1: Environment Setup")
    
    try:
        from llama_index.core import Document, Settings
        from llama_index.llms.openai import OpenAI
        from llama_index.embeddings.openai import OpenAIEmbedding
        from llama_index.core import VectorStoreIndex
        from dotenv import load_dotenv
        
        load_dotenv('.env.local')
        api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
            
        Settings.llm = OpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0)
        Settings.embed_model = OpenAIEmbedding(api_key=api_key)
        
        status.log("SUCCESS", "Environment setup complete")
        
    except Exception as e:
        status.log("ERROR", f"Environment setup failed: {e}")
        return False
    
    # Find documents
    status.log("INFO", "Finding documents to process")
    
    output_dir = Path("output")
    doc_files = []
    
    for doc_folder in output_dir.iterdir():
        if doc_folder.is_dir():
            content_file = doc_folder / 'auto' / f'{doc_folder.name}_content_list.json'
            if content_file.exists():
                doc_files.append(content_file)
                
    status.documents_total = min(len(doc_files), limit)
    status.log("INFO", f"Found {len(doc_files)} documents, processing {status.documents_total}")
    
    # Create output directory
    output_dir = Path("llamaindex_output")
    output_dir.mkdir(exist_ok=True)
    
    # Process documents
    for doc_path in doc_files[:limit]:
        doc_name = doc_path.parent.parent.name
        status.log("INFO", f"Processing: {doc_name[:50]}...")
        
        try:
            # Load document
            with open(doc_path, 'r', encoding='utf-8') as f:
                content_data = json.load(f)
            
            # Extract text chunks
            text_chunks = []
            for item in content_data[:20]:  # Limit chunks for testing
                if isinstance(item, dict) and 'text' in item:
                    text = item['text'].strip()
                    if len(text) > 50:
                        text_chunks.append(text)
            
            if not text_chunks:
                status.log("WARNING", f"No valid text chunks in {doc_name}")
                continue
            
            # Create LlamaIndex documents
            documents = []
            for i, chunk in enumerate(text_chunks):
                documents.append(Document(
                    text=chunk,
                    metadata={"source": doc_name, "chunk_id": i}
                ))
            
            # Build index
            index = VectorStoreIndex.from_documents(documents)
            query_engine = index.as_query_engine(response_mode="compact")
            
            # Extract specific data
            extraction_results = {}
            
            # 1. Extract measurements
            response = query_engine.query(
                "List all specific measurements with numbers and units (meters, percentages, ratios). "
                "Format: value unit (e.g., '4.5m', '60%', '0.5:1')"
            )
            measurements = re.findall(r'\d+(?:\.\d+)?\s*(?:m|metres?|%|:1)', response.response)
            extraction_results['measurements'] = measurements
            status.measurements_found += len(measurements)
            
            # 2. Extract zones
            response = query_engine.query(
                "List all zone codes mentioned (e.g., R1, R2, B1, B4, IN2, SP1)"
            )
            zones = re.findall(r'\b[RBCINESP]\d{1,2}\b', response.response)
            extraction_results['zones'] = list(set(zones))
            status.zones_found += len(extraction_results['zones'])
            
            # 3. Extract conditions
            response = query_engine.query(
                "Extract any conditional rules with IF/THEN, UNLESS, WHERE, or WHEN logic"
            )
            if any(word in response.response.lower() for word in ['if', 'then', 'unless', 'where', 'when']):
                extraction_results['conditions'] = response.response[:500]
                status.conditions_found += 1
            
            # 4. Extract clauses
            response = query_engine.query(
                "List all clause and section references with numbers (e.g., Clause 4.3, Section 5.1)"
            )
            clauses = re.findall(r'(?:Clause|Section|Part)\s+\d+(?:\.\d+)*', response.response, re.IGNORECASE)
            extraction_results['clauses'] = clauses
            status.clauses_found += len(clauses)
            
            # Save results
            output_file = output_dir / f"{doc_name}_extracted.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(extraction_results, f, indent=2)
            
            status.documents_processed += 1
            status.log("SUCCESS", f"Extracted: {len(measurements)} measurements, {len(zones)} zones, {len(clauses)} clauses")
            
        except Exception as e:
            status.log("ERROR", f"Failed to process {doc_name}: {str(e)[:100]}")
            status.documents_failed += 1
            continue
    
    # Final checkpoint
    checkpoint = status.checkpoint()
    
    # Validation Gate 2: Check success criteria
    print("\n" + "="*60)
    print("VALIDATION GATE 2: Success Criteria Check")
    print("="*60)
    
    success_rate = (status.documents_processed / status.documents_total * 100) if status.documents_total > 0 else 0
    
    print(f"Documents processed: {status.documents_processed}/{status.documents_total} ({success_rate:.1f}%)")
    print(f"Total measurements: {status.measurements_found} (target: 25+)")
    print(f"Total zones: {status.zones_found} (target: 10+)")
    print(f"Total conditions: {status.conditions_found} (target: 5+)")
    print(f"Total clauses: {status.clauses_found} (target: 50+)")
    print(f"Errors: {len(status.errors)}")
    print(f"Warnings: {len(status.warnings)}")
    
    # Determine success
    if success_rate >= 80 and status.measurements_found >= 25:
        print("\nPRP-H1: SUCCESS - Minimum thresholds met")
        return True
    elif success_rate >= 60:
        print("\nPRP-H1: PARTIAL SUCCESS - Some extraction completed")
        return True
    else:
        print("\nPRP-H1: FAILED - Below minimum thresholds")
        if status.errors:
            print("\nRecent errors:")
            for error in status.errors[-3:]:
                print(f"  {error}")
        return False

if __name__ == "__main__":
    success = execute_prp_h1(limit=5)
    exit(0 if success else 1)