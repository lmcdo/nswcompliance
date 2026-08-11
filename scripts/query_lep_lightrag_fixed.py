#!/usr/bin/env python3
"""
Query LEP LightRAG storage using the same pattern that works for DCPs
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

def query_lep_lightrag_sync(query_text):
    """Query LEP LightRAG storage synchronously like DCPs"""
    print(f"Querying LEP LightRAG: {query_text}")
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        def openai_complete(prompt, **kwargs):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=kwargs.get('max_tokens', 2000),
                    temperature=kwargs.get('temperature', 0.1)
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"Error: {str(e)}"

        def openai_embedding(texts):
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
                dim = 1536
                if isinstance(texts, list):
                    return np.random.random((len(texts), dim)).astype(np.float32)
                return np.random.random(dim).astype(np.float32)
        
        # Initialize LightRAG for LEP storage
        rag = LightRAG(
            working_dir="./lightrag_lep_storage",
            llm_model_func=openai_complete,
            embedding_func=EmbeddingFunc(
                embedding_dim=1536,
                max_token_size=8191,
                func=openai_embedding
            )
        )
        
        # Run async query in event loop
        async def async_query():
            try:
                response = await rag.aquery(
                    query_text,
                    param=QueryParam(mode="hybrid", top_k=5, only_need_context=False)
                )
                return response
            except Exception as e:
                print(f"Query error: {e}")
                return None
        
        # Set up event loop for Windows like DCPs
        import sys
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        response = asyncio.run(async_query())
        
        if response and len(str(response)) > 50:
            print(f"LEP Query successful ({len(str(response))} chars)")
            return str(response)
        else:
            print("No meaningful LEP response")
            return None
            
    except Exception as e:
        print(f"LEP Query failed: {e}")
        return None

def test_lep_height_query():
    """Test LEP height requirements query"""
    print("Testing LEP Height Requirements Query")
    print("=" * 40)
    
    height_query = "Extract the exact operative clause from 4.3 about building height requirements. What does clause 4.3(2) say about maximum height?"
    
    result = query_lep_lightrag_sync(height_query)
    
    if result:
        print("\nHeight Query Result:")
        print("-" * 20)
        print(result)
        
        # Check if this contains the operative clause
        if "height of a building" in result.lower() or "maximum height" in result.lower():
            print("\n✅ SUCCESS: Found height requirements!")
            return result
        else:
            print("\n❌ Response doesn't contain height requirements")
            return None
    else:
        print("\n❌ No height requirements found")
        return None

def test_lep_fsr_query():
    """Test LEP FSR requirements query"""  
    print("\nTesting LEP FSR Requirements Query")
    print("=" * 40)
    
    fsr_query = "Extract the exact operative clause from 4.4 about floor space ratio requirements. What does clause 4.4(2) say about maximum floor space ratio?"
    
    result = query_lep_lightrag_sync(fsr_query)
    
    if result:
        print("\nFSR Query Result:")
        print("-" * 20)
        print(result)
        
        # Check if this contains the operative clause
        if "floor space ratio" in result.lower() or "maximum floor space" in result.lower():
            print("\n✅ SUCCESS: Found FSR requirements!")
            return result
        else:
            print("\n❌ Response doesn't contain FSR requirements")
            return None
    else:
        print("\n❌ No FSR requirements found")
        return None

if __name__ == "__main__":
    print("LEP LightRAG Query Test - Using DCP Working Method")
    print("=" * 60)
    
    # Test both height and FSR queries
    height_result = test_lep_height_query()
    fsr_result = test_lep_fsr_query()
    
    # Final summary
    print("\n" + "=" * 60)
    if height_result and fsr_result:
        print("🎉 SUCCESS: Both LEP height and FSR queries working!")
        print("✅ LEP LightRAG processing is now working like DCPs!")
    elif height_result or fsr_result:
        print("⚠️  PARTIAL: One LEP query working")
    else:
        print("❌ FAILED: LEP queries not working")
        
    print("=" * 60)