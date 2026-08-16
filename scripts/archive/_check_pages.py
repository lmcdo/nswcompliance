#!/usr/bin/env python3
"""Check PDF page number state across regulatory_provisions and dcp_chapter_registry."""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'frontend-nextjs', '.env.local'))
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# ─── 0. Discover council-related columns ───
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
      AND (column_name ILIKE '%%council%%' OR column_name ILIKE '%%source%%')
    ORDER BY column_name
""")
council_cols = [r[0] for r in cur.fetchall()]
print("Council/source columns:", council_cols)

# Pick best council column(s) for COALESCE
council_col = 'source_council' if 'source_council' in council_cols else None
former_col = next((c for c in council_cols if 'former' in c), None)
coalesce_parts = [c for c in [council_col, former_col] if c]
if not coalesce_parts:
    coalesce_parts = ['document_id']
CE = f"COALESCE({', '.join(coalesce_parts)}, 'UNKNOWN')"
print(f"Using council expression: {CE}\n")

# ─── 1. pdf_page set vs NULL by council ───
print("=" * 70)
print("1. regulatory_provisions -- pdf_page set vs NULL by council")
print("=" * 70)

cur.execute(f'''
    SELECT
        {CE} AS council,
        COUNT(*) AS total,
        COUNT(pdf_page) AS has_pdf_page,
        COUNT(*) - COUNT(pdf_page) AS null_pdf_page,
        ROUND(100.0 * COUNT(pdf_page) / NULLIF(COUNT(*), 0), 1) AS pct_set
    FROM regulatory_provisions
    GROUP BY {CE}
    ORDER BY total DESC
''')
rows = cur.fetchall()
print(f"{'Council':<30} {'Total':>8} {'Has Page':>10} {'NULL':>10} {'% Set':>8}")
print("-" * 70)
for r in rows:
    print(f"{r[0]:<30} {r[1]:>8} {r[2]:>10} {r[3]:>10} {r[4]:>7}%")

# ─── 2. Sample pdf_page values ───
print("\n" + "=" * 70)
print("2. Sample pdf_page values (non-NULL, per council, 5 each)")
print("=" * 70)

cur.execute(f'''
    SELECT DISTINCT {CE} AS council
    FROM regulatory_provisions
    WHERE pdf_page IS NOT NULL
    ORDER BY council
''')
councils = [r[0] for r in cur.fetchall()]

for council in councils:
    cur.execute(f'''
        SELECT pdf_page, LEFT(provision_text, 80)
        FROM regulatory_provisions
        WHERE {CE} = %s
          AND pdf_page IS NOT NULL
        ORDER BY RANDOM()
        LIMIT 5
    ''', (council,))
    samples = cur.fetchall()
    print(f"\n  [{council}]")
    for s in samples:
        print(f"    page={s[0]:<6}  text: {s[1]}...")

# ─── 2b. Check for suspicious values ───
print("\n" + "=" * 70)
print("2b. Suspicious pdf_page values (0, negative, or >500)")
print("=" * 70)

cur.execute(f'''
    SELECT
        {CE} AS council,
        COUNT(*) FILTER (WHERE pdf_page = 0) AS zero_pages,
        COUNT(*) FILTER (WHERE pdf_page < 0) AS negative_pages,
        COUNT(*) FILTER (WHERE pdf_page > 500) AS over_500,
        MIN(pdf_page) AS min_page,
        MAX(pdf_page) AS max_page
    FROM regulatory_provisions
    WHERE pdf_page IS NOT NULL
    GROUP BY {CE}
    ORDER BY council
''')
rows = cur.fetchall()
print(f"{'Council':<30} {'Zero':>6} {'Neg':>6} {'>500':>6} {'Min':>6} {'Max':>6}")
print("-" * 70)
for r in rows:
    print(f"{r[0]:<30} {r[1]:>6} {r[2]:>6} {r[3]:>6} {r[4]:>6} {r[5]:>6}")

# ─── 3. Check for pdf_page_start / pdf_page_end columns ───
print("\n" + "=" * 70)
print("3. Columns containing 'page' in regulatory_provisions")
print("=" * 70)

cur.execute('''
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
      AND column_name ILIKE '%%page%%'
    ORDER BY ordinal_position
''')
rows = cur.fetchall()
for r in rows:
    print(f"  {r[0]:<35} {r[1]:<20} nullable={r[2]}")

# ─── 4. dcp_chapter_registry page_start / page_end ───
print("\n" + "=" * 70)
print("4. dcp_chapter_registry -- page_start / page_end coverage")
print("=" * 70)

cur.execute('''
    SELECT
        council,
        COUNT(*) AS total_chapters,
        COUNT(page_start) AS has_page_start,
        COUNT(page_end) AS has_page_end,
        COUNT(*) - COUNT(page_start) AS missing_page_start
    FROM dcp_chapter_registry
    GROUP BY council
    ORDER BY council
''')
rows = cur.fetchall()
print(f"{'Council':<30} {'Total':>8} {'Has Start':>10} {'Has End':>10} {'Missing':>10}")
print("-" * 70)
for r in rows:
    print(f"{r[0]:<30} {r[1]:>8} {r[2]:>10} {r[3]:>10} {r[4]:>10}")

# Sample page_start/page_end values
cur.execute('''
    SELECT council, chapter_key, page_start, page_end
    FROM dcp_chapter_registry
    WHERE page_start IS NOT NULL
    ORDER BY council, page_start
    LIMIT 15
''')
rows = cur.fetchall()
if rows:
    print(f"\n  Sample page ranges:")
    print(f"  {'Council':<20} {'Chapter Key':<40} {'Start':>6} {'End':>6}")
    print("  " + "-" * 75)
    for r in rows:
        print(f"  {r[0]:<20} {r[1]:<40} {r[2]:>6} {r[3]:>6}")
else:
    print("\n  No chapters have page_start/page_end set.")

cur.close()
conn.close()
print("\nDone.")
