import os, psycopg2
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()
cur.execute("""
    UPDATE dcp_chapter_registry
    SET needs_extraction = FALSE,
        notes = 'Extraction aborted — only 2 sections from 11 pages. Likely scanned/image PDF. Manual inspection required before retry.'
    WHERE council = 'leichhardt' AND chapter_key = 'appendix-e-water-guidelines'
""")
conn.commit()
conn.close()
print("Done.")
