#!/usr/bin/env python
"""
PRP-A2-EXT: Process 87 Marrickville DCP files using direct mineru calls
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

def process_pdf_with_mineru(pdf_path):
 """Process a single PDF using mineru directly"""
 try:
 # Create temporary output directory
 with tempfile.TemporaryDirectory() as temp_dir:
 # Run mineru command
 cmd = [
 "./venv_linux/Scripts/mineru.exe",
 "-p", str(pdf_path),
 "-o", temp_dir,
 "-m", "txt", # Use text extraction method
 "-b", "pipeline" # Use pipeline backend
 ]
 
 result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
 
 if result.returncode != 0:
 print(f"mineru failed for {pdf_path.name}: {result.stderr}")
 return None
 
 # Read the output files
 output_files = list(Path(temp_dir).rglob("*.md"))
 if not output_files:
 output_files = list(Path(temp_dir).rglob("*.txt"))
 
 if not output_files:
 print(f"No output files found for {pdf_path.name}")
 return None
 
 # Read the content
 content_text = ""
 for output_file in output_files:
 with open(output_file, 'r', encoding='utf-8') as f:
 content_text += f.read() + "\n"
 
 return content_text
 
 except subprocess.TimeoutExpired:
 print(f"Timeout processing {pdf_path.name}")
 return None
 except Exception as e:
 print(f"Error processing {pdf_path.name}: {e}")
 return None

def process_marrickville_dcps_direct():
 print("PRP-A2-EXT: MARRICKVILLE DCP PROCESSOR (DIRECT MINERU)")
 print("=" * 60)
 
 # Find all Marrickville PDF files
 marrickville_dir = Path("docs/dcps/INNERWEST/Marrickville")
 pdf_files = list(marrickville_dir.glob("*.pdf"))
 
 print(f"Found {len(pdf_files)} Marrickville PDF files")
 
 all_extracted_content = {}
 processed_count = 0
 
 # Process first 5 files as a test
 test_files = pdf_files[:5]
 
 for pdf_path in test_files:
 print(f"Processing [{processed_count+1}/5]: {pdf_path.name}")
 
 # Extract content using mineru
 content_text = process_pdf_with_mineru(pdf_path)
 
 if content_text:
 # Store with file path as key
 file_key = str(pdf_path).replace('\\', '/').replace('/', '_').replace('.pdf', '')
 all_extracted_content[file_key] = {
 "source_path": str(pdf_path).replace('\\', '/'),
 "content": content_text,
 "processed_timestamp": datetime.now().isoformat(),
 "file_size_kb": pdf_path.stat().st_size / 1024,
 "processing_stage": "A2_EXT_marrickville_direct",
 "extraction_method": "mineru_direct"
 }
 
 processed_count += 1
 print(f"Completed {processed_count}/5 PDFs")
 else:
 print(f"Failed to extract content from {pdf_path.name}")
 
 # Save extracted content
 os.makedirs("validated_outputs", exist_ok=True)
 output_file = "validated_outputs/A2_EXT_marrickville_direct_test.json"
 
 with open(output_file, "w", encoding="utf-8") as f:
 json.dump(all_extracted_content, f, indent=2, ensure_ascii=False)
 
 print(f"\n{processed_count} Marrickville DCPs extracted to: {output_file}")
 print(f"Success rate: {processed_count}/{len(test_files)} ({processed_count/len(test_files)*100:.1f}%)")
 
 return all_extracted_content

if __name__ == "__main__":
 extracted_data = process_marrickville_dcps_direct()
 print("PRP-A2-EXT Direct test completed")