#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

# Check zone data in regulatory_provisions
results = cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE zone IS NOT NULL AND zone != ''").fetchone()
print(f'Zone records: {results[0]}/22092 ({results[0]/22092*100:.1f}%)')

# Check AutoSchemaKG data in regulatory_refs
results2 = cursor.execute("SELECT COUNT(*) FROM regulatory_refs WHERE ref_context LIKE '%autoschema%'").fetchone()
print(f'AutoSchemaKG records: {results2[0]}')

# Check if the integration worked by looking for zone entities
results3 = cursor.execute("SELECT COUNT(*) FROM regulatory_refs WHERE ref_type = 'zone'").fetchone()
print(f'Zone entity records: {results3[0]}')

conn.close()