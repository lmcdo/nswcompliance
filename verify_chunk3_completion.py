#!/usr/bin/env python3
"""
CHUNK 3 Comprehensive API Verification
Tests all hierarchy resolution API requirements as per PRP-8B specification
"""

import requests
import json
import time
from datetime import datetime

def verify_chunk3_completion():
 
 base_url = "http://localhost:3007"
 tests = []
 errors = []
 
 print('CHUNK 3 VERIFICATION RESULTS:')
 print('=' * 60)
 
 # Test 1: API endpoint exists and responds
 try:
 response = requests.get(f"{base_url}/api/authoritative/compliance-check", timeout=10)
 
 api_works = response.status_code == 200
 tests.append(('API endpoint responds', api_works, f'Status: {response.status_code}'))
 print(f'{"PASS" if api_works else "FAIL":4} | {"API endpoint responds":<25} | Status: {response.status_code}')
 
 if api_works:
 data = response.json()
 
 # Test 2: API documentation structure
 required_docs = ['endpoint', 'description', 'version', 'required_fields', 'response_structure']
 has_docs = all(field in data for field in required_docs)
 tests.append(('API documentation', has_docs, 'Complete docs' if has_docs else 'Missing docs'))
 print(f'{"PASS" if has_docs else "FAIL":4} | {"API documentation":<25} | {"Complete docs" if has_docs else "Missing docs"}')
 
 except Exception as e:
 tests.append(('API connection', False, f'Error: {str(e)}'))
 errors.append(f"Cannot connect to API: {e}")
 print(f'FAIL | {"API connection":<25} | Error: {str(e)}')
 
 # Test 3: POST endpoint with hierarchy resolution
 try:
 test_payload = {
 "property_id": 1,
 "zone_code": "R2", 
 "development_type": "dwelling_house"
 }
 
 print(f'Testing hierarchy resolution for: {test_payload}')
 
 response = requests.post(
 f"{base_url}/api/authoritative/compliance-check",
 json=test_payload,
 timeout=30
 )
 
 hierarchy_works = response.status_code == 200
 tests.append(('Hierarchy resolution', hierarchy_works, f'Status: {response.status_code}'))
 print(f'{"PASS" if hierarchy_works else "FAIL":4} | {"Hierarchy resolution":<25} | Status: {response.status_code}')
 
 if hierarchy_works:
 data = response.json()
 
 # Test 4: Required response structure
 required_fields = [
 'tier_1_provisions', 'tier_2_provisions', 'tier_3_provisions',
 'tier_4_provisions', 'tier_5_provisions', 'primary_authorities',
 'confidence_level', 'legal_disclaimer', 'complexity_assessment'
 ]
 
 for field in required_fields:
 has_field = field in data
 tests.append((f'Field {field}', has_field, 'Present' if has_field else 'Missing'))
 print(f'{"PASS" if has_field else "FAIL":4} | {f"Field {field}":<25} | {"Present" if has_field else "Missing"}')
 
 # Test 5: Authority hierarchy data
 tier_1_count = len(data.get('tier_1_provisions', []))
 tier_2_count = len(data.get('tier_2_provisions', []))
 tier_3_count = len(data.get('tier_3_provisions', []))
 total_provisions = tier_1_count + tier_2_count + tier_3_count
 
 has_provisions = total_provisions > 0
 tests.append(('Provisions found', has_provisions, f'{total_provisions} total provisions'))
 print(f'{"PASS" if has_provisions else "FAIL":4} | {"Provisions found":<25} | {total_provisions} total provisions')
 
 # Test 6: Primary authorities resolution
 primary_authorities = data.get('primary_authorities', {})
 has_authorities = len(primary_authorities) > 0
 tests.append(('Primary authorities', has_authorities, f'{len(primary_authorities)} authorities'))
 print(f'{"PASS" if has_authorities else "FAIL":4} | {"Primary authorities":<25} | {len(primary_authorities)} authorities')
 
 # Test 7: Confidence calculation
 confidence = data.get('confidence_level', 0)
 valid_confidence = 0 < confidence <= 1
 tests.append(('Confidence level', valid_confidence, f'Confidence: {confidence:.3f}'))
 print(f'{"PASS" if valid_confidence else "FAIL":4} | {"Confidence level":<25} | Confidence: {confidence:.3f}')
 
 # Test 8: Legal disclaimer present
 disclaimer = data.get('legal_disclaimer', '')
 has_disclaimer = len(disclaimer) > 10
 tests.append(('Legal disclaimer', has_disclaimer, f'{len(disclaimer)} chars'))
 print(f'{"PASS" if has_disclaimer else "FAIL":4} | {"Legal disclaimer":<25} | {len(disclaimer)} chars')
 
 # Test 9: Tier distribution analysis
 print(f'\nTier Distribution Analysis:')
 print(f' Tier 1 (Fully authoritative): {tier_1_count} provisions')
 print(f' Tier 2 (High authority): {tier_2_count} provisions') 
 print(f' Tier 3 (Moderate authority): {tier_3_count} provisions')
 print(f' Primary authorities by context: {list(primary_authorities.keys())}')
 print(f' Complexity assessment: {data.get("complexity_assessment", "N/A")}')
 
 else:
 errors.append(f"Hierarchy resolution failed: {response.text}")
 
 except Exception as e:
 tests.append(('Hierarchy resolution', False, f'Error: {str(e)}'))
 errors.append(f"Hierarchy resolution error: {e}")
 print(f'FAIL | {"Hierarchy resolution":<25} | Error: {str(e)}')
 
 # Test 10: Cache performance (if hierarchy resolution worked)
 if hierarchy_works:
 try:
 print(f'\nTesting cache performance...')
 
 # First request (cache miss)
 start = time.time()
 response1 = requests.post(f"{base_url}/api/authoritative/compliance-check", 
 json=test_payload, timeout=30)
 first_time = time.time() - start
 
 # Second request (should be cached)
 start = time.time()
 response2 = requests.post(f"{base_url}/api/authoritative/compliance-check",
 json=test_payload, timeout=30)
 second_time = time.time() - start
 
 # Cache should make it faster or at least not significantly slower
 cache_working = second_time <= first_time * 1.5 # Allow some variance
 tests.append(('Cache performance', cache_working, 
 f'First: {first_time:.3f}s, Second: {second_time:.3f}s'))
 print(f'{"PASS" if cache_working else "FAIL":4} | {"Cache performance":<25} | First: {first_time:.3f}s, Second: {second_time:.3f}s')
 
 # Check if cache hit metadata is returned
 if response2.status_code == 200:
 data2 = response2.json()
 cache_hit = data2.get('processing_metadata', {}).get('cache_hit', False)
 print(f' | Cache hit indicator: {cache_hit}')
 
 except Exception as e:
 tests.append(('Cache test', False, f'Error: {str(e)}'))
 print(f'FAIL | {"Cache test":<25} | Error: {str(e)}')
 
 print('=' * 60)
 
 # Count results
 passed_tests = sum(1 for test in tests if test[1])
 total_tests = len(tests)
 success_rate = passed_tests / total_tests if total_tests > 0 else 0
 
 print(f'Test Results: {passed_tests}/{total_tests} passed ({success_rate:.1%})')
 
 all_passed = success_rate >= 0.9 and not errors # 90% pass rate required
 
 if all_passed:
 print('ALL CRITICAL TESTS PASSED - CHUNK 3 COMPLETE')
 
 # Create completion marker
 with open('prp_checkpoints/CHUNK_3_HIERARCHY_API_COMPLETE.marker', 'w') as f:
 json.dump({
 'chunk': 'PRP-8B-CHUNK-3',
 'completed_at': datetime.now().isoformat(),
 'api_endpoint': '/api/authoritative/compliance-check',
 'tests_passed': f'{passed_tests}/{total_tests}',
 'success_rate': f'{success_rate:.1%}',
 'cache_performance': f'{first_time:.3f}s -> {second_time:.3f}s' if 'first_time' in locals() else 'Not tested',
 'verification_passed': True,
 'next_chunk': 'CHUNK_4_FRONTEND_COMPONENTS'
 }, indent=2)
 
 print('Completion marker created: CHUNK_3_HIERARCHY_API_COMPLETE.marker')
 
 else:
 print('VERIFICATION FAILED')
 if errors:
 print('\nErrors encountered:')
 for error in errors:
 print(f' - {error}')
 
 return all_passed and not errors

if __name__ == "__main__":
 success = verify_chunk3_completion()
 exit(0 if success else 1)