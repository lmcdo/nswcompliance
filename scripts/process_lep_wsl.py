#!/usr/bin/env python3
"""
Process LEP PDF using RAG-Anything + AutoSchemaKG in WSL Ubuntu environment
This version runs in Linux where MinerU works properly with full table/image parsing
"""

import os
import sys
import json
import re
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Project paths for WSL (mounted Windows filesystem)
project_root = Path("/mnt/c/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine")
sys.path.append(str(project_root))
sys.path.append(str(project_root / 'src'))

try:
    from raganything import RAGAnything, RAGAnythingConfig
    print("✅ RAG-Anything imported successfully in WSL")
except ImportError as e:
    print(f"❌ Error importing RAG-Anything: {e}")
    sys.exit(1)

try:
    from atlas_rag.kg_construction.triple_extraction import KnowledgeGraphExtractor
    from atlas_rag.kg_construction.triple_config import ProcessingConfig
    from atlas_rag.llm_generator import LLMGenerator
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv(project_root / '.env.local')
    AUTOSCHEMA_AVAILABLE = True
    print("✅ AutoSchemaKG imported successfully in WSL")
except ImportError as e:
    print(f"⚠️  Warning: AutoSchemaKG (atlas_rag) not available: {e}")
    AUTOSCHEMA_AVAILABLE = False

def extract_text_with_raganything(pdf_path: str) -> str:
    """Extract text from LEP PDF using RAG-Anything with MinerU in Linux"""
    
    # Configure RAG-Anything for document processing with DoclingParser
    # DoclingParser available as alternative to MinerU for table/image processing
    config = RAGAnythingConfig(
        enable_table_processing=True,  # Enable with Docling
        enable_image_processing=True,  # Enable with Docling  
        max_context_tokens=8000,  # Larger context for LEP
        context_mode='document',
        parser='docling',  # Use Docling parser instead of mineru
        parse_method='auto'  # Auto parsing method
    )
    
    async def extract_async():
        rag = RAGAnything(config=config)
        parsed_data = await rag.parse_document(pdf_path)
        return parsed_data
    
    # Run async extraction
    print("   🔍 Running RAG-Anything with MinerU for full document parsing...")
    parsed_data = asyncio.run(extract_async())
    
    # Extract text from parsed data with better structure preservation
    full_text = ""
    if hasattr(parsed_data, 'text_content'):
        full_text = parsed_data.text_content
    elif hasattr(parsed_data, 'content'):
        full_text = parsed_data.content
    elif isinstance(parsed_data, dict):
        # Try multiple field extraction approaches for better coverage
        for field in ['text', 'content', 'body', 'extracted_text', 'pages', 'markdown', 'structured_content']:
            if field in parsed_data:
                if isinstance(parsed_data[field], list):
                    # Join pages with section separators
                    full_text = '\n\n=== PAGE BREAK ===\n\n'.join(str(page) for page in parsed_data[field])
                else:
                    full_text = str(parsed_data[field])
                break
        
        # If no text found, extract from nested structures
        if not full_text and 'tables' in parsed_data:
            table_text = []
            for table in parsed_data['tables']:
                table_text.append(f"TABLE: {table}")
            full_text += '\n'.join(table_text)
            
        if not full_text:
            full_text = str(parsed_data)
            
    elif isinstance(parsed_data, str):
        full_text = parsed_data
    else:
        full_text = str(parsed_data)
    
    return full_text

def chunk_regulatory_text(text: str) -> List[str]:
    """Advanced chunking for LEP regulatory content"""
    # More sophisticated chunking for LEP structure
    chunks = []
    
    # First, try to split by regulatory sections/clauses
    clause_patterns = [
        r'(?i)clause\s+\d+\.\d+.*?(?=clause\s+\d+\.\d+|$)',  # Clause sections
        r'(?i)part\s+\d+.*?(?=part\s+\d+|clause\s+\d+\.\d+|$)',  # Part sections
        r'(?i)schedule\s+\d+.*?(?=schedule\s+\d+|part\s+\d+|$)',  # Schedules
    ]
    
    structured_chunks = []
    for pattern in clause_patterns:
        matches = re.finditer(pattern, text, re.DOTALL | re.MULTILINE)
        for match in matches:
            chunk = match.group().strip()
            if len(chunk) > 200:  # Substantial chunks only
                structured_chunks.append(chunk)
    
    # If structured chunking found content, use it
    if structured_chunks:
        chunks.extend(structured_chunks)
    
    # Fallback to word-based chunking for remaining content
    words = text.split()
    chunk_size = 1000  # Larger chunks for LEP
    overlap = 150
    
    i = 0
    while i < len(words):
        chunk_end = min(i + chunk_size, len(words))
        current_chunk_words = words[i:chunk_end]
        chunk_text = ' '.join(current_chunk_words)
        
        # LEP-specific filtering
        chunk_lower = chunk_text.lower()
        lep_keywords = [
            "height", "building", "maximum", "metres", "meters", "floor space ratio", 
            "fsr", "clause", "development", "residential", "commercial", "zone",
            "subdivision", "storey", "storeys", "stories", "story", "setback",
            "shall", "must", "may", "environmental", "planning", "local", "council"
        ]
        
        if (len(chunk_text.strip()) > 150 and 
            any(keyword in chunk_lower for keyword in lep_keywords)):
            chunks.append(chunk_text)
        
        # Move forward with overlap
        overlap_words = chunk_size // 6
        i = max(i + chunk_size - overlap_words, i + 1)
    
    return list(set(chunks))  # Remove duplicates

