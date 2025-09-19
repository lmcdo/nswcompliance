#!/usr/bin/env python3
"""
PRP-8D: Bulletproof Migration Engine
Atomic, fault-tolerant migration with comprehensive verification
"""

import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import traceback

class BulletproofMigrationEngine:
    """Atomic migration engine with comprehensive error handling and verification"""
    
    def __init__(self, source_db="nsw_planning.db"):
        self.source_db = source_db
        self.target_conn = None
        self.migration_run_id = None
        
        # Migration statistics
        self.stats = {
            'provisions_processed': 0,
            'provisions_successful': 0, 
            'provisions_failed': 0,
            'provisions_skipped': 0,
            'start_time': None,
            'end_time': None,
            'errors': []
        }
        
    def execute_bulletproof_migration(self):
        """Execute complete bulletproof migration"""
        
        print("PRP-8D: BULLETPROOF MIGRATION ENGINE")
        print("=" * 50)
        
        self.stats['start_time'] = datetime.now()
        
        try:
            # Phase 1: Setup and initialization
            self.initialize_migration()
            
            # Phase 2: Load source data
            source_provisions = self.load_source_provisions()
            
            # Phase 3: Execute atomic migrations
            self.execute_atomic_migrations(source_provisions)
            
            # Phase 4: Verify migration integrity
            self.verify_migration_integrity()
            
            # Phase 5: Complete migration tracking
            self.complete_migration_tracking()
            
            # Phase 6: Generate comprehensive report
            self.generate_migration_report()
            
            return self.calculate_success_rate() >= 0.95
            
        except Exception as e:
            print(f"MIGRATION FAILED: {e}")
            traceback.print_exc()
            self.handle_migration_failure(str(e))
            return False
            
        finally:
            self.cleanup_connections()
    
    def initialize_migration(self):
        """Initialize migration tracking and database connections"""
        
        print("[1/6] Initializing migration...")
        
        # Connect to target PostgreSQL
        self.target_conn = psycopg2.connect(
            host='localhost',
            database='nsw_planning',
            user='postgres',
            password='postgres'
        )
        
        # Create migration run record
        with self.target_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO migration_tracking.migration_runs (
                    run_name, started_at, source_database, status
                ) VALUES (%s, %s, %s, %s)
                RETURNING run_id
            """, (
                f"PRP_8D_Bulletproof_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                self.stats['start_time'],
                self.source_db,
                'IN_PROGRESS'
            ))
            
            self.migration_run_id = cur.fetchone()[0]
            self.target_conn.commit()
        
        print(f"    Migration run ID: {self.migration_run_id}")
        print(f"    Target database: nsw_planning")
        print(f"    Source database: {self.source_db}")
    
    def load_source_provisions(self):
        """Load source provisions for migration"""
        
        print("[2/6] Loading source provisions...")
        
        conn = sqlite3.connect(self.source_db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Load provisions with zones (our validated subset)
        cur.execute("""
            SELECT 
                rp.*,
                qs.numeric_value,
                qs.unit,
                qs.context as measurement_context,
                qs.confidence_score
            FROM regulatory_provisions rp
            LEFT JOIN quantitative_standards qs ON rp.id = qs.provision_id
            WHERE rp.zone IS NOT NULL
            ORDER BY rp.id
        """)
        
        provisions = cur.fetchall()
        conn.close()
        
        print(f"    Loaded {len(provisions)} provisions with zones")
        return provisions
    
    def execute_atomic_migrations(self, provisions: List):
        """Execute migration with atomic transactions per provision"""
        
        print(f"[3/6] Executing atomic migrations...")
        
        total_provisions = len(provisions)
        batch_size = 50  # Commit every 50 provisions
        last_progress = 0
        
        for i, provision in enumerate(provisions):
            try:
                # Execute single provision migration in atomic transaction
                success = self.migrate_single_provision(provision)
                
                if success:
                    self.stats['provisions_successful'] += 1
                else:
                    self.stats['provisions_failed'] += 1
                    
                self.stats['provisions_processed'] += 1
                
                # Progress reporting
                progress = int((i + 1) / total_provisions * 100)
                if progress >= last_progress + 10:  # Report every 10%
                    print(f"    Progress: {progress}% ({i+1}/{total_provisions}) - Success: {self.stats['provisions_successful']}, Failed: {self.stats['provisions_failed']}")
                    last_progress = progress
                
                # Optional: Early termination if failure rate too high
                if self.stats['provisions_processed'] > 100:  # After 100 provisions
                    failure_rate = self.stats['provisions_failed'] / self.stats['provisions_processed']
                    if failure_rate > 0.1:  # >10% failure rate
                        print(f"    WARNING: High failure rate detected ({failure_rate:.1%})")
                        
            except Exception as e:
                print(f"    FATAL ERROR processing provision {provision['id']}: {e}")
                self.stats['provisions_failed'] += 1
                self.stats['provisions_processed'] += 1
                self.record_provision_error(provision['id'], f"FATAL: {str(e)}")
        
        print(f"    Migration completed: {self.stats['provisions_successful']}/{total_provisions} successful")
    
    def migrate_single_provision(self, provision) -> bool:
        """Migrate a single provision with atomic transaction"""
        
        try:
            with self.target_conn.cursor() as cur:
                # Start individual transaction
                cur.execute("BEGIN")
                
                # Determine document hierarchy
                authority_level, doc_type = self.determine_authority_level(provision)
                
                # Prepare data for insertion
                provision_data = self.prepare_provision_data(provision, authority_level, doc_type)
                
                # Insert provision
                cur.execute("""
                    INSERT INTO authoritative.planning_provisions (
                        document_type, document_name, clause_reference,
                        authority_level, provision_text, provision_type,
                        applicable_zones, numeric_value, unit, measurement_context,
                        original_json, extraction_method, extraction_confidence,
                        created_at
                    ) VALUES (
                        %(document_type)s, %(document_name)s, %(clause_reference)s,
                        %(authority_level)s, %(provision_text)s, %(provision_type)s,
                        %(applicable_zones)s, %(numeric_value)s, %(unit)s, %(measurement_context)s,
                        %(original_json)s, %(extraction_method)s, %(extraction_confidence)s,
                        %(created_at)s
                    ) RETURNING id
                """, provision_data)
                
                new_provision_id = cur.fetchone()[0]
                
                # Create authority tier classification
                tier_data = self.calculate_authority_tier(authority_level, provision_data['extraction_confidence'])
                
                cur.execute("""
                    INSERT INTO authoritative.provision_authority_tiers (
                        provision_id, tier_level, tier_name, confidence_level
                    ) VALUES (%s, %s, %s, %s)
                """, (
                    new_provision_id,
                    tier_data['tier_level'],
                    tier_data['tier_name'], 
                    provision_data['extraction_confidence']
                ))
                
                # Commit individual transaction
                cur.execute("COMMIT")
                
                # Record successful migration
                self.record_provision_success(provision['id'], new_provision_id, provision_data)
                
                return True
                
        except Exception as e:
            # Rollback individual transaction on any error
            try:
                with self.target_conn.cursor() as cur:
                    cur.execute("ROLLBACK")
            except:
                pass  # Rollback might fail if connection is broken
            
            # Record detailed error
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.record_provision_error(provision['id'], error_msg)
            
            return False
    
    def prepare_provision_data(self, provision, authority_level: int, doc_type: str) -> Dict:
        """Prepare provision data for insertion with proper validation"""
        
        # Create safe JSON metadata
        original_json = {
            'original_provision_id': provision['id'],
            'document_id': provision.get('document_id'),
            'ref_number': provision.get('ref_number'),
            'domain_classification': provision.get('domain_classification'),
            'classification_confidence': float(provision.get('classification_confidence') or 0.85),
            'migration_metadata': {
                'method': 'bulletproof_atomic_migration',
                'migration_timestamp': datetime.now().isoformat(),
                'run_id': self.migration_run_id
            }
        }
        
        return {
            'document_type': doc_type,
            'document_name': f"Document_{provision.get('document_id', 'unknown')}"[:200],  # Truncate
            'clause_reference': provision.get('ref_number') or f"ref_{provision['id']}",
            'authority_level': authority_level,
            'provision_text': provision.get('provision_text', '')[:5000],  # Truncate long text
            'provision_type': (provision.get('provision_type') or 'general')[:50],
            'applicable_zones': [provision['zone']] if provision['zone'] else [],
            'numeric_value': provision.get('numeric_value'),
            'unit': provision.get('unit'),
            'measurement_context': (provision.get('measurement_context') or '')[:100],
            'original_json': json.dumps(original_json),
            'extraction_method': 'bulletproof_migration',
            'extraction_confidence': float(provision.get('confidence_score') or provision.get('classification_confidence') or 0.85),
            'created_at': datetime.now()
        }
    
    def determine_authority_level(self, provision) -> Tuple[int, str]:
        """Determine authority level and document type"""
        
        doc_id = str(provision.get('document_id', '')).lower()
        ref_num = str(provision.get('ref_number', '')).lower() 
        section = str(provision.get('section_header', '')).lower()
        
        combined_text = f"{doc_id} {ref_num} {section}"
        
        # SEPP (State Environmental Planning Policy) - Highest authority
        if any(keyword in combined_text for keyword in ['sepp', 'state environmental planning policy']):
            return 1, "SEPP"
        
        # LEP (Local Environmental Plan) - Medium authority  
        elif any(keyword in combined_text for keyword in ['lep', 'local environmental plan']):
            return 2, "LEP"
        
        # DCP (Development Control Plan) - Local authority
        else:
            return 3, "DCP"
    
    def calculate_authority_tier(self, authority_level: int, confidence: float) -> Dict:
        """Calculate 5-tier authority classification"""
        
        # Tier 1: Fully authoritative (SEPP + high confidence)
        if authority_level == 1 and confidence >= 0.90:
            return {'tier_level': 1, 'tier_name': 'fully_authoritative'}
        
        # Tier 2: High authority (LEP high confidence or SEPP medium confidence)
        elif (authority_level == 2 and confidence >= 0.85) or (authority_level == 1 and confidence >= 0.75):
            return {'tier_level': 2, 'tier_name': 'high_authority'}
        
        # Tier 3: Moderate authority (DCP high confidence or LEP medium confidence)
        elif (authority_level == 3 and confidence >= 0.80) or (authority_level == 2 and confidence >= 0.70):
            return {'tier_level': 3, 'tier_name': 'moderate_authority'}
        
        # Tier 4: Limited authority (lower confidence across all levels)
        elif confidence >= 0.60:
            return {'tier_level': 4, 'tier_name': 'limited_authority'}
        
        # Tier 5: Specialist referral required (very low confidence)
        else:
            return {'tier_level': 5, 'tier_name': 'specialist_referral'}
    
    def record_provision_success(self, source_id: int, target_id: int, provision_data: Dict):
        """Record successful provision migration"""
        
        try:
            with self.target_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO migration_tracking.provision_migrations (
                        run_id, source_provision_id, target_provision_id,
                        status, data_hash
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (
                    self.migration_run_id,
                    source_id,
                    target_id, 
                    'SUCCESS',
                    hashlib.md5(str(provision_data).encode()).hexdigest()
                ))
                self.target_conn.commit()
                
        except Exception as e:
            print(f"    Warning: Could not record success for provision {source_id}: {e}")
    
    def record_provision_error(self, source_id: int, error_msg: str):
        """Record provision migration error"""
        
        try:
            with self.target_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO migration_tracking.provision_migrations (
                        run_id, source_provision_id, status, error_message
                    ) VALUES (%s, %s, %s, %s)
                """, (
                    self.migration_run_id,
                    source_id,
                    'FAILED',
                    error_msg[:1000]  # Truncate long error messages
                ))
                self.target_conn.commit()
                
        except Exception as e:
            print(f"    Warning: Could not record error for provision {source_id}: {e}")
        
        # Also add to stats
        self.stats['errors'].append({
            'provision_id': source_id,
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        })
    
    def verify_migration_integrity(self):
        """Verify migration integrity and data consistency"""
        
        print("[4/6] Verifying migration integrity...")
        
        with self.target_conn.cursor() as cur:
            # Check provision count
            cur.execute("SELECT COUNT(*) FROM authoritative.planning_provisions")
            migrated_provisions = cur.fetchone()[0]
            
            # Check tier count
            cur.execute("SELECT COUNT(*) FROM authoritative.provision_authority_tiers")  
            migrated_tiers = cur.fetchone()[0]
            
            # Check for orphaned tiers
            cur.execute("""
                SELECT COUNT(*) FROM authoritative.provision_authority_tiers t
                LEFT JOIN authoritative.planning_provisions p ON t.provision_id = p.id
                WHERE p.id IS NULL
            """)
            orphaned_tiers = cur.fetchone()[0]
            
            # Verify data integrity
            integrity_passed = (
                migrated_provisions == self.stats['provisions_successful'] and
                migrated_tiers == self.stats['provisions_successful'] and
                orphaned_tiers == 0
            )
            
            print(f"    Provisions migrated: {migrated_provisions}")
            print(f"    Authority tiers: {migrated_tiers}")
            print(f"    Orphaned tiers: {orphaned_tiers}")
            print(f"    Integrity check: {'PASSED' if integrity_passed else 'FAILED'}")
            
            if not integrity_passed:
                raise Exception("Migration integrity check failed!")
    
    def complete_migration_tracking(self):
        """Complete migration tracking record"""
        
        print("[5/6] Completing migration tracking...")
        
        self.stats['end_time'] = datetime.now()
        duration = self.stats['end_time'] - self.stats['start_time']
        
        success_rate = self.calculate_success_rate()
        status = 'COMPLETED' if success_rate >= 0.95 else 'PARTIAL_SUCCESS'
        
        with self.target_conn.cursor() as cur:
            cur.execute("""
                UPDATE migration_tracking.migration_runs
                SET completed_at = %s,
                    status = %s,
                    provisions_processed = %s,
                    provisions_successful = %s,
                    provisions_failed = %s,
                    error_summary = %s
                WHERE run_id = %s
            """, (
                self.stats['end_time'],
                status,
                self.stats['provisions_processed'],
                self.stats['provisions_successful'],
                self.stats['provisions_failed'],
                json.dumps({'error_count': len(self.stats['errors']), 'duration_seconds': duration.total_seconds()}),
                self.migration_run_id
            ))
            
            self.target_conn.commit()
        
        print(f"    Migration duration: {duration}")
        print(f"    Success rate: {success_rate:.1%}")
        print(f"    Status: {status}")
    
    def calculate_success_rate(self) -> float:
        """Calculate migration success rate"""
        
        if self.stats['provisions_processed'] == 0:
            return 0.0
        
        return self.stats['provisions_successful'] / self.stats['provisions_processed']
    
    def generate_migration_report(self):
        """Generate comprehensive migration report"""
        
        print("[6/6] Generating migration report...")
        
        success_rate = self.calculate_success_rate()
        duration = self.stats['end_time'] - self.stats['start_time']
        
        report = {
            'prp': 'PRP-8D',
            'phase': 'Bulletproof Migration Execution',
            'migration_run_id': self.migration_run_id,
            'completed_at': self.stats['end_time'].isoformat(),
            'duration_seconds': duration.total_seconds(),
            'statistics': {
                'provisions_processed': self.stats['provisions_processed'],
                'provisions_successful': self.stats['provisions_successful'],
                'provisions_failed': self.stats['provisions_failed'],
                'success_rate': success_rate,
                'provisions_per_second': self.stats['provisions_processed'] / max(duration.total_seconds(), 1)
            },
            'quality_assessment': {
                'migration_quality': 'EXCELLENT' if success_rate >= 0.98 else 
                                   'GOOD' if success_rate >= 0.95 else
                                   'ACCEPTABLE' if success_rate >= 0.90 else 'POOR',
                'production_ready': success_rate >= 0.95,
                'data_integrity_verified': True
            }
        }
        
        # Save detailed report
        report_file = f"PRP_8D_MIGRATION_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)
        except Exception as e:
            print(f"Could not save report: {e}")
        
        # Generate summary
        print(f"\n" + "=" * 50)
        print("BULLETPROOF MIGRATION COMPLETED")
        print("=" * 50)
        
        status_icon = "✓" if success_rate >= 0.95 else "!" if success_rate >= 0.90 else "✗"
        
        print(f"[{status_icon}] Success Rate: {success_rate:.1%}")
        print(f"    Processed: {self.stats['provisions_processed']:,}")
        print(f"    Successful: {self.stats['provisions_successful']:,}")
        print(f"    Failed: {self.stats['provisions_failed']:,}")
        print(f"    Duration: {duration}")
        print(f"    Rate: {report['statistics']['provisions_per_second']:.1f} provisions/sec")
        
        if success_rate >= 0.95:
            print(f"\n🎉 MIGRATION SUCCESS: System ready for production!")
        else:
            print(f"\n⚠️ PARTIAL SUCCESS: Review failed provisions before production")
        
        print(f"\nDetailed report: {report_file}")
        
        return report
    
    def handle_migration_failure(self, error_msg: str):
        """Handle overall migration failure"""
        
        if self.migration_run_id and self.target_conn:
            try:
                with self.target_conn.cursor() as cur:
                    cur.execute("""
                        UPDATE migration_tracking.migration_runs
                        SET status = 'FAILED',
                            completed_at = %s,
                            error_summary = %s
                        WHERE run_id = %s
                    """, (
                        datetime.now(),
                        json.dumps({'fatal_error': error_msg}),
                        self.migration_run_id
                    ))
                    self.target_conn.commit()
            except Exception as e:
                print(f"Could not update migration tracking: {e}")
    
    def cleanup_connections(self):
        """Clean up database connections"""
        
        if self.target_conn:
            try:
                self.target_conn.close()
            except Exception as e:
                print(f"Error closing target connection: {e}")

def main():
    """Execute bulletproof migration"""
    
    engine = BulletproofMigrationEngine()
    success = engine.execute_bulletproof_migration()
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)