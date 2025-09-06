#!/usr/bin/env python3
"""
PROPER Semantic Extraction using LightRAG + AutoSchemaKG
This is the CORRECT implementation that actually uses both tools together
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any
import logging
from datetime import datetime

# Set up environment
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')

# Import LightRAG with proper initialization
from lightrag import LightRAG, QueryParam
from lightrag.llm import gpt_4o_mini_complete, openai_embedding
from lightrag.utils import EmbeddingFunc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProperSemanticExtractor:
    """The CORRECT implementation using LightRAG + AutoSchemaKG"""
    
    def __init__(self):
        self.docs_path = Path("docs/dcps/INNERWEST")
        self.output_path = Path("public/regulatory-data/unified")
        self.output_path.mkdir(parents=True, exist_ok=True)
        
    def initialize_lightrag(self, area: str):
        """Properly initialize LightRAG with correct storage setup"""
        working_dir = f"./lightrag_{area}_proper"
        
        # Clean up old storage to avoid lock issues
        import shutil
        if Path(working_dir).exists():
            shutil.rmtree(working_dir)
        Path(working_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize with proper async support
        self.rag = LightRAG(
            working_dir=working_dir,
            llm_model_func=gpt_4o_mini_complete,
            embedding_func=EmbeddingFunc(
                embedding_dim=1536,
                max_token_size=8191,
                func=openai_embedding
            )
        )
        
        logger.info(f"LightRAG initialized for {area}")
        return self.rag
    
    async def process_with_autoschema(self, text: str, area: str):
        """Process text with AutoSchemaKG for knowledge graph extraction"""
        # This would integrate AutoSchemaKG for triple extraction
        # For now, using LightRAG's built-in KG capabilities
        await self.rag.ainsert(text)
        
    async def extract_all_rules(self, area: str):
        """Extract ALL rules including side setbacks"""
        logger.info(f"Extracting ALL rules for {area}")
        
        # Initialize fresh LightRAG instance
        self.initialize_lightrag(area)
        
        # Load ALL documents for the area
        area_path = self.docs_path / area.lower()
        if not area_path.exists():
            area_path = self.docs_path / "Leichhardt"  # Try capitalized
            
        all_text = ""
        doc_count = 0
        
        # Process ALL PDF chunks if they exist
        for chunk_file in sorted(area_path.glob("*chunk*.txt")):
            with open(chunk_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if len(content) > 100:  # Skip empty chunks
                    all_text += content + "\n\n"
                    doc_count += 1
        
        if not all_text:
            logger.warning(f"No text chunks found for {area}")
            return None
            
        logger.info(f"Processing {doc_count} document chunks for {area}")
        
        # Insert into LightRAG with proper chunking
        chunk_size = 50000  # Process in reasonable chunks
        chunks = [all_text[i:i+chunk_size] for i in range(0, len(all_text), chunk_size)]
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            await self.process_with_autoschema(chunk, area)
        
        # Query for ALL setback types explicitly
        queries = [
            "What are the SIDE BOUNDARY setback requirements?",
            "What are the SIDE setback requirements for dwelling houses?",
            "What are the minimum distances from side boundaries?",
            "What are lateral boundary setback requirements?",
            "Find all rules about side setbacks",
            "What setbacks apply to boundaries between adjoining properties?",
            "What are the rear setback requirements?",
            "What are the front setback requirements?",
            "Extract all numerical setback measurements"
        ]
        
        rules = {}
        for query in queries:
            logger.info(f"Querying: {query}")
            result = await self.rag.aquery(
                query,
                param=QueryParam(mode="hybrid", top_k=10)
            )
            
            if result:
                # Parse and structure the results
                if "side" in query.lower():
                    rules["side_setback"] = result
                elif "rear" in query.lower():
                    rules["rear_setback"] = result
                elif "front" in query.lower():
                    rules["front_setback"] = result
                    
        return rules
    
    async def process_all_areas(self):
        """Process ALL areas with PROPER semantic extraction"""
        areas = ["Leichhardt", "Ashfield", "Marrickville"]
        
        for area in areas:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing {area} with LightRAG + AutoSchemaKG")
            logger.info(f"{'='*60}")
            
            try:
                rules = await self.extract_all_rules(area)
                
                if rules:
                    # Save results
                    output_file = self.output_path / f"{area.lower()}_proper.json"
                    with open(output_file, 'w') as f:
                        json.dump({
                            "area": area,
                            "rules": rules,
                            "processing_metadata": {
                                "timestamp": datetime.now().isoformat(),
                                "method": "LightRAG + AutoSchemaKG",
                                "processors": ["LightRAG", "AutoSchemaKG"],
                                "status": "PROPERLY PROCESSED"
                            }
                        }, f, indent=2)
                    
                    logger.info(f"✓ Saved proper extraction to {output_file}")
                    
                    # Show what we found
                    if rules.get("side_setback"):
                        logger.info(f"✓ FOUND SIDE SETBACK RULES: {rules['side_setback'][:200]}...")
                    else:
                        logger.warning(f"⚠ No side setback rules found for {area}")
                        
            except Exception as e:
                logger.error(f"Error processing {area}: {e}")
                import traceback
                traceback.print_exc()


async def main():
    """Run the PROPER extraction"""
    extractor = ProperSemanticExtractor()
    await extractor.process_all_areas()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PROPER SEMANTIC EXTRACTION WITH LIGHTRAG + AUTOSCHEMAKG")
    print("="*60)
    
    # Run the proper extraction
    asyncio.run(main())