#!/usr/bin/env python3
"""
Parse specific DCP sections for setback rules ahead of time
Focus on known setback sections across Inner West DCPs
"""

import os
import sys
from pathlib import Path

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
sys.path.insert(0, src_path)

# Import with absolute paths
import pymupdf
from enum import Enum

class FormerCouncilArea(Enum):
    ASHFIELD = "Ashfield"
    LEICHHARDT = "Leichhardt" 
    MARRICKVILLE = "Marrickville"

class SimplePDFProcessor:
    """Simple PDF text extraction using PyMuPDF"""
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        doc = pymupdf.open(pdf_path)
        full_text = []
        
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text = page.get_text()
            if text.strip():
                full_text.append(text)
        
        doc.close()
        return '\n'.join(full_text)

class SetbackSectionParser:
    """Parse known DCP setback sections to understand schemas ahead of time"""
    
    def __init__(self):
        self.processor = SimplePDFProcessor()
        self.docs_path = Path(__file__).parent.parent / "docs" / "dcps" / "INNERWEST"
        
        # Known setback-related documents for each council area
        self.setback_documents = {
            FormerCouncilArea.ASHFIELD: [
                "Inner West Ashfield DCP 2016 - Chapter F - Development Category with IWLEP 2022 amendment.pdf"
            ],
            FormerCouncilArea.LEICHHARDT: [
                "leichhardt/Leichhardt DCP 2013 - 5 -  Part C Place Section 1 - with IWLEP 2022 amendments March 23.pdf"
            ],
            FormerCouncilArea.MARRICKVILLE: [
                "Marrickville/Marrickville DCP 2011 - Contents Nov 22.pdf"  # May need to find specific section
            ]
        }
    
    def parse_all_setback_sections(self):
        """Parse all known setback sections"""
        print("Parsing Known DCP Setback Sections")
        print("=" * 50)
        
        all_schemas = {}
        
        for area, documents in self.setback_documents.items():
            print(f"\n{area.value} Council Setback Rules:")
            print("-" * 30)
            
            area_schemas = []
            
            for doc_name in documents:
                doc_path = self.docs_path / doc_name
                
                if not doc_path.exists():
                    print(f"WARNING: Document not found: {doc_name}")
                    continue
                
                print(f"Processing: {doc_name}")
                
                try:
                    # Extract text from the document
                    full_text = self.processor.extract_text_from_pdf(str(doc_path))
                    
                    # Find setback-related sections
                    setback_sections = self._find_setback_sections(full_text)
                    
                    for section in setback_sections:
                        schema = self._analyze_setback_schema(section)
                        if schema:
                            area_schemas.append({
                                'document': doc_name,
                                'section_title': schema['title'],
                                'content_preview': schema['preview'],
                                'detected_patterns': schema['patterns'],
                                'setback_types': schema['setback_types']
                            })
                            
                            print(f"  FOUND: {schema['title']}")
                            print(f"    Patterns: {', '.join(schema['patterns'])}")
                            print(f"    Setback Types: {', '.join(schema['setback_types'])}")
                
                except Exception as e:
                    print(f"ERROR processing {doc_name}: {e}")
            
            all_schemas[area.value] = area_schemas
        
        return all_schemas
    
    def _find_setback_sections(self, text: str) -> list:
        """Find sections that contain setback rules"""
        import re
        
        # Look for common setback section headers
        setback_patterns = [
            r'(?i)(setbacks?.*?)(?=\n[A-Z]|\n\d+\.|\Z)',
            r'(?i)(building envelope.*?)(?=\n[A-Z]|\n\d+\.|\Z)',
            r'(?i)(rear.*?setback.*?)(?=\n[A-Z]|\n\d+\.|\Z)',
            r'(?i)(side.*?setback.*?)(?=\n[A-Z]|\n\d+\.|\Z)',
            r'(?i)(front.*?setback.*?)(?=\n[A-Z]|\n\d+\.|\Z)',
            r'(?i)(building.*?separation.*?)(?=\n[A-Z]|\n\d+\.|\Z)'
        ]
        
        sections = []
        for pattern in setback_patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
            for match in matches:
                section_text = match.group(1)
                if len(section_text) > 100:  # Skip very short matches
                    sections.append(section_text[:2000])  # Limit to reasonable length
        
        return sections
    
    def _analyze_setback_schema(self, section_text: str) -> dict:
        """Analyze a setback section to understand its schema"""
        import re
        
        schema = {
            'title': self._extract_section_title(section_text),
            'preview': section_text[:300] + "...",
            'patterns': [],
            'setback_types': []
        }
        
        # Look for common setback measurement patterns
        measurement_patterns = [
            r'\d+(?:\.\d+)?\s*m(?:etres?)?',  # "6 metres", "6.0m"
            r'\d+(?:\.\d+)?m',               # "6m"
            r'minimum.*?\d+(?:\.\d+)?\s*m',  # "minimum 6 metres"
            r'maximum.*?\d+(?:\.\d+)?\s*m',  # "maximum 3 metres"
            r'at least.*?\d+(?:\.\d+)?\s*m', # "at least 1.5 metres"
        ]
        
        for pattern in measurement_patterns:
            if re.search(pattern, section_text, re.IGNORECASE):
                schema['patterns'].append(pattern)
        
        # Identify setback types mentioned
        setback_types = ['rear', 'side', 'front', 'building']
        for setback_type in setback_types:
            if setback_type in section_text.lower():
                schema['setback_types'].append(setback_type)
        
        return schema if schema['patterns'] and schema['setback_types'] else None
    
    def _extract_section_title(self, text: str) -> str:
        """Extract the section title from text"""
        lines = text.split('\n')[:5]  # Look at first few lines
        for line in lines:
            line = line.strip()
            if len(line) > 10 and len(line) < 100:  # Reasonable title length
                if any(word in line.lower() for word in ['setback', 'envelope', 'building']):
                    return line
        return "Setback Section"

def main():
    parser = SetbackSectionParser()
    schemas = parser.parse_all_setback_sections()
    
    print(f"\n{'='*50}")
    print("SCHEMA ANALYSIS COMPLETE")
    print(f"{'='*50}")
    
    # Summary
    total_sections = sum(len(sections) for sections in schemas.values())
    print(f"Total setback sections found: {total_sections}")
    
    for area, sections in schemas.items():
        print(f"\n{area}: {len(sections)} sections")
        for section in sections:
            print(f"  - {section['section_title']}")
    
    return schemas

if __name__ == "__main__":
    main()