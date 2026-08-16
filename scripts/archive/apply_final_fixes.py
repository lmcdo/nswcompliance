#!/usr/bin/env python3
"""Apply final fixes for clear errors in no-keyword provisions."""
import os
import psycopg2
from dotenv import load_dotenv
import pathlib

env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Final fixes based on review of no-keyword provisions
fixes = [
    # Signage provisions that aren't about signage
    (79765, 'residential'),   # "To significantly increase the supply of adaptable housing" -> residential
    (80576, 'views'),         # "To maintain significant views..." - keep as views? No, text says "views", change to views

    # Views provisions about weeds
    (80012, 'environmental'),  # "Priority Weed Species" -> environmental
    (81372, 'environmental'),  # Same - weeds -> environmental

    # Food premises about public domain
    (80358, 'general'),       # "To manage and encourage the responsible shared use of the public domain" -> general

    # Signage in wrong topic
    (87364, 'general'),       # "WestConnex Motorway" State Significant Infrastructure -> general
    (87409, 'general'),       # Same WestConnex -> general
    (80440, 'heritage'),      # "Structures at Nos.13, 27, 29A... should be retained" -> heritage

    # Access that's about adaptable housing
    (79770, 'residential'),   # "To facilitate provision of sufficient adaptable housing" -> residential

    # Building form that's about public info meeting
    (80568, 'general'),       # "A Public Information meeting..." -> general
]

for pid, topic in fixes:
    cur.execute('UPDATE regulatory_provisions SET v2_topic = %s WHERE id = %s', (topic, pid))
    print(f'Fixed {pid} -> {topic}')

conn.commit()
print(f'\nApplied {len(fixes)} fixes')
conn.close()