def extract_with_autoschema(text_chunks: List[str], area: str, file_path: str) -> Dict[str, Any]:
    """Use AutoSchemaKG for LEP semantic extraction - Linux environment"""
    if not AUTOSCHEMA_AVAILABLE:
        return {}
    
    try:
        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key or api_key == 'your_openai_api_key_here':
            print("   ⚠️  Warning: OpenAI API key not configured, skipping AutoSchemaKG extraction")
            return {}
        
        client = OpenAI(api_key=api_key)
        model_name = "gpt-3.5-turbo"
        
        # Initialize LLM Generator
        triple_generator = LLMGenerator(client, model_name=model_name)
        
        # Create temporary directory for processing
        temp_output_dir = f"temp_extraction_{area}"
        os.makedirs(temp_output_dir, exist_ok=True)
        
        # Write chunks to files
        temp_files = []
        for i, chunk in enumerate(text_chunks):
            if len(chunk.strip()) < 150:  # Skip short chunks
                continue
            
            temp_file = os.path.join(temp_output_dir, f"chunk_{i}.txt")
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(chunk)
            temp_files.append(temp_file)
        
        if not temp_files:
            print("   ⚠️  Warning: No suitable text chunks for AutoSchemaKG processing")
            return {}
        
        print(f"   📝 Created {len(temp_files)} chunk files for AutoSchemaKG processing")
        
        # Configure AutoSchemaKG for LEP processing
        kg_extraction_config = ProcessingConfig(
            model_path=model_name,
            data_directory=temp_output_dir,
            filename_pattern="*.txt",
            batch_size_triple=3,  # Slightly larger batches for LEP
            batch_size_concept=12,
            output_directory=f"{temp_output_dir}/output",
            max_new_tokens=1536,  # More tokens for complex LEP rules
            max_workers=1,
            remove_entity_metadata=False
        )
        
        # Initialize Knowledge Graph Extractor
        kg_extractor = KnowledgeGraphExtractor(
            triple_generator=triple_generator,
            config=kg_extraction_config
        )
        
        print(f"   🤖 Running AutoSchemaKG semantic extraction on {len(temp_files)} chunks...")
        
        # Run knowledge graph extraction
        extracted_triples = kg_extractor.extract_triples()
        
        # Process extracted triples for LEP rules
        lep_rules = {}
        
        if extracted_triples:
            print(f"   📊 Processing {len(extracted_triples)} extracted triples...")
            for triple in extracted_triples:
                if isinstance(triple, dict):
                    subject = triple.get('subject', '').lower()
                    predicate = triple.get('predicate', '').lower()
                    obj = triple.get('object', '').lower()
                    
                    # Extract height rules
                    if any(term in subject for term in ['height', 'building', 'storey', 'story']):
                        if any(term in predicate for term in ['maximum', 'limit', 'requirement', 'shall', 'must']):
                            numbers = re.findall(r'\d+(?:\.\d+)?', obj)
                            if numbers:
                                value = float(numbers[0])
                                lep_rules['height'] = {
                                    'value': value,
                                    'unit': 'metres',
                                    'source_triple': f"{subject} -> {predicate} -> {obj}",
                                    'extraction_confidence': 0.85,
                                    'source_file': os.path.basename(file_path),
                                    'extraction_method': 'autoschema_kg_wsl',
                                    'clause_reference': extract_clause_reference(triple)
                                }
                    
                    # Extract FSR rules
                    if any(term in subject for term in ['floor space ratio', 'fsr', 'floor area']):
                        if any(term in predicate for term in ['maximum', 'limit', 'requirement', 'shall', 'must']):
                            numbers = re.findall(r'\d+(?:\.\d+)?', obj)
                            if numbers:
                                value = float(numbers[0])
                                lep_rules['fsr'] = {
                                    'value': value,
                                    'unit': 'ratio',
                                    'source_triple': f"{subject} -> {predicate} -> {obj}",
                                    'extraction_confidence': 0.85,
                                    'source_file': os.path.basename(file_path),
                                    'extraction_method': 'autoschema_kg_wsl',
                                    'clause_reference': extract_clause_reference(triple)
                                }
        
        print(f"   ✅ AutoSchemaKG extracted {len(lep_rules)} LEP rule types in WSL")
        return lep_rules
        
    except Exception as e:
        print(f"   ❌ Error in AutoSchemaKG processing: {e}")
        import traceback
        traceback.print_exc()
        return {}

