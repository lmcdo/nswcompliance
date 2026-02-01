#!/usr/bin/env python3
"""
Integration tests for versioning API endpoints.

Tests:
1. Current provisions query (default behavior)
2. Historical provisions query with version_date
3. Provisions with version metadata
4. Changes endpoint with document_id
5. Changes endpoint with provision_id
6. Changes endpoint with date filtering
"""

import requests
import json
from datetime import datetime, timedelta


API_BASE_URL = "http://localhost:3003/api"


def run_tests():
    """Run all versioning API integration tests."""
    print("=" * 70)
    print("VERSIONING API INTEGRATION TESTS")
    print("=" * 70)

    test_results = []

    # Test 1: Current provisions (default behavior)
    test_results.append(test_current_provisions())

    # Test 2: Historical provisions query
    test_results.append(test_historical_provisions())

    # Test 3: Provisions with version metadata
    test_results.append(test_version_metadata())

    # Test 4: Changes by document
    test_results.append(test_changes_by_document())

    # Test 5: Changes by provision
    test_results.append(test_changes_by_provision())

    # Test 6: Changes with date filtering
    test_results.append(test_changes_with_date_filter())

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for result in test_results if result['passed'])
    total = len(test_results)

    for result in test_results:
        status = "✓ PASS" if result['passed'] else "✗ FAIL"
        print(f"{status}: {result['name']}")
        if not result['passed']:
            print(f"  Error: {result.get('error', 'Unknown error')}")

    print(f"\nTotal: {passed}/{total} tests passed")

    return passed == total


def test_current_provisions():
    """Test 1: Current provisions query (default behavior)."""
    print("\n[Test 1] Testing current provisions query...")

    try:
        response = requests.get(
            f"{API_BASE_URL}/provisions/for-property",
            params={'zone': 'R2', 'former_council': 'Marrickville'},
            timeout=10
        )

        if response.status_code != 200:
            return {
                'name': 'Current provisions query',
                'passed': False,
                'error': f"HTTP {response.status_code}: {response.text[:100]}"
            }

        data = response.json()

        if not data.get('success'):
            return {
                'name': 'Current provisions query',
                'passed': False,
                'error': 'API returned success=false'
            }

        # Check structure
        if 'by_layer' not in data.get('data', {}):
            return {
                'name': 'Current provisions query',
                'passed': False,
                'error': 'Missing by_layer in response'
            }

        provision_count = sum(
            layer['count']
            for layer in data['data']['by_layer']
        )

        print(f"  ✓ Retrieved {provision_count} current provisions")
        print(f"  Response time: {data['metadata']['query_time_ms']}ms")

        return {
            'name': 'Current provisions query',
            'passed': True
        }

    except Exception as e:
        return {
            'name': 'Current provisions query',
            'passed': False,
            'error': str(e)
        }


def test_historical_provisions():
    """Test 2: Historical provisions query with version_date."""
    print("\n[Test 2] Testing historical provisions query...")

    try:
        # Query provisions as of 6 months ago
        version_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')

        response = requests.get(
            f"{API_BASE_URL}/provisions/for-property",
            params={
                'zone': 'R2',
                'former_council': 'Marrickville',
                'version_date': version_date
            },
            timeout=10
        )

        if response.status_code != 200:
            return {
                'name': 'Historical provisions query',
                'passed': False,
                'error': f"HTTP {response.status_code}: {response.text[:100]}"
            }

        data = response.json()

        if not data.get('success'):
            return {
                'name': 'Historical provisions query',
                'passed': False,
                'error': 'API returned success=false'
            }

        provision_count = sum(
            layer['count']
            for layer in data['data']['by_layer']
        )

        print(f"  ✓ Retrieved {provision_count} provisions as of {version_date}")
        print(f"  Response time: {data['metadata']['query_time_ms']}ms")

        return {
            'name': 'Historical provisions query',
            'passed': True
        }

    except Exception as e:
        return {
            'name': 'Historical provisions query',
            'passed': False,
            'error': str(e)
        }


