#!/usr/bin/env python3
"""
Automated Verification Scripts for REVISED PRP-Q1 through PRP-Q4
Granular proof of completion for each Priority 2 Fix (leveraging NSW API integration)

REVISED FOCUS:
- PRP-Q1: Live Compliance Calculator Engine
- PRP-Q2: Development Pathway Intelligence
- PRP-Q3: Advanced Compliance Rules Engine
- PRP-Q4: Legal Disclaimers & API Monitoring
"""

import sqlite3
import json
import time
import re
import asyncio
import os
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Any
import requests

class RevisedPRPVerificationSuite:
    def __init__(self):
        self.db_path = 'nsw_planning.db'
        self.verification_results = {}
        self.start_time = time.time()

    async def run_all_verifications(self) -> Dict:
        """Run all PRP-Q verifications in sequence"""
        print("REVISED PRP-Q SERIES VERIFICATION SUITE")
        print("=====================================")
        print("Leveraging existing NSW Planning API integration")
        print(f"Started at: {datetime.now().isoformat()}")

        # Verify each PRP in sequence
        self.verification_results['PRP-Q1'] = await self.verify_prp_q1_live_compliance()
        self.verification_results['PRP-Q2'] = await self.verify_prp_q2_pathway_intelligence()
        self.verification_results['PRP-Q3'] = await self.verify_prp_q3_advanced_compliance()
        self.verification_results['PRP-Q4'] = await self.verify_prp_q4_legal_disclaimers()

        # Generate summary
        self.verification_results['summary'] = self.generate_verification_summary()

        return self.verification_results

    async def verify_prp_q1_live_compliance(self) -> Dict:
        """Verify PRP-Q1: Live Compliance Calculator Engine"""
        print("\n=== VERIFYING PRP-Q1: LIVE COMPLIANCE CALCULATOR ===")

        verification = {
            'prp_id': 'PRP-Q1',
            'title': 'Live Compliance Calculator Engine',
            'tests': [],
            'success_criteria_met': {},
            'overall_status': 'pending',
            'performance_metrics': {}
        }

        # Test 1: Check if live compliance engine exists
        engine_exists = os.path.exists('services/live_compliance_engine.py')
        verification['tests'].append({
            'test_name': 'live_compliance_engine_exists',
            'passed': engine_exists,
            'description': 'Live compliance calculation engine file created'
        })

        if engine_exists:
            # Test 2: Test live FSR calculation using NSW API data
            try:
                # Import and test the live compliance engine
                sys.path.append('services')
                from live_compliance_engine import LiveComplianceEngine

                engine = LiveComplianceEngine()

                # Test with a known Inner West address
                test_address = "45 Liverpool Street, Ashfield NSW 2131"
                test_proposal = {
                    'gross_floor_area': 180,
                    'height': 8.5
                }

                start_time = time.time()
                result = await engine.calculate_compliance(test_address, test_proposal)
                calculation_time = int((time.time() - start_time) * 1000)

                # Verify performance requirement (<100ms)
                performance_ok = calculation_time < 100
                verification['tests'].append({
                    'test_name': 'live_calculation_performance',
                    'passed': performance_ok,
                    'actual_time_ms': calculation_time,
                    'target_time_ms': 100,
                    'description': 'Live calculation <100ms response time'
                })

                # Verify API data usage
                uses_api_data = (
                    result.fsr_compliance and 'nsw_api' in result.fsr_compliance.data_source or
                    result.height_compliance and 'nsw_api' in result.height_compliance.data_source
                )
                verification['tests'].append({
                    'test_name': 'uses_live_api_data',
                    'passed': uses_api_data,
                    'description': 'Uses live NSW API data for calculations'
                })

                verification['performance_metrics'] = {
                    'calculation_time_ms': calculation_time,
                    'uses_live_data': uses_api_data,
                    'overall_compliant_calculated': result.overall_compliant if result else False
                }

            except ImportError as e:
                verification['tests'].append({
                    'test_name': 'live_engine_import',
                    'passed': False,
                    'error': str(e),
                    'description': 'Live compliance engine import failed'
                })

        # Test 3: Check API endpoint exists
        api_exists = os.path.exists('frontend-nextjs/app/api/compliance/live-check/route.ts')
        verification['tests'].append({
            'test_name': 'live_compliance_api_exists',
            'passed': api_exists,
            'description': 'Live compliance API endpoint created'
        })

        # Success criteria evaluation
        tests_passed = sum(1 for test in verification['tests'] if test['passed'])
        total_tests = len(verification['tests'])

        verification['success_criteria_met'] = {
            'live_api_integration': engine_exists,
            'performance_target': verification['performance_metrics'].get('calculation_time_ms', 999) < 100 if verification.get('performance_metrics') else False,
            'api_data_usage': verification['performance_metrics'].get('uses_live_data', False) if verification.get('performance_metrics') else False,
            'tests_passed_ratio': f"{tests_passed}/{total_tests}"
        }

        verification['overall_status'] = 'PASS' if tests_passed == total_tests else 'FAIL'
        return verification

    async def verify_prp_q2_pathway_intelligence(self) -> Dict:
        """Verify PRP-Q2: Development Pathway Intelligence"""
        print("\n=== VERIFYING PRP-Q2: PATHWAY INTELLIGENCE ===")

        verification = {
            'prp_id': 'PRP-Q2',
            'title': 'Development Pathway Intelligence',
            'tests': [],
            'success_criteria_met': {},
            'overall_status': 'pending',
            'pathway_accuracy': {}
        }

        # Test 1: Check pathway intelligence engine exists
        engine_exists = os.path.exists('services/pathway_intelligence_engine.py')
        verification['tests'].append({
            'test_name': 'pathway_engine_exists',
            'passed': engine_exists,
            'description': 'Pathway intelligence engine file created'
        })

        if engine_exists:
            # Test 2: Test pathway determination accuracy
            try:
                sys.path.append('services')
                from pathway_intelligence_engine import PathwayIntelligenceEngine, DevelopmentPathway

                engine = PathwayIntelligenceEngine()

                # Test scenarios
                test_cases = [
                    {
                        'address': '45 Liverpool Street, Ashfield NSW 2131',
                        'development_type': 'dwelling_house',
                        'details': {'height': 7.5},
                        'expected': DevelopmentPathway.EXEMPT
                    },
                    {
                        'address': '15 Norton Street, Leichhardt NSW 2040',
                        'development_type': 'dwelling_house',
                        'details': {'height': 8.5, 'fsr': 0.5},
                        'expected': DevelopmentPathway.COMPLYING
                    }
                ]

                correct_predictions = 0
                total_tests = len(test_cases)

                for test_case in test_cases:
                    try:
                        result = await engine.determine_pathway(
                            test_case['address'],
                            test_case['development_type'],
                            test_case['details']
                        )

                        if result.recommended_pathway == test_case['expected']:
                            correct_predictions += 1

                        # Test response time (<500ms)
                        performance_ok = result.processing_time_ms < 500

                    except Exception as e:
                        print(f"Pathway test failed: {e}")

                accuracy = (correct_predictions / total_tests) * 100 if total_tests > 0 else 0

                verification['tests'].append({
                    'test_name': 'pathway_accuracy',
                    'passed': accuracy >= 90,
                    'accuracy_percent': accuracy,
                    'target_accuracy': 90,
                    'description': '90%+ pathway determination accuracy'
                })

                verification['pathway_accuracy'] = {
                    'correct_predictions': correct_predictions,
                    'total_tests': total_tests,
                    'accuracy_percent': accuracy
                }

            except ImportError as e:
                verification['tests'].append({
                    'test_name': 'pathway_engine_import',
                    'passed': False,
                    'error': str(e),
                    'description': 'Pathway engine import failed'
                })

        # Test 3: Check API endpoint exists
        api_exists = os.path.exists('frontend-nextjs/app/api/pathway/determine/route.ts')
        verification['tests'].append({
            'test_name': 'pathway_api_exists',
            'passed': api_exists,
            'description': 'Pathway determination API endpoint created'
        })

        # Success criteria evaluation
        tests_passed = sum(1 for test in verification['tests'] if test['passed'])
        total_tests = len(verification['tests'])

        verification['success_criteria_met'] = {
            'pathway_engine_created': engine_exists,
            'accuracy_target': verification['pathway_accuracy'].get('accuracy_percent', 0) >= 90 if verification.get('pathway_accuracy') else False,
            'api_endpoint_created': api_exists,
            'tests_passed_ratio': f"{tests_passed}/{total_tests}"
        }

        verification['overall_status'] = 'PASS' if tests_passed == total_tests else 'FAIL'
        return verification

    async def verify_prp_q3_advanced_compliance(self) -> Dict:
        """Verify PRP-Q3: Advanced Compliance Rules Engine"""
        print("\n=== VERIFYING PRP-Q3: ADVANCED COMPLIANCE RULES ===")

        verification = {
            'prp_id': 'PRP-Q3',
            'title': 'Advanced Compliance Rules Engine',
            'tests': [],
            'success_criteria_met': {},
            'overall_status': 'pending',
            'multi_factor_metrics': {}
        }

        # Test 1: Check advanced compliance engine exists
        engine_exists = os.path.exists('services/advanced_compliance_engine.py')
        verification['tests'].append({
            'test_name': 'advanced_engine_exists',
            'passed': engine_exists,
            'description': 'Advanced compliance engine file created'
        })

        if engine_exists:
            # Test 2: Test multi-factor compliance assessment
            try:
                sys.path.append('services')
                from advanced_compliance_engine import AdvancedComplianceEngine, DevelopmentProposal

                engine = AdvancedComplianceEngine()

                # Test comprehensive compliance check
                test_address = "45 Liverpool Street, Ashfield NSW 2131"
                test_proposal = DevelopmentProposal(
                    development_type='dwelling_house',
                    gross_floor_area=200,
                    building_area=120,
                    height=8.5,
                    storeys=2,
                    dwelling_count=1,
                    proposed_parking_spaces=2,
                    landscaped_area=100,
                    setbacks={'front': 6.0, 'side': 1.5, 'rear': 6.0}
                )

                start_time = time.time()
                result = await engine.assess_advanced_compliance(test_address, test_proposal)
                assessment_time = int((time.time() - start_time) * 1000)

                # Test performance requirement (<200ms)
                performance_ok = assessment_time < 200
                verification['tests'].append({
                    'test_name': 'multi_factor_performance',
                    'passed': performance_ok,
                    'actual_time_ms': assessment_time,
                    'target_time_ms': 200,
                    'description': 'Multi-factor assessment <200ms'
                })

                # Test compliance factors covered
                factors_assessed = sum([
                    1 if result.site_coverage else 0,
                    1 if result.parking_compliance else 0,
                    1 if result.landscaping_compliance else 0,
                    1 if result.setback_compliance else 0
                ])

                verification['tests'].append({
                    'test_name': 'compliance_factors',
                    'passed': factors_assessed >= 3,
                    'factors_assessed': factors_assessed,
                    'target_factors': 3,
                    'description': 'Multiple compliance factors assessed'
                })

                verification['multi_factor_metrics'] = {
                    'assessment_time_ms': assessment_time,
                    'factors_assessed': factors_assessed,
                    'overall_compliant': result.overall_compliant,
                    'compliance_score': result.compliance_score
                }

            except ImportError as e:
                verification['tests'].append({
                    'test_name': 'advanced_engine_import',
                    'passed': False,
                    'error': str(e),
                    'description': 'Advanced compliance engine import failed'
                })

        # Test 3: Check API endpoint exists
        api_exists = os.path.exists('frontend-nextjs/app/api/compliance/advanced-check/route.ts')
        verification['tests'].append({
            'test_name': 'advanced_compliance_api_exists',
            'passed': api_exists,
            'description': 'Advanced compliance API endpoint created'
        })

        # Success criteria evaluation
        tests_passed = sum(1 for test in verification['tests'] if test['passed'])
        total_tests = len(verification['tests'])

        verification['success_criteria_met'] = {
            'advanced_engine_created': engine_exists,
            'performance_target': verification['multi_factor_metrics'].get('assessment_time_ms', 999) < 200 if verification.get('multi_factor_metrics') else False,
            'multi_factor_assessment': verification['multi_factor_metrics'].get('factors_assessed', 0) >= 3 if verification.get('multi_factor_metrics') else False,
            'tests_passed_ratio': f"{tests_passed}/{total_tests}"
        }

        verification['overall_status'] = 'PASS' if tests_passed == total_tests else 'FAIL'
        return verification

    async def verify_prp_q4_legal_disclaimers(self) -> Dict:
        """Verify PRP-Q4: Legal Disclaimers & API Monitoring"""
        print("\n=== VERIFYING PRP-Q4: LEGAL DISCLAIMERS & API MONITORING ===")

        verification = {
            'prp_id': 'PRP-Q4',
            'title': 'Legal Disclaimers & API Monitoring',
            'tests': [],
            'success_criteria_met': {},
            'overall_status': 'pending',
            'legal_compliance': {}
        }

        # Test 1: Check API monitoring service exists
        monitoring_exists = os.path.exists('services/nsw_api_monitoring_service.py')
        verification['tests'].append({
            'test_name': 'api_monitoring_exists',
            'passed': monitoring_exists,
            'description': 'NSW API monitoring service created'
        })

        # Test 2: Check legal disclaimer manager exists
        disclaimer_exists = os.path.exists('services/legal_disclaimer_manager.py')
        verification['tests'].append({
            'test_name': 'disclaimer_manager_exists',
            'passed': disclaimer_exists,
            'description': 'Legal disclaimer manager created'
        })

        # Test 3: Check for authoritative language removal
        authoritative_language_check = self.check_authoritative_language_removed()
        verification['tests'].append({
            'test_name': 'authoritative_language_removed',
            'passed': authoritative_language_check['clean'],
            'violations_found': authoritative_language_check['violations'],
            'description': 'Authoritative language removed from system'
        })

        # Test 4: Test API health monitoring
        if monitoring_exists:
            try:
                sys.path.append('services')
                from nsw_api_monitoring_service import NSWAPIMonitoringService

                async with NSWAPIMonitoringService() as monitor:
                    health_report = await monitor.check_system_health()

                    # Verify health report structure
                    has_required_fields = all([
                        hasattr(health_report, 'overall_status'),
                        hasattr(health_report, 'nsw_planning_api'),
                        hasattr(health_report, 'recommended_disclaimers'),
                        hasattr(health_report, 'system_confidence')
                    ])

                    verification['tests'].append({
                        'test_name': 'api_health_monitoring',
                        'passed': has_required_fields,
                        'system_confidence': health_report.system_confidence if has_required_fields else 0,
                        'description': 'API health monitoring functional'
                    })

                    verification['legal_compliance'] = {
                        'system_confidence': health_report.system_confidence if has_required_fields else 0,
                        'disclaimer_count': len(health_report.recommended_disclaimers) if has_required_fields else 0,
                        'api_status': health_report.overall_status.value if has_required_fields else 'unknown'
                    }

            except ImportError as e:
                verification['tests'].append({
                    'test_name': 'monitoring_import',
                    'passed': False,
                    'error': str(e),
                    'description': 'API monitoring service import failed'
                })

        # Success criteria evaluation
        tests_passed = sum(1 for test in verification['tests'] if test['passed'])
        total_tests = len(verification['tests'])

        verification['success_criteria_met'] = {
            'monitoring_service_created': monitoring_exists,
            'disclaimer_manager_created': disclaimer_exists,
            'authoritative_language_removed': authoritative_language_check['clean'],
            'api_health_functional': verification['legal_compliance'].get('disclaimer_count', 0) > 0 if verification.get('legal_compliance') else False,
            'tests_passed_ratio': f"{tests_passed}/{total_tests}"
        }

        verification['overall_status'] = 'PASS' if tests_passed == total_tests else 'FAIL'
        return verification

    def check_authoritative_language_removed(self) -> Dict:
        """Check for removal of authoritative language"""

        authoritative_terms = [
            'authoritative', 'definitive', 'conclusive', 'binding',
            'determines', 'confirms', 'establishes', 'certified'
        ]

        violations = []
        files_to_check = [
            'frontend-nextjs/app/api/property/[address]/route.ts',
            'services/nsw_planning_api.py',
            'frontend-nextjs/components/compliance/AuthoritativeComplianceDisplay.tsx'
        ]

        for file_path in files_to_check:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                        for term in authoritative_terms:
                            if term in content:
                                violations.append(f"{file_path}: '{term}' found")
                except Exception as e:
                    violations.append(f"Error checking {file_path}: {e}")

        return {
            'clean': len(violations) == 0,
            'violations': violations
        }

    def generate_verification_summary(self) -> Dict:
        """Generate overall verification summary"""

        summary = {
            'total_prps': 4,
            'prps_passed': 0,
            'prps_failed': 0,
            'overall_success': False,
            'completion_timestamp': datetime.now().isoformat(),
            'total_verification_time_seconds': round(time.time() - self.start_time, 2),
            'prp_status_summary': {}
        }

        for prp_id, result in self.verification_results.items():
            if prp_id != 'summary':
                status = result.get('overall_status', 'UNKNOWN')
                summary['prp_status_summary'][prp_id] = {
                    'status': status,
                    'title': result.get('title', 'Unknown'),
                    'tests_passed': sum(1 for test in result.get('tests', []) if test.get('passed', False)),
                    'total_tests': len(result.get('tests', []))
                }

                if status == 'PASS':
                    summary['prps_passed'] += 1
                else:
                    summary['prps_failed'] += 1

        summary['overall_success'] = summary['prps_passed'] == summary['total_prps']

        return summary

    def save_verification_report(self, filename: str = None):
        """Save verification results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"PRP_Q_VERIFICATION_REPORT_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.verification_results, f, indent=2, default=str)

        print(f"\nVerification report saved to: {filename}")
        return filename

async def main():
    """Main verification execution"""

    print("REVISED PRP-Q SERIES AUTOMATED VERIFICATION")
    print("==========================================")
    print("Verifying PRPs that leverage existing NSW Planning API integration")

    suite = RevisedPRPVerificationSuite()
    results = await suite.run_all_verifications()

    # Print summary
    summary = results.get('summary', {})
    print(f"\n=== VERIFICATION SUMMARY ===")
    print(f"Total PRPs: {summary.get('total_prps', 0)}")
    print(f"PRPs Passed: {summary.get('prps_passed', 0)}")
    print(f"PRPs Failed: {summary.get('prps_failed', 0)}")
    print(f"Overall Success: {summary.get('overall_success', False)}")
    print(f"Verification Time: {summary.get('total_verification_time_seconds', 0)}s")

    for prp_id, status in summary.get('prp_status_summary', {}).items():
        print(f"{prp_id}: {status['status']} ({status['tests_passed']}/{status['total_tests']} tests passed)")

    # Save report
    report_file = suite.save_verification_report()

    return results

if __name__ == '__main__':
    asyncio.run(main())