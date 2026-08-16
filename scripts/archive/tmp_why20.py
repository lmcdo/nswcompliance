import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# How many distinct LGAs in the controls table?
cur.execute("SELECT DISTINCT lga FROM dcp_setback_controls WHERE is_current = true ORDER BY lga")
lgas = [r[0] for r in cur.fetchall()]
print(f"LGAs in dcp_setback_controls: {len(lgas)}")
for l in lgas:
    print(f"  {l}")

# How many LGAs do we have provisions for?
# Try common column names for LGA
for col in ['v2_lga', 'lga', 'council', 'lga_name']:
    cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = 'regulatory_provisions' AND column_name = '{col}'")
    if cur.fetchone():
        print(f"\nFound LGA column: {col}")
        cur.execute(f"SELECT DISTINCT {col} FROM regulatory_provisions WHERE {col} IS NOT NULL ORDER BY {col}")
        prov_lgas = [r[0] for r in cur.fetchall()]
        print(f"LGAs in regulatory_provisions: {len(prov_lgas)}")
        controls_set = set(lgas)
        missing = [l for l in prov_lgas if l.lower().replace(' ', '_').replace('-', '_') not in controls_set]
        print(f"\nProvision LGAs with NO controls: {len(missing)}")
        for l in missing:
            print(f"  {l}")
        break

conn.close()
