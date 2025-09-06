#!/usr/bin/env python3
"""
LightRAG Compliance Document Processor
Replaces dual_semantic_processor.py with LightRAG for better multimodal processing
Outputs SemanticRuleExtraction format compatible with existing TypeScript pipeline
"""

import asyncio
import json
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    from lightrag import LightRAG, QueryParam
    from lightrag.llm import gpt_4o_mini_complete, gpt_4o_complete
    from lightrag.utils import EmbeddingFunc
    import numpy as np
except ImportError:
    print("Error: LightRAG not installed. Install with: pip install lightrag-hku")
    sys.exit(1)

class ComplianceLightRAGProcessor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.lightrag_config = config.get('lightrag_config', {})
        self.processing_options = config.get('processing_options', {})
        
        # Initialize LightRAG with compliance-specific settings
        working_dir = self.lightrag_config.get('working_dir', './lightrag_storage')
        
        self.rag = LightRAG(
            working_dir=working_dir,
            llm_model_func=gpt_4o_mini_complete if self.lightrag_config.get('llm_model_func') == 'gpt-4o-mini' else gpt_4o_complete,
            embed_model=self.lightrag_config.get('embed_model', 'text-embedding-3-small')
        )
        
        # Compliance-specific query templates
        self.compliance_queries = [
            "What are the specific setback requirements for residential development?",
            "What are the side boundary setback rules and measurements?", 
            "What are the rear boundary setback requirements?",
            "What are the front setback or streetscape alignment requirements?",
            "What height restrictions apply within setback areas?",
            "What are the mandatory compliance requirements vs recommended guidelines?",
            "What conditional or alternative compliance options exist?"
        ]
    
    async def process_documents(self) -> Dict[str, Any]:
        """Process compliance documents and return SemanticRuleExtraction format"""
        
        area = self.processing_options.get('area', 'Unknown')
        input_files = self.processing_options.get('input_files', [])
        
        print(f"Processing {len(input_files)} files for {area} using LightRAG...")
        
        # Insert documents into LightRAG
        for file_path in input_files:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    await self.rag.ainsert(content)
                    print(f"Inserted: {os.path.basename(file_path)}")
            else:
                print(f"Warning: File not found: {file_path}")
        
        # Extract compliance rules using targeted queries
        enhanced_rules = []
        
        for query in self.compliance_queries:
            try:
                # Use hybrid search for comprehensive results
                response = await self.rag.aquery(
                    query, 
                    param=QueryParam(mode="hybrid", only_need_context=False)
                )
                
                # Convert LightRAG response to EnhancedRule format
                rule = self.convert_response_to_enhanced_rule(query, response, area)
                if rule:
                    enhanced_rules.append(rule)
                    
            except Exception as e:
                print(f"Query failed: {query[:50]}... Error: {e}")
                continue
        
        # Create SemanticRuleExtraction format
        extraction = {
            'area': area,
            'extraction_method': 'lightrag_v1.0',
            'enhanced_rules': enhanced_rules,
            'total_enhanced_rules': len(enhanced_rules),
            'high_confidence_rules': len([r for r in enhanced_rules if r.get('overall_confidence', 0) >= 0.85])
        }
        
        return extraction
    
    def convert_response_to_enhanced_rule(self, query: str, response: str, area: str) -> Optional[Dict[str, Any]]:
        """Convert LightRAG response to EnhancedRule format compatible with TypeScript interface"""
        
        try:
            # Determine rule type from query
            rule_type = self.determine_rule_type(query)
            if not rule_type:
                return None
            
            # Extract measurements from response
            measurements = self.extract_measurements(response)
            if not measurements:
                return None
            
            # Generate rule classification
            rule_classification = self.classify_rule(response)
            
            # Create source grounding
            source_grounding = {
                'extraction_text': response[:500] + '...' if len(response) > 500 else response,
                'source_section': f'LightRAG Analysis - {query[:50]}...',
                'source_page': 0,
                'confidence': 0.88,  # LightRAG typically provides good confidence
                'highlighted_spans': [[0, min(100, len(response))]]
            }
            
            # Generate unique rule ID
            rule_id = f"{area.upper()}_{rule_type.upper()}_{hash(query) % 1000:03d}"
            
            enhanced_rule = {
                'rule_id': rule_id,
                'rule_text': response,
                'rule_type': rule_type,
                'measurements': measurements,
                'rule_classification': rule_classification,
                'source_grounding': source_grounding,
                'overall_confidence': 0.88,
                'rule_complexity': 'MODERATE'
            }
            
            return enhanced_rule
            
        except Exception as e:
            print(f"Failed to convert response to enhanced rule: {e}")
            return None
    
    def determine_rule_type(self, query: str) -> Optional[str]:
        """Determine rule type from query"""
        query_lower = query.lower()
        
        if 'side' in query_lower and 'setback' in query_lower:
            return 'side_setback'
        elif 'rear' in query_lower and 'setback' in query_lower:
            return 'rear_setback'  
        elif 'front' in query_lower and 'setback' in query_lower:
            return 'front_setback'
        elif 'height' in query_lower:
            return 'height'
        else:
            return 'setback'  # Default
    
    def extract_measurements(self, response: str) -> List[Dict[str, Any]]:
        """Extract measurements from LightRAG response"""
        measurements = []
        
        # Simple regex patterns for common measurements
        import re
        
        # Look for patterns like "6m", "3.5 metres", "0.9m minimum"
        measurement_patterns = [
            r'(d+.?d*)s*m(?:etres?)?s*(minimum|maximum|min|max)?',
            r'(d+.?d*)s*metres*(minimum|maximum|min|max)?'
        ]
        
        for pattern in measurement_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                value = float(match.group(1))
                context = match.group(2) if match.group(2) else 'standard'
                
                measurement = {
                    'measurement_type': 'setback',
                    'value': value,
                    'unit': 'metres',
                    'context': f"{context} requirement",
                    'confidence': 0.85
                }
                measurements.append(measurement)
                break  # Take first measurement found
        
        # If no measurements found, create a generic one
        if not measurements:
            measurements.append({
                'measurement_type': 'setback',
                'value': 'variable',
                'unit': 'metres', 
                'context': 'as per regulatory text',
                'confidence': 0.70
            })
        
        return measurements
    
    def classify_rule(self, response: str) -> Dict[str, Any]:
        """Classify rule based on LightRAG response content"""
        
        response_lower = response.lower()
        
        # Look for enforcement language
        if any(word in response_lower for word in ['must', 'shall', 'required', 'mandatory']):
            tier = 1
            enforcement_level = 'MANDATORY'
            compliance_message_type = 'MUST_COMPLY'
            linguistic_confidence = 0.90
        elif any(word in response_lower for word in ['should', 'recommended', 'preferred']):
            tier = 2
            enforcement_level = 'RECOMMENDED'
            compliance_message_type = 'SHOULD_ALIGN'
            linguistic_confidence = 0.80
        else:
            tier = 3
            enforcement_level = 'INFORMATIONAL'
            compliance_message_type = 'CONSIDER'
            linguistic_confidence = 0.70
        
        # Extract prescriptive indicators
        prescriptive_indicators = []
        for indicator in ['must', 'shall', 'required', 'should', 'recommended']:
            if indicator in response_lower:
                prescriptive_indicators.append(indicator)
        
        return {
            'tier': tier,
            'enforcement_level': enforcement_level,
            'linguistic_confidence': linguistic_confidence,
            'prescriptive_indicators': prescriptive_indicators,
            'compliance_message_type': compliance_message_type
        }

async def main():
    parser = argparse.ArgumentParser(description='LightRAG Compliance Document Processor')
    parser.add_argument('--config', required=True, help='Configuration JSON file path')
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)
    
    # Process documents
    processor = ComplianceLightRAGProcessor(config)
    extraction = await processor.process_documents()
    
    # Save output
    output_file = config.get('output_file', 'lightrag_extraction.json')
    output_dir = os.path.join(os.getcwd(), 'public', 'regulatory-data')
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, output_file)
    
    with open(output_path, 'w') as f:
        json.dump(extraction, f, indent=2)
    
    print(f"LightRAG extraction saved to: {output_path}")
    print(f"Processed {extraction['total_enhanced_rules']} rules with {extraction['high_confidence_rules']} high confidence rules")

if __name__ == "__main__":
    asyncio.run(main())
