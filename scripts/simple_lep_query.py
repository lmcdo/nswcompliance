#!/usr/bin/env python3
"""
Simple LEP query exactly like working DCP test
"""
import asyncio
import os
import openai
import numpy as np
from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc

# Set API key
OPENAI_API_KEY = "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"
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

async def test_lep_simple():
    print("Testing LEP LightRAG - Simple Direct Query")
    print("=" * 50)
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
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
            print(f"OpenAI completion error: {e}")
            return f"Error: {str(e)}"

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
            print(f"OpenAI embedding error: {e}")
            dim = 1536
            if isinstance(texts, list):
                return np.random.random((len(texts), dim)).astype(np.float32)
            return np.random.random(dim).astype(np.float32)
    
    # Initialize LightRAG pointing to existing LEP storage - NO INITIALIZATION CALLS
    rag = LightRAG(
        working_dir="./lightrag_lep_storage",
        llm_model_func=openai_complete,
        embedding_func=EmbeddingFunc(
            embedding_dim=1536,
            max_token_size=8191,
            func=openai_embedding
        )
    )
    
    # Simple test queries
    queries = [
        "What are the height requirements for buildings?",
        "What does clause 4.3 say about building height?"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        try:
            response = await rag.aquery(
                query,
                param=QueryParam(mode="hybrid", top_k=5, only_need_context=False)
            )
            
            if response and len(str(response)) > 50:
                print(f"+ Response ({len(str(response))} chars):")
                print(f"   {str(response)[:300]}...")
            else:
                print("- No meaningful response")
                
        except Exception as e:
            print(f"- Query failed: {e}")
    
    print("\nDone testing LEP LightRAG")

if __name__ == "__main__":
    asyncio.run(test_lep_simple())