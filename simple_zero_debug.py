#!/usr/bin/env python3
"""
Simple test to identify the exact source of '0' errors
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import traceback

def test_zero_error_reproduction():
    """Test to reproduce the exact '0' error condition"""
    
    print("ZERO ERROR REPRODUCTION TEST")
    print("=" * 40)
    
    conn = psycopg2.connect(
        host="localhost",
        database="nsw_planning",
        user="postgres", 
        password="postgres"
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get the exact provision that was failing
    cur.execute("SELECT * FROM regulatory_provisions WHERE id = 7")
    prov = cur.fetchone()
    
    print(f"Provision 7 data:")
    print(f"  classification_confidence: {repr(prov.get('classification_confidence'))}")
    print(f"  Type: {type(prov.get('classification_confidence'))}")
    
    # Test the exact failing code path
    try:
        # This is the line from the original migration that was failing
        confidence = float(prov.get('classification_confidence') or 0.85)
        print(f"SUCCESS: confidence = {confidence}")
        
    except Exception as e:
        print(f"EXCEPTION: {e}")
        print(f"Exception type: {type(e)}")
        print(f"str(e): '{str(e)}'")
        
        # Test if this creates the "0" 
        error_str = str(e)
        print(f"Error string length: {len(error_str)}")
        print(f"Error string repr: {repr(error_str)}")
        
        # Check if this is somehow becoming "0"
        if error_str == "0":
            print("FOUND IT: Exception str() equals '0'")
        elif "0" in error_str:
            print(f"FOUND RELATED: Exception contains '0': {error_str}")
        else:
            print("NOT THE SOURCE: Exception doesn't contain '0'")
    
    # Test other potential sources
    print(f"\nTesting other fields...")
    
    try:
        numeric_val = prov.get('numeric_value') 
        if numeric_val is not None:
            float(numeric_val)
        print(f"numeric_value OK: {numeric_val}")
    except Exception as e:
        print(f"numeric_value ERROR: {e} -> str: '{str(e)}'")
    
    # Test the specific join that was used in migration
    print(f"\nTesting the JOIN query...")
    try:
        cur.execute("""
            SELECT 
                rp.*,
                qs.numeric_value,
                qs.unit,
                qs.context as measurement_context,
                qs.confidence_score
            FROM regulatory_provisions rp
            LEFT JOIN quantitative_standards qs ON rp.id = qs.provision_id
            WHERE rp.id = 7
        """)
        joined_prov = cur.fetchone()
        
        print(f"Joined data confidence_score: {repr(joined_prov.get('confidence_score'))}")
        
        # Test the confidence_score from quantitative_standards (this might be the issue!)
        try:
            qs_confidence = float(joined_prov.get('confidence_score') or 0.85) 
            print(f"QS confidence OK: {qs_confidence}")
        except Exception as e:
            print(f"QS confidence ERROR: {e} -> str: '{str(e)}'")
            if str(e) == "0":
                print("BINGO! quantitative_standards.confidence_score causes '0' error")
                
    except Exception as e:
        print(f"JOIN query failed: {e}")
    
    conn.close()

if __name__ == "__main__":
    test_zero_error_reproduction()