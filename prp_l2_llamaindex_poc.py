#!/usr/bin/env python3
"""
PRP-L2: LlamaIndex Proof of Concept with Planning-Specific Extraction
Test on single document with structured planning queries
"""
import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Import LlamaIndex components
from llama_index.core import Document, Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import VectorStoreIndex

load_dotenv('.env.local')

def setup_llamaindex():
    """Configure LlamaIndex with OpenAI models"""
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in .env.local")
        return False
    
    # Configure LlamaIndex settings
    Settings.llm = OpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0)
    Settings.embed_model = OpenAIEmbedding(api_key=api_key)
    
    print("SUCCESS: LlamaIndex configured with gpt-4o-mini")
    return True

def load_test_document():
    """Load a single test document from extracted JSONs"""
    
    # Use a planning-rich document for testing
    test_files = [
        "output/Marrickville DCP 2011 - 2 16 Energy Efficiency/auto/Marrickville DCP 2011 - 2 16 Energy Efficiency_content_list.json",
        "output/Inner West Ashfield DCP 2016 - Chapter A - Miscellaneous - with IWLEP 2022 amendments/auto/Inner West Ashfield DCP 2016 - Chapter A - Miscellaneous - with IWLEP 2022 amendments_content_list.json",
        "langextract_verified_output/Marrickville DCP 2011 - 5 0 Commercial and Mixed Use Development - with IWLEP 2022 amendments_verified.json"
    ]
    
    documents = []
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"Loading: {test_file}")
            
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content_data = json.load(f)
                
                if test_file.endswith('_content_list.json'):
                    # MinERU processed format
                    text_chunks = [item.get('text', '') for item in content_data if item.get('text', '').strip()]
                    doc_name = Path(test_file).parent.parent.name
                    
                    for i, chunk in enumerate(text_chunks[:10]):  # First 10 chunks
                        if len(chunk.strip()) > 50:  # Skip short chunks
                            documents.append(Document(
                                text=chunk.strip(),
                                metadata={
                                    "source": doc_name,
                                    "chunk_id": i,
                                    "type": "mineru_processed"
                                }
                            ))
                
                elif test_file.endswith('_verified.json'):
                    # LangExtract verified format
                    provisions = content_data.get('verified_provisions', [])
                    doc_name = content_data.get('document', 'unknown')
                    
                    for provision in provisions:
                        if provision.get('regulatory_text'):
                            documents.append(Document(
                                text=f"Clause {provision.get('clause_reference', 'unknown')}: {provision.get('regulatory_text')}",
                                metadata={
                                    "source": doc_name,
                                    "clause_reference": provision.get('clause_reference'),
                                    "provision_type": provision.get('provision_type'),
                                    "type": "langextract_verified"
                                }
                            ))
                
                print(f"  Added {len([d for d in documents if d.metadata['source'] == (doc_name if 'doc_name' in locals() else Path(test_file).stem)])} chunks")
                
            except Exception as e:
                print(f"  ERROR loading {test_file}: {e}")
                continue
    
    print(f"\nTotal documents loaded: {len(documents)}")
    return documents

def test_planning_queries(index):
    """Test LlamaIndex with planning-specific queries"""
    
    print("\n=== TESTING PLANNING-SPECIFIC QUERIES ===")
    
    planning_queries = [
        {
            "query": "What are the specific setback requirements with measurements?",
            "expected": "setbacks, measurements in meters, front/side/rear boundaries"
        },
        {
            "query": "Extract all zone codes and their development controls",
            "expected": "R1, R2, B1, zone-specific rules"
        },
        {
            "query": "What height limits apply to different building types?",
            "expected": "height measurements, building type restrictions"
        },
        {
            "query": "Find floor space ratio (FSR) requirements",
            "expected": "FSR values, ratios, development constraints"
        },
        {
            "query": "What clause references relate to heritage controls?",
            "expected": "clause numbers, heritage requirements, processes"
        }
    ]
    
    results = []
    
    for test in planning_queries:
        print(f"\nQuery: {test['query']}")
        print(f"Expected: {test['expected']}")
        print("-" * 50)
        
        try:
            # Query the index
            query_engine = index.as_query_engine(
                response_mode="compact",
                similarity_top_k=5
            )
            
            response = query_engine.query(test['query'])
            
            print(f"LlamaIndex Response:")
            print(f"  {response.response[:200]}...")
            
            # Check source nodes
            source_info = []
            if hasattr(response, 'source_nodes'):
                for node in response.source_nodes[:3]:  # Top 3 sources
                    source_info.append({
                        'source': node.metadata.get('source', 'unknown'),
                        'type': node.metadata.get('type', 'unknown'),
                        'score': getattr(node, 'score', 0.0)
                    })
            
            results.append({
                'query': test['query'],
                'response': response.response,
                'sources': source_info,
                'success': len(response.response) > 50  # Basic success metric
            })
            
            print(f"  Sources: {[s['source'][:30] for s in source_info]}")
            
        except Exception as e:
            print(f"  ERROR: Query failed: {e}")
            results.append({
                'query': test['query'],
                'response': f"Error: {e}",
                'sources': [],
                'success': False
            })
    
    return results

