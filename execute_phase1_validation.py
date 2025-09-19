#!/usr/bin/env python3
"""
PRP-M1 Phase 1 Execution: Pre-migration Validation
=================================================
Execute Steps 1-5 with critical stage feedback
"""

import os
import sys
import json
import time
import hashlib
import sqlite3
import psycopg2
import subprocess
from datetime import datetime
from pathlib import Path

class Phase1Executor:
    """Execute Phase 1: Pre-migration validation with feedback"""
    
    def __init__(self):
        self.execution_id = f"PHASE1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.results = []
        self.start_time = datetime.now()
        
        print(f"""
🎯 PRP-M1 PHASE 1: PRE-MIGRATION VALIDATION
==========================================
Execution ID: {self.execution_id}
Start Time: {self.start_time.isoformat()}

This phase will:
✓ Audit source data integrity
✓ Assess data quality issues  
✓ Create backup snapshots
✓ Validate PostgreSQL schema
✓ Perform compatibility checks
""")
    
    def execute_step(self, step_id, step_name, step_function):
        """Execute a step with metrics and feedback"""
        print(f"\n{'='*60}")
        print(f"🚀 STEP {step_id}: {step_name}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            result = step_function()
            duration = time.time() - start_time
            
            print(f"\n⏱️  Duration: {duration:.2f} seconds")
            
            if result.get('success', False):
                print(f"✅ STEP {step_id} COMPLETED SUCCESSFULLY")
            else:
                print(f"❌ STEP {step_id} FAILED")
            
            # Show metrics
            if result.get('metrics'):
                print(f"\n📊 Metrics:")
                for key, value in result['metrics'].items():
                    if isinstance(value, (int, float)):
                        print(f"   • {key}: {value:,}")
                    else:
                        print(f"   • {key}: {value}")
            
            # Show warnings
            if result.get('warnings'):
                print(f"\n⚠️  Warnings ({len(result['warnings'])}):")
                for warning in result['warnings'][:3]:
                    print(f"   • {warning}")
                if len(result['warnings']) > 3:
                    print(f"   ... and {len(result['warnings']) - 3} more")
            
            # Show errors
            if result.get('errors'):
                print(f"\n❌ Errors ({len(result['errors'])}):")
                for error in result['errors'][:3]:
                    print(f"   • {error}")
                if len(result['errors']) > 3:
                    print(f"   ... and {len(result['errors']) - 3} more")
            
            result['step_id'] = step_id
            result['step_name'] = step_name
            result['duration'] = duration
            self.results.append(result)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            error_result = {
                'step_id': step_id,
                'step_name': step_name,
                'success': False,
                'duration': duration,
                'errors': [str(e)],
                'metrics': {},
                'warnings': []
            }
            self.results.append(error_result)
            print(f"❌ STEP {step_id} FAILED with exception: {e}")
            return error_result
    
    def wait_for_confirmation(self, result):
        """Wait for user confirmation after each step"""
        print(f"\n{'='*60}")
        print(f"📋 STEP {result['step_id']} RESULTS REVIEW")
        print(f"{'='*60}")
        
        status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
        print(f"Status: {status}")
        print(f"Duration: {result['duration']:.2f} seconds")
        
        while True:
            choice = input(f"""
Choose next action:
[C] Continue to next step
[R] Retry this step
[D] View detailed results  
[S] Stop execution
> """).strip().upper()
            
            if choice == 'C':
                return 'continue'
            elif choice == 'R':
                return 'retry'
            elif choice == 'D':
                print(json.dumps(result, indent=2, default=str))
            elif choice == 'S':
                print("🛑 Execution stopped by user")
                return 'stop'
            else:
                print("❌ Invalid choice. Please select C, R, D, or S")
    
    def step_1_source_data_audit(self):
        """Step 1: Complete source data audit with checksums"""
        metrics = {}
        warnings = []
        errors = []
        
        try:
            # Connect to SQLite
            conn = sqlite3.connect('./nsw_planning.db')
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            metrics['total_tables'] = len(tables)
            
            # Audit each table
            table_details = {}
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    table_details[table] = count
                    metrics[f"{table}_count"] = count
                except Exception as e:
                    errors.append(f"Failed to count {table}: {e}")
            
            # Focus on critical tables
            critical_tables = ['documents', 'regulatory_provisions', 'quantitative_standards']
            missing_critical = []
            
            for table in critical_tables:
                if table not in tables:
                    missing_critical.append(table)
                    errors.append(f"Critical table missing: {table}")
                elif table_details.get(table, 0) == 0:
                    warnings.append(f"Critical table {table} is empty")
            
            # Database file integrity
            db_path = Path('./nsw_planning.db')
            if db_path.exists():
                db_size = db_path.stat().st_size
                metrics['database_size_mb'] = round(db_size / 1024 / 1024, 2)
                
                # Create checksum
                with open('./nsw_planning.db', 'rb') as f:
                    db_content = f.read()
                    db_checksum = hashlib.md5(db_content).hexdigest()
                    metrics['database_checksum'] = db_checksum
            
            # Data quality indicators
            if 'regulatory_provisions' in table_details:
                # Check for null text
                cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE provision_text IS NULL OR provision_text = ''")
                null_text = cursor.fetchone()[0]
                metrics['provisions_null_text'] = null_text
                
                if null_text > 0:
                    warnings.append(f"{null_text} provisions have no text content")
                
                # Check average text length
                cursor.execute("SELECT AVG(LENGTH(provision_text)) FROM regulatory_provisions WHERE provision_text IS NOT NULL")
                avg_length = cursor.fetchone()[0]
                metrics['avg_provision_length'] = round(avg_length, 1) if avg_length else 0
                
                # Zone distribution analysis
                cursor.execute("""
                    SELECT zone, COUNT(*) as count 
                    FROM regulatory_provisions 
                    WHERE zone IS NOT NULL 
                    GROUP BY zone 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                zone_dist = cursor.fetchall()
                metrics['top_zones'] = dict(zone_dist)
                
                # Check for the R2 bias
                total_with_zones = sum(count for _, count in zone_dist)
                if zone_dist and zone_dist[0][0] == 'R2':
                    r2_percent = (zone_dist[0][1] / total_with_zones) * 100
                    if r2_percent > 50:
                        warnings.append(f"R2 zone dominance detected: {r2_percent:.1f}% of all zone assignments")
                        metrics['r2_bias_detected'] = True
            
            conn.close()
            
            return {
                'success': len(missing_critical) == 0,
                'metrics': metrics,
                'warnings': warnings,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'metrics': metrics,
                'warnings': warnings,
                'errors': errors + [f"Audit failed: {e}"]
            }
    
    def step_2_data_quality_assessment(self):
        """Step 2: Comprehensive data quality assessment"""
        metrics = {}
        warnings = []
        errors = []
        
        try:
            conn = sqlite3.connect('./nsw_planning.db')
            cursor = conn.cursor()
            
            # Regulatory provisions quality
            cursor.execute("SELECT COUNT(*) FROM regulatory_provisions")
            total_provisions = cursor.fetchone()[0]
            metrics['total_provisions'] = total_provisions
            
            # Text content quality
            cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE provision_text IS NOT NULL AND LENGTH(provision_text) > 10")
            meaningful_text = cursor.fetchone()[0]
            text_quality_rate = (meaningful_text / total_provisions) * 100
            metrics['meaningful_text_rate'] = round(text_quality_rate, 1)
            
            if text_quality_rate < 90:
                warnings.append(f"Only {text_quality_rate:.1f}% of provisions have meaningful text content")
            
            # Zone assignment quality
            cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE zone IS NOT NULL")
            with_zones = cursor.fetchone()[0]
            zone_coverage_rate = (with_zones / total_provisions) * 100
            metrics['zone_coverage_rate'] = round(zone_coverage_rate, 1)
            
            if zone_coverage_rate < 20:
                warnings.append(f"Low zone coverage: only {zone_coverage_rate:.1f}% have zone assignments")
            
            # Document coverage
            cursor.execute("SELECT COUNT(DISTINCT document_id) FROM regulatory_provisions")
            docs_with_provisions = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM documents")
            total_docs = cursor.fetchone()[0]
            metrics['documents_with_provisions'] = docs_with_provisions
            metrics['total_documents'] = total_docs
            
            if docs_with_provisions < total_docs:
                missing_docs = total_docs - docs_with_provisions
                warnings.append(f"{missing_docs} documents have no provisions extracted")
            
            # Quantitative standards quality
            cursor.execute("SELECT COUNT(*) FROM quantitative_standards")
            total_standards = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM quantitative_standards WHERE numeric_value IS NOT NULL")
            numeric_standards = cursor.fetchone()[0]
            
            metrics['total_quantitative_standards'] = total_standards
            metrics['standards_with_values'] = numeric_standards
            
            if total_standards > 0:
                numeric_rate = (numeric_standards / total_standards) * 100
                metrics['numeric_standards_rate'] = round(numeric_rate, 1)
                
                if numeric_rate < 95:
                    warnings.append(f"Only {numeric_rate:.1f}% of quantitative standards have numeric values")
            
            # Cross-reference integrity
            cursor.execute("""
                SELECT COUNT(*) 
                FROM quantitative_standards qs 
                LEFT JOIN regulatory_provisions rp ON qs.provision_id = rp.id 
                WHERE rp.id IS NULL
            """)
            orphaned_standards = cursor.fetchone()[0]
            
            if orphaned_standards > 0:
                warnings.append(f"{orphaned_standards} quantitative standards are orphaned (no parent provision)")
                metrics['orphaned_standards'] = orphaned_standards
            
            conn.close()
            
            # Quality assessment
            quality_issues = len(warnings) + len(errors)
            metrics['quality_issues_count'] = quality_issues
            
            return {
                'success': quality_issues < 10,  # Allow some warnings
                'metrics': metrics,
                'warnings': warnings,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'metrics': metrics,
                'warnings': warnings,
                'errors': errors + [f"Quality assessment failed: {e}"]
            }
    
    def step_3_create_backups(self):
        """Step 3: Create comprehensive backup snapshots"""
        metrics = {}
        warnings = []
        errors = []
        
        try:
            # Create backups directory
            backup_dir = Path('./backups')
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # SQLite backup
            sqlite_backup = backup_dir / f"nsw_planning_phase1_{timestamp}.db"
            try:
                import shutil
                shutil.copy2('./nsw_planning.db', sqlite_backup)
                backup_size = sqlite_backup.stat().st_size
                metrics['sqlite_backup_size_mb'] = round(backup_size / 1024 / 1024, 2)
                metrics['sqlite_backup_path'] = str(sqlite_backup)
                print(f"✅ SQLite backup created: {sqlite_backup}")
            except Exception as e:
                errors.append(f"SQLite backup failed: {e}")
            
            # PostgreSQL backup
            pg_backup = backup_dir / f"nsw_planning_phase1_{timestamp}.sql"
            try:
                env = os.environ.copy()
                env['PGPASSWORD'] = 'postgres'
                
                result = subprocess.run([
                    'pg_dump', '-h', 'localhost', '-U', 'postgres',
                    '-d', 'nsw_planning', '-f', str(pg_backup)
                ], env=env, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    if pg_backup.exists():
                        backup_size = pg_backup.stat().st_size
                        metrics['pg_backup_size_mb'] = round(backup_size / 1024 / 1024, 2)
                        metrics['pg_backup_path'] = str(pg_backup)
                        print(f"✅ PostgreSQL backup created: {pg_backup}")
                    else:
                        warnings.append("PostgreSQL backup command succeeded but file not found")
                else:
                    errors.append(f"PostgreSQL backup failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                errors.append("PostgreSQL backup timed out after 5 minutes")
            except Exception as e:
                errors.append(f"PostgreSQL backup failed: {e}")
            
            # Create checksums
            checksum_file = backup_dir / f"checksums_{timestamp}.txt"
            try:
                with open(checksum_file, 'w') as f:
                    for backup_file in [sqlite_backup, pg_backup]:
                        if backup_file.exists():
                            with open(backup_file, 'rb') as bf:
                                content = bf.read()
                                checksum = hashlib.md5(content).hexdigest()
                                f.write(f"{checksum}  {backup_file.name}\n")
                
                metrics['checksum_file'] = str(checksum_file)
                print(f"✅ Checksums created: {checksum_file}")
            except Exception as e:
                warnings.append(f"Checksum creation failed: {e}")
            
            # Backup metadata
            metadata = {
                'backup_timestamp': timestamp,
                'execution_id': self.execution_id,
                'sqlite_backup': str(sqlite_backup) if sqlite_backup.exists() else None,
                'pg_backup': str(pg_backup) if pg_backup.exists() else None,
                'created_by': 'PRP-M1 Phase 1',
                'purpose': 'Pre-migration safety backup'
            }
            
            metadata_file = backup_dir / f"backup_metadata_{timestamp}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            metrics['metadata_file'] = str(metadata_file)
            metrics['total_backups_created'] = sum(1 for f in [sqlite_backup, pg_backup] if f.exists())
            
            return {
                'success': len(errors) == 0,
                'metrics': metrics,
                'warnings': warnings,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'metrics': metrics,
                'warnings': warnings,
                'errors': errors + [f"Backup creation failed: {e}"]
            }
    
    def step_4_postgresql_schema_validation(self):
        """Step 4: Validate and create PostgreSQL schema"""
        metrics = {}
        warnings = []
        errors = []
        
        try:
            # Check schema file
            schema_file = Path('./research_assistant_schema_optimized.sql')
            if not schema_file.exists():
                errors.append("PostgreSQL schema file not found")
                return {
                    'success': False,
                    'metrics': metrics,
                    'warnings': warnings,
                    'errors': errors
                }
            
            # Read schema
            with open(schema_file, 'r') as f:
                schema_content = f.read()
            
            # Analyze schema
            schema_objects = {
                'CREATE SCHEMA': schema_content.upper().count('CREATE SCHEMA'),
                'CREATE TABLE': schema_content.upper().count('CREATE TABLE'),
                'CREATE INDEX': schema_content.upper().count('CREATE INDEX'),
                'CREATE TYPE': schema_content.upper().count('CREATE TYPE'),
                'CREATE FUNCTION': schema_content.upper().count('CREATE FUNCTION'),
                'CREATE TRIGGER': schema_content.upper().count('CREATE TRIGGER')
            }
            
            total_objects = sum(schema_objects.values())
            metrics.update(schema_objects)
            metrics['total_objects_to_create'] = total_objects
            
            print(f"📊 Schema Analysis:")
            for obj_type, count in schema_objects.items():
                if count > 0:
                    print(f"   • {obj_type}: {count}")
            
            # Test PostgreSQL connection
            try:
                conn = psycopg2.connect(
                    host="localhost",
                    database="nsw_planning",
                    user="postgres",
                    password="postgres"
                )
                conn.autocommit = True
                cursor = conn.cursor()
                
                # Check existing schemas
                cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'research_assistant'")
                existing_schema = cursor.fetchone()
                
                if existing_schema:
                    warnings.append("research_assistant schema already exists - will be recreated")
                    # Drop existing schema
                    cursor.execute("DROP SCHEMA IF EXISTS research_assistant CASCADE")
                    print("⚠️  Existing research_assistant schema dropped")
                
                # Execute schema creation
                print("🔨 Creating PostgreSQL schema...")
                cursor.execute(schema_content)
                
                # Verify creation
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'research_assistant'
                """)
                created_tables = [row[0] for row in cursor.fetchall()]
                metrics['tables_created'] = len(created_tables)
                metrics['created_table_names'] = created_tables
                
                cursor.execute("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE schemaname = 'research_assistant'
                """)
                created_indexes = [row[0] for row in cursor.fetchall()]
                metrics['indexes_created'] = len(created_indexes)
                
                print(f"✅ Schema created successfully:")
                print(f"   • Tables: {len(created_tables)}")
                print(f"   • Indexes: {len(created_indexes)}")
                
                conn.close()
                
            except Exception as e:
                errors.append(f"Schema creation failed: {e}")
            
            return {
                'success': len(errors) == 0,
                'metrics': metrics,
                'warnings': warnings,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'metrics': metrics,
                'warnings': warnings,
                'errors': errors + [f"Schema validation failed: {e}"]
            }
    
    def step_5_compatibility_checks(self):
        """Step 5: Final compatibility and readiness checks"""
        metrics = {}
        warnings = []
        errors = []
        
        try:
            # Test zone extraction capability
            import re
            
            conn = sqlite3.connect('./nsw_planning.db')
            cursor = conn.cursor()
            
            # Sample zone extraction test
            cursor.execute("""
                SELECT provision_text, zone 
                FROM regulatory_provisions 
                WHERE provision_text IS NOT NULL 
                AND zone IN ('R1', 'R2', 'R3', 'R4')
                LIMIT 100
            """)
            
            samples = cursor.fetchall()
            zone_pattern = r'\bZone\s+([A-Z]+[0-9]+[A-Z]*)\b'
            
            explicit_count = 0
            for text, assigned_zone in samples:
                matches = re.findall(zone_pattern, text, re.IGNORECASE)
                if matches:
                    explicit_count += 1
            
            extraction_rate = (explicit_count / len(samples)) * 100 if samples else 0
            metrics['sample_size'] = len(samples)
            metrics['explicit_extraction_rate'] = round(extraction_rate, 1)
            
            if extraction_rate < 30:
                warnings.append(f"Low zone extraction rate: {extraction_rate:.1f}%")
            
            # Test PostgreSQL schema functionality
            try:
                pg_conn = psycopg2.connect(
                    host="localhost",
                    database="nsw_planning",
                    user="postgres",
                    password="postgres"
                )
                pg_cursor = pg_conn.cursor()
                
                # Test insert capability
                pg_cursor.execute("""
                    INSERT INTO research_assistant.documents 
                    (document_name, document_type, jurisdiction) 
                    VALUES ('Test Document', 'LEP', 'Test')
                    RETURNING id
                """)
                test_id = pg_cursor.fetchone()[0]
                
                # Test search capability
                pg_cursor.execute("""
                    SELECT COUNT(*) FROM research_assistant.documents 
                    WHERE document_name = 'Test Document'
                """)
                test_count = pg_cursor.fetchone()[0]
                
                # Cleanup test data
                pg_cursor.execute("DELETE FROM research_assistant.documents WHERE id = %s", (test_id,))
                pg_conn.commit()
                pg_conn.close()
                
                metrics['postgresql_functionality_test'] = 'passed'
                print("✅ PostgreSQL schema functionality verified")
                
            except Exception as e:
                errors.append(f"PostgreSQL functionality test failed: {e}")
            
            # Disk space check
            import shutil
            total, used, free = shutil.disk_usage('.')
            free_gb = free / (1024**3)
            metrics['free_disk_space_gb'] = round(free_gb, 2)
            
            if free_gb < 5:
                warnings.append(f"Low disk space: only {free_gb:.1f} GB available")
            
            # Migration readiness assessment
            readiness_checks = {
                'database_connections': True,
                'source_data_quality': len([r for r in self.results if r.get('success', False)]) >= 3,
                'schema_created': metrics.get('postgresql_functionality_test') == 'passed',
                'sufficient_disk_space': free_gb >= 1,
                'zone_extraction_viable': extraction_rate >= 10
            }
            
            passed_checks = sum(readiness_checks.values())
            total_checks = len(readiness_checks)
            
            metrics['readiness_checks'] = readiness_checks
            metrics['readiness_score'] = f"{passed_checks}/{total_checks}"
            
            if passed_checks < total_checks:
                failed_checks = [check for check, passed in readiness_checks.items() if not passed]
                errors.extend([f"Readiness check failed: {check}" for check in failed_checks])
            
            conn.close()
            
            return {
                'success': passed_checks == total_checks,
                'metrics': metrics,
                'warnings': warnings,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'metrics': metrics,
                'warnings': warnings,
                'errors': errors + [f"Compatibility check failed: {e}"]
            }
    
    def validation_gate_1(self):
        """Validation Gate 1: Pre-migration readiness assessment"""
        print(f"\n{'='*60}")
        print(f"🚦 VALIDATION GATE 1: PRE-MIGRATION READINESS")
        print(f"{'='*60}")
        
        # Analyze all step results
        successful_steps = sum(1 for r in self.results if r.get('success', False))
        total_steps = len(self.results)
        
        print(f"📊 Step Results: {successful_steps}/{total_steps} successful")
        
        critical_issues = []
        for result in self.results:
            if not result.get('success', False):
                critical_issues.extend(result.get('errors', []))
        
        if critical_issues:
            print(f"❌ Critical Issues Found ({len(critical_issues)}):")
            for issue in critical_issues[:5]:
                print(f"   • {issue}")
            if len(critical_issues) > 5:
                print(f"   ... and {len(critical_issues) - 5} more")
        
        # Overall assessment
        gate_passed = successful_steps == total_steps and len(critical_issues) == 0
        
        if gate_passed:
            print(f"\n✅ VALIDATION GATE 1 PASSED")
            print(f"   ✓ All pre-migration checks successful")
            print(f"   ✓ Source data validated")
            print(f"   ✓ Backups created")
            print(f"   ✓ PostgreSQL schema ready")
            print(f"   ✓ System compatibility verified")
            print(f"\n🎯 READY TO PROCEED TO PHASE 2")
        else:
            print(f"\n❌ VALIDATION GATE 1 FAILED")
            print(f"   • Fix critical issues before proceeding")
            print(f"   • Review step results above")
            print(f"   • Consider rollback if needed")
        
        return gate_passed
    
    def execute_phase_1(self):
        """Execute complete Phase 1 with step-by-step feedback"""
        
        try:
            # Step 1: Source Data Audit
            while True:
                result = self.execute_step("1", "Source Data Audit", self.step_1_source_data_audit)
                action = self.wait_for_confirmation(result)
                if action == 'continue':
                    break
                elif action == 'stop':
                    return False
                # If 'retry', the loop continues
            
            # Step 2: Data Quality Assessment
            while True:
                result = self.execute_step("2", "Data Quality Assessment", self.step_2_data_quality_assessment)
                action = self.wait_for_confirmation(result)
                if action == 'continue':
                    break
                elif action == 'stop':
                    return False
            
            # Step 3: Create Backups
            while True:
                result = self.execute_step("3", "Create Safety Backups", self.step_3_create_backups)
                action = self.wait_for_confirmation(result)
                if action == 'continue':
                    break
                elif action == 'stop':
                    return False
            
            # Step 4: PostgreSQL Schema Validation
            while True:
                result = self.execute_step("4", "PostgreSQL Schema Creation", self.step_4_postgresql_schema_validation)
                action = self.wait_for_confirmation(result)
                if action == 'continue':
                    break
                elif action == 'stop':
                    return False
            
            # Step 5: Compatibility Checks
            while True:
                result = self.execute_step("5", "Compatibility & Readiness Checks", self.step_5_compatibility_checks)
                action = self.wait_for_confirmation(result)
                if action == 'continue':
                    break
                elif action == 'stop':
                    return False
            
            # Validation Gate 1
            gate_passed = self.validation_gate_1()
            
            # Generate Phase 1 report
            self.generate_phase1_report()
            
            return gate_passed
            
        except KeyboardInterrupt:
            print(f"\n🛑 Phase 1 execution interrupted by user")
            return False
        except Exception as e:
            print(f"❌ Phase 1 execution failed: {e}")
            return False
    
    def generate_phase1_report(self):
        """Generate comprehensive Phase 1 execution report"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        report = {
            'execution_id': self.execution_id,
            'phase': 'Phase 1: Pre-migration Validation',
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'duration_seconds': duration,
            'steps_completed': len(self.results),
            'successful_steps': sum(1 for r in self.results if r.get('success', False)),
            'step_results': self.results
        }
        
        report_file = f"phase1_report_{self.execution_id}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📊 PHASE 1 EXECUTION REPORT")
        print(f"Report saved to: {report_file}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Steps completed: {report['successful_steps']}/{report['steps_completed']}")

if __name__ == "__main__":
    executor = Phase1Executor()
    success = executor.execute_phase_1()
    
    if success:
        print(f"\n🎉 PHASE 1 COMPLETED SUCCESSFULLY!")
        print(f"Ready to proceed to Phase 2: Data Extraction & Transformation")
        sys.exit(0)
    else:
        print(f"\n❌ PHASE 1 FAILED")
        print(f"Review results and fix issues before proceeding")
        sys.exit(1)