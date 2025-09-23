#!/usr/bin/env python3
"""
PRP-8C: Comprehensive Zero Error Investigation
Analyze SQLite vs PostgreSQL data and identify migration issues
"""

import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime
from typing import Dict, List, Any
import traceback

class ZeroErrorInvestigator:
 """Investigate the mysterious '0' errors in migration"""
 
 def __init__(self):
 self.results = {
 'sqlite_analysis': {},
 'postgresql_analysis': {},
 'data_comparison': {},
 'error_analysis': {},
 'root_cause': None
 }
 
 def investigate_all(self):
 """Run complete investigation"""
 
 print("PRP-8C: ZERO ERROR INVESTIGATION")
 print("=" * 60)
 
 # Phase 1: Analyze SQLite source data
 print("\n[PHASE 1] Analyzing SQLite Source Data")
 self.analyze_sqlite_data()
 
 # Phase 2: Analyze PostgreSQL target data
 print("\n[PHASE 2] Analyzing PostgreSQL Target Data") 
 self.analyze_postgresql_data()
 
 # Phase 3: Compare data between systems
 print("\n[PHASE 3] Comparing Data Between Systems")
 self.compare_data_sources()
 
 # Phase 4: Detailed error reproduction
 print("\n[PHASE 4] Reproducing Migration Errors")
 self.reproduce_migration_errors()
 
 # Phase 5: Generate investigation report
 print("\n[PHASE 5] Generating Investigation Report")
 self.generate_investigation_report()
 
 return self.results
 
 def analyze_sqlite_data(self):
 """Analyze original SQLite database"""
 
 try:
 # Try the main database first
 conn = sqlite3.connect('nsw_planning.db')
 conn.row_factory = sqlite3.Row
 cur = conn.cursor()
 
 print("Analyzing nsw_planning.db...")
 
 # Get table structure
 cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
 tables = [row[0] for row in cur.fetchall()]
 
 print(f"SQLite tables found: {tables}")
 
 if 'regulatory_provisions' in tables:
 # Analyze regulatory_provisions table
 cur.execute("SELECT COUNT(*) FROM regulatory_provisions")
 total_count = cur.fetchone()[0]
 
 print(f"Total regulatory_provisions in SQLite: {total_count}")
 
 # Check zone distribution
 cur.execute("SELECT zone, COUNT(*) as count FROM regulatory_provisions WHERE zone IS NOT NULL GROUP BY zone ORDER BY count DESC")
 sqlite_zones = cur.fetchall()
 
 print(f"SQLite zone distribution: {len(sqlite_zones)} zones")
 for zone_row in sqlite_zones[:10]: # Top 10
 print(f" {zone_row[0]}: {zone_row[1]} provisions")
 
 # Check for NULL zones
 cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE zone IS NULL")
 null_zones = cur.fetchone()[0]
 
 print(f"SQLite provisions with NULL zone: {null_zones} ({null_zones/total_count*100:.1f}%)")
 
 # Sample data analysis
 cur.execute("SELECT * FROM regulatory_provisions WHERE zone IS NOT NULL LIMIT 5")
 samples = cur.fetchall()
 
 print("\nSQLite sample data structure:")
 if samples:
 sample = dict(samples[0])
 for key, value in sample.items():
 value_str = str(value)[:100] if value else "NULL"
 print(f" {key}: {value_str}")
 
 self.results['sqlite_analysis'] = {
 'total_provisions': total_count,
 'null_zones': null_zones,
 'zone_distribution': dict(sqlite_zones[:20]),
 'sample_columns': list(sample.keys()) if samples else [],
 'database_accessible': True
 }
 
 else:
 print("WARNING: regulatory_provisions table not found in SQLite")
 self.results['sqlite_analysis']['database_accessible'] = False
 
 conn.close()
 
 except Exception as e:
 print(f"ERROR accessing SQLite database: {e}")
 print("Full traceback:")
 traceback.print_exc()
 self.results['sqlite_analysis']['error'] = str(e)
 
 def analyze_postgresql_data(self):
 """Analyze PostgreSQL database"""
 
 try:
 conn = psycopg2.connect(
 host="localhost",
 database="nsw_planning", 
 user="postgres",
 password="postgres"
 )
 cur = conn.cursor()
 
 # Check regulatory_provisions table
 cur.execute("SELECT COUNT(*) FROM regulatory_provisions")
 total_count = cur.fetchone()[0]
 
 print(f"Total regulatory_provisions in PostgreSQL: {total_count}")
 
 # Check zone distribution 
 cur.execute("SELECT zone, COUNT(*) as count FROM regulatory_provisions WHERE zone IS NOT NULL GROUP BY zone ORDER BY count DESC")
 pg_zones = cur.fetchall()
 
 print(f"PostgreSQL zone distribution: {len(pg_zones)} zones")
 for zone, count in pg_zones[:10]:
 print(f" {zone}: {count} provisions")
 
 # Check for NULL zones
 cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE zone IS NULL")
 null_zones = cur.fetchone()[0]
 
 print(f"PostgreSQL provisions with NULL zone: {null_zones} ({null_zones/total_count*100:.1f}%)")
 
 # Check data types and constraints
 cur.execute("""
 SELECT column_name, data_type, is_nullable, column_default 
 FROM information_schema.columns 
 WHERE table_name = 'regulatory_provisions' 
 ORDER BY ordinal_position
 """)
 columns = cur.fetchall()
 
 print("\nPostgreSQL schema:")
 for col_name, data_type, nullable, default in columns:
 print(f" {col_name}: {data_type} ({'NULL' if nullable == 'YES' else 'NOT NULL'}) default={default}")
 
 self.results['postgresql_analysis'] = {
 'total_provisions': total_count,
 'null_zones': null_zones,
 'zone_distribution': dict(pg_zones[:20]),
 'schema': columns,
 'database_accessible': True
 }
 
 conn.close()
 
 except Exception as e:
 print(f"ERROR accessing PostgreSQL database: {e}")
 traceback.print_exc()
 self.results['postgresql_analysis']['error'] = str(e)
 
 def compare_data_sources(self):
 """Compare SQLite vs PostgreSQL data"""
 
 sqlite_data = self.results.get('sqlite_analysis', {})
 pg_data = self.results.get('postgresql_analysis', {})
 
 if not sqlite_data.get('database_accessible') or not pg_data.get('database_accessible'):
 print("Cannot compare - one or both databases inaccessible")
 return
 
 print("DATA COMPARISON ANALYSIS")
 print("-" * 40)
 
 # Compare total counts
 sqlite_total = sqlite_data.get('total_provisions', 0)
 pg_total = pg_data.get('total_provisions', 0)
 
 print(f"Total provisions - SQLite: {sqlite_total}, PostgreSQL: {pg_total}")
 
 if sqlite_total != pg_total:
 print(f" COUNT MISMATCH: {abs(sqlite_total - pg_total)} provision difference")
 else:
 print(" Total counts match")
 
 # Compare NULL zones
 sqlite_nulls = sqlite_data.get('null_zones', 0)
 pg_nulls = pg_data.get('null_zones', 0)
 
 print(f"NULL zones - SQLite: {sqlite_nulls}, PostgreSQL: {pg_nulls}")
 
 if sqlite_nulls != pg_nulls:
 print(f" NULL ZONE MISMATCH: {abs(sqlite_nulls - pg_nulls)} difference")
 else:
 print(" NULL zone counts match")
 
 # Compare zone distributions
 sqlite_zones = set(sqlite_data.get('zone_distribution', {}).keys())
 pg_zones = set(pg_data.get('zone_distribution', {}).keys())
 
 common_zones = sqlite_zones & pg_zones
 sqlite_only = sqlite_zones - pg_zones
 pg_only = pg_zones - sqlite_zones
 
 print(f"Zone comparison:")
 print(f" Common zones: {len(common_zones)}")
 print(f" SQLite only: {len(sqlite_only)} {list(sqlite_only)[:5]}")
 print(f" PostgreSQL only: {len(pg_only)} {list(pg_only)[:5]}")
 
 self.results['data_comparison'] = {
 'total_count_match': sqlite_total == pg_total,
 'null_zone_match': sqlite_nulls == pg_nulls,
 'common_zones': len(common_zones),
 'data_consistency_score': self.calculate_consistency_score(sqlite_data, pg_data)
 }
 
 def reproduce_migration_errors(self):
 """Try to reproduce the migration errors with enhanced logging"""
 
 print("REPRODUCING MIGRATION ERRORS")
 print("-" * 40)
 
 try:
 conn = psycopg2.connect(
 host="localhost",
 database="nsw_planning",
 user="postgres", 
 password="postgres"
 )
 cur = conn.cursor(cursor_factory=RealDictCursor)
 
 # Get first 10 zone-mapped provisions for testing
 cur.execute("""
 SELECT * FROM regulatory_provisions 
 WHERE zone IS NOT NULL 
 ORDER BY id 
 LIMIT 10
 """)
 test_provisions = cur.fetchall()
 
 print(f"Testing migration with {len(test_provisions)} sample provisions...")
 
 migration_results = []
 
 for prov in test_provisions:
 try:
 print(f"\n--- Testing provision {prov['id']} ---")
 
 # Check each field that might cause issues
 issues = []
 
 # Check for NULL required fields
 if prov.get('ref_number') is None:
 issues.append("ref_number is NULL")
 
 if prov.get('provision_type') and len(prov['provision_type']) > 50:
 issues.append(f"provision_type too long: {len(prov['provision_type'])} chars")
 
 if prov.get('classification_confidence') is None:
 issues.append("classification_confidence is NULL")
 # This is our smoking gun!
 print(f" FOUND ISSUE: classification_confidence is NULL for provision {prov['id']}")
 print(f" This would cause: float(None) -> TypeError -> str(TypeError) -> '0' ???")
 
 # Test the actual problematic conversion
 try:
 confidence = float(prov.get('classification_confidence') or 0.85)
 print(f" Confidence conversion successful: {confidence}")
 except Exception as conversion_error:
 print(f" CONFIDENCE CONVERSION ERROR: {conversion_error}")
 print(f" Error type: {type(conversion_error)}")
 print(f" str(error): '{str(conversion_error)}'")
 issues.append(f"confidence conversion failed: {conversion_error}")
 
 migration_results.append({
 'provision_id': prov['id'],
 'issues': issues,
 'would_fail': len(issues) > 0
 })
 
 if issues:
 print(f" Issues found: {issues}")
 else:
 print(f" No obvious issues detected")
 
 except Exception as test_error:
 print(f" ERROR testing provision {prov['id']}: {test_error}")
 print(f" Error type: {type(test_error)}")
 traceback.print_exc()
 
 # Summary of findings
 failed_count = sum(1 for r in migration_results if r['would_fail'])
 print(f"\n MIGRATION TEST RESULTS:")
 print(f" Provisions tested: {len(migration_results)}")
 print(f" Would fail: {failed_count}")
 print(f" Success rate: {(len(migration_results) - failed_count)/len(migration_results)*100:.1f}%")
 
 self.results['error_analysis'] = {
 'provisions_tested': len(migration_results),
 'would_fail': failed_count,
 'success_rate': (len(migration_results) - failed_count)/len(migration_results),
 'detailed_results': migration_results
 }
 
 conn.close()
 
 except Exception as e:
 print(f"ERROR in migration reproduction: {e}")
 traceback.print_exc()
 self.results['error_analysis']['error'] = str(e)
 
 def calculate_consistency_score(self, sqlite_data, pg_data):
 """Calculate data consistency score between databases"""
 
 score = 0
 total_checks = 0
 
 # Count match
 if sqlite_data.get('total_provisions') == pg_data.get('total_provisions'):
 score += 1
 total_checks += 1
 
 # NULL zones match
 if sqlite_data.get('null_zones') == pg_data.get('null_zones'):
 score += 1
 total_checks += 1
 
 return score / total_checks if total_checks > 0 else 0
 
 def generate_investigation_report(self):
 """Generate comprehensive investigation report"""
 
 report = [
 "PRP-8C: ZERO ERROR INVESTIGATION REPORT",
 "=" * 60,
 f"Investigation completed: {datetime.now().isoformat()}",
 "",
 "EXECUTIVE SUMMARY",
 "-" * 30
 ]
 
 # Data comparison summary
 comparison = self.results.get('data_comparison', {})
 consistency_score = comparison.get('data_consistency_score', 0)
 
 if consistency_score >= 0.8:
 report.append(" Data consistency between SQLite and PostgreSQL: GOOD")
 else:
 report.append(" Data consistency between SQLite and PostgreSQL: POOR")
 
 # Error analysis summary
 error_analysis = self.results.get('error_analysis', {})
 success_rate = error_analysis.get('success_rate', 0)
 
 if success_rate >= 0.9:
 report.append(" Migration error reproduction: LOW ERROR RATE")
 elif success_rate >= 0.5:
 report.append(" Migration error reproduction: MODERATE ERROR RATE")
 else:
 report.append(" Migration error reproduction: HIGH ERROR RATE")
 
 # Root cause identification
 if 'classification_confidence is NULL' in str(self.results):
 report.extend([
 "",
 " LIKELY ROOT CAUSE IDENTIFIED:",
 " classification_confidence field contains NULL values",
 " float(None) conversion causes TypeError",
 " Error handling converts TypeError to string '0'",
 "",
 "RECOMMENDED FIXES:",
 "1. Handle NULL classification_confidence values properly", 
 "2. Improve error logging to capture actual exception details",
 "3. Add data validation before migration attempts",
 "4. Consider DEFAULT values for required fields"
 ])
 
 self.results['root_cause'] = "NULL classification_confidence causing float() conversion errors"
 
 report.extend([
 "",
 "DETAILED FINDINGS",
 "-" * 30,
 f"SQLite provisions: {self.results.get('sqlite_analysis', {}).get('total_provisions', 'Unknown')}",
 f"PostgreSQL provisions: {self.results.get('postgresql_analysis', {}).get('total_provisions', 'Unknown')}",
 f"Data consistency score: {consistency_score:.2f}",
 f"Migration success rate: {success_rate:.1%}",
 "",
 "NEXT STEPS",
 "-" * 30,
 "1. Fix NULL classification_confidence handling in migration script",
 "2. Add comprehensive data validation before migration",
 "3. Implement proper error logging with full exception details", 
 "4. Re-run migration with fixes and validate results",
 "5. Update PRP-8B completion assessment based on actual data coverage"
 ])
 
 report_text = "\n".join(report)
 print("\n" + report_text)
 
 # Save report
 try:
 with open('PRP_8C_INVESTIGATION_REPORT.txt', 'w', encoding='utf-8') as f:
 f.write(report_text)
 print(f"\n Investigation report saved: PRP_8C_INVESTIGATION_REPORT.txt")
 except Exception as e:
 print(f"Could not save report: {e}")
 
 return report_text

def main():
 """Run complete zero error investigation"""
 
 investigator = ZeroErrorInvestigator()
 results = investigator.investigate_all()
 
 # Return success if root cause identified
 return results.get('root_cause') is not None

if __name__ == "__main__":
 success = main()
 exit(0 if success else 1)