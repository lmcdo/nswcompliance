#!/usr/bin/env python3
"""
Quick runner for the RAG extraction pipeline
Usage: python run_extraction.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.processing.rag_enhanced_processor import RAGEnhancedProcessor
from src.processing.rule_generator import RuleGenerator

def main():
 print(" Starting RAG-based rule extraction...")
 
 # Initialize processor
 processor = RAGEnhancedProcessor()
 
 # Process DCP documents
 docs_path = "docs/dcps"
 results = processor.process_documents(docs_path)
 
 # Generate compliance rules
 generator = RuleGenerator()
 rules = generator.generate_rules(results, "Inner West")
 
 # Save to public folder
 output_path = "public/regulatory-data/inner-west-compliance-rules.json"
 generator.save_rules(rules, output_path)
 
 print(f" Extraction complete! Rules saved to {output_path}")
 print(f" Extracted {len(rules.get('rules', []))} rules")

if __name__ == "__main__":
 main()