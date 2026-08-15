#!/usr/bin/env python3
"""
Extract Part 6 "Additional Local Provisions" from Inner West LEP 2022
Pages 60-88, Clauses 6.1 through 6.34
"""
import pdfplumber
import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Any
import json

# Configuration
PDF_PATH = Path("./extraction_outputs/leps/Inner West Local Environmental Plan 2022 - NSW Legislation/auto/Inner West Local Environmental Plan 2022 - NSW Legislation_origin.pdf")
DB_PATH = Path("./nsw_planning.db")
DOCUMENT_ID = "Inner_West_Local_Environmental_Plan_2022_Part_6"

# Part 6 page range (0-indexed for Python)
START_PAGE = 59  # Page 60
END_PAGE = 88    # Page 89

class Part6Extractor:
    """Extract Part 6 clauses from Inner West LEP 2022"""
    
    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self.clauses = []
    
    def extract_clauses(self) -> List[Dict[str, Any]]:
        """Extract all clauses from Part 6"""
        print(f"Opening PDF: {self.pdf_path}")
        
        with pdfplumber.open(self.pdf_path) as pdf:
            print(f"Total pages in PDF: {len(pdf.pages)}")
            print(f"Extracting pages {START_PAGE + 1} to {END_PAGE + 1}...")
            
            current_clause = None
            
            for page_idx in range(START_PAGE, END_PAGE + 1):
                if page_idx >= len(pdf.pages):
                    break
                
                page = pdf.pages[page_idx]
                page_num = page_idx + 1
                text = page.extract_text() or ""
                
                print(f"  Page {page_num}...", end='\r')
                
                # Look for clause headings: "6.XX" followed by clause title
                # Pattern: "6.1 Acid sulfate soils" or "6.32 Special entertainment precinct"
                clause_matches = list(re.finditer(r'^(6\.(\d+))\s+([A-Z][a-z][^\n]{5,80})', text, re.MULTILINE))
                
                if clause_matches:
                    for match in clause_matches:
                        # Save previous clause
                        if current_clause:
                            current_clause['page_end'] = page_num - 1
                            self.clauses.append(current_clause)
                        
                        # Start new clause
                        clause_num = match.group(1)
                        clause_title = match.group(3).strip()
                        
                        current_clause = {
                            'clause_number': clause_num,
                            'clause_title': clause_title,
                            'content': '',
                            'page_start': page_num,
                            'page_end': page_num,
                            'pages': [page_num]
                        }
                        
                        print(f"\n  Found: {clause_num} - {clause_title}")
                
                # Append content to current clause
                if current_clause:
                    current_clause['content'] += f"\n{text}"
                    if page_num not in current_clause['pages']:
                        current_clause['pages'].append(page_num)
            
            # Save final clause
            if current_clause:
                current_clause['page_end'] = END_PAGE + 1
                self.clauses.append(current_clause)
        
        print(f"\n\nExtracted {len(self.clauses)} clauses")
        return self.clauses
    
    def clean_content(self, content: str) -> str:
        """Clean up extracted text"""
        # Remove excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        # Remove page numbers and headers
        content = re.sub(r'^\d+\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^Inner West Local Environmental Plan.*$', '', content, flags=re.MULTILINE)
        return content.strip()
    
    def save_to_database(self):
        """Save extracted clauses to database"""
        print("\nConnecting to database...")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("Deleting existing Part 6 provisions...")
        cursor.execute("""
            DELETE FROM regulatory_provisions 
            WHERE document_id = ?
        """, (DOCUMENT_ID,))
        
        print(f"Inserting {len(self.clauses)} provisions...")
        
        for clause in self.clauses:
            content = self.clean_content(clause['content'])
            
            # Insert provision
            cursor.execute("""
                INSERT INTO regulatory_provisions (
                    document_id,
                    provision_type,
                    ref_number,
                    provision_text,
                    page_number,
                    section_header,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                DOCUMENT_ID,
                'lep_additional_local',
                clause['clause_number'],
                content,
                clause['page_start'],
                clause['clause_title']
            ))
        
        conn.commit()
        
        # Verify insertion
        cursor.execute("""
            SELECT COUNT(*) FROM regulatory_provisions 
            WHERE document_id = ?
        """, (DOCUMENT_ID,))
        
        count = cursor.fetchone()[0]
        print(f"✓ Saved {count} provisions to database")
        
        conn.close()
    
    def generate_summary(self):
        """Generate extraction summary"""
        print("\n" + "="*80)
        print("EXTRACTION SUMMARY")
        print("="*80)
        
        for clause in self.clauses:
            pages_str = f"{clause['page_start']}-{clause['page_end']}" if clause['page_start'] != clause['page_end'] else str(clause['page_start'])
            content_len = len(clause['content'])
            
            print(f"{clause['clause_number']:6} | p.{pages_str:6} | {content_len:5} chars | {clause['clause_title'][:50]}")
        
        print("="*80)
        print(f"Total: {len(self.clauses)} clauses extracted")


def main():
    print("="*80)
    print("INNER WEST LEP 2022 - PART 6 EXTRACTION")
    print("="*80)
    
    if not PDF_PATH.exists():
        print(f"ERROR: PDF not found at {PDF_PATH}")
        return 1
    
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        return 1
    
    extractor = Part6Extractor(PDF_PATH)
    
    # Extract clauses
    clauses = extractor.extract_clauses()
    
    if not clauses:
        print("ERROR: No clauses extracted!")
        return 1
    
    # Show summary
    extractor.generate_summary()
    
    # Save to database
    extractor.save_to_database()
    
    print("\n✓ Extraction complete!")
    return 0


if __name__ == "__main__":
    exit(main())
