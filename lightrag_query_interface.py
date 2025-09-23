#!/usr/bin/env python3
"""
Enhanced LightRAG Query Interface
Provides conversational query interface for the enhanced knowledge graph.

Usage:
python lightrag_query_interface.py
"""

import os
import asyncio
import logging
import sys
from datetime import datetime

# Import LightRAG components
sys.path.append('./lightrag/LightRAG-main')

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.utils import setup_logger

# Configuration
WORKING_DIR = "./lightrag_enhanced_storage"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key-here")

# Setup logging
setup_logger("lightrag", level="INFO")
logger = logging.getLogger("lightrag_query")

class LightRAGQueryInterface:
 """Interactive query interface for the enhanced knowledge graph."""
 
 def __init__(self):
 self.rag = None
 
 async def initialize(self):
 """Initialize LightRAG for querying."""
 if not os.path.exists(WORKING_DIR):
 print(f" Enhanced knowledge graph not found at: {WORKING_DIR}")
 print("Please run lightrag_enhanced_kg_builder.py first")
 return False
 
 self.rag = LightRAG(
 working_dir=WORKING_DIR,
 llm_model_func=gpt_4o_mini_complete,
 embedding_func=openai_embed,
 )
 
 try:
 await self.rag.initialize_storages()
 await initialize_pipeline_status()
 logger.info("LightRAG query interface initialized successfully")
 return True
 except Exception as e:
 logger.error(f"Failed to initialize: {str(e)}")
 return False
 
 async def query(self, question: str, mode: str = "hybrid") -> str:
 """Execute a query against the knowledge graph."""
 try:
 result = await self.rag.aquery(
 question,
 param=QueryParam(
 mode=mode,
 response_type="Multiple Paragraphs",
 top_k=20 # Get more context for comprehensive responses
 )
 )
 return result
 except Exception as e:
 logger.error(f"Query failed: {str(e)}")
 return f"Error: {str(e)}"
 
 async def interactive_session(self):
 """Run interactive query session."""
 print("\n Enhanced LightRAG Query Interface")
 print("=" * 50)
 print("Ask questions about NSW planning regulations")
 print("Commands: 'quit' to exit, 'mode <mode>' to change query mode")
 print("Available modes: naive, local, global, hybrid, mix")
 print("=" * 50)
 
 current_mode = "hybrid"
 query_count = 0
 
 while True:
 try:
 # Get user input
 user_input = input(f"\n[{current_mode}] Query: ").strip()
 
 # Handle commands
 if user_input.lower() in ['quit', 'exit', 'q']:
 break
 elif user_input.lower().startswith('mode '):
 new_mode = user_input[5:].strip().lower()
 if new_mode in ['naive', 'local', 'global', 'hybrid', 'mix']:
 current_mode = new_mode
 print(f" Query mode changed to: {current_mode}")
 else:
 print(" Invalid mode. Available: naive, local, global, hybrid, mix")
 continue
 elif not user_input:
 continue
 
 # Execute query
 query_count += 1
 print(f"\n Query {query_count} [{current_mode}]: {user_input}")
 print("-" * 50)
 
 start_time = datetime.now()
 result = await self.query(user_input, current_mode)
 end_time = datetime.now()
 
 response_time = (end_time - start_time).total_seconds()
 
 print(result)
 print("-" * 50)
 print(f"⏱ Response time: {response_time:.2f} seconds")
 
 except KeyboardInterrupt:
 print("\n\nExiting...")
 break
 except Exception as e:
 print(f" Error: {str(e)}")
 
 async def run_sample_queries(self):
 """Run sample queries to demonstrate the system."""
 sample_queries = [
 {
 "query": "What are the setback requirements for dual occupancy development in Marrickville?",
 "mode": "hybrid"
 },
 {
 "query": "What heritage controls apply in the Inner West council area?",
 "mode": "local"
 },
 {
 "query": "What are the height limits for residential zones in NSW?",
 "mode": "global"
 },
 {
 "query": "Which State Environmental Planning Policies (SEPPs) apply to housing development?",
 "mode": "hybrid"
 },
 {
 "query": "What assessment criteria apply to development applications?",
 "mode": "mix"
 }
 ]
 
 print("\n Sample Query Demonstrations")
 print("=" * 50)
 
 for i, sample in enumerate(sample_queries, 1):
 print(f"\n Sample Query {i} [{sample['mode']}]: {sample['query']}")
 print("-" * 50)
 
 start_time = datetime.now()
 result = await self.query(sample['query'], sample['mode'])
 end_time = datetime.now()
 
 response_time = (end_time - start_time).total_seconds()
 
 # Show truncated response for demo
 if len(result) > 500:
 print(result[:500] + "...")
 print(f"[Response truncated - full length: {len(result)} characters]")
 else:
 print(result)
 
 print(f"⏱ Response time: {response_time:.2f} seconds")
 print("=" * 50)

async def main():
 """Main execution function."""
 print(" Enhanced LightRAG Query Interface")
 
 # Check API key
 if not os.getenv("OPENAI_API_KEY"):
 print(" OPENAI_API_KEY not set. Please set your OpenAI API key:")
 print("export OPENAI_API_KEY='your-key-here'")
 return
 
 interface = LightRAGQueryInterface()
 
 # Initialize
 print(" Initializing query interface...")
 if not await interface.initialize():
 return
 
 print(" Query interface ready")
 
 # Show menu
 print("\nChoose an option:")
 print("1. Run sample queries (demo)")
 print("2. Interactive query session")
 print("3. Both")
 
 try:
 choice = input("\nChoice (1/2/3): ").strip()
 
 if choice in ['1', '3']:
 await interface.run_sample_queries()
 
 if choice in ['2', '3']:
 await interface.interactive_session()
 
 print("\n Thank you for using Enhanced LightRAG!")
 
 except KeyboardInterrupt:
 print("\n\nExiting...")
 except Exception as e:
 logger.error(f"Interface error: {str(e)}")
 print(f" Error: {str(e)}")
 
 finally:
 if interface.rag:
 await interface.rag.finalize_storages()

if __name__ == "__main__":
 asyncio.run(main())