#!/usr/bin/env python3
"""
Split Large PDF Documents for Faster Processing
===============================================
Identifies documents >300k chars and splits them into smaller sections
"""

import sqlite3
import json
from datetime import datetime

def identify_large_documents(threshold=300000):
    """Find documents larger than threshold"""
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT pdf_name, char_count, full_text 
        FROM documents 
        WHERE char_count > ? 
        ORDER BY char_count DESC
    """, (threshold,))
    
    large_docs = cursor.fetchall()
    conn.close()
    
    return large_docs

def analyze_document_sections(full_text, pdf_name):
    """Analyze document for natural split points"""
    
    # Look for section markers
    section_markers = [
        "CHAPTER ", "PART ", "SECTION ", "SCHEDULE ",
        "DIVISION ", "CLAUSE ", "APPENDIX "
    ]
    
    sections = []
    current_pos = 0
    
    for i, line in enumerate(full_text.split('\n')):
        line_upper = line.upper().strip()
        
        # Check if this line starts a new section
        for marker in section_markers:
            if line_upper.startswith(marker) and len(line_upper) < 100:
                if current_pos > 0:  # Don't split at very beginning
                    sections.append({
                        'start': current_pos,
                        'end': i,
                        'title': line.strip(),
                        'estimated_chars': (i - current_pos) * 50  # Rough estimate
                    })
                current_pos = i
                break
    
    # Add final section
    if current_pos < len(full_text.split('\n')):
        sections.append({
            'start': current_pos,
            'end': len(full_text.split('\n')),
            'title': 'Final Section',
            'estimated_chars': (len(full_text.split('\n')) - current_pos) * 50
        })
    
    return sections

def create_split_strategy():
    """Create strategy for splitting large documents"""
    
    large_docs = identify_large_documents()
    
    print("LARGE DOCUMENT SPLITTING ANALYSIS")
    print("=" * 50)
    
    split_candidates = []
    
    for pdf_name, char_count, full_text in large_docs:
        print(f"\nDOC: {pdf_name}")
        print(f"   Size: {char_count:,} characters")
        
        # Analyze sections
        sections = analyze_document_sections(full_text, pdf_name)
        
        if len(sections) > 1:
            print(f"   Found {len(sections)} natural sections:")
            for i, section in enumerate(sections[:5]):  # Show first 5
                print(f"     {i+1}. {section['title'][:50]}... (~{section['estimated_chars']:,} chars)")
            
            if len(sections) > 5:
                print(f"     ... and {len(sections) - 5} more sections")
            
            split_candidates.append({
                'pdf_name': pdf_name,
                'char_count': char_count,
                'sections': len(sections),
                'can_split': len(sections) > 2,
                'recommended_splits': min(len(sections), 4)  # Max 4 splits
            })
        else:
            print(f"   No clear section breaks found - difficult to split")
            split_candidates.append({
                'pdf_name': pdf_name,
                'char_count': char_count,
                'sections': 0,
                'can_split': False,
                'recommended_splits': 1
            })
    
    print(f"\nSUMMARY")
    print(f"   Documents >300k chars: {len(large_docs)}")
    splittable = [doc for doc in split_candidates if doc['can_split']]
    print(f"   Splittable documents: {len(splittable)}")
    
    total_reduction = 0
    for doc in splittable:
        reduction = doc['char_count'] / doc['recommended_splits']
        total_reduction += doc['char_count'] - reduction
        print(f"   REDUCE: {doc['pdf_name'][:50]}...")
        print(f"       {doc['char_count']:,} chars → ~{reduction:,.0f} chars per section")
    
    print(f"\nPROCESSING TIME IMPROVEMENT:")
    print(f"   Before: ~{sum(doc['char_count'] for doc in large_docs) / 50000 * 15:.0f} minutes")
    print(f"   After:  ~{(sum(doc['char_count'] for doc in large_docs) - total_reduction) / 50000 * 15:.0f} minutes")
    print(f"   Savings: ~{total_reduction / 50000 * 15:.0f} minutes")
    
    return split_candidates

if __name__ == "__main__":
    create_split_strategy()