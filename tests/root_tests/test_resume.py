#!/usr/bin/env python3
"""
Test Resume Logic
"""
import json
import sys
sys.path.append('.')

from ultimate_multimodal_pipeline import UltimateMultimodalPipeline

def test_resume():
    print("Loading resume config...")
    with open('resume_config.json', 'r') as f:
        config = json.load(f)
    
    remaining_docs = config['remaining_documents']
    print(f"Remaining docs: {len(remaining_docs)}")
    
    print("Initializing pipeline...")
    pipeline = UltimateMultimodalPipeline()
    
    print("Setting document override...")
    pipeline.documents = remaining_docs
    print(f"Pipeline.documents set to {len(pipeline.documents)} documents")
    
    print("Testing document loading logic...")
    # Test the document loading logic directly
    import sqlite3
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    
    if hasattr(pipeline, 'documents') and pipeline.documents:
        placeholders = ','.join('?' * len(pipeline.documents))
        cursor.execute(f"SELECT id, pdf_name, full_text FROM documents WHERE pdf_name IN ({placeholders}) AND char_count > 500 ORDER BY char_count", pipeline.documents)
        documents = cursor.fetchall()
        print(f"RESUME MODE: Found {len(documents)} documents in database")
        for i, (doc_id, pdf_name, full_text_len) in enumerate(documents[:3]):
            print(f"  {i+1}. {pdf_name} (ID: {doc_id}, text length: {len(full_text_len) if full_text_len else 0})")
    
    conn.close()
    print("Test complete!")

if __name__ == "__main__":
    test_resume()