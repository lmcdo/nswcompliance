#!/usr/bin/env python3
"""
PRP-8D: SQLite Source Data Validation
Comprehensive validation of source data before migration
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter
import re

class SQLiteSourceValidator:
    """Validate SQLite source data for migration readiness"""
    
    def __init__(self, database_path="nsw_planning.db"):
        self.database_path = database_path
        self.validation_results = {
            'database_info': {},
            'data_quality': {},
            'migration_readiness': {},
            'recommendations': [],
            'issues': []
        }
    
    def validate_complete_source(self):
        """Complete validation of SQLite source database"""
        
        print("PRP-8D: SQLITE SOURCE VALIDATION")
        print("=" * 50)
        print(f"Source database: {self.database_path}")
        
        try:
            # Phase 1: Database accessibility and structure
            self.validate_database_access()
            
            # Phase 2: Regulatory provisions analysis
            self.analyze_regulatory_provisions()
            
            # Phase 3: Data quality assessment  
            self.assess_data_quality()
            
            # Phase 4: Migration readiness check
            self.check_migration_readiness()
            
            # Phase 5: Generate recommendations
            self.generate_recommendations()
            
            # Phase 6: Create validation report
            self.create_validation_report()
            
            return True
            
        except Exception as e:
            print(f"VALIDATION FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def validate_database_access(self):
        """Validate database accessibility and basic structure"""
        
        db_path = Path(self.database_path)
        
        if not db_path.exists():
            raise Exception(f"Database file not found: {self.database_path}")
        
        try:
            conn = sqlite3.connect(self.database_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            # Get database file info
            file_size = db_path.stat().st_size
            modified_time = datetime.fromtimestamp(db_path.stat().st_mtime)
            
            # Get database structure
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cur.fetchall()]
            
            # Check for required tables
            required_tables = ['regulatory_provisions', 'quantitative_standards']
            missing_tables = [t for t in required_tables if t not in tables]
            
            if missing_tables:
                raise Exception(f"Missing required tables: {missing_tables}")
            
            self.validation_results['database_info'] = {
                'file_path': str(db_path.absolute()),
                'file_size': file_size,
                'file_size_mb': round(file_size / (1024*1024), 2),
                'last_modified': modified_time.isoformat(),
                'tables_count': len(tables),
                'tables_list': tables,
                'required_tables_present': len(missing_tables) == 0
            }
            
            print(f"[OK] Database accessible: {len(tables)} tables, {self.validation_results['database_info']['file_size_mb']} MB")
            
            conn.close()
            
        except Exception as e:
            raise Exception(f"Database access failed: {e}")
    
    def analyze_regulatory_provisions(self):
        """Comprehensive analysis of regulatory provisions table"""
        
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        try:
            # Basic counts
            cur.execute("SELECT COUNT(*) FROM regulatory_provisions")
            total_provisions = cur.fetchone()[0]
            
            # Zone analysis
            cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE zone IS NOT NULL")
            with_zones = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE zone IS NULL")
            null_zones = cur.fetchone()[0]
            
            # Zone distribution
            cur.execute("""
                SELECT zone, COUNT(*) as count 
                FROM regulatory_provisions 
                WHERE zone IS NOT NULL 
                GROUP BY zone 
                ORDER BY count DESC
            """)
            zone_distribution = dict(cur.fetchall())
            
            # Data completeness analysis
            completeness = {}
            key_fields = ['provision_type', 'ref_number', 'provision_text', 'classification_confidence']
            
            for field in key_fields:
                cur.execute(f"SELECT COUNT(*) FROM regulatory_provisions WHERE {field} IS NOT NULL")
                non_null = cur.fetchone()[0]
                completeness[field] = {
                    'non_null_count': non_null,
                    'completeness_rate': round(non_null / total_provisions * 100, 2)
                }
            
            # Provision type analysis
            cur.execute("""
                SELECT provision_type, COUNT(*) as count
                FROM regulatory_provisions
                WHERE provision_type IS NOT NULL
                GROUP BY provision_type
                ORDER BY count DESC
                LIMIT 20
            """)
            provision_types = dict(cur.fetchall())
            
            # Document source analysis
            cur.execute("""
                SELECT document_id, COUNT(*) as count
                FROM regulatory_provisions
                GROUP BY document_id
                ORDER BY count DESC
                LIMIT 10  
            """)
            document_distribution = dict(cur.fetchall())
            
            self.validation_results['data_quality'] = {
                'total_provisions': total_provisions,
                'zone_coverage': {
                    'with_zones': with_zones,
                    'null_zones': null_zones,
                    'coverage_rate': round(with_zones / total_provisions * 100, 2)
                },
                'zone_distribution': zone_distribution,
                'field_completeness': completeness,
                'provision_types': provision_types,
                'document_distribution': document_distribution
            }
            
            print(f"[OK] Provisions analyzed: {total_provisions:,} total, {with_zones:,} with zones ({(with_zones/total_provisions*100):.1f}%)")
            
            conn.close()
            
        except Exception as e:
            conn.close()
            raise Exception(f"Provisions analysis failed: {e}")
    
    def assess_data_quality(self):
        """Assess overall data quality for migration suitability"""
        
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        quality_issues = []
        quality_score = 100  # Start with perfect score and deduct points
        
        try:
            # Check for data anomalies
            
            # 1. Duplicate provisions
            cur.execute("""
                SELECT provision_text, COUNT(*) as count
                FROM regulatory_provisions
                WHERE provision_text IS NOT NULL
                GROUP BY provision_text
                HAVING COUNT(*) > 1
                ORDER BY count DESC
                LIMIT 10
            """)
            duplicates = cur.fetchall()
            
            if duplicates:
                duplicate_count = sum(row[1] for row in duplicates)
                quality_issues.append(f"Found {len(duplicates)} groups of duplicate provisions ({duplicate_count} total)")
                quality_score -= 10
            
            # 2. Extremely long text fields
            cur.execute("""
                SELECT COUNT(*) FROM regulatory_provisions
                WHERE LENGTH(provision_text) > 5000
            """)
            long_texts = cur.fetchone()[0]
            
            if long_texts > 0:
                quality_issues.append(f"{long_texts} provisions with very long text (>5000 chars)")
                quality_score -= 5
            
            # 3. Invalid zone codes (using LIKE pattern instead of REGEXP)
            cur.execute("""
                SELECT zone, COUNT(*) as count
                FROM regulatory_provisions
                WHERE zone IS NOT NULL 
                AND (LENGTH(zone) < 1 OR LENGTH(zone) > 10)
                GROUP BY zone
                ORDER BY count DESC
            """)
            invalid_zones = cur.fetchall()
            
            if invalid_zones:
                quality_issues.append(f"Found {len(invalid_zones)} invalid zone formats")
                quality_score -= 5
            
            # 4. Confidence scores out of range
            cur.execute("""
                SELECT COUNT(*) FROM regulatory_provisions
                WHERE classification_confidence IS NOT NULL
                AND (classification_confidence < 0 OR classification_confidence > 1)
            """)
            invalid_confidence = cur.fetchone()[0]
            
            if invalid_confidence > 0:
                quality_issues.append(f"{invalid_confidence} provisions with invalid confidence scores")
                quality_score -= 10
            
            # 5. Check quantitative standards relationship
            cur.execute("""
                SELECT COUNT(*) FROM quantitative_standards qs
                LEFT JOIN regulatory_provisions rp ON qs.provision_id = rp.id
                WHERE rp.id IS NULL
            """)
            orphaned_standards = cur.fetchone()[0]
            
            if orphaned_standards > 0:
                quality_issues.append(f"{orphaned_standards} orphaned quantitative standards")
                quality_score -= 5
            
            # Calculate overall quality assessment
            quality_rating = "EXCELLENT" if quality_score >= 90 else \
                           "GOOD" if quality_score >= 80 else \
                           "ACCEPTABLE" if quality_score >= 70 else \
                           "POOR"
            
            self.validation_results['data_quality']['quality_assessment'] = {
                'overall_score': quality_score,
                'rating': quality_rating,
                'issues_found': quality_issues,
                'duplicate_provisions': len(duplicates) if duplicates else 0,
                'long_text_provisions': long_texts,
                'invalid_zones': len(invalid_zones) if invalid_zones else 0,
                'invalid_confidence_scores': invalid_confidence,
                'orphaned_standards': orphaned_standards
            }
            
            print(f"[OK] Data quality: {quality_rating} ({quality_score}/100)")
            if quality_issues:
                print("    Issues found:")
                for issue in quality_issues[:5]:  # Show first 5 issues
                    print(f"    - {issue}")
            
            conn.close()
            
        except Exception as e:
            conn.close()
            raise Exception(f"Data quality assessment failed: {e}")
    
    def check_migration_readiness(self):
        """Check if data is ready for migration"""
        
        readiness_checks = []
        blocking_issues = []
        
        # Check 1: Minimum data volume
        total_provisions = self.validation_results['data_quality']['total_provisions']
        if total_provisions < 1000:
            blocking_issues.append(f"Insufficient data volume: {total_provisions} provisions (minimum: 1000)")
        else:
            readiness_checks.append(f"Data volume adequate: {total_provisions:,} provisions")
        
        # Check 2: Zone coverage
        zone_coverage = self.validation_results['data_quality']['zone_coverage']['coverage_rate']
        if zone_coverage < 5:
            blocking_issues.append(f"Very low zone coverage: {zone_coverage}% (minimum: 5%)")
        else:
            readiness_checks.append(f"Zone coverage acceptable: {zone_coverage}%")
        
        # Check 3: Data quality score
        quality_score = self.validation_results['data_quality']['quality_assessment']['overall_score']
        if quality_score < 70:
            blocking_issues.append(f"Data quality too low: {quality_score}/100 (minimum: 70)")
        else:
            readiness_checks.append(f"Data quality sufficient: {quality_score}/100")
        
        # Check 4: Required fields completeness
        completeness = self.validation_results['data_quality']['field_completeness']
        critical_fields = ['provision_text', 'classification_confidence']
        
        for field in critical_fields:
            rate = completeness.get(field, {}).get('completeness_rate', 0)
            if rate < 90:
                blocking_issues.append(f"Low {field} completeness: {rate}% (minimum: 90%)")
            else:
                readiness_checks.append(f"{field} completeness good: {rate}%")
        
        # Overall readiness determination
        migration_ready = len(blocking_issues) == 0
        
        self.validation_results['migration_readiness'] = {
            'ready_for_migration': migration_ready,
            'readiness_checks_passed': readiness_checks,
            'blocking_issues': blocking_issues,
            'total_checks': len(readiness_checks) + len(blocking_issues),
            'passed_checks': len(readiness_checks)
        }
        
        status = "READY" if migration_ready else "NOT READY"
        print(f"[{'OK' if migration_ready else 'FAIL'}] Migration readiness: {status}")
        
        if blocking_issues:
            print("    Blocking issues:")
            for issue in blocking_issues:
                print(f"    - {issue}")
    
    def generate_recommendations(self):
        """Generate recommendations for migration optimization"""
        
        recommendations = []
        
        # Based on data quality assessment
        quality_data = self.validation_results['data_quality']['quality_assessment']
        
        if quality_data['duplicate_provisions'] > 0:
            recommendations.append({
                'type': 'DATA_CLEANUP',
                'priority': 'HIGH',
                'issue': 'Duplicate provisions detected',
                'recommendation': 'Run deduplication process before migration',
                'impact': 'Prevents constraint violations during migration'
            })
        
        if quality_data['invalid_zones'] > 0:
            recommendations.append({
                'type': 'DATA_VALIDATION',
                'priority': 'MEDIUM',
                'issue': 'Invalid zone formats',
                'recommendation': 'Validate and correct zone codes',
                'impact': 'Ensures proper zone-based filtering'
            })
        
        # Based on zone coverage
        zone_coverage = self.validation_results['data_quality']['zone_coverage']['coverage_rate']
        
        if zone_coverage < 20:
            recommendations.append({
                'type': 'MIGRATION_STRATEGY',
                'priority': 'HIGH',
                'issue': f'Low zone coverage: {zone_coverage}%',
                'recommendation': 'Consider zone mapping enhancement or accept limited coverage',
                'impact': 'Affects completeness of authoritative compliance system'
            })
        
        # Migration optimization recommendations
        total_provisions = self.validation_results['data_quality']['total_provisions']
        
        if total_provisions > 10000:
            recommendations.append({
                'type': 'PERFORMANCE',
                'priority': 'MEDIUM',
                'issue': f'Large dataset: {total_provisions:,} provisions',
                'recommendation': 'Use batch processing with progress monitoring',
                'impact': 'Prevents timeout and memory issues during migration'
            })
        
        # Database optimization
        if self.validation_results['database_info']['file_size_mb'] > 100:
            recommendations.append({
                'type': 'DATABASE_OPTIMIZATION',
                'priority': 'LOW',
                'issue': f"Large database: {self.validation_results['database_info']['file_size_mb']} MB",
                'recommendation': 'Consider database cleanup and optimization before migration',
                'impact': 'Improves migration performance'
            })
        
        self.validation_results['recommendations'] = recommendations
        
        print(f"[OK] Generated {len(recommendations)} recommendations")
        for rec in recommendations[:3]:  # Show top 3
            print(f"    {rec['priority']}: {rec['recommendation']}")
    
    def create_validation_report(self):
        """Create comprehensive validation report"""
        
        report = {
            'prp': 'PRP-8D',
            'phase': 'SQLite Source Validation',
            'validation_timestamp': datetime.now().isoformat(),
            'database_path': self.database_path,
            'validation_results': self.validation_results,
            'summary': {
                'migration_ready': self.validation_results['migration_readiness']['ready_for_migration'],
                'data_quality_score': self.validation_results['data_quality']['quality_assessment']['overall_score'],
                'total_provisions': self.validation_results['data_quality']['total_provisions'],
                'zone_coverage_rate': self.validation_results['data_quality']['zone_coverage']['coverage_rate'],
                'recommendations_count': len(self.validation_results['recommendations'])
            }
        }
        
        # Save detailed report
        report_file = f"PRP_8D_SOURCE_VALIDATION_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)
        except Exception as e:
            print(f"Could not save detailed report: {e}")
        
        # Generate summary report
        print(f"\n" + "=" * 50)
        print("SOURCE VALIDATION SUMMARY")
        print("=" * 50)
        
        summary = report['summary']
        readiness_status = "READY FOR MIGRATION" if summary['migration_ready'] else "NOT READY FOR MIGRATION"
        
        print(f"Status: {readiness_status}")
        print(f"Database: {self.database_path}")
        print(f"Provisions: {summary['total_provisions']:,}")
        print(f"Zone Coverage: {summary['zone_coverage_rate']:.1f}%")
        print(f"Quality Score: {summary['data_quality_score']}/100")
        print(f"Recommendations: {summary['recommendations_count']}")
        
        if report_file:
            print(f"Detailed Report: {report_file}")
        
        # Show critical recommendations
        high_priority_recs = [r for r in self.validation_results['recommendations'] if r['priority'] == 'HIGH']
        if high_priority_recs:
            print(f"\nCRITICAL RECOMMENDATIONS:")
            for rec in high_priority_recs:
                print(f"  - {rec['recommendation']}")
        
        if summary['migration_ready']:
            print(f"\n[OK] Source database validated and ready for bulletproof migration")
        else:
            blocking = self.validation_results['migration_readiness']['blocking_issues']
            print(f"\n[FAIL] {len(blocking)} blocking issues must be resolved before migration")
        
        return report

def main():
    """Execute SQLite source validation"""
    
    validator = SQLiteSourceValidator()
    success = validator.validate_complete_source()
    
    # Return True only if ready for migration
    migration_ready = validator.validation_results.get('migration_readiness', {}).get('ready_for_migration', False)
    
    return success and migration_ready

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)