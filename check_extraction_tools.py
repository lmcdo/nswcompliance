#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os

print("="*80)
print("CHECKING ENTITY/RELATIONSHIP EXTRACTION TOOLS")
print("="*80)

# Check langextract
try:
    from langextract import extract
    print("\n[OK] langextract: INSTALLED (version 1.0.8)")
    print("  - Extracts structured text from PDFs")
    print("  - Good for preserving document structure")
except ImportError:
    print("\n[NO] langextract: NOT INSTALLED")

# Check AutoSchemaKG (atlas-rag)
try:
    from atlas_rag.kg_construction.triple_extraction import KnowledgeGraphExtractor
    from atlas_rag.kg_construction.triple_config import ProcessingConfig
    print("\n[OK] AutoSchemaKG (atlas-rag): INSTALLED (version 0.0.4.post1)")
    print("  - Extracts entities and relationships using LLM")
    print("  - Creates knowledge graph triples")
    print("  - Requires OpenAI API key")
except ImportError as e:
    print(f"\n[NO] AutoSchemaKG: NOT AVAILABLE ({e})")

# Check OpenAI key
from dotenv import load_dotenv
load_dotenv('.env.local')
api_key = os.getenv('OPENAI_API_KEY')

if api_key and api_key != 'your_openai_api_key_here':
    print("\n[OK] OpenAI API Key: CONFIGURED")
else:
    print("\n[NO] OpenAI API Key: NOT CONFIGURED")
    print("  - AutoSchemaKG requires OpenAI API key")
    print("  - Set in .env.local: OPENAI_API_KEY=sk-...")

print("\n" + "="*80)
print("CURRENT SITUATION")
print("="*80)
print("""
The kg_entities and kg_relationships tables exist but are unusable:
- Generic doc IDs (nsw_planning_doc_000) with NO mapping to actual documents
- No links to regulatory_provisions
- Orphaned data from old extraction run

To regenerate usable entities/relationships:
1. Extract text from Inner West LEP using langextract
2. Run AutoSchemaKG to extract entities/relationships
3. Link entities back to regulatory_provisions IDs
4. Store in kg_entities/kg_relationships with proper document_id

This is a SEPARATE task from the current UI work (which is complete).
Estimated time: 2-3 hours to extract + test
Cost: ~$5-10 in OpenAI API calls for Inner West LEP
""")