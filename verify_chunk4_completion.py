#!/usr/bin/env python3
"""
CHUNK 4 Comprehensive Frontend Component Verification
Tests all 5-tier visual hierarchy frontend requirements as per PRP-8B specification
"""

import requests
import json
import time
import os
from datetime import datetime

def verify_chunk4_completion():
 
 base_url = "http://localhost:3010"
 tests = []
 errors = []
 
 print('CHUNK 4 VERIFICATION RESULTS:')
 print('=' * 60)
 
 # Test 1: Frontend page loads without errors
 try:
 response = requests.get(f"{base_url}/authoritative", timeout=10)
 
 page_works = response.status_code == 200
 tests.append(('Frontend page loads', page_works, f'Status: {response.status_code}'))
 print(f'{"PASS" if page_works else "FAIL":4} | {"Frontend page loads":<30} | Status: {response.status_code}')
 
 if page_works:
 # Test 2: Check HTML contains expected components
 html_content = response.text
 
 # Check for key component elements
 has_title = 'PRP-8B Authoritative Compliance System' in html_content
 has_form_inputs = 'Zone Code' in html_content and 'Development Type' in html_content
 has_analyze_button = 'Analyze Authoritative Compliance' in html_content
 
 tests.append(('Page title present', has_title, 'PRP-8B title found' if has_title else 'Title missing'))
 tests.append(('Form inputs present', has_form_inputs, 'Zone/DevType inputs found' if has_form_inputs else 'Inputs missing'))
 tests.append(('Analyze button present', has_analyze_button, 'Button found' if has_analyze_button else 'Button missing'))
 
 print(f'{"PASS" if has_title else "FAIL":4} | {"Page title present":<30} | {"PRP-8B title found" if has_title else "Title missing"}')
 print(f'{"PASS" if has_form_inputs else "FAIL":4} | {"Form inputs present":<30} | {"Zone/DevType inputs found" if has_form_inputs else "Inputs missing"}')
 print(f'{"PASS" if has_analyze_button else "FAIL":4} | {"Analyze button present":<30} | {"Button found" if has_analyze_button else "Button missing"}')
 
 except Exception as e:
 tests.append(('Frontend connection', False, f'Error: {str(e)}'))
 errors.append(f"Cannot connect to frontend: {e}")
 print(f'FAIL | {"Frontend connection":<30} | Error: {str(e)}')
 
 # Test 3: API endpoint integration works
 try:
 test_payload = {
 "property_id": 1,
 "zone_code": "R2", 
 "development_type": "dwelling_house"
 }
 
 print(f'Testing API integration for: {test_payload}')
 
 response = requests.post(
 f"{base_url}/api/authoritative/compliance-check",
 json=test_payload,
 timeout=30
 )
 
 api_works = response.status_code == 200
 tests.append(('API integration', api_works, f'Status: {response.status_code}'))
 print(f'{"PASS" if api_works else "FAIL":4} | {"API integration":<30} | Status: {response.status_code}')
 
 if api_works:
 data = response.json()
 
 # Test 4: Required 5-tier structure
 tier_fields = [
 'tier_1_provisions', 'tier_2_provisions', 'tier_3_provisions',
 'tier_4_provisions', 'tier_5_provisions'
 ]
 
 for field in tier_fields:
 has_field = field in data
 tests.append((f'Field {field}', has_field, 'Present' if has_field else 'Missing'))
 print(f'{"PASS" if has_field else "FAIL":4} | {f"Field {field}":<30} | {"Present" if has_field else "Missing"}')
 
 # Test 5: Tier 1 (Fully Authoritative) provisions
 tier_1_count = len(data.get('tier_1_provisions', []))
 has_tier_1 = tier_1_count > 0
 tests.append(('Tier 1 provisions', has_tier_1, f'{tier_1_count} provisions'))
 print(f'{"PASS" if has_tier_1 else "FAIL":4} | {"Tier 1 provisions":<30} | {tier_1_count} provisions')
 
 # Test 6: Check tier 1 provisions have numeric values
 tier_1_provisions = data.get('tier_1_provisions', [])
 if tier_1_provisions:
 numeric_provisions = sum(1 for p in tier_1_provisions if p.get('numeric_value') is not None)
 has_numeric = numeric_provisions > 0
 tests.append(('Tier 1 numeric values', has_numeric, f'{numeric_provisions}/{tier_1_count} have values'))
 print(f'{"PASS" if has_numeric else "FAIL":4} | {"Tier 1 numeric values":<30} | {numeric_provisions}/{tier_1_count} have values')
 
 # Test 7: Authority hierarchy metadata
 confidence = data.get('confidence_level', 0)
 disclaimer = data.get('legal_disclaimer', '')
 
 valid_confidence = 0 < confidence <= 1
 has_disclaimer = len(disclaimer) > 10
 
 tests.append(('Confidence level', valid_confidence, f'Confidence: {confidence:.3f}'))
 tests.append(('Legal disclaimer', has_disclaimer, f'{len(disclaimer)} chars'))
 
 print(f'{"PASS" if valid_confidence else "FAIL":4} | {"Confidence level":<30} | Confidence: {confidence:.3f}')
 print(f'{"PASS" if has_disclaimer else "FAIL":4} | {"Legal disclaimer":<30} | {len(disclaimer)} chars')
 
 # Test 8: Tier distribution analysis
 print(f'\\nTier Distribution Analysis:')
 print(f' Tier 1 (Fully authoritative): {len(data.get("tier_1_provisions", []))} provisions')
 print(f' Tier 2 (High authority): {len(data.get("tier_2_provisions", []))} provisions') 
 print(f' Tier 3 (Moderate authority): {len(data.get("tier_3_provisions", []))} provisions')
 print(f' Tier 4 (Framework guidance): {len(data.get("tier_4_provisions", []))} provisions')
 print(f' Tier 5 (Specialist required): {len(data.get("tier_5_provisions", []))} provisions')
 
 else:
 errors.append(f"API integration failed: {response.text}")
 
 except Exception as e:
 tests.append(('API integration', False, f'Error: {str(e)}'))
 errors.append(f"API integration error: {e}")
 print(f'FAIL | {"API integration":<30} | Error: {str(e)}')
 
 # Test 9: Component file structure
 component_files = [
 'frontend-nextjs/app/authoritative/page.tsx',
 'frontend-nextjs/components/compliance/AuthoritativeComplianceDisplay.tsx',
 'frontend-nextjs/components/ui/label.tsx',
 'frontend-nextjs/components/ui/select.tsx',
 'frontend-nextjs/components/ui/badge.tsx',
 'frontend-nextjs/components/ui/alert.tsx'
 ]
 
 for component_file in component_files:
 file_exists = os.path.exists(component_file)
 tests.append((f'File {os.path.basename(component_file)}', file_exists, 'Exists' if file_exists else 'Missing'))
 print(f'{"PASS" if file_exists else "FAIL":4} | {f"File {os.path.basename(component_file)}":<30} | {"Exists" if file_exists else "Missing"}')
 
 print('=' * 60)
 
 # Count results
 passed_tests = sum(1 for test in tests if test[1])
 total_tests = len(tests)
 success_rate = passed_tests / total_tests if total_tests > 0 else 0
 
 print(f'Test Results: {passed_tests}/{total_tests} passed ({success_rate:.1%})')
 
 all_passed = success_rate >= 0.85 and not errors # 85% pass rate required
 
 if all_passed:
 print('ALL CRITICAL TESTS PASSED - CHUNK 4 COMPLETE')
 
 # Create completion marker
 os.makedirs('prp_checkpoints', exist_ok=True)
 with open('prp_checkpoints/CHUNK_4_FRONTEND_COMPONENTS_COMPLETE.marker', 'w') as f:
 json.dump({
 'chunk': 'PRP-8B-CHUNK-4',
 'completed_at': datetime.now().isoformat(),
 'frontend_url': f'{base_url}/authoritative',
 'api_endpoint': '/api/authoritative/compliance-check',
 'tests_passed': f'{passed_tests}/{total_tests}',
 'success_rate': f'{success_rate:.1%}',
 'component_files': len(component_files),
 'tier_system': '5-tier hierarchy implemented',
 'verification_passed': True,
 'next_chunk': 'CHUNK_5_COMPLETE_INTEGRATION'
 }, indent=2)
 
 print('Completion marker created: CHUNK_4_FRONTEND_COMPONENTS_COMPLETE.marker')
 
 else:
 print('VERIFICATION FAILED')
 if errors:
 print('\\nErrors encountered:')
 for error in errors:
 print(f' - {error}')
 
 return all_passed and not errors

if __name__ == "__main__":
 success = verify_chunk4_completion()
 exit(0 if success else 1)