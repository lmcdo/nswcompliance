#!/usr/bin/env python3
"""Replace single CB registry entry with two chapter-specific entries (Ch 5.1 + 5.2)."""
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()

CB_PAGE = 'https://www.cbcity.nsw.gov.au/planning-and-building/planning-city/planning-controls-and-policies/canterbury-bankstown-development-control-plan'

# Remove the generic entry
cur.execute("DELETE FROM dcp_chapter_registry WHERE council='canterbury_bankstown' AND chapter_key='cb-dcp-2023-residential' RETURNING id")
deleted = cur.fetchone()
print(f"Deleted generic entry id={deleted[0] if deleted else 'none'}")

entries = [
    {
        'council': 'canterbury_bankstown',
        'dcp_name': 'Canterbury-Bankstown DCP 2023',
        'chapter_key': 'cb-dcp-2023-ch5-1-bankstown',
        'chapter_label': 'CB DCP 2023 Amendment 11 — Chapter 5.1 Former Bankstown LGA',
        'council_url': 'http://webdocs.bankstown.nsw.gov.au/api/publish?documentPath=aHR0cDovL2lzaGFyZS9zaXRlcy9QbGFubmluZy9TUC9EQ1AgQW1lbmRtZW50cy9EQ1AgLSBXZWJzaXRlIERvY3VtZW50cyAtIEN1cnJlbnQgdmVyc2lvbnMgb24gQ291bmNpbCdzIHdlYnNpdGUvMjAyNi4wMy4xMiAtIERDUCAyMDIzIC0gQU1FTkRNRU5UIDExIC0gQ2hhcHRlciA1LjEgLSBGb3JtZXIgQmFua3N0b3duIExHQS5wZGY=&title=2026.03.12%20-%20DCP%202023%20-%20AMENDMENT%2011%20-%20Chapter%205.1%20-%20Former%20Bankstown%20LGA.pdf',
        'council_page_url': CB_PAGE,
        'notes': 'DH + SD setbacks manually extracted. section_ref ch5-1-* in dcp_setback_controls. Amendment 11, effective 2026-03-12.',
    },
    {
        'council': 'canterbury_bankstown',
        'dcp_name': 'Canterbury-Bankstown DCP 2023',
        'chapter_key': 'cb-dcp-2023-ch5-2-canterbury',
        'chapter_label': 'CB DCP 2023 Amendment 11 — Chapter 5.2 Former Canterbury LGA',
        'council_url': 'http://webdocs.bankstown.nsw.gov.au/api/publish?documentPath=aHR0cDovL2lzaGFyZS9zaXRlcy9QbGFubmluZy9TUC9EQ1AgQW1lbmRtZW50cy9EQ1AgLSBXZWJzaXRlIERvY3VtZW50cyAtIEN1cnJlbnQgdmVyc2lvbnMgb24gQ291bmNpbCdzIHdlYnNpdGUvMjAyNi4wMy4xMiAtIERDUCAyMDIzIC0gQU1FTkRNRU5UIDExIC0gQ2hhcHRlciA1LjIgLSBGb3JtZXIgQ2FudGVyYnVyeSBMR0EucGRm&title=2026.03.12%20-%20DCP%202023%20-%20AMENDMENT%2011%20-%20Chapter%205.2%20-%20Former%20Canterbury%20LGA.pdf',
        'council_page_url': CB_PAGE,
        'notes': 'DH setbacks manually extracted (Table 3+4, major road). SD defers to SEPP H2021 — no DCP rows. section_ref ch5-2-* in dcp_setback_controls. Amendment 11, effective 2026-03-12.',
    },
]

for e in entries:
    cur.execute("""
        INSERT INTO dcp_chapter_registry
            (council, dcp_name, chapter_key, chapter_label, council_url, council_page_url,
             is_active, needs_extraction, check_failures, notes)
        VALUES
            (%(council)s, %(dcp_name)s, %(chapter_key)s, %(chapter_label)s,
             %(council_url)s, %(council_page_url)s,
             TRUE, FALSE, 0, %(notes)s)
        RETURNING id
    """, e)
    row_id = cur.fetchone()[0]
    print(f"Inserted id={row_id}  {e['chapter_key']}")

conn.commit()
conn.close()
print("Done.")
