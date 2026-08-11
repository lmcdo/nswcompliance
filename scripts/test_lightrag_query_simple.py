#!/usr/bin/env python3
"""
Test LightRAG query with proper async handling
"""

import asyncio
import sys
import os
from pathlib import Path
import openai
import numpy as np
from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc

# Set OpenAI API key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

async def test_lightrag_query():
    """Test LightRAG query properly"""
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        def openai_complete(prompt, system_prompt=None, history_messages=[], **kwargs):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=kwargs.get("max_tokens", 2000),
                    temperature=kwargs.get("temperature", 0.1)
                )
                return response.choices[0].message.content
            except Exception as e:
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
                dim = 1536
                if isinstance(texts, list):
                    return np.random.random((len(texts), dim)).astype(np.float32)
                return np.random.random(dim).astype(np.float32)

        embedding_func = EmbeddingFunc(
            embedding_dim=1536,
            max_token_size=8191,
            func=openai_embedding
        )
        
        # Test with working Leichhardt storage first
        project_root = Path(__file__).parent.parent
        leichhardt_storage = project_root / "lightrag_leichhardt_storage"
        
        lightrag = LightRAG(
            working_dir=str(leichhardt_storage),
            llm_model_func=openai_complete,
            embedding_func=embedding_func,
            llm_model_name="gpt-4o-mini"
        )
        
        # Use aquery directly to avoid event loop issues
        query = sys.argv[1] if len(sys.argv) > 1 else "What are the specific setback requirements for buildings? Provide only the operative regulatory text."
        
        result = await lightrag.aquery(query, param=QueryParam(mode="hybrid"))
        print(result)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_lightrag_query())