#!/usr/bin/env python3
"""
Simple analysis of clause text content and linking for Referenced Legislation accordion
"""
import sqlite3
from database_setback_calculator import DatabaseSetbackCalculator

def main():
    print("NSW PLANNING COMPLIANCE ENGINE")
    print("Clause Text Pipeline Analysis for Referenced Legislation Accordion\n")
    
    conn = sqlite3.connect('nsw_planning.db')
    cur = conn.cursor()
    
    # 1. Database Schema Analysis
    print("=== 1. DATABASE SCHEMA ANALYSIS ===\n")
    
    # Check regulatory_provisions structure
    cur.execute("PRAGMA table_info(regulatory_provisions)")
    columns = cur.fetchall()
    print("REGULATORY_PROVISIONS table columns:")
    for col in columns:
        print(f"  {col[1]:<25} {col[2]:<15}")
    
    # Basic stats
    cur.execute("SELECT COUNT(*) FROM regulatory_provisions")
    total_provisions = cur.fetchone()[0]
    print(f"\nTotal regulatory provisions: {total_provisions:,}")
    
    cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE provision_text IS NOT NULL AND LENGTH(provision_text) > 50")
    with_text = cur.fetchone()[0]
    print(f"Provisions with substantial text (>50 chars): {with_text:,}")
    
    # 2. Setback Controls Analysis
    print("\n=== 2. SETBACK CONTROLS ANALYSIS ===\n")
    
    cur.execute("SELECT COUNT(*) FROM development_controls WHERE control_type = 'setback'")
    setback_controls = cur.fetchone()[0]
    print(f"Total setback controls: {setback_controls}")
    
    cur.execute("""
    SELECT COUNT(*) FROM development_controls dc
    JOIN regulatory_provisions rp ON dc.provision_id = rp.id
    WHERE dc.control_type = 'setback'
    """)
    linked_setbacks = cur.fetchone()[0]
    print(f"Setback controls linked to provisions: {linked_setbacks}")
    
    # Sample setback controls with provision text
    print("\n=== SAMPLE SETBACK CONTROLS WITH CLAUSE TEXT ===")
    cur.execute("""
    SELECT dc.control_subtype, dc.value_numeric, rp.ref_number, 
           SUBSTR(rp.provision_text, 1, 150) as text_preview
    FROM development_controls dc
    JOIN regulatory_provisions rp ON dc.provision_id = rp.id
    WHERE dc.control_type = 'setback' 
      AND rp.provision_text IS NOT NULL
      AND LENGTH(rp.provision_text) > 50
    LIMIT 5
    """)
    
    for row in cur.fetchall():
        print(f"Control: {row[0]} - {row[1]}m")
        print(f"  Clause: {row[2]}")
        print(f"  Text: {row[3]}...")
        print("---")
    
    # 3. Current API Response Check
    print("\n=== 3. CURRENT API RESPONSE ===\n")
    
    # Test current setback calculator
    class MockProperty:
        def __init__(self):
            self.zone = 'R2'
            self.address = '34 Pile Street, Dulwich Hill'
    
    calc = DatabaseSetbackCalculator()
    property_data = MockProperty()
    setbacks = calc.get_setbacks_for_property(property_data)
    
    print("Current setback API returns:")
    for position, data in setbacks.items():
        print(f"\n{position.upper()}:")
        for key, value in data.items():
            print(f"  {key}: {value}")
    
    # Check if provision IDs are included
    has_provision_ids = any('provision_id' in str(data) for data in setbacks.values())
    has_clause_text = any('text' in data and len(str(data.get('text', ''))) > 50 for data in setbacks.values())
    
    print(f"\nAPI includes provision IDs: {'YES' if has_provision_ids else 'NO'}")
    print(f"API includes full clause text: {'YES' if has_clause_text else 'NO'}")
    
    # 4. Document Hierarchy Check
    print("\n=== 4. DOCUMENT HIERARCHY ===\n")
    
    cur.execute("""
    SELECT d.pdf_name, COUNT(*) as provision_count
    FROM regulatory_provisions rp
    JOIN documents d ON rp.document_id = d.id
    GROUP BY d.pdf_name
    ORDER BY provision_count DESC
    LIMIT 10
    """)
    
    print("Top documents by provision count:")
    sepp_count = lep_count = dcp_count = 0
    for row in cur.fetchall():
        doc_name = row[0]
        count = row[1]
        print(f"  {doc_name}: {count:,} provisions")
        
        if 'SEPP' in doc_name.upper():
            sepp_count += 1
        elif 'LEP' in doc_name.upper():
            lep_count += 1
        elif 'DCP' in doc_name.upper():
            dcp_count += 1
    
    print(f"\nDocument types found:")
    print(f"  SEPP documents: {sepp_count}")
    print(f"  LEP documents: {lep_count}")
    print(f"  DCP documents: {dcp_count}")
    
    # 5. Readiness Assessment
    print("\n=== 5. ACCORDION READINESS ASSESSMENT ===\n")
    
    requirements = {
        'Full clause text available': with_text > 100,
        'Setback controls linked to provisions': linked_setbacks > 10,
        'Provision reference numbers': False,
        'Document hierarchy (SEPP/LEP/DCP)': (sepp_count + lep_count + dcp_count) > 0,
        'Page references available': False
    }
    
    # Check reference numbers
    cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE ref_number IS NOT NULL AND ref_number != ''")
    ref_count = cur.fetchone()[0]
    requirements['Provision reference numbers'] = ref_count > 100
    
    # Check page numbers
    cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE page_number IS NOT NULL")
    page_count = cur.fetchone()[0]
    requirements['Page references available'] = page_count > 100
    
    print("Requirements checklist:")
    ready_count = 0
    for req, status in requirements.items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {req}")
        if status:
            ready_count += 1
    
    readiness_pct = (ready_count / len(requirements)) * 100
    print(f"\nOverall readiness: {ready_count}/{len(requirements)} ({readiness_pct:.1f}%)")
    
    # 6. Recommendations
    print("\n=== 6. RECOMMENDATIONS ===\n")
    
    if requirements['Setback controls linked to provisions'] and requirements['Full clause text available']:
        print("✅ READY FOR BASIC IMPLEMENTATION!")
        print("\nRecommended approach:")
        print("1. Modify database_setback_calculator.py to return provision_id in results")
        print("2. Create new API endpoint: /api/clause/{provision_id} to fetch full clause text")
        print("3. Add accordion component to frontend that calls clause API")
        print("4. Display clause text with reference number and page if available")
    else:
        print("⚠️ DATA GAPS NEED ADDRESSING:")
        if not requirements['Setback controls linked to provisions']:
            print("- Link more setback controls to regulatory provisions")
        if not requirements['Full clause text available']:
            print("- Ensure clause text extraction is complete")
    
    # Show what a typical API response could look like
    print("\n=== 7. ENHANCED API RESPONSE EXAMPLE ===\n")
    
    # Get a real example of linked data
    cur.execute("""
    SELECT dc.control_subtype, dc.value_numeric, dc.provision_id,
           rp.ref_number, rp.section_header, d.pdf_name
    FROM development_controls dc
    JOIN regulatory_provisions rp ON dc.provision_id = rp.id
    JOIN documents d ON rp.document_id = d.id
    WHERE dc.control_type = 'setback' AND rp.provision_text IS NOT NULL
    LIMIT 1
    """)
    
    example = cur.fetchone()
    if example:
        print("Enhanced setback response could include:")
        print(f"{{")
        print(f"  'front': {{")
        print(f"    'value': {example[1]},")
        print(f"    'source': '{example[5]}',")
        print(f"    'provision_id': {example[2]},")
        print(f"    'clause_reference': '{example[3]}',")
        print(f"    'section': '{example[4]}',")
        print(f"    'confidence': 'HIGH'")
        print(f"  }}")
        print(f"}}")
    
    conn.close()

if __name__ == "__main__":
    main()