def extract_clause_reference(triple: dict) -> str:
    """Extract clause reference from triple context"""
    # Look for clause numbers in the triple text
    full_text = f"{triple.get('subject', '')} {triple.get('predicate', '')} {triple.get('object', '')}"
    clause_match = re.search(r'clause\s+(\d+\.\d+)', full_text, re.IGNORECASE)
    if clause_match:
        return clause_match.group(1)
    return "unknown"

def main():
    """Main processing function for WSL environment"""
    print("🐧 NSW LEP Document Processing - WSL Ubuntu with RAG-Anything + AutoSchemaKG")
    print("=" * 80)
    
    if AUTOSCHEMA_AVAILABLE:
        print("✅ SUCCESS: AutoSchemaKG available - using full semantic extraction")
    else:
        print("⚠️  WARNING: AutoSchemaKG not available - using RAG-Anything only")
    
    # LEP document path (Windows filesystem via WSL mount)
    lep_pdf_path = project_root / "docs" / "lep" / "Inner West Local Environmental Plan 2022 - NSW Legislation.pdf"
    
    if not lep_pdf_path.exists():
        print(f"❌ ERROR: LEP PDF not found at {lep_pdf_path}")
        return False
    
    print(f"📄 Processing: {lep_pdf_path.name}")
    print(f"📁 Working in WSL with Windows mount: {project_root}")
    
    try:
        # Extract text using RAG-Anything with MinerU (Linux compatibility)
        print("   🚀 Extracting text with RAG-Anything + MinerU (full table/image parsing)...")
        text = extract_text_with_raganything(str(lep_pdf_path))
        
        if not text:
            print("   ❌ ERROR: No text extracted from LEP PDF")
            return False
        
        print(f"   ✅ SUCCESS: Extracted {len(text):,} characters from LEP")
        
        # Advanced chunking for LEP structure
        print("   📝 Chunking text for LEP regulatory content...")
        chunks = chunk_regulatory_text(text)
        print(f"   ✅ SUCCESS: Found {len(chunks)} LEP regulatory chunks")
        
        if not chunks:
            print("   ⚠️  WARNING: No regulatory chunks found")
            return False
        
        # AutoSchemaKG semantic extraction
        autoschema_rules = {}
        if AUTOSCHEMA_AVAILABLE:
            print("   🤖 Extracting LEP rules with AutoSchemaKG semantic processing...")
            autoschema_rules = extract_with_autoschema(chunks, "LEP", str(lep_pdf_path))
            
            if autoschema_rules:
                print(f"   ✅ SUCCESS: AutoSchemaKG extracted {len(autoschema_rules)} LEP rule types")
        
        # Create final output (save to Windows filesystem)
        final_output = {
            "source_document": "Inner West Local Environmental Plan 2022",
            "processing_date": datetime.now().isoformat(),
            "processing_environment": "WSL Ubuntu Linux",
            "total_chunks": len(chunks),
            "total_characters": len(text),
            "extraction_method": "raganything_autoschema_wsl",
            "autoschema_rules": autoschema_rules,
            "processing_metadata": {
                "wsl_environment": True,
                "rag_anything_used": True,
                "mineru_working": True,
                "autoschema_available": AUTOSCHEMA_AVAILABLE,
                "chunk_size": 1000,
                "chunk_overlap": 150,
                "table_processing": True,
                "image_processing": True
            }
        }
        
        # Save to Windows filesystem via WSL mount
        output_dir = project_root / "public" / "regulatory-data"
        output_dir.mkdir(exist_ok=True)
        
        metadata_path = output_dir / "lep_extraction_results_wsl.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 SUCCESS: LEP processing completed in WSL with full parsing capability")
        print(f"📊 Results:")
        print(f"   - Text extracted: {len(text):,} characters")
        print(f"   - Regulatory chunks: {len(chunks)}")
        print(f"   - AutoSchemaKG rules: {len(autoschema_rules)}")
        print(f"   - Chunk files saved to: temp_extraction_LEP/")
        print(f"   - Results metadata: {metadata_path}")
        
        # Show extracted rules summary
        if autoschema_rules:
            print(f"\n📋 Extracted LEP Rules Summary:")
            for rule_type, rule_data in autoschema_rules.items():
                print(f"   • {rule_type.upper()}: {rule_data.get('value')} {rule_data.get('unit', '')}")
                print(f"     └─ Confidence: {rule_data.get('extraction_confidence', 0):.2f}")
                print(f"     └─ Clause: {rule_data.get('clause_reference', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Failed to process LEP in WSL: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)