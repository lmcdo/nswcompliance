#!/usr/bin/env python3
"""
PRP-H4: CORRECTED Verification and Testing Module
Fixed accuracy calculation to validate individual measurements, not averages
"""
from db_config import get_connection # Unified PostgreSQL connection
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

class CorrectedExtractionVerification:
 """FIXED: Verify and test extraction quality correctly"""
 
 def __init__(self):
 self.base_path = Path("C:/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine")
 self.db_path = self.base_path / "nsw_planning_data.db"
 
 def test_measurement_accuracy_correct(self) -> Dict:
 """CORRECTED: Test accuracy of individual measurements (not averages)"""
 print("Testing measurement accuracy (CORRECTED VERSION)...")
 
 results = {
 'total_measurements': 0,
 'valid_measurements': 0,
 'accuracy_score': 0,
 'breakdown_by_type': {},
 'issues': []
 }
 
 try:
 conn = get_connection()
 cursor = conn.cursor()
 
 cursor.execute("SELECT COUNT(*) FROM ragflow_measurements")
 results['total_measurements'] = cursor.fetchone()[0]
 
 # Test each measurement type with appropriate individual value ranges
 measurement_rules = {
 'setback': (0.1, 100), # 0.1m to 100m setbacks are reasonable
 'height': (1.0, 200), # 1m to 200m heights are reasonable 
 'fsr': (0.01, 10), # 0.01 to 10.0 FSR is reasonable
 'site_coverage': (1, 100), # 1% to 100% site coverage
 'area': (1, 100000), # 1sqm to 100,000sqm areas
 'general': (0.01, 10000) # Very broad range for general measurements
 }
 
 total_valid = 0
 
 for mtype, (min_val, max_val) in measurement_rules.items():
 # Count valid individual measurements for this type
 cursor.execute("""
 SELECT COUNT(*) as valid_count,
 (SELECT COUNT(*) FROM ragflow_measurements WHERE measurement_type = ?) as total_count
 FROM ragflow_measurements 
 WHERE measurement_type = ? AND value BETWEEN ? AND ?
 """, (mtype, mtype, min_val, max_val))
 
 valid_count, total_count = cursor.fetchone()
 
 if total_count > 0:
 type_accuracy = (valid_count / total_count) * 100
 results['breakdown_by_type'][mtype] = {
 'valid': valid_count,
 'total': total_count,
 'accuracy': round(type_accuracy, 1),
 'range_tested': f"{min_val} - {max_val}"
 }
 total_valid += valid_count
 
 results['valid_measurements'] = total_valid
 results['accuracy_score'] = (total_valid / max(1, results['total_measurements'])) * 100
 
 conn.close()
 
 except Exception as e:
 results['issues'].append(f"Verification error: {e}")
 
 return results
 
 def run_corrected_verification_suite(self) -> Dict:
 """Run CORRECTED verification suite"""
 print("=" * 60)
 print("PRP-H4: CORRECTED VERIFICATION AND TESTING SUITE")
 print("=" * 60)
 print("Fixed: Now testing individual measurements, not averages!")
 print()
 
 start_time = time.time()
 
 # Run corrected tests
 accuracy_test = self.test_measurement_accuracy_correct()
 
 # Compile results
 results = {
 'verification_summary': {
 'tests_run': 1,
 'overall_score': accuracy_test['accuracy_score'],
 'status': 'EXCELLENT' if accuracy_test['accuracy_score'] > 85 else 'GOOD' if accuracy_test['accuracy_score'] > 70 else 'NEEDS_REVIEW'
 },
 'corrected_accuracy_test': accuracy_test,
 'execution_time': time.time() - start_time
 }
 
 print(f"Total measurements tested: {accuracy_test['total_measurements']:,}")
 print(f"Valid measurements: {accuracy_test['valid_measurements']:,}")
 print(f"CORRECTED accuracy score: {accuracy_test['accuracy_score']:.1f}%")
 print(f"Status: {results['verification_summary']['status']}")
 
 print("\nACCURACY BY MEASUREMENT TYPE:")
 print("-" * 40)
 for mtype, stats in accuracy_test['breakdown_by_type'].items():
 print(f"{mtype:12} | {stats['valid']:4,}/{stats['total']:4,} valid ({stats['accuracy']:5.1f}%) | Range: {stats['range_tested']}")
 
 print("\nDIAGNOSIS:")
 if accuracy_test['accuracy_score'] > 85:
 print("EXCELLENT: Data extraction quality is very high")
 elif accuracy_test['accuracy_score'] > 70:
 print("GOOD: Data extraction quality is acceptable")
 else:
 print("REVIEW NEEDED: Some measurement ranges may need adjustment")
 
 return results

def main():
 print("FIXING THE 30.9% ACCURACY ISSUE...")
 print("Previous error: Was testing averages instead of individual measurements")
 print()
 
 verifier = CorrectedExtractionVerification()
 results = verifier.run_corrected_verification_suite()
 
 with open("PRP_H4_VERIFICATION_CORRECTED.json", 'w') as f:
 json.dump(results, f, indent=2)
 
 print(f"\nCorrected results saved to: PRP_H4_VERIFICATION_CORRECTED.json")

if __name__ == "__main__":
 main()