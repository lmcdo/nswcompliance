#!/usr/bin/env python3
"""
CHUNK 2 Comprehensive Verification
Tests all migration requirements as per PRP-8B specification
"""
import psycopg2
import json
from datetime import datetime

def verify_chunk2_completion():
    conn = psycopg2.connect(host='localhost', database='nsw_planning', user='postgres', password='postgres')
    cur = conn.cursor()
    
    tests = []
    
    print('CHUNK 2 VERIFICATION RESULTS:')
    print('=' * 60)
    
    # Test 1: Data migrated
    cur.execute("SELECT COUNT(*) FROM public.regulatory_provisions WHERE zone IS NOT NULL")
    source_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM authoritative.planning_provisions")
    target_count = cur.fetchone()[0]
    
    migration_rate = target_count / source_count if source_count > 0 else 0
    passed = migration_rate >= 0.8
    tests.append(('Data migrated', passed, f'{migration_rate:.1%} migration rate'))
    print(f'{"PASS" if passed else "FAIL":4} | {"Data migrated":<25} | {migration_rate:.1%} migration rate')
    
    # Test 2: Authority tiers created
    cur.execute("SELECT COUNT(*) FROM authoritative.provision_authority_tiers")
    tier_count = cur.fetchone()[0]
    passed = tier_count > 100
    tests.append(('Authority tiers', passed, f'{tier_count} tiers created'))
    print(f'{"PASS" if passed else "FAIL":4} | {"Authority tiers":<25} | {tier_count} tiers created')
    
    # Test 3: Authority level distribution
    cur.execute("""
        SELECT document_type, COUNT(*) 
        FROM authoritative.planning_provisions 
        GROUP BY document_type 
        ORDER BY document_type
    """)
    
    distribution = dict(cur.fetchall())
    
    # Check reasonable distribution
    sepp_count = distribution.get('SEPP', 0)
    lep_count = distribution.get('LEP', 0)  
    dcp_count = distribution.get('DCP', 0)
    
    passed = 5 <= sepp_count <= 50
    tests.append(('SEPP provisions', passed, f'{sepp_count} SEPP provisions'))
    print(f'{"PASS" if passed else "FAIL":4} | {"SEPP provisions":<25} | {sepp_count} SEPP provisions')
    
    passed = 10 <= lep_count <= 200
    tests.append(('LEP provisions', passed, f'{lep_count} LEP provisions'))
    print(f'{"PASS" if passed else "FAIL":4} | {"LEP provisions":<25} | {lep_count} LEP provisions')
    
    passed = dcp_count > 0
    tests.append(('DCP provisions', passed, f'{dcp_count} DCP provisions'))
    print(f'{"PASS" if passed else "FAIL":4} | {"DCP provisions":<25} | {dcp_count} DCP provisions')
    
    # Test 4: Original JSON preserved
    cur.execute("SELECT COUNT(*) FROM authoritative.planning_provisions WHERE original_json IS NOT NULL")
    json_count = cur.fetchone()[0]
    passed = json_count > 0
    tests.append(('JSON preservation', passed, f'{json_count} provisions with JSON'))
    print(f'{"PASS" if passed else "FAIL":4} | {"JSON preservation":<25} | {json_count} provisions with JSON')
    
    # Test 5: Tier confidence levels
    cur.execute("""
        SELECT tier_level, AVG(confidence_level), COUNT(*)
        FROM authoritative.provision_authority_tiers 
        GROUP BY tier_level 
        ORDER BY tier_level
    """)
    
    tier_confidence = cur.fetchall()
    for tier, avg_confidence, count in tier_confidence:
        expected_confidence = {1: 0.95, 2: 0.85, 3: 0.70, 4: 0.60, 5: 0.30}.get(tier, 0.50)
        passed = avg_confidence >= expected_confidence - 0.1
        tests.append((f'Tier {tier} confidence', passed, f'Avg confidence: {avg_confidence:.2f}'))
        print(f'{"PASS" if passed else "FAIL":4} | {f"Tier {tier} confidence":<25} | Avg confidence: {avg_confidence:.2f}')
    
    print('=' * 60)
    print(f'SOURCE DATA: {source_count} provisions')
    print(f'MIGRATED: {target_count} provisions ({migration_rate:.1%})')
    print(f'AUTHORITY DISTRIBUTION: {distribution}')
    
    # Show tier distribution
    cur.execute("""
        SELECT tier_level, COUNT(*) 
        FROM authoritative.provision_authority_tiers 
        GROUP BY tier_level 
        ORDER BY tier_level
    """)
    tier_distribution = dict(cur.fetchall())
    print(f'TIER DISTRIBUTION: {tier_distribution}')
    print('=' * 60)
    
    all_passed = all(test[1] for test in tests)
    
    if all_passed:
        print('✅ ALL TESTS PASSED - CHUNK 2 COMPLETE')
        
        # Create completion marker
        with open('prp_checkpoints/CHUNK_2_MIGRATION_COMPLETE.marker', 'w') as f:
            json.dump({
                'chunk': 'PRP-8B-CHUNK-2',
                'completed_at': datetime.now().isoformat(),
                'provisions_migrated': target_count,
                'migration_rate': f'{migration_rate:.1%}',
                'authority_distribution': distribution,
                'tier_distribution': tier_distribution,
                'verification_passed': True,
                'next_chunk': 'CHUNK_3_HIERARCHY_API'
            }, f, indent=2)
            
        print('📄 Completion marker created: CHUNK_2_MIGRATION_COMPLETE.marker')
        
    else:
        print('❌ VERIFICATION FAILED - INVESTIGATE AND ROLLBACK')
    
    conn.close()
    return all_passed

if __name__ == "__main__":
    success = verify_chunk2_completion()
    exit(0 if success else 1)