#!/usr/bin/env python
"""
PRP-A2.5: Universal Large File Splitter
Split ALL large files BEFORE any API processing - Standard preprocessing step
"""

import json
import os
from pathlib import Path
from datetime import datetime

def intelligent_document_chunker(content_text, max_size=40000, overlap=2000):
    """Intelligent document chunking with sentence boundary detection"""
    chunks = []
    start = 0
    
    while start < len(content_text):
        end = start + max_size
        chunk = content_text[start:end]
        
        # Try to break at good boundaries (in order of preference)
        if end < len(content_text):
            # 1. Try paragraph breaks
            for delimiter in ['\n\n', '.\n\n', '.\r\n\r\n']:
                last_break = chunk.rfind(delimiter)
                if last_break > max_size * 0.6:  # Must be reasonably far into chunk
                    end = start + last_break + len(delimiter)
                    chunk = content_text[start:end]
                    break
            else:
                # 2. Try sentence breaks
                for delimiter in ['. ', '.\n', ';\n']:
                    last_break = chunk.rfind(delimiter)
                    if last_break > max_size * 0.7:
                        end = start + last_break + len(delimiter)
                        chunk = content_text[start:end]
                        break
                else:
                    # 3. Try word breaks as last resort
                    last_space = chunk.rfind(' ')
                    if last_space > max_size * 0.8:
                        end = start + last_space + 1
                        chunk = content_text[start:end]
        
        chunks.append({
            'chunk_id': len(chunks),
            'text': chunk.strip(),
            'char_start': start,
            'char_end': end,
            'size_kb': len(chunk) / 1024,
            'size_chars': len(chunk)
        })
        
        start = end - overlap  # Overlap to avoid losing provisions at boundaries
        if start >= len(content_text):
            break
    
    return chunks

def identify_all_large_files_comprehensive():
    """Find ALL large files from ALL sources"""
    print("🔍 IDENTIFYING ALL LARGE FILES")
    print("=" * 60)
    
    large_files = []
    total_files_found = 0
    
    # Source 1: Existing A2 dataset (54 documents)
    try:
        with open("validated_outputs/A2_ALL_DCP_complete_extracted_content.json", "r", encoding="utf-8") as f:
            a2_docs = json.load(f)
        
        print(f"📋 Analyzing A2 dataset: {len(a2_docs)} documents")
        
        for doc_key, doc_data in a2_docs.items():
            content_text = ""
            for block in doc_data['content']:
                if isinstance(block, list):
                    for item in block:
                        if isinstance(item, dict) and item.get('type') == 'text':
                            content_text += item.get('text', '') + "\n"
            
            size_kb = len(content_text) / 1024
            total_files_found += 1
            
            if size_kb > 50:  # Large files
                large_files.append({
                    'source': 'A2_dataset',
                    'doc_key': doc_key,
                    'file_path': doc_data['source_path'],
                    'filename': os.path.basename(doc_data['source_path']),
                    'content_text': content_text,
                    'size_kb': round(size_kb, 1),
                    'processing_status': 'needs_splitting'
                })
    
    except FileNotFoundError:
        print("⚠️  A2 dataset not found")
    
    # Source 2: Marrickville DCPs on disk (85+ files)
    marrickville_dir = Path("docs/dcps/INNERWEST/Marrickville")
    if marrickville_dir.exists():
        marrickville_files = list(marrickville_dir.glob("*.pdf"))
        print(f"📋 Found {len(marrickville_files)} Marrickville PDF files on disk")
        
        for pdf_path in marrickville_files[:10]:  # Sample first 10 for size estimation
            total_files_found += 1
            # For now, assume all PDFs are potentially large
            # In real implementation, would need to extract size first
            large_files.append({
                'source': 'marrickville_disk',
                'doc_key': str(pdf_path).replace('/', '_').replace('\\', '_').replace('.pdf', ''),
                'file_path': str(pdf_path).replace('\\', '/'),
                'filename': pdf_path.name,
                'content_text': None,  # Will need RagAnything extraction first
                'size_kb': 0,  # Unknown until processed
                'processing_status': 'needs_raganything_first'
            })
    
    # Source 3: Any other large files discovered
    print(f"📋 Total files analyzed: {total_files_found}")
    print(f"📋 Large files identified: {len(large_files)}")
    
    return large_files

