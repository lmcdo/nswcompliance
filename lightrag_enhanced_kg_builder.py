#!/usr/bin/env python3
"""
Enhanced LightRAG Knowledge Graph Builder - Option 2
Builds a comprehensive LightRAG knowledge graph from the ultimate pipeline data.

Based on LIGHTRAG_DEPLOYMENT_STRATEGY.md - Option 2: Enhanced Knowledge Graph Construction
Using the 22,092 regulatory references from the Ultimate Multimodal Pipeline.
"""

import os
import asyncio
import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

# Import LightRAG components
import sys
sys.path.append('./lightrag/LightRAG-main')

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.utils import setup_logger

# Configuration
WORKING_DIR = "./lightrag_enhanced_storage"
DATABASE_PATH = "./nsw_planning.db"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key-here")

# Setup logging
setup_logger("lightrag", level="INFO")
logger = logging.getLogger("lightrag_enhanced")

class EnhancedLightRAGBuilder:
 """Builds enhanced LightRAG knowledge graph from Ultimate Pipeline data."""
 
 def __init__(self):
 self.rag = None
 self.db_path = DATABASE_PATH
 
 async def initialize_lightrag(self):
 """Initialize LightRAG with enhanced configuration."""
 if not os.path.exists(WORKING_DIR):
 os.makedirs(WORKING_DIR)
 
 self.rag = LightRAG(
 working_dir=WORKING_DIR,
 # Use GPT-4o-mini for faster processing with 22K entries
 llm_model_func=gpt_4o_mini_complete,
 # Use OpenAI embeddings for compatibility
 embedding_func=openai_embed,
 # Enhanced configuration for regulatory content
 chunk_token_size=800, # Smaller chunks for precise regulatory content
 chunk_overlap_token_size=100,
 entity_extract_max_gleaning=1, # One pass for efficiency with large dataset
 # Token limits optimized for regulatory queries
 addon_params={
 "language": "English",
 "entity_types": [
 "regulation", "clause", "requirement", "zone", 
 "development_standard", "assessment_criteria", 
 "sepp", "dcp", "council_area", "heritage_item"
 ]
 }
 )
 
 # Initialize storage and pipeline
 await self.rag.initialize_storages()
 await initialize_pipeline_status()
 
 logger.info("LightRAG initialized successfully")
 return self.rag
 
 def get_database_content(self) -> List[Dict[str, Any]]:
 """Extract structured content from the regulatory database."""
 logger.info("Extracting content from regulatory database...")
 
 conn = sqlite3.connect(self.db_path)
 cursor = conn.cursor()
 
 # Get comprehensive regulatory content with metadata
 query = """
 SELECT 
 document_id,
 ref_type,
 ref_number, 
 ref_context,
 page_number,
 section_header,
 extraction_timestamp,
 ROW_NUMBER() OVER (ORDER BY document_id, ref_number) as content_sequence
 FROM regulatory_refs 
 WHERE ref_context IS NOT NULL 
 AND LENGTH(ref_context) > 50
 ORDER BY document_id, ref_number
 """
 
 cursor.execute(query)
 rows = cursor.fetchall()
 
 # Convert to structured format
 content_items = []
 for row in rows:
 item = {
 'document_id': row[0],
 'ref_type': row[1],
 'ref_number': row[2],
 'content': row[3],
 'page_number': row[4],
 'section_header': row[5],
 'timestamp': row[6],
 'sequence_id': row[7],
 'source': f"{row[0]} - {row[1]} {row[2]}" + (f" (Page {row[4]})" if row[4] else "")
 }
 content_items.append(item)
 
 conn.close()
 logger.info(f"Extracted {len(content_items)} regulatory content items")
 return content_items
 
 def format_content_for_lightrag(self, content_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
 """Format content items into LightRAG-compatible documents."""
 logger.info("Formatting content for LightRAG ingestion...")
 
 # Group by document for better context
 doc_groups = {}
 for item in content_items:
 doc_id = item['document_id']
 if doc_id not in doc_groups:
 doc_groups[doc_id] = []
 doc_groups[doc_id].append(item)
 
 formatted_docs = []
 
 for doc_id, items in doc_groups.items():
 # Sort by sequence for proper document flow
 items_sorted = sorted(items, key=lambda x: x['sequence_id'])
 
 # Build comprehensive document content
 doc_content_parts = []
 doc_content_parts.append(f"DOCUMENT: {doc_id}")
 doc_content_parts.append("=" * 50)
 
 current_section = None
 for item in items_sorted:
 # Add section headers when they change
 if item['section_header'] and item['section_header'] != current_section:
 current_section = item['section_header']
 doc_content_parts.append(f"\nSECTION: {current_section}")
 doc_content_parts.append("-" * 30)
 
 # Format regulatory item with metadata
 content_line = f"{item['ref_type']} {item['ref_number']}: {item['content']}"
 if item['page_number']:
 content_line += f" [Page {item['page_number']}]"
 
 doc_content_parts.append(content_line)
 
 # Create formatted document
 formatted_doc = {
 'document_id': doc_id,
 'content': '\n'.join(doc_content_parts),
 'item_count': len(items_sorted),
 'source_info': f"NSW Planning Document: {doc_id}",
 'metadata': {
 'document_type': 'regulatory',
 'total_items': len(items_sorted),
 'coverage': f"Contains {len(items_sorted)} regulatory provisions"
 }
 }
 
 formatted_docs.append(formatted_doc)
 
 logger.info(f"Formatted {len(formatted_docs)} documents for LightRAG")
 return formatted_docs
 
 async def build_knowledge_graph(self, formatted_docs: List[Dict[str, Any]]):
 """Build the enhanced knowledge graph in LightRAG."""
 logger.info("Building enhanced knowledge graph...")
 
 # Process documents in batches for efficiency
 batch_size = 5 # Process 5 documents at a time to avoid overwhelming the LLM
 total_docs = len(formatted_docs)
 
 for i in range(0, total_docs, batch_size):
 batch = formatted_docs[i:i + batch_size]
 batch_num = (i // batch_size) + 1
 total_batches = (total_docs + batch_size - 1) // batch_size
 
 logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} documents)")
 
 # Insert batch of documents
 for doc in batch:
 try:
 # Insert document content into LightRAG
 await self.rag.ainsert(
 doc['content'],
 ids=[doc['document_id']] # Use document_id as the ID
 )
 
 logger.info(f"Inserted document: {doc['document_id']} ({doc['item_count']} items)")
 
 except Exception as e:
 logger.error(f"Failed to insert document {doc['document_id']}: {str(e)}")
 continue
 
 # Brief pause between batches to avoid rate limits
 await asyncio.sleep(2)
 
 logger.info("Enhanced knowledge graph construction completed")
 
 async def test_knowledge_graph(self):
 """Test the built knowledge graph with sample queries."""
 logger.info("Testing enhanced knowledge graph...")
 
 test_queries = [
 "What are the setback requirements for residential development?",
 "What heritage controls apply in the Inner West?",
 "What are the height limits for different zones?",
 "Which SEPPs apply to housing development?",
 "What assessment criteria apply to dual occupancy development?"
 ]
 
 for i, query in enumerate(test_queries, 1):
 logger.info(f"Test Query {i}: {query}")
 try:
 # Test hybrid mode (combines local and global search)
 result = await self.rag.aquery(
 query, 
 param=QueryParam(mode="hybrid")
 )
 logger.info(f"Response length: {len(result)} characters")
 logger.info(f"Sample response: {result[:200]}...")
 logger.info("-" * 50)
 
 except Exception as e:
 logger.error(f"Query failed: {str(e)}")
 
 logger.info("Knowledge graph testing completed")
 
 async def get_graph_statistics(self):
 """Get statistics about the built knowledge graph."""
 try:
 # Query for basic statistics - this may need adjustment based on LightRAG API
 logger.info("Gathering knowledge graph statistics...")
 
 # Test a simple query to verify the system is working
 test_result = await self.rag.aquery(
 "What types of regulations are in this database?",
 param=QueryParam(mode="global", only_need_context=True)
 )
 
 logger.info(f"Knowledge graph appears to be functional")
 logger.info(f"Sample context length: {len(test_result)} characters")
 
 except Exception as e:
 logger.error(f"Failed to get statistics: {str(e)}")

