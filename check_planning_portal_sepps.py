from db_config import get_connection

c = get_connection()
cur = c.cursor()

print("=== CHECKING PLANNING PORTAL SEPP DETECTIONS ===\n")

# 1. Thermal Energy from Waste Prohibition Map
print("1. THERMAL ENERGY FROM WASTE PROHIBITION MAP\n")
print("   Planning Portal: Transport and Infrastructure Amendment (Thermal Energy from Waste) 2022")
print("   Map Type: TEW\n")

cur.execute("""
    SELECT id, provision_text, ref_number, document_id
    FROM regulatory_provisions
    WHERE provision_text ILIKE '%thermal%waste%'
    OR provision_text ILIKE '%energy from waste%'
    OR provision_text ILIKE '%thermal energy%prohibition%'
    LIMIT 10
""")
rows = cur.fetchall()
if rows:
    print(f"   Found {len(rows)} provisions:\n")
    for row in rows:
        print(f"   ID: {row[0]} | Ref: {row[2]}")
        print(f"   Doc: {row[3]}")
        print(f"   Text: {row[1][:150]}...")
        print()
else:
    print("   NOT FOUND IN DATABASE\n")

print("="*80 + "\n")

# 2. Climate Zones for BASIX Alterations Map
print("2. CLIMATE ZONES FOR BASIX ALTERATIONS MAP\n")
print("   Planning Portal: SEPP (Sustainable Buildings) 2022")
print("   Map Type: BAL")
print("   Label: INNER WEST\n")

cur.execute("""
    SELECT id, provision_text, ref_number, document_id
    FROM regulatory_provisions
    WHERE document_id LIKE '%Sustainable_Buildings%'
    AND (provision_text ILIKE '%basix%alterations%'
         OR provision_text ILIKE '%climate zone%alterations%')
    LIMIT 10
""")
rows = cur.fetchall()
if rows:
    print(f"   Found {len(rows)} provisions:\n")
    for row in rows:
        print(f"   ID: {row[0]} | Ref: {row[2]}")
        print(f"   Text: {row[1][:200]}...")
        print()
else:
    print("   NOT FOUND - Checking for any BASIX alterations provisions...\n")
    cur.execute("""
        SELECT id, provision_text, ref_number, document_id
        FROM regulatory_provisions
        WHERE provision_text ILIKE '%alterations%additions%'
        AND document_id LIKE '%Sustainable%'
        LIMIT 5
    """)
    rows = cur.fetchall()
    if rows:
        for row in rows:
            print(f"   ID: {row[0]} | Ref: {row[2]}")
            print(f"   Text: {row[1][:200]}...")
            print()
    else:
        print("   NOT FOUND IN DATABASE\n")

print("="*80 + "\n")

# 3. Climate Zones for BASIX Buildings Map
print("3. CLIMATE ZONES FOR BASIX BUILDINGS MAP\n")
print("   Planning Portal: SEPP (Sustainable Buildings) 2022")
print("   Map Type: CLM")
print("   Label: 2049\n")

cur.execute("""
    SELECT id, provision_text, ref_number, document_id
    FROM regulatory_provisions
    WHERE document_id LIKE '%Sustainable_Buildings%'
    AND (provision_text ILIKE '%climate zone%'
         OR provision_text ILIKE '%climate map%')
    LIMIT 10
""")
rows = cur.fetchall()
if rows:
    print(f"   Found {len(rows)} provisions:\n")
    for row in rows:
        print(f"   ID: {row[0]} | Ref: {row[2]}")
        print(f"   Text: {row[1][:200]}...")
        print()
else:
    print("   NOT FOUND IN DATABASE\n")

print("="*80 + "\n")

# 4. Minimum Water Use Standard
print("4. MINIMUM WATER USE STANDARD (40%)\n")
print("   Planning Portal: SEPP (Sustainable Buildings) 2022\n")

cur.execute("""
    SELECT id, provision_text, ref_number, document_id
    FROM regulatory_provisions
    WHERE document_id LIKE '%Sustainable_Buildings%'
    AND (provision_text ILIKE '%water%standard%'
         OR provision_text ILIKE '%water%reduction%40%'
         OR provision_text ILIKE '%potable water%')
    LIMIT 10
""")
rows = cur.fetchall()
if rows:
    print(f"   Found {len(rows)} provisions:\n")
    for row in rows:
        print(f"   ID: {row[0]} | Ref: {row[2]}")
        print(f"   Text: {row[1][:200]}...")
        print()
else:
    print("   NOT FOUND IN DATABASE\n")

c.close()