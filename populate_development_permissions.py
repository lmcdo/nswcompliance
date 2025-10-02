#!/usr/bin/env python3
"""
Step 2: Populate development_permissions table

Analyzes existing Exempt & Complying provisions and populates
development_permissions table with permission status for each
zone + development_type combination.

This enables the compliance API to determine if a development:
- Is exempt (no DA required)
- Is complying (CDC required)
- Requires full DA
"""
from db_config import get_connection
import re
from collections import defaultdict

conn = get_connection()
cur = conn.cursor()

print("=" * 80)
print("POPULATING DEVELOPMENT_PERMISSIONS TABLE")
print("=" * 80)

# Step 1: Analyze existing provisions to determine permission logic
print("\n1. ANALYZING EXISTING PROVISIONS")
print("-" * 80)

cur.execute("""
    SELECT
        id,
        document_id,
        ref_number,
        section_header,
        provision_text,
        zone,
        development_type
    FROM regulatory_provisions
    WHERE (document_id ILIKE '%exempt%' OR document_id ILIKE '%complying%')
      AND zone IS NOT NULL
      AND zone != ''
""")

provisions = cur.fetchall()
print(f"Found {len(provisions):,} provisions with zone tags")

# Step 2: Determine permission status based on document structure
print("\n2. DETERMINING PERMISSION STATUS")
print("-" * 80)

# Group provisions by zone + development_type
permission_map = defaultdict(lambda: {
    'exempt': [],
    'complying': [],
    'provisions': []
})

for prov_id, doc_id, ref_num, header, text, zone, dev_type in provisions:
    # Determine permission status from document_id
    # Autoschema split documents into sections - parse section number
    permission_status = None

    # Check document_id for section indicators
    # Section 0-1: Preliminary (not actual development permissions)
    # Section 2: Exempt development
    # Section 3+: Complying development

    section_match = re.search(r'_section_(\d+)', doc_id)
    if section_match:
        section_num = int(section_match.group(1))
        if section_num <= 1:
            continue  # Skip preliminary sections
        elif section_num == 2:
            permission_status = 'exempt'
        elif section_num >= 3:
            permission_status = 'complying'
    else:
        # For non-sectioned documents, check ref_number or text
        if ref_num and '2.' in str(ref_num):
            permission_status = 'exempt'
        elif ref_num and '3' in str(ref_num):
            permission_status = 'complying'

    # Also check development_type field directly
    if dev_type:
        if 'exempt' in dev_type.lower():
            permission_status = 'exempt'
        elif 'complying' in dev_type.lower():
            permission_status = 'complying'

    # Check text content for explicit mentions
    if not permission_status:
        text_lower = text.lower() if text else ''
        if 'exempt development' in text_lower:
            permission_status = 'exempt'
        elif 'complying development' in text_lower:
            permission_status = 'complying'

    if permission_status:
        # Use development_type if available, otherwise infer from text
        dev_type_key = dev_type if dev_type else 'general'

        # Create key: zone + dev_type
        key = (zone, dev_type_key)
        permission_map[key][permission_status].append(prov_id)
        permission_map[key]['provisions'].append({
            'id': prov_id,
            'ref': ref_num,
            'text': text[:200] if text else ''
        })

print(f"Analyzed {len(permission_map)} unique zone + development_type combinations")

# Step 3: Generate permission records
print("\n3. GENERATING PERMISSION RECORDS")
print("-" * 80)

permission_records = []

for (zone, dev_type), statuses in permission_map.items():
    exempt_count = len(statuses['exempt'])
    complying_count = len(statuses['complying'])

    # Determine primary permission status
    if exempt_count > complying_count:
        primary_status = 'exempt'
        provision_ids = statuses['exempt'][:5]  # Take first 5 as examples
    elif complying_count > 0:
        primary_status = 'complying'
        provision_ids = statuses['complying'][:5]
    else:
        primary_status = 'consent_required'
        provision_ids = []

    # Create conditions string
    conditions = f"Based on {exempt_count} exempt + {complying_count} complying provisions"

    permission_records.append({
        'zone': zone,
        'development_type': dev_type,
        'permission_status': primary_status,
        'conditions': conditions,
        'source_provision_ids': ','.join(str(p) for p in provision_ids),
        'source_type': 'SEPP_Exempt_Complying_2008',
        'confidence_score': 0.85 if provision_ids else 0.5
    })

