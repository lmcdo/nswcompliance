#!/usr/bin/env python3
"""
Full Clause Extractor - Extract complete regulatory paragraphs from DCP documents
Builds on existing MinerU/PDF processing to create council-quality citations
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from services.full_clause_langextract_config import extract_full_clauses_with_langextract

logger = logging.getLogger(__name__)

@dataclass
class FullClauseCitation:
    """Complete regulatory clause citation for council use"""
    clause_number: str
    clause_title: str
    full_text: str
    document_name: str
    document_section: str
    page_number: Optional[int]
    char_start: int
    char_end: int
    extraction_confidence: float
    source_file_path: str
    extraction_timestamp: str

class FullClauseExtractor:
    """
    Extract complete regulatory clauses maintaining full authoritative text
    Uses existing MinerU-extracted content as source
    """
    
    def __init__(self, output_dir: str = "clause_citations"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.citation_cache = {}
        
    def extract_from_existing_mineru_output(self, output_dir: str = "output") -> Dict[str, List[FullClauseCitation]]:
        """
        Process existing MinerU output to extract complete clause citations
        Uses the high-quality markdown files already generated
        """
        mineru_output = Path(output_dir)
        if not mineru_output.exists():
            logger.error(f"MinerU output directory not found: {output_dir}")
            return {}
            
        logger.info(f"Processing MinerU output from {mineru_output}")
        
        all_citations = {}
        processed_files = 0
        
        # Process all markdown files from MinerU
        for md_file in mineru_output.glob("**/*.md"):
            try:
                document_name = self._extract_document_name_from_path(md_file)
                logger.info(f"Extracting full clauses from: {document_name}")
                
                # Read the high-quality markdown content
                with open(md_file, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
                
                if len(markdown_content) < 500:  # Skip empty or minimal files
                    logger.warning(f"Skipping small file: {md_file} ({len(markdown_content)} chars)")
                    continue
                
                # Extract complete clauses using enhanced LangExtract
                extraction_result = extract_full_clauses_with_langextract(
                    document_text=markdown_content,
                    document_name=document_name
                )
                
                if extraction_result.get('processing_successful'):
                    citations = []
                    for clause_num, clause_data in extraction_result['clauses'].items():
                        citation = FullClauseCitation(
                            clause_number=clause_num,
                            clause_title=clause_data.get('clause_title', ''),
                            full_text=clause_data.get('full_text', ''),
                            document_name=document_name,
                            document_section=clause_data.get('document_section', ''),
                            page_number=None,  # Could enhance with page detection
                            char_start=clause_data.get('char_start', 0),
                            char_end=clause_data.get('char_end', 0),
                            extraction_confidence=clause_data.get('extraction_confidence', 0.85),
                            source_file_path=str(md_file),
                            extraction_timestamp=datetime.now().isoformat()
                        )
                        citations.append(citation)
                    
                    all_citations[document_name] = citations
                    processed_files += 1
                    
                    logger.info(f"✅ Extracted {len(citations)} complete clauses from {document_name}")
                    
                else:
                    logger.error(f"❌ Failed to process {document_name}: {extraction_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"Error processing {md_file}: {e}")
                continue
        
        logger.info(f"Processed {processed_files} documents, extracted citations from {len(all_citations)} documents")
        return all_citations
    
    def process_priority_documents(self) -> Dict[str, List[FullClauseCitation]]:
        """
        Process the most important documents first for MVP
        Focus on Inner West DCPs and LEPs that users query most
        """
        priority_patterns = [
            "*Marrickville*DCP*2011*",
            "*Inner*West*LEP*2022*", 
            "*Ashfield*DCP*2016*",
            "*Leichhardt*DCP*2013*"
        ]
        
        all_citations = {}
        
        for pattern in priority_patterns:
            logger.info(f"Processing priority documents matching: {pattern}")
            
            # Find matching MinerU output files
            output_dir = Path("output")
            for md_file in output_dir.glob(f"**/{pattern}.md"):
                document_name = self._extract_document_name_from_path(md_file)
                
                if document_name in all_citations:
                    continue  # Already processed
                    
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if len(content) < 1000:  # Skip minimal files
                        continue
                        
                    logger.info(f"Priority processing: {document_name}")
                    
                    extraction_result = extract_full_clauses_with_langextract(content, document_name)
                    
                    if extraction_result.get('processing_successful'):
                        citations = []
                        for clause_num, clause_data in extraction_result['clauses'].items():
                            citation = FullClauseCitation(
                                clause_number=clause_num,
                                clause_title=clause_data.get('clause_title', ''),
                                full_text=clause_data.get('full_text', ''),
                                document_name=document_name,
                                document_section=clause_data.get('document_section', ''),
                                page_number=None,
                                char_start=clause_data.get('char_start', 0),
                                char_end=clause_data.get('char_end', 0),
                                extraction_confidence=clause_data.get('extraction_confidence', 0.85),
                                source_file_path=str(md_file),
                                extraction_timestamp=datetime.now().isoformat()
                            )
                            citations.append(citation)
                        
                        all_citations[document_name] = citations
                        logger.info(f"✅ Priority document processed: {len(citations)} clauses from {document_name}")
                        
                except Exception as e:
                    logger.error(f"Error processing priority document {md_file}: {e}")
        
        return all_citations
    
    def save_citations_to_storage(self, citations: Dict[str, List[FullClauseCitation]], output_file: str = "full_clause_citations.json"):
        """Save extracted citations to JSON storage for quick retrieval"""
        
        output_path = self.output_dir / output_file
        
        # Convert dataclasses to dictionaries for JSON serialization
        serializable_citations = {}
        for doc_name, citation_list in citations.items():
            serializable_citations[doc_name] = [asdict(citation) for citation in citation_list]
        
        # Add extraction metadata
        storage_data = {
            'extraction_metadata': {
                'total_documents': len(citations),
                'total_clauses': sum(len(citation_list) for citation_list in citations.values()),
                'extraction_method': 'LangExtract_Enhanced_Full_Clause',
                'created_timestamp': datetime.now().isoformat(),
                'version': '1.0.0'
            },
            'citations_by_document': serializable_citations
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(storage_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Saved {storage_data['extraction_metadata']['total_clauses']} citations to {output_path}")
        return output_path
    
    def create_clause_number_index(self, citations: Dict[str, List[FullClauseCitation]]) -> Dict[str, FullClauseCitation]:
        """
        Create fast lookup index: clause_number → full_citation
        For quick retrieval during API responses
        """
        clause_index = {}
        
        for doc_name, citation_list in citations.items():
            for citation in citation_list:
                # Create multiple lookup keys for flexible matching
                clause_keys = [
                    citation.clause_number,
                    citation.clause_number.replace('Clause ', ''),
                    f"Clause {citation.clause_number}",
                    citation.clause_number.lower(),
                    citation.clause_number.upper()
                ]
                
                for key in clause_keys:
                    if key and key not in clause_index:  # Avoid duplicates, first wins
                        clause_index[key] = citation
        
        # Save index for fast loading
        index_path = self.output_dir / "clause_number_index.json"
        serializable_index = {k: asdict(v) for k, v in clause_index.items()}
        
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_index, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📇 Created clause index with {len(clause_index)} lookup keys")
        return clause_index
    
    def _extract_document_name_from_path(self, file_path: Path) -> str:
        """Extract clean document name from file path"""
        name = file_path.stem
        
        # Clean up common MinerU naming patterns
        name = name.replace('_', ' ').replace('-', ' ')
        name = ' '.join(name.split())  # Normalize whitespace
        
        # Add proper document type if not present
        if 'DCP' not in name.upper() and 'LEP' not in name.upper():
            if 'marrickville' in name.lower():
                name = f"Marrickville DCP 2011 - {name}"
            elif 'inner west' in name.lower():
                name = f"Inner West LEP 2022 - {name}"
        
        return name

def run_full_clause_extraction_mvp():
    """
    Run the complete clause extraction process for MVP
    Focus on priority documents needed for council demonstration
    """
    print("🎯 STARTING FULL CLAUSE EXTRACTION FOR COUNCIL MVP")
    print("=" * 60)
    
    extractor = FullClauseExtractor()
    
    # Step 1: Process priority documents first
    print("\n📋 Step 1: Processing priority documents...")
    priority_citations = extractor.process_priority_documents()
    
    if not priority_citations:
        print("⚠️  No priority documents found, processing all available...")
        priority_citations = extractor.extract_from_existing_mineru_output()
    
    if not priority_citations:
        print("❌ No documents processed successfully")
        return False
    
    # Step 2: Save citations to storage
    print("\n💾 Step 2: Saving citations to storage...")
    storage_path = extractor.save_citations_to_storage(priority_citations)
    
    # Step 3: Create fast lookup index
    print("\n📇 Step 3: Creating clause number index...")
    clause_index = extractor.create_clause_number_index(priority_citations)
    
    # Step 4: Validation and summary
    print("\n✅ EXTRACTION COMPLETE!")
    print(f"Documents processed: {len(priority_citations)}")
    total_clauses = sum(len(citations) for citations in priority_citations.values())
    print(f"Total clauses extracted: {total_clauses}")
    print(f"Lookup index entries: {len(clause_index)}")
    print(f"Storage location: {storage_path}")
    
    # Show sample citations
    print("\n📄 Sample extracted citations:")
    sample_count = 0
    for doc_name, citation_list in priority_citations.items():
        if sample_count >= 3:
            break
        for citation in citation_list[:2]:  # Show 2 from each document
            print(f"   {citation.clause_number}: {citation.full_text[:100]}...")
            sample_count += 1
            if sample_count >= 3:
                break
    
    print(f"\n🎯 Ready for API integration and council MVP demonstration!")
    return True

if __name__ == "__main__":
    success = run_full_clause_extraction_mvp()
    if success:
        print("\n✅ Full clause extraction completed successfully!")
    else:
        print("\n❌ Extraction failed - check logs for details")