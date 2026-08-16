import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
import os, psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Check Part D pages 1-5 — are there provisions there?
print("=== Part D: provision distribution by page ===")
cur.execute("""
    SELECT pdf_page, count(*) as n
    FROM regulatory_provisions
    WHERE document_id = 'Leichhardt DCP 2013 - 9 - Part D Energy - with IWLEP 2022 amendments'
        AND is_current = TRUE
    GROUP BY pdf_page ORDER BY pdf_page
""")
for r in cur.fetchall():
    print(f"  page {r[0]}: {r[1]} provisions")

print("\n=== Part D TOC entries ===")
cur.execute("""
    SELECT section_number, section_title, page_start, page_end
    FROM dcp_table_of_contents
    WHERE document_id = 'Leichhardt_DCP_2013__part_d_energy'
    ORDER BY page_start
""")
for r in cur.fetchall():
    print(f"  {r[0]} | {r[1]} | pages {r[2]}-{r[3]}")

print("\n=== Part F: provision distribution by page ===")
cur.execute("""
    SELECT pdf_page, count(*) as n
    FROM regulatory_provisions
    WHERE document_id = 'Leichhardt DCP 2013 - 11 - Part F Food - with IWLEP 2022 amendments'
        AND is_current = TRUE
    GROUP BY pdf_page ORDER BY pdf_page
""")
for r in cur.fetchall():
    print(f"  page {r[0]}: {r[1]} provisions")

print("\n=== Part F TOC entries ===")
cur.execute("""
    SELECT section_number, section_title, page_start, page_end
    FROM dcp_table_of_contents
    WHERE document_id = 'Leichhardt_DCP_2013__part_f_food'
    ORDER BY page_start
""")
for r in cur.fetchall():
    print(f"  {r[0]} | {r[1]} | pages {r[2]}-{r[3]}")

# Simulate AFTER migration (with NULL page_ends fixed using max(pdf_page))
print("\n=== Post-migration simulation (NULL page_end fixed to max(pdf_page)) ===")
old_to_new = [
    ('Leichhardt DCP 2013 - 3 - Part A  Introduction - with IWLEP 2022 amendments',
     'Leichhardt_DCP_2013__part_a_introduction', 9),
    ('Leichhardt DCP 2013 - 5 -  Part C Place Section 1 - with IWLEP 2022 amendments March 23',
     'Leichhardt_DCP_2013__part_c_s1_general', 109),
    ('Leichhardt DCP 2013 - 9 - Part D Energy - with IWLEP 2022 amendments',
     'Leichhardt_DCP_2013__part_d_energy', 15),
    ('Leichhardt DCP 2013 - 10 - Part E Water - with IWLEP 2022 amendments',
     'Leichhardt_DCP_2013__part_e_water', 20),
    ('Leichhardt DCP 2013 - 11 - Part F Food - with IWLEP 2022 amendments',
     'Leichhardt_DCP_2013__part_f_food', 6),
    ('Leichhardt DCP 2013 - 12 - Part G Section 1-12 - Amdt 19 - Nov 2023',
     'Leichhardt_DCP_2013__part_g_s1_site_specific', 149),
]
for old_id, new_id, max_page in old_to_new:
    # Simulate with COALESCE(page_end, max_page)
    cur.execute("""
        SELECT
            count(*) as total_provs,
            count(t.section_number) as would_match
        FROM regulatory_provisions p
        LEFT JOIN dcp_table_of_contents t
            ON t.document_id = %s
            AND p.pdf_page BETWEEN t.page_start AND COALESCE(t.page_end, %s)
        WHERE p.document_id = %s
            AND p.is_current = TRUE
    """, (new_id, max_page, old_id))
    r = cur.fetchone()
    if r[0]:
        pct = 100 * r[1] / r[0]
        label = old_id.split(' - ')[2].strip()[:25]
        print(f"  {label:<27} {r[1]}/{r[0]} would match ({pct:.0f}%)")

conn.close()
