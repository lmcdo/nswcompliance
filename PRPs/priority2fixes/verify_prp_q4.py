#!/usr/bin/env python3
"""
PRP-Q4 Granular Verification Script: Legal Disclaimers & API Monitoring
Comprehensive automated testing with detailed success criteria
"""

import asyncio
import json
import time
import os
import sys
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

class PRPQ4VerificationSuite:
    """Granular verification for PRP-Q4: Legal Disclaimers & API Monitoring"""

    def __init__(self):
        self.test_results = []
        self.start_time = time.time()

    async def run_complete_verification(self) -> Dict:
        """Run all PRP-Q4 verification tests"""

        print("🛡️  PRP-Q4 GRANULAR VERIFICATION SUITE")
        print("=====================================")
        print("Testing: Legal Disclaimers & API Monitoring")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Test categories
        await self._verify_file_structure()
        await self._verify_monitoring_service()
        await self._verify_disclaimer_manager()
        await self._verify_authoritative_language_removal()
        await self._verify_api_health_monitoring()
        await self._verify_legal_framework_integration()
        await self._verify_system_positioning()

        return self._generate_final_report()

    async def _verify_file_structure(self):
        """Test 1: Verify required files exist"""
        print("📁 TESTING FILE STRUCTURE")
        print("-" * 25)

        required_files = [
            'services/nsw_api_monitoring_service.py',
            'services/legal_disclaimer_manager.py',
            'frontend-nextjs/components/disclaimers/LegalDisclaimerBanner.tsx',
            'frontend-nextjs/components/disclaimers/DisclaimerAcceptanceModal.tsx'
        ]

        for file_path in required_files:
            exists = os.path.exists(file_path)
            self._record_test(
                test_name=f"file_exists_{file_path.replace('/', '_').replace('.', '_')}",
                passed=exists,
                description=f"Required file exists: {file_path}",
                category="file_structure",
                details={"file_path": file_path, "exists": exists}
            )
            print(f"  {'✅' if exists else '❌'} {file_path}")

    async def _verify_monitoring_service(self):
        """Test 2: Verify API monitoring service"""
        print("\n📡 TESTING API MONITORING SERVICE")
        print("-" * 32)

        monitoring_path = 'services/nsw_api_monitoring_service.py'

        if not os.path.exists(monitoring_path):
            self._record_test(
                test_name="monitoring_service_missing",
                passed=False,
                description="Monitoring service file missing",
                category="monitoring_service"
            )
            print("  ❌ Monitoring service file missing - skipping tests")
            return

        try:
            # Test monitoring service import
            sys.path.append('services')
            from nsw_api_monitoring_service import NSWAPIMonitoringService, APIHealthStatus, APIHealthCheck, SystemHealthReport

            self._record_test(
                test_name="monitoring_service_import",
                passed=True,
                description="Monitoring service imports successfully",
                category="monitoring_service"
            )
            print("  ✅ Monitoring service imports successfully")

            # Test enum values
            health_statuses = [
                APIHealthStatus.HEALTHY,
                APIHealthStatus.DEGRADED,
                APIHealthStatus.UNAVAILABLE
            ]

            enum_complete = len(health_statuses) == 3

            self._record_test(
                test_name="api_health_status_enum",
                passed=enum_complete,
                description="APIHealthStatus enum has required values",
                category="monitoring_service",
                details={"enum_values": [status.value for status in health_statuses]}
            )
            print(f"  {'✅' if enum_complete else '❌'} APIHealthStatus enum complete")

            # Test monitoring service instantiation
            try:
                async with NSWAPIMonitoringService() as monitor:
                    service_instantiated = monitor is not None

                    self._record_test(
                        test_name="monitoring_service_instantiation",
                        passed=service_instantiated,
                        description="Monitoring service instantiates with context manager",
                        category="monitoring_service"
                    )
                    print("  ✅ Monitoring service instantiates correctly")

                    # Test required methods
                    required_methods = [
                        'check_system_health',
                        '_check_planning_api_health',
                        '_check_valuation_api_health'
                    ]

                    for method_name in required_methods:
                        has_method = hasattr(monitor, method_name)
                        self._record_test(
                            test_name=f"monitoring_method_{method_name}",
                            passed=has_method,
                            description=f"Monitoring service has method: {method_name}",
                            category="monitoring_service"
                        )
                        print(f"  {'✅' if has_method else '❌'} Method exists: {method_name}")

            except Exception as e:
                self._record_test(
                    test_name="monitoring_service_instantiation_error",
                    passed=False,
                    description=f"Monitoring service instantiation failed: {str(e)}",
                    category="monitoring_service",
                    details={"error": str(e)}
                )
                print(f"  ❌ Monitoring service instantiation error: {e}")

        except ImportError as e:
            self._record_test(
                test_name="monitoring_service_import_error",
                passed=False,
                description=f"Monitoring service import failed: {str(e)}",
                category="monitoring_service",
                details={"error": str(e)}
            )
            print(f"  ❌ Monitoring service import failed: {e}")

    async def _verify_disclaimer_manager(self):
        """Test 3: Verify legal disclaimer manager"""
        print("\n📜 TESTING LEGAL DISCLAIMER MANAGER")
        print("-" * 35)

        disclaimer_path = 'services/legal_disclaimer_manager.py'

        if not os.path.exists(disclaimer_path):
            self._record_test(
                test_name="disclaimer_manager_missing",
                passed=False,
                description="Disclaimer manager file missing",
                category="disclaimer_manager"
            )
            print("  ❌ Disclaimer manager file missing - skipping tests")
            return

        try:
            # Test disclaimer manager import
            sys.path.append('services')
            from legal_disclaimer_manager import LegalDisclaimerManager, LegalDisclaimer

            self._record_test(
                test_name="disclaimer_manager_import",
                passed=True,
                description="Disclaimer manager imports successfully",
                category="disclaimer_manager"
            )
            print("  ✅ Disclaimer manager imports successfully")

            # Test LegalDisclaimer dataclass
            test_disclaimer = LegalDisclaimer(
                disclaimer_type="test",
                content="Test disclaimer",
                severity="info",
                required_display=True,
                applies_to_api_data=False,
                last_updated=datetime.now()
            )

            disclaimer_dataclass_ok = test_disclaimer is not None

            self._record_test(
                test_name="legal_disclaimer_dataclass",
                passed=disclaimer_dataclass_ok,
                description="LegalDisclaimer dataclass works",
                category="disclaimer_manager"
            )
            print(f"  {'✅' if disclaimer_dataclass_ok else '❌'} LegalDisclaimer dataclass")

            # Test disclaimer manager methods
            try:
                # This would require the monitoring service, so we test the class exists
                manager_class_exists = LegalDisclaimerManager is not None

                required_methods = ['enhance_response_with_disclaimers', 'remove_authoritative_language']

                methods_exist = all(hasattr(LegalDisclaimerManager, method) for method in required_methods)

                self._record_test(
                    test_name="disclaimer_manager_methods",
                    passed=methods_exist,
                    description="Disclaimer manager has required methods",
                    category="disclaimer_manager",
                    details={"required_methods": required_methods}
                )
                print(f"  {'✅' if methods_exist else '❌'} Disclaimer manager methods exist")

            except Exception as e:
                self._record_test(
                    test_name="disclaimer_manager_methods_error",
                    passed=False,
                    description=f"Disclaimer manager method test failed: {str(e)}",
                    category="disclaimer_manager",
                    details={"error": str(e)}
                )
                print(f"  ❌ Disclaimer manager methods error: {e}")

        except ImportError as e:
            self._record_test(
                test_name="disclaimer_manager_import_error",
                passed=False,
                description=f"Disclaimer manager import failed: {str(e)}",
                category="disclaimer_manager",
                details={"error": str(e)}
            )
            print(f"  ❌ Disclaimer manager import failed: {e}")

    async def _verify_authoritative_language_removal(self):
        """Test 4: Verify authoritative language removal"""
        print("\n🔍 TESTING AUTHORITATIVE LANGUAGE REMOVAL")
        print("-" * 41)

        # List of authoritative terms that should be removed
        authoritative_terms = [
            'authoritative',
            'definitive',
            'conclusive',
            'binding',
            'determines',
            'confirms',
            'establishes',
            'certified'
        ]

        # Files to check for authoritative language
        files_to_check = [
            'frontend-nextjs/app/api/property/[address]/route.ts',
            'services/nsw_planning_api.py',
            'frontend-nextjs/components/compliance/AuthoritativeComplianceDisplay.tsx',
            'services/enhanced_compliance_api.py'
        ]

        violations_found = []
        files_checked = 0
        files_clean = 0

        for file_path in files_to_check:
            if os.path.exists(file_path):
                files_checked += 1

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()

                    file_violations = []
                    for term in authoritative_terms:
                        if term in content:
                            # Count occurrences
                            count = content.count(term)
                            file_violations.append(f"{term} ({count}x)")
                            violations_found.append(f"{file_path}: {term}")

                    if not file_violations:
                        files_clean += 1

                    self._record_test(
                        test_name=f"authoritative_language_removed_{file_path.replace('/', '_').replace('.', '_')}",
                        passed=len(file_violations) == 0,
                        description=f"Authoritative language removed from {os.path.basename(file_path)}",
                        category="authoritative_language_removal",
                        details={
                            "file_path": file_path,
                            "violations": file_violations,
                            "clean": len(file_violations) == 0
                        }
                    )

                    status = "✅" if len(file_violations) == 0 else "❌"
                    violation_text = f" ({', '.join(file_violations)})" if file_violations else ""
                    print(f"  {status} {os.path.basename(file_path)}{violation_text}")

                except Exception as e:
                    self._record_test(
                        test_name=f"authoritative_language_check_error_{file_path.replace('/', '_').replace('.', '_')}",
                        passed=False,
                        description=f"Error checking {file_path}: {str(e)}",
                        category="authoritative_language_removal",
                        details={"error": str(e), "file_path": file_path}
                    )
                    print(f"  ❌ Error checking {os.path.basename(file_path)}: {e}")

        # Overall authoritative language removal success
        language_cleanup_success = len(violations_found) == 0 and files_checked > 0

        self._record_test(
            test_name="overall_authoritative_language_cleanup",
            passed=language_cleanup_success,
            description="All authoritative language successfully removed",
            category="authoritative_language_removal",
            details={
                "files_checked": files_checked,
                "files_clean": files_clean,
                "total_violations": len(violations_found),
                "violations": violations_found
            }
        )

        print(f"  {'✅' if language_cleanup_success else '❌'} Overall cleanup: {files_clean}/{files_checked} files clean")

    async def _verify_api_health_monitoring(self):
        """Test 5: Verify API health monitoring functionality"""
        print("\n🏥 TESTING API HEALTH MONITORING")
        print("-" * 31)

        try:
            sys.path.append('services')
            from nsw_api_monitoring_service import NSWAPIMonitoringService

            # Test health monitoring functionality
            try:
                async with NSWAPIMonitoringService() as monitor:
                    # Test system health check
                    start_time = time.time()
                    health_report = await monitor.check_system_health()
                    health_check_time = int((time.time() - start_time) * 1000)

                    # Test health report structure
                    required_health_fields = [
                        'overall_status',
                        'nsw_planning_api',
                        'valuation_api',
                        'system_confidence',
                        'recommended_disclaimers',
                        'last_health_check'
                    ]

                    health_structure_ok = all(hasattr(health_report, field) for field in required_health_fields)

                    self._record_test(
                        test_name="health_report_structure",
                        passed=health_structure_ok,
                        description="Health report has required structure",
                        category="api_health_monitoring",
                        details={
                            "required_fields": required_health_fields,
                            "health_check_time_ms": health_check_time,
                            "system_confidence": health_report.system_confidence if hasattr(health_report, 'system_confidence') else None
                        }
                    )
                    print(f"  {'✅' if health_structure_ok else '❌'} Health report structure ({health_check_time}ms)")

                    if health_structure_ok:
                        # Test system confidence scoring (should be 0-1)
                        confidence_valid = (
                            isinstance(health_report.system_confidence, (int, float)) and
                            0 <= health_report.system_confidence <= 1
                        )

                        self._record_test(
                            test_name="system_confidence_scoring",
                            passed=confidence_valid,
                            description="System confidence score is valid (0-1 range)",
                            category="api_health_monitoring",
                            details={"system_confidence": health_report.system_confidence}
                        )
                        print(f"  {'✅' if confidence_valid else '❌'} System confidence: {health_report.system_confidence:.2f}")

                        # Test disclaimer generation
                        disclaimers_generated = len(health_report.recommended_disclaimers) > 0

                        self._record_test(
                            test_name="disclaimers_generated",
                            passed=disclaimers_generated,
                            description="Contextual disclaimers generated",
                            category="api_health_monitoring",
                            details={"disclaimer_count": len(health_report.recommended_disclaimers)}
                        )
                        print(f"  {'✅' if disclaimers_generated else '❌'} Disclaimers generated: {len(health_report.recommended_disclaimers)}")

                        # Test API status checking
                        api_checks_performed = (
                            hasattr(health_report.nsw_planning_api, 'status') and
                            hasattr(health_report.valuation_api, 'status')
                        )

                        self._record_test(
                            test_name="api_status_checks",
                            passed=api_checks_performed,
                            description="Individual API status checks performed",
                            category="api_health_monitoring",
                            details={
                                "planning_api_status": health_report.nsw_planning_api.status.value if api_checks_performed else None,
                                "valuation_api_status": health_report.valuation_api.status.value if api_checks_performed else None
                            }
                        )
                        print(f"  {'✅' if api_checks_performed else '❌'} API status checks performed")

            except Exception as e:
                self._record_test(
                    test_name="api_health_monitoring_error",
                    passed=False,
                    description=f"API health monitoring failed: {str(e)}",
                    category="api_health_monitoring",
                    details={"error": str(e)}
                )
                print(f"  ❌ API health monitoring error: {e}")

        except ImportError:
            print("  ⏭️  Skipping API health monitoring tests - service not available")

    async def _verify_legal_framework_integration(self):
        """Test 6: Verify legal framework integration"""
        print("\n⚖️  TESTING LEGAL FRAMEWORK INTEGRATION")
        print("-" * 37)

        try:
            sys.path.append('services')
            from legal_disclaimer_manager import LegalDisclaimerManager
            from nsw_api_monitoring_service import NSWAPIMonitoringService

            # Test legal framework integration
            try:
                async with NSWAPIMonitoringService() as monitor:
                    disclaimer_manager = LegalDisclaimerManager(monitor)

                    # Test response enhancement
                    test_response = {
                        "property": {
                            "zone": "R2",
                            "height_limit": "9m"
                        },
                        "success": True
                    }

                    enhanced_response = await disclaimer_manager.enhance_response_with_disclaimers(test_response)

                    # Test if legal framework added
                    legal_framework_added = 'legal_framework' in enhanced_response

                    self._record_test(
                        test_name="legal_framework_integration",
                        passed=legal_framework_added,
                        description="Legal framework added to API responses",
                        category="legal_framework_integration",
                        details={"legal_framework_present": legal_framework_added}
                    )
                    print(f"  {'✅' if legal_framework_added else '❌'} Legal framework integration")

                    if legal_framework_added:
                        legal_framework = enhanced_response['legal_framework']

                        # Test framework structure
                        required_framework_fields = [
                            'disclaimers',
                            'system_status',
                            'api_status',
                            'professional_verification_required',
                            'council_authority_acknowledgment'
                        ]

                        framework_structure_ok = all(field in legal_framework for field in required_framework_fields)

                        self._record_test(
                            test_name="legal_framework_structure",
                            passed=framework_structure_ok,
                            description="Legal framework has required structure",
                            category="legal_framework_integration",
                            details={"required_fields": required_framework_fields}
                        )
                        print(f"  {'✅' if framework_structure_ok else '❌'} Framework structure complete")

                        # Test professional verification requirement
                        professional_verification_required = legal_framework.get('professional_verification_required', False)

                        self._record_test(
                            test_name="professional_verification_required",
                            passed=professional_verification_required,
                            description="Professional verification requirement set",
                            category="legal_framework_integration"
                        )
                        print(f"  {'✅' if professional_verification_required else '❌'} Professional verification required")

            except Exception as e:
                self._record_test(
                    test_name="legal_framework_integration_error",
                    passed=False,
                    description=f"Legal framework integration failed: {str(e)}",
                    category="legal_framework_integration",
                    details={"error": str(e)}
                )
                print(f"  ❌ Legal framework integration error: {e}")

        except ImportError:
            print("  ⏭️  Skipping legal framework integration tests - services not available")

    async def _verify_system_positioning(self):
        """Test 7: Verify system positioning as reference tool"""
        print("\n🎯 TESTING SYSTEM POSITIONING")
        print("-" * 28)

        # Test positioning language in key files
        positioning_tests = [
            {
                'file_path': 'services/legal_disclaimer_manager.py',
                'should_contain': ['regulation reference', 'reference tool', 'guidance'],
                'should_not_contain': ['authoritative', 'definitive', 'binding']
            },
            {
                'file_path': 'README.md',
                'should_contain': ['regulation reference', 'planning guidance'],
                'should_not_contain': ['authoritative', 'official determination']
            }
        ]

        positioning_correct = True

        for test in positioning_tests:
            file_path = test['file_path']

            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()

                    # Check positive positioning terms
                    positive_terms_found = any(term in content for term in test['should_contain'])

                    # Check negative terms not present
                    negative_terms_absent = not any(term in content for term in test['should_not_contain'])

                    file_positioning_ok = positive_terms_found and negative_terms_absent

                    if not file_positioning_ok:
                        positioning_correct = False

                    self._record_test(
                        test_name=f"positioning_{os.path.basename(file_path).replace('.', '_')}",
                        passed=file_positioning_ok,
                        description=f"Correct positioning language in {os.path.basename(file_path)}",
                        category="system_positioning",
                        details={
                            "file_path": file_path,
                            "positive_terms_found": positive_terms_found,
                            "negative_terms_absent": negative_terms_absent
                        }
                    )

                    print(f"  {'✅' if file_positioning_ok else '❌'} {os.path.basename(file_path)} positioning")

                except Exception as e:
                    self._record_test(
                        test_name=f"positioning_error_{os.path.basename(file_path).replace('.', '_')}",
                        passed=False,
                        description=f"Error checking positioning in {file_path}: {str(e)}",
                        category="system_positioning",
                        details={"error": str(e), "file_path": file_path}
                    )
                    print(f"  ❌ Error checking {os.path.basename(file_path)}: {e}")

        # Overall positioning assessment
        self._record_test(
            test_name="overall_system_positioning",
            passed=positioning_correct,
            description="System correctly positioned as regulation reference tool",
            category="system_positioning"
        )
        print(f"  {'✅' if positioning_correct else '❌'} Overall system positioning")

    def _record_test(self, test_name: str, passed: bool, description: str,
                     category: str, details: Optional[Dict] = None):
        """Record a test result"""
        self.test_results.append({
            'test_name': test_name,
            'passed': passed,
            'description': description,
            'category': category,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        })

    def _generate_final_report(self) -> Dict:
        """Generate comprehensive final report"""

        total_tests = len(self.test_results)
        passed_tests = sum(1 for test in self.test_results if test['passed'])
        failed_tests = total_tests - passed_tests

        # Group by category
        category_results = {}
        for test in self.test_results:
            category = test['category']
            if category not in category_results:
                category_results[category] = {'passed': 0, 'failed': 0, 'total': 0}

            category_results[category]['total'] += 1
            if test['passed']:
                category_results[category]['passed'] += 1
            else:
                category_results[category]['failed'] += 1

        # Success criteria evaluation
        success_criteria = {
            'file_structure_complete': category_results.get('file_structure', {}).get('passed', 0) >= 2,
            'monitoring_service_functional': category_results.get('monitoring_service', {}).get('passed', 0) >= 4,
            'disclaimer_manager_working': category_results.get('disclaimer_manager', {}).get('passed', 0) >= 2,
            'authoritative_language_removed': category_results.get('authoritative_language_removal', {}).get('passed', 0) >= category_results.get('authoritative_language_removal', {}).get('total', 1),
            'api_health_monitoring_functional': category_results.get('api_health_monitoring', {}).get('passed', 0) >= 3,
            'legal_framework_integrated': category_results.get('legal_framework_integration', {}).get('passed', 0) >= 2,
            'system_positioning_correct': category_results.get('system_positioning', {}).get('passed', 0) >= 2
        }

        overall_success = (
            passed_tests >= total_tests * 0.8 and  # 80% pass rate
            all(success_criteria.values())  # All key criteria met
        )

        report = {
            'prp_id': 'PRP-Q4',
            'title': 'Legal Disclaimers & API Monitoring',
            'verification_timestamp': datetime.now().isoformat(),
            'total_verification_time_seconds': round(time.time() - self.start_time, 2),
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'pass_rate_percent': round((passed_tests / total_tests) * 100, 1) if total_tests > 0 else 0
            },
            'category_results': category_results,
            'success_criteria': success_criteria,
            'overall_success': overall_success,
            'overall_status': 'PASS' if overall_success else 'FAIL',
            'detailed_test_results': self.test_results,
            'recommendations': self._generate_recommendations(success_criteria, category_results)
        }

        return report

    def _generate_recommendations(self, success_criteria: Dict, category_results: Dict) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []

        if not success_criteria.get('file_structure_complete', False):
            recommendations.append("Create missing files: nsw_api_monitoring_service.py, legal_disclaimer_manager.py, and disclaimer components")

        if not success_criteria.get('monitoring_service_functional', False):
            recommendations.append("Implement functional API monitoring service with health checks and status reporting")

        if not success_criteria.get('disclaimer_manager_working', False):
            recommendations.append("Implement legal disclaimer manager with response enhancement capabilities")

        if not success_criteria.get('authoritative_language_removed', False):
            recommendations.append("Remove all authoritative language from system files and replace with reference language")

        if not success_criteria.get('api_health_monitoring_functional', False):
            recommendations.append("Implement comprehensive API health monitoring with confidence scoring and disclaimer generation")

        if not success_criteria.get('legal_framework_integrated', False):
            recommendations.append("Integrate legal framework into all API responses with proper disclaimer structure")

        if not success_criteria.get('system_positioning_correct', False):
            recommendations.append("Update system positioning language to clearly identify as regulation reference tool, not authoritative source")

        return recommendations

    def save_report(self, filename: Optional[str] = None) -> str:
        """Save verification report to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"PRP_Q4_VERIFICATION_REPORT_{timestamp}.json"

        report = self._generate_final_report()

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)

        return filename

async def main():
    """Run PRP-Q4 verification"""
    print("🚀 Starting PRP-Q4 Granular Verification")
    print()

    suite = PRPQ4VerificationSuite()
    report = await suite.run_complete_verification()

    # Print summary
    print(f"\n📊 VERIFICATION SUMMARY")
    print("=" * 50)
    print(f"Overall Status: {'✅ PASS' if report['overall_success'] else '❌ FAIL'}")
    print(f"Tests Passed: {report['test_summary']['passed_tests']}/{report['test_summary']['total_tests']} ({report['test_summary']['pass_rate_percent']}%)")
    print(f"Verification Time: {report['total_verification_time_seconds']}s")
    print()

    # Print category breakdown
    print("📈 Category Breakdown:")
    for category, results in report['category_results'].items():
        status = "✅" if results['passed'] == results['total'] else "⚠️" if results['passed'] > 0 else "❌"
        print(f"  {status} {category}: {results['passed']}/{results['total']}")

    print()

    # Print recommendations if any
    if report['recommendations']:
        print("💡 Recommendations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")
        print()

    # Save report
    filename = suite.save_report()
    print(f"📄 Detailed report saved: {filename}")

    return report

if __name__ == '__main__':
    asyncio.run(main())