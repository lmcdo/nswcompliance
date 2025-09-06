#!/usr/bin/env python3
"""
Simple NSW Query Script - Direct LightRAG access
Uses the working ultimate_nsw_processor knowledge base
"""
import sys
import json
import asyncio
import os
import openai
import numpy as np

# Set working directory to the ultimate processor
os.chdir('/home/lawre/compliance-engine')

# Set OpenAI API key
OPENAI_API_KEY = "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"
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "height requirements"
    
    try:
        from lightrag import LightRAG, QueryParam
        from lightrag.utils import EmbeddingFunc
        
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Simple LLM function
        async def llm_func(prompt, **kwargs):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.1
            )
            return response.choices[0].message.content
        
        # Simple embedding function
        async def embedding_func(texts):
            if isinstance(texts, str):
                texts = [texts]
            
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            
            embeddings = np.array([item.embedding for item in response.data])
            return embeddings if len(embeddings) > 1 else embeddings[0]
        
        # Initialize LightRAG
        rag = LightRAG(
            working_dir="./ultimate_nsw_processor",
            llm_model_func=llm_func,
            embedding_func=EmbeddingFunc(
                embedding_dim=1536,
                max_token_size=8191,
                func=embedding_func
            )
        )
        
        # Run query
        result = asyncio.run(rag.aquery(query, param=QueryParam(mode="hybrid")))
        
        if result and len(result.strip()) > 0:
            print(json.dumps({"success": True, "result": result}))
        else:
            print(json.dumps({"success": False, "error": "No results found"}))
            
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))

if __name__ == "__main__":
    main()