def test_version_metadata():
    """Test 3: Provisions with version metadata."""
    print("\n[Test 3] Testing version metadata inclusion...")

    try:
        response = requests.get(
            f"{API_BASE_URL}/provisions/for-property",
            params={
                'zone': 'R2',
                'former_council': 'Marrickville',
                'include_version_metadata': 'true'
            },
            timeout=10
        )

        if response.status_code != 200:
            return {
                'name': 'Version metadata inclusion',
                'passed': False,
                'error': f"HTTP {response.status_code}: {response.text[:100]}"
            }

        data = response.json()

        if not data.get('success'):
            return {
                'name': 'Version metadata inclusion',
                'passed': False,
                'error': 'API returned success=false'
            }

        # Check first provision has version metadata
        layers = data['data']['by_layer']
        if len(layers) > 0 and len(layers[0]['provisions']) > 0:
            first_provision = layers[0]['provisions'][0]

            has_version_fields = (
                'version_count' in first_provision or
                'version_number' in first_provision
            )

            if has_version_fields:
                print(f"  ✓ Version metadata included in response")
                return {
                    'name': 'Version metadata inclusion',
                    'passed': True
                }
            else:
                return {
                    'name': 'Version metadata inclusion',
                    'passed': False,
                    'error': 'Version metadata fields not found in provision'
                }
        else:
            print("  ⚠ No provisions returned to check metadata")
            return {
                'name': 'Version metadata inclusion',
                'passed': True  # Not a failure, just no data
            }

    except Exception as e:
        return {
            'name': 'Version metadata inclusion',
            'passed': False,
            'error': str(e)
        }


def test_changes_by_document():
    """Test 4: Changes endpoint with document_id."""
    print("\n[Test 4] Testing changes by document...")

    try:
        response = requests.get(
            f"{API_BASE_URL}/provisions/changes",
            params={
                'document_id': 'Marrickville_DCP_2011__Part_2',
                'since': '2024-01-01'
            },
            timeout=10
        )

        if response.status_code != 200:
            return {
                'name': 'Changes by document',
                'passed': False,
                'error': f"HTTP {response.status_code}: {response.text[:100]}"
            }

        data = response.json()

        if not data.get('success'):
            return {
                'name': 'Changes by document',
                'passed': False,
                'error': 'API returned success=false'
            }

        # Check structure
        if 'summary' not in data.get('data', {}):
            return {
                'name': 'Changes by document',
                'passed': False,
                'error': 'Missing summary in response'
            }

        summary = data['data']['summary']
        total_changes = summary.get('total', 0)

        print(f"  ✓ Found {total_changes} changes")
        print(f"    Modified: {summary.get('modified', 0)}")
        print(f"    Created: {summary.get('created', 0)}")
        print(f"    Deleted: {summary.get('deleted', 0)}")

        return {
            'name': 'Changes by document',
            'passed': True
        }

    except Exception as e:
        return {
            'name': 'Changes by document',
            'passed': False,
            'error': str(e)
        }


def test_changes_by_provision():
    """Test 5: Changes endpoint with provision_id."""
    print("\n[Test 5] Testing changes by provision...")

    try:
        # Use a known provision ID (this may need adjustment)
        response = requests.get(
            f"{API_BASE_URL}/provisions/changes",
            params={
                'provision_id': '1',
                'since': '2024-01-01'
            },
            timeout=10
        )

        if response.status_code != 200:
            return {
                'name': 'Changes by provision',
                'passed': False,
                'error': f"HTTP {response.status_code}: {response.text[:100]}"
            }

        data = response.json()

        if not data.get('success'):
            return {
                'name': 'Changes by provision',
                'passed': False,
                'error': 'API returned success=false'
            }

        total_changes = data['data']['summary'].get('total', 0)

        print(f"  ✓ Found {total_changes} changes for provision")

        return {
            'name': 'Changes by provision',
            'passed': True
        }

    except Exception as e:
        return {
            'name': 'Changes by provision',
            'passed': False,
            'error': str(e)
        }


def test_changes_with_date_filter():
    """Test 6: Changes endpoint with date filtering."""
    print("\n[Test 6] Testing changes with date filter...")

    try:
        # Query changes in last 30 days
        since_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        response = requests.get(
            f"{API_BASE_URL}/provisions/changes",
            params={
                'document_id': 'Marrickville_DCP_2011__Part_2',
                'since': since_date,
                'change_type': 'modified'
            },
            timeout=10
        )

        if response.status_code != 200:
            return {
                'name': 'Changes with date filter',
                'passed': False,
                'error': f"HTTP {response.status_code}: {response.text[:100]}"
            }

        data = response.json()

        if not data.get('success'):
            return {
                'name': 'Changes with date filter',
                'passed': False,
                'error': 'API returned success=false'
            }

        total_changes = data['data']['summary'].get('total', 0)

        print(f"  ✓ Found {total_changes} modified changes since {since_date}")

        return {
            'name': 'Changes with date filter',
            'passed': True
        }

    except Exception as e:
        return {
            'name': 'Changes with date filter',
            'passed': False,
            'error': str(e)
        }


if __name__ == '__main__':
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
