#!/usr/bin/env python3
"""
Check if unmarked provisions can inherit topic from marked provisions on same page.
"""
import os
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print("="*80)
print("PAGE-BASED TOPIC INHERITANCE")
print("="*80)

# Get all Leichhardt Part C Section 1 provisions with their pages
cur.execute("""
    SELECT id, pdf_page, v2_marker, v2_topic
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
    AND v2_is_actionable = true
    AND v2_dcp_part = 'Part C Section 1'
    ORDER BY pdf_page
""")

provisions = cur.fetchall()

# Build page → marker mapping (from provisions that HAVE markers)
page_markers = defaultdict(set)
page_topics = defaultdict(set)

for prov_id, page, marker, topic in provisions:
    if marker and page:
        page_markers[page].add(marker)
    if topic and page:
        page_topics[page].add(topic)

# Now check unmarked provisions
unmarked_with_page = 0
unmarked_can_inherit = 0
unmarked_no_page = 0
unmarked_page_no_marker = 0

cur.execute("""
    SELECT id, pdf_page, LEFT(provision_text, 80)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
    AND v2_is_actionable = true
    AND v2_dcp_part = 'Part C Section 1'
    AND (v2_marker IS NULL OR v2_marker = '')
""")

unmarked = cur.fetchall()
pages_with_no_markers = set()

for prov_id, page, text in unmarked:
    if not page:
        unmarked_no_page += 1
    elif page in page_markers:
        unmarked_can_inherit += 1
    else:
        unmarked_page_no_marker += 1
        pages_with_no_markers.add(page)

print(f"\nUnmarked provisions: {len(unmarked)}")
print(f"  Has page + can inherit from marker on same page: {unmarked_can_inherit}")
print(f"  Has page but NO marker on that page: {unmarked_page_no_marker}")
print(f"  No page number: {unmarked_no_page}")

print(f"\nPages with unmarked provisions but no markers: {len(pages_with_no_markers)}")
if pages_with_no_markers:
    print(f"  Pages: {sorted(pages_with_no_markers)[:20]}...")

# Check what % of pages have markers
all_pages = set()
for prov_id, page, marker, topic in provisions:
    if page:
        all_pages.add(page)

pages_with_markers = set(page_markers.keys())
print(f"\nTotal pages in Part C Section 1: {len(all_pages)}")
print(f"Pages with at least one marker: {len(pages_with_markers)}")
print(f"Pages without any markers: {len(all_pages - pages_with_markers)}")

# Show example of inheritance
print(f"\n\nEXAMPLE - Page 15:")
cur.execute("""
    SELECT id, v2_marker, v2_topic, LEFT(provision_text, 100)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
    AND v2_is_actionable = true
    AND v2_dcp_part = 'Part C Section 1'
    AND pdf_page = 15
    ORDER BY v2_marker DESC NULLS LAST
""")

for prov_id, marker, topic, text in cur.fetchall():
    marker_str = marker or 'NO MARKER'
    print(f"  [{marker_str:10}] {topic or 'NO TOPIC':15} | {text[:50]}...")

conn.close()
