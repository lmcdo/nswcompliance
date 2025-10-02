#!/usr/bin/env python3
"""
Diagnose current state of exempt/complying codes in database
Check: provisions, controls, permissions, and data flow
"""
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

print('=' * 80)
print('CURRENT EXEMPT/COMPLYING CODES DIAGNOSIS')
print('=' * 80)

# 1. Check if canonical view is working
print('\n1. DATABASE STATE:')
print('-' * 80)
cur.execute('''
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE is_canonical = TRUE) as canonical,
  COUNT(*) FILTER (WHERE is_canonical = FALSE) as duplicates
FROM regulatory_provisions;
''')
row = cur.fetchone()
print(f'  Total provisions: {row[0]:,}')
print(f'  Canonical: {row[1]:,} ({row[1]/row[0]*100:.1f}%)')
print(f'  Duplicates: {row[2]:,} ({row[2]/row[0]*100:.1f}%)')

# 2. Check exempt/complying SEPP provisions
print('\n2. EXEMPT/COMPLYING SEPP PROVISIONS:')
print('-' * 80)
cur.execute('''
SELECT
  COUNT(*) as total_provisions,
  COUNT(*) FILTER (WHERE is_canonical = TRUE) as canonical
FROM regulatory_provisions
WHERE document_id LIKE '%Exempt%' OR document_id LIKE '%Complying%';
''')
row = cur.fetchone()
if row[0] > 0:
    print(f'  Total Exempt/Complying provisions: {row[0]:,}')
    print(f'  Canonical: {row[1]:,}')
else:
    print('  [WARNING] No Exempt/Complying provisions found!')

# 3. Check development_permissions table
print('\n3. DEVELOPMENT PERMISSIONS TABLE:')
print('-' * 80)
cur.execute('SELECT COUNT(*) FROM development_permissions;')
perm_count = cur.fetchone()[0]
print(f'  Total permissions: {perm_count:,}')

if perm_count > 0:
    cur.execute('''
    SELECT
        permission_status,
        COUNT(*) as count
    FROM development_permissions
    GROUP BY permission_status
    ORDER BY count DESC;
    ''')
    print('  By status:')
    for row in cur.fetchall():
        print(f'    {row[0]:20s}: {row[1]:,}')

    # Sample
    cur.execute('''
    SELECT zone, development_type, permission_status, conditions
    FROM development_permissions
    WHERE permission_status IN ('exempt', 'complying')
    LIMIT 5;
    ''')
    print('\n  Sample exempt/complying permissions:')
    for row in cur.fetchall():
        print(f'    Zone {row[0]}, Dev: {row[1]:20s} -> {row[2]}')
else:
    print('  [WARNING] No permissions found!')

# 4. Check development_controls
print('\n4. DEVELOPMENT CONTROLS:')
print('-' * 80)
cur.execute('SELECT COUNT(*) FROM development_controls;')
ctrl_count = cur.fetchone()[0]
print(f'  Total controls: {ctrl_count:,}')

# Check if any controls are orphaned (point to non-canonical)
cur.execute('''
SELECT COUNT(*)
FROM development_controls dc
WHERE dc.provision_id IN (
    SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
);
''')
orphaned = cur.fetchone()[0]
if orphaned > 0:
    print(f'  [WARNING] Orphaned controls (point to duplicates): {orphaned:,}')
else:
    print(f'  Orphaned controls: 0 (good!)')

# 5. Check canonical view
print('\n5. CANONICAL VIEW CHECK:')
print('-' * 80)
cur.execute('''
SELECT COUNT(*) FROM regulatory_provisions_canonical;
''')
canonical_view_count = cur.fetchone()[0]
print(f'  Provisions in canonical view: {canonical_view_count:,}')

# 6. Test query: Can we get exempt provisions for a property?
print('\n6. TEST QUERY - Exempt provisions for R2 zone:')
print('-' * 80)
cur.execute('''
SELECT
    rp.ref_number,
    rp.provision_text,
    COUNT(dc.id) as control_count
FROM regulatory_provisions_canonical rp
LEFT JOIN development_controls dc ON dc.provision_id = rp.id::text
WHERE rp.zone LIKE '%R2%'
  AND (rp.document_id LIKE '%Exempt%' OR rp.document_id LIKE '%Complying%')
GROUP BY rp.id, rp.ref_number, rp.provision_text
LIMIT 5;
''')
results = cur.fetchall()
if results:
    print(f'  Found {len(results)} provisions (showing first 5):')
    for row in results:
        ref = row[0][:30] if row[0] else 'N/A'
        text = row[1][:60] if row[1] else 'N/A'
        print(f'    {ref:32s}: {row[2]} controls')
        print(f'      Text: {text}...')
else:
    print('  [WARNING] No exempt/complying provisions found for R2 zone!')

# 7. Check document types in database
print('\n7. DOCUMENT TYPES IN DATABASE:')
print('-' * 80)
cur.execute('''
SELECT
    CASE
        WHEN document_id LIKE '%SEPP%' THEN 'SEPP'
        WHEN document_id LIKE '%LEP%' THEN 'LEP'
        WHEN document_id LIKE '%DCP%' THEN 'DCP'
        ELSE 'Other'
    END as doc_type,
    COUNT(*) as count,
    COUNT(*) FILTER (WHERE is_canonical = TRUE) as canonical
FROM regulatory_provisions
GROUP BY doc_type
ORDER BY count DESC;
''')
print('  By document type:')
for row in cur.fetchall():
    print(f'    {row[0]:10s}: {row[1]:6,} total, {row[2]:6,} canonical')

# 8. Check zone coverage
print('\n8. ZONE COVERAGE:')
print('-' * 80)
cur.execute('''
SELECT
    zone,
    COUNT(*) as provision_count
FROM regulatory_provisions_canonical
WHERE zone IS NOT NULL AND zone != ''
GROUP BY zone
ORDER BY provision_count DESC
LIMIT 10;
''')
print('  Top 10 zones by provision count:')
for row in cur.fetchall():
    zone = row[0][:20] if row[0] else 'N/A'
    print(f'    {zone:22s}: {row[1]:,} provisions')

# 9. Check development_type tagging
print('\n9. DEVELOPMENT TYPE COVERAGE:')
print('-' * 80)
cur.execute('''
SELECT
    development_type,
    COUNT(*) as provision_count
FROM regulatory_provisions_canonical
WHERE development_type IS NOT NULL AND development_type != ''
GROUP BY development_type
ORDER BY provision_count DESC
LIMIT 10;
''')
print('  Top 10 development types:')
for row in cur.fetchall():
    dev_type = row[0][:30] if row[0] else 'N/A'
    print(f'    {dev_type:32s}: {row[1]:,} provisions')

conn.close()

print('\n' + '=' * 80)
print('DIAGNOSIS COMPLETE')
print('=' * 80)
