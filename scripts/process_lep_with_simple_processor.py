#!/usr/bin/env python3
"""
Process LEP PDF using the same SimplePDFProcessor that worked for DCPs
This creates text chunks just like the DCP processing for consistent pipeline
"""

import os
import sys
import json
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / 'src'))

from src.processing.simple_pdf_processor import SimplePDFProcessor

def process_lep_document():
    """Process LEP using the same method as DCPs"""
    
    # Paths
    lep_pdf_path = project_root / "docs" / "lep" / "Inner West Local Environmental Plan 2022 - NSW Legislation.pdf"
    output_dir = project_root / "temp_extraction_LEP"
    
    if not lep_pdf_path.exists():
        print(f"LEP PDF not found at {lep_pdf_path}")
        return False
    
    print(f"Processing LEP document: {lep_pdf_path}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Initialize the same processor used for DCPs
        print("Initializing SimplePDFProcessor...")
        pdf_processor = SimplePDFProcessor(chunk_size=800, chunk_overlap=100)
        
        # Extract text using PyMuPDF (same as DCPs)
        print("Extracting text with PyMuPDF...")
        text = pdf_processor.extract_text_from_pdf(str(lep_pdf_path))
        
        if not text:
            print("ERROR: No text extracted from LEP PDF")
            return False
        
        print(f"SUCCESS: Extracted {len(text)} characters from LEP PDF")
        
        # Chunk text for processing (same as DCPs)
        print("Chunking text for regulatory content...")
        chunks = pdf_processor.chunk_regulatory_text(text)
        print(f"SUCCESS: Found {len(chunks)} regulatory chunks")
        
        if not chunks:
            print("WARNING: No regulatory chunks found")
            return False
        
        # Save chunks to files (same format as DCPs)
        print("Saving chunks to files...")
        for i, chunk in enumerate(chunks):
            chunk_filename = f"lep_chunk_{i}.txt"
            chunk_path = os.path.join(output_dir, chunk_filename)
            
            with open(chunk_path, 'w', encoding='utf-8') as f:
                f.write(f"# LEP Chunk {i}\n")
                f.write(f"# Source: Inner West Local Environmental Plan 2022\n")
                f.write(f"# Length: {len(chunk)} characters\n\n")
                f.write(chunk)
        
        # Create metadata (same format as DCPs)
        metadata = {
            "source_document": "Inner West Local Environmental Plan 2022",
            "processing_date": "2025-08-25",
            "total_chunks": len(chunks),
            "total_characters": len(text),
            "extraction_method": "simple_pdf_processor_pymupdf",
            "processor": "SimplePDFProcessor",
            "chunk_size": 800,
            "chunk_overlap": 100,
            "keywords_used": pdf_processor.setback_keywords
        }
        
        metadata_path = os.path.join(output_dir, "lep_extraction_metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"\nSUCCESS: LEP processing completed")
        print(f"- Extracted {len(chunks)} text chunks")
        print(f"- Chunks saved to: {output_dir}")
        print(f"- Metadata saved to: {metadata_path}")
        
        # Show some sample chunk content
        if len(chunks) > 0:
            print(f"\nSample chunk content (first 200 chars):")
            print(f"Chunk 0: {chunks[0][:200]}...")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to process LEP: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main execution"""
    print("NSW LEP Document Processing - Using SimplePDFProcessor")
    print("=" * 60)
    
    success = process_lep_document()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())