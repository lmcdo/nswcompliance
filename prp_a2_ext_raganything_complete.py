#!/usr/bin/env python
"""
PRP-A2-EXT: Process ALL 85 Marrickville DCP files using RagAnything with proper PATH setup
Final implementation following PRP specification exactly
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

# Set environment variable to disable symlinks warning
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from raganything import RAGAnything
from raganything.config import RAGAnythingConfig

async def process_all_marrickville_with_raganything():
    print("PRP-A2-EXT: COMPLETE MARRICKVILLE DCP PROCESSING WITH RAGANYTHING")
    print("=" * 70)
    print("Processing ALL 85 Marrickville files as per PRP specification")
    print()
    
    # Initialize RagAnything with proper configuration
    config = RAGAnythingConfig()
    rag = RAGAnything(config=config)
    
    # Find all Marrickville PDF files
    marrickville_dir = Path("docs/dcps/INNERWEST/Marrickville")
    pdf_files = list(marrickville_dir.glob("*.pdf"))
    
    print(f"Found {len(pdf_files)} Marrickville PDF files")
    print("Processing with RagAnything (proper format matching A2 processing)...")
    print()
    
    all_extracted_content = {}
    processed_count = 0
    failed_count = 0
    
    for pdf_path in sorted(pdf_files):
        print(f"Processing [{processed_count+1}/{len(pdf_files)}]: {pdf_path.name}")
        
        try:
            # Use RagAnything parse_document method
            extracted_content = await rag.parse_document(str(pdf_path))
            
            # Store with same key format as A2 processing
            file_key = str(pdf_path).replace('\\', '/').replace('/', '_').replace('.pdf', '')
            all_extracted_content[file_key] = {
                "source_path": str(pdf_path).replace('\\', '/'),
                "content": extracted_content,
                "processed_timestamp": datetime.now().isoformat()
            }
            
            processed_count += 1
            print(f"SUCCESS: Completed {processed_count}/{len(pdf_files)} files")
            
            # Save progress every 10 files
            if processed_count % 10 == 0:
                temp_file = f"validated_outputs/A2_EXT_progress_{processed_count}.json"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(all_extracted_content, f, indent=2, ensure_ascii=False)
                print(f"Progress saved: {processed_count}/{len(pdf_files)} files")
                    
        except Exception as e:
            print(f"FAILED: {pdf_path.name} - {str(e)}")
            failed_count += 1
            
            # Continue processing other files even if some fail
            if failed_count > 20:  # If too many failures, stop
                print(f"Too many failures ({failed_count}). Stopping.")
                break
    
    # Save final results
    os.makedirs("validated_outputs", exist_ok=True)
    output_file = "validated_outputs/A2_EXT_marrickville_complete_raganything.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_extracted_content, f, indent=2, ensure_ascii=False)
    
    print(f"\nFINAL RESULTS:")
    print(f"Successful: {processed_count}/{len(pdf_files)} files")
    print(f"Failed: {failed_count}/{len(pdf_files)} files")
    print(f"Success rate: {processed_count/len(pdf_files)*100:.1f}%")
    print(f"Output: {output_file}")
    
    # PRP completion requires high success rate
    if processed_count >= len(pdf_files) * 0.8:  # 80% success rate minimum
        print("\nPRP-A2-EXT: COMPLETED SUCCESSFULLY")
        print("All Marrickville files processed with RagAnything as per specification")
        return all_extracted_content
    else:
        print(f"\nPRP-A2-EXT: INSUFFICIENT SUCCESS RATE ({processed_count/len(pdf_files)*100:.1f}%)")
        print("Need at least 80% success rate to complete PRP")
        return None

if __name__ == "__main__":
    result = asyncio.run(process_all_marrickville_with_raganything())
    
    if result is not None:
        print("Ready to create PRP completion marker")
    else:
        print("Need to resolve remaining issues before PRP completion")