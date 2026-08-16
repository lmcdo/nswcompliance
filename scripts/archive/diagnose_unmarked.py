#!/usr/bin/env python3
"""
Diagnose WHY provisions don't have markers.
Are they real controls or garbage data?
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print("="*70)
print("DIAGNOSING UNMARKED PROVISIONS")
print("="*70)

for council in ['leichhardt', 'ashfield', 'marrickville']:
    print(f"\n{'='*70}")
    print(f"{council.upper()}")
    print(f"{'='*70}")

    # Get unmarked provisions by part
    cur.execute(f"""
        SELECT v2_dcp_part, COUNT(*)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%{council}%'
        AND v2_is_actionable = true
        AND (v2_marker IS NULL OR v2_marker = '')
        GROUP BY v2_dcp_part
        ORDER BY COUNT(*) DESC
    """)

    print(f"\nUnmarked provisions by part:")
    for part, count in cur.fetchall():
        print(f"  {part or 'NULL':<30} {count:>5}")

    # Sample the largest group
    cur.execute(f"""
        SELECT v2_dcp_part, LEFT(provision_text, 200)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%{council}%'
        AND v2_is_actionable = true
        AND (v2_marker IS NULL OR v2_marker = '')
        LIMIT 10
    """)

    print(f"\nSample unmarked provisions:")
    for part, text in cur.fetchall():
        # Check if it looks like a real control or garbage
        is_toc = '......' in text or 'SECTION' in text[:20]
        is_intro = text.startswith('This ') or text.startswith('The ')
        is_figure = 'Figure' in text[:30] or 'FIGURE' in text[:30]

        status = "TOC" if is_toc else ("INTRO" if is_intro else ("FIGURE" if is_figure else "???"))
        print(f"  [{status:6}] {part or 'NULL':<20} | {text[:60]}...")

conn.close()

print("\n" + "="*70)
print("CONCLUSION")
print("="*70)
print("""
If most unmarked provisions are TOC/INTRO/FIGURE:
  → Mark them as v2_is_actionable = false
  → Only real controls should be actionable

If they're real controls without markers:
  → Need to re-extract from PDF with section context
  → Or manually assign based on page ranges
""")