print(f"Generated {len(permission_records)} permission records")

# Display sample records
print("\nSample records to be inserted:")
for i, record in enumerate(permission_records[:10], 1):
    print(f"\n{i}. Zone: {record['zone']}, Dev Type: {record['development_type']}")
    print(f"   Status: {record['permission_status']}")
    print(f"   Conditions: {record['conditions']}")
    print(f"   Confidence: {record['confidence_score']}")

# Step 4: Insert into development_permissions table
print(f"\n4. INSERTING INTO DATABASE")
print("-" * 80)

# First, check if table has records
cur.execute("SELECT COUNT(*) FROM development_permissions WHERE source_type ILIKE '%exempt%'")
existing_count = cur.fetchone()[0]

if existing_count > 0:
    print(f"[WARN] Table already has {existing_count} exempt/complying records")
    response = input("Delete existing and re-import? (yes/no): ")
    if response.lower() == 'yes':
        cur.execute("DELETE FROM development_permissions WHERE source_type ILIKE '%exempt%'")
        conn.commit()
        print(f"[OK] Deleted {existing_count} existing records")
    else:
        print("[SKIP] Import cancelled")
        conn.close()
        exit(0)

# Get next available ID
cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM development_permissions")
next_id = cur.fetchone()[0]
print(f"Next available ID: {next_id}")

# Insert new records with explicit ID
insert_query = """
    INSERT INTO development_permissions
    (id, zone, development_type, permission_status, conditions, source_provision_id,
     source_type, confidence_score, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
    ON CONFLICT (id) DO NOTHING
"""

inserted_count = 0
for i, record in enumerate(permission_records):
    try:
        cur.execute(insert_query, (
            next_id + i,
            record['zone'],
            record['development_type'],
            record['permission_status'],
            record['conditions'],
            record['source_provision_ids'],
            record['source_type'],
            record['confidence_score']
        ))
        inserted_count += 1
    except Exception as e:
        print(f"[ERROR] Failed to insert {record['zone']} + {record['development_type']}: {e}")
        conn.rollback()  # Rollback failed transaction
        # Start new transaction
        conn = get_connection()
        cur = conn.cursor()
        continue

conn.commit()

print(f"\n[OK] Inserted {inserted_count} records into development_permissions")

# Step 5: Verify insertion
print(f"\n5. VERIFICATION")
print("-" * 80)

cur.execute("""
    SELECT
        permission_status,
        COUNT(*) as count
    FROM development_permissions
    WHERE source_type ILIKE '%exempt%'
    GROUP BY permission_status
    ORDER BY count DESC
""")

print("Permission status distribution:")
for status, count in cur.fetchall():
    print(f"  {status:20} {count:,} records")

# Show sample by zone
print("\nSample records by zone:")
cur.execute("""
    SELECT
        zone,
        development_type,
        permission_status
    FROM development_permissions
    WHERE source_type ILIKE '%exempt%'
    ORDER BY zone, development_type
    LIMIT 15
""")

for zone, dev_type, status in cur.fetchall():
    print(f"  {zone:10} {dev_type:30} -> {status}")

# Step 6: Test API query
print(f"\n6. TESTING API QUERY PATTERN")
print("-" * 80)

test_zone = 'R2'
test_dev_type = 'complying_development'

cur.execute("""
    SELECT
        zone,
        development_type,
        permission_status,
        conditions,
        confidence_score
    FROM development_permissions
    WHERE zone = %s
      AND development_type = %s
""", (test_zone, test_dev_type))

result = cur.fetchone()
if result:
    print(f"[OK] API query works!")
    print(f"  Zone: {result[0]}")
    print(f"  Dev Type: {result[1]}")
    print(f"  Status: {result[2]}")
    print(f"  Conditions: {result[3]}")
    print(f"  Confidence: {result[4]}")
else:
    print(f"[WARN] No record found for {test_zone} + {test_dev_type}")

conn.close()

print(f"\n{'='*80}")
print("POPULATION COMPLETE")
print("=" * 80)
print("\nNext steps:")
print("  1. Update API to query development_permissions table")
print("  2. Update UI to display exempt/complying status")
print("  3. Test with real property addresses")
print("=" * 80)
