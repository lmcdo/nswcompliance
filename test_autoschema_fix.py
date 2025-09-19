#!/usr/bin/env python3
"""
Test AutoSchema on existing processed documents
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from atlas_rag.kg_construction.triple_extraction import KnowledgeGraphExtractor
from atlas_rag.kg_construction.triple_config import ProcessingConfig  
from atlas_rag.llm_generator import LLMGenerator
from openai import OpenAI

load_dotenv('.env.local')

def test_autoschema():
    api_key = os.getenv('OPENAI_API_KEY')
    
    # Setup
    client = OpenAI(api_key=api_key)
    triple_generator = LLMGenerator(client, model_name='gpt-4o-mini')
    
    # Use ONE document for testing
    test_doc = "output/Inner West Ashfield DCP 2016 - Chapter A - Miscellaneous - with IWLEP 2022 amendments/auto/Inner West Ashfield DCP 2016 - Chapter A - Miscellaneous - with IWLEP 2022 amendments_content_list.json"
    
    if not os.path.exists(test_doc):
        print(f"Test document not found: {test_doc}")
        return False
    
    # Load content
    with open(test_doc, 'r', encoding='utf-8') as f:
        content_data = json.load(f)
    
    # Extract text
    text_chunks = [item.get('text', '') for item in content_data if item.get('text', '').strip()]
    
    if not text_chunks:
        print("No text chunks found")
        return False
    
    print(f"Found {len(text_chunks)} text chunks")
    
    # Create temp directory with text files
    temp_dir = os.path.abspath("autoschema_test")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Debug chunk sizes
    chunk_sizes = [len(chunk.strip()) for chunk in text_chunks[:10]]
    print(f"First 10 chunk sizes: {chunk_sizes}")
    
    # Write first few chunks to test
    files_written = 0
    for i, chunk in enumerate(text_chunks[:3]):  # Just test first 3 chunks
        if len(chunk.strip()) > 10:
            filename = f"{temp_dir}/chunk_{i}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(chunk.strip())
            files_written += 1
            print(f"Written file: {filename} ({len(chunk)} chars)")
    
    print(f"Total files written: {files_written}")
    
    # Configure AutoSchema
    config = ProcessingConfig(
        model_path='gpt-4o-mini',
        data_directory=temp_dir,
        filename_pattern='*.txt',
        batch_size_triple=1,
        batch_size_concept=1,
        output_directory=f"{temp_dir}_output",
        max_new_tokens=512,
        max_workers=1
    )
    
    try:
        # Run extraction
        print("Starting AutoSchema extraction...")
        kg_extractor = KnowledgeGraphExtractor(
            model=triple_generator,
            config=config
        )
        
        result = kg_extractor.run_extraction()
        print(f"AutoSchema extraction completed: {result}")
        return True
        
    except Exception as e:
        print(f"AutoSchema extraction failed: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = test_autoschema()
    if success:
        print("SUCCESS: AutoSchema HTTP 400 errors FIXED - extraction working")
    else:
        print("FAILED: AutoSchema still has issues")