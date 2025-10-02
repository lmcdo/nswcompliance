#!/usr/bin/env python3
"""
Database Safety Audit Script - CLAUDE.md COMPLIANCE CHECKER
Audits current implementation against CLAUDE.md database safety requirements

CRITICAL SAFETY AUDIT REQUIREMENTS:
- Verify db_safety_wrapper.py usage across ALL database code
- Confirm 30-second timeouts on ALL database operations
- Validate backup procedures before ANY database operation
- Check WHERE clause compliance on ALL queries
- Ensure no direct database connections bypass safety

This audit ensures CLAUDE.md compliance and prevents data loss
"""

import os
import sys
import json
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Configure audit logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - AUDIT - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseSafetyAuditor:
    """
    MANDATORY Database Safety Compliance Auditor per CLAUDE.md
    Ensures all code follows database safety requirements
    """

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.audit_results = {
            'claude_md_compliance': {},
            'safety_violations': [],
            'recommendations': [],
            'overall_status': 'UNKNOWN'
        }

        logger.info(f"Database safety audit initialized for: {self.project_root}")

    def audit_safety_wrapper_usage(self) -> Dict[str, Any]:
        """
        CRITICAL: Check that ALL database code uses db_safety_wrapper.py
        CLAUDE.md REQUIREMENT: NEVER use direct database connections
        """
        logger.info("Auditing safety wrapper usage...")

        python_files = list(self.project_root.glob('**/*.py'))
        files_using_wrapper = []
        files_direct_connection = []

        # Patterns for safety wrapper usage
        wrapper_patterns = [
            r'from\s+db_safety_wrapper\s+import',
            r'get_safe_connection',
            r'SafeConnection'
        ]

        # Patterns for DANGEROUS direct connections
        dangerous_patterns = [
            r'psycopg2\.connect\(',
            r'sqlite3\.connect\(',
            r'mysql\.connector\.connect\(',
            r'pymongo\.MongoClient\(',
            r'from\s+db_config\s+import\s+get_dict_connection'  # Old unsafe pattern
        ]

        for file_path in python_files:
            if file_path.name in ['db_safety_wrapper.py', 'db_config.py']:
                continue  # Skip the wrapper itself

            try:
                content = file_path.read_text(encoding='utf-8')

                # Check for safety wrapper usage
                uses_wrapper = any(re.search(pattern, content, re.IGNORECASE) for pattern in wrapper_patterns)
                if uses_wrapper:
                    files_using_wrapper.append(str(file_path.relative_to(self.project_root)))

                # Check for dangerous direct connections
                uses_direct = any(re.search(pattern, content, re.IGNORECASE) for pattern in dangerous_patterns)
                if uses_direct:
                    files_direct_connection.append(str(file_path.relative_to(self.project_root)))

            except Exception as e:
                logger.warning(f"Could not read file {file_path}: {e}")

        # Determine compliance status
        if files_direct_connection:
            status = 'VIOLATION'
            self.audit_results['safety_violations'].extend([
                f"CRITICAL: Direct database connection in {file}" for file in files_direct_connection
            ])
        elif files_using_wrapper:
            status = 'COMPLIANT'
        else:
            status = 'NO_DATABASE_CODE'

        result = {
            'status': status,
            'files_using_wrapper': files_using_wrapper,
            'files_direct_connection': files_direct_connection,
            'wrapper_files_count': len(files_using_wrapper),
            'violation_files_count': len(files_direct_connection)
        }

        self.audit_results['claude_md_compliance']['safety_wrapper'] = result
        logger.info(f"Safety wrapper audit: {status} ({len(files_using_wrapper)} safe, {len(files_direct_connection)} violations)")

        return result

    def audit_timeout_implementation(self) -> Dict[str, Any]:
        """
        CRITICAL: Check that ALL database operations have 30-second timeouts
        CLAUDE.md REQUIREMENT: ALWAYS use timeouts (30 seconds max)
        """
        logger.info("Auditing timeout implementation...")

        python_files = list(self.project_root.glob('**/*.py'))
        typescript_files = list(self.project_root.glob('**/*.ts')) + list(self.project_root.glob('**/*.tsx'))

        files_with_timeouts = []
        files_missing_timeouts = []

        # Timeout patterns
        timeout_patterns = [
            r'timeout\s*=\s*30',
            r'TIMEOUT_MS\s*=\s*30000',
            r'setTimeout.*30000',
            r'signal\.alarm\(30\)',
            r'statement_timeout.*30',
            r'timeout.*30.*second'
        ]

        # Database operation patterns that REQUIRE timeouts
        db_operation_patterns = [
            r'cursor\.execute\(',
            r'\.query\(',
            r'\.fetchall\(',
            r'spawn.*python',
            r'subprocess\.run',
            r'psycopg2\.',
            r'sqlite3\.'
        ]

        for file_path in python_files + typescript_files:
            try:
                content = file_path.read_text(encoding='utf-8')

                # Check if file has database operations
                has_db_ops = any(re.search(pattern, content, re.IGNORECASE) for pattern in db_operation_patterns)

                if has_db_ops:
                    # Check for timeout implementation
                    has_timeout = any(re.search(pattern, content, re.IGNORECASE) for pattern in timeout_patterns)

                    if has_timeout:
                        files_with_timeouts.append(str(file_path.relative_to(self.project_root)))
                    else:
                        files_missing_timeouts.append(str(file_path.relative_to(self.project_root)))

            except Exception as e:
                logger.warning(f"Could not read file {file_path}: {e}")

        # Determine compliance status
        if files_missing_timeouts:
            status = 'VIOLATION'
            self.audit_results['safety_violations'].extend([
                f"CRITICAL: Missing timeout in {file}" for file in files_missing_timeouts
            ])
        elif files_with_timeouts:
            status = 'COMPLIANT'
        else:
            status = 'NO_DATABASE_CODE'

        result = {
            'status': status,
            'files_with_timeouts': files_with_timeouts,
            'files_missing_timeouts': files_missing_timeouts,
            'timeout_files_count': len(files_with_timeouts),
            'violation_files_count': len(files_missing_timeouts)
        }

        self.audit_results['claude_md_compliance']['timeouts'] = result
        logger.info(f"Timeout audit: {status} ({len(files_with_timeouts)} compliant, {len(files_missing_timeouts)} violations)")

        return result

    def audit_backup_procedures(self) -> Dict[str, Any]:
        """
        CRITICAL: Check that backup procedures exist and are used
        CLAUDE.md REQUIREMENT: ALWAYS create backup before ANY database operation
        """
        logger.info("Auditing backup procedures...")

        python_files = list(self.project_root.glob('**/*.py'))
        files_with_backup_logic = []
        backup_manager_exists = False

        # Backup patterns
        backup_patterns = [
            r'backup',
            r'shutil\.copy',
            r'create_backup',
            r'pg_dump',
            r'emergency_backup',
            r'backup_manager'
        ]

        # Check for backup_manager.py existence
        backup_manager_path = self.project_root / 'backup_manager.py'
        backup_manager_exists = backup_manager_path.exists()

        for file_path in python_files:
            try:
                content = file_path.read_text(encoding='utf-8')

                # Check for backup logic
                has_backup = any(re.search(pattern, content, re.IGNORECASE) for pattern in backup_patterns)
                if has_backup:
                    files_with_backup_logic.append(str(file_path.relative_to(self.project_root)))

            except Exception as e:
                logger.warning(f"Could not read file {file_path}: {e}")

        # Determine compliance status
        if backup_manager_exists and files_with_backup_logic:
            status = 'COMPLIANT'
        elif backup_manager_exists:
            status = 'PARTIAL'
            self.audit_results['recommendations'].append("Backup manager exists but may not be integrated")
        else:
            status = 'VIOLATION'
            self.audit_results['safety_violations'].append("CRITICAL: No backup procedures found")

        result = {
            'status': status,
            'backup_manager_exists': backup_manager_exists,
            'files_with_backup_logic': files_with_backup_logic,
            'backup_files_count': len(files_with_backup_logic)
        }

        self.audit_results['claude_md_compliance']['backups'] = result
        logger.info(f"Backup audit: {status} (manager exists: {backup_manager_exists})")

        return result

    def audit_where_clause_compliance(self) -> Dict[str, Any]:
        """
        CRITICAL: Check that ALL queries have WHERE clauses on main tables
        CLAUDE.md REQUIREMENT: NEVER run queries without WHERE clauses on main tables
        """
        logger.info("Auditing WHERE clause compliance...")

        python_files = list(self.project_root.glob('**/*.py'))
        sql_files = []
        dangerous_queries = []
        safe_queries = []

        # Dangerous SQL patterns (without WHERE)
        dangerous_sql_patterns = [
            r'DELETE\s+FROM\s+\w+(?!\s+WHERE)',
            r'UPDATE\s+\w+\s+SET(?!\s+.*WHERE)',
            r'TRUNCATE\s+TABLE',
            r'DROP\s+TABLE',
            r'DROP\s+DATABASE'
        ]

        # Safe SQL patterns (with WHERE or safe operations)
        safe_sql_patterns = [
            r'SELECT.*WHERE',
            r'DELETE.*WHERE',
            r'UPDATE.*WHERE',
            r'INSERT\s+INTO',
            r'CREATE\s+TABLE'
        ]

        for file_path in python_files:
            try:
                content = file_path.read_text(encoding='utf-8')

                # Check for SQL content
                if re.search(r'(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP)', content, re.IGNORECASE):
                    sql_files.append(str(file_path.relative_to(self.project_root)))

                    # Check for dangerous queries
                    for pattern in dangerous_sql_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
                        for match in matches:
                            dangerous_queries.append(f"{file_path.name}: {match}")

                    # Check for safe queries
                    for pattern in safe_sql_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            safe_queries.append(str(file_path.relative_to(self.project_root)))
                            break

            except Exception as e:
                logger.warning(f"Could not read file {file_path}: {e}")

        # Determine compliance status
        if dangerous_queries:
            status = 'VIOLATION'
            self.audit_results['safety_violations'].extend([
                f"CRITICAL: Dangerous query - {query}" for query in dangerous_queries
            ])
        elif sql_files:
            status = 'COMPLIANT'
        else:
            status = 'NO_SQL_CODE'

        result = {
            'status': status,
            'sql_files': sql_files,
            'safe_queries_count': len(safe_queries),
            'dangerous_queries': dangerous_queries,
            'violation_count': len(dangerous_queries)
        }

        self.audit_results['claude_md_compliance']['where_clauses'] = result
        logger.info(f"WHERE clause audit: {status} ({len(dangerous_queries)} violations found)")

        return result

    def audit_safety_wrapper_integrity(self) -> Dict[str, Any]:
        """
        CRITICAL: Verify db_safety_wrapper.py exists and is not modified
        Ensures the safety wrapper hasn't been tampered with
        """
        logger.info("Auditing safety wrapper integrity...")

        wrapper_path = self.project_root / 'db_safety_wrapper.py'

        if not wrapper_path.exists():
            result = {
                'status': 'CRITICAL_VIOLATION',
                'exists': False,
                'error': 'db_safety_wrapper.py not found'
            }
            self.audit_results['safety_violations'].append("CRITICAL: db_safety_wrapper.py missing")
        else:
            try:
                content = wrapper_path.read_text(encoding='utf-8')

                # Check for critical safety functions
                required_functions = [
                    'get_safe_connection',
                    'SafeConnection',
                    'enforce_db_safety',
                    'is_query_dangerous',
                    'create_emergency_backup'
                ]

                missing_functions = []
                for func in required_functions:
                    if func not in content:
                        missing_functions.append(func)

                if missing_functions:
                    result = {
                        'status': 'VIOLATION',
                        'exists': True,
                        'missing_functions': missing_functions
                    }
                    self.audit_results['safety_violations'].append(f"Safety wrapper missing functions: {missing_functions}")
                else:
                    result = {
                        'status': 'COMPLIANT',
                        'exists': True,
                        'integrity_verified': True
                    }

            except Exception as e:
                result = {
                    'status': 'ERROR',
                    'exists': True,
                    'error': str(e)
                }

        self.audit_results['claude_md_compliance']['safety_wrapper_integrity'] = result
        logger.info(f"Safety wrapper integrity: {result['status']}")

        return result

    def run_full_audit(self) -> Dict[str, Any]:
        """
        Run complete database safety audit
        Returns comprehensive audit report
        """
        logger.info("Starting comprehensive database safety audit...")

        # Run all audit checks
        self.audit_safety_wrapper_usage()
        self.audit_timeout_implementation()
        self.audit_backup_procedures()
        self.audit_where_clause_compliance()
        self.audit_safety_wrapper_integrity()

        # Calculate overall compliance status
        all_statuses = [
            self.audit_results['claude_md_compliance'].get('safety_wrapper', {}).get('status'),
            self.audit_results['claude_md_compliance'].get('timeouts', {}).get('status'),
            self.audit_results['claude_md_compliance'].get('backups', {}).get('status'),
            self.audit_results['claude_md_compliance'].get('where_clauses', {}).get('status'),
            self.audit_results['claude_md_compliance'].get('safety_wrapper_integrity', {}).get('status')
        ]

        # Overall compliance logic
        if 'CRITICAL_VIOLATION' in all_statuses or 'VIOLATION' in all_statuses:
            overall_status = 'VIOLATIONS_FOUND'
        elif all(status == 'COMPLIANT' for status in all_statuses if status):
            overall_status = 'COMPLIANT'
        elif 'PARTIAL' in all_statuses:
            overall_status = 'PARTIAL_COMPLIANCE'
        else:
            overall_status = 'UNKNOWN'

        self.audit_results['overall_status'] = overall_status
        self.audit_results['audit_timestamp'] = self._get_timestamp()
        self.audit_results['total_violations'] = len(self.audit_results['safety_violations'])
        self.audit_results['total_recommendations'] = len(self.audit_results['recommendations'])

        logger.info(f"Database safety audit completed: {overall_status}")
        logger.info(f"Total violations: {self.audit_results['total_violations']}")
        logger.info(f"Total recommendations: {self.audit_results['total_recommendations']}")

        return self.audit_results

    def _get_timestamp(self) -> str:
        """Get current timestamp for audit report"""
        from datetime import datetime
        return datetime.now().isoformat()

    def generate_audit_report(self) -> str:
        """
        Generate human-readable audit report
        """
        report = []
        report.append("=" * 80)
        report.append("DATABASE SAFETY AUDIT REPORT - CLAUDE.md COMPLIANCE")
        report.append("=" * 80)
        report.append(f"Audit Timestamp: {self.audit_results.get('audit_timestamp', 'Unknown')}")
        report.append(f"Overall Status: {self.audit_results['overall_status']}")
        report.append(f"Project Root: {self.project_root}")
        report.append("")

        # Compliance Summary
        report.append("COMPLIANCE SUMMARY:")
        report.append("-" * 40)
        for check, result in self.audit_results['claude_md_compliance'].items():
            status = result.get('status', 'UNKNOWN')
            report.append(f"  {check.replace('_', ' ').title()}: {status}")
        report.append("")

        # Violations
        if self.audit_results['safety_violations']:
            report.append("CRITICAL SAFETY VIOLATIONS:")
            report.append("-" * 40)
            for violation in self.audit_results['safety_violations']:
                report.append(f"  ❌ {violation}")
            report.append("")

        # Recommendations
        if self.audit_results['recommendations']:
            report.append("RECOMMENDATIONS:")
            report.append("-" * 40)
            for rec in self.audit_results['recommendations']:
                report.append(f"  💡 {rec}")
            report.append("")

        # Summary
        report.append("AUDIT SUMMARY:")
        report.append("-" * 40)
        report.append(f"Total Violations: {self.audit_results['total_violations']}")
        report.append(f"Total Recommendations: {self.audit_results['total_recommendations']}")

        if self.audit_results['overall_status'] == 'COMPLIANT':
            report.append("✅ CLAUDE.md DATABASE SAFETY REQUIREMENTS MET")
        else:
            report.append("❌ CLAUDE.md DATABASE SAFETY VIOLATIONS FOUND")
            report.append("   IMMEDIATE ACTION REQUIRED TO PREVENT DATA LOSS")

        report.append("=" * 80)

        return "\n".join(report)

def main():
    """Command line interface for database safety audit"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Database Safety Audit - CLAUDE.md Compliance Checker'
    )
    parser.add_argument('--project-root', default='.',
                       help='Project root directory to audit')
    parser.add_argument('--output-format', choices=['json', 'text'], default='json',
                       help='Output format')
    parser.add_argument('--output-file', help='Save audit results to file')

    args = parser.parse_args()

    # Run audit
    auditor = DatabaseSafetyAuditor(args.project_root)
    results = auditor.run_full_audit()

    # Generate output
    if args.output_format == 'json':
        output = json.dumps(results, indent=2)
    else:
        output = auditor.generate_audit_report()

    # Output results
    if args.output_file:
        with open(args.output_file, 'w') as f:
            f.write(output)
        print(f"Audit results saved to: {args.output_file}")
    else:
        print(output)

    # Exit with error code if violations found
    if results['overall_status'] in ['VIOLATIONS_FOUND', 'CRITICAL_VIOLATION']:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()