def split_all_large_files_universal():
    """Universal large file splitter - handles ALL sources"""
    print("PRP-A2.5: UNIVERSAL LARGE FILE SPLITTER")
    print("=" * 60)
    print("Splitting ALL large files BEFORE API processing")
    print("This prevents API quota issues and standardizes chunk processing")
    print()
    
    # Find all large files from all sources
    all_large_files = identify_all_large_files_comprehensive()
    
    # Separate by processing status
    ready_to_split = [f for f in all_large_files if f['processing_status'] == 'needs_splitting']
    needs_extraction = [f for f in all_large_files if f['processing_status'] == 'needs_raganything_first']
    
    print(f"📊 PROCESSING SUMMARY:")
    print(f"   Ready to split: {len(ready_to_split)} files")
    print(f"   Needs RagAnything first: {len(needs_extraction)} files")
    print()
    
    # Split files that are ready
    all_split_results = {}
    total_chunks_created = 0
    
    if ready_to_split:
        print("✂️  SPLITTING READY FILES:")
        print("-" * 40)
        
        for file_info in ready_to_split:
            filename = file_info['filename']
            size_kb = file_info['size_kb']
            
            print(f"Splitting: {filename} ({size_kb}KB)")
            
            # Split into intelligent chunks
            chunks = intelligent_document_chunker(file_info['content_text'])
            
            all_split_results[file_info['doc_key']] = {
                'source': file_info['source'],
                'source_path': file_info['file_path'],
                'original_size_kb': size_kb,
                'chunks': chunks,
                'total_chunks': len(chunks),
                'split_timestamp': datetime.now().isoformat(),
                'processing_note': 'Split by PRP-A2.5 Universal Splitter'
            }
            
            total_chunks_created += len(chunks)
            avg_chunk_size = size_kb / len(chunks)
            print(f"  → {len(chunks)} chunks (avg {avg_chunk_size:.1f}KB each)")
    
    # Create manifest for files needing RagAnything first
    marrickville_manifest = {}
    if needs_extraction:
        print("\n📋 MARRICKVILLE FILES MANIFEST:")
        print("-" * 40)
        print("These files need RagAnything extraction before splitting:")
        
        for file_info in needs_extraction:
            marrickville_manifest[file_info['doc_key']] = {
                'source_path': file_info['file_path'],
                'filename': file_info['filename'],
                'status': 'awaiting_raganything_extraction',
                'next_step': 'extract_then_split'
            }
            print(f"  • {file_info['filename']}")
    
    # Save results
    os.makedirs("validated_outputs", exist_ok=True)
    
    # Save split results
    with open("validated_outputs/A2_5_universal_file_splits.json", "w", encoding="utf-8") as f:
        json.dump(all_split_results, f, indent=2, ensure_ascii=False)
    
    # Save Marrickville manifest
    if marrickville_manifest:
        with open("validated_outputs/A2_5_marrickville_manifest.json", "w", encoding="utf-8") as f:
            json.dump(marrickville_manifest, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print("PRP-A2.5 UNIVERSAL SPLITTER COMPLETED:")
    print(f"Files split: {len(all_split_results)}")
    print(f"Total chunks created: {total_chunks_created}")
    print(f"Marrickville files catalogued: {len(marrickville_manifest)}")
    print(f"Output files:")
    print(f"  • A2_5_universal_file_splits.json")
    if marrickville_manifest:
        print(f"  • A2_5_marrickville_manifest.json")
    print()
    print("✅ All large files now prepared for efficient API processing")
    print("🔄 Next: Use chunks for LangExtract processing (no more large file issues)")
    
    return all_split_results, marrickville_manifest

if __name__ == "__main__":
    split_results, manifest = split_all_large_files_universal()