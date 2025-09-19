#!/usr/bin/env python3
"""
PRP-M1 Dry Run Test Framework
============================
Tests the execution framework without making any changes
"""

import os
import sys
import json
import time
from db_config import get_connection  # Unified PostgreSQL connection
import psycopg2
from datetime import datetime
from pathlib import Path

class PRP_M1_DryRunTester:
    """Test the PRP-M1 execution framework with dry run"""
    
    def __init__(self):
        self.test_results = []
        self.start_time = datetime.now()
        
    def test_database_connections(self):
        """Test database connectivity"""
        print("🔍 Testing Database Connections")
        print("=" * 40)
        
        results = {
            'sqlite': False,
            'postgresql': False,
            'errors': []
        }
        
        # Test SQLite
        try:
            if os.path.exists('./nsw_planning.db'):
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                conn.close()
                
                print(f"✅ SQLite: Connected successfully ({table_count} tables)")
                results['sqlite'] = True
            else:
                print("❌ SQLite: Database file not found")
                results['errors'].append("SQLite database file missing")
        except Exception as e:
            print(f"❌ SQLite: Connection failed - {e}")
            results['errors'].append(f"SQLite error: {e}")
        
        # Test PostgreSQL
        try:
            conn = psycopg2.connect(
                host="localhost",
                database="nsw_planning", 
                user="postgres",
                password="postgres"
            )
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            conn.close()
            
            print(f"✅ PostgreSQL: Connected successfully")
            print(f"   Version: {version.split()[1]}")
            results['postgresql'] = True
        except Exception as e:
            print(f"❌ PostgreSQL: Connection failed - {e}")
            results['errors'].append(f"PostgreSQL error: {e}")
        
        return results
    
    def test_sqlite_data_structure(self):
        """Test SQLite data structure and content"""
        print("\n🗄️  Testing SQLite Data Structure")
        print("=" * 40)
        
        results = {
            'tables_present': [],
            'missing_tables': [],
            'row_counts': {},
            'data_quality': {}
        }
        
        expected_tables = ['documents', 'regulatory_provisions', 'quantitative_standards']
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Check tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            actual_tables = [row[0] for row in cursor.fetchall()]
            
            for table in expected_tables:
                if table in actual_tables:
                    results['tables_present'].append(table)
                    print(f"✅ Table found: {table}")
                    
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    results['row_counts'][table] = count
                    print(f"   Rows: {count:,}")
                else:
                    results['missing_tables'].append(table)
                    print(f"❌ Missing table: {table}")
            
            # Test data quality on regulatory_provisions
            if 'regulatory_provisions' in results['tables_present']:
                print(f"\n📊 Data Quality Analysis:")
                
                # Check for null text
                cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE provision_text IS NULL OR provision_text = ''")
                null_text = cursor.fetchone()[0]
                results['data_quality']['null_text_provisions'] = null_text
                print(f"   Provisions with no text: {null_text:,}")
                
                # Check zone assignments
                cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE zone IS NOT NULL")
                with_zones = cursor.fetchone()[0]
                results['data_quality']['provisions_with_zones'] = with_zones
                total = results['row_counts']['regulatory_provisions']
                zone_percentage = (with_zones / total * 100) if total > 0 else 0
                print(f"   Provisions with zones: {with_zones:,} ({zone_percentage:.1f}%)")
                
                # Check for the R2 bias issue
                cursor.execute("SELECT zone, COUNT(*) FROM regulatory_provisions WHERE zone IS NOT NULL GROUP BY zone ORDER BY COUNT(*) DESC LIMIT 5")
                zone_distribution = cursor.fetchall()
                print(f"   Top zones by provision count:")
                for zone, count in zone_distribution:
                    print(f"     {zone}: {count:,} provisions")
                results['data_quality']['zone_distribution'] = zone_distribution
            
            conn.close()
            
        except Exception as e:
            print(f"❌ SQLite analysis failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def test_postgresql_schema_creation(self):
        """Test PostgreSQL schema creation (dry run)"""
        print("\n🐘 Testing PostgreSQL Schema Creation")
        print("=" * 40)
        
        results = {
            'schema_readable': False,
            'syntax_valid': False,
            'estimated_objects': 0
        }
        
        try:
            # Check if schema file exists and is readable
            schema_file = './research_assistant_schema_optimized.sql'
            if os.path.exists(schema_file):
                print(f"✅ Schema file found: {schema_file}")
                results['schema_readable'] = True
                
                # Read and analyze schema
                with open(schema_file, 'r') as f:
                    schema_content = f.read()
                
                # Count objects to be created
                create_statements = [
                    'CREATE SCHEMA',
                    'CREATE TABLE', 
                    'CREATE INDEX',
                    'CREATE TYPE',
                    'CREATE FUNCTION',
                    'CREATE TRIGGER'
                ]
                
                object_counts = {}
                for statement in create_statements:
                    count = schema_content.upper().count(statement)
                    if count > 0:
                        object_counts[statement] = count
                        results['estimated_objects'] += count
                
                print(f"📊 Schema Analysis:")
                for statement, count in object_counts.items():
                    print(f"   {statement}: {count}")
                
                print(f"   Total objects to create: {results['estimated_objects']}")
                
                # Basic syntax validation (check for balanced parentheses)
                open_parens = schema_content.count('(')
                close_parens = schema_content.count(')')
                if open_parens == close_parens:
                    print(f"✅ Basic syntax validation passed")
                    results['syntax_valid'] = True
                else:
                    print(f"⚠️  Parentheses mismatch: {open_parens} open, {close_parens} close")
                
            else:
                print(f"❌ Schema file not found: {schema_file}")
        
        except Exception as e:
            print(f"❌ Schema analysis failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def test_transformation_logic(self):
        """Test data transformation logic without executing"""
        print("\n🔄 Testing Transformation Logic")
        print("=" * 40)
        
        results = {
            'zone_extraction_test': False,
            'sample_extractions': [],
            'performance_estimate': {}
        }
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Get sample provisions for testing
            cursor.execute("""
                SELECT id, provision_text, zone 
                FROM regulatory_provisions 
                WHERE provision_text IS NOT NULL 
                LIMIT 20
            """)
            samples = cursor.fetchall()
            
            if samples:
                print(f"📊 Testing zone extraction on {len(samples)} sample provisions:")
                
                import re
                zone_pattern = r'\bZone\s+([A-Z]+[0-9]+[A-Z]*)\b'
                
                explicit_found = 0
                for prov_id, text, old_zone in samples:
                    # Test explicit zone extraction
                    zone_matches = re.findall(zone_pattern, text, re.IGNORECASE)
                    
                    if zone_matches:
                        explicit_found += 1
                        results['sample_extractions'].append({
                            'id': prov_id,
                            'old_zone': old_zone,
                            'extracted_zones': zone_matches,
                            'text_preview': text[:100] + '...' if len(text) > 100 else text
                        })
                        print(f"   ✅ ID {prov_id}: Found zones {zone_matches} (was {old_zone})")
                    else:
                        print(f"   ⚪ ID {prov_id}: No explicit zone mention (was {old_zone})")
                
                explicit_rate = (explicit_found / len(samples)) * 100
                print(f"\n📈 Extraction Results:")
                print(f"   Explicit zone mentions: {explicit_found}/{len(samples)} ({explicit_rate:.1f}%)")
                
                # Estimate performance for full dataset
                total_provisions = cursor.execute("SELECT COUNT(*) FROM regulatory_provisions").fetchone()[0]
                estimated_explicit = int(total_provisions * explicit_rate / 100)
                print(f"   Estimated explicit zones in full dataset: {estimated_explicit:,}")
                
                results['zone_extraction_test'] = True
                results['performance_estimate'] = {
                    'total_provisions': total_provisions,
                    'estimated_explicit_zones': estimated_explicit,
                    'explicit_rate_percent': explicit_rate
                }
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Transformation test failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def test_execution_framework(self):
        """Test the execution framework components"""
        print("\n🚀 Testing Execution Framework")
        print("=" * 40)
        
        results = {
            'python_script_exists': False,
            'bash_script_exists': False,
            'can_import_modules': False,
            'permissions_ok': False
        }
        
        try:
            # Check if execution scripts exist
            python_script = './execute_prp_m1.py'
            bash_script = './run_prp_m1.sh'
            
            if os.path.exists(python_script):
                print(f"✅ Python execution script found")
                results['python_script_exists'] = True
            else:
                print(f"❌ Python script missing: {python_script}")
            
            if os.path.exists(bash_script):
                print(f"✅ Bash execution script found")
                results['bash_script_exists'] = True
            else:
                print(f"❌ Bash script missing: {bash_script}")
            
            # Test Python imports
            try:
                from db_config import get_connection  # Unified PostgreSQL connection
                import psycopg2
                import json
                import hashlib
                print(f"✅ All required Python modules can be imported")
                results['can_import_modules'] = True
            except ImportError as e:
                print(f"❌ Missing Python module: {e}")
            
            # Test file permissions
            if os.access('./nsw_planning.db', os.R_OK):
                print(f"✅ SQLite database is readable")
                results['permissions_ok'] = True
            else:
                print(f"❌ SQLite database is not readable")
        
        except Exception as e:
            print(f"❌ Framework test failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def generate_dry_run_report(self, all_results):
        """Generate comprehensive dry run report"""
        
        report = {
            'dry_run_id': f"DRY_RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'execution_timestamp': datetime.now().isoformat(),
            'duration_seconds': (datetime.now() - self.start_time).total_seconds(),
            'overall_readiness': True,
            'test_results': all_results,
            'recommendations': [],
            'blocking_issues': []
        }
        
        # Analyze results and generate recommendations
        db_test = all_results.get('database_connections', {})
        if not db_test.get('sqlite', False):
            report['overall_readiness'] = False
            report['blocking_issues'].append("SQLite database connection failed")
        
        if not db_test.get('postgresql', False):
            report['overall_readiness'] = False
            report['blocking_issues'].append("PostgreSQL database connection failed")
        
        data_test = all_results.get('sqlite_data_structure', {})
        if data_test.get('missing_tables'):
            report['overall_readiness'] = False
            report['blocking_issues'].extend([f"Missing table: {t}" for t in data_test['missing_tables']])
        
        schema_test = all_results.get('postgresql_schema', {})
        if not schema_test.get('schema_readable', False):
            report['overall_readiness'] = False
            report['blocking_issues'].append("PostgreSQL schema file not readable")
        
        # Add recommendations
        transform_test = all_results.get('transformation_logic', {})
        if transform_test.get('performance_estimate'):
            perf = transform_test['performance_estimate']
            if perf.get('explicit_rate_percent', 0) < 10:
                report['recommendations'].append("Very low explicit zone extraction rate - consider manual zone assignment")
            elif perf.get('explicit_rate_percent', 0) < 30:
                report['recommendations'].append("Moderate zone extraction rate - review geographical context assignment")
        
        framework_test = all_results.get('execution_framework', {})
        if not framework_test.get('can_import_modules', False):
            report['blocking_issues'].append("Required Python modules missing")
        
        # Save report
        report_file = f"prp_m1_dryrun_report_{report['dry_run_id']}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report, report_file
    
    def run_dry_run(self):
        """Execute complete dry run test"""
        
        print(f"""
🧪 PRP-M1 DRY RUN TEST
===================
Testing execution framework without making changes
Start time: {self.start_time.isoformat()}
""")
        
        all_results = {}
        
        # Run all tests
        all_results['database_connections'] = self.test_database_connections()
        all_results['sqlite_data_structure'] = self.test_sqlite_data_structure()
        all_results['postgresql_schema'] = self.test_postgresql_schema_creation()
        all_results['transformation_logic'] = self.test_transformation_logic()
        all_results['execution_framework'] = self.test_execution_framework()
        
        # Generate report
        report, report_file = self.generate_dry_run_report(all_results)
        
        # Print summary
        print(f"\n" + "="*60)
        print(f"🎯 DRY RUN SUMMARY")
        print(f"="*60)
        
        if report['overall_readiness']:
            print(f"✅ READY FOR MIGRATION")
            print(f"   All critical tests passed")
        else:
            print(f"❌ NOT READY FOR MIGRATION")
            print(f"   Blocking issues found:")
            for issue in report['blocking_issues']:
                print(f"   • {issue}")
        
        if report['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in report['recommendations']:
                print(f"   • {rec}")
        
        print(f"\n📊 Test Results:")
        print(f"   Total tests: {len(all_results)}")
        print(f"   Duration: {report['duration_seconds']:.2f} seconds")
        print(f"   Report saved: {report_file}")
        
        return report['overall_readiness']

if __name__ == "__main__":
    tester = PRP_M1_DryRunTester()
    success = tester.run_dry_run()
    
    if success:
        print(f"\n🎉 DRY RUN PASSED - Ready to execute PRP-M1!")
        sys.exit(0)
    else:
        print(f"\n🛑 DRY RUN FAILED - Fix issues before proceeding")
        sys.exit(1)