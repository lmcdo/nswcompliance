#!/usr/bin/env python3
"""
Debug the exact source of the '0' error by testing specific provisions
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime
import traceback

def test_single_provision_migration():
    """Test migration of a single provision with full debugging"""
    
    print("DEBUGGING ZERO ERROR SOURCE")
    print("=" * 50)
    
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="nsw_planning",
            user="postgres",
            password="postgres"
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get first provision with zone for testing
        cur.execute("""
            SELECT 
                rp.*,
                qs.numeric_value,
                qs.unit,
                qs.context as measurement_context,
                qs.confidence_score
            FROM regulatory_provisions rp
            LEFT JOIN quantitative_standards qs ON rp.id = qs.provision_id
            WHERE rp.zone IS NOT NULL
            ORDER BY rp.id
            LIMIT 1
        """)
        
        provision = cur.fetchone()
        
        if not provision:
            print("No provisions with zones found!")
            return False
            
        print(f"Testing provision ID: {provision['id']}")
        print(f"Zone: {provision['zone']}")
        print(f"Provision type: {provision['provision_type']}")
        
        # Test each step of migration logic
        print("\n--- TESTING MIGRATION STEPS ---")
        
        # Step 1: Document type determination
        try:
            doc_id = str(provision.get('document_id', ''))
            ref_num = str(provision.get('ref_number', ''))
            section = str(provision.get('section_header', ''))
            
            authority_level = 3  # Default to DCP
            doc_type = "DCP"
            
            # Test SEPP detection
            if any(keyword in (doc_id + ref_num + section).lower() for keyword in [
                'sepp', 'state environmental planning policy', 'environmental planning policy'
            ]):
                authority_level = 1
                doc_type = "SEPP"
            elif any(keyword in (doc_id + ref_num + section).lower() for keyword in [
                'lep', 'local environmental plan', 'environmental plan'
            ]):
                authority_level = 2
                doc_type = "LEP"
                
            print(f"✓ Authority level: {authority_level} ({doc_type})")
            
        except Exception as e:
            print(f"✗ Authority level determination failed: {e}")
            print(f"  Exception type: {type(e)}")
            print(f"  str(e): '{str(e)}'")
            if str(e) == "0":
                print("  🚨 FOUND THE '0' ERROR SOURCE!")
            return False
        
        # Step 2: JSON creation
        try:
            original_json = {
                'original_provision_id': provision['id'],
                'document_id': provision.get('document_id'),
                'ref_number': provision.get('ref_number'),
                'domain_classification': provision.get('domain_classification'),
                'classification_confidence': provision.get('classification_confidence'),
                'extraction_metadata': {
                    'method': 'zone_mapped_migration',
                    'migration_timestamp': datetime.now().isoformat(),
                    'original_created_at': provision.get('created_at').isoformat() if provision.get('created_at') else None
                }
            }
            
            # Test JSON serialization
            json_str = json.dumps(original_json)
            print(f"✓ JSON serialization successful ({len(json_str)} chars)")
            
        except Exception as e:
            print(f"✗ JSON creation failed: {e}")
            print(f"  Exception type: {type(e)}")  
            print(f"  str(e): '{str(e)}'")
            if str(e) == "0":
                print("  🚨 FOUND THE '0' ERROR SOURCE!")
            return False
        
        # Step 3: Field preparation
        try:
            applicable_zones = [provision['zone']] if provision['zone'] else []
            
            # Test each field conversion
            clause_ref = provision.get('ref_number') or f"ref_{provision['id']}"
            prov_text = provision.get('provision_text', '')
            prov_type = (provision.get('provision_type') or 'general')[:50]
            numeric_val = provision.get('numeric_value')
            unit_val = provision.get('unit')
            context_val = (provision.get('measurement_context') or '')[:100]
            confidence_val = float(provision.get('confidence_score') or 0.85)
            
            print(f"✓ Field preparation successful")
            print(f"  Clause ref: {clause_ref}")
            print(f"  Prov type: {prov_type}")
            print(f"  Zones: {applicable_zones}")
            print(f"  Confidence: {confidence_val}")
            
        except Exception as e:
            print(f"✗ Field preparation failed: {e}")
            print(f"  Exception type: {type(e)}")
            print(f"  str(e): '{str(e)}'")
            if str(e) == "0":
                print("  🚨 FOUND THE '0' ERROR SOURCE!")
                
                # Detailed investigation of which field caused the issue
                print("  🔍 Investigating specific field...")
                
                try:
                    test_confidence = float(provision.get('confidence_score') or 0.85)
                    print(f"    confidence_score OK: {test_confidence}")
                except Exception as conf_e:
                    print(f"    🚨 confidence_score FAILED: {conf_e}")
                
                try:
                    test_numeric = provision.get('numeric_value')
                    if test_numeric is not None:
                        float(test_numeric)
                    print(f"    numeric_value OK: {test_numeric}")
                except Exception as num_e:
                    print(f"    🚨 numeric_value FAILED: {num_e}")
            
            return False
        
        # Step 4: Database insertion test (dry run)
        try:
            print("\n--- TESTING DATABASE INSERTION (DRY RUN) ---")
            
            # Test the INSERT statement without actually executing
            insert_sql = """
                INSERT INTO authoritative.planning_provisions (
                    document_type,
                    document_name,
                    clause_reference,
                    authority_level,
                    provision_text,
                    provision_type,
                    applicable_zones,
                    numeric_value,
                    unit,
                    measurement_context,
                    original_json,
                    extraction_method,
                    extraction_confidence,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                doc_type,
                f"Document_{provision.get('document_id', 'unknown')}",
                clause_ref,
                authority_level,
                prov_text,
                prov_type,
                applicable_zones,
                numeric_val,
                unit_val,
                context_val,
                json_str,
                'zone_mapped_migration',
                confidence_val,
                datetime.now()
            )
            
            # Test parameter serialization
            print(f"✓ Parameters prepared for insertion")
            print(f"  Document type: {doc_type}")
            print(f"  Authority level: {authority_level}")
            print(f"  Zones array: {applicable_zones}")
            
            # Actually try the insertion in a transaction that we'll rollback
            cur.execute("BEGIN")
            cur.execute(insert_sql, params)
            cur.execute("ROLLBACK")  # Don't actually insert
            
            print(f"✓ Database insertion test successful (rolled back)")
            
        except Exception as e:
            print(f"✗ Database insertion failed: {e}")
            print(f"  Exception type: {type(e)}")
            print(f"  str(e): '{str(e)}'")
            if str(e) == "0":
                print("  🚨 FOUND THE '0' ERROR SOURCE!")
                
            # Try to rollback the transaction
            try:
                cur.execute("ROLLBACK")
            except:
                pass
                
            return False
        
        conn.close()
        print(f"\n✅ MIGRATION TEST COMPLETED SUCCESSFULLY")
        print(f"   No '0' error found with provision {provision['id']}")
        return True
        
    except Exception as e:
        print(f"FATAL ERROR in migration test: {e}")
        print(f"Exception type: {type(e)}")
        print(f"str(e): '{str(e)}'")
        if str(e) == "0":
            print("🚨 FOUND THE '0' ERROR SOURCE AT TOP LEVEL!")
        traceback.print_exc()
        return False

