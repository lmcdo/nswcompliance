#!/usr/bin/env python3
"""Audit Leichhardt provisions for URL/part/topic mismatches."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print("=== AUDIT: Leichhardt Provisions ===\n")

# 1. Check for URL/Part mismatches
print("1. URL vs Part mismatches:")
cur.execute('''
    SELECT id, v2_dcp_part, pdf_page_image_url
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
    AND v2_is_actionable = true
    AND pdf_page_image_url IS NOT NULL
    AND (
        (v2_dcp_part = 'Part C Section 1' AND pdf_page_image_url NOT LIKE '%part-c1%')
        OR (v2_dcp_part = 'Part C Section 2' AND pdf_page_image_url NOT LIKE '%part-c2%')
        OR (v2_dcp_part = 'Part D' AND pdf_page_image_url NOT LIKE '%part-d%')
        OR (v2_dcp_part = 'Part E' AND pdf_page_image_url NOT LIKE '%part-e%')
        OR (v2_dcp_part = 'Part F' AND pdf_page_image_url NOT LIKE '%part-f%')
        OR (v2_dcp_part = 'Part G' AND pdf_page_image_url NOT LIKE '%part-g%')
    )
''')
mismatches = cur.fetchall()
print(f"  Found {len(mismatches)} mismatches")
for r in mismatches[:10]:
    print(f"    ID {r[0]}: Part={r[1]}, URL={r[2]}")

# 2. Check topic distribution
print("\n2. Topic distribution:")
cur.execute('''
    SELECT v2_topic, COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
    AND v2_is_actionable = true
    GROUP BY v2_topic
    ORDER BY COUNT(*) DESC
''')
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

# 3. Check for remaining duplicates
print("\n3. Remaining duplicates (same text, first 150 chars):")
cur.execute('''
    SELECT LEFT(provision_text, 150) as text, COUNT(*) as cnt
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
    AND v2_is_actionable = true
    GROUP BY LEFT(provision_text, 150)
    HAVING COUNT(*) > 1
    ORDER BY cnt DESC
    LIMIT 10
''')
dups = cur.fetchall()
print(f"  Found {len(dups)} duplicate texts")
for r in dups[:5]:
    print(f"    '{r[0][:60]}...' appears {r[1]} times")

# 4. Check provisions without URLs
print("\n4. Provisions without PDF URLs:")
cur.execute('''
    SELECT v2_dcp_part, COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
    AND v2_is_actionable = true
    AND pdf_page_image_url IS NULL
    GROUP BY v2_dcp_part
''')
no_urls = cur.fetchall()
total_no_url = sum(r[1] for r in no_urls)
print(f"  Total: {total_no_url}")
for r in no_urls:
    print(f"    {r[0]}: {r[1]}")

# 5. Check Part D offset - all Part D provisions should have correct offset
print("\n5. Part D page check (sample):")
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url, LEFT(provision_text, 60)
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part D'
    AND v2_is_actionable = true
    AND pdf_page_image_url IS NOT NULL
    ORDER BY pdf_page
    LIMIT 5
''')
for r in cur.fetchall():
    print(f"  ID {r[0]}: page {r[1]}, {r[2]}")

cur.close()
conn.close()
