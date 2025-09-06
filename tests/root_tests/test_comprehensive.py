#!/usr/bin/env python3
"""
Test Comprehensive Extraction
=============================
"""

from comprehensive_extraction_pipeline import ComprehensiveExtractionPipeline
import sqlite3

def test_comprehensive():
    """Test comprehensive extraction on one document"""
    
    print("TESTING COMPREHENSIVE EXTRACTION")
    print("=" * 50)
    
    # Get a document with good content
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, pdf_name, full_text, char_count 
        FROM documents 
        WHERE char_count BETWEEN 15000 AND 50000
        AND (full_text LIKE '%zone%' OR full_text LIKE '%setback%' OR full_text LIKE '%SEPP%')
        LIMIT 1
    """)
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        print("No suitable test document found")
        return False
    
    doc_id, pdf_name, full_text, char_count = result
    
    print(f"Test document: {pdf_name}")
    print(f"Size: {char_count:,} characters")
    print()
    
    try:
        pipeline = ComprehensiveExtractionPipeline()
        
        # Extract with comprehensive method
        print("Running comprehensive extraction...")
        extraction_results = pipeline.extract_from_document(doc_id, pdf_name, full_text)
        
        # Show results
        entities = extraction_results['entities']
        relationships = extraction_results['relationships']
        provisions = extraction_results['provisions']
        
        print(f"\nRESULTS:")
        print(f"Entities: {len(entities)}")
        print(f"Relationships: {len(relationships)}")
        print(f"Provisions: {len(provisions)}")
        
        if entities:
            print(f"\nSample entities:")
            for i, entity in enumerate(entities[:10]):
                verified = "[OK]" if entity.get('verified') else "[?]"
                print(f"  {i+1}. [{entity.get('type', 'unknown')}] {entity.get('reference', 'N/A')} {verified}")
                if entity.get('category'):
                    print(f"      Category: {entity.get('category')}")
                print(f"      Text: {entity.get('text', '')[:60]}...")
        
        if relationships:
            print(f"\nSample relationships:")
            for i, rel in enumerate(relationships[:5]):
                print(f"  {i+1}. {rel.get('source')} --{rel.get('type')}--> {rel.get('target')}")
        
        if provisions:
            print(f"\nSample provisions:")
            for i, prov in enumerate(provisions[:5]):
                print(f"  {i+1}. [{prov.get('type')}] {prov.get('entity', 'N/A')}")
                if prov.get('measurement'):
                    print(f"      Measurement: {prov.get('measurement')}")
        
        # Compare to basic extraction
        expected_improvement = len(entities) > 10  # Should get much more than basic extraction
        
        print(f"\nASSESSMENT:")
        if expected_improvement:
            print("[SUCCESS] Comprehensive extraction working - significant increase in entities")
            return True
        else:
            print("[WARNING] May need to adjust extraction prompts")
            return False
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_comprehensive()
    if success:
        print("\n[SUCCESS] Ready for full comprehensive pipeline")
    else:
        print("\n[FAILED] Need to adjust comprehensive extraction")