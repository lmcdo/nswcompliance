#!/usr/bin/env python3
"""
Integrated Multimodal Query System
Combines database-driven AutoSchema with RAG-Anything multimodal data
"""

import json
import os
from typing import Dict, List, Optional
from db_config import get_connection  # Unified PostgreSQL connection
from .database_autoschema_query import DatabaseAutoSchemaQuery

class IntegratedMultimodalQuery:
    """Unified query system combining regulatory relationships with visual context"""
    
    def __init__(self, 
                 db_path: str = "nsw_planning.db",
                 multimodal_path: str = "unified_multimodal_relationships.json"):
        self.db_query = DatabaseAutoSchemaQuery(db_path)
        self.multimodal_path = multimodal_path
        self.multimodal_data = self._load_multimodal_data()
    
    def _load_multimodal_data(self) -> Dict:
        """Load multimodal relationships data"""
        if not os.path.exists(self.multimodal_path):
            print(f"Multimodal data file not found: {self.multimodal_path}")
            return {}
            
        try:
            with open(self.multimodal_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading multimodal data: {e}")
            return {}
    
    def query_integrated_planning_rules(self, 
                                      address: str, 
                                      query_context: str, 
                                      lga_name: Optional[str] = None) -> Dict:
        """
        Query planning rules combining regulatory relationships with visual context
        """
        results = {
            "success": True,
            "address": address,
            "regulatory_relationships": [],
            "visual_context": [],
            "integrated_rules": [],
            "summary": {
                "total_regulatory": 0,
                "total_visual": 0,
                "total_integrated": 0
            }
        }
        
        try:
            # Extract query terms from context
            query_terms = self._extract_query_terms(query_context, address)
            
            # Get regulatory relationships from database
            regulatory_rels = self.db_query.find_regulatory_relationships(query_terms)
            results["regulatory_relationships"] = regulatory_rels
            results["summary"]["total_regulatory"] = len(regulatory_rels)
            
            # Get visual context from multimodal data
            visual_context = self._find_visual_context(query_terms)
            results["visual_context"] = visual_context
            results["summary"]["total_visual"] = len(visual_context)
            
            # Create integrated rules combining both
            integrated_rules = self._create_integrated_rules(regulatory_rels, visual_context)
            results["integrated_rules"] = integrated_rules
            results["summary"]["total_integrated"] = len(integrated_rules)
            
            # Filter by LGA if specified
            if lga_name:
                results = self._filter_by_lga(results, lga_name)
                
        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            print(f"Error in integrated query: {e}")
        
        return results
    
    def _extract_query_terms(self, query_context: str, address: str) -> List[str]:
        """Extract relevant query terms from context and address"""
        terms = []
        
        # Add address components
        if address:
            address_parts = address.replace(',', ' ').split()
            terms.extend([part for part in address_parts if len(part) > 2])
        
        # Add context terms
        if query_context:
            context_terms = query_context.lower().split()
            # Focus on regulatory terms
            regulatory_keywords = [
                'height', 'setback', 'fsr', 'zone', 'development', 'control',
                'residential', 'commercial', 'industrial', 'building', 'planning'
            ]
            for term in context_terms:
                if term in regulatory_keywords or len(term) > 4:
                    terms.append(term)
        
        # Add common NSW planning terms
        terms.extend(['section', 'clause', 'DCP', 'LEP'])
        
        return list(set(terms))
    
    def _find_visual_context(self, query_terms: List[str]) -> List[Dict]:
        """Find relevant visual context from multimodal data"""
        visual_results = []
        
        if not self.multimodal_data or "documents" not in self.multimodal_data:
            return visual_results
        
        # Search through document content for relevant visual elements
        for doc_key, doc_data in self.multimodal_data["documents"].items():
            if "content_sequence" not in doc_data:
                continue
            
            for item in doc_data["content_sequence"]:
                if item.get("type") == "text":
                    text = item.get("text", "").lower()
                    
                    # Check if any query terms appear in the text
                    for term in query_terms:
                        if term.lower() in text:
                            visual_results.append({
                                "document": doc_data.get("document_name", doc_key),
                                "page": item.get("page_idx", 0),
                                "text": item.get("text", "")[:200] + "..." if len(item.get("text", "")) > 200 else item.get("text", ""),
                                "text_level": item.get("text_level", 0),
                                "matched_term": term,
                                "context_type": "document_text"
                            })
                            break  # Only one match per item
        
        return visual_results[:10]  # Limit results
    
    def _create_integrated_rules(self, regulatory_rels: List[Dict], visual_context: List[Dict]) -> List[Dict]:
        """Create integrated planning rules combining regulatory and visual data"""
        integrated_rules = []
        
        # Create rules from regulatory relationships
        for rel in regulatory_rels:
            rule = {
                "rule_id": f"reg_{len(integrated_rules)}",
                "type": "regulatory_rule",
                "source": rel["source"],
                "target": rel["target"],
                "relation": rel["relation"],
                "regulatory_text": rel["text"],
                "document": rel["document"],
                "visual_support": [],
                "confidence": 0.8
            }
            
            # Find supporting visual context
            for visual in visual_context:
                if any(term in visual["text"].lower() for term in [rel["target"].lower(), rel["source"].lower()]):
                    rule["visual_support"].append({
                        "document": visual["document"],
                        "page": visual["page"],
                        "supporting_text": visual["text"],
                        "relevance": "supporting_context"
                    })
                    rule["confidence"] = min(0.95, rule["confidence"] + 0.1)
            
            integrated_rules.append(rule)
        
        # Create rules from visual context that don't have regulatory matches
        visual_only_rules = []
        for visual in visual_context:
            # Check if this visual context already supports a regulatory rule
            already_used = any(
                visual["document"] in [vs.get("document", "") for vs in rule.get("visual_support", [])]
                for rule in integrated_rules
            )
            
            if not already_used and self._is_regulatory_relevant(visual["text"]):
                visual_only_rules.append({
                    "rule_id": f"vis_{len(integrated_rules) + len(visual_only_rules)}",
                    "type": "visual_rule",
                    "source": "visual_analysis",
                    "target": visual["matched_term"],
                    "relation": "references",
                    "visual_text": visual["text"],
                    "document": visual["document"],
                    "page": visual["page"],
                    "confidence": 0.6
                })
        
        integrated_rules.extend(visual_only_rules[:5])  # Limit visual-only rules
        
        return integrated_rules
    
    def _is_regulatory_relevant(self, text: str) -> bool:
        """Check if text contains regulatory language"""
        regulatory_indicators = [
            'shall', 'must', 'required', 'permitted', 'prohibited',
            'section', 'clause', 'development', 'building', 'setback',
            'height', 'metres', 'zone', 'control'
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in regulatory_indicators)
    
    def _filter_by_lga(self, results: Dict, lga_name: str) -> Dict:
        """Filter results by Local Government Area"""
        lga_upper = lga_name.upper()
        
        # Filter regulatory relationships
        filtered_regulatory = [
            rel for rel in results["regulatory_relationships"]
            if lga_upper in rel.get("document", "").upper()
        ]
        
        # Filter visual context
        filtered_visual = [
            vis for vis in results["visual_context"] 
            if lga_upper in vis.get("document", "").upper()
        ]
        
        # Filter integrated rules
        filtered_integrated = [
            rule for rule in results["integrated_rules"]
            if lga_upper in rule.get("document", "").upper()
        ]
        
        # Update results
        results["regulatory_relationships"] = filtered_regulatory
        results["visual_context"] = filtered_visual
        results["integrated_rules"] = filtered_integrated
        results["summary"] = {
            "total_regulatory": len(filtered_regulatory),
            "total_visual": len(filtered_visual), 
            "total_integrated": len(filtered_integrated)
        }
        
        return results

# Test the integrated system
if __name__ == "__main__":
    print("Testing Integrated Multimodal Query System...")
    
    query_system = IntegratedMultimodalQuery()
    
    # Test query
    result = query_system.query_integrated_planning_rules(
        address="123 King St, Marrickville",
        query_context="height and setback requirements for residential development",
        lga_name="Marrickville"
    )
    
    print(f"Success: {result['success']}")
    print(f"Regulatory relationships: {result['summary']['total_regulatory']}")
    print(f"Visual context items: {result['summary']['total_visual']}")
    print(f"Integrated rules: {result['summary']['total_integrated']}")
    
    if result["integrated_rules"]:
        print("\nSample integrated rule:")
        rule = result["integrated_rules"][0]
        print(f"  {rule['source']} -> {rule['relation']} -> {rule['target']}")
        print(f"  Document: {rule['document']}")
        print(f"  Confidence: {rule['confidence']}")