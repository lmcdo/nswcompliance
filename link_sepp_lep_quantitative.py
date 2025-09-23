#!/usr/bin/env python3
"""
Comprehensive Authoritative Linking of Quantitative Standards to SEPP/LEP Provisions
Based on proven extraction patterns from the existing system
"""

import re
import psycopg2
from typing import Dict, Tuple, Optional, List
from decimal import Decimal

class AuthoritativeQuantitativeLinking:
 """Link quantitative standards to SEPP/LEP provisions using proven patterns"""
 
 def __init__(self):
 self.pg_conn = psycopg2.connect(
 host='localhost',
 database='nsw_planning',
 user='postgres',
 password='postgres'
 )
 self.pg_cursor = self.pg_conn.cursor()
 
 # Proven regex patterns from schema_extractor.py
 self.extraction_patterns = {
 'setback_front': [
 r'front\s+setback.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
 r'minimum\s+front\s+setback\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
 r'setback.*?front.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
 r'(\d+(?:\.\d+)?)\s*m(?:etres?)?\s+front\s+setback'
 ],
 'setback_rear': [
 r'rear\s+setback.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
 r'minimum\s+rear\s+setback\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
 r'setback.*?rear.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
 r'(\d+(?:\.\d+)?)\s*m(?:etres?)?\s+rear\s+setback'
 ],
 'setback_side': [
 r'side\s+setback.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
 r'minimum\s+side\s+setback\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
 r'setback.*?side.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
 r'(\d+(?:\.\d+)?)\s*m(?:etres?)?\s+side\s+setback'
 ],
 'setback': [ # General setback patterns
 r'setback.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
 r'minimum\s+setback\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
 r'(\d+(?:\.\d+)?)\s*m(?:etres?)?\s+setback'
 ],
 'height': [
 r'maximum\s+(?:building\s+)?height.*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
 r'height.*?(?:must\s+not\s+exceed|maximum).*?(\d+(?:\.\d+)?)\s*m(?:etres?)?',
 r'(\d+(?:\.\d+)?)\s*m(?:etres?)?\s+(?:maximum\s+)?height'
 ],
 'fsr': [
 r'floor\s+space\s+ratio.*?(\d+(?:\.\d+)?):1',
 r'FSR.*?(\d+(?:\.\d+)?)',
 r'maximum\s+FSR.*?(\d+(?:\.\d+)?)'
 ]
 }
 
 self.stats = {
 'sepp_processed': 0,
 'lep_processed': 0,
 'sepp_linked': 0,
 'lep_linked': 0,
 'total_standards_created': 0
 }
 
 def determine_authority_level(self, document_id: str) -> int:
 """Determine legal authority level from document ID"""
 doc_upper = document_id.upper()
 
 if 'STATE_ENVIRONMENTAL' in doc_upper or 'SEPP' in doc_upper:
 return 1 # SEPP - highest authority
 elif 'LOCAL_ENVIRONMENTAL' in doc_upper or '_LEP_' in doc_upper:
 return 2 # LEP - medium authority
 elif 'DCP' in doc_upper or 'DEVELOPMENT_CONTROL' in doc_upper:
 return 3 # DCP - lowest authority
 else:
 return 4 # Other
 
 def extract_numeric_values(self, text: str, context: str) -> List[Tuple[float, str, float]]:
 """Extract numeric values using proven patterns
 Returns: List of (value, unit, confidence) tuples
 """
 results = []
 patterns = self.extraction_patterns.get(context, [])
 
 for pattern in patterns:
 matches = re.finditer(pattern, text, re.IGNORECASE)
 for match in matches:
 try:
 value = float(match.group(1))
 # Filter unrealistic values
 if context.startswith('setback') and (value < 0.5 or value > 50):
 continue
 if context == 'height' and (value < 2 or value > 200):
 continue
 if context == 'fsr' and (value < 0.1 or value > 10):
 continue
 
 # Calculate confidence based on pattern specificity
 confidence = 0.85 if match.group(0).lower().count('minimum') > 0 else 0.75
 confidence = min(0.95, confidence + 0.1) if 'must' in text.lower() else confidence
 
 results.append((value, 'm' if context != 'fsr' else 'ratio', confidence))
 except (ValueError, IndexError):
 continue
 
 return results
 
 def determine_qualifier(self, text: str) -> str:
 """Determine qualifier (minimum, maximum, exactly) from text"""
 text_lower = text.lower()
 
 if 'minimum' in text_lower or 'at least' in text_lower:
 return 'minimum'
 elif 'maximum' in text_lower or 'must not exceed' in text_lower:
 return 'maximum'
 elif 'exactly' in text_lower or 'must be' in text_lower:
 return 'exactly'
 else:
 return 'minimum' # Default for setbacks
 
 def link_quantitative_standards(self):
 """Main process to link quantitative standards to SEPP/LEP provisions"""
 
 print("AUTHORITATIVE QUANTITATIVE STANDARDS LINKING")
 print("=" * 60)
 
 # Get all SEPP/LEP provisions without quantitative standards
 self.pg_cursor.execute("""
 SELECT rp.id, rp.document_id, rp.provision_text, rp.zone, 
 rp.development_type, rp.provision_type
 FROM public.regulatory_provisions rp
 LEFT JOIN public.quantitative_standards qs ON rp.id = qs.provision_id
 WHERE qs.id IS NULL
 AND (
 rp.document_id LIKE '%State_Environmental%'
 OR rp.document_id LIKE '%Local_Environmental%'
 OR rp.document_id LIKE '%SEPP%'
 OR rp.document_id LIKE '%LEP%'
 )
 AND rp.provision_text IS NOT NULL
 """)
 
 provisions = self.pg_cursor.fetchall()
 print(f"Found {len(provisions)} SEPP/LEP provisions without quantitative standards")
 
 for provision in provisions:
 prov_id, doc_id, text, zone, dev_type, prov_type = provision
 
 authority_level = self.determine_authority_level(doc_id)
 
 if authority_level == 1:
 self.stats['sepp_processed'] += 1
 elif authority_level == 2:
 self.stats['lep_processed'] += 1
 
 # Try different context patterns
 contexts_to_try = []
 
 # Determine relevant contexts based on provision type
 if prov_type and 'setback' in prov_type.lower():
 contexts_to_try = ['setback_front', 'setback_rear', 'setback_side', 'setback']
 elif prov_type and 'height' in prov_type.lower():
 contexts_to_try = ['height']
 elif prov_type and 'fsr' in prov_type.lower():
 contexts_to_try = ['fsr']
 else:
 # Try all patterns for unclassified provisions
 if 'setback' in text.lower():
 contexts_to_try.extend(['setback_front', 'setback_rear', 'setback_side', 'setback'])
 if 'height' in text.lower():
 contexts_to_try.append('height')
 if 'fsr' in text.lower() or 'floor space ratio' in text.lower():
 contexts_to_try.append('fsr')
 
 # Extract values for each context
 for context in contexts_to_try:
 values = self.extract_numeric_values(text, context)
 
 for value, unit, confidence in values:
 try:
 # Insert quantitative standard
 self.pg_cursor.execute("""
 INSERT INTO public.quantitative_standards (
 provision_id, numeric_value, unit, qualifier,
 context, confidence_score, manual_verified, raw_text
 ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
 ON CONFLICT DO NOTHING
 RETURNING id
 """, (
 prov_id, 
 value, 
 unit, 
 self.determine_qualifier(text),
 context, 
 confidence, 
 False,
 text[:500] # Store first 500 chars of raw text
 ))
 
 result = self.pg_cursor.fetchone()
 if result:
 self.stats['total_standards_created'] += 1
 
 if authority_level == 1:
 self.stats['sepp_linked'] += 1
 elif authority_level == 2:
 self.stats['lep_linked'] += 1
 
 print(f" [{doc_id[:30]}...] {context}: {value}{unit} (conf: {confidence:.2f})")
 
 except Exception as e:
 if 'duplicate' not in str(e).lower():
 print(f" Error linking standard: {e}")
 
 # Commit all changes
 self.pg_conn.commit()
 
 # Print statistics
 print("\n" + "=" * 60)
 print("LINKING STATISTICS:")
 print(f" SEPP provisions processed: {self.stats['sepp_processed']}")
 print(f" SEPP standards linked: {self.stats['sepp_linked']}")
 print(f" LEP provisions processed: {self.stats['lep_processed']}")
 print(f" LEP standards linked: {self.stats['lep_linked']}")
 print(f" Total standards created: {self.stats['total_standards_created']}")
 
 # Verify results
 self.verify_linkages()
 
 def verify_linkages(self):
 """Verify the linking results"""
 
 print("\n" + "=" * 60)
 print("VERIFICATION:")
 
 # Check SEPP quantitative standards
 self.pg_cursor.execute("""
 SELECT COUNT(DISTINCT rp.id)
 FROM public.regulatory_provisions rp
 JOIN public.quantitative_standards qs ON rp.id = qs.provision_id
 WHERE rp.document_id LIKE '%State_Environmental%'
 OR rp.document_id LIKE '%SEPP%'
 """)
 sepp_with_quant = self.pg_cursor.fetchone()[0]
 
 # Check LEP quantitative standards
 self.pg_cursor.execute("""
 SELECT COUNT(DISTINCT rp.id)
 FROM public.regulatory_provisions rp
 JOIN public.quantitative_standards qs ON rp.id = qs.provision_id
 WHERE rp.document_id LIKE '%Local_Environmental%'
 OR rp.document_id LIKE '%LEP%'
 """)
 lep_with_quant = self.pg_cursor.fetchone()[0]
 
 print(f" SEPP provisions with quantitative standards: {sepp_with_quant}")
 print(f" LEP provisions with quantitative standards: {lep_with_quant}")
 
 # Sample hierarchy test
 self.pg_cursor.execute("""
 SELECT 
 CASE 
 WHEN rp.document_id LIKE '%State_Environmental%' THEN 'SEPP'
 WHEN rp.document_id LIKE '%Local_Environmental%' THEN 'LEP'
 ELSE 'DCP'
 END as authority,
 rp.zone,
 qs.context,
 qs.numeric_value,
 qs.unit
 FROM public.regulatory_provisions rp
 JOIN public.quantitative_standards qs ON rp.id = qs.provision_id
 WHERE rp.zone = 'R2'
 AND qs.context LIKE '%setback%'
 ORDER BY 
 CASE 
 WHEN rp.document_id LIKE '%State_Environmental%' THEN 1
 WHEN rp.document_id LIKE '%Local_Environmental%' THEN 2
 ELSE 3
 END
 LIMIT 5
 """)
 
 print("\n Sample R2 Setbacks by Authority:")
 for row in self.pg_cursor.fetchall():
 print(f" [{row[0]}] Zone {row[1]} - {row[2]}: {row[3]}{row[4]}")
 
 def close(self):
 """Close database connections"""
 self.pg_conn.close()

if __name__ == "__main__":
 linker = AuthoritativeQuantitativeLinking()
 try:
 linker.link_quantitative_standards()
 finally:
 linker.close()
 
 print("\n Authoritative quantitative linking complete!")