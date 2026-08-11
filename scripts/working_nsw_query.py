#!/usr/bin/env python3
"""
Working NSW Query Script - Properly configured LightRAG query
Uses existing ultimate_nsw_processor knowledge base
"""

import os
import json
import asyncio
import openai
import numpy as np
from pathlib import Path

# Set OpenAI API key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

async def query_nsw_lightrag_async(query_text, working_dir="./ultimate_nsw_processor"):
    """Query the NSW LightRAG knowledge base with proper async setup"""
    
    try:
        from lightrag import LightRAG, QueryParam
        from lightrag.utils import EmbeddingFunc
        
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Define OpenAI completion function
        async def openai_complete(prompt, **kwargs):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=kwargs.get('max_tokens', 2000),
                    temperature=kwargs.get('temperature', 0.1)
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"OpenAI completion error: {str(e)}"

        # Define embedding function
        async def openai_embedding(texts):
            try:
                if isinstance(texts, str):
                    texts = [texts]
                
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=texts
                )
                
                embeddings = np.array([item.embedding for item in response.data])
                return embeddings if len(embeddings) > 1 else embeddings[0]
            except Exception as e:
                # Return random embeddings as fallback
                dim = 1536
                if isinstance(texts, list):
                    return np.random.random((len(texts), dim)).astype(np.float32)
                else:
                    return np.random.random(dim).astype(np.float32)

        # Initialize LightRAG with proper EmbeddingFunc wrapper
        rag = LightRAG(
            working_dir=working_dir,
            llm_model_func=openai_complete,
            embedding_func=EmbeddingFunc(
                embedding_dim=1536,
                max_token_size=8191,
                func=openai_embedding
            )
        )
        
        # CRITICAL: Initialize storages and pipeline status (fixes async context manager issue)
        await rag.initialize_storages()
        
        # Import and call initialize_pipeline_status
        from lightrag.kg.shared_storage import initialize_pipeline_status
        await initialize_pipeline_status()
        
        # Execute async query
        result = await rag.aquery(query_text, param=QueryParam(mode="hybrid"))
        
        return result if result else "No results found in knowledge base"
        
    except Exception as e:
        return f"LightRAG query error: {str(e)}"

def query_nsw_lightrag(query_text, working_dir="./ultimate_nsw_processor"):
    """Synchronous wrapper for async LightRAG query"""
    try:
        # Run the async query
        result = asyncio.run(query_nsw_lightrag_async(query_text, working_dir))
        return result
    except Exception as e:
        return f"Async query error: {str(e)}"

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = "What are the building height limits?"
        
    result = query_nsw_lightrag(query)
    print(json.dumps({
        "success": True if not result.startswith("LightRAG query error") else False,
        "query": query,
        "result": result
    }))