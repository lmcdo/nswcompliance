#!/usr/bin/env python3
"""
Populate dcp_precinct_localities from the authoritative source (regulatory_provisions.section_header).
Adds canonical suburb→precinct mappings for the Canterbury Road corridor.
"""

import os
import sys
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL') or os.environ.get('SUPABASE_DB_URL')

if not DATABASE_URL:
    print("ERROR: No DATABASE_URL / POSTGRES_URL / SUPABASE_DB_URL env var set", file=sys.stderr)
    sys.exit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# ── 1. Create table (idempotent) ──────────────────────────────────────────────
cur.execute("""
CREATE TABLE IF NOT EXISTS dcp_precinct_localities (
    id          SERIAL PRIMARY KEY,
    locality    TEXT NOT NULL,
    precinct_id TEXT NOT NULL,
    council     TEXT NOT NULL,
    notes       TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (locality, precinct_id, council)
);
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_dpl_locality_council
    ON dcp_precinct_localities (UPPER(locality), council);
""")

conn.commit()
print("Table and index ensured.")

# ── 2. Extract canonical locality→precinct_id pairs from regulatory_provisions ─
cur.execute("""
SELECT DISTINCT
    UPPER(SPLIT_PART(section_header, ' — ', 1)) AS locality,
    SPLIT_PART(section_header, ' — ', 1)        AS precinct_id,
    source_council                               AS council
FROM regulatory_provisions
WHERE v2_structural_category = 'precinct'
  AND v2_dcp_layer = 'precinct'
  AND section_header IS NOT NULL
  AND section_header LIKE '% — %'
ORDER BY 3, 1;
""")

rows = cur.fetchall()
print(f"\nRows derived from regulatory_provisions ({len(rows)}):")
for r in rows:
    print(f"  locality={r[0]!r}  precinct_id={r[1]!r}  council={r[2]!r}")

# ── 3. Upsert from regulatory_provisions ─────────────────────────────────────
inserted = 0
for (locality, precinct_id, council) in rows:
    cur.execute("""
        INSERT INTO dcp_precinct_localities (locality, precinct_id, council, notes)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (locality, precinct_id, council) DO NOTHING
    """, (locality, precinct_id, council, 'auto-derived from section_header'))
    inserted += cur.rowcount

conn.commit()
print(f"\nUpserted {inserted} rows from regulatory_provisions.")

# ── 4. Add known suburb→precinct mappings for Canterbury Road corridor ─────────
# These suburbs fall within the Canterbury Road precinct (border of Ashfield/Canterbury LGAs)
# but don't appear verbatim in section_header since Canterbury Road sections aren't suburb-named.
# These are the only manual entries — everything else comes from the DB itself.
CANTON_ROAD_SUBURBS = [
    # (upper-locality, precinct_id, council, notes)
    ('CAMPSIE',        'Canterbury Road', 'ashfield', 'suburb spans Canterbury Road precinct corridor'),
    ('CANTERBURY',     'Canterbury Road', 'ashfield', 'suburb spans Canterbury Road precinct corridor'),
]

extra_inserted = 0
for (locality, precinct_id, council, notes) in CANTON_ROAD_SUBURBS:
    cur.execute("""
        INSERT INTO dcp_precinct_localities (locality, precinct_id, council, notes)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (locality, precinct_id, council) DO NOTHING
    """, (locality, precinct_id, council, notes))
    extra_inserted += cur.rowcount

conn.commit()
print(f"Upserted {extra_inserted} Canterbury Road corridor entries.")

# ── 5. Verify ──────────────────────────────────────────────────────────────────
cur.execute("SELECT locality, precinct_id, council, notes FROM dcp_precinct_localities ORDER BY council, locality")
final = cur.fetchall()
print(f"\nFinal table ({len(final)} rows):")
for r in final:
    print(f"  {r[2]:<12} | {r[0]:<26} | {r[1]}")

cur.close()
conn.close()
print("\nDone.")
