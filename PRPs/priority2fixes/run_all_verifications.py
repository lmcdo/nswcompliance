#!/usr/bin/env python3
"""
Master Verification Runner for All PRP-Q Series
Run individual PRP verifications or all PRPs with detailed reporting
"""

import asyncio
import json
import sys
import argparse
from datetime import datetime
from typing import Dict, List, Optional
import importlib.util

# Import individual verification suites
from verify_prp_q1 import PRPQ1VerificationSuite
from verify_prp_q2 import PRPQ2VerificationSuite
from verify_prp_q3 import PRPQ3VerificationSuite
from verify_prp_q4 import PRPQ4VerificationSuite

class MasterVerificationRunner:
    """Master runner for all PRP-Q verification suites"""

    def __init__(self):
        self.verification_suites = {
            'Q1': PRPQ1VerificationSuite,
            'Q2': PRPQ2VerificationSuite,
            'Q3': PRPQ3VerificationSuite,
            'Q4': PRPQ4VerificationSuite
        }
        self.results = {}

    async def run_all_verifications(self) -> Dict:
        """Run all PRP-Q verifications"""

        print("🚀 MASTER PRP-Q VERIFICATION RUNNER")
        print("==================================")
        print("Running all PRP-Q granular verifications")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        overall_start_time = asyncio.get_event_loop().time()

        # Run each verification suite
        for prp_id, suite_class in self.verification_suites.items():
            print(f"🔍 Starting PRP-{prp_id} verification...")

            suite = suite_class()
            try:
                self.results[f'PRP-{prp_id}'] = await suite.run_complete_verification()

                # Print quick status
                result = self.results[f'PRP-{prp_id}']
                status = "✅ PASS" if result.get('overall_success', False) else "❌ FAIL"
                pass_rate = result.get('test_summary', {}).get('pass_rate_percent', 0)

                print(f"   {status} - {pass_rate}% tests passed")
                print()

            except Exception as e:
                print(f"   ❌ ERROR - {str(e)}")
                self.results[f'PRP-{prp_id}'] = {
                    'overall_success': False,
                    'error': str(e),
                    'test_summary': {'total_tests': 0, 'passed_tests': 0, 'pass_rate_percent': 0}
                }
                print()

        overall_time = asyncio.get_event_loop().time() - overall_start_time

        # Generate master summary
        master_summary = self._generate_master_summary(overall_time)
        self.results['master_summary'] = master_summary

        return self.results

    async def run_single_verification(self, prp_id: str) -> Dict:
        """Run a single PRP verification"""

        if prp_id not in self.verification_suites:
            raise ValueError(f"Unknown PRP ID: {prp_id}. Available: {list(self.verification_suites.keys())}")

        print(f"🔍 SINGLE PRP-{prp_id} VERIFICATION")
        print("=" * 35)
        print(f"Running PRP-{prp_id} granular verification")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        suite_class = self.verification_suites[prp_id]
        suite = suite_class()

        result = await suite.run_complete_verification()
        self.results[f'PRP-{prp_id}'] = result

        return {f'PRP-{prp_id}': result}

    def _generate_master_summary(self, total_time: float) -> Dict:
        """Generate master summary across all PRPs"""

        prp_results = [result for key, result in self.results.items() if key.startswith('PRP-')]

        total_prps = len(prp_results)
        passed_prps = sum(1 for result in prp_results if result.get('overall_success', False))
        failed_prps = total_prps - passed_prps

        total_tests = sum(result.get('test_summary', {}).get('total_tests', 0) for result in prp_results)
        total_passed = sum(result.get('test_summary', {}).get('passed_tests', 0) for result in prp_results)

        overall_pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        # PRP status breakdown
        prp_status = {}
        for key, result in self.results.items():
            if key.startswith('PRP-'):
                prp_status[key] = {
                    'status': 'PASS' if result.get('overall_success', False) else 'FAIL',
                    'pass_rate': result.get('test_summary', {}).get('pass_rate_percent', 0),
                    'tests_passed': result.get('test_summary', {}).get('passed_tests', 0),
                    'total_tests': result.get('test_summary', {}).get('total_tests', 0),
                    'verification_time': result.get('total_verification_time_seconds', 0)
                }

        # Implementation readiness assessment
        readiness_score = self._calculate_implementation_readiness(prp_status)

        return {
            'verification_timestamp': datetime.now().isoformat(),
            'total_verification_time_seconds': round(total_time, 2),
            'prp_summary': {
                'total_prps': total_prps,
                'prps_passed': passed_prps,
                'prps_failed': failed_prps,
                'prp_pass_rate_percent': round((passed_prps / total_prps * 100), 1) if total_prps > 0 else 0
            },
            'test_summary': {
                'total_tests_across_all_prps': total_tests,
                'total_tests_passed': total_passed,
                'overall_pass_rate_percent': round(overall_pass_rate, 1)
            },
            'prp_status_breakdown': prp_status,
            'implementation_readiness': readiness_score,
            'next_steps': self._generate_next_steps(prp_status),
            'overall_success': passed_prps == total_prps and overall_pass_rate >= 80
        }

    def _calculate_implementation_readiness(self, prp_status: Dict) -> Dict:
        """Calculate implementation readiness score"""

        readiness_factors = {
            'file_structure': 0,
            'core_functionality': 0,
            'api_integration': 0,
            'performance': 0,
            'legal_compliance': 0
        }

        total_prps = len(prp_status)

        for prp_id, status in prp_status.items():
            if status['status'] == 'PASS':
                if prp_id == 'PRP-Q1':  # Live compliance calculator
                    readiness_factors['core_functionality'] += 25
                    readiness_factors['api_integration'] += 25
                    readiness_factors['performance'] += 25
                elif prp_id == 'PRP-Q2':  # Pathway intelligence
                    readiness_factors['core_functionality'] += 25
                    readiness_factors['api_integration'] += 25
                elif prp_id == 'PRP-Q3':  # Advanced compliance
                    readiness_factors['core_functionality'] += 25
                    readiness_factors['performance'] += 25
                elif prp_id == 'PRP-Q4':  # Legal disclaimers
                    readiness_factors['legal_compliance'] += 50

                readiness_factors['file_structure'] += 25

        # Normalize to percentage
        for factor in readiness_factors:
            readiness_factors[factor] = min(100, readiness_factors[factor])

        overall_readiness = sum(readiness_factors.values()) / len(readiness_factors)

        return {
            'overall_readiness_percent': round(overall_readiness, 1),
            'factor_breakdown': readiness_factors,
            'readiness_level': self._get_readiness_level(overall_readiness),
            'blocking_issues': self._identify_blocking_issues(prp_status)
        }

    def _get_readiness_level(self, readiness_percent: float) -> str:
        """Get readiness level description"""
        if readiness_percent >= 90:
            return "PRODUCTION_READY"
        elif readiness_percent >= 75:
            return "NEAR_PRODUCTION_READY"
        elif readiness_percent >= 50:
            return "DEVELOPMENT_COMPLETE"
        elif readiness_percent >= 25:
            return "EARLY_DEVELOPMENT"
        else:
            return "SETUP_REQUIRED"

    def _identify_blocking_issues(self, prp_status: Dict) -> List[str]:
        """Identify blocking issues preventing implementation"""

        blocking_issues = []

        for prp_id, status in prp_status.items():
            if status['status'] == 'FAIL':
                if status['pass_rate'] < 50:
                    blocking_issues.append(f"{prp_id}: Major implementation missing ({status['pass_rate']}% tests passed)")
                elif status['pass_rate'] < 80:
                    blocking_issues.append(f"{prp_id}: Minor issues need resolution ({status['pass_rate']}% tests passed)")

        return blocking_issues

    def _generate_next_steps(self, prp_status: Dict) -> List[str]:
        """Generate recommended next steps"""

        next_steps = []

        # Check implementation priority order
        prp_priority = ['PRP-Q1', 'PRP-Q2', 'PRP-Q3', 'PRP-Q4']

        for prp_id in prp_priority:
            if prp_id in prp_status and prp_status[prp_id]['status'] == 'FAIL':
                next_steps.append(f"Implement {prp_id} ({prp_status[prp_id]['tests_passed']}/{prp_status[prp_id]['total_tests']} tests passing)")
                break  # Focus on one PRP at a time

        # If all PRPs pass, suggest optimization steps
        if all(status['status'] == 'PASS' for status in prp_status.values()):
            next_steps.extend([
                "All PRPs verified successfully",
                "Ready for production deployment",
                "Consider performance optimization",
                "Set up continuous monitoring"
            ])

        return next_steps

    def save_results(self, filename: Optional[str] = None) -> str:
        """Save all verification results to JSON file"""

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"MASTER_PRP_Q_VERIFICATION_REPORT_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str)

        return filename

    def print_summary(self):
        """Print comprehensive summary"""

        if 'master_summary' not in self.results:
            print("No master summary available. Run verifications first.")
            return

        summary = self.results['master_summary']

        print("\n" + "=" * 60)
        print("🎯 MASTER VERIFICATION SUMMARY")
        print("=" * 60)

        # Overall status
        overall_status = "✅ SUCCESS" if summary['overall_success'] else "❌ NEEDS WORK"
        print(f"Overall Status: {overall_status}")
        print(f"Verification Time: {summary['total_verification_time_seconds']}s")
        print()

        # PRP breakdown
        print("📊 PRP STATUS BREAKDOWN:")
        prp_summary = summary['prp_summary']
        print(f"  PRPs Passed: {prp_summary['prps_passed']}/{prp_summary['total_prps']} ({prp_summary['prp_pass_rate_percent']}%)")

        for prp_id, status in summary['prp_status_breakdown'].items():
            status_icon = "✅" if status['status'] == 'PASS' else "❌"
            print(f"  {status_icon} {prp_id}: {status['pass_rate']}% ({status['tests_passed']}/{status['total_tests']} tests)")
        print()

        # Test summary
        test_summary = summary['test_summary']
        print("🧪 TEST SUMMARY:")
        print(f"  Total Tests: {test_summary['total_tests_across_all_prps']}")
        print(f"  Tests Passed: {test_summary['total_tests_passed']}")
        print(f"  Overall Pass Rate: {test_summary['overall_pass_rate_percent']}%")
        print()

        # Implementation readiness
        readiness = summary['implementation_readiness']
        print("🚀 IMPLEMENTATION READINESS:")
        print(f"  Overall Readiness: {readiness['overall_readiness_percent']}% ({readiness['readiness_level']})")

        print("  Factor Breakdown:")
        for factor, score in readiness['factor_breakdown'].items():
            print(f"    {factor}: {score}%")

        if readiness['blocking_issues']:
            print("\n  🚫 Blocking Issues:")
            for issue in readiness['blocking_issues']:
                print(f"    • {issue}")
        print()

        # Next steps
        print("📋 NEXT STEPS:")
        for step in summary['next_steps']:
            print(f"  • {step}")

async def main():
    """Main execution function"""

    parser = argparse.ArgumentParser(description='Run PRP-Q verification suites')
    parser.add_argument('--prp', choices=['Q1', 'Q2', 'Q3', 'Q4'],
                       help='Run verification for specific PRP only')
    parser.add_argument('--save', action='store_true',
                       help='Save results to JSON file')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress detailed output, show summary only')

    args = parser.parse_args()

    runner = MasterVerificationRunner()

    try:
        if args.prp:
            # Run single PRP verification
            results = await runner.run_single_verification(args.prp)

            if not args.quiet:
                print(f"\n✅ PRP-{args.prp} verification completed")

        else:
            # Run all PRP verifications
            results = await runner.run_all_verifications()

            if not args.quiet:
                runner.print_summary()

        # Save results if requested
        if args.save:
            filename = runner.save_results()
            print(f"\n📄 Results saved to: {filename}")

    except KeyboardInterrupt:
        print("\n\n⏹️  Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Verification failed with error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    # Set up asyncio event loop policy for Windows compatibility
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())