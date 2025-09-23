#!/usr/bin/env python
"""
PRP-A2-EXT: Process 87 Marrickville DCP files
Extract regulatory provisions from all Marrickville DCPs using RagAnything
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
import sys

# Add the virtual environment path
sys.path.append('./venv_linux/Lib/site-packages')

async def process_marrickville_dcps():
 print("PRP-A2-EXT: MARRICKVILLE DCP PROCESSOR")
 print("=" * 60)
 print("Processing 87 Marrickville DCP files with RagAnything")
 print()
 
 # Import RagAnything
 try:
 from raganything import RAGAnything
 from raganything.config import RAGAnythingConfig
 print("RagAnything imported successfully")
 except ImportError as e:
 print(f"Failed to import RagAnything: {e}")
 print("Attempting to use system Python...")
 import subprocess
 result = subprocess.run([
 sys.executable, "-c", "from raganything import RAGAnything; print('RagAnything available')"
 ], capture_output=True, text=True)
 if result.returncode != 0:
 raise Exception("RagAnything not available in any Python environment")
 
 # Initialize RagAnything processor with PyPDF parser
 config = RAGAnythingConfig()
 rag = RAGAnything(config=config)
 
 # Find all Marrickville PDF files
 marrickville_dir = Path("docs/dcps/INNERWEST/Marrickville")
 pdf_files = list(marrickville_dir.glob("*.pdf"))
 
 print(f"Found {len(pdf_files)} Marrickville PDF files")
 
 if len(pdf_files) != 87:
 print(f"WARNING: Expected 87 files, found {len(pdf_files)}")
 
 all_extracted_content = {}
 processed_count = 0
 
 for pdf_path in pdf_files:
 print(f"Processing [{processed_count+1}/{len(pdf_files)}]: {pdf_path.name}")
 
 try:
 # Extract content from each PDF
 extracted_content = await rag.parse_document(str(pdf_path))
 
 # Store with file path as key
 file_key = str(pdf_path).replace('\\', '/').replace('/', '_').replace('.pdf', '')
 all_extracted_content[file_key] = {
 "source_path": str(pdf_path).replace('\\', '/'),
 "content": extracted_content,
 "processed_timestamp": datetime.now().isoformat(),
 "file_size_kb": pdf_path.stat().st_size / 1024,
 "processing_stage": "A2_EXT_marrickville"
 }
 
 processed_count += 1
 print(f"Completed {processed_count}/{len(pdf_files)} PDFs")
 
 except Exception as e:
 print(f"Failed to process {pdf_path.name}: {e}")
 # Continue with other files instead of failing completely
 continue
 
 # Save extracted content
 os.makedirs("validated_outputs", exist_ok=True)
 output_file = "validated_outputs/A2_EXT_marrickville_extracted_content.json"
 
 with open(output_file, "w", encoding="utf-8") as f:
 json.dump(all_extracted_content, f, indent=2, ensure_ascii=False)
 
 print(f"\n{processed_count} Marrickville DCPs extracted to: {output_file}")
 print(f"Success rate: {processed_count}/{len(pdf_files)} ({processed_count/len(pdf_files)*100:.1f}%)")
 
 return all_extracted_content

if __name__ == "__main__":
 extracted_data = asyncio.run(process_marrickville_dcps())
 print("PRP-A2-EXT Marrickville extraction completed")