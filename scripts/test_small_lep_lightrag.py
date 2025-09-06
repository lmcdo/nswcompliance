#!/usr/bin/env python3
"""
Test LEP processing with small, clean text to isolate the issue
"""

import asyncio
import os
import tempfile
import subprocess
from pathlib import Path

def test_small_lep():
    """Test with just clause 4.3 text, cleaned"""
    
    # Clean, small LEP text - just clause 4.3
    test_text = """
Inner West Local Environmental Plan 2022
Part 4 Principal development standards

4.3 Height of buildings
(1) The objectives of this clause are as follows:
(a) to ensure the height of buildings is compatible with the character of the locality,
(b) to minimise adverse impacts on local amenity,
(c) to provide an appropriate transition between buildings of different heights.

(2) The height of a building on any land is not to exceed the maximum height shown for the land on the Height of Buildings Map.

(2A) A building on land identified as Area 1, Area 2 or Area 3 on the Height of Buildings Map must not contain, or be reasonably capable of being modified to contain, an area forming part of the buildings gross floor area within 3m of the maximum height shown for the land on the Height of Buildings Map.
"""
    
    project_root = Path(__file__).parent.parent
    
    # Create temp file with clean content
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(test_text)
        temp_file = f.name
    
    # Create processing script
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

async def process_small_text():
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    def openai_complete(prompt, system_prompt=None, history_messages=[], **kwargs):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{{"role": "user", "content": prompt}}],
                max_tokens=kwargs.get("max_tokens", 1000),
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
    
    # Initialize LightRAG for test
    lightrag = LightRAG(
        working_dir=r"{project_root}/lightrag_test_small",
        llm_model_func=openai_complete,
        embedding_func=embedding_func,
        llm_model_name="gpt-4o-mini"
    )
    
    # Initialize storages
    await lightrag.initialize_storages()
    
    from lightrag.kg.shared_storage import initialize_pipeline_status
    await initialize_pipeline_status()
    
    # Read and process the small content
    with open(r"{temp_file}", 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Processing small LEP text with LightRAG...")
    await lightrag.ainsert(content)
    print("SUCCESS: Small LEP processing complete!")

if __name__ == "__main__":
    asyncio.run(process_small_text())
'''
    
    # Write script to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script_content)
        script_file = f.name
    
    try:
        # Clean any existing test storage
        import shutil
        test_storage = project_root / "lightrag_test_small"
        if test_storage.exists():
            shutil.rmtree(test_storage)
        
        # Run the script
        print("Testing small, clean LEP text...")
        result = subprocess.run([
            r"C:\Users\lawre\.pyenv\pyenv-win\versions\3.11.0\python.exe",
            script_file
        ], capture_output=True, text=True, timeout=300)
        
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print("SUCCESS: Small LEP text processed successfully!")
            print("This means the issue is with large/complex LEP content, not LightRAG itself")
        else:
            print(f"FAILED: Even small LEP text failed with code {result.returncode}")
            print("This means the issue is fundamental to LEP processing")
            
    except subprocess.TimeoutExpired:
        print("TIMEOUT: Small LEP processing timed out")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        # Cleanup temp files
        try:
            os.unlink(temp_file)
            os.unlink(script_file)
        except:
            pass

if __name__ == "__main__":
    test_small_lep()