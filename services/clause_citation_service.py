#!/usr/bin/env python3
"""
Clause Citation Service - Retrieve full clause text for citations
Provides expandable clause content for UI display
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
import re

class ClauseCitationService:
    """Service to retrieve full clause text for citations in UI"""
    
    def __init__(self, data_dir: str = "autoschemakg_data_ollama_final"):
        self.data_dir = Path(data_dir)
        self.clause_cache = {}
        self._build_clause_index()
    
    def _build_clause_index(self):
        """Build an index of all clauses and their full text"""
        
        if not self.data_dir.exists():
            print(f"Warning: Data directory {self.data_dir} not found")
            return
        
        # Process all JSON files
        for json_file in self.data_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                text = data.get('text', '')
                doc_name = data.get('metadata', {}).get('document_name', '')
                
                # Parse clauses from text
                self._extract_clauses(text, doc_name)
                    
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
    
    def _extract_clauses(self, text: str, doc_name: str):
        """Extract individual clauses from document text"""
        
        lines = text.split('\n')
        
        for line in lines:
            if line.strip().startswith('Clause'):
                # Parse clause pattern: "Clause X.X.X(x) - type: content"
                match = re.match(r'Clause\s+([0-9.()a-z]+)\s*-\s*([^:]+):\s*(.+)', line.strip())
                if match:
                    clause_num = match.group(1)
                    clause_type = match.group(2).strip()
                    clause_content = match.group(3).strip()
                    
                    # Store in cache with full details
                    clause_key = f"Clause {clause_num}"
                    
                    self.clause_cache[clause_key] = {
                        'clause_number': clause_num,
                        'clause_type': clause_type,
                        'content': clause_content,
                        'full_text': line.strip(),
                        'document': doc_name,
                        'dcp_section': self._get_dcp_section(clause_num)
                    }
    
    def _get_dcp_section(self, clause_num: str) -> str:
        """Determine which DCP section a clause belongs to"""
        
        if clause_num.startswith('4.1'):
            return "Section 4.1 - Low Density Residential Development"
        elif clause_num.startswith('4.2'):
            return "Section 4.2 - Multi Dwelling Housing and RFBs"
        elif clause_num.startswith('4.3'):
            return "Section 4.3 - Boarding Houses"
        elif clause_num.startswith('5.'):
            return "Section 5 - Commercial and Mixed Use Development"
        elif clause_num.startswith('6.'):
            return "Section 6 - Industrial Development"
        elif clause_num.startswith('2.'):
            return "Section 2 - General Development Controls"
        elif clause_num.startswith('8.'):
            return "Section 8 - Heritage"
        elif clause_num.startswith('9.'):
            return "Section 9 - Precinct Controls"
        else:
            return "General Provisions"
    
    def get_clause_citation(self, clause_ref: str) -> Optional[Dict]:
        """
        Get full citation details for a clause reference
        
        Args:
            clause_ref: Clause reference like "Clause 4.2.4(b)" or "4.2.4(b)"
            
        Returns:
            Dictionary with full clause details or None if not found
        """
        
        # Normalize clause reference
        if not clause_ref.startswith('Clause '):
            clause_ref = f"Clause {clause_ref}"
        
        # Look up in cache
        if clause_ref in self.clause_cache:
            return self.clause_cache[clause_ref]
        
        # Try without subsection letter
        base_clause = re.sub(r'\([a-z]\)$', '', clause_ref)
        if base_clause in self.clause_cache:
            return self.clause_cache[base_clause]
        
        return None
    
    def get_related_clauses(self, clause_ref: str) -> List[Dict]:
        """Get all related subclauses for a main clause"""
        
        # Extract base clause number
        base_match = re.match(r'(?:Clause\s+)?(\d+\.\d+(?:\.\d+)?)', clause_ref)
        if not base_match:
            return []
        
        base_num = base_match.group(1)
        related = []
        
        # Find all clauses that start with the same base number
        for key, value in self.clause_cache.items():
            if value['clause_number'].startswith(base_num):
                related.append(value)
        
        # Sort by clause number
        related.sort(key=lambda x: x['clause_number'])
        
        return related
    
    def format_citation_for_ui(self, clause_ref: str) -> Dict:
        """
        Format clause citation for UI display with accordion
        
        Returns dictionary with:
        - citation_text: Brief citation for inline display
        - accordion_title: Title for accordion header
        - accordion_content: Full clause text for accordion body
        - metadata: Additional context (document, section, etc.)
        """
        
        citation = self.get_clause_citation(clause_ref)
        
        if not citation:
            return {
                'citation_text': clause_ref,
                'accordion_title': clause_ref,
                'accordion_content': 'Clause details not found',
                'metadata': {}
            }
        
        # Format for UI display
        return {
            'citation_text': f"Clause {citation['clause_number']}",
            'accordion_title': f"Clause {citation['clause_number']} - {citation['clause_type'].title()}",
            'accordion_content': citation['content'],
            'metadata': {
                'document': citation['document'],
                'section': citation['dcp_section'],
                'type': citation['clause_type']
            },
            'related_clauses': [
                {
                    'number': c['clause_number'],
                    'type': c['clause_type'],
                    'preview': c['content'][:100] + '...' if len(c['content']) > 100 else c['content']
                }
                for c in self.get_related_clauses(clause_ref)[:3]  # Show up to 3 related
            ]
        }

def get_clause_citations_for_api(clause_refs: List[str]) -> List[Dict]:
    """
    API endpoint helper to get multiple clause citations
    
    Args:
        clause_refs: List of clause references
        
    Returns:
        List of formatted citation dictionaries for UI
    """
    
    service = ClauseCitationService()
    citations = []
    
    for ref in clause_refs:
        citations.append(service.format_citation_for_ui(ref))
    
    return citations

# Example usage
if __name__ == "__main__":
    service = ClauseCitationService()
    
    # Test with a sample clause
    test_clauses = [
        "Clause 4.2.4(b)",
        "4.2.4(c)",
        "Clause 4.3.3"
    ]
    
    for clause in test_clauses:
        print(f"\n{'='*60}")
        print(f"Testing: {clause}")
        print('='*60)
        
        result = service.format_citation_for_ui(clause)
        
        print(f"Citation: {result['citation_text']}")
        print(f"Accordion Title: {result['accordion_title']}")
        print(f"Content Preview: {result['accordion_content'][:200]}...")
        print(f"Document: {result['metadata'].get('document', 'N/A')}")
        print(f"Section: {result['metadata'].get('section', 'N/A')}")
        
        if result.get('related_clauses'):
            print(f"\nRelated Clauses:")
            for related in result['related_clauses']:
                print(f"  - {related['number']}: {related['preview'][:50]}...")