#!/usr/bin/env python3
"""
Simple LightRAG Test
Test LightRAG with existing text chunks to validate integration
"""

import os
import json
import asyncio
from pathlib import Path
import logging

# Set up environment
os.environ['OPENAI_API_KEY'] = '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'

from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc
import openai
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_lightrag_with_existing_chunks():
    """Test LightRAG with existing text chunks"""
    
    logger.info("Testing LightRAG with existing text chunks...")
    
    # Setup OpenAI client
    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    async def openai_complete(prompt, **kwargs):
        """Simple OpenAI completion function for LightRAG"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=kwargs.get('max_tokens', 1000),
            temperature=kwargs.get('temperature', 0.1)
        )
        return response.choices[0].message.content
    
    async def openai_embedding(texts):
        """OpenAI embedding function for LightRAG"""
        if isinstance(texts, str):
            texts = [texts]
        
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        
        embeddings = np.array([item.embedding for item in response.data])
        return embeddings if len(embeddings) > 1 else embeddings[0]
    
    # Create embedding function
    embedding_func = EmbeddingFunc(
        embedding_dim=1536,  # text-embedding-3-small dimension
        max_token_size=8191,  # Max tokens for text-embedding-3-small
        func=openai_embedding
    )
    
    # Initialize LightRAG
    lightrag = LightRAG(
        working_dir="./lightrag_test_storage",
        llm_model_func=openai_complete,
        embedding_func=embedding_func,
        llm_model_name="gpt-4o-mini"
    )
    
    # Test with existing Ashfield chunks
    ashfield_path = Path("temp_extraction_Ashfield")
    if ashfield_path.exists():
        logger.info(f"Found Ashfield chunks: {len(list(ashfield_path.glob('*.txt')))} files")
        
        # Read and insert text chunks
        for chunk_file in ashfield_path.glob("*.txt"):
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content:
                        logger.info(f"Inserting {chunk_file.name} ({len(content)} chars)...")
                        await lightrag.ainsert(content)
            except Exception as e:
                logger.error(f"Failed to insert {chunk_file.name}: {e}")
    
    # Test queries
    test_queries = [
        "What are the setback requirements?",
        "What are the minimum distances for side setbacks?", 
        "What are the front setback rules?",
        "What are the building height restrictions?",
        "Can I build a duplex?"
    ]
    
    results = {}
    
    for query in test_queries:
        logger.info(f"Testing query: {query}")
        try:
            response = await lightrag.aquery(
                query,
                param=QueryParam(mode="hybrid", only_need_context=False)
            )
            results[query] = response
            logger.info(f"  ✓ Response: {str(response)[:100]}...")
        except Exception as e:
            logger.error(f"  ✗ Query failed: {e}")
            results[query] = f"Error: {str(e)}"
    
    # Save results
    output_file = Path("public/regulatory-data/lightrag_test_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"Test results saved to: {output_file}")
    
    # Print summary
    logger.info("=" * 50)
    logger.info("LightRAG Test Results:")
    for query, response in results.items():
        status = "✓" if not response.startswith("Error") else "✗"
        logger.info(f"{status} {query}")
    
    return results

if __name__ == "__main__":
    # Set up event loop for Windows
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(test_lightrag_with_existing_chunks())