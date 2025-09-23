#!/usr/bin/env python3
"""Audit current version implementation status"""

import sys
import os
sys.path.append('.')
from db_config import get_connection

def audit_version_implementation():
 conn = get_connection()
 cursor = conn.cursor()

 print('=== CURRENT VERSION IMPLEMENTATION AUDIT ===\n')

 # 1. Check version schema exists
 cursor.execute("""
 SELECT table_name FROM information_schema.tables
 WHERE table_schema = 'versions'
 ORDER BY table_name
 """)
 version_tables = [row[0] for row in cursor.fetchall()]
 print(f'Version schema tables: {version_tables}\n')

 # 2. Check provision version columns
 cursor.execute("""
 SELECT column_name, data_type FROM information_schema.columns
 WHERE table_name = 'regulatory_provisions'
 AND column_name LIKE '%version%'
 ORDER BY column_name
 """)
 version_columns = cursor.fetchall()
 print('Provision version columns:')
 for col in version_columns:
 print(f' {col[0]} ({col[1]})')
 print()

 # 3. Check document versions data
 cursor.execute('SELECT COUNT(*) FROM versions.document_versions')
 doc_versions_count = cursor.fetchone()[0]
 print(f'Total document versions: {doc_versions_count}')

 if doc_versions_count > 0:
 cursor.execute("""
 SELECT document_type, document_identifier, version_number, version_status, effective_date
 FROM versions.document_versions
 ORDER BY created_at DESC
 LIMIT 5
 """)
 print('\nRecent document versions:')
 for row in cursor.fetchall():
 print(f' {row[0]:4} | {row[1]:30} | {row[2]:8} | {row[3]:8} | {row[4]}')

 # 4. Check provision versioning status
 cursor.execute("""
 SELECT
 COUNT(*) as total_provisions,
 COUNT(version_id) as provisions_with_version_id,
 COUNT(CASE WHEN is_current = true THEN 1 END) as current_provisions,
 COUNT(CASE WHEN is_current = false THEN 1 END) as non_current_provisions,
 COUNT(CASE WHEN is_current IS NULL THEN 1 END) as null_current_provisions
 FROM regulatory_provisions
 """)
 provision_stats = cursor.fetchone()
 print(f'\nProvision versioning status:')
 print(f' Total provisions: {provision_stats[0]}')
 print(f' With version_id: {provision_stats[1]}')
 print(f' Marked current: {provision_stats[2]}')
 print(f' Marked non-current: {provision_stats[3]}')
 print(f' Unmarked (NULL): {provision_stats[4]}')

 # 5. Check version_id linkage
 if provision_stats[1] > 0:
 cursor.execute("""
 SELECT
 dv.document_type,
 dv.version_status,
 COUNT(rp.id) as provision_count
 FROM regulatory_provisions rp
 JOIN versions.document_versions dv ON rp.version_id = dv.id
 GROUP BY dv.document_type, dv.version_status
 ORDER BY dv.document_type, dv.version_status
 """)
 print(f'\nProvisions linked to document versions:')
 for row in cursor.fetchall():
 print(f' {row[0]} {row[1]}: {row[2]} provisions')

 # 6. Check for unversioned provisions
 cursor.execute("""
 SELECT COUNT(*) FROM regulatory_provisions
 WHERE version_id IS NULL
 """)
 unversioned_count = cursor.fetchone()[0]
 print(f'\nUnversioned provisions: {unversioned_count}')

 # 7. Sample provision version data
 cursor.execute("""
 SELECT
 rp.id,
 rp.document_id,
 rp.version_id,
 rp.is_current,
 dv.version_number,
 dv.version_status
 FROM regulatory_provisions rp
 LEFT JOIN versions.document_versions dv ON rp.version_id = dv.id
 LIMIT 5
 """)
 print(f'\nSample provision version linkage:')
 print(' Provision ID | Document ID | Version ID | is_current | Version # | Status')
 print(' ' + '-' * 80)
 for row in cursor.fetchall():
 print(f' {str(row[0]):11} | {str(row[1])[:15]:15} | {str(row[2]):9} | {str(row[3]):9} | {str(row[4]):8} | {str(row[5]):8}')

 conn.close()

if __name__ == "__main__":
 audit_version_implementation()