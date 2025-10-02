from db_config import get_connection

# Map UI dropdown values to database values
DEVTYPE_MAP = {
    'dwelling_house': 'dwelling_house',
    'secondary_dwelling': 'dwelling_house',  # Typically same rules
    'shop_top_housing': 'business_premises',
    'multi_dwelling': 'residential_flat_building',
    'residential_flat': 'residential_flat_building',
    'boarding_house': 'boarding_house',
    'child_care': 'information_and_education_facility',
    'commercial': 'business_premises'
}

conn = get_connection()
cur = conn.cursor()

# Insert mapped records for E1
for ui_type, db_type in DEVTYPE_MAP.items():
    # Get the base permission
    cur.execute("""
        SELECT permission_status, source_type
        FROM development_permissions  
        WHERE zone = 'E1' AND development_type = %s
        AND source_type NOT ILIKE '%%exempt%%'
        LIMIT 1
    """, (db_type,))
    
    result = cur.fetchone()
    if result:
        status, source = result
        
        # Check if UI type already exists
        cur.execute("""
            SELECT COUNT(*) FROM development_permissions
            WHERE zone = 'E1' AND development_type = %s
        """, (ui_type,))
        
        if cur.fetchone()[0] == 0:
            # Insert mapped record
            cur.execute("""
                INSERT INTO development_permissions
                (zone, development_type, permission_status, source_type)
                VALUES (%s, %s, %s, %s)
            """, ('E1', ui_type, status, source))
            print(f"✓ Added E1 + {ui_type} = {status}")

conn.commit()
conn.close()
print("\nMapping complete!")