def test_problematic_provisions():
    """Test the specific provisions that were failing with '0' errors"""
    
    print("\n" + "=" * 50)
    print("TESTING KNOWN PROBLEMATIC PROVISIONS")
    print("=" * 50)
    
    # Test the specific provision IDs that were showing "Error migrating provision X: 0"
    problem_ids = [7, 8, 9, 10, 11, 12, 33, 34, 35]
    
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="nsw_planning", 
            user="postgres",
            password="postgres"
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        for prov_id in problem_ids:
            print(f"\n--- TESTING PROVISION {prov_id} ---")
            
            cur.execute("SELECT * FROM regulatory_provisions WHERE id = %s", (prov_id,))
            prov = cur.fetchone()
            
            if not prov:
                print(f"Provision {prov_id} not found!")
                continue
            
            print(f"Zone: {prov.get('zone')}")
            print(f"Type: {prov.get('provision_type')}")
            print(f"Confidence: {prov.get('classification_confidence')}")
            
            # Test the specific problematic conversion
            try:
                conf_val = prov.get('classification_confidence')
                print(f"Raw confidence value: {repr(conf_val)} (type: {type(conf_val)})")
                
                # This is the line that was causing issues
                result = float(conf_val or 0.85)
                print(f"✓ float() conversion OK: {result}")
                
            except Exception as e:
                print(f"✗ float() conversion FAILED: {e}")
                print(f"  Exception type: {type(e)}")
                print(f"  str(e): '{str(e)}'")
                
                if str(e) == "0":
                    print(f"  🚨 FOUND IT! Provision {prov_id} causes the '0' error")
                    print(f"  Raw value: {repr(conf_val)}")
                    return prov_id
        
        conn.close()
        return None
        
    except Exception as e:
        print(f"ERROR testing problematic provisions: {e}")
        traceback.print_exc()
        return None

def main():
    """Main debugging execution"""
    
    print("ZERO ERROR SOURCE DEBUGGING")
    print("Looking for the exact cause of 'Error migrating provision X: 0'")
    
    # Test 1: Single provision migration
    success = test_single_provision_migration()
    
    if not success:
        print("❌ Single provision test failed - but may not be the '0' error")
    
    # Test 2: Known problematic provisions
    problem_id = test_problematic_provisions()
    
    if problem_id:
        print(f"\n🎯 ROOT CAUSE IDENTIFIED:")
        print(f"   Provision ID {problem_id} contains data that causes the '0' error")
        print(f"   This is likely due to unexpected data type in classification_confidence")
        return True
    else:
        print(f"\n❓ '0' error source not identified in tested provisions")
        print(f"   May require testing more provisions or different migration conditions")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)