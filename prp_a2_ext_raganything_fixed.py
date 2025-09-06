#!/usr/bin/env python
"""
PRP-A2-EXT: Process 85 Marrickville DCP files using RagAnything with proper PATH setup
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add venv Scripts to PATH so RagAnything can find mineru
venv_scripts = os.path.abspath("./venv_linux/Scripts")
if venv_scripts not in os.environ["PATH"]:
    os.environ["PATH"] = venv_scripts + os.pathsep + os.environ["PATH"]

from raganything import RAGAnything
from raganything.config import RAGAnythingConfig

async def process_marrickville_with_raganything_fixed():
    print("PRP-A2-EXT: MARRICKVILLE DCP PROCESSING WITH RAGANYTHING (PATH FIXED)")
    print("=" * 70)
    print("Added venv Scripts to PATH to resolve mineru dependency")
    print(f"PATH includes: {venv_scripts}")
    print()
    
    # Initialize RagAnything with proper configuration
    config = RAGAnythingConfig()
    rag = RAGAnything(config=config)
    
    # Find all Marrickville PDF files
    marrickville_dir = Path("docs/dcps/INNERWEST/Marrickville")
    pdf_files = list(marrickville_dir.glob("*.pdf"))
    
    print(f"Found {len(pdf_files)} Marrickville PDF files")
    print("Processing with RagAnything (PATH fixed for mineru access)...")
    print()
    
    all_extracted_content = {}
    processed_count = 0
    failed_count = 0
    
    # Process first 3 files as test
    test_files = sorted(pdf_files)[:3]
    
    for pdf_path in test_files:
        print(f"Processing [{processed_count+1}/{len(test_files)}]: {pdf_path.name}")
        
        try:
            # Use RagAnything parse_document method
            extracted_content = await rag.parse_document(str(pdf_path))
            
            # Store with file path as key (same format as successful A2 processing)
            file_key = str(pdf_path).replace('\\', '/').replace('/', '_').replace('.pdf', '')
            all_extracted_content[file_key] = {
                "source_path": str(pdf_path).replace('\\', '/'),
                "content": extracted_content,
                "processed_timestamp": datetime.now().isoformat(),
                "file_size_kb": pdf_path.stat().st_size / 1024,
                "processing_stage": "A2_EXT_marrickville_raganything_fixed"
            }
            
            processed_count += 1
            print(f"SUCCESS: Completed {processed_count}/{len(test_files)} files")
            print(f"Content type: {type(extracted_content)}")
            print(f"Content length: {len(str(extracted_content))}")
            print()
                    
        except Exception as e:
            print(f"FAILED: {pdf_path.name} - {str(e)}")
            failed_count += 1
    
    # Save test results
    os.makedirs("validated_outputs", exist_ok=True)
    output_file = "validated_outputs/A2_EXT_marrickville_test_fixed.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_extracted_content, f, indent=2, ensure_ascii=False)
    
    print(f"Test results:")
    print(f"Successful: {processed_count}/{len(test_files)} files")
    print(f"Failed: {failed_count}/{len(test_files)} files")
    print(f"Output: {output_file}")
    
    if processed_count > 0:
        print("\n✅ RagAnything is working! Ready to process all 85 files")
        return True
    else:
        print("\n❌ RagAnything still not working")
        return False

if __name__ == "__main__":
    success = asyncio.run(process_marrickville_with_raganything_fixed())
    
    if success:
        print("PATH fix successful - RagAnything can process Marrickville files")
    else:
        print("Still need to resolve RagAnything configuration issue")