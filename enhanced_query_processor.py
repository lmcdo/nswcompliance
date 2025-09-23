#!/usr/bin/env python3
"""
ENHANCED QUERY PROCESSOR
========================

Replaces the missing scripts.validated_nsw_query module with a working
query processor that uses the new normalized database structure.

Fixes the broken setback query system by providing:
- Direct database access to regulatory provisions
- Extracted development controls with numeric values
- Page-perfect citations from LangExtract
- Zone-specific queries with confidence scoring
"""

import sqlite3
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
 """Structured query result with citations"""
 text: str
 confidence: float
 page_number: Optional[int]
 section_header: Optional[str] 
 document_id: str
 zone: Optional[str]
 development_type: Optional[str]
 source_table: str
 
@dataclass
class ControlResult:
 """Structured control result with extracted values"""
 control_type: str
 control_subtype: str
 value_numeric: float
 value_text: str
 unit: str
 zone_applicable: str
 confidence_score: float
 provision_text: str
 page_number: Optional[int]
 section_header: Optional[str]

class EnhancedQueryProcessor:
 """Enhanced query processor using normalized database structure"""
 
 def __init__(self, db_path='nsw_planning.db'):
 self.db_path = db_path
 
 def query_validated_processor(self, query: str) -> str:
 """Main query interface - replaces the missing scripts.validated_nsw_query"""
 try:
 # Parse query intent
 query_intent = self._parse_query_intent(query)
 
 if query_intent['type'] == 'setback':
 results = self._query_setback_controls(query_intent)
 return self._format_setback_response(results)
 
 elif query_intent['type'] == 'height':
 results = self._query_height_controls(query_intent)
 return self._format_height_response(results)
 
 elif query_intent['type'] == 'general':
 results = self._query_general_provisions(query_intent)
 return self._format_general_response(results)
 
 else:
 return "No specific controls found for this query"
 
 except Exception as e:
 logger.error(f"Query processing failed: {e}")
 return f"ERROR: Query processing failed - {str(e)}"
 
 def _parse_query_intent(self, query: str) -> Dict[str, Any]:
 """Parse user query to understand intent"""
 query_lower = query.lower()
 
 # Setback queries
 if any(term in query_lower for term in ['setback', 'front', 'side', 'rear', 'boundary']):
 intent = {
 'type': 'setback',
 'zones': self._extract_zones(query),
 'setback_types': self._extract_setback_types(query),
 'development_types': self._extract_development_types(query)
 }
 return intent
 
 # Height queries
 elif any(term in query_lower for term in ['height', 'storey', 'floor', 'level']):
 return {
 'type': 'height',
 'zones': self._extract_zones(query),
 'height_types': self._extract_height_types(query)
 }
 
 # General provision queries
 else:
 return {
 'type': 'general',
 'zones': self._extract_zones(query),
 'keywords': self._extract_keywords(query)
 }
 
 def _extract_zones(self, query: str) -> List[str]:
 """Extract zone references from query"""
 zones = []
 zone_patterns = [
 r'\b(R[1-4]|B[1-4]|IN[1-2]|RE[1-2]|SP[1-2])\b',
 r'\bresidential\b.*\b(low|medium|high)\b',
 r'\bcommercial\b',
 r'\bindustrial\b'
 ]
 
 for pattern in zone_patterns:
 matches = re.findall(pattern, query, re.IGNORECASE)
 zones.extend(matches)
 
 return list(set(zones))
 
 def _extract_setback_types(self, query: str) -> List[str]:
 """Extract setback types from query"""
 types = []
 if re.search(r'\bfront\b', query, re.IGNORECASE):
 types.append('front')
 if re.search(r'\bside\b', query, re.IGNORECASE):
 types.append('side')
 if re.search(r'\brear\b', query, re.IGNORECASE):
 types.append('rear')
 
 return types or ['general']
 
 def _extract_development_types(self, query: str) -> List[str]:
 """Extract development types from query"""
 dev_types = []
 dev_patterns = [
 (r'dual\s+occupanc', 'dual_occupancy'),
 (r'single\s+dwelling', 'single_dwelling'),
 (r'multi\s+dwelling', 'multi_dwelling'),
 (r'townhouse', 'townhouse'),
 (r'apartment', 'apartment')
 ]
 
 for pattern, dev_type in dev_patterns:
 if re.search(pattern, query, re.IGNORECASE):
 dev_types.append(dev_type)
 
 return dev_types
 
 def _extract_height_types(self, query: str) -> List[str]:
 """Extract height control types from query"""
 types = []
 if re.search(r'\blimit\b', query, re.IGNORECASE):
 types.append('limit')
 if re.search(r'\bmaximum\b', query, re.IGNORECASE):
 types.append('maximum')
 if re.search(r'\bstorey', query, re.IGNORECASE):
 types.append('storeys')
 
 return types or ['general']
 
 def _extract_keywords(self, query: str) -> List[str]:
 """Extract key search terms from query"""
 # Remove common words and extract meaningful terms
 stop_words = {'the', 'and', 'or', 'is', 'are', 'for', 'in', 'of', 'to', 'a', 'an'}
 words = re.findall(r'\b\w+\b', query.lower())
 return [word for word in words if word not in stop_words and len(word) > 2]
 
 def _query_setback_controls(self, intent: Dict[str, Any]) -> List[ControlResult]:
 """Query specific setback controls from database"""
 conn = sqlite3.connect(self.db_path)
 cur = conn.cursor()
 
 # Build query based on intent
 where_conditions = ["dc.control_type = 'setback'"]
 params = []
 
 # Zone filtering
 if intent.get('zones'):
 zone_conditions = []
 for zone in intent['zones']:
 zone_conditions.append("(rp.zone = ? OR dc.zone_applicable = ?)")
 params.extend([zone, zone])
 where_conditions.append(f"({' OR '.join(zone_conditions)})")
 
 # Setback type filtering
 if intent.get('setback_types') and 'general' not in intent['setback_types']:
 type_conditions = []
 for setback_type in intent['setback_types']:
 type_conditions.append("dc.control_subtype = ?")
 params.append(setback_type)
 where_conditions.append(f"({' OR '.join(type_conditions)})")
 
 query = f"""
 SELECT rp.provision_text, dc.control_type, dc.control_subtype, dc.value_numeric,
 dc.value_text, dc.unit, dc.zone_applicable, dc.confidence_score,
 rp.page_number, rp.section_header, rp.document_id, rp.zone
 FROM regulatory_provisions rp
 JOIN development_controls dc ON rp.id = dc.provision_id
 WHERE {' AND '.join(where_conditions)}
 ORDER BY dc.confidence_score DESC, rp.page_number ASC
 LIMIT 10
 """
 
 cur.execute(query, params)
 rows = cur.fetchall()
 
 results = []
 for row in rows:
 (provision_text, control_type, control_subtype, value_numeric,
 value_text, unit, zone_applicable, confidence_score,
 page_number, section_header, document_id, zone) = row
 
 results.append(ControlResult(
 control_type=control_type,
 control_subtype=control_subtype,
 value_numeric=value_numeric,
 value_text=value_text,
 unit=unit,
 zone_applicable=zone_applicable,
 confidence_score=confidence_score,
 provision_text=provision_text,
 page_number=page_number,
 section_header=section_header
 ))
 
 conn.close()
 return results
 
 def _query_height_controls(self, intent: Dict[str, Any]) -> List[ControlResult]:
 """Query height controls from database"""
 conn = sqlite3.connect(self.db_path)
 cur = conn.cursor()
 
 where_conditions = ["dc.control_type = 'height'"]
 params = []
 
 # Zone filtering
 if intent.get('zones'):
 zone_conditions = []
 for zone in intent['zones']:
 zone_conditions.append("(rp.zone = ? OR dc.zone_applicable = ?)")
 params.extend([zone, zone])
 where_conditions.append(f"({' OR '.join(zone_conditions)})")
 
 query = f"""
 SELECT rp.provision_text, dc.control_type, dc.control_subtype, dc.value_numeric,
 dc.value_text, dc.unit, dc.zone_applicable, dc.confidence_score,
 rp.page_number, rp.section_header, rp.document_id, rp.zone
 FROM regulatory_provisions rp
 JOIN development_controls dc ON rp.id = dc.provision_id
 WHERE {' AND '.join(where_conditions)}
 ORDER BY dc.confidence_score DESC, rp.page_number ASC
 LIMIT 10
 """
 
 cur.execute(query, params)
 rows = cur.fetchall()
 
 results = []
 for row in rows:
 (provision_text, control_type, control_subtype, value_numeric,
 value_text, unit, zone_applicable, confidence_score,
 page_number, section_header, document_id, zone) = row
 
 results.append(ControlResult(
 control_type=control_type,
 control_subtype=control_subtype,
 value_numeric=value_numeric,
 value_text=value_text,
 unit=unit,
 zone_applicable=zone_applicable,
 confidence_score=confidence_score,
 provision_text=provision_text,
 page_number=page_number,
 section_header=section_header
 ))
 
 conn.close()
 return results
 
 def _query_general_provisions(self, intent: Dict[str, Any]) -> List[QueryResult]:
 """Query general regulatory provisions"""
 conn = sqlite3.connect(self.db_path)
 cur = conn.cursor()
 
 where_conditions = []
 params = []
 
 # Zone filtering
 if intent.get('zones'):
 zone_conditions = []
 for zone in intent['zones']:
 zone_conditions.append("zone = ?")
 params.append(zone)
 where_conditions.append(f"({' OR '.join(zone_conditions)})")
 
 # Keyword filtering
 if intent.get('keywords'):
 keyword_conditions = []
 for keyword in intent['keywords']:
 keyword_conditions.append("provision_text LIKE ?")
 params.append(f'%{keyword}%')
 where_conditions.append(f"({' OR '.join(keyword_conditions)})")
 
 if where_conditions:
 where_clause = f"WHERE {' AND '.join(where_conditions)}"
 else:
 where_clause = "WHERE page_number IS NOT NULL" # Prioritize entries with citations
 
 query = f"""
 SELECT provision_text, page_number, section_header, document_id, 
 zone, development_type
 FROM regulatory_provisions
 {where_clause}
 ORDER BY page_number ASC, text_level ASC
 LIMIT 10
 """
 
 cur.execute(query, params)
 rows = cur.fetchall()
 
 results = []
 for row in rows:
 (provision_text, page_number, section_header, document_id, 
 zone, development_type) = row
 
 results.append(QueryResult(
 text=provision_text,
 confidence=0.8, # Default confidence for general queries
 page_number=page_number,
 section_header=section_header,
 document_id=document_id,
 zone=zone,
 development_type=development_type,
 source_table='regulatory_provisions'
 ))
 
 conn.close()
 return results
 
 def _format_setback_response(self, results: List[ControlResult]) -> str:
 """Format setback control results into response text"""
 if not results:
 return "No setback controls found for the specified criteria."
 
 response_parts = []
 
 for result in results:
 # Create citation
 citation = ""
 if result.page_number:
 citation = f" (Page {result.page_number}"
 if result.section_header:
 citation += f", {result.section_header}"
 citation += ")"
 
 # Format the response
 control_desc = f"{result.control_subtype} setback {result.value_text}" if result.control_subtype != 'general' else f"setback {result.value_text}"
 
 response_parts.append(f"{control_desc}{citation}: {result.provision_text[:150]}...")
 
 return "\n\n".join(response_parts)
 
 def _format_height_response(self, results: List[ControlResult]) -> str:
 """Format height control results into response text"""
 if not results:
 return "No height controls found for the specified criteria."
 
 response_parts = []
 
 for result in results:
 citation = ""
 if result.page_number:
 citation = f" (Page {result.page_number}"
 if result.section_header:
 citation += f", {result.section_header}"
 citation += ")"
 
 control_desc = f"{result.control_subtype} height {result.value_text}" if result.control_subtype != 'general' else f"height {result.value_text}"
 
 response_parts.append(f"{control_desc}{citation}: {result.provision_text[:150]}...")
 
 return "\n\n".join(response_parts)
 
 def _format_general_response(self, results: List[QueryResult]) -> str:
 """Format general query results into response text"""
 if not results:
 return "No relevant provisions found for this query."
 
 response_parts = []
 
 for result in results:
 citation = ""
 if result.page_number:
 citation = f" (Page {result.page_number}"
 if result.section_header:
 citation += f", {result.section_header}"
 citation += ")"
 
 response_parts.append(f"{result.text[:200]}...{citation}")
 
 return "\n\n".join(response_parts)

# Global instance for compatibility with existing code
_query_processor = None

def query_validated_processor(query: str) -> str:
 """Global function interface - replaces scripts.validated_nsw_query.query_validated_processor"""
 global _query_processor
 if _query_processor is None:
 _query_processor = EnhancedQueryProcessor()
 
 return _query_processor.query_validated_processor(query)

def test_query_system():
 """Test the enhanced query system"""
 processor = EnhancedQueryProcessor()
 
 test_queries = [
 "R2 front setback requirements",
 "side setback for dual occupancy",
 "height limit R2 zone",
 "Marrickville DCP setback controls"
 ]
 
 print("TESTING ENHANCED QUERY SYSTEM")
 print("=" * 60)
 
 for query in test_queries:
 print(f"\nQuery: {query}")
 print("-" * 40)
 try:
 result = processor.query_validated_processor(query)
 print(result[:300] + "..." if len(result) > 300 else result)
 except Exception as e:
 print(f"Error: {e}")

if __name__ == "__main__":
 test_query_system()