#!/usr/bin/env python3
"""Check current database status after classifier migration."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM regulatory_provisions WHERE v2_is_actionable = true')
actionable = cur.fetchone()[0]

cur.execute('SELECT COUNT(*) FROM regulatory_provisions WHERE v2_is_actionable = false')
excluded = cur.fetchone()[0]

cur.execute("""SELECT COUNT(*) FROM regulatory_provisions WHERE v2_is_actionable = false AND provision_text ~* '\\ymust\\y'""")
must_excluded = cur.fetchone()[0]

cur.execute("""SELECT COUNT(*) FROM regulatory_provisions WHERE v2_is_actionable = false AND provision_text ~* '\\yshall\\y'""")
shall_excluded = cur.fetchone()[0]

print('DATABASE STATUS')
print('=' * 40)
print(f'Actionable: {actionable}')
print(f'Excluded: {excluded}')
print(f'Total: {actionable + excluded}')
print()
print(f'"must" excluded: {must_excluded}')
print(f'"shall" excluded: {shall_excluded}')
print()
if must_excluded == 0 and shall_excluded == 0:
    print('STATUS: MIGRATION COMPLETE')
    print('All mandatory language provisions are included.')
else:
    print('STATUS: NEEDS MIGRATION')

conn.close()
