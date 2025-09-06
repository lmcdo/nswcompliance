#!/usr/bin/env python3
"""
Query LEP LightRAG storage for regulatory text
"""

import sys
import asyncio
import os
from pathlib import Path
from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc
import numpy as np
import openai

# Set OpenAI API key
OPENAI_API_KEY = "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"
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

async def query_lep(query):
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

        embedding_func = EmbeddingFunc(
            embedding_dim=1536,
            max_token_size=8191,
            func=openai_embedding
        )
        
        # Initialize LightRAG with LEP storage
        project_root = Path(__file__).parent.parent
        lep_storage = project_root / "lightrag_lep_storage"
        
        lightrag = LightRAG(
            working_dir=str(lep_storage),
            llm_model_func=openai_complete,
            embedding_func=embedding_func,
            llm_model_name="gpt-4o-mini"
        )
        
        # Query the LEP knowledge graph - use synchronous query
        result = lightrag.query(query, param=QueryParam(mode="hybrid"))
        print(result)
        
    except Exception as e:
        print(f"Error querying LEP: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    if len(sys.argv) != 2:
        print("Usage: python query_lep_lightrag.py <query>", file=sys.stderr)
        sys.exit(1)
        
    query = sys.argv[1]
    
    # Check if there's already an event loop running
    try:
        loop = asyncio.get_running_loop()
        # If there is, we need to use a different approach
        import concurrent.futures
        import threading
        
        def run_in_thread():
            asyncio.run(query_lep(query))
            
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            future.result()  # Wait for completion
    except RuntimeError:
        # No running loop, safe to use asyncio.run
        asyncio.run(query_lep(query))

if __name__ == "__main__":
    main()