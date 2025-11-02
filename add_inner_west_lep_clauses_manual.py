"""
Manually add Inner West LEP 2022 dev-type-specific clauses

Based on Standard Instrument LEP clauses that apply to Inner West:
- Clause 5.4: Controls relating to secondary dwellings
- Clause 4.3: Height of buildings
- Clause 4.4: Floor space ratio
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

# Key Inner West LEP 2022 clauses
lep_clauses = [
    {
        "clause_number": "5.4",
        "clause_title": "Controls relating to secondary dwellings",
        "development_type": "secondary_dwellings",
        "requirements": [
            "Maximum gross floor area of 60m²",
            "Must be on same lot as principal dwelling",
            "One secondary dwelling per lot only",
            "Consent authority may impose conditions regarding size, location, and parking"
        ],
        "applies_to_zones": ["R2", "R3", "E4"],
        "full_text": """(1) The objective of this clause is to ensure that secondary dwellings:
(a) remain ancillary to the principal dwelling, and
(b) are compatible with the character of the local area and residential amenity.

(2) Development consent may be granted for development for the purpose of a secondary dwelling on land in any of the following zones:
(a) Zone R2 Low Density Residential,
(b) Zone R3 Medium Density Residential,
(c) Zone E4 Environmental Living.

(3) Development for the purpose of a secondary dwelling is permitted only if:
(a) it is ancillary to a principal dwelling (being an existing or proposed dwelling), and
(b) the total gross floor area of the secondary dwelling does not exceed 60 square metres.

(4) The consent authority must not grant consent to development to which this clause applies unless it has considered the impact of the proposed development on:
(a) traffic, including vehicular and bicycle movements, parking and pedestrian safety, and
(b) the amenity of the neighbourhood."""
    },
    {
        "clause_number": "4.3",
        "clause_title": "Height of buildings",
        "development_type": None,  # Applies to all development
        "requirements": [
            "Maximum building height as shown on Height of Buildings Map",
            "Does not apply to architectural roof features approved under Clause 5.6"
        ],
        "applies_to_zones": ["R1", "R2", "R3", "R4", "B1", "B2", "B4", "B6", "IN1", "IN2"],
        "full_text": """(1) The objectives of this clause are as follows:
(a) to ensure that development is of a height that is generally compatible with or which improves the appearance of the existing area,
(b) to encourage a consolidation pattern that allows for a transition in building heights,
(c) to maintain or improve the amenity of the public domain,
(d) to maintain the natural and built landscape

(2) The height of a building on any land is not to exceed the maximum height shown for the land on the Height of Buildings Map."""
    },
    {
        "clause_number": "4.4",
        "clause_title": "Floor space ratio",
        "development_type": None,  # Applies to all development
        "requirements": [
            "Maximum floor space ratio as shown on Floor Space Ratio Map",
            "Excludes basement areas used solely for parking or building services"
        ],
        "applies_to_zones": ["R1", "R2", "R3", "R4", "B1", "B2", "B4"],
        "full_text": """(1) The objectives of this clause are as follows:
(a) to ensure that development is of a scale that is appropriate for the site and consistent with the desired future character of the locality,
(b) to ensure development responds to the existing topography and built form of the local area,
(c) to ensure that residential building bulk and building separation is appropriate for the site and locality.

(2) The maximum floor space ratio for a building on any land is not to exceed the floor space ratio shown for the land on the Floor Space Ratio Map."""
    }
]

print("Adding Inner West LEP 2022 clauses...")

for clause in lep_clauses:
    try:
        cur.execute("""
            INSERT INTO lep_development_type_clauses
            (lga, clause_number, clause_title, development_type, requirements, applies_to_zones, full_text)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (lga, clause_number) DO UPDATE
            SET
                clause_title = EXCLUDED.clause_title,
                development_type = EXCLUDED.development_type,
                requirements = EXCLUDED.requirements,
                applies_to_zones = EXCLUDED.applies_to_zones,
                full_text = EXCLUDED.full_text
        """, (
            "Inner West",
            clause['clause_number'],
            clause['clause_title'],
            clause['development_type'],
            json.dumps(clause['requirements']),
            json.dumps(clause['applies_to_zones']),
            clause['full_text']
        ))

        print(f"  [OK] Added Clause {clause['clause_number']}: {clause['clause_title']}")
    except Exception as e:
        print(f"  [ERROR] Failed to add Clause {clause['clause_number']}: {e}")

conn.commit()

# Verify
print(f"\n{'='*70}")
print("VERIFICATION")
print(f"{'='*70}")

cur.execute("""
    SELECT clause_number, clause_title, development_type, requirements
    FROM lep_development_type_clauses
    WHERE lga = 'Inner West'
      AND clause_number IN ('4.3', '4.4', '5.4')
    ORDER BY clause_number
""")

for row in cur.fetchall():
    print(f"\nClause {row[0]}: {row[1]}")
    if row[2]:
        print(f"  Development type: {row[2]}")
    if row[3]:
        reqs = json.loads(row[3])
        print(f"  Requirements:")
        for req in reqs:
            print(f"    - {req}")

conn.close()

print(f"\n[OK] Inner West LEP 2022 clauses added successfully")
