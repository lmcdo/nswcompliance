#!/usr/bin/env python
"""
PRP-A2-EXT: Process 85 Marrickville DCP files using RagAnything with PyPDF parser
Following the exact same approach that worked for A2 processing
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from raganything import RAGAnything
from raganything.config import RAGAnythingConfig

async def process_marrickville_with_pypdf_parser():
    print("PRP-A2-EXT: MARRICKVILLE DCP PROCESSING WITH RAGANYTHING (PyPDF)")
    print("=" * 70)
    print("Using PyPDF parser to avoid mineru dependency - same as A2 processing")
    print()
    
    # Initialize RagAnything processor with PyPDF parser (same as A2)
    config = RAGAnythingConfig()
    config.parser = 'pypdf'  # Use PyPDF instead of mineru
    rag = RAGAnything(config=config)
    
    # Find all Marrickville PDF files
    marrickville_dir = Path("docs/dcps/INNERWEST/Marrickville")
    pdf_files = list(marrickville_dir.glob("*.pdf"))
    
    print(f"Found {len(pdf_files)} Marrickville PDF files")
    print("Using PyPDF parser (same configuration that worked for A2)")
    print()
    
    all_extracted_content = {}
    processed_count = 0
    
    for pdf_path in sorted(pdf_files):
        print(f"Processing [{processed_count+1}/{len(pdf_files)}]: {pdf_path.name}")
        
        try:
            # Extract content from each PDF using RagAnything + PyPDF
            extracted_content = await rag.parse_document(str(pdf_path))
            
            # Store with exact same format as A2 processing
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
                temp_file = f"validated_outputs/A2_EXT_pypdf_progress_{processed_count}.json"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(all_extracted_content, f, indent=2, ensure_ascii=False)
                print(f"Progress saved: {processed_count}/{len(pdf_files)} files")
                    
        except Exception as e:
            print(f"FAILED: {pdf_path.name} - {str(e)}")
            break  # Stop on first failure to debug
    
    # Save final results
    os.makedirs("validated_outputs", exist_ok=True)
    output_file = "validated_outputs/A2_EXT_marrickville_pypdf_raganything.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_extracted_content, f, indent=2, ensure_ascii=False)
    
    print(f"\nRagAnything + PyPDF Results:")
    print(f"Successful: {processed_count}/{len(pdf_files)} files")
    print(f"Output: {output_file}")
    
    if processed_count == len(pdf_files):
        print("\nPRP-A2-EXT: COMPLETED WITH RAGANYTHING")
        return all_extracted_content
    else:
        print(f"\nOnly {processed_count}/{len(pdf_files)} completed")
        return None

if __name__ == "__main__":
    result = asyncio.run(process_marrickville_with_pypdf_parser())
    
    if result is not None:
        print("✓ PRP-A2-EXT completed with RagAnything + PyPDF parser")
    else:
        print("✗ PRP-A2-EXT failed")