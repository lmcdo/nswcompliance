#!/usr/bin/env python3
"""Direct insert of Penrith single dwelling (dwelling_house) setbacks from DCP 2014 s2.1.2."""
import sys, os, psycopg2
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()

ROWS = [
    dict(control_type='front_setback', value_min=5.5, unit='m',
         condition='or average of adjoining property setbacks, whichever is greater',
         source_text='s2.1.2 B.1a: Front setback is the greater of either i) 5.5m, or ii) the average of the setbacks of the adjoining properties.'),
    dict(control_type='front_setback', value_min=3.0, unit='m',
         condition='secondary (corner) street frontage; garage entrance setback 5.5m',
         source_text='s2.1.2 B.1b: Secondary street frontage is 3m to external walls and 5.5m to garage entrances.'),
    dict(control_type='side_setback', value_min=0.9, unit='m',
         condition=None,
         source_text='s2.1.2 B.1d: Side setbacks to external walls should be a minimum of 900mm.'),
    dict(control_type='rear_setback', value_min=4.0, unit='m',
         condition='single storey building or single storey component',
         source_text='s2.1.2 B.1e-i: The minimum rear setback for a single storey building (or any single storey component of a building) is 4m.'),
    dict(control_type='rear_setback', value_min=6.0, unit='m',
         condition='two storey building or two storey component',
         source_text='s2.1.2 B.1e-ii: The minimum rear setback for a two storey building (or any two storey component of a building) is 6m.'),
]

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()
inserted = 0
for r in ROWS:
    cur.execute(
        "SELECT id FROM dcp_setback_controls WHERE lga='penrith' AND dev_type='dwelling_house' "
        "AND control_type=%s AND COALESCE(condition,'')=COALESCE(%s,'') AND COALESCE(value_min::text,'')=COALESCE(%s::text,'')",
        (r['control_type'], r.get('condition'), r['value_min']),
    )
    if cur.fetchone():
        print(f"  DUP: {r['control_type']} {r['value_min']}m")
        continue
    cur.execute(
        "INSERT INTO dcp_setback_controls "
        "(lga,dev_type,control_type,value_min,unit,condition,applicability,source_text,section_ref,dcp_version,is_current,extraction_method) "
        "VALUES ('penrith','dwelling_house',%s,%s,%s,%s,'universal_residential',%s,'penrith-part-d2-residential.pdf#dwelling_house','v1.0-baseline',TRUE,'manual')",
        (r['control_type'], r['value_min'], r['unit'], r.get('condition'), r['source_text']),
    )
    inserted += 1
    print(f"  INSERTED: {r['control_type']} {r['value_min']}m {r.get('condition') or ''}")
conn.commit()
print(f'Done. {inserted} rows inserted.')
conn.close()
