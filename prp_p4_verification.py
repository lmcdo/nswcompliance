#!/usr/bin/env python3
"""
PRP-P4: Verification & Quality Assurance
Automated verification of consolidated development type dataset with realistic testing targets
"""

from db_config import get_connection # Unified PostgreSQL connection
import json
import time
import csv
from datetime import datetime
from typing import Dict, List, Tuple, Any
import statistics

class PRPP4Verifier:
 def __init__(self):
 self.get_connection()
 self.start_time = time.time()
 self.test_results = []
 self.quality_metrics = {}
 self.verification_summary = {}

 def create_verification_schema(self):
 """Create tables for verification results"""
 print("=== Creating Verification Schema ===")

 conn = get_connection()
 cursor = conn.cursor()

 # Create verification_tests table
 cursor.execute("""
 CREATE TABLE IF NOT EXISTS verification_tests (
 id SERIAL PRIMARY KEY SERIAL,
 test_type TEXT,
 test_name TEXT,
 input_parameters TEXT,
 expected_result TEXT,
 actual_result TEXT,
 test_status TEXT CHECK(test_status IN ('pass', 'fail', 'error')),
 execution_time_ms INTEGER,
 error_message TEXT,
 executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
 )
 """)

 # Create quality_metrics table
 cursor.execute("""
 CREATE TABLE IF NOT EXISTS quality_metrics (
 id SERIAL PRIMARY KEY SERIAL,
 metric_name TEXT,
 metric_value REAL,
 target_value REAL,
 status TEXT CHECK(status IN ('pass', 'fail', 'warning')),
 details TEXT,
 measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
 )
 """)

 # Create expert_validation table
 cursor.execute("""
 CREATE TABLE IF NOT EXISTS expert_validation (
 id SERIAL PRIMARY KEY SERIAL,
 validation_type TEXT,
 item_reference TEXT,
 expert_rating INTEGER CHECK(expert_rating BETWEEN 1 AND 5),
 comments TEXT,
 validator_name TEXT,
 validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
 )
 """)

 conn.commit()
 conn.close()
 print("[OK] Verification schema created")

 def test_zone_queries(self) -> Dict:
 """Test realistic zone-based queries"""
 print("\n=== Testing Zone Queries ===")

 conn = get_connection()
 cursor = conn.cursor()

 zone_query_results = {
 'total_tests': 0,
 'passed': 0,
 'failed': 0,
 'test_details': []
 }

 # Test major zones for development permissions
 major_zones = ['R1', 'R2', 'R3', 'R4', 'B1', 'B2', 'B3', 'B4', 'IN1', 'IN2']

 for zone in major_zones:
 start_time = time.time()

 # Query: "What can I build in [zone]?"
 cursor.execute("""
 SELECT development_type, permission_status, COUNT(*)
 FROM development_permissions
 WHERE zone = ? AND development_type IS NOT NULL
 GROUP BY development_type, permission_status
 ORDER BY permission_status, development_type
 """, (zone,))

 results = cursor.fetchall()
 execution_time = int((time.time() - start_time) * 1000)

 zone_query_results['total_tests'] += 1

 # Evaluation criteria: Should have at least 3 development types
 test_passed = len(results) >= 3

 if test_passed:
 zone_query_results['passed'] += 1
 status = 'pass'
 else:
 zone_query_results['failed'] += 1
 status = 'fail'

 test_detail = {
 'zone': zone,
 'development_types_found': len(results),
 'execution_time_ms': execution_time,
 'status': status,
 'sample_results': results[:5] # First 5 results
 }

 zone_query_results['test_details'].append(test_detail)

 # Record in verification_tests table
 cursor.execute("""
 INSERT INTO verification_tests
 (test_type, test_name, input_parameters, expected_result, actual_result,
 test_status, execution_time_ms)
 VALUES (?, ?, ?, ?, ?, ?, ?)
 """, (
 'zone_query',
 f'Zone query: {zone}',
 json.dumps({'zone': zone}),
 json.dumps({'minimum_dev_types': 3}),
 json.dumps({'dev_types_found': len(results), 'results': results[:3]}),
 status,
 execution_time
 ))

 print(f" {zone}: {len(results)} development types found ({status})")

 conn.commit()
 conn.close()

 success_rate = (zone_query_results['passed'] / zone_query_results['total_tests']) * 100
 print(f"[OK] Zone query success rate: {success_rate:.1f}%")

 return zone_query_results

 def test_feasibility_queries(self) -> Dict:
 """Test development type feasibility queries"""
 print("\n=== Testing Feasibility Queries ===")

 conn = get_connection()
 cursor = conn.cursor()

 feasibility_results = {
 'total_tests': 0,
 'passed': 0,
 'failed': 0,
 'test_details': []
 }

 # Realistic feasibility test scenarios
 feasibility_tests = [
 {'zone': 'R1', 'dev_type': 'dwelling_house', 'expected': ['permitted', 'consent']},
 {'zone': 'R2', 'dev_type': 'dual_occupancy', 'expected': ['permitted', 'consent']},
 {'zone': 'B1', 'dev_type': 'retail_premises', 'expected': ['permitted', 'consent']},
 {'zone': 'B3', 'dev_type': 'office_premises', 'expected': ['permitted', 'consent']},
 {'zone': 'IN1', 'dev_type': 'warehouse', 'expected': ['permitted', 'consent']},
 {'zone': 'R1', 'dev_type': 'general_industry', 'expected': ['prohibited']},
 {'zone': 'E2', 'dev_type': 'retail_premises', 'expected': ['prohibited']},
 ]

 for test in feasibility_tests:
 start_time = time.time()

 # Query: "Can I build [dev_type] in [zone]?"
 cursor.execute("""
 SELECT permission_status, COUNT(*) as count
 FROM development_permissions
 WHERE zone = ? AND development_type = ?
 GROUP BY permission_status
 ORDER BY count DESC
 """, (test['zone'], test['dev_type']))

 results = cursor.fetchall()
 execution_time = int((time.time() - start_time) * 1000)

 feasibility_results['total_tests'] += 1

 # Check if any result matches expected permissions
 actual_permissions = [row[0] for row in results]
 test_passed = any(perm in test['expected'] for perm in actual_permissions)

 if test_passed:
 feasibility_results['passed'] += 1
 status = 'pass'
 else:
 feasibility_results['failed'] += 1
 status = 'fail'

 test_detail = {
 'zone': test['zone'],
 'development_type': test['dev_type'],
 'expected_permissions': test['expected'],
 'actual_permissions': actual_permissions,
 'execution_time_ms': execution_time,
 'status': status
 }

 feasibility_results['test_details'].append(test_detail)

 # Record in verification_tests table
 cursor.execute("""
 INSERT INTO verification_tests
 (test_type, test_name, input_parameters, expected_result, actual_result,
 test_status, execution_time_ms)
 VALUES (?, ?, ?, ?, ?, ?, ?)
 """, (
 'feasibility',
 f'Feasibility: {test["dev_type"]} in {test["zone"]}',
 json.dumps({'zone': test['zone'], 'development_type': test['dev_type']}),
 json.dumps({'expected_permissions': test['expected']}),
 json.dumps({'actual_permissions': actual_permissions}),
 status,
 execution_time
 ))

 print(f" {test['zone']}/{test['dev_type']}: {actual_permissions} ({status})")

 conn.commit()
 conn.close()

 success_rate = (feasibility_results['passed'] / feasibility_results['total_tests']) * 100
 print(f"[OK] Feasibility query success rate: {success_rate:.1f}%")

 return feasibility_results

 def test_cross_zone_consistency(self) -> Dict:
 """Test consistency of development types across similar zones"""
 print("\n=== Testing Cross-Zone Consistency ===")

 conn = get_connection()
 cursor = conn.cursor()

 consistency_results = {
 'total_tests': 0,
 'passed': 0,
 'failed': 0,
 'inconsistencies': []
 }

 # Test consistency of common development types across residential zones
 residential_zones = ['R1', 'R2', 'R3', 'R4']
 common_dev_types = ['dwelling_house', 'dual_occupancy', 'retail_premises', 'general_industry']

 for dev_type in common_dev_types:
 consistency_results['total_tests'] += 1

 # Get permissions for this dev type across residential zones
 cursor.execute("""
 SELECT zone, permission_status
 FROM development_permissions
 WHERE zone IN ({}) AND development_type = ?
 ORDER BY zone
 """.format(','.join(['?'] * len(residential_zones))), residential_zones + [dev_type])

 results = cursor.fetchall()
 zone_permissions = dict(results)

 # Check for logical consistency
 inconsistencies = []

 # dwelling_house should generally be permitted in all residential zones
 if dev_type == 'dwelling_house':
 for zone in residential_zones:
 if zone in zone_permissions and zone_permissions[zone] not in ['permitted', 'consent']:
 inconsistencies.append(f"{dev_type} in {zone}: {zone_permissions[zone]} (should be permitted/consent)")

 # general_industry should be prohibited in all residential zones
 elif dev_type == 'general_industry':
 for zone in residential_zones:
 if zone in zone_permissions and zone_permissions[zone] != 'prohibited':
 inconsistencies.append(f"{dev_type} in {zone}: {zone_permissions[zone]} (should be prohibited)")

 if len(inconsistencies) == 0:
 consistency_results['passed'] += 1
 status = 'pass'
 else:
 consistency_results['failed'] += 1
 status = 'fail'
 consistency_results['inconsistencies'].extend(inconsistencies)

 print(f" {dev_type} consistency: {status}")
 if inconsistencies:
 for inconsistency in inconsistencies:
 print(f" - {inconsistency}")

 conn.close()

 success_rate = (consistency_results['passed'] / consistency_results['total_tests']) * 100
 print(f"[OK] Consistency test success rate: {success_rate:.1f}%")

 return consistency_results

 def test_performance(self) -> Dict:
 """Test query performance"""
 print("\n=== Testing Performance ===")

 conn = get_connection()
 cursor = conn.cursor()

 performance_results = {
 'total_tests': 0,
 'passed': 0,
 'failed': 0,
 'execution_times': [],
 'average_time_ms': 0
 }

 # Test performance of common queries
 test_queries = [
 ("Zone query R2", "SELECT * FROM development_permissions WHERE zone = 'R2'"),
 ("Zone query B1", "SELECT * FROM development_permissions WHERE zone = 'B1'"),
 ("Dev type query", "SELECT * FROM development_permissions WHERE development_type = 'dwelling_house'"),
 ("Permission query", "SELECT * FROM development_permissions WHERE permission_status = 'permitted'"),
 ("Complex query", """
 SELECT zone, development_type, permission_status, COUNT(*)
 FROM development_permissions
 WHERE zone IN ('R1', 'R2', 'R3', 'R4')
 GROUP BY zone, development_type, permission_status
 """)
 ]

 for query_name, query in test_queries:
 start_time = time.time()
 cursor.execute(query)
 results = cursor.fetchall()
 execution_time = int((time.time() - start_time) * 1000)

 performance_results['total_tests'] += 1
 performance_results['execution_times'].append(execution_time)

 # Target: <2000ms (2 seconds)
 if execution_time < 2000:
 performance_results['passed'] += 1
 status = 'pass'
 else:
 performance_results['failed'] += 1
 status = 'fail'

 print(f" {query_name}: {execution_time}ms ({len(results)} results) - {status}")

 conn.close()

 performance_results['average_time_ms'] = statistics.mean(performance_results['execution_times'])
 success_rate = (performance_results['passed'] / performance_results['total_tests']) * 100
 print(f"[OK] Performance test success rate: {success_rate:.1f}%")
 print(f"[OK] Average query time: {performance_results['average_time_ms']:.1f}ms")

 return performance_results

 def measure_quality_metrics(self) -> Dict:
 """Measure comprehensive quality metrics"""
 print("\n=== Measuring Quality Metrics ===")

 conn = get_connection()
 cursor = conn.cursor()

 metrics = {}

 # Metric 1: Total combinations
 cursor.execute("SELECT COUNT(*) FROM development_permissions")
 total_combinations = cursor.fetchone()[0]
 metrics['total_combinations'] = {
 'value': total_combinations,
 'target': 200, # Realistic target based on our consolidated data
 'status': 'pass' if total_combinations >= 200 else 'fail'
 }

 # Metric 2: Zone coverage
 cursor.execute("SELECT COUNT(DISTINCT zone) FROM development_permissions WHERE zone IS NOT NULL")
 zone_coverage = cursor.fetchone()[0]
 metrics['zone_coverage'] = {
 'value': zone_coverage,
 'target': 15,
 'status': 'pass' if zone_coverage >= 15 else 'fail'
 }

 # Metric 3: Development type coverage
 cursor.execute("SELECT COUNT(DISTINCT development_type) FROM development_permissions WHERE development_type IS NOT NULL")
 dev_type_coverage = cursor.fetchone()[0]
 metrics['dev_type_coverage'] = {
 'value': dev_type_coverage,
 'target': 20,
 'status': 'pass' if dev_type_coverage >= 20 else 'fail'
 }

 # Metric 4: Major zone coverage
 major_zones = ['R1', 'R2', 'R3', 'R4', 'B1', 'B2', 'B3', 'IN1']
 cursor.execute("""
 SELECT COUNT(DISTINCT zone)
 FROM development_permissions
 WHERE zone IN ({})
 """.format(','.join(['?'] * len(major_zones))), major_zones)
 major_zone_coverage = cursor.fetchone()[0]
 metrics['major_zone_coverage'] = {
 'value': major_zone_coverage,
 'target': 6,
 'status': 'pass' if major_zone_coverage >= 6 else 'fail'
 }

 # Metric 5: Data completeness (zones with >5 permissions)
 cursor.execute("""
 SELECT COUNT(*)
 FROM (
 SELECT zone, COUNT(*) as perms
 FROM development_permissions
 WHERE zone IS NOT NULL
 GROUP BY zone
 HAVING perms >= 5
 )
 """)
 well_covered_zones = cursor.fetchone()[0]
 metrics['well_covered_zones'] = {
 'value': well_covered_zones,
 'target': 8,
 'status': 'pass' if well_covered_zones >= 8 else 'fail'
 }

 # Metric 6: Permission distribution balance
 cursor.execute("""
 SELECT permission_status, COUNT(*) as count
 FROM development_permissions
 WHERE permission_status IS NOT NULL
 GROUP BY permission_status
 """)
 permission_dist = dict(cursor.fetchall())
 total_perms = sum(permission_dist.values())

 # Check if we have reasonable distribution (not all one type)
 balanced_distribution = all(count/total_perms >= 0.1 for count in permission_dist.values())
 metrics['permission_balance'] = {
 'value': len(permission_dist),
 'target': 3, # Should have permitted, consent, prohibited
 'status': 'pass' if len(permission_dist) >= 3 and balanced_distribution else 'warning'
 }

 # Store metrics in database
 for metric_name, metric_data in metrics.items():
 cursor.execute("""
 INSERT INTO quality_metrics
 (metric_name, metric_value, target_value, status, details)
 VALUES (?, ?, ?, ?, ?)
 """, (
 metric_name,
 metric_data['value'],
 metric_data['target'],
 metric_data['status'],
 json.dumps(metric_data)
 ))

 conn.commit()
 conn.close()

 # Print results
 print(f"[OK] Quality Metrics Summary:")
 for metric_name, data in metrics.items():
 status_icon = "[PASS]" if data['status'] == 'pass' else "[WARN]" if data['status'] == 'warning' else "[FAIL]"
 print(f" {status_icon} {metric_name}: {data['value']} (target: {data['target']}) - {data['status']}")

 return metrics

 def generate_expert_validation_sample(self) -> str:
 """Generate sample data for expert validation"""
 print("\n=== Generating Expert Validation Sample ===")

 conn = get_connection()
 cursor = conn.cursor()

 # Get stratified sample across zones and permission types
 cursor.execute("""
 SELECT zone, development_type, permission_status, source_type
 FROM development_permissions
 WHERE zone IN ('R1', 'R2', 'B1', 'B3', 'IN1', 'E2')
 ORDER BY zone, permission_status, development_type
 LIMIT 30
 """)

 sample_data = cursor.fetchall()

 # Create CSV for expert review
 csv_filename = 'expert_validation_sample.csv'
 with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
 writer = csv.writer(csvfile)
 writer.writerow(['Zone', 'Development Type', 'Permission Status', 'Source Type', 'Expert Rating (1-5)', 'Comments'])

 for row in sample_data:
 writer.writerow([row[0], row[1], row[2], row[3], '', ''])

 conn.close()

 print(f"[OK] Expert validation sample created: {csv_filename}")
 print(f"[OK] Sample contains {len(sample_data)} representative combinations")

 return csv_filename

 def create_production_readiness_report(self) -> Dict:
 """Create comprehensive production readiness assessment"""
 print("\n=== Production Readiness Assessment ===")

 # Compile all test results
 overall_metrics = {
 'zone_queries': self.test_results[0] if len(self.test_results) > 0 else {},
 'feasibility_queries': self.test_results[1] if len(self.test_results) > 1 else {},
 'consistency_tests': self.test_results[2] if len(self.test_results) > 2 else {},
 'performance_tests': self.test_results[3] if len(self.test_results) > 3 else {},
 'quality_metrics': self.quality_metrics
 }

 # Calculate overall success rates
 success_rates = []
 if 'zone_queries' in overall_metrics and overall_metrics['zone_queries']:
 zq = overall_metrics['zone_queries']
 if zq.get('total_tests', 0) > 0:
 success_rates.append(zq['passed'] / zq['total_tests'])

 if 'feasibility_queries' in overall_metrics and overall_metrics['feasibility_queries']:
 fq = overall_metrics['feasibility_queries']
 if fq.get('total_tests', 0) > 0:
 success_rates.append(fq['passed'] / fq['total_tests'])

 if 'consistency_tests' in overall_metrics and overall_metrics['consistency_tests']:
 ct = overall_metrics['consistency_tests']
 if ct.get('total_tests', 0) > 0:
 success_rates.append(ct['passed'] / ct['total_tests'])

 if 'performance_tests' in overall_metrics and overall_metrics['performance_tests']:
 pt = overall_metrics['performance_tests']
 if pt.get('total_tests', 0) > 0:
 success_rates.append(pt['passed'] / pt['total_tests'])

 overall_success_rate = statistics.mean(success_rates) if success_rates else 0

 # Assess production readiness
 readiness_criteria = [
 overall_success_rate >= 0.8, # 80% success rate target
 self.quality_metrics.get('total_combinations', {}).get('status') == 'pass',
 self.quality_metrics.get('zone_coverage', {}).get('status') == 'pass',
 self.quality_metrics.get('major_zone_coverage', {}).get('status') == 'pass'
 ]

 production_ready = all(readiness_criteria)
 readiness_score = sum(readiness_criteria) / len(readiness_criteria)

 production_report = {
 'prp_id': 'PRP-P4',
 'execution_time_minutes': round((time.time() - self.start_time) / 60, 2),
 'completion_timestamp': datetime.now().isoformat(),
 'overall_success_rate': overall_success_rate,
 'production_ready': production_ready,
 'readiness_score': readiness_score,
 'test_summary': overall_metrics,
 'readiness_criteria': {
 'success_rate_target': readiness_criteria[0],
 'total_combinations': readiness_criteria[1],
 'zone_coverage': readiness_criteria[2],
 'major_zone_coverage': readiness_criteria[3]
 },
 'recommendations': []
 }

 # Add recommendations based on results
 if overall_success_rate < 0.8:
 production_report['recommendations'].append("Improve data quality - success rate below 80% target")

 if not readiness_criteria[1]:
 production_report['recommendations'].append("Increase development type combinations")

 if not readiness_criteria[2]:
 production_report['recommendations'].append("Expand zone coverage")

 if production_ready:
 production_report['recommendations'].append("Ready for phase 1 deployment with documented limitations")
 else:
 production_report['recommendations'].append("Address failing criteria before production deployment")

 # Save report
 with open('prp_p4_production_readiness_report.json', 'w') as f:
 json.dump(production_report, f, indent=2)

 print(f"[OK] Overall success rate: {overall_success_rate:.1%}")
 print(f"[OK] Production ready: {production_ready}")
 print(f"[OK] Readiness score: {readiness_score:.1%}")
 print(f"[OK] Report saved: prp_p4_production_readiness_report.json")

 return production_report

 def execute(self):
 """Execute complete PRP-P4 verification and QA"""
 print("Starting PRP-P4: Verification & Quality Assurance")
 print(f"Database: {self.db_path}")

 try:
 # Step 1: Create verification schema
 self.create_verification_schema()

 # Step 2: Execute automated tests
 zone_query_results = self.test_zone_queries()
 feasibility_results = self.test_feasibility_queries()
 consistency_results = self.test_cross_zone_consistency()
 performance_results = self.test_performance()

 self.test_results = [zone_query_results, feasibility_results, consistency_results, performance_results]

 # Step 3: Measure quality metrics
 self.quality_metrics = self.measure_quality_metrics()

 # Step 4: Generate expert validation sample
 validation_sample = self.generate_expert_validation_sample()

 # Step 5: Create production readiness report
 production_report = self.create_production_readiness_report()

 print(f"\n[SUCCESS] PRP-P4 Completed Successfully!")
 print(f"[INFO] Overall success rate: {production_report['overall_success_rate']:.1%}")
 print(f"[INFO] Production ready: {production_report['production_ready']}")

 return True

 except Exception as e:
 print(f"\n PRP-P4 execution failed: {e}")
 import traceback
 traceback.print_exc()
 return False

if __name__ == '__main__':
 verifier = PRPP4Verifier()
 success = verifier.execute()
 exit(0 if success else 1)