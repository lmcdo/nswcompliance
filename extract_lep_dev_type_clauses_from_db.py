"""
Extract dev-type-specific LEP clauses from regulatory_provisions table

Creates lep_development_type_clauses table and populates it with:
- Clause 5.4: Secondary dwellings
- Clause 5.5: Secondary dwellings (rural)
- Clause 5.10: Heritage conservation
- Other relevant Part 5 clauses
"""

import psycopg2
import json

conn = psycopg2.connect(
    host='localhost',
    database='nsw_planning',
    user='postgres',
    password='postgres'
)

cur = conn.cursor()

# Create table
print("Creating lep_development_type_clauses table...")
cur.execute("""
    CREATE TABLE IF NOT EXISTS lep_development_type_clauses (
        id SERIAL PRIMARY KEY,
        lga VARCHAR(255) NOT NULL,
        clause_number VARCHAR(50) NOT NULL,
        clause_title TEXT NOT NULL,
        development_type VARCHAR(255),
        requirements JSONB,
        applies_to_zones JSONB,
        full_text TEXT,
        source_provision_id INTEGER,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(lga, clause_number)
    )
""")

conn.commit()
print("[OK] Table created")

# Get all Clause 5.x provisions
cur.execute("""
    SELECT id, ref_number, section_header, provision_text, zone, development_type
    FROM regulatory_provisions
    WHERE ref_number LIKE '5.%'
    ORDER BY ref_number
""")

provisions = cur.fetchall()
print(f"\nFound {len(provisions)} Clause 5.x provisions")

# Process each provision and extract clause info
inserted_count = 0

for prov_id, ref_num, section_header, provision_text, zone, dev_type in provisions:
    # Extract clause title from section header or provision text
    clause_title = section_header if section_header else f"Clause {ref_num}"

    # Determine development type from clause number or text
    dev_type_inferred = None
    if '5.4' in ref_num or 'secondary dwelling' in provision_text.lower():
        dev_type_inferred = 'secondary_dwellings'
    elif '5.5' in ref_num or 'dual occupanc' in provision_text.lower():
        dev_type_inferred = 'dual_occupancies'
    elif 'heritage' in provision_text.lower():
        dev_type_inferred = 'heritage'
    elif 'boarding house' in provision_text.lower():
        dev_type_inferred = 'boarding_houses'

    # Extract requirements from text (simplified - can be enhanced)
    requirements = []
    if 'maximum' in provision_text.lower():
        # Extract maximum constraints
        if '60' in provision_text and 'm' in provision_text:
            requirements.append("Maximum floor area: 60m²")
    if 'must' in provision_text.lower():
        # Extract mandatory requirements
        requirements.append("Subject to development consent")

    # Determine applicable zones
    applies_to_zones = []
    if zone:
        applies_to_zones.append(zone)
    if 'R2' in provision_text or 'Low Density' in provision_text:
        if 'R2' not in applies_to_zones:
            applies_to_zones.append('R2')
    if 'R3' in provision_text or 'Medium Density' in provision_text:
        if 'R3' not in applies_to_zones:
            applies_to_zones.append('R3')

    try:
        cur.execute("""
            INSERT INTO lep_development_type_clauses
            (lga, clause_number, clause_title, development_type, requirements, applies_to_zones, full_text, source_provision_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (lga, clause_number) DO UPDATE
            SET
                clause_title = EXCLUDED.clause_title,
                development_type = EXCLUDED.development_type,
                requirements = EXCLUDED.requirements,
                applies_to_zones = EXCLUDED.applies_to_zones,
                full_text = EXCLUDED.full_text,
                source_provision_id = EXCLUDED.source_provision_id
        """, (
            "Inner West",
            ref_num,
            clause_title,
            dev_type_inferred or dev_type,
            json.dumps(requirements) if requirements else None,
            json.dumps(applies_to_zones) if applies_to_zones else None,
            provision_text[:5000],  # Limit text length
            prov_id
        ))
        inserted_count += 1
    except Exception as e:
        print(f"Error inserting clause {ref_num}: {e}")

conn.commit()

# Verify
cur.execute("SELECT COUNT(*) FROM lep_development_type_clauses")
total_count = cur.fetchone()[0]

print(f"\n{'='*60}")
print(f"EXTRACTION COMPLETE")
print(f"{'='*60}")
print(f"Total clauses extracted: {total_count}")

# Show sample data
cur.execute("""
    SELECT clause_number, clause_title, development_type
    FROM lep_development_type_clauses
    WHERE lga = 'Inner West'
    ORDER BY clause_number
    LIMIT 10
""")

print(f"\nSample dev-type-specific clauses:")
for row in cur.fetchall():
    print(f"  Clause {row[0]}: {row[1]}")
    if row[2]:
        print(f"    Dev type: {row[2]}")

# Show secondary dwelling clause
cur.execute("""
    SELECT clause_number, clause_title, requirements, full_text
    FROM lep_development_type_clauses
    WHERE development_type = 'secondary_dwellings'
    LIMIT 1
""")

row = cur.fetchone()
if row:
    print(f"\nSecondary Dwellings Clause:")
    print(f"  Clause {row[0]}: {row[1]}")
    if row[2]:
        reqs = json.loads(row[2])
        print(f"  Requirements: {reqs}")
    print(f"  Full text: {row[3][:200]}...")

conn.close()

print(f"\n[OK] LEP dev-type-specific clauses extracted successfully")
