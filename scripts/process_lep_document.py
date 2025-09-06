#!/usr/bin/env python3
"""
Process LEP PDF to extract height and FSR clauses using RAG-Anything + AutoSchemaKG
Uses the exact same approach as DCP processing but with LEP document
"""

import os
import sys
import json
import re
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / 'src'))

try:
    from raganything import RAGAnything, RAGAnythingConfig
    print("RAG-Anything imported successfully")
except ImportError as e:
    print(f"Error importing RAG-Anything: {e}")
    print("Install with: ./venv_linux/Scripts/pip.exe install git+https://github.com/HKUDS/RAG-Anything.git")
    sys.exit(1)

try:
    from atlas_rag.kg_construction.triple_extraction import KnowledgeGraphExtractor
    from atlas_rag.kg_construction.triple_config import ProcessingConfig
    from atlas_rag.llm_generator import LLMGenerator
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    AUTOSCHEMA_AVAILABLE = True
    print("AutoSchemaKG imported successfully")
except ImportError as e:
    print(f"Warning: AutoSchemaKG (atlas_rag) not available: {e}")
    AUTOSCHEMA_AVAILABLE = False

def extract_text_with_raganything(pdf_path: str) -> str:
    """Extract text from LEP PDF using RAG-Anything with MinerU"""
    # Set up environment for RAG-Anything
    venv_scripts_path = project_root / "venv_linux" / "Scripts"
    if venv_scripts_path.exists():
        current_path = os.environ.get('PATH', '')
        if str(venv_scripts_path) not in current_path:
            os.environ['PATH'] = f"{venv_scripts_path};{current_path}"
    
    config = RAGAnythingConfig(
        enable_table_processing=True,
        enable_image_processing=True,
        max_context_tokens=4000,
        context_mode='document',
        pdf_parser='pymupdf'  # Use PyMuPDF instead of MinerU for Windows compatibility
    )
    
    async def extract_async():
        rag = RAGAnything(config=config)
        parsed_data = await rag.parse_document(pdf_path)
        return parsed_data
    
    # Run async extraction
    parsed_data = asyncio.run(extract_async())
    
    # Extract text from parsed data
    full_text = ""
    if hasattr(parsed_data, 'text_content'):
        full_text = parsed_data.text_content
    elif hasattr(parsed_data, 'content'):
        full_text = parsed_data.content
    elif isinstance(parsed_data, dict):
        for field in ['text', 'content', 'body', 'extracted_text', 'pages']:
            if field in parsed_data:
                if isinstance(parsed_data[field], list):
                    full_text = '\n'.join(str(page) for page in parsed_data[field])
                else:
                    full_text = str(parsed_data[field])
                break
        if not full_text:
            full_text = str(parsed_data)
    elif isinstance(parsed_data, str):
        full_text = parsed_data
    else:
        full_text = str(parsed_data)
    
    return full_text

def chunk_regulatory_text(text: str) -> List[str]:
    """Chunk text for regulatory processing"""
    # Simple chunking approach
    words = text.split()
    chunks = []
    chunk_size = 800
    overlap = 100
    
    i = 0
    while i < len(words):
        chunk_end = min(i + chunk_size, len(words))
        current_chunk_words = words[i:chunk_end]
        chunk_text = ' '.join(current_chunk_words)
        
        # Filter for regulatory content
        chunk_lower = chunk_text.lower()
        regulatory_keywords = [
            "height", "building", "maximum", "metres", "meters", "floor space ratio", 
            "fsr", "clause", "development", "residential", "commercial", "zone",
            "subdivision", "storey", "storeys", "stories", "story", "setback"
        ]
        
        if (len(chunk_text.strip()) > 100 and 
            any(keyword in chunk_lower for keyword in regulatory_keywords)):
            chunks.append(chunk_text)
        
        # Move forward with overlap
        overlap_words = chunk_size // 4
        i = max(i + chunk_size - overlap_words, i + 1)
    
    return chunks

