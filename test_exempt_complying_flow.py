#!/usr/bin/env python3
"""
Test the end-to-end data flow for exempt/complying codes
Simulates what the API does when user searches for property + development type
"""
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

print('=' * 80)
print('EXEMPT/COMPLYING WORKFLOW TEST')
print('=' * 80)

# Test scenario: User searches for "30 Illawarra Road" (R2 zone) + "dwelling_house"
test_zone = 'R2'
test_dev_type = 'dwelling_house'

print(f'\nTest Scenario:')
print(f'  Zone: {test_zone}')
print(f'  Development Type: {test_dev_type}')
print('-' * 80)

# STEP 1: Check LEP base permissibility
print('\nSTEP 1: Check LEP Base Permissibility')
print('-' * 80)

cur.execute('''
SELECT
    zone,
    development_type,
    permission_status,
    conditions,
    source_type,
    confidence_score
FROM development_permissions
WHERE zone = %s
AND development_type = %s
AND source_type NOT ILIKE '%%exempt%%'
ORDER BY
    CASE source_type
        WHEN 'nsw_standard' THEN 1
        WHEN 'existing' THEN 2
        ELSE 3
    END,
    confidence_score DESC
LIMIT 1;
''', (test_zone, test_dev_type))

lep_result = cur.fetchone()
if lep_result:
    print(f'  LEP Permission: {lep_result[2]}')
    print(f'  Source: {lep_result[4]}')
    print(f'  Conditions: {lep_result[3]}')
    base_permission = lep_result[2]
else:
    print('  [NOT FOUND] No LEP permission found')
    base_permission = None

# STEP 2: If permitted, check SEPP exempt/complying
if base_permission == 'permitted':
    print('\nSTEP 2: Check SEPP Exempt/Complying Pathway')
    print('-' * 80)

    cur.execute('''
    SELECT
        zone,
        development_type,
        permission_status,
        conditions,
        source_type,
        confidence_score
    FROM development_permissions
    WHERE zone = %s
    AND (development_type = %s OR development_type = 'general')
    AND source_type ILIKE '%%exempt%%'
    ORDER BY
        CASE WHEN development_type = %s THEN 1 ELSE 2 END,
        confidence_score DESC
    LIMIT 1;
    ''', (test_zone, test_dev_type, test_dev_type))

    sepp_result = cur.fetchone()
    if sepp_result:
        print(f'  SEPP Status: {sepp_result[2]}')
        print(f'  Source: {sepp_result[4]}')
        print(f'  Conditions: {sepp_result[3]}')
        final_status = sepp_result[2]
    else:
        print('  [NOT FOUND] No SEPP exempt/complying pathway')
        print('  Final Status: consent_required (DA needed)')
        final_status = 'consent_required'
else:
    print(f'\nSTEP 2: Skipped (base permission is {base_permission})')
    final_status = base_permission or 'consent_required'

# STEP 3: Get associated provisions if exempt/complying
print(f'\n\nSTEP 3: Get Exempt/Complying Provisions')
print('-' * 80)

cur.execute('''
SELECT
    rp.id,
    rp.ref_number,
    LEFT(rp.provision_text, 100) as text_preview,
    rp.document_id,
    COUNT(dc.id) as control_count
FROM regulatory_provisions_canonical rp
LEFT JOIN development_controls dc ON dc.provision_id = rp.id::text
WHERE rp.zone LIKE '%%' || %s || '%%'
  AND (rp.document_id LIKE '%%Exempt%%' OR rp.document_id LIKE '%%Complying%%')
  AND (rp.development_type = %s OR rp.development_type = 'general' OR rp.development_type IS NULL)
GROUP BY rp.id, rp.ref_number, rp.provision_text, rp.document_id
LIMIT 10;
''', (test_zone, test_dev_type))

provisions = cur.fetchall()
if provisions:
    print(f'  Found {len(provisions)} relevant provisions:')
    for prov in provisions[:5]:
        print(f'\n    ID: {prov[0]}')
        print(f'    Ref: {prov[1]}')
        print(f'    Text: {prov[2]}...')
        print(f'    Controls: {prov[4]}')
        doc_short = prov[3][:60] if prov[3] else 'N/A'
        print(f'    Doc: {doc_short}...')
else:
    print('  [WARNING] No exempt/complying provisions found for this zone+dev_type')

# STEP 4: Check if controls exist for those provisions
print(f'\n\nSTEP 4: Check Development Controls')
print('-' * 80)

if provisions:
    provision_ids = [str(p[0]) for p in provisions]
    ids_list = ','.join([f"'{pid}'" for pid in provision_ids])

    cur.execute(f'''
    SELECT
        control_type,
        COUNT(*) as count
    FROM development_controls
    WHERE provision_id IN ({ids_list})
    GROUP BY control_type
    ORDER BY count DESC;
    ''')

    controls = cur.fetchall()
    if controls:
        print('  Controls by type:')
        for ctrl in controls:
            print(f'    {ctrl[0]:20s}: {ctrl[1]} controls')
    else:
        print('  [WARNING] No controls found for exempt/complying provisions')
else:
    print('  Skipped (no provisions to check)')

# STEP 5: Check orphaned controls
print(f'\n\nSTEP 5: Check for Orphaned Controls')
print('-' * 80)

cur.execute('''
SELECT COUNT(*)
FROM development_controls dc
WHERE dc.provision_id IN (
    SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
);
''')
orphaned = cur.fetchone()[0]
if orphaned > 0:
    print(f'  [WARNING] {orphaned:,} controls point to non-canonical provisions')
    print('  These will be invisible when using regulatory_provisions_canonical view')
else:
    print(f'  Good! No orphaned controls found')

# SUMMARY
print('\n\n' + '=' * 80)
print('WORKFLOW SUMMARY')
print('=' * 80)
print(f'  Zone: {test_zone}')
print(f'  Dev Type: {test_dev_type}')
print(f'  LEP Base Permission: {base_permission or "NOT FOUND"}')
print(f'  Final Status: {final_status}')
print(f'  Provisions Found: {len(provisions) if provisions else 0}')
print(f'  Controls Attached: {"Yes" if controls else "No"}')
print(f'  Orphaned Controls: {orphaned:,}')

# DIAGNOSIS
print('\n' + '=' * 80)
print('DIAGNOSIS')
print('=' * 80)

issues = []

if not lep_result:
    issues.append('[ISSUE 1] No LEP base permission data for this zone+dev_type')

if base_permission == 'permitted' and not sepp_result:
    issues.append('[ISSUE 2] Permitted but no SEPP exempt/complying pathway defined')

if not provisions:
    issues.append('[ISSUE 3] No exempt/complying provisions found in database')

if provisions and not controls:
    issues.append('[ISSUE 4] Provisions exist but no controls attached')

if orphaned > 0:
    issues.append(f'[ISSUE 5] {orphaned:,} orphaned controls need to be re-linked to canonical provisions')

if issues:
    print('\nIssues Found:')
    for issue in issues:
        print(f'  {issue}')
else:
    print('\n  All checks passed! Workflow is functional.')

conn.close()

print('\n' + '=' * 80)
