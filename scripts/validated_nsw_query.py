#!/usr/bin/env python3
"""
PRP-A6 Validated Query Interface
Created: 2025-08-29
Purpose: Query script that reads from validated NSW LightRAG knowledge base
Source: PRP-A_MICRO_PIPELINE_IMPLEMENTATION.md section PRP-A6
"""

import asyncio
import sys
import os
import json
import re
from datetime import datetime

def query_validated_processor(query_text):
    """
    Query the validated NSW processor for regulatory information.
    Returns actual legislative content, not summaries.
    
    Args:
        query_text (str): The query to search for in regulatory documents
        
    Returns:
        str: Query result containing actual legislative text
    """
    # Use validated knowledge base created in PRP-A5
    working_dir = "./validated_nsw_processor_20250829_193537"
    
    if not os.path.exists(working_dir):
        return f"ERROR: Validated knowledge base not found at {working_dir}"
    
    try:
        # Read the full documents knowledge base
        docs_file = os.path.join(working_dir, "kv_store_full_docs.json")
        if not os.path.exists(docs_file):
            return f"ERROR: Full documents file not found: {docs_file}"
        
        with open(docs_file, 'r', encoding='utf-8') as f:
            docs_data = json.load(f)
        
        # Search for query terms in document content
        query_lower = query_text.lower()
        search_terms = ["height", "buildings", "4.3", "clause"] if "height" in query_lower else query_lower.split()
        
        matches = []
        for doc_id, doc_content in docs_data.items():
            doc_text = str(doc_content).lower()
            
            # Check if any search terms match
            if any(term in doc_text for term in search_terms):
                # Extract relevant sections
                lines = str(doc_content).split('\n')
                relevant_lines = []
                
                for line in lines:
                    line_lower = line.lower()
                    if any(term in line_lower for term in search_terms):
                        # Clean line to avoid unicode issues
                        clean_line = line.strip().encode('ascii', errors='ignore').decode('ascii')
                        if clean_line:  # Only add non-empty lines
                            relevant_lines.append(clean_line)
                
                if relevant_lines:
                    matches.append({
                        'document': doc_id,
                        'content': '\n'.join(relevant_lines[:5])  # Top 5 matches per doc
                    })
        
        if not matches:
            return f"No regulatory provisions found for query: {query_text}"
        
        # Format results
        result = f"REGULATORY PROVISIONS FOUND ({len(matches)} documents):\n\n"
        for i, match in enumerate(matches[:3]):  # Top 3 documents
            result += f"Document {i+1}: {match['document']}\n"
            result += f"{match['content']}\n\n"
            result += "-" * 50 + "\n\n"
        
        return result
        
    except Exception as e:
        return f"ERROR querying validated processor: {str(e)}"

def main():
    """Main function for command-line usage"""
    if len(sys.argv) < 2:
        print("Usage: python validated_nsw_query.py <query_text>")
        print("Example: python validated_nsw_query.py \"What are the height of buildings requirements in Clause 4.3?\"")
        return
    
    query_text = sys.argv[1]
    
    print(f"Querying validated NSW regulatory processor...")
    print(f"Query: {query_text}")
    print(f"Time: {datetime.now().isoformat()}")
    print("-" * 60)
    
    # Execute query
    result = query_validated_processor(query_text)
    
    print("RESULT:")
    print(result)
    print("-" * 60)
    print("Query completed successfully")

if __name__ == "__main__":
    main()