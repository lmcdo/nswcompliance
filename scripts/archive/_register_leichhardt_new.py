import os, psycopg2
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()

NEW_HUB_URL = "https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-controls-lep-and-dcp/development-control-plans-dcp/leichhardt-dcp/leichhardt-dcp"

# 1. Update part-c-s2 URL to full-resolution version
cur.execute("""
    UPDATE dcp_chapter_registry
    SET council_url = %s,
        council_page_url = %s,
        needs_extraction = TRUE,
        notes = 'Updated to full-resolution PDF (29.78MB) — was low-res version'
    WHERE council = 'leichhardt' AND chapter_key = 'part-c-s2-urban-character'
    RETURNING chapter_key
""", (
    "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/Leichhardt%20DCP%202013%20-%206%20-%20Part%20C%20Place%20Section%202%20-%20with%20IWLEP%202022%20amendments.pdf",
    NEW_HUB_URL,
))
print(f"Updated: {cur.fetchone()}")

# 2. Update ALL leichhardt chapters to new hub page URL
cur.execute("""
    UPDATE dcp_chapter_registry
    SET council_page_url = %s
    WHERE council = 'leichhardt'
""", (NEW_HUB_URL,))
print(f"Updated hub URL for {cur.rowcount} leichhardt chapters")

# Get next sort_order
cur.execute("SELECT MAX(sort_order) FROM dcp_chapter_registry WHERE council = 'leichhardt'")
sort_order = cur.fetchone()[0] + 1

NEW_CHAPTERS = [
    # (chapter_key, chapter_label, council_url, is_spatial, needs_extraction, notes)
    (
        "appendix-c-urban-framework-plans",
        "Appendix C – Urban Framework Plans",
        "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/Leichhardt%20DCP%202013%20-%2015%20-Appendix%20C%20Urban%20Framework%20Plans%20-%20with%20IWLEP%202022%20amendments.pdf",
        True, False, "Maps/plans appendix — spatial only, no numbered controls"
    ),
    (
        "appendix-d-waste-template",
        "Appendix D – Site Waste Minimisation and Management Plan Template",
        "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/LE9962_1.PDF",
        False, False, "Template document — no numbered controls, not extractable"
    ),
    (
        "appendix-e-water-guidelines",
        "Appendix E – Water Guidelines",
        "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/Leichhardt%20DCP%202013%20-%2017%20-%20Appendix%20E%20Water%20Guidelines%20-%20with%20IWLEP%202022%20amendments.pdf",
        False, True, "Substantive water guidelines — extract for numbered controls"
    ),
    (
        "flood-map-north",
        "Flood Control Lot Map – Northern view",
        "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/Flood%20Control%20Lot%20Map%20-%20Northern%20view.pdf",
        True, False, "Spatial map — no extractable controls"
    ),
    (
        "flood-map-central",
        "Flood Control Lot Map – Central view",
        "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/Flood%20Control%20Lot%20Map%20%E2%80%93%20Central%20View.pdf",
        True, False, "Spatial map — no extractable controls"
    ),
    (
        "flood-map-south",
        "Flood Control Lot Map – Southern view",
        "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/Flood%20Control%20Lot%20Map%20-%20Southern%20view.pdf",
        True, False, "Spatial map — no extractable controls"
    ),
    (
        "foreshore-flood-map-north",
        "Foreshore Flood Control Lot Map – Northern view",
        "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/Foreshore%20Flood%20Control%20Lot%20Map%20-%20Northern%20view.pdf",
        True, False, "Spatial map — no extractable controls"
    ),
    (
        "foreshore-flood-map-central",
        "Foreshore Flood Control Lot Map – Central view",
        "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/Foreshore%20Flood%20Control%20Lot%20Map%20-%20Central%20view.pdf",
        True, False, "Spatial map — no extractable controls"
    ),
    (
        "appendix-f-late-night-trading-maps",
        "Appendix F – Late Night Trading Maps",
        "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/Leichhardt%20DCP%202013%20-%2018%20-%20Appendix%20F%20Late%20Night%20Trading%20Maps%20with%20IWLEP%202022%20amendments.pdf",
        True, False, "Maps appendix — spatial only, no numbered controls"
    ),
    (
        "amendment-1-george-upward-streets",
        "Amendment 1 – George and Upward Streets, Leichhardt",
        "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/Amendment%201%20DCP%202014%20for%20George%20and%20Upward%20Streets%2C%20Leichhardt.pdf",
        False, False, "Site-specific 2014 amendment — controls baked into main chapter PDFs"
    ),
    (
        "tree-management-technical-manual",
        "Tree Management Technical Manual",
        "https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/Tree%20Management%20Technical%20Manual%20%281%29.pdf",
        False, True, "Separate technical manual referenced by DCP — contains numbered conditions"
    ),
]

for chap in NEW_CHAPTERS:
    key, label, url, is_spatial, needs_extraction, notes = chap
    cur.execute("""
        INSERT INTO dcp_chapter_registry (
            council, dcp_name, chapter_key, chapter_label,
            council_url, council_page_url,
            sort_order, is_active, is_spatial,
            needs_extraction, notes
        ) VALUES (
            'leichhardt', 'Leichhardt DCP 2013', %s, %s,
            %s, %s,
            %s, TRUE, %s,
            %s, %s
        )
        ON CONFLICT (council, chapter_key) DO NOTHING
        RETURNING chapter_key
    """, (key, label, url, NEW_HUB_URL, sort_order, is_spatial, needs_extraction, notes))
    result = cur.fetchone()
    status = "inserted" if result else "already exists"
    print(f"  {key}: {status}")
    sort_order += 1

conn.commit()
conn.close()
print("\nDone.")
