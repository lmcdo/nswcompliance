#!/usr/bin/env python3
"""
Register council DCP source URLs in dcp_chapter_registry for the
13 LGAs that have dcp_setback_controls rows.

The r2_legislation_monitor and dcp_watchdog will then detect when
council PDFs change — triggering a manual setback review.
"""
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()

ENTRIES = [
    {
        'council': 'canterbury_bankstown',
        'dcp_name': 'Canterbury-Bankstown DCP 2023',
        'chapter_key': 'cb-dcp-2023-residential',
        'chapter_label': 'Canterbury-Bankstown DCP 2023 (Ch 5 Residential)',
        'council_url': 'https://hdp-au-prod-app-cbnks-haveyoursay-files.s3.ap-southeast-2.amazonaws.com/5617/4468/8884/Canterbury-Bankstown_Development_Control_Plan_2023.pdf',
        'notes': 'Setbacks manually extracted from Ch 5.1 (Bankstown) and Ch 5.2 (Canterbury). In dcp_setback_controls, section_ref ch5-1-* and ch5-2-*.',
    },
    {
        'council': 'blacktown',
        'dcp_name': 'Blacktown DCP 2015',
        'chapter_key': 'blacktown-dcp-2015-part-c',
        'chapter_label': 'Blacktown DCP 2015 Part C — Residential Areas',
        'council_url': 'https://www.blacktown.nsw.gov.au/files/content/public/plan-build/stage-2-plans-and-guidelines/blacktown-planning-controls/blacktown-development-control-plan-2015/dcp-part-c-development-within-the-residential-areas.pdf',
        'notes': 'DH setbacks s3.11; SD setbacks s4.3.5/4.3.6. Stored in dcp_setback_controls.',
    },
    {
        'council': 'parramatta',
        'dcp_name': 'Parramatta DCP 2023 (Amendment 4)',
        'chapter_key': 'parramatta-dcp-2023-full',
        'chapter_label': 'Parramatta DCP 2023 Amendment 4 (full — 1563 pages)',
        'council_url': 'https://cityofparramatta.nsw.gov.au/sites/council/files/2024-09/Parramatta_DCP_2023_(Amendment_4)-As_published_18_September_2024-BOOK_VERSION.pdf',
        'notes': 'PDF is 1563 pages — exceeds Mistral OCR 1000-page limit. Need specific residential chapter PDF. No setback rows in dcp_setback_controls yet.',
    },
    {
        'council': 'cumberland',
        'dcp_name': 'Cumberland DCP Part B — Residential Zones 2021',
        'chapter_key': 'cumberland-dcp-part-b-residential',
        'chapter_label': 'Cumberland DCP Part B — Development in Residential Zones',
        'council_url': 'https://www.cumberland.nsw.gov.au/sites/default/files/inline-files/cumberland-dcp-part-b-development-residential-zones-2021.pdf',
        'notes': 'DH + SD setbacks in dcp_setback_controls.',
    },
    {
        'council': 'campbelltown',
        'dcp_name': 'Campbelltown (Sustainable City) DCP 2015',
        'chapter_key': 'campbelltown-dcp-part3-low-medium',
        'chapter_label': 'Campbelltown DCP 2015 Part 3 — Low and Medium Density Residential',
        'council_url': 'https://www.campbelltown.nsw.gov.au/files/sharedassets/public/v/2/build-and-develop/documents/dcp/volume-1/part-3-low-and-medium-desnity-residential-development.pdf',
        'notes': 'DH s3.6.1.3; SD s3.6.2.2. Both stored in dcp_setback_controls.',
    },
    {
        'council': 'penrith',
        'dcp_name': 'Penrith DCP 2014',
        'chapter_key': 'penrith-dcp-2014-part-d2',
        'chapter_label': 'Penrith DCP 2014 Part D2 — Residential Development',
        'council_url': 'https://www.penrithcity.nsw.gov.au/images/documents/building-development/planning-zoning/planning-controls/Penrith_DCP_2014_Part_D2_Residential_Development2.pdf',
        'notes': 'DH s2.1.2 + SD s2.3.3 manually inserted. Stored in dcp_setback_controls.',
    },
    {
        'council': 'liverpool',
        'dcp_name': 'Liverpool DCP 2008',
        'chapter_key': 'liverpool-dcp-2008-part8',
        'chapter_label': 'Liverpool DCP 2008 Part 8 — Dwelling Houses (300–900m², R1/R2/R3)',
        'council_url': 'https://www.liverpool.nsw.gov.au/__data/assets/pdf_file/0015/111822/Part-8-Dwelling-houses-and-class-10-structures-on-lots-greater-than-300m2-but-less-than-900m2-in-the-R1-R2-R3-zones-PDF-copy-linked-to-webpage-23-January-2017.pdf',
        'notes': 'DH only (Part 8 scope). SD not covered — defer to SEPP H2021. Stored in dcp_setback_controls.',
    },
    {
        'council': 'ku_ring_gai',
        'dcp_name': 'Ku-ring-gai DCP — Part 5 Secondary Dwellings',
        'chapter_key': 'ku-ring-gai-dcp-part5-secondary',
        'chapter_label': 'Ku-ring-gai DCP Part 5 — Secondary Dwellings',
        'council_url': 'https://www.krg.nsw.gov.au/files/assets/public/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-planning-and-development/dcp_principal_section_a_-_part_5_-_secondary_dwellings.pdf',
        'notes': 'DH rear 12m (depth>48m); SD rear 6m. Stored in dcp_setback_controls.',
    },
    {
        'council': 'hornsby',
        'dcp_name': 'Hornsby DCP 2024',
        'chapter_key': 'hornsby-dcp-2024-part3-residential',
        'chapter_label': 'Hornsby DCP 2024 Part 3 — Residential (last amended June 2025)',
        'council_url': 'https://www.hornsby.nsw.gov.au/files/assets/public/v/2/property/building-and-development/policies-and-guidelines/hornsby-development-control-plan/documents/hdcp-2024-part-3-residential.pdf',
        'notes': 'DH Table 3.1.2-a. No dedicated SD section — SD inherits DH controls. Stored in dcp_setback_controls.',
    },
    {
        'council': 'northern_beaches',
        'dcp_name': 'Warringah DCP 2011',
        'chapter_key': 'warringah-dcp-2011-full',
        'chapter_label': 'Warringah (Northern Beaches) DCP 2011 — as amended May 2016',
        'council_url': 'https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/_R15/Warringah%20DCP%202011%20-%20as%20amended%207%20May%202016.pdf',
        'notes': 'R2 front 6.5m / rear 6m. Side setbacks are map-based. SD not in DCP text. Stored in dcp_setback_controls.',
    },
]

