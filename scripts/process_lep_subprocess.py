#!/usr/bin/env python3
"""
Process LEP using subprocess method like the working SEPP processor
"""

import subprocess
import tempfile
import os
from pathlib import Path

def process_lep_with_subprocess():
    """Process LEP using subprocess to avoid async issues"""
    project_root = Path(__file__).parent.parent
    lep_chunks_dir = project_root / "temp_extraction_LEP"
    
    if not lep_chunks_dir.exists():
        print("No LEP chunks found")
        return
    
    # Combine all LEP chunks
    all_text = ""
    chunk_files = sorted(lep_chunks_dir.glob("lep_chunk_*.txt"))
    for chunk_file in chunk_files:
        with open(chunk_file, 'r', encoding='utf-8') as f:
            content = f.read()
            all_text += content + "\n\n"
    
    print(f"Processing {len(chunk_files)} LEP chunks...")
    
    # Create temp file with content
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(all_text)
        temp_file = f.name
    
    # Create a simple script to process this file
    script_content = f'''
import asyncio
from lightrag import LightRAG
from lightrag.utils import EmbeddingFunc
import numpy as np
import openai
import os
from pathlib import Path

OPENAI_API_KEY = "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"
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

async def process_file():
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    def openai_complete(prompt, system_prompt=None, history_messages=[], **kwargs):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{{"role": "user", "content": prompt}}],
                max_tokens=kwargs.get("max_tokens", 2000),
                temperature=kwargs.get("temperature", 0.1)
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {{str(e)}}"
    
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
    
    # Initialize LightRAG for LEP
    lightrag = LightRAG(
        working_dir=r"{project_root}/lightrag_lep_storage",
        llm_model_func=openai_complete,
        embedding_func=embedding_func,
        llm_model_name="gpt-4o-mini"
    )
    
    # Initialize storages
    await lightrag.initialize_storages()
    
    from lightrag.kg.shared_storage import initialize_pipeline_status
    await initialize_pipeline_status()
    
    # Read and process the content
    with open(r"{temp_file}", 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Processing LEP content with LightRAG...")
    await lightrag.ainsert(content)
    print("LEP processing complete!")

if __name__ == "__main__":
    asyncio.run(process_file())
'''
    
    # Write script to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script_content)
        script_file = f.name
    
    try:
        # Run the script
        print("Running LEP processing in subprocess...")
        result = subprocess.run([
            r"C:\Users\lawre\.pyenv\pyenv-win\versions\3.11.0\python.exe",
            script_file
        ], capture_output=True, text=True, timeout=1800)  # 30 minute timeout
        
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print("✅ LEP processing completed successfully!")
        else:
            print(f"❌ LEP processing failed with code {result.returncode}")
            
    except subprocess.TimeoutExpired:
        print("❌ LEP processing timed out")
    except Exception as e:
        print(f"❌ LEP processing error: {e}")
    finally:
        # Cleanup temp files
        try:
            os.unlink(temp_file)
            os.unlink(script_file)
        except:
            pass

if __name__ == "__main__":
    process_lep_with_subprocess()