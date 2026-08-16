#!/usr/bin/env python3
"""Check how topics were originally extracted and current state"""

import psycopg2
import os
from dotenv import load_dotenv
import pathlib

# Load env
script_dir = pathlib.Path(__file__).parent.absolute()
project_root = script_dir.parent
env_file = project_root / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print("=" * 80)
print("TOPIC EXTRACTION AUDIT - ALL THREE COUNCILS")
print("=" * 80)

# 1. Check what columns exist
print("\n1. COLUMNS RELATED TO TOPICS/SECTIONS:")
print("-" * 80)
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name='regulatory_provisions'
    AND (column_name LIKE '%section%' OR column_name LIKE '%topic%' OR column_name LIKE '%header%')
    ORDER BY column_name
""")

for row in cur.fetchall():
    print(f"  {row[0]:30} {row[1]}")

# 2. Check section_header population
print("\n2. SECTION_HEADER POPULATION BY COUNCIL:")
print("-" * 80)

for council in ['Leichhardt', 'Ashfield', 'Marrickville']:
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(section_header) as has_section_header,
            COUNT(v2_topic) as has_v2_topic
        FROM regulatory_provisions
        WHERE document_id ILIKE %s
        AND is_current = TRUE
    """, (f'%{council}%',))

    row = cur.fetchone()
    total, has_header, has_topic = row
    pct_header = (has_header/total*100) if total else 0
    pct_topic = (has_topic/total*100) if total else 0

    print(f"\n{council}:")
    print(f"  Total provisions: {total}")
    print(f"  Has section_header: {has_header} ({pct_header:.1f}%)")
    print(f"  Has v2_topic: {has_topic} ({pct_topic:.1f}%)")

# 3. Sample section headers for each council
print("\n3. SAMPLE SECTION HEADERS (first 10 unique per council):")
print("-" * 80)

for council in ['Leichhardt', 'Ashfield', 'Marrickville']:
    cur.execute("""
        SELECT DISTINCT section_header, COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id ILIKE %s
        AND section_header IS NOT NULL
        AND is_current = TRUE
        GROUP BY section_header
        ORDER BY count DESC
        LIMIT 10
    """, (f'%{council}%',))

    rows = cur.fetchall()
    print(f"\n{council}: ({len(rows)} unique headers)")
    for row in rows:
        print(f"  {row[0][:60]:60} ({row[1]} provisions)")

# 4. Check v2_topic distribution by council
print("\n4. V2_TOPIC DISTRIBUTION BY COUNCIL:")
print("-" * 80)

for council in ['Leichhardt', 'Ashfield', 'Marrickville']:
    cur.execute("""
        SELECT v2_topic, COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id ILIKE %s
        AND is_current = TRUE
        GROUP BY v2_topic
        ORDER BY count DESC
    """, (f'%{council}%',))

    rows = cur.fetchall()
    total = sum(row[1] for row in rows)

    print(f"\n{council} (top 15 topics, total={total}):")
    for i, row in enumerate(rows[:15]):
        topic = row[0] or 'None'
        count = row[1]
        pct = (count/total*100) if total else 0
        print(f"  {topic:25} {count:4} ({pct:5.1f}%)")

# 5. Check relationship between section_header and v2_topic
print("\n5. SECTION_HEADER -> V2_TOPIC MAPPING (Leichhardt Part D):")
print("-" * 80)

cur.execute("""
    SELECT
        section_header,
        v2_topic,
        pdf_page,
        COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
    AND v2_dcp_part = 'Part D'
    AND is_current = TRUE
    GROUP BY section_header, v2_topic, pdf_page
    ORDER BY pdf_page
""")

for row in cur.fetchall():
    header = str(row[0])[:40] if row[0] else 'None'
    topic = row[1] or 'None'
    page = row[2] or 0
    count = row[3]
    print(f"  Page {page:3} | Header: {header:40} | Topic: {topic:20} | Count: {count}")

# 6. Check for multi-topic parts in other councils
print("\n6. PARTS WITH MULTIPLE TOPICS (like Part D issue):")
print("-" * 80)

for council in ['Leichhardt', 'Ashfield', 'Marrickville']:
    cur.execute("""
        SELECT
            v2_dcp_part,
            COUNT(DISTINCT v2_topic) as topic_count,
            COUNT(*) as provision_count,
            STRING_AGG(DISTINCT v2_topic, ', ') as topics
        FROM regulatory_provisions
        WHERE document_id ILIKE %s
        AND is_current = TRUE
        AND v2_dcp_part IS NOT NULL
        GROUP BY v2_dcp_part
        HAVING COUNT(DISTINCT v2_topic) > 1
        ORDER BY topic_count DESC
    """, (f'%{council}%',))

    rows = cur.fetchall()
    if rows:
        print(f"\n{council}:")
        for row in rows:
            part = row[0]
            topic_count = row[1]
            prov_count = row[2]
            topics = row[3][:60]
            print(f"  {part:25} {topic_count} topics, {prov_count} provs: {topics}")

conn.close()

print("\n" + "=" * 80)
print("END OF AUDIT")
print("=" * 80)
