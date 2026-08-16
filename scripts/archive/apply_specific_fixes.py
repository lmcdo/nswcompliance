#!/usr/bin/env python3
"""Apply specific manual fixes based on review."""
import os
import psycopg2
from dotenv import load_dotenv
import pathlib

env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Specific manual fixes based on review
fixes = [
    (81117, 'signage'),      # building_form -> signage (3 signage keywords)
    (81186, 'energy'),       # roofing -> energy (about passive solar)
    (81118, 'signage'),      # roofing -> signage (about signs on rooflines)
    (81176, 'energy'),       # building_design -> energy (about BCA energy)
    (79383, 'general'),      # building_form -> general (EPA Act reference)
    (81035, 'general'),      # building_form -> general (performance criteria)
    (80943, 'building_design'),  # general -> building_design (about electrical)
    (80365, 'landscaping'),  # food_premises -> landscaping (about gardens)
]

for pid, topic in fixes:
    cur.execute('UPDATE regulatory_provisions SET v2_topic = %s WHERE id = %s', (topic, pid))
    print(f'Fixed {pid} -> {topic}')

conn.commit()
print(f'\nApplied {len(fixes)} fixes')
conn.close()
