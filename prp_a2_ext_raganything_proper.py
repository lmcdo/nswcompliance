#!/usr/bin/env python
"""
PRP-A2-EXT: Process 85 Marrickville DCP files using RagAnything properly
Following PRP specification exactly - must use RagAnything, not alternative methods
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from raganything import RAGAnything
from raganything.config import RAGAnythingConfig

async def process_marrickville_with_raganything():
    print("PRP-A2-EXT: MARRICKVILLE DCP PROCESSING WITH RAGANYTHING")
    print("=" * 60)
    print("Following PRP specification - using RagAnything for PDF processing")
    print()
    
    # Configure RagAnything to avoid mineru dependency issues
    config = RAGAnythingConfig()
    
    # Try to force it to use a different parser
    try:
        config.pdf_parser = "pypdf"  # Try to use pypdf backend
    except:
        pass
        
    rag = RAGAnything(config=config)
    
    # Find all Marrickville PDF files
    marrickville_dir = Path("docs/dcps/INNERWEST/Marrickville")
    pdf_files = list(marrickville_dir.glob("*.pdf"))
    
    print(f"Found {len(pdf_files)} Marrickville PDF files")
    print("Processing with RagAnything as per PRP specification...")
    print()
    
    all_extracted_content = {}
    processed_count = 0
    failed_count = 0
    
    for pdf_path in sorted(pdf_files):
        print(f"Processing [{processed_count+1}/{len(pdf_files)}]: {pdf_path.name}")
        
        try:
            # Use RagAnything parse_document method
            extracted_content = await rag.parse_document(str(pdf_path))
            
            # Store with file path as key
            file_key = str(pdf_path).replace('\\', '/').replace('/', '_').replace('.pdf', '')
            all_extracted_content[file_key] = {
                "source_path": str(pdf_path).replace('\\', '/'),
                "content": extracted_content,
                "processed_timestamp": datetime.now().isoformat(),
                "file_size_kb": pdf_path.stat().st_size / 1024,
                "processing_stage": "A2_EXT_marrickville_raganything",
                "extraction_method": "raganything"
            }
            
            processed_count += 1
            print(f"SUCCESS: Completed {processed_count}/{len(pdf_files)} files")
            
            # Save progress every 10 files
            if processed_count % 10 == 0:
                progress_file = "validated_outputs/A2_EXT_progress.json"
                with open(progress_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "processed": processed_count,
                        "total": len(pdf_files),
                        "last_update": datetime.now().isoformat()
                    }, f, indent=2)
                    
        except Exception as e:
            print(f"FAILED: {pdf_path.name} - {str(e)}")
            failed_count += 1
            
            # Store failed entry to track what didn't work
            file_key = str(pdf_path).replace('\\', '/').replace('/', '_').replace('.pdf', '')
            all_extracted_content[file_key] = {
                "source_path": str(pdf_path).replace('\\', '/'),
                "content": None,
                "error": str(e),
                "processed_timestamp": datetime.now().isoformat(),
                "file_size_kb": pdf_path.stat().st_size / 1024,
                "processing_stage": "A2_EXT_marrickville_failed",
                "extraction_method": "raganything_failed"
            }
            
            # If too many failures, we need to address the underlying issue
            if failed_count > 10:
                print(f"\nToo many failures ({failed_count}). Likely configuration issue.")
                print("Need to resolve RagAnything dependencies properly.")
                break
    
    # Save final results
    os.makedirs("validated_outputs", exist_ok=True)
    output_file = "validated_outputs/A2_EXT_marrickville_raganything.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_extracted_content, f, indent=2, ensure_ascii=False)
    
    print(f"\nRagAnything processing completed:")
    print(f"Successful: {processed_count}/{len(pdf_files)} files")
    print(f"Failed: {failed_count}/{len(pdf_files)} files")
    print(f"Output: {output_file}")
    
    # If we have too many failures, this indicates the approach needs fixing
    if failed_count > len(pdf_files) * 0.5:
        print("\nWARNING: High failure rate indicates RagAnything configuration issue")
        print("This violates PRP specification requirement to use RagAnything")
        return None
    
    return all_extracted_content

if __name__ == "__main__":
    extracted_data = asyncio.run(process_marrickville_with_raganything())
    
    if extracted_data is not None:
        print("\nPRP-A2-EXT: RagAnything processing completed successfully")
    else:
        print("\nPRP-A2-EXT: RagAnything processing failed - need to resolve dependencies")