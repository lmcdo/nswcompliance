#!/usr/bin/env python3
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

# Search for development type terminology in LEP provisions
search_terms = [
    ('secondary dwelling', 'secondary_dwelling'),
    ('dual occupancy', 'dual_occupancy'),
    ('shop top housing', 'shop_top_housing'),
    ('multi dwelling', 'multi_dwelling'),
    ('residential flat building', 'residential_flat')
]

print("=== LEP Development Type Terminology ===\n")

for proper_term, ui_value in search_terms:
    cur.execute("""
        SELECT COUNT(*) 
        FROM regulatory_provisions
        WHERE document_id ILIKE '%inner%west%lep%'
        AND provision_text ILIKE %s
    """, (f'%{proper_term}%',))
    
    count = cur.fetchone()[0]
    
    if count > 0:
        print(f"✓ '{proper_term}' found {count} times → UI: {ui_value}")
        
        # Get a sample
        cur.execute("""
            SELECT ref_number, provision_text
            FROM regulatory_provisions
            WHERE document_id ILIKE '%inner%west%lep%'
            AND provision_text ILIKE %s
            LIMIT 1
        """, (f'%{proper_term}%',))
        
        sample = cur.fetchone()
        if sample:
            print(f"   Sample (Ref {sample[0]}): {sample[1][:100]}...\n")
    else:
        print(f"✗ '{proper_term}' NOT found → UI: {ui_value}\n")

# Check if terminology uses hyphens or spaces
print("\n=== Checking Format Variations ===\n")
cur.execute("""
    SELECT provision_text
    FROM regulatory_provisions
    WHERE document_id ILIKE '%inner%west%lep%'
    AND (
        provision_text ILIKE '%shop-top%'
        OR provision_text ILIKE '%shop top%'
    )
    LIMIT 1
""")

result = cur.fetchone()
if result:
    text = result[0]
    if 'shop-top' in text.lower():
        print("Format: Uses HYPHENS (shop-top housing)")
    elif 'shop top' in text.lower():
        print("Format: Uses SPACES (shop top housing)")

conn.close()
