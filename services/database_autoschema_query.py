#!/usr/bin/env python3
"""
Database-driven AutoSchema Query Interface
Query regulatory relationships directly from the nsw_planning.db database
"""

import sqlite3
import re
from typing import Dict, List, Optional

class DatabaseAutoSchemaQuery:
    """Query AutoSchemaKG data directly from the nsw_planning database"""
    
    def __init__(self, db_path: str = "nsw_planning.db"):
        self.db_path = db_path
    
    def find_regulatory_relationships(self, query_terms: List[str]) -> List[Dict]:
        """Find regulatory relationships based on query terms using database text search"""
        
        relationships = []
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Search for related clauses in the full text
            for term in query_terms:
                # Search in regulatory_refs for clause relationships
                cursor.execute("""
                    SELECT 
                        r.ref_number,
                        r.ref_type,
                        r.ref_context,
                        d.pdf_name,
                        d.full_text,
                        d.document_area
                    FROM regulatory_refs r
                    JOIN documents d ON r.document_id = d.id
                    WHERE r.ref_context LIKE ? 
                       OR d.full_text LIKE ?
                       OR r.ref_number LIKE ?
                    LIMIT 20
                """, (f'%{term}%', f'%{term}%', f'%{term}%'))
                
                results = cursor.fetchall()
                
                for row in results:
                    # Extract potential relationships from the context and full text
                    ref_text = row['ref_context'] or ''
                    full_text = row['full_text'] or ''
                    
                    # Use a section of full text around the reference for context
                    context_text = self._extract_context_around_reference(
                        full_text, row['ref_number'], row['ref_type']
                    )
                    
                    clause_relationships = self._extract_relationships_from_text(
                        ref_text + ' ' + context_text, 
                        f"{row['ref_type']} {row['ref_number']}",
                        row['pdf_name']
                    )
                    relationships.extend(clause_relationships)
        
        return self._deduplicate_relationships(relationships)
    
    def _extract_context_around_reference(self, full_text: str, ref_number: str, ref_type: str) -> str:
        """Extract text context around a reference for relationship extraction"""
        if not full_text or not ref_number:
            return ''
        
        # Look for the reference in the text
        patterns = [
            f'{ref_type} {ref_number}',
            f'{ref_number}',
            f'section {ref_number}',
            f'clause {ref_number}'
        ]
        
        for pattern in patterns:
            pos = full_text.lower().find(pattern.lower())
            if pos >= 0:
                # Extract 500 characters around the reference
                start = max(0, pos - 250)
                end = min(len(full_text), pos + 250)
                return full_text[start:end]
        
        return ''
    
    def _extract_relationships_from_text(self, text: str, clause_number: str, document: str) -> List[Dict]:
        """Extract relationships from regulatory text using patterns"""
        relationships = []
        
        if not text:
            return relationships
        
        # Pattern 1: "in accordance with" - enhanced patterns
        accordance_patterns = [
            r'in accordance with\s+part\s+(\d+(?:\.\d+)*)',
            r'in accordance with\s+section\s+(\d+(?:\.\d+)*)',
            r'in accordance with\s+clause\s+(\d+(?:\.\d+)*)', 
            r'in accordance with\s+part\s+(\d+)\s*\(([^)]+)\)',  # "Part 8 (Heritage)"
            r'in accordance with\s+([a-z\s]+standards)',  # "relevant Australian Standards"
            r'in accordance with\s+([a-z\s]+council[^\.]+)',  # Council guidelines
        ]
        
        for pattern in accordance_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                if isinstance(match, tuple):
                    if len(match) == 2 and match[1]:  # "Part 8 (Heritage)" format
                        target = f'Part {match[0]} ({match[1].title()})'
                    else:
                        target = match[0] if match[0] else match[1]
                else:
                    target = f'Section {match}' if pattern.startswith(r'in accordance with\s+section') else match
                
                relationships.append({
                    'source': clause_number,
                    'relation': 'in_accordance_with',
                    'target': target.title(),
                    'document': document,
                    'text': text[:200] + "..." if len(text) > 200 else text
                })
        
        # Pattern 2: "subject to the requirements of"
        subject_pattern = r'subject to.*?requirements of.*?(clause|section)\s+(\d+(?:\.\d+)*)'
        matches = re.findall(subject_pattern, text.lower())
        for match in matches:
            relationships.append({
                'source': clause_number,
                'relation': 'subject_to',
                'target': f'{match[0].title()} {match[1]}',
                'document': document,
                'text': text[:200] + "..." if len(text) > 200 else text
            })
        
        # Pattern 3: "must comply with"
        comply_pattern = r'must comply with.*?(clause|section)\s+(\d+(?:\.\d+)*)'
        matches = re.findall(comply_pattern, text.lower())
        for match in matches:
            relationships.append({
                'source': clause_number,
                'relation': 'must_comply_with',
                'target': f'{match[0].title()} {match[1]}',
                'document': document,
                'text': text[:200] + "..." if len(text) > 200 else text
            })
        
        # Pattern 4: Development type relationships
        if 'height' in text.lower() and any(term in text.lower() for term in ['metres', 'storeys']):
            relationships.append({
                'source': clause_number,
                'relation': 'regulates',
                'target': 'building_height',
                'document': document,
                'text': text[:200] + "..." if len(text) > 200 else text
            })
        
        if 'setback' in text.lower():
            relationships.append({
                'source': clause_number,
                'relation': 'regulates', 
                'target': 'building_setback',
                'document': document,
                'text': text[:200] + "..." if len(text) > 200 else text
            })
        
        # Pattern 5: "Refer to" references - very common in DCPs
        refer_patterns = [
            r'refer to\s+part\s+(\d+(?:\.\d+)*)',
            r'refer to\s+section\s+(\d+(?:\.\d+)*)',
            r'refer to\s+clause\s+(\d+(?:\.\d+)*)',
            r'refer to\s+part\s+(\d+)\s*\(([^)]+)\)',  # "Part 8 (Heritage)"
            r'refer to\s+schedule\s+(\d+)',
            r'see\s+part\s+(\d+(?:\.\d+)*)',
            r'see\s+section\s+(\d+(?:\.\d+)*)',
        ]
        
        for pattern in refer_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                if isinstance(match, tuple):
                    if len(match) == 2 and match[1]:  # "Part 8 (Heritage)" format
                        target = f'Part {match[0]} ({match[1].title()})'
                    else:
                        target = match[0] if match[0] else match[1]
                else:
                    if 'part' in pattern:
                        target = f'Part {match}'
                    elif 'section' in pattern:
                        target = f'Section {match}'
                    elif 'clause' in pattern:
                        target = f'Clause {match}'
                    elif 'schedule' in pattern:
                        target = f'Schedule {match}'
                    else:
                        target = match
                
                relationships.append({
                    'source': clause_number,
                    'relation': 'refers_to',
                    'target': target,
                    'document': document,
                    'text': text[:200] + "..." if len(text) > 200 else text
                })
        
        # Pattern 6: "under" references
        under_patterns = [
            r'under\s+part\s+(\d+(?:\.\d+)*)',
            r'under\s+section\s+(\d+(?:\.\d+)*)',
            r'under\s+clause\s+(\d+(?:\.\d+)*)',
            r'pursuant to\s+(part|section|clause)\s+(\d+(?:\.\d+)*)',
        ]
        
        for pattern in under_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                if isinstance(match, tuple):
                    target = f'{match[0].title()} {match[1]}'
                else:
                    if 'part' in pattern:
                        target = f'Part {match}'
                    elif 'section' in pattern:
                        target = f'Section {match}'
                    elif 'clause' in pattern:
                        target = f'Clause {match}'
                    else:
                        target = match
                
                relationships.append({
                    'source': clause_number,
                    'relation': 'under',
                    'target': target,
                    'document': document,
                    'text': text[:200] + "..." if len(text) > 200 else text
                })
        
        # Pattern 7: LEP and SEPP references - CRITICAL for hierarchy
        lep_sepp_patterns = [
            r'inner west lep\s+(\d+)',  # "Inner West LEP 2022"
            r'lep\s+(\d+)',            # "LEP 2022"
            r'local environmental plan\s+(\d+)',
            r'sepp\s+(\d+)',           # "SEPP 65"
            r'state environmental planning policy\s+(\d+)',
            r'provisions of.*?lep.*?shall prevail',  # LEP precedence
            r'provisions of.*?inner west lep.*?(\d+)',
            r'clause\s+(\d+(?:\.\d+)*)\s+of.*?lep',  # "Clause 4.3 of LEP"
            r'clause\s+(\d+(?:\.\d+)*)\s+of.*?sepp',  # "Clause 6 of SEPP 65"
        ]
        
        for pattern in lep_sepp_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                if 'lep' in pattern:
                    if 'prevail' in pattern:
                        target = f'Inner West LEP {match}' if match else 'Inner West LEP 2022'
                        relation = 'prevails_over'
                    elif 'clause' in pattern:
                        target = f'LEP Clause {match}'
                        relation = 'subject_to'
                    else:
                        target = f'Inner West LEP {match}'
                        relation = 'in_accordance_with'
                elif 'sepp' in pattern:
                    if 'clause' in pattern:
                        target = f'SEPP Clause {match}'
                        relation = 'must_comply_with'
                    else:
                        target = f'SEPP {match}'
                        relation = 'in_accordance_with'
                else:
                    target = match
                    relation = 'refers_to'
                
                relationships.append({
                    'source': clause_number,
                    'relation': relation,
                    'target': target,
                    'document': document,
                    'text': text[:200] + "..." if len(text) > 200 else text
                })
        
        # Pattern 8: Specific NSW planning hierarchy patterns
        hierarchy_patterns = [
            r'shall prevail to the extent of.*?inconsistency',  # LEP precedence
            r'to be read in conjunction with.*?(lep|sepp)',
            r'subject to.*?(lep|sepp)',
            r'notwithstanding.*?(lep|sepp)',
        ]
        
        for pattern in hierarchy_patterns:
            if re.search(pattern, text.lower()):
                if 'lep' in text.lower():
                    target = 'Inner West LEP 2022'
                    relation = 'subject_to' if 'subject' in pattern else 'prevails_over'
                elif 'sepp' in text.lower():
                    # Extract SEPP number if possible
                    sepp_match = re.search(r'sepp\s+(\d+)', text.lower())
                    target = f'SEPP {sepp_match.group(1)}' if sepp_match else 'SEPP'
                    relation = 'must_comply_with'
                else:
                    continue
                
                relationships.append({
                    'source': clause_number,
                    'relation': relation,
                    'target': target,
                    'document': document,
                    'text': text[:200] + "..." if len(text) > 200 else text
                })
        
        return relationships
    
    def _deduplicate_relationships(self, relationships: List[Dict]) -> List[Dict]:
        """Remove duplicate and self-referential relationships"""
        seen = set()
        unique = []
        
        for rel in relationships:
            # Skip self-referential relationships (not useful)
            source_normalized = rel['source'].lower().strip()
            target_normalized = rel['target'].lower().strip()
            
            # Skip if source and target are effectively the same
            if source_normalized == target_normalized:
                continue
            
            # Skip if target is just the source clause reference repeated  
            if rel['target'].lower().replace('section ', '').replace('sections ', '') in rel['source'].lower():
                continue
                
            key = f"{rel['source']}|{rel['relation']}|{rel['target']}"
            if key not in seen:
                seen.add(key)
                unique.append(rel)
        
        return unique
    
    def query_clause_relationships(self, clause_ref: str) -> List[Dict]:
        """Find all relationships for a specific clause"""
        return self.find_regulatory_relationships([clause_ref])
    
    def query_development_controls(self, development_type: str, zone: str) -> List[Dict]:
        """Find development controls for specific type and zone"""
        query_terms = [development_type, zone, 'setback', 'height', 'FSR']
        return self.find_regulatory_relationships(query_terms)

# Test the database query system
if __name__ == "__main__":
    print("Testing Database AutoSchema Query...")
    
    db_query = DatabaseAutoSchemaQuery()
    
    # Test 1: Find height relationships
    print("\n1. Finding height relationships...")
    height_rels = db_query.find_regulatory_relationships(['height', 'metres'])
    print(f"Found {len(height_rels)} height relationships")
    for rel in height_rels[:3]:
        print(f"  {rel['source']} -> {rel['relation']} -> {rel['target']}")
    
    # Test 2: Find setback relationships  
    print("\n2. Finding setback relationships...")
    setback_rels = db_query.find_regulatory_relationships(['setback'])
    print(f"Found {len(setback_rels)} setback relationships")
    for rel in setback_rels[:3]:
        print(f"  {rel['source']} -> {rel['relation']} -> {rel['target']}")
    
    # Test 3: Zone-specific query
    print("\n3. Finding R2 zone relationships...")
    r2_rels = db_query.query_development_controls('residential', 'R2')
    print(f"Found {len(r2_rels)} R2 relationships")
    for rel in r2_rels[:3]:
        print(f"  {rel['source']} -> {rel['relation']} -> {rel['target']}")