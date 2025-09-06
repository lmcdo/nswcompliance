#!/usr/bin/env python3
import sqlite3
from datetime import datetime

def check_actual_progress():
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    
    # Get all original PDF documents
    cursor.execute("SELECT pdf_name FROM documents ORDER BY pdf_name")
    all_pdfs = [r[0] for r in cursor.fetchall()]
    
    # Get unique processed document IDs (simplified)
    cursor.execute("SELECT DISTINCT document_id FROM regulatory_refs")
    processed_ids = [r[0] for r in cursor.fetchall()]
    
    # Map processed IDs back to PDF names
    processed_pdfs = set()
    for pdf in all_pdfs:
        pdf_clean = pdf.replace('.pdf', '').replace(' ', '_').replace('-', '_')
        for proc_id in processed_ids:
            if pdf_clean in proc_id or proc_id.startswith(pdf_clean):
                processed_pdfs.add(pdf)
                break
    
    remaining_pdfs = [pdf for pdf in all_pdfs if pdf not in processed_pdfs]
    
    # Total entries
    cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
    total_refs = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"ACTUAL PROCESSING STATUS - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    print(f"Total PDF documents: {len(all_pdfs)}")
    print(f"Documents processed: {len(processed_pdfs)}")
    print(f"Documents remaining: {len(remaining_pdfs)}")
    print(f"Total regulatory entries: {total_refs:,}")
    print(f"Completion rate: {len(processed_pdfs)/len(all_pdfs)*100:.1f}%")
    
    if remaining_pdfs:
        print(f"\nRemaining documents ({len(remaining_pdfs)}):")
        for i, pdf in enumerate(sorted(remaining_pdfs)[:10], 1):
            print(f"  {i:2}. {pdf}")
        if len(remaining_pdfs) > 10:
            print(f"  ... and {len(remaining_pdfs) - 10} more")

if __name__ == "__main__":
    check_actual_progress()