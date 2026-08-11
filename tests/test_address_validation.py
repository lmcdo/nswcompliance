import pytest

"""
Address Validation Test Suite

Tests that don't require ground truth:
1. Cross-source validation (our API vs NSW Planning Portal)
2. Internal consistency (no cross-council contamination)
3. Source document validation (PDF links work)
4. Text quality checks (provisions are readable)
5. Statistical anomaly detection
6. Temporal consistency (same input = same output)
7. Mathematical sanity checks
8. Sibling comparison (adjacent addresses similar)
"""

import json
import requests
import time
import hashlib
import statistics
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path


# Configuration
BASE_URL = "http://localhost:3007"
FIXTURES_PATH = Path(__file__).parent / "fixtures" / "test_addresses.json"


@dataclass
class TestResult:
    test_name: str
    address: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    results: List[TestResult] = field(default_factory=list)

    def add(self, result: TestResult):
        self.total_tests += 1
        if result.passed:
            self.passed += 1
        else:
            self.failed += 1
        self.results.append(result)

    def summary(self) -> str:
        pct = (self.passed / self.total_tests * 100) if self.total_tests > 0 else 0
        return f"{self.passed}/{self.total_tests} passed ({pct:.1f}%)"


def load_test_addresses() -> List[Dict]:
    """Load test addresses from fixture file"""
    with open(FIXTURES_PATH) as f:
        data = json.load(f)
    return data["addresses"]


def fetch_property_api(address: str) -> Optional[Dict]:
    """Fetch from our property API"""
    try:
        resp = requests.get(
            f"{BASE_URL}/api/property",
            params={"address": address},
            timeout=30
        )
        if resp.status_code == 200:
            result = resp.json()
            # API returns {success, data: {...}} - extract data
            if result.get("success") and result.get("data"):
                return result["data"]
            return result
        return None
    except Exception as e:
        print(f"  API error for {address}: {e}")
        return None


