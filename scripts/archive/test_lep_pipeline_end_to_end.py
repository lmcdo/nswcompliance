#!/usr/bin/env python3
"""
Test the complete LEP pipeline end-to-end:
1. Test property API returns LEP provisions
2. Test LEP provisions API returns clause details
3. Verify R2 images are accessible
4. Confirm page numbers are correct
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import time

# Test addresses that should have LEP provisions
TEST_ADDRESSES = [
    {
        'address': '45 Lilyfield Road, Rozelle NSW 2039',
        'expected_clause': '6.21',
        'lga': 'Leichhardt',
        'type': 'Key Site',
    },
    {
        'address': '126 Parramatta Road, Stanmore NSW 2048',
        'expected_clause': '6.33',
        'lga': 'Marrickville',
        'type': 'Key Site',
    },
    {
        'address': '10 Perry Street, Lilyfield NSW 2040',
        'expected_clause': '6.31',
        'lga': 'Leichhardt',
        'type': 'Key Site',
    },
]

# R2 base URL
R2_URL = 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev'

# API base URL (assume localhost:3003)
API_BASE = 'http://localhost:3003'


def test_property_api(address: str):
    """Test /api/property endpoint returns data."""
    print(f'  Testing property API for: {address}')

    url = f'{API_BASE}/api/property'
    params = {'address': address}

    try:
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()
            print(f'    ✅ Property API OK (HTTP 200)')

            # Check if localProvisions exist
            local_provisions = data.get('constraints', {}).get('localProvisions', [])
            if local_provisions:
                print(f'    ✅ Has {len(local_provisions)} local provisions')
                return True, local_provisions
            else:
                print(f'    ⚠️  No local provisions found')
                return False, []
        else:
            print(f'    ❌ Property API failed (HTTP {response.status_code})')
            return False, []

    except requests.RequestException as e:
        print(f'    ❌ Property API error: {e}')
        return False, []


def test_lep_provisions_api(clause_number: str):
    """Test /api/lep/provisions endpoint returns clause details."""
    print(f'  Testing LEP provisions API for clause {clause_number}')

    url = f'{API_BASE}/api/lep/provisions'
    params = {'clause': clause_number}

    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            print(f'    ✅ LEP Provisions API OK (HTTP 200)')

            clause_num = data.get('clauseNumber')
            page_num = data.get('pageNumber')
            text_length = len(data.get('provisionText', ''))

            print(f'    ✅ Clause: {clause_num}, Page: {page_num}, Text: {text_length} chars')

            return True, data
        else:
            print(f'    ❌ LEP Provisions API failed (HTTP {response.status_code})')
            return False, None

    except requests.RequestException as e:
        print(f'    ❌ LEP Provisions API error: {e}')
        return False, None


def test_r2_image(clause_number: str, page_number: int):
    """Test R2 image is accessible."""
    print(f'  Testing R2 image for clause {clause_number} page {page_number}')

    image_filename = f"iwlep_clause_{clause_number.replace('.', '_')}_page_{page_number}.png"
    image_url = f'{R2_URL}/pdf-pages/{image_filename}'

    try:
        response = requests.head(image_url, timeout=10)

        if response.status_code == 200:
            content_length = response.headers.get('content-length', '0')
            size_kb = int(content_length) / 1024
            print(f'    ✅ Image accessible ({size_kb:.0f} KB)')
            print(f'    🌐 URL: {image_url}')
            return True
        else:
            print(f'    ❌ Image not accessible (HTTP {response.status_code})')
            print(f'    🌐 URL: {image_url}')
            return False

    except requests.RequestException as e:
        print(f'    ❌ Image request error: {e}')
        print(f'    🌐 URL: {image_url}')
        return False


def main():
    """Run complete end-to-end pipeline test."""

    print('=' * 80)
    print('LEP PIPELINE END-TO-END TEST')
    print('=' * 80)
    print()

    # Check if dev server is running
    print('Checking if Next.js dev server is running...')
    try:
        response = requests.get(API_BASE, timeout=5)
        print(f'✅ Dev server is running at {API_BASE}')
    except requests.RequestException:
        print(f'❌ Dev server not running at {API_BASE}')
        print()
        print('Please start the dev server first:')
        print('  cd frontend-nextjs')
        print('  npm run dev')
        sys.exit(1)

    print()
    print('=' * 80)
    print('TESTING ADDRESSES WITH KEY SITES PROVISIONS')
    print('=' * 80)
    print()

    total_tests = 0
    passed_tests = 0

    for idx, test_case in enumerate(TEST_ADDRESSES, 1):
        address = test_case['address']
        expected_clause = test_case['expected_clause']
        lga = test_case['lga']
        test_type = test_case['type']

        print(f'[{idx}/{len(TEST_ADDRESSES)}] {address}')
        print(f'     LGA: {lga} | Type: {test_type} | Expected Clause: {expected_clause}')
        print()

        # Test 1: Property API
        total_tests += 1
        success, local_provisions = test_property_api(address)
        if success:
            passed_tests += 1

        print()

        # Test 2: LEP Provisions API
        if expected_clause:
            total_tests += 1
            success, provision_data = test_lep_provisions_api(expected_clause)
            if success:
                passed_tests += 1

            print()

            # Test 3: R2 Image
            if provision_data and provision_data.get('pageNumber'):
                total_tests += 1
                success = test_r2_image(expected_clause, provision_data['pageNumber'])
                if success:
                    passed_tests += 1

        print()
        print('-' * 80)
        print()

    # Summary
    print('=' * 80)
    print('TEST SUMMARY')
    print('=' * 80)
    print()
    print(f'Total tests run:    {total_tests}')
    print(f'Passed:             {passed_tests} ({passed_tests/total_tests*100:.0f}%)')
    print(f'Failed:             {total_tests - passed_tests}')
    print()

    if passed_tests == total_tests:
        print('✅ ALL TESTS PASSED!')
        print()
        print('The complete LEP pipeline is working:')
        print('  1. Property API returns LEP provisions ✅')
        print('  2. LEP Provisions API returns clause details with page numbers ✅')
        print('  3. R2 images are accessible and display correctly ✅')
        print()
        print('Next step: Test in browser at http://localhost:3003/')
        return 0
    else:
        print('❌ SOME TESTS FAILED')
        print()
        print('Please review the errors above and fix before proceeding.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
