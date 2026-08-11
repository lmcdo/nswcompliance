#!/usr/bin/env python3
"""
Test the working LEP LightRAG storage for height and FSR queries
"""

import asyncio
import os
import openai
import numpy as np
from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc

# Set API key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

async def test_lep_queries():
    print("Testing Working LEP LightRAG Storage")
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
            # Return dummy embedding for fallback
            dim = 1536
            if isinstance(texts, list):
                return np.random.random((len(texts), dim)).astype(np.float32)
            return np.random.random(dim).astype(np.float32)
    
    # Initialize LightRAG pointing to LEP storage
    rag = LightRAG(
        working_dir="./lightrag_lep_storage",
        llm_model_func=openai_complete,
        embedding_func=EmbeddingFunc(
            embedding_dim=1536,
            max_token_size=8191,
            func=openai_embedding
        )
    )
    
    # Test queries for height and FSR from LEP
    queries = [
        "What are the height of building requirements from clause 4.3?",
        "What is the maximum height shown on the Height of Buildings Map?",
        "What are the floor space ratio requirements from clause 4.4?", 
        "What is the maximum floor space ratio shown on the Floor Space Ratio Map?",
        "Extract the exact text of clause 4.3(2) about building height",
        "Extract the exact text of clause 4.4(2) about floor space ratio"
    ]
    
    results = {}
    
    for query in queries:
        print(f"\nQuery: {query}")
        try:
            response = await rag.aquery(
                query,
                param=QueryParam(mode="hybrid", top_k=5, only_need_context=False)
            )
            
            if response and len(str(response)) > 50:
                print(f"✅ Response ({len(str(response))} chars):")
                print(f"   {str(response)[:400]}...")
                results[query] = response
            else:
                print("❌ No meaningful response")
                results[query] = None
                
        except Exception as e:
            print(f"❌ Query failed: {e}")
            results[query] = f"Error: {e}"
    
    # Summary
    successful = len([r for r in results.values() if r and 'Error' not in str(r)])
    print(f"\n🎉 SUCCESS: {successful}/{len(queries)} LEP queries answered!")
    
    # Look for specific height and FSR mentions
    height_mentions = []
    fsr_mentions = []
    
    for query, response in results.items():
        if response and isinstance(response, str):
            if any(term in response.lower() for term in ['height', 'building height', 'maximum height']):
                height_mentions.append((query, response))
            if any(term in response.lower() for term in ['floor space', 'fsr', 'ratio']):
                fsr_mentions.append((query, response))
    
    if height_mentions:
        print(f"\n🏢 Found {len(height_mentions)} height-related responses:")
        for query, response in height_mentions[:2]:  # Show first 2
            print(f"   Query: {query[:50]}...")
            print(f"   Response: {str(response)[:200]}...")
    
    if fsr_mentions:
        print(f"\n📐 Found {len(fsr_mentions)} FSR-related responses:")
        for query, response in fsr_mentions[:2]:  # Show first 2
            print(f"   Query: {query[:50]}...")
            print(f"   Response: {str(response)[:200]}...")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_lep_queries())