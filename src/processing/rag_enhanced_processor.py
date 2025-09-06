"""
Enhanced RAG Processor using RAG-Anything for reliable DCP rule extraction
Focuses on structured extraction with quality control
"""

import os
import sys
import json
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

# Try to import RAG-Anything
try:
    from rag_anything import RAGAnything
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logging.warning("RAG-Anything not available, falling back to simple processing")

from ..models import FormerCouncilArea, SetbackRule

class RAGEnhancedProcessor:
    """Enhanced processor using RAG-Anything for reliable rule extraction"""
    
    def __init__(self):
        self.rag_engine = None
        if RAG_AVAILABLE:
            try:
                self.rag_engine = RAGAnything()
                logging.info("RAG-Anything engine initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize RAG-Anything: {e}")
                self.rag_engine = None
        
        # Quality control patterns for extracted measurements
        self.measurement_patterns = {
            'setback_measurement': re.compile(r'(\d+(?:\.\d+)?)\s*(?:metres?|m)\b', re.IGNORECASE),
            'height_measurement': re.compile(r'height.*?(\d+(?:\.\d+)?)\s*(?:metres?|m)\b', re.IGNORECASE),
            'distance_measurement': re.compile(r'(?:minimum|maximum|at least)\s*(\d+(?:\.\d+)?)\s*(?:metres?|m)', re.IGNORECASE)
        }
        
        # Reasonable value ranges for quality control
        self.value_ranges = {
            'setback': (0.3, 15.0),  # 0.3m to 15m reasonable for setbacks
            'height': (2.0, 30.0),   # 2m to 30m reasonable for height limits
            'distance': (0.5, 20.0)  # 0.5m to 20m reasonable for distances
        }
    
    def process_dcp_document(self, pdf_path: str, council_area: FormerCouncilArea) -> Dict[str, any]:
        """
        Process a single DCP document using RAG-Anything for reliable extraction
        
        Args:
            pdf_path: Path to the PDF document
            council_area: The former council area this DCP applies to
            
        Returns:
            Dictionary with extracted rules and metadata
        """
        logging.info(f"Processing {pdf_path} for {council_area.value}")
        
        try:
            if self.rag_engine:
                return self._process_with_rag(pdf_path, council_area)
            else:
                return self._process_fallback(pdf_path, council_area)
        except Exception as e:
            logging.error(f"Failed to process {pdf_path}: {e}")
            return self._empty_result(pdf_path, council_area)
    
    def _process_with_rag(self, pdf_path: str, council_area: FormerCouncilArea) -> Dict[str, any]:
        """Process document using RAG-Anything engine"""
        
        # Initialize document in RAG engine
        doc_id = self.rag_engine.add_document(pdf_path)
        
        # Targeted queries for setback information
        setback_queries = [
            "What are the minimum rear setback requirements for residential buildings?",
            "What are the side setback requirements for R2 residential zones?", 
            "What are the front setback requirements for residential development?",
            "What building height limits apply within setback areas?",
            "What are the minimum distances from boundaries for residential buildings?"
        ]
        
        extracted_rules = {}
        all_responses = []
        
        for query in setback_queries:
            try:
                response = self.rag_engine.query(query, doc_id=doc_id)
                all_responses.append({
                    'query': query,
                    'response': response,
                    'confidence': getattr(response, 'confidence', 0.5)
                })
                
                # Extract structured data from response
                rules = self._extract_rules_from_response(response, query)
                for rule_type, rule_data in rules.items():
                    if rule_type not in extracted_rules:
                        extracted_rules[rule_type] = []
                    extracted_rules[rule_type].append(rule_data)
                    
            except Exception as e:
                logging.warning(f"Query failed: {query} - {e}")
        
        # Validate and consolidate extracted rules
        validated_rules = self._validate_extracted_rules(extracted_rules)
        
        return {
            'source_file': pdf_path,
            'council_area': council_area.value,
            'extraction_method': 'RAG-Anything',
            'raw_responses': all_responses,
            'extracted_rules': validated_rules,
            'quality_score': self._calculate_quality_score(validated_rules)
        }
    
    def _extract_rules_from_response(self, response, query: str) -> Dict[str, Dict]:
        """Extract structured rule data from RAG response"""
        rules = {}
        response_text = str(response) if response else ""
        
        # Identify rule type from query
        rule_type = self._identify_rule_type(query)
        if not rule_type:
            return rules
        
        # Extract measurements from response text
        measurements = self._extract_measurements(response_text)
        
        for measurement in measurements:
            if self._is_valid_measurement(measurement, rule_type):
                rule_data = {
                    'value': measurement['value'],
                    'units': measurement['units'],
                    'context': measurement['context'],
                    'source_text': measurement['source_text'],
                    'confidence': measurement.get('confidence', 0.7)
                }
                
                if rule_type not in rules:
                    rules[rule_type] = []
                rules[rule_type].append(rule_data)
        
        return rules
    
    def _identify_rule_type(self, query: str) -> Optional[str]:
        """Identify the type of rule from the query"""
        query_lower = query.lower()
        
        if 'rear' in query_lower and 'setback' in query_lower:
            return 'rear_setback'
        elif 'side' in query_lower and 'setback' in query_lower:
            return 'side_setback'
        elif 'front' in query_lower and 'setback' in query_lower:
            return 'front_setback'
        elif 'height' in query_lower and ('setback' in query_lower or 'within' in query_lower):
            return 'height_in_setback'
        elif 'height' in query_lower:
            return 'building_height'
        
        return None
    
    def _extract_measurements(self, text: str) -> List[Dict]:
        """Extract numerical measurements from text with context"""
        measurements = []
        
        # Find all measurement patterns
        for pattern_name, pattern in self.measurement_patterns.items():
            matches = pattern.finditer(text)
            
            for match in matches:
                value = float(match.group(1))
                
                # Get surrounding context (50 chars before/after)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                measurements.append({
                    'value': value,
                    'units': 'metres',
                    'context': context,
                    'source_text': match.group(0),
                    'pattern_type': pattern_name,
                    'confidence': self._calculate_measurement_confidence(context, value)
                })
        
        return measurements
    
    def _calculate_measurement_confidence(self, context: str, value: float) -> float:
        """Calculate confidence score for an extracted measurement"""
        confidence = 0.5  # Base confidence
        
        # Boost confidence for specific keywords
        confidence_keywords = [
            'minimum', 'maximum', 'must', 'required', 'shall',
            'setback', 'distance', 'metres', 'boundary'
        ]
        
        context_lower = context.lower()
        keyword_matches = sum(1 for keyword in confidence_keywords if keyword in context_lower)
        confidence += keyword_matches * 0.1
        
        # Reduce confidence for unrealistic values
        if value < 0.3 or value > 20.0:
            confidence -= 0.3
        
        # Boost confidence for common realistic values
        common_values = [0.9, 1.0, 1.5, 3.0, 6.0, 9.0]
        if any(abs(value - cv) < 0.1 for cv in common_values):
            confidence += 0.2
        
        return min(1.0, max(0.0, confidence))
    
    def _is_valid_measurement(self, measurement: Dict, rule_type: str) -> bool:
        """Validate if a measurement is reasonable for the rule type"""
        value = measurement['value']
        
        # Get appropriate range for this rule type
        if 'setback' in rule_type:
            min_val, max_val = self.value_ranges['setback']
        elif 'height' in rule_type:
            min_val, max_val = self.value_ranges['height']
        else:
            min_val, max_val = self.value_ranges['distance']
        
        # Check if value is within reasonable range
        if not (min_val <= value <= max_val):
            logging.warning(f"Rejected unrealistic {rule_type} value: {value}m")
            return False
        
        # Check confidence threshold
        if measurement.get('confidence', 0) < 0.3:
            logging.warning(f"Rejected low-confidence {rule_type} value: {value}m")
            return False
        
        return True
    
    def _validate_extracted_rules(self, extracted_rules: Dict) -> Dict:
        """Validate and consolidate extracted rules"""
        validated_rules = {}
        
        for rule_type, rule_list in extracted_rules.items():
            if not rule_list:
                continue
            
            # Sort by confidence and take the best measurements
            rule_list.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            # Take top 3 measurements for each rule type
            top_rules = rule_list[:3]
            
            # If multiple similar values, consolidate them
            consolidated = self._consolidate_similar_values(top_rules)
            
            if consolidated:
                validated_rules[rule_type] = consolidated
        
        return validated_rules
    
    def _consolidate_similar_values(self, rules: List[Dict]) -> Optional[Dict]:
        """Consolidate similar measurement values"""
        if not rules:
            return None
        
        # Group similar values (within 0.2m)
        groups = []
        for rule in rules:
            value = rule['value']
            added = False
            
            for group in groups:
                if any(abs(value - r['value']) <= 0.2 for r in group):
                    group.append(rule)
                    added = True
                    break
            
            if not added:
                groups.append([rule])
        
        # Take the largest group (most consensus)
        if not groups:
            return None
        
        best_group = max(groups, key=len)
        
        # Average the values in the best group, weighted by confidence
        total_weight = sum(r.get('confidence', 0.5) for r in best_group)
        if total_weight == 0:
            return None
        
        weighted_value = sum(r['value'] * r.get('confidence', 0.5) for r in best_group) / total_weight
        
        # Take the context from the highest confidence rule
        best_rule = max(best_group, key=lambda x: x.get('confidence', 0))
        
        return {
            'value': round(weighted_value, 1),
            'units': 'metres',
            'context': best_rule['context'],
            'confidence': sum(r.get('confidence', 0.5) for r in best_group) / len(best_group),
            'source_count': len(best_group),
            'all_values': [r['value'] for r in best_group]
        }
    
    def _calculate_quality_score(self, validated_rules: Dict) -> float:
        """Calculate overall quality score for extracted rules"""
        if not validated_rules:
            return 0.0
        
        total_confidence = 0
        total_rules = 0
        
        for rule_type, rule_data in validated_rules.items():
            if isinstance(rule_data, dict) and 'confidence' in rule_data:
                total_confidence += rule_data['confidence']
                total_rules += 1
        
        if total_rules == 0:
            return 0.0
        
        base_quality = total_confidence / total_rules
        
        # Bonus for having multiple rule types
        coverage_bonus = min(len(validated_rules) * 0.1, 0.3)
        
        return min(1.0, base_quality + coverage_bonus)
    
    def _process_fallback(self, pdf_path: str, council_area: FormerCouncilArea) -> Dict[str, any]:
        """Fallback processing when RAG-Anything is not available"""
        logging.warning(f"Using fallback processing for {pdf_path}")
        
        # Use simple text extraction and pattern matching
        try:
            import pymupdf
            doc = pymupdf.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            
            # Simple pattern-based extraction
            measurements = self._extract_measurements(text)
            
            # Group by likely rule types based on context
            rules = {}
            for measurement in measurements:
                context = measurement['context'].lower()
                
                if 'rear' in context and 'setback' in context:
                    rule_type = 'rear_setback'
                elif 'side' in context and 'setback' in context:
                    rule_type = 'side_setback'
                elif 'front' in context and 'setback' in context:
                    rule_type = 'front_setback'
                else:
                    continue
                
                if self._is_valid_measurement(measurement, rule_type):
                    if rule_type not in rules:
                        rules[rule_type] = []
                    rules[rule_type].append(measurement)
            
            validated_rules = self._validate_extracted_rules(rules)
            
            return {
                'source_file': pdf_path,
                'council_area': council_area.value,
                'extraction_method': 'Fallback Pattern Matching',
                'extracted_rules': validated_rules,
                'quality_score': self._calculate_quality_score(validated_rules)
            }
            
        except Exception as e:
            logging.error(f"Fallback processing failed: {e}")
            return self._empty_result(pdf_path, council_area)
    
    def _empty_result(self, pdf_path: str, council_area: FormerCouncilArea) -> Dict[str, any]:
        """Return empty result structure"""
        return {
            'source_file': pdf_path,
            'council_area': council_area.value,
            'extraction_method': 'Failed',
            'extracted_rules': {},
            'quality_score': 0.0,
            'error': 'Processing failed'
        }