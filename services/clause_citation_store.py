#!/usr/bin/env python3
"""
Clause Citation Store - Fast retrieval system for full regulatory citations
Provides immediate access to complete clause text for API responses
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
import re
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class FullClauseResult:
    """Complete clause result with metadata for API responses"""
    clause_number: str
    clause_title: str
    full_text: str
    document_name: str
    document_section: str
    page_number: Optional[int]
    extraction_confidence: float
    source_authority: str  # "Inner West Council" etc.
    citation_format: str   # Formatted for copy-paste
    requires_verification: bool
    last_updated: str

@dataclass
class CitationSearchResult:
    """Search result with matching citations"""
    query: str
    matches_found: int
    exact_matches: List[FullClauseResult]
    partial_matches: List[FullClauseResult]
    search_time_ms: int

class ClauseCitationStore:
    """
    Fast storage and retrieval system for complete clause citations
    Supports various lookup patterns for API integration
    """
    
    def __init__(self, storage_dir: str = "clause_citations"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        self._clause_index = {}
        self._document_index = {}
        self._loaded = False
        
        # Load indexes if they exist
        self._load_indexes()
    
    def _load_indexes(self):
        """Load pre-built indexes from storage"""
        try:
            clause_index_path = self.storage_dir / "clause_number_index.json"
            if clause_index_path.exists():
                with open(clause_index_path, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                    self._clause_index = {k: self._dict_to_clause_result(v) for k, v in index_data.items()}
                logger.info(f"Loaded clause index with {len(self._clause_index)} entries")
            
            doc_citations_path = self.storage_dir / "full_clause_citations.json"
            if doc_citations_path.exists():
                with open(doc_citations_path, 'r', encoding='utf-8') as f:
                    doc_data = json.load(f)
                    self._document_index = doc_data.get('citations_by_document', {})
                logger.info(f"Loaded document index with {len(self._document_index)} documents")
            
            self._loaded = True
            
        except Exception as e:
            logger.error(f"Failed to load indexes: {e}")
            self._clause_index = {}
            self._document_index = {}
    
    def get_full_clause_citation(self, clause_reference: str) -> Optional[FullClauseResult]:
        """
        Get complete clause citation by clause number/reference
        Supports various formats: "4.1.5.1", "Clause 4.1.5.1", etc.
        """
        if not self._loaded:
            self._load_indexes()
        
        # Normalize the clause reference for lookup
        normalized_refs = self._normalize_clause_reference(clause_reference)
        
        for ref in normalized_refs:
            if ref in self._clause_index:
                citation = self._clause_index[ref]
                logger.debug(f"Found citation for {clause_reference} -> {citation.clause_number}")
                return citation
        
        logger.warning(f"No citation found for clause reference: {clause_reference}")
        return None
    
    def search_clauses(self, query: str, max_results: int = 10) -> CitationSearchResult:
        """
        Search for clauses by text content, title, or number
        Returns both exact and partial matches
        """
        start_time = datetime.now()
        
        if not self._loaded:
            self._load_indexes()
        
        query_lower = query.lower()
        exact_matches = []
        partial_matches = []
        
        for clause_ref, citation in self._clause_index.items():
            # Check for exact clause number match
            if query_lower in clause_ref.lower():
                exact_matches.append(citation)
                continue
            
            # Check for text content matches
            if (query_lower in citation.full_text.lower() or 
                query_lower in citation.clause_title.lower() or
                query_lower in citation.document_section.lower()):
                partial_matches.append(citation)
                
                if len(partial_matches) >= max_results:
                    break
        
        # Remove duplicates and limit results
        exact_matches = list({c.clause_number: c for c in exact_matches}.values())[:max_results]
        partial_matches = list({c.clause_number: c for c in partial_matches}.values())[:max_results]
        
        search_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return CitationSearchResult(
            query=query,
            matches_found=len(exact_matches) + len(partial_matches),
            exact_matches=exact_matches,
            partial_matches=partial_matches,
            search_time_ms=search_time
        )
    
    def get_clauses_by_document(self, document_name: str) -> List[FullClauseResult]:
        """Get all clauses from a specific document"""
        if not self._loaded:
            self._load_indexes()
        
        for doc_key, citation_list in self._document_index.items():
            if document_name.lower() in doc_key.lower():
                return [self._dict_to_clause_result(citation) for citation in citation_list]
        
        return []
    
    def enrich_planning_rule(self, planning_rule) -> Dict[str, Any]:
        """
        Enhance existing PlanningRule with complete citation
        Takes existing rule and adds full regulatory text
        """
        # Extract clause reference from existing rule
        clause_ref = self._extract_clause_from_title(planning_rule.title)
        
        if clause_ref:
            full_citation = self.get_full_clause_citation(clause_ref)
            
            if full_citation:
                return {
                    # Original fields
                    'title': planning_rule.title,
                    'text': planning_rule.text,  # Keep summary
                    'source': planning_rule.source,
                    'type': getattr(planning_rule, 'type', 'unknown'),
                    'confidence': getattr(planning_rule, 'confidence', 0.8),
                    
                    # Enhanced citation fields
                    'full_clause_text': full_citation.full_text,
                    'clause_number': full_citation.clause_number,
                    'clause_title': full_citation.clause_title,
                    'document_section': full_citation.document_section,
                    'citation_format': full_citation.citation_format,
                    'extraction_confidence': full_citation.extraction_confidence,
                    'source_authority': full_citation.source_authority,
                    'requires_verification': full_citation.requires_verification,
                    
                    # Display metadata
                    'has_full_citation': True,
                    'citation_available': True
                }
        
        # Return original data if no citation found
        return {
            'title': planning_rule.title,
            'text': planning_rule.text,
            'source': planning_rule.source,
            'type': getattr(planning_rule, 'type', 'unknown'),
            'confidence': getattr(planning_rule, 'confidence', 0.8),
            'has_full_citation': False,
            'citation_available': False,
            'citation_note': f'Full citation not available for: {clause_ref or "clause reference not found"}'
        }
    
    def batch_enrich_planning_rules(self, planning_rules: List) -> List[Dict[str, Any]]:
        """Enrich multiple planning rules with citations"""
        enriched_rules = []
        
        for rule in planning_rules:
            enriched_rule = self.enrich_planning_rule(rule)
            enriched_rules.append(enriched_rule)
        
        citations_found = sum(1 for rule in enriched_rules if rule.get('has_full_citation', False))
        logger.info(f"Enriched {len(planning_rules)} rules, {citations_found} with full citations")
        
        return enriched_rules
    
    def get_citation_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored citations"""
        if not self._loaded:
            self._load_indexes()
        
        total_clauses = len(self._clause_index)
        total_documents = len(self._document_index)
        
        # Count clauses by document type
        doc_types = {}
        confidence_levels = []
        
        for citation in self._clause_index.values():
            # Extract document type
            if 'DCP' in citation.document_name:
                doc_type = 'DCP'
            elif 'LEP' in citation.document_name:
                doc_type = 'LEP'
            elif 'SEPP' in citation.document_name:
                doc_type = 'SEPP'
            else:
                doc_type = 'Other'
            
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            confidence_levels.append(citation.extraction_confidence)
        
        avg_confidence = sum(confidence_levels) / len(confidence_levels) if confidence_levels else 0
        
        return {
            'total_clauses': total_clauses,
            'total_documents': total_documents,
            'clauses_by_document_type': doc_types,
            'average_extraction_confidence': round(avg_confidence, 3),
            'high_confidence_clauses': sum(1 for c in confidence_levels if c >= 0.9),
            'storage_loaded': self._loaded
        }
    
    def _normalize_clause_reference(self, clause_ref: str) -> List[str]:
        """Generate multiple normalized forms for flexible lookup"""
        if not clause_ref:
            return []
        
        normalized = []
        clean_ref = clause_ref.strip()
        
        # Add original
        normalized.append(clean_ref)
        
        # Remove "Clause " prefix if present
        if clean_ref.startswith('Clause '):
            clean_num = clean_ref.replace('Clause ', '')
            normalized.append(clean_num)
        else:
            normalized.append(f'Clause {clean_ref}')
        
        # Add case variations
        normalized.extend([clean_ref.lower(), clean_ref.upper()])
        
        # Handle parenthetical references like "4.2.4(a)" -> "4.2.4.1"
        if '(' in clean_ref and ')' in clean_ref:
            letter_map = {'a': '1', 'b': '2', 'c': '3', 'd': '4', 'e': '5'}
            for letter, number in letter_map.items():
                if f'({letter})' in clean_ref:
                    dot_format = clean_ref.replace(f'({letter})', f'.{number}')
                    normalized.append(dot_format)
        
        return normalized
    
    def _extract_clause_from_title(self, title: str) -> Optional[str]:
        """Extract clause reference from planning rule title"""
        if not title:
            return None
        
        # Common patterns for clause references
        patterns = [
            r'Clause\s+(\d+(?:\.\d+)*(?:\([a-z]\))?)',  # "Clause 4.1.5.1" or "Clause 4.2.4(a)"
            r'Section\s+(\d+(?:\.\d+)*)',                # "Section 4.1.5"
            r'(\d+(?:\.\d+){2,})',                       # "4.1.5.1" (at least 3 parts)
            r'(\d+\.\d+\([a-z]\))',                      # "4.2.4(a)" format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _dict_to_clause_result(self, citation_dict: Dict[str, Any]) -> FullClauseResult:
        """Convert dictionary to FullClauseResult dataclass"""
        return FullClauseResult(
            clause_number=citation_dict.get('clause_number', ''),
            clause_title=citation_dict.get('clause_title', ''),
            full_text=citation_dict.get('full_text', ''),
            document_name=citation_dict.get('document_name', ''),
            document_section=citation_dict.get('document_section', ''),
            page_number=citation_dict.get('page_number'),
            extraction_confidence=citation_dict.get('extraction_confidence', 0.8),
            source_authority=self._determine_source_authority(citation_dict.get('document_name', '')),
            citation_format=self._format_citation(citation_dict),
            requires_verification=citation_dict.get('extraction_confidence', 0.8) < 0.9,
            last_updated=citation_dict.get('extraction_timestamp', datetime.now().isoformat())
        )
    
    def _determine_source_authority(self, document_name: str) -> str:
        """Determine the regulatory authority from document name"""
        if 'Inner West' in document_name or 'Marrickville' in document_name or 'Ashfield' in document_name:
            return 'Inner West Council'
        elif 'NSW' in document_name or 'State' in document_name:
            return 'NSW Planning'
        else:
            return 'Unknown Authority'
    
    def _format_citation(self, citation_dict: Dict[str, Any]) -> str:
        """Format citation for copy-paste use"""
        doc_name = citation_dict.get('document_name', '')
        clause_num = citation_dict.get('clause_number', '')
        clause_title = citation_dict.get('clause_title', '')
        
        if clause_title:
            return f"{doc_name}, Clause {clause_num} - {clause_title}"
        else:
            return f"{doc_name}, Clause {clause_num}"

# Convenience functions for API integration
def get_citation_for_clause(clause_ref: str) -> Optional[FullClauseResult]:
    """Quick function to get citation for a clause reference"""
    store = ClauseCitationStore()
    return store.get_full_clause_citation(clause_ref)

def enrich_planning_rules_with_citations(planning_rules: List) -> List[Dict[str, Any]]:
    """Quick function to enrich planning rules with full citations"""
    store = ClauseCitationStore()
    return store.batch_enrich_planning_rules(planning_rules)

def search_clause_citations(query: str, max_results: int = 10) -> CitationSearchResult:
    """Quick function to search clause citations"""
    store = ClauseCitationStore()
    return store.search_clauses(query, max_results)

if __name__ == "__main__":
    # Test the citation store
    store = ClauseCitationStore()
    stats = store.get_citation_statistics()
    
    print("📊 Clause Citation Store Statistics:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Test citation retrieval
    if stats['total_clauses'] > 0:
        print("\n🔍 Testing citation retrieval...")
        test_clauses = ['4.1.5.1', 'Clause 2.12.4.6', '4.3']
        
        for test_clause in test_clauses:
            citation = store.get_full_clause_citation(test_clause)
            if citation:
                print(f"✅ Found: {citation.clause_number} - {citation.clause_title[:50]}...")
            else:
                print(f"❌ Not found: {test_clause}")
    
    print(f"\n✅ Citation store ready for API integration!")