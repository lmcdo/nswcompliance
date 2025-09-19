#!/usr/bin/env python3
"""
PRP-L1: LlamaIndex + Unstructured.io Setup & Validation
Uses existing extracted JSONs instead of PDFs
"""
import os
import json
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv('.env.local')

def map_extracted_data():
    """Map all available extracted JSON data sources"""
    
    print("=== PRP-L1: MAPPING EXTRACTED DATA SOURCES ===")
    
    data_sources = {
        'output_folder': [],
        'langextract_verified': [],
        'autoschema_output': [],
        'prp_k9_extractions': []
    }
    
    # 1. Main output folder (112 processed documents)
    output_dir = Path("output")
    if output_dir.exists():
        for doc_folder in output_dir.iterdir():
            if doc_folder.is_dir():
                content_file = doc_folder / 'auto' / f'{doc_folder.name}_content_list.json'
                if content_file.exists():
                    data_sources['output_folder'].append({
                        'name': doc_folder.name,
                        'path': str(content_file),
                        'type': 'mineru_processed'
                    })
    
    # 2. LangExtract verified output  
    langextract_dir = Path("langextract_verified_output")
    if langextract_dir.exists():
        for json_file in langextract_dir.glob("*_verified.json"):
            data_sources['langextract_verified'].append({
                'name': json_file.stem.replace('_verified', ''),
                'path': str(json_file),
                'type': 'langextract_provisions'
            })
    
    # 3. AutoSchema knowledge graph data
    autoschema_dirs = ['autoschemakg_output', 'autoschemakg_output_ollama_final']
    for dir_name in autoschema_dirs:
        kg_dir = Path(dir_name) / 'kg_extraction'
        if kg_dir.exists():
            for json_file in kg_dir.glob("*.json"):
                data_sources['autoschema_output'].append({
                    'name': json_file.stem,
                    'path': str(json_file),
                    'type': 'autoschema_kg'
                })
    
    # 4. PRP-K9 complete extractions
    k9_dirs = ['prp_k9_complete_dcp_extraction', 'prp_k9_complete_lep_extraction']
    for dir_name in k9_dirs:
        k9_dir = Path(dir_name)
        if k9_dir.exists():
            for item in k9_dir.rglob("*.json"):
                data_sources['prp_k9_extractions'].append({
                    'name': item.stem,
                    'path': str(item),
                    'type': 'prp_k9_complete'
                })
    
    return data_sources

def test_llamaindex_compatibility():
    """Test if LlamaIndex can be installed without conflicts"""
    
    print("\n=== TESTING LLAMAINDEX COMPATIBILITY ===")
    
    try:
        # Test basic import to see if environment is clean
        import sys
        print(f"Python version: {sys.version}")
        print(f"Current packages: {len([p for p in sys.modules.keys()])} modules loaded")
        
        # Check for potential conflicts
        conflict_packages = ['atlas_rag', 'langextract']
        remaining_conflicts = []
        
        for package in conflict_packages:
            try:
                __import__(package)
                remaining_conflicts.append(package)
            except ImportError:
                print(f"SUCCESS: {package} successfully removed")
        
        if remaining_conflicts:
            print(f"WARNING: Still have conflicts: {remaining_conflicts}")
            return False
        
        print("SUCCESS: Environment clean for LlamaIndex installation")
        return True
        
    except Exception as e:
        print(f"ERROR: Compatibility test failed: {e}")
        return False

def install_llamaindex():
    """Install LlamaIndex with minimal dependencies first"""
    
    print("\n=== INSTALLING LLAMAINDEX + UNSTRUCTURED.IO ===")
    
    # Install order to minimize conflicts
    packages = [
        "llama-index-core",
        "llama-index-llms-openai", 
        "llama-index-embeddings-openai",
        "unstructured[local-inference]"
    ]
    
    for package in packages:
        print(f"\nInstalling {package}...")
        try:
            result = subprocess.run([
                "venv_linux/Scripts/pip.exe", "install", package
            ], check=True, capture_output=True, text=True)
            print(f"SUCCESS: {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to install {package}")
            print(f"Error output: {e.stderr}")
            return False
    
    return True

def test_single_document():
    """Test LlamaIndex on one extracted JSON document"""
    
    print("\n=== TESTING SINGLE DOCUMENT EXTRACTION ===")
    
    try:
        from llama_index.core import Document, Settings
        from llama_index.llms.openai import OpenAI
        from llama_index.embeddings.openai import OpenAIEmbedding
        
        # Configure LlamaIndex
        Settings.llm = OpenAI(model="gpt-4o-mini", api_key=os.getenv('OPENAI_API_KEY'))
        Settings.embed_model = OpenAIEmbedding(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Load a test document
        test_file = "output/Inner West Ashfield DCP 2016 - Chapter A - Miscellaneous - with IWLEP 2022 amendments/auto/Inner West Ashfield DCP 2016 - Chapter A - Miscellaneous - with IWLEP 2022 amendments_content_list.json"
        
        if not os.path.exists(test_file):
            print(f"ERROR: Test file not found: {test_file}")
            return False
        
        with open(test_file, 'r', encoding='utf-8') as f:
            content_data = json.load(f)
        
        # Convert to LlamaIndex documents
        text_chunks = [item.get('text', '') for item in content_data if item.get('text', '').strip()]
        documents = [Document(text=chunk, metadata={"source": "test_doc"}) for chunk in text_chunks[:5]]  # Just first 5 chunks
        
        print(f"SUCCESS: Loaded {len(documents)} document chunks")
        print(f"SUCCESS: First chunk preview: {documents[0].text[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Single document test failed: {e}")
        return False

if __name__ == "__main__":
    print("PRP-L1: LLAMAINDEX + UNSTRUCTURED.IO SETUP")
    print("=" * 50)
    
    # Step 1: Map existing data
    data_sources = map_extracted_data()
    
    print(f"\nDATA SOURCES FOUND:")
    for source_type, items in data_sources.items():
        print(f"  {source_type}: {len(items)} files")
    
    total_files = sum(len(items) for items in data_sources.values())
    print(f"\nTotal JSON files available: {total_files}")
    
    # Step 2: Test compatibility
    if not test_llamaindex_compatibility():
        print("ERROR: Environment not ready for LlamaIndex")
        exit(1)
    
    # Step 3: Install packages
    if not install_llamaindex():
        print("ERROR: LlamaIndex installation failed")
        exit(1)
    
    # Step 4: Test single document
    if not test_single_document():
        print("ERROR: Single document test failed")
        exit(1)
    
    print("\n" + "=" * 50)
    print("SUCCESS: PRP-L1 COMPLETED SUCCESSFULLY")
    print("SUCCESS: LlamaIndex + Unstructured.io ready")
    print("SUCCESS: Environment validated with extracted JSONs")
    print("SUCCESS: Ready for PRP-L2: Single Document Proof of Concept")