INSERT_SQL = """
    INSERT INTO dcp_chapter_registry
        (council, dcp_name, chapter_key, chapter_label, council_url,
         is_active, needs_extraction, check_failures, notes)
    VALUES
        (%(council)s, %(dcp_name)s, %(chapter_key)s, %(chapter_label)s, %(council_url)s,
         TRUE, FALSE, 0, %(notes)s)
    ON CONFLICT (council, chapter_key) DO UPDATE SET
        council_url     = EXCLUDED.council_url,
        chapter_label   = EXCLUDED.chapter_label,
        notes           = EXCLUDED.notes,
        updated_at      = NOW()
    RETURNING id, council, chapter_key
"""

# Check for unique constraint first
cur.execute("SELECT conname FROM pg_constraint WHERE conrelid = 'dcp_chapter_registry'::regclass AND contype = 'u'")
constraints = [r[0] for r in cur.fetchall()]
print(f"Unique constraints: {constraints}")

print(f"\nRegistering {len(ENTRIES)} source URLs...")
for e in ENTRIES:
    try:
        cur.execute(INSERT_SQL, e)
        row = cur.fetchone()
        print(f"  [{'INSERT' if row else 'UPDATE':6}] id={row[0]:4d}  {row[1]:25} {row[2]}")
    except Exception as ex:
        # If no unique constraint on (council, chapter_key), use plain INSERT
        conn.rollback()
        cur.execute("""
            SELECT id FROM dcp_chapter_registry WHERE council = %(council)s AND chapter_key = %(chapter_key)s
        """, e)
        existing = cur.fetchone()
        if existing:
            cur.execute("""
                UPDATE dcp_chapter_registry SET council_url=%(council_url)s, notes=%(notes)s, updated_at=NOW()
                WHERE council=%(council)s AND chapter_key=%(chapter_key)s
            """, e)
            print(f"  [UPDATE] {e['council']:25} {e['chapter_key']}")
        else:
            cur.execute("""
                INSERT INTO dcp_chapter_registry (council, dcp_name, chapter_key, chapter_label, council_url, is_active, needs_extraction, check_failures, notes)
                VALUES (%(council)s, %(dcp_name)s, %(chapter_key)s, %(chapter_label)s, %(council_url)s, TRUE, FALSE, 0, %(notes)s)
                RETURNING id
            """, e)
            row_id = cur.fetchone()[0]
            print(f"  [INSERT] id={row_id:4d}  {e['council']:25} {e['chapter_key']}")

conn.commit()
print("\nDone.")
conn.close()
