import os, psycopg2
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()

HUB_URL = "https://www.innerwest.nsw.gov.au/development-controls-lep-and-dcp/marrickville-development-control-plan-dcp"

cur.execute("SELECT MAX(sort_order) FROM dcp_chapter_registry WHERE council = 'marrickville'")
sort_order = cur.fetchone()[0] + 1

NEW_CHAPTERS = [
    ("cover", "Cover Page",
     "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/Marrickville%20DCP%202011%20-%20Cover.pdf",
     False, False, "Cover page"),
    ("map-parking-areas", "Parking Areas Map",
     "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/Marrickville%20DCP%202011%20-%202.10%20Parking%20Areas%20Map.pdf",
     True, False, "Spatial map"),
    ("map-biodiversity", "Biodiversity Map",
     "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/Marrickville%20DCP%202011%20-%202.13%20Biodiversity%20Map.pdf",
     True, False, "Spatial map"),
    ("map-thornley-scenic", "Thornley Street Scenic Protection Area Map",
     "https://www.innerwest.nsw.gov.au/sites/default/files/2026-01/Marrickville%20DCP%202011%20-%202.14%20Thornley%20Street%20Scenic%20Protection%20Area%20Map.pdf",
     True, False, "Spatial map"),
    ("map-flood-liable-land", "Flood Liable Land Map",
     "https://www.innerwest.nsw.gov.au/sites/default/files/2026-01/Marrickville%20Flood%20Liable%20Land%20Map.pdf",
     True, False, "Spatial map"),
    ("map-flood-planning-area", "Flood Planning Area Map",
     "https://www.innerwest.nsw.gov.au/sites/default/files/2026-01/Marrickville%20Flood%20Planning%20Area%20Map.pdf",
     True, False, "Spatial map"),
    ("cover-part-4", "Cover Page – Part 4",
     "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/Marrickville%20DCP%202011%20-%204%200%20Cover.pdf",
     False, False, "Cover page"),
    ("cover-part-7", "Cover Page – Part 7",
     "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/Marrickville%20DCP%202011%20-%207.0%20Cover.pdf",
     False, False, "Cover page"),
    ("map-heritage-conservation-areas", "Heritage Conservation Areas Map",
     "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/Marrickville%20DCP%202011%20-%208.0%20Heritage%20Conservation%20Areas%20Map.pdf",
     True, False, "Spatial map"),
    ("cover-part-9", "Cover Page – Part 9",
     "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/Marrickville%20DCP%202011%20-%209%200%20Cover.pdf",
     False, False, "Cover page"),
    ("map-planning-precincts", "Planning Precincts Map",
     "https://www.innerwest.nsw.gov.au/sites/default/files/2026-01/Marrickville%20DCP%202011%20-%209.0%20Precincts%20Map.pdf",
     True, False, "Spatial map"),
]

for key, label, url, is_spatial, needs_extraction, notes in NEW_CHAPTERS:
    cur.execute("""
        INSERT INTO dcp_chapter_registry (
            council, dcp_name, chapter_key, chapter_label,
            council_url, council_page_url,
            sort_order, is_active, is_spatial,
            needs_extraction, notes
        ) VALUES (
            'marrickville', 'Marrickville DCP 2011', %s, %s,
            %s, %s,
            %s, TRUE, %s, %s, %s
        )
        ON CONFLICT (council, chapter_key) DO NOTHING
        RETURNING chapter_key
    """, (key, label, url, HUB_URL, sort_order, is_spatial, needs_extraction, notes))
    result = cur.fetchone()
    print(f"  {key}: {'inserted' if result else 'already exists'}")
    sort_order += 1

conn.commit()
conn.close()
print("Done.")