def analyze_results(results):
    """Analyze and compare LlamaIndex results vs existing methods"""
    
    print(f"\n{'='*60}")
    print("PRP-L2 RESULTS ANALYSIS")
    print(f"{'='*60}")
    
    successful_queries = len([r for r in results if r['success']])
    total_queries = len(results)
    
    print(f"Query Success Rate: {successful_queries}/{total_queries} ({successful_queries/total_queries*100:.1f}%)")
    
    # Check for planning-specific extractions
    planning_entities_found = []
    
    for result in results:
        response_text = result['response'].lower()
        
        # Check for planning entities
        if any(word in response_text for word in ['setback', 'metre', 'meter', 'm ']):
            planning_entities_found.append('measurements')
        
        if any(word in response_text for word in ['r1', 'r2', 'b1', 'b2', 'zone']):
            planning_entities_found.append('zones')
        
        if any(word in response_text for word in ['clause', 'section']):
            planning_entities_found.append('clause_references')
        
        if any(word in response_text for word in ['height', 'storey', 'floor']):
            planning_entities_found.append('heights')
        
        if 'fsr' in response_text or 'floor space ratio' in response_text:
            planning_entities_found.append('fsr')
    
    unique_entities = list(set(planning_entities_found))
    
    print(f"\nPlanning Entities Found: {len(unique_entities)}")
    for entity in unique_entities:
        print(f"  - {entity}")
    
    # Compare vs existing extractions
    print(f"\nCOMPARISON VS EXISTING METHODS:")
    print(f"  Rule-based extraction: 2,109 entities (zones, setbacks, measurements, clauses)")
    print(f"  LangExtract: 18 documents with structured provisions")
    print(f"  AutoSchema: Knowledge graph relationships")
    print(f"  LlamaIndex: {successful_queries} successful planning queries with {len(unique_entities)} entity types")
    
    return {
        'success_rate': successful_queries/total_queries,
        'entities_found': unique_entities,
        'total_responses': len(results),
        'recommendation': 'hybrid' if successful_queries > 0 else 'rule_based'
    }

async def main():
    """Main PRP-L2 execution"""
    
    print("PRP-L2: LLAMAINDEX PROOF OF CONCEPT")
    print("=" * 50)
    
    # Step 1: Setup LlamaIndex
    if not setup_llamaindex():
        print("ERROR: LlamaIndex setup failed")
        return False
    
    # Step 2: Load test documents  
    documents = load_test_document()
    if not documents:
        print("ERROR: No documents loaded")
        return False
    
    # Step 3: Build index
    print(f"\nBuilding vector index from {len(documents)} documents...")
    try:
        index = VectorStoreIndex.from_documents(documents)
        print("SUCCESS: Vector index built successfully")
    except Exception as e:
        print(f"ERROR: Index building failed: {e}")
        return False
    
    # Step 4: Test planning queries
    results = test_planning_queries(index)
    
    # Step 5: Analyze results
    analysis = analyze_results(results)
    
    print(f"\n{'='*60}")
    if analysis['success_rate'] > 0.5:
        print("SUCCESS: PRP-L2 COMPLETED - LlamaIndex shows promise for planning extraction")
        print(f"Recommendation: Proceed with hybrid approach (Rule-based + LlamaIndex)")
        print("Ready for PRP-L3: Batch Processing Design")
    else:
        print("PARTIAL SUCCESS: LlamaIndex working but limited planning-specific results")
        print(f"Recommendation: Focus on rule-based extraction, use LlamaIndex for complex queries")
    
    return analysis['success_rate'] > 0.3

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)