def fetch_dcp_api(address: str, zone: str, lga: str, coords: Dict) -> Optional[Dict]:
    """Fetch from DCP complete API"""
    try:
        resp = requests.post(
            f"{BASE_URL}/api/compliance/dcp-complete",
            json={
                "address": address,
                "zone": zone or "R2",
                "developmentType": "dwelling_house",
                "lga": lga or "Inner West",
                "coordinates": coords
            },
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as e:
        print(f"  DCP API error: {e}")
        return None


# =============================================================================
# TEST 1: Cross-Source Validation
# =============================================================================

def test_cross_source_validation(test_addr: Dict, report: ValidationReport):
    """Compare our API results with NSW Planning Portal"""
    address = test_addr["address"]

    # Skip rejected addresses
    if test_addr["test_category"] == "rejected":
        return

    result = fetch_property_api(address)
    if not result:
        report.add(TestResult(
            test_name="cross_source_validation",
            address=address,
            passed=False,
            message="API returned no data"
        ))
        return

    constraints = result.get("constraints", {})

    # Check zone matches expected (if specified)
    expected_zone = test_addr.get("expected_zone")
    actual_zone = constraints.get("zone")

    if expected_zone and actual_zone:
        zone_match = actual_zone.startswith(expected_zone[:2])  # R2 matches R2, R3, etc.
        report.add(TestResult(
            test_name="cross_source_zone",
            address=address,
            passed=zone_match,
            message=f"Zone: expected {expected_zone}, got {actual_zone}",
            details={"expected": expected_zone, "actual": actual_zone}
        ))

    # Check LGA is Inner West
    lga = constraints.get("lga") or ""
    is_inner_west = "inner west" in lga.lower() if lga else False
    report.add(TestResult(
        test_name="cross_source_lga",
        address=address,
        passed=is_inner_west,
        message=f"LGA: {lga}",
        details={"lga": lga}
    ))


# =============================================================================
# TEST 2: Internal Consistency
# =============================================================================

def test_internal_consistency(test_addr: Dict, report: ValidationReport):
    """Check that council and provisions don't contradict"""
    address = test_addr["address"]

    if test_addr["test_category"] == "rejected":
        return

    prop_result = fetch_property_api(address)
    if not prop_result:
        return

    constraints = prop_result.get("constraints") or {}
    former_council = constraints.get("formerCouncil") or ""
    zone = constraints.get("zone") or "R2"
    lga = constraints.get("lga") or ""

    coords = {
        "lat": prop_result.get("coordinates", {}).get("lat") or prop_result.get("geometry", {}).get("y"),
        "lon": prop_result.get("coordinates", {}).get("lon") or prop_result.get("geometry", {}).get("x")
    }

    dcp_result = fetch_dcp_api(address, zone, lga, coords)
    if not dcp_result or not dcp_result.get("success"):
        return

    # Check no cross-council contamination
    other_councils = {"Ashfield", "Marrickville", "Leichhardt"} - {former_council}

    provisions_json = json.dumps(dcp_result.get("general_provisions", {}))

    contamination = []
    for other in other_councils:
        # Check if other council's DCP appears in provisions
        if f"{other} DCP" in provisions_json or f"{other}_DCP" in provisions_json:
            contamination.append(other)

    report.add(TestResult(
        test_name="no_cross_contamination",
        address=address,
        passed=len(contamination) == 0,
        message=f"Council: {former_council}, Contamination: {contamination or 'None'}",
        details={"council": former_council, "contamination": contamination}
    ))


# =============================================================================
# TEST 3: Text Quality Checks
# =============================================================================

def test_text_quality(test_addr: Dict, report: ValidationReport):
    """Check that provision text is readable, not garbage"""
    address = test_addr["address"]

    if test_addr["test_category"] == "rejected":
        return

    prop_result = fetch_property_api(address)
    if not prop_result:
        return

    constraints = prop_result.get("constraints", {})
    zone = constraints.get("zone") or "R2"
    lga = constraints.get("lga") or ""
    coords = {
        "lat": prop_result.get("coordinates", {}).get("lat") or prop_result.get("geometry", {}).get("y"),
        "lon": prop_result.get("coordinates", {}).get("lon") or prop_result.get("geometry", {}).get("x")
    }

    dcp_result = fetch_dcp_api(address, zone, lga, coords)
    if not dcp_result or not dcp_result.get("success"):
        return

    requirements = dcp_result.get("general_provisions", {}).get("requirements", [])

    if not requirements:
        report.add(TestResult(
            test_name="text_quality",
            address=address,
            passed=False,
            message="No requirements returned"
        ))
        return

    quality_issues = []
    for i, req in enumerate(requirements[:20]):  # Check first 20
        text = req.get("requirement_text", "") or req.get("provision_text", "")

        if not text:
            quality_issues.append(f"Empty text at index {i}")
            continue

        # Check for PDF header garbage
        if text.strip().startswith("Page ") or re.match(r"^\d+\s*$", text.strip()):
            quality_issues.append(f"PDF header garbage at index {i}")

        # Check minimum length
        if len(text) < 10:
            quality_issues.append(f"Too short ({len(text)} chars) at index {i}")

        # Check has actual words
        if not re.search(r"[a-zA-Z]{3,}", text):
            quality_issues.append(f"No real words at index {i}")

    report.add(TestResult(
        test_name="text_quality",
        address=address,
        passed=len(quality_issues) == 0,
        message=f"{len(quality_issues)} quality issues" if quality_issues else "Text quality OK",
        details={"issues": quality_issues[:5], "checked": min(20, len(requirements))}
    ))


# =============================================================================
# TEST 4: Mathematical Sanity
# =============================================================================

def test_mathematical_sanity(test_addr: Dict, report: ValidationReport):
    """Check that numeric values are in reasonable ranges"""
    address = test_addr["address"]

    if test_addr["test_category"] == "rejected":
        return

    prop_result = fetch_property_api(address)
    if not prop_result:
        return

    constraints = prop_result.get("constraints", {})
    issues = []

    # Check FSR
    fsr = constraints.get("maxFsr")
    if fsr is not None:
        if not (0 < fsr <= 10):
            issues.append(f"FSR out of range: {fsr}")

    # Check height
    height = constraints.get("maxHeight")
    if height is not None:
        if not (0 < height <= 100):
            issues.append(f"Height out of range: {height}")

    # Check lot size
    lot_size = constraints.get("minLotSize")
    if lot_size is not None:
        if not (0 < lot_size <= 50000):
            issues.append(f"Lot size out of range: {lot_size}")

    report.add(TestResult(
        test_name="mathematical_sanity",
        address=address,
        passed=len(issues) == 0,
        message="; ".join(issues) if issues else "All values in range",
        details={"fsr": fsr, "height": height, "lot_size": lot_size}
    ))


# =============================================================================
# TEST 5: Temporal Consistency
# =============================================================================

def test_temporal_consistency(test_addr: Dict, report: ValidationReport):
    """Same address queried twice should return same results"""
    address = test_addr["address"]

    if test_addr["test_category"] == "rejected":
        return

    result1 = fetch_property_api(address)
    time.sleep(0.5)  # Brief delay
    result2 = fetch_property_api(address)

    if not result1 or not result2:
        return

    # Compare key fields
    c1 = result1.get("constraints", {})
    c2 = result2.get("constraints", {})

    matches = {
        "zone": c1.get("zone") == c2.get("zone"),
        "lga": c1.get("lga") == c2.get("lga"),
        "formerCouncil": c1.get("formerCouncil") == c2.get("formerCouncil"),
    }

    all_match = all(matches.values())

    report.add(TestResult(
        test_name="temporal_consistency",
        address=address,
        passed=all_match,
        message="Results consistent" if all_match else f"Inconsistent: {matches}",
        details=matches
    ))


# =============================================================================
# TEST 6: Rejected Address Handling
# =============================================================================

def test_rejected_addresses(test_addr: Dict, report: ValidationReport):
    """Addresses outside Inner West should be rejected or flagged"""
    address = test_addr["address"]

    if test_addr["test_category"] != "rejected":
        return

    result = fetch_property_api(address)

    if not result:
        # No result could mean rejected - that's acceptable
        report.add(TestResult(
            test_name="rejected_handling",
            address=address,
            passed=True,
            message="Address returned no data (expected for non-Inner West)"
        ))
        return

    constraints = result.get("constraints", {})
    lga = constraints.get("lga", "").lower()

    # Should NOT be Inner West
    is_inner_west = "inner west" in lga

    report.add(TestResult(
        test_name="rejected_handling",
        address=address,
        passed=not is_inner_west,
        message=f"LGA detected: {constraints.get('lga', 'None')}",
        details={"lga": constraints.get("lga"), "should_reject": True}
    ))


# =============================================================================
# TEST 7: Provision Count Sanity
# =============================================================================

def test_provision_count(test_addr: Dict, report: ValidationReport):
    """Check reasonable number of provisions returned"""
    address = test_addr["address"]

    if test_addr["test_category"] == "rejected":
        return

    prop_result = fetch_property_api(address)
    if not prop_result:
        return

    constraints = prop_result.get("constraints", {})
    zone = constraints.get("zone") or "R2"
    lga = constraints.get("lga") or ""
    coords = {
        "lat": prop_result.get("coordinates", {}).get("lat") or prop_result.get("geometry", {}).get("y"),
        "lon": prop_result.get("coordinates", {}).get("lon") or prop_result.get("geometry", {}).get("x")
    }

    dcp_result = fetch_dcp_api(address, zone, lga, coords)
    if not dcp_result or not dcp_result.get("success"):
        return

    total = dcp_result.get("combined", {}).get("total_requirements", 0)

    # Should have SOME provisions but not absurdly many
    reasonable = 5 <= total <= 500

    report.add(TestResult(
        test_name="provision_count",
        address=address,
        passed=reasonable,
        message=f"{total} provisions returned",
        details={"count": total, "min_expected": 5, "max_expected": 500}
    ))


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_all_tests() -> ValidationReport:
    """Run all tests on all addresses"""
    print("=" * 60)
    print("ADDRESS VALIDATION TEST SUITE")
    print("=" * 60)

    addresses = load_test_addresses()
    print(f"\nLoaded {len(addresses)} test addresses")

    report = ValidationReport()

    for i, test_addr in enumerate(addresses):
        addr = test_addr["address"]
        print(f"\n[{i+1}/{len(addresses)}] Testing: {addr[:50]}...")

        # Run all test types
        test_cross_source_validation(test_addr, report)
        test_internal_consistency(test_addr, report)
        test_text_quality(test_addr, report)
        test_mathematical_sanity(test_addr, report)
        test_temporal_consistency(test_addr, report)
        test_rejected_addresses(test_addr, report)
        test_provision_count(test_addr, report)

    return report


def print_report(report: ValidationReport):
    """Print formatted test report"""
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"\nSummary: {report.summary()}")
    print(f"  Passed: {report.passed}")
    print(f"  Failed: {report.failed}")

    # Group by test name
    by_test = {}
    for r in report.results:
        if r.test_name not in by_test:
            by_test[r.test_name] = {"passed": 0, "failed": 0, "failures": []}
        if r.passed:
            by_test[r.test_name]["passed"] += 1
        else:
            by_test[r.test_name]["failed"] += 1
            by_test[r.test_name]["failures"].append(r)

    print("\nBy Test Type:")
    for test_name, stats in by_test.items():
        total = stats["passed"] + stats["failed"]
        pct = stats["passed"] / total * 100 if total > 0 else 0
        status = "PASS" if stats["failed"] == 0 else "FAIL"
        print(f"  [{status}] {test_name}: {stats['passed']}/{total} ({pct:.0f}%)")

    # Print failures
    failures = [r for r in report.results if not r.passed]
    if failures:
        print(f"\nFailures ({len(failures)}):")
        for f in failures[:10]:  # First 10
            print(f"  [FAIL] [{f.test_name}] {f.address[:40]}")
            print(f"         {f.message}")

    # Export to JSON
    output_path = Path(__file__).parent / "results" / "validation_report.json"
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, "w") as f:
        json.dump({
            "summary": report.summary(),
            "passed": report.passed,
            "failed": report.failed,
            "total": report.total_tests,
            "results": [
                {
                    "test": r.test_name,
                    "address": r.address,
                    "passed": r.passed,
                    "message": r.message
                }
                for r in report.results
            ]
        }, f, indent=2)

    print(f"\nFull report saved to: {output_path}")


if __name__ == "__main__":
    report = run_all_tests()
    print_report(report)

_PROBE_URL = "http://localhost:3007"

# ── Live-server guard ────────────────────────────────────────────────────────
# This is a genuine integration test: it drives a running local server, not a
# pure function. It was quarantined on 2026-05-23 and became invisible, which
# is worse than being skipped — an uncollected file reports nothing at all.
#
# So instead of hiding it, it now SKIPS with a reason when the server is not
# up, and carries the `integration` marker so it stays out of the default run
# while remaining visible and runnable on demand:
#
#     pytest -m integration        (with the dev server running)
#
# The probe uses a short timeout and is evaluated once at import, so a missing
# server costs a fraction of a second rather than a hung suite.
def _server_is_up(url: str, timeout: float = 1.0) -> bool:
    try:
        import urllib.request
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _server_is_up(_PROBE_URL),
        reason=f"needs a local server at {_PROBE_URL} — start the dev server, then: pytest -m integration",
    ),
]
