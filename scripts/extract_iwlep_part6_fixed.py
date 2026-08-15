#!/usr/bin/env python3
"""
Extract Part 6 from Inner West LEP 2022 - FIXED VERSION
Handles multiple clauses on same page correctly
"""
import pdfplumber
import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Any

PDF_PATH = Path("./extraction_outputs/leps/Inner West Local Environmental Plan 2022 - NSW Legislation/auto/Inner West Local Environmental Plan 2022 - NSW Legislation_origin.pdf")
DB_PATH = Path("./nsw_planning.db")
DOCUMENT_ID = "Inner_West_Local_Environmental_Plan_2022_Part_6"

START_PAGE = 59  # Page 60
END_PAGE = 88    # Page 89


def extract_part6():
    """Extract Part 6 with proper handling of multiple clauses per page"""
    print("Opening PDF...")
    
    with pdfplumber.open(PDF_PATH) as pdf:
        # First pass: collect all text
        all_text = ""
        page_boundaries = [0]  # Track where each page starts in the text
        
        for page_idx in range(START_PAGE, END_PAGE + 1):
            if page_idx >= len(pdf.pages):
                break
            
            page = pdf.pages[page_idx]
            text = page.extract_text() or ""
            all_text += f"\n\n=== PAGE {page_idx + 1} ===\n\n{text}"
            page_boundaries.append(len(all_text))
        
        print(f"Extracted {len(all_text)} characters from {END_PAGE - START_PAGE + 1} pages")
        
        # Second pass: find all clause headings and their positions
        clause_pattern = r'^(6\.(\d+))\s+([A-Z][a-z][^\n]{5,80})'
        matches = list(re.finditer(clause_pattern, all_text, re.MULTILINE))
        
        print(f"Found {len(matches)} clause headings")
        
        clauses = []
        
        for i, match in enumerate(matches):
            clause_num = match.group(1)
            clause_title = match.group(3).strip()
            start_pos = match.start()
            
            # Find end position (start of next clause or end of text)
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(all_text)
            
            # Extract content
            content = all_text[start_pos:end_pos].strip()
            
            # Find which pages this clause spans
            start_page = None
            end_page = None
            
            for page_idx in range(len(page_boundaries) - 1):
                if start_page is None and page_boundaries[page_idx] <= start_pos < page_boundaries[page_idx + 1]:
                    start_page = START_PAGE + page_idx + 1
                if end_page is None and page_boundaries[page_idx] <= end_pos <= page_boundaries[page_idx + 1]:
                    end_page = START_PAGE + page_idx + 1
                    break
            
            if start_page is None:
                start_page = START_PAGE + 1
            if end_page is None:
                end_page = END_PAGE + 1
            
            clauses.append({
                'clause_number': clause_num,
                'clause_title': clause_title,
                'content': content,
                'page_start': start_page,
                'page_end': end_page,
                'content_length': len(content)
            })
            
            print(f"  {clause_num:6} p.{start_page}-{end_page} ({len(content):5} chars) - {clause_title[:50]}")
        
        return clauses


def clean_content(content: str) -> str:
    """Clean up extracted text"""
    # Remove page markers
    content = re.sub(r'=== PAGE \d+ ===', '', content)
    # Remove excessive whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)
    # Remove page numbers
    content = re.sub(r'^\d+\s*$', '', content, flags=re.MULTILINE)
    return content.strip()


def save_to_database(clauses):
    """Save to database"""
    print("\nSaving to database...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Delete existing
    cursor.execute("DELETE FROM regulatory_provisions WHERE document_id = ?", (DOCUMENT_ID,))
    
    # Insert new
    for clause in clauses:
        content = clean_content(clause['content'])
        
        cursor.execute("""
            INSERT INTO regulatory_provisions (
                document_id, provision_type, ref_number, 
                provision_text, page_number, section_header, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            DOCUMENT_ID, 'lep_additional_local', clause['clause_number'],
            content, clause['page_start'], clause['clause_title']
        ))
    
    conn.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE document_id = ?", (DOCUMENT_ID,))
    count = cursor.fetchone()[0]
    print(f"Saved {count} provisions")
    
    conn.close()


def main():
    print("="*80)
    print("INNER WEST LEP 2022 - PART 6 EXTRACTION (FIXED)")
    print("="*80 + "\n")
    
    clauses = extract_part6()
    
    if not clauses:
        print("ERROR: No clauses extracted")
        return 1
    
    save_to_database(clauses)
    
    print("\nDone!")
    return 0


if __name__ == "__main__":
    exit(main())
