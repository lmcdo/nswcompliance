#!/usr/bin/env python3
"""Direct insert of Penrith secondary dwelling setbacks from DCP 2014 s2.3.3."""
import sys, os, psycopg2
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()

ROWS = [
    dict(control_type='rear_setback', value_min=3.0, unit='m',
         condition='detached secondary dwelling',
         source_text='s2.3.3 B.3d: The minimum rear setback for a detached secondary dwelling is 3m.'),
    dict(control_type='rear_setback', value_min=0.0, unit='m',
         condition='secondary dwelling above garage facing rear laneway',
         source_text='s2.3.3 B.3e: Where located above a garage facing a rear laneway, the building may be built to the rear boundary.'),
    dict(control_type='front_setback', value_min=3.0, unit='m',
         condition='secondary street frontage (corner sites)',
         source_text='s2.3.3 B.3b: The minimum setback to the secondary street frontage is 3m.'),
    dict(control_type='landscaping_min', value_min=50.0, unit='%',
         condition='R2 Low Density Residential zone',
         source_text='s2.3.2 Table D2.3.1: R2 Low Density Residential minimum landscaped area 50% of site.'),
]

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()
inserted = 0
for r in ROWS:
    cur.execute(
        "SELECT id FROM dcp_setback_controls WHERE lga='penrith' AND dev_type='secondary_dwelling' "
        "AND control_type=%s AND COALESCE(condition,'')=COALESCE(%s,'') AND COALESCE(value_min::text,'')=COALESCE(%s::text,'')",
        (r['control_type'], r.get('condition'), r['value_min']),
    )
    if cur.fetchone():
        print(f"  DUP: {r['control_type']} {r['value_min']}")
        continue
    cur.execute(
        "INSERT INTO dcp_setback_controls "
        "(lga,dev_type,control_type,value_min,unit,condition,applicability,source_text,section_ref,dcp_version,is_current,extraction_method) "
        "VALUES ('penrith','secondary_dwelling',%s,%s,%s,%s,'secondary_dwelling_specific',%s,'penrith-part-d2-residential.pdf#secondary_dwelling','v1.0-baseline',TRUE,'manual')",
        (r['control_type'], r['value_min'], r['unit'], r.get('condition'), r['source_text']),
    )
    inserted += 1
    print(f"  INSERTED: {r['control_type']} {r['value_min']} — {r.get('condition') or ''}")
conn.commit()
print(f'Done. {inserted} rows inserted.')
conn.close()