def extract_with_autoschema(text_chunks: List[str], area: str, file_path: str) -> Dict[str, Any]:
    """Use AutoSchemaKG for enhanced semantic extraction - exact same as DCP processing"""
    if not AUTOSCHEMA_AVAILABLE:
        return {}
    
    try:
        # Initialize OpenAI client and LLM Generator
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key or api_key == 'your_openai_api_key_here':
            print("   Warning: OpenAI API key not configured, skipping AutoSchemaKG extraction")
            return {}
        
        # Set up OpenAI client
        client = OpenAI(api_key=api_key)
        model_name = "gpt-3.5-turbo"
        
        # Initialize LLM Generator
        triple_generator = LLMGenerator(client, model_name=model_name)
        
        # Create a temporary directory for processing - SAME AS DCPs
        temp_output_dir = f"temp_extraction_{area}"
        os.makedirs(temp_output_dir, exist_ok=True)
        
        # Write text chunks to temporary files for processing - SAME AS DCPs
        temp_files = []
        for i, chunk in enumerate(text_chunks):
            if len(chunk.strip()) < 100:  # Skip very short chunks
                continue
            
            temp_file = os.path.join(temp_output_dir, f"chunk_{i}.txt")
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(chunk)
            temp_files.append(temp_file)
        
        if not temp_files:
            print("   Warning: No suitable text chunks for AutoSchemaKG processing")
            return {}
        
        # Configure AutoSchemaKG processing - SAME AS DCPs
        kg_extraction_config = ProcessingConfig(
            model_path=model_name,
            data_directory=temp_output_dir,
            filename_pattern="*.txt",
            batch_size_triple=2,
            batch_size_concept=8,
            output_directory=f"{temp_output_dir}/output",
            max_new_tokens=1024,
            max_workers=1,
            remove_entity_metadata=False
        )
        
        # Initialize KnowledgeGraphExtractor - SAME AS DCPs
        kg_extractor = KnowledgeGraphExtractor(
            triple_generator=triple_generator,
            config=kg_extraction_config
        )
        
        print(f"   Running AutoSchemaKG extraction on {len(temp_files)} chunks...")
        
        # Run knowledge graph extraction - SAME AS DCPs
        extracted_triples = kg_extractor.extract_triples()
        
        # Process extracted triples for LEP rules (height/FSR instead of setbacks)
        lep_rules = {}
        
        if extracted_triples:
            for triple in extracted_triples:
                if isinstance(triple, dict):
                    subject = triple.get('subject', '').lower()
                    predicate = triple.get('predicate', '').lower()
                    obj = triple.get('object', '').lower()
                    
                    # Look for height and FSR relationships
                    if any(term in subject for term in ['height', 'building', 'storey']):
                        if any(term in predicate for term in ['maximum', 'limit', 'requirement']):
                            import re
                            numbers = re.findall(r'\d+(?:\.\d+)?', obj)
                            if numbers:
                                value = float(numbers[0])
                                lep_rules['height'] = {
                                    'value': value,
                                    'source_triple': f"{subject} -> {predicate} -> {obj}",
                                    'extraction_confidence': 0.8,
                                    'source_file': os.path.basename(file_path),
                                    'extraction_method': 'autoschema_kg'
                                }
                    
                    if any(term in subject for term in ['floor space ratio', 'fsr']):
                        if any(term in predicate for term in ['maximum', 'limit', 'requirement']):
                            import re
                            numbers = re.findall(r'\d+(?:\.\d+)?', obj)
                            if numbers:
                                value = float(numbers[0])
                                lep_rules['fsr'] = {
                                    'value': value,
                                    'source_triple': f"{subject} -> {predicate} -> {obj}",
                                    'extraction_confidence': 0.8,
                                    'source_file': os.path.basename(file_path),
                                    'extraction_method': 'autoschema_kg'
                                }
        
        print(f"   AutoSchemaKG extracted {len(lep_rules)} LEP rule types")
        return lep_rules
        
    except Exception as e:
        print(f"   Error in AutoSchemaKG processing: {e}")
        import traceback
        traceback.print_exc()
        return {}

def main():
    """Main processing function - exact same structure as DCP processing"""
    print("NSW LEP Document Processing - Using RAG-Anything + AutoSchemaKG")
    print("=" * 60)
    
    if AUTOSCHEMA_AVAILABLE:
        print("SUCCESS: AutoSchemaKG available - using semantic extraction")
    else:
        print("WARNING: AutoSchemaKG not available - using RAG-Anything only")
    
    # Process LEP document
    lep_pdf_path = project_root / "docs" / "lep" / "Inner West Local Environmental Plan 2022 - NSW Legislation.pdf"
    
    if not lep_pdf_path.exists():
        print(f"ERROR: LEP PDF not found at {lep_pdf_path}")
        return False
    
    print(f"\nProcessing: {lep_pdf_path.name}")
    
    try:
        # Extract text using RAG-Anything (instead of SimplePDFProcessor)
        print("   Extracting text with RAG-Anything...")
        text = extract_text_with_raganything(str(lep_pdf_path))
        
        if not text:
            print("   ERROR: No text extracted from LEP PDF")
            return False
        
        print(f"   SUCCESS: Extracted {len(text)} characters")
        
        # Chunk text for processing
        print("   Chunking text for regulatory content...")
        chunks = chunk_regulatory_text(text)
        print(f"   SUCCESS: Found {len(chunks)} regulatory chunks")
        
        if not chunks:
            print("   WARNING: No regulatory chunks found")
            return False
        
        # Try AutoSchemaKG if available - SAME AS DCPs
        autoschema_rules = {}
        if AUTOSCHEMA_AVAILABLE:
            print("   Extracting rules with AutoSchemaKG semantic processing...")
            autoschema_rules = extract_with_autoschema(chunks, "LEP", str(lep_pdf_path))
            
            if autoschema_rules:
                print(f"   SUCCESS: AutoSchemaKG extracted {len(autoschema_rules)} rule types")
        
        # Create final output
        final_output = {
            "source_document": "Inner West Local Environmental Plan 2022",
            "processing_date": datetime.now().isoformat(),
            "total_chunks": len(chunks),
            "total_characters": len(text),
            "extraction_method": "raganything_autoschema",
            "autoschema_rules": autoschema_rules,
            "processing_metadata": {
                "rag_anything_used": True,
                "autoschema_available": AUTOSCHEMA_AVAILABLE,
                "chunk_size": 800,
                "chunk_overlap": 100
            }
        }
        
        # Save metadata
        output_dir = project_root / "public" / "regulatory-data"
        os.makedirs(output_dir, exist_ok=True)
        
        metadata_path = output_dir / "lep_extraction_results.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
        
        print(f"\nSUCCESS: LEP processing completed using RAG-Anything + AutoSchemaKG")
        print(f"- Text extracted with RAG-Anything: {len(text)} characters")
        print(f"- Regulatory chunks created: {len(chunks)}")
        print(f"- AutoSchemaKG rules extracted: {len(autoschema_rules)}")
        print(f"- Results saved to: {metadata_path}")
        
        # Show chunk files created
        temp_dir = project_root / "temp_extraction_LEP"
        if temp_dir.exists():
            chunk_files = list(temp_dir.glob("chunk_*.txt"))
            print(f"- Chunk files created: {len(chunk_files)}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to process LEP: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)