async def main():
 """Main execution function."""
 print(" Enhanced LightRAG Knowledge Graph Builder")
 print("=" * 50)
 print(f"Database: {DATABASE_PATH}")
 print(f"Working Directory: {WORKING_DIR}")
 print(f"Target: 22,092+ regulatory references")
 print("=" * 50)
 
 # Check API key
 if not os.getenv("OPENAI_API_KEY"):
 print(" OPENAI_API_KEY not set. Please set your OpenAI API key:")
 print("export OPENAI_API_KEY='your-key-here'")
 return
 
 # Check database exists
 if not os.path.exists(DATABASE_PATH):
 print(f" Database not found: {DATABASE_PATH}")
 return
 
 builder = EnhancedLightRAGBuilder()
 
 try:
 # Step 1: Initialize LightRAG
 print("\n Step 1: Initializing LightRAG...")
 await builder.initialize_lightrag()
 print(" LightRAG initialized successfully")
 
 # Step 2: Extract database content
 print("\n Step 2: Extracting regulatory content...")
 content_items = builder.get_database_content()
 print(f" Extracted {len(content_items)} regulatory items")
 
 # Step 3: Format for LightRAG
 print("\n Step 3: Formatting content for knowledge graph...")
 formatted_docs = builder.format_content_for_lightrag(content_items)
 print(f" Formatted {len(formatted_docs)} documents")
 
 # Step 4: Build knowledge graph
 print("\n Step 4: Building enhanced knowledge graph...")
 start_time = datetime.now()
 await builder.build_knowledge_graph(formatted_docs)
 end_time = datetime.now()
 duration = (end_time - start_time).total_seconds()
 print(f" Knowledge graph built in {duration:.1f} seconds")
 
 # Step 5: Test knowledge graph
 print("\n Step 5: Testing knowledge graph...")
 await builder.test_knowledge_graph()
 print(" Knowledge graph testing completed")
 
 # Step 6: Get statistics
 print("\n Step 6: Gathering statistics...")
 await builder.get_graph_statistics()
 print(" Statistics gathered")
 
 print("\n Enhanced LightRAG Knowledge Graph completed successfully!")
 print(f" Storage location: {WORKING_DIR}")
 print(f" Ready for conversational queries with {len(content_items)} regulatory provisions")
 
 except Exception as e:
 logger.error(f"Build process failed: {str(e)}")
 print(f" Build failed: {str(e)}")
 
 finally:
 if builder.rag:
 await builder.rag.finalize_storages()

if __name__ == "__main__":
 asyncio.run(main())