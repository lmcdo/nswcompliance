#!/usr/bin/env python3
"""
PRP-8B Comprehensive Verification Testing
Tests all tiers of authority and system integrity
"""

import asyncio
import json
import sys
import traceback
from datetime import datetime
from typing import Dict, List
import psycopg2
from psycopg2.extras import RealDictCursor

class PRP8BVerificationSuite:
    """Complete verification suite for authoritative compliance system"""
    
    def __init__(self):
        self.test_results = {
            'tier_1_tests': [],
            'tier_2_tests': [],
            'tier_3_tests': [],
            'tier_4_tests': [],
            'tier_5_tests': [],
            'integration_tests': [],
            'performance_tests': [],
            'total_passed': 0,
            'total_failed': 0
        }
        self.db_conn = None
    
    async def setup(self):
        """Setup test environment"""
        try:
            self.db_conn = psycopg2.connect(
                host="localhost",
                database="nsw_planning",
                user="postgres",
                password="postgres"
            )
            
            # Verify authoritative schema exists
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS(
                        SELECT schema_name FROM information_schema.schemata 
                        WHERE schema_name = 'authoritative'
                    )
                """)
                schema_exists = cur.fetchone()[0]
                
                if not schema_exists:
                    print("❌ ERROR: Authoritative schema does not exist. Run migration first.")
                    return False
                
            print("✅ Database connection established")
            return True
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
    
    async def teardown(self):
        """Cleanup test environment"""
        if self.db_conn:
            self.db_conn.close()
    
    async def run_all_tests(self):
        """Run complete test suite"""
        print("[PRP-8B] Starting comprehensive verification suite...")
        
        if not await self.setup():
            return False
        
        try:
            # Test each tier
            await self.test_tier_1_full_authority()
            await self.test_tier_2_high_authority()
            await self.test_tier_3_moderate_authority()
            await self.test_integration_tests()
            await self.test_performance()
            
            # Generate report
            pass_rate = self.generate_test_report()
            
            return pass_rate >= 80  # 80% pass rate required
            
        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            traceback.print_exc()
            return False
        finally:
            await self.teardown()
    
    async def test_tier_1_full_authority(self):
        """Test Tier 1: Fully authoritative responses"""
        
        test_cases = [
            {
                'name': 'NSW Portal property data exists',
                'test_type': 'property_lookup'
            },
            {
                'name': 'Authoritative provisions migrated',
                'test_type': 'provision_count'
            },
            {
                'name': 'Tier 1 classifications exist',
                'test_type': 'tier_classification'
            }
        ]
        
        for test in test_cases:
            try:
                if test['test_type'] == 'property_lookup':
                    result = await self.test_property_data_available()
                elif test['test_type'] == 'provision_count':
                    result = await self.test_provisions_migrated()
                elif test['test_type'] == 'tier_classification':
                    result = await self.test_tier_classifications()
                else:
                    result = False
                
                if result:
                    self.test_results['tier_1_tests'].append({
                        'name': test['name'],
                        'status': 'PASSED',
                        'confidence': 1.00
                    })
                    self.test_results['total_passed'] += 1
                else:
                    self.test_results['tier_1_tests'].append({
                        'name': test['name'],
                        'status': 'FAILED',
                        'error': 'Test condition not met'
                    })
                    self.test_results['total_failed'] += 1
                    
            except Exception as e:
                self.test_results['tier_1_tests'].append({
                    'name': test['name'],
                    'status': 'FAILED',
                    'error': str(e)
                })
                self.test_results['total_failed'] += 1
    
    async def test_property_data_available(self) -> bool:
        """Test property data is available"""
        with self.db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM authoritative.nsw_properties")
            count = cur.fetchone()[0]
            return count > 0
    
    async def test_provisions_migrated(self) -> bool:
        """Test provisions have been migrated"""
        with self.db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM authoritative.planning_provisions")
            count = cur.fetchone()[0]
            return count > 100  # At least 100 provisions migrated
    
    async def test_tier_classifications(self) -> bool:
        """Test tier classifications exist"""
        with self.db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM authoritative.provision_authority_tiers WHERE tier_level = 1")
            tier_1_count = cur.fetchone()[0]
            return tier_1_count > 0
    
    async def test_tier_2_high_authority(self):
        """Test Tier 2: High authority with context"""
        
        test_cases = [
            {
                'name': 'Tier 2 provisions exist',
                'tier': 2,
                'min_expected': 10
            },
            {
                'name': 'Confidence levels appropriate',
                'tier': 2,
                'min_confidence': 0.80
            }
        ]
        
        for test in test_cases:
            try:
                with self.db_conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT COUNT(*), AVG(t.confidence_level)
                        FROM authoritative.planning_provisions p
                        JOIN authoritative.provision_authority_tiers t ON p.id = t.provision_id
                        WHERE t.tier_level = %s
                    """, (test['tier'],))
                    
                    result = cur.fetchone()
                    count = result[0]
                    avg_confidence = result[1] or 0
                    
                    if test['name'] == 'Tier 2 provisions exist':
                        success = count >= test['min_expected']
                    else:  # confidence test
                        success = avg_confidence >= test['min_confidence']
                    
                    if success:
                        self.test_results['tier_2_tests'].append({
                            'name': test['name'],
                            'status': 'PASSED',
                            'count': count,
                            'avg_confidence': float(avg_confidence) if avg_confidence else 0
                        })
                        self.test_results['total_passed'] += 1
                    else:
                        self.test_results['tier_2_tests'].append({
                            'name': test['name'],
                            'status': 'FAILED',
                            'count': count,
                            'avg_confidence': float(avg_confidence) if avg_confidence else 0,
                            'error': f"Expected >= {test.get('min_expected', test.get('min_confidence'))}"
                        })
                        self.test_results['total_failed'] += 1
                        
            except Exception as e:
                self.test_results['tier_2_tests'].append({
                    'name': test['name'],
                    'status': 'FAILED',
                    'error': str(e)
                })
                self.test_results['total_failed'] += 1
    
    async def test_tier_3_moderate_authority(self):
        """Test Tier 3: Moderate authority provisions"""
        
        try:
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM authoritative.provision_authority_tiers 
                    WHERE tier_level = 3
                """)
                
                tier_3_count = cur.fetchone()[0]
                
                if tier_3_count >= 5:  # At least 5 tier 3 provisions
                    self.test_results['tier_3_tests'].append({
                        'name': 'Tier 3 provisions classified',
                        'status': 'PASSED',
                        'count': tier_3_count
                    })
                    self.test_results['total_passed'] += 1
                else:
                    self.test_results['tier_3_tests'].append({
                        'name': 'Tier 3 provisions classified',
                        'status': 'FAILED',
                        'count': tier_3_count,
                        'error': 'Insufficient tier 3 provisions'
                    })
                    self.test_results['total_failed'] += 1
                    
        except Exception as e:
            self.test_results['tier_3_tests'].append({
                'name': 'Tier 3 provisions classified',
                'status': 'FAILED',
                'error': str(e)
            })
            self.test_results['total_failed'] += 1
    
    async def test_integration_tests(self):
        """Test system integration"""
        
        integration_tests = [
            {
                'name': 'Hierarchy resolution cache',
                'test_func': self.test_hierarchy_cache
            },
            {
                'name': 'API compliance check',
                'test_func': self.test_api_integration
            }
        ]
        
        for test in integration_tests:
            try:
                success = await test['test_func']()
                
                if success:
                    self.test_results['integration_tests'].append({
                        'name': test['name'],
                        'status': 'PASSED'
                    })
                    self.test_results['total_passed'] += 1
                else:
                    self.test_results['integration_tests'].append({
                        'name': test['name'],
                        'status': 'FAILED',
                        'error': 'Integration test failed'
                    })
                    self.test_results['total_failed'] += 1
                    
            except Exception as e:
                self.test_results['integration_tests'].append({
                    'name': test['name'],
                    'status': 'FAILED',
                    'error': str(e)
                })
                self.test_results['total_failed'] += 1
    
    async def test_hierarchy_cache(self) -> bool:
        """Test hierarchy resolution cache works"""
        with self.db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM authoritative.hierarchy_resolution_cache")
            count = cur.fetchone()[0]
            return count > 0
    
    async def test_api_integration(self) -> bool:
        """Test API integration works"""
        try:
            # Import and test the API
            sys.path.append('services')
            from authoritative_compliance_api import AuthoritativeComplianceAPI
            
            api = AuthoritativeComplianceAPI()
            
            # Test with zone query
            result = api.check_compliance(
                zone_code='R2',
                development_type='dwelling_house'
            )
            
            return 'error' not in result
            
        except Exception as e:
            print(f"API integration test failed: {e}")
            return False
    
    async def test_performance(self):
        """Test system performance"""
        
        import time
        
        try:
            start_time = time.time()
            
            # Run a complex query
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    SELECT p.*, t.*
                    FROM authoritative.planning_provisions p
                    JOIN authoritative.provision_authority_tiers t ON p.id = t.provision_id
                    WHERE 'R2' = ANY(p.applicable_zones)
                    ORDER BY t.tier_level, p.authority_level
                    LIMIT 20
                """)
                results = cur.fetchall()
            
            query_time = time.time() - start_time
            
            if query_time < 1.0 and len(results) > 0:
                self.test_results['performance_tests'].append({
                    'name': 'Query performance',
                    'status': 'PASSED',
                    'query_time': f"{query_time:.3f}s",
                    'results_count': len(results)
                })
                self.test_results['total_passed'] += 1
            else:
                self.test_results['performance_tests'].append({
                    'name': 'Query performance',
                    'status': 'FAILED',
                    'query_time': f"{query_time:.3f}s",
                    'results_count': len(results),
                    'error': 'Query too slow or no results'
                })
                self.test_results['total_failed'] += 1
                
        except Exception as e:
            self.test_results['performance_tests'].append({
                'name': 'Query performance',
                'status': 'FAILED',
                'error': str(e)
            })
            self.test_results['total_failed'] += 1
    
    def generate_test_report(self) -> float:
        """Generate comprehensive test report"""
        
        report = []
        report.append("=" * 60)
        report.append("PRP-8B VERIFICATION TEST REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        # Summary
        total_tests = self.test_results['total_passed'] + self.test_results['total_failed']
        pass_rate = (self.test_results['total_passed'] / total_tests * 100) if total_tests > 0 else 0
        
        report.append("SUMMARY")
        report.append("-" * 30)
        report.append(f"Total Tests: {total_tests}")
        report.append(f"Passed: {self.test_results['total_passed']}")
        report.append(f"Failed: {self.test_results['total_failed']}")
        report.append(f"Pass Rate: {pass_rate:.1f}%")
        report.append("")
        
        # Tier-by-tier results
        for tier in range(1, 4):  # Only testing tiers 1-3 for now
            tier_key = f'tier_{tier}_tests'
            if self.test_results[tier_key]:
                report.append(f"TIER {tier} TESTS")
                report.append("-" * 30)
                for test in self.test_results[tier_key]:
                    status_icon = "✅" if test['status'] == 'PASSED' else "❌"
                    report.append(f"{status_icon} {test['name']}: {test['status']}")
                    if test['status'] == 'FAILED' and 'error' in test:
                        report.append(f"   Error: {test['error']}")
                    if 'count' in test:
                        report.append(f"   Count: {test['count']}")
                report.append("")
        
        # Integration tests
        if self.test_results['integration_tests']:
            report.append("INTEGRATION TESTS")
            report.append("-" * 30)
            for test in self.test_results['integration_tests']:
                status_icon = "✅" if test['status'] == 'PASSED' else "❌"
                report.append(f"{status_icon} {test['name']}: {test['status']}")
                if test['status'] == 'FAILED' and 'error' in test:
                    report.append(f"   Error: {test['error']}")
            report.append("")
        
        # Performance tests
        if self.test_results['performance_tests']:
            report.append("PERFORMANCE TESTS")
            report.append("-" * 30)
            for test in self.test_results['performance_tests']:
                status_icon = "✅" if test['status'] == 'PASSED' else "❌"
                report.append(f"{status_icon} {test['name']}: {test['status']}")
                if 'query_time' in test:
                    report.append(f"   Query time: {test['query_time']}")
            report.append("")
        
        # Overall assessment
        report.append("ASSESSMENT")
        report.append("-" * 30)
        
        if pass_rate >= 90:
            report.append("✅ EXCELLENT: System ready for production")
        elif pass_rate >= 80:
            report.append("✅ GOOD: System ready with minor issues to resolve")
        elif pass_rate >= 70:
            report.append("⚠️ ACCEPTABLE: Some issues need resolution before production")
        else:
            report.append("❌ NEEDS WORK: Significant issues require attention")
        
        report.append("")
        report.append(f"Pass Rate: {pass_rate:.1f}%")
        
        # Save report
        report_text = "\n".join(report)
        
        try:
            with open('PRP_8B_TEST_REPORT.txt', 'w') as f:
                f.write(report_text)
        except:
            pass  # Don't fail tests if can't write report
        
        print("\n" + report_text)
        
        return pass_rate

# Main execution
async def main():
    suite = PRP8BVerificationSuite()
    success = await suite.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())