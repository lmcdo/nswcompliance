import os, psycopg2
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()

NEW_CHAPTERS = [
    'appendix-d-waste-template',
    'appendix-e-water-guidelines',
    'amendment-1-george-upward-streets',
    'tree-management-technical-manual',
]

print("=== New chapter provisions — frontend readiness ===\n")
for key in NEW_CHAPTERS:
    cur.execute("""
        SELECT
            p.ref_number,
            p.v2_topic,
            p.v2_applicable_dev_types,
            p.v2_is_actionable,
            p.pdf_source_file,
            p.pdf_page,
            r.r2_public_pdf_url
        FROM regulatory_provisions p
        JOIN dcp_chapter_registry r
          ON r.council = p.source_council AND r.chapter_key = p.source_chapter_key
        WHERE p.source_council = 'leichhardt'
          AND p.source_chapter_key = %s
          AND p.is_current = TRUE
    """, (key,))
    rows = cur.fetchall()
    print(f"[{key}] — {len(rows)} provisions")
    for r in rows:
        dev_types = r[2] or []
        print(f"  ref={r[0]}")
        print(f"    topic={r[1]} | actionable={r[3]} | dev_types={dev_types}")
        print(f"    pdf_page={r[5]} | r2_public_pdf_url={'SET' if r[6] else 'MISSING'}")
    print()

conn.close()
