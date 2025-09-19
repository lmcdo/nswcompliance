#!/usr/bin/env python3
"""
Exact reproduction of the migration logic that was causing '0' errors
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

def exact_migration_reproduction():
    """Reproduce the exact migration logic"""
    
    print("EXACT MIGRATION REPRODUCTION")
    print("=" * 40)
    
    conn = psycopg2.connect(
        host="localhost", 
        database="nsw_planning",
        user="postgres",
        password="postgres"
    )
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Use the EXACT query from the original migration
        cur.execute("""
            SELECT 
                rp.*,
                qs.numeric_value,
                qs.unit,
                qs.context as measurement_context,
                qs.confidence_score
            FROM public.regulatory_provisions rp
            LEFT JOIN public.quantitative_standards qs ON rp.id = qs.provision_id
            WHERE rp.zone IS NOT NULL
            ORDER BY rp.id
            LIMIT 5
        """)
        
        provisions = cur.fetchall()
        
        for prov in provisions:
            print(f"\n--- PROVISION {prov['id']} ---")
            
            try:
                # EXACT logic from authoritative_migration_fixed.py
                
                # Step 1: Determine authority level
                authority_level = 3
                doc_type = "DCP"
                
                # Step 2: Create JSON - this was the problematic part
                original_json = {
                    'original_provision_id': prov['id'],
                    'document_id': prov.get('document_id'),
                    'ref_number': prov.get('ref_number'),
                    'domain_classification': prov.get('domain_classification'),
                    'classification_confidence': float(prov.get('classification_confidence') or 0.85),
                    'extraction_metadata': {
                        'method': 'zone_mapped_migration',
                        'migration_timestamp': datetime.now().isoformat(),
                        'original_created_at': prov.get('created_at').isoformat() if prov.get('created_at') else None
                    }
                }
                
                # Step 3: Zone processing
                applicable_zones = [prov['zone']] if prov['zone'] else []
                
                # Step 4: Insert preparation - this is where it was failing
                params = (
                    doc_type,
                    f"Document_{prov.get('document_id', 'unknown')}",
                    prov.get('ref_number') or f"ref_{prov['id']}",
                    authority_level,
                    prov.get('provision_text', ''),
                    (prov.get('provision_type') or 'general')[:50],
                    applicable_zones,
                    prov.get('numeric_value'),
                    prov.get('unit'),
                    (prov.get('measurement_context') or '')[:100],
                    json.dumps(original_json),
                    'zone_mapped_migration',
                    float(prov.get('confidence_score') or 0.85),  # This line was problematic
                    datetime.now()
                )
                
                print(f"SUCCESS: All steps completed for provision {prov['id']}")
                
            except Exception as e:
                print(f"Error migrating provision {prov['id']}: {e}")
                
                # This is the EXACT error logging from the original
                error_msg = str(e)
                print(f"Error string: '{error_msg}'")
                print(f"Error length: {len(error_msg)}")
                print(f"Error repr: {repr(error_msg)}")
                
                # Check if this somehow becomes "0"
                if error_msg == "0":
                    print("FOUND IT! The error string is literally '0'")
                    
                    # Investigate further
                    print(f"Exception type: {type(e)}")
                    print(f"Exception args: {e.args}")
                    
                    # Test if it's a specific type of error
                    import traceback
                    traceback.print_exc()
                    
                elif len(error_msg) == 1 and error_msg.isdigit():
                    print(f"SUSPICIOUS: Single digit error '{error_msg}'")
                elif not error_msg:
                    print("EMPTY ERROR STRING!")
                else:
                    print("Normal error message")
                    
                # Continue to next provision
                continue
    
    conn.close()

if __name__ == "__main__":
    exact_migration_reproduction()