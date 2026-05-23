"""
Update 8 needs_review rows for Leichhardt, Marrickville, and Burwood.

Extracted from DCP PDFs using PyMuPDF text extraction (2026-05-22).
All 3 PDFs had text layers — no OCR needed.

Results:
- Leichhardt (3 rows): → not_applicable (BLZ system, no prescriptive numerics)
- Marrickville max_site_coverage: → numeric (Table 1, 40–60% by lot area)
- Marrickville landscaping_min: → not_applicable (qualitative front setback only)
- Burwood rear_setback: → numeric (Table 3: 3m single / 6m two storey)
- Burwood landscaping_min: → numeric (30% front / 70% rear yard soft landscaping)
"""

import os
import sys
import psycopg2
from datetime import date

ENV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "..", "..", ".env"
)
# Try multiple .env locations
for candidate in [ENV_PATH, os.path.join(os.path.dirname(__file__), "..", ".env")]:
    candidate = os.path.normpath(candidate)
    if os.path.exists(candidate):
        with open(candidate) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())
        break

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found")
    sys.exit(1)

TODAY = date.today().isoformat()

# ── Updates ──────────────────────────────────────────────────────────────────

UPDATES = [
    # ── Leichhardt: 3 rows → not_applicable (BLZ system) ──
    {
        "id": 1085,
        "lga": "leichhardt",
        "control_type": "deep_soil_min",
        "value_min": None,
        "value_max": None,
        "needs_review": False,
        "condition": "No prescriptive numeric deep soil control. DCP uses Building Location Zone (BLZ) system with qualitative siting controls per Distinctive Neighbourhood.",
        "source_text": (
            "Leichhardt DCP 2013 Part C Section 3 (Residential Provisions): "
            "Controls are structured by Distinctive Neighbourhood using a Building Location Zone (BLZ) system. "
            "The BLZ defines building envelopes through front, side, and rear setback lines and height planes "
            "but does not prescribe minimum deep soil percentages or areas. "
            "Stormwater infiltration and deep soil tree planting are listed as objectives (O12) "
            "but no numeric minimum is specified."
        ),
        "section_ref": "part-C-s3",
        "review_reason": "Resolved: BLZ system — no prescriptive numeric deep soil control exists",
    },
    {
        "id": 1086,
        "lga": "leichhardt",
        "control_type": "landscaping_min",
        "value_min": None,
        "value_max": None,
        "needs_review": False,
        "condition": "Qualitative only: 'soft landscape areas must be included at front and rear of site.' No numeric minimum percentage. BLZ system controls siting.",
        "source_text": (
            "Leichhardt DCP 2013 Part C Section 3 (Residential Provisions): "
            "Qualitative requirement that 'soft landscape areas must be included at front and rear of site.' "
            "No whole-of-site numeric landscaping minimum is specified. "
            "The BLZ (Building Location Zone) system controls building envelopes "
            "and implicitly preserves some open space, but does not set a landscaping percentage."
        ),
        "section_ref": "part-C-s3",
        "review_reason": "Resolved: qualitative only — no numeric landscaping minimum exists in DCP",
    },
    {
        "id": 1087,
        "lga": "leichhardt",
        "control_type": "max_site_coverage",
        "value_min": None,
        "value_max": None,
        "needs_review": False,
        "condition": "No prescriptive numeric site coverage control. BLZ system defines building footprint limits per Distinctive Neighbourhood through setback lines and height planes.",
        "source_text": (
            "Leichhardt DCP 2013 Part C Section 3 (Residential Provisions): "
            "Site coverage is controlled implicitly through the Building Location Zone (BLZ) system, "
            "which defines permitted building envelopes by Distinctive Neighbourhood. "
            "No numeric maximum site coverage percentage is specified. "
            "The BLZ approach means coverage varies by lot geometry and neighbourhood character."
        ),
        "section_ref": "part-C-s3",
        "review_reason": "Resolved: BLZ system — no prescriptive numeric site coverage control exists",
    },

    # ── Marrickville max_site_coverage → numeric (Table 1) ──
    {
        "id": 1090,
        "lga": "marrickville",
        "control_type": "max_site_coverage",
        "value_min": 40,
        "value_max": 60,
        "needs_review": False,
        "condition": (
            "C13 Table 1 by allotment area: 0–300sqm = on merit; "
            ">300–350sqm = 60%; >350–400sqm = 55%; "
            ">400–500sqm = 50%; >500–700sqm = 45%; >700sqm = 40%"
        ),
        "source_text": (
            "Marrickville DCP 2011 s4.1.6.3 C13: 'The following maximum site coverage must not be exceeded: "
            "Allotment Area / Maximum Site Coverage — "
            "0–300sqm: On Merit (site coverage will be based on the site and context analysis); "
            ">300–350sqm: 60%; >350–400sqm: 55%; >400–500sqm: 50%; "
            ">500–700sqm: 45%; >700sqm: 40%.'"
        ),
        "section_ref": "s4.1.6.3",
        "review_reason": "Resolved: Table 1 extracted — 6-tier site coverage by allotment area (40–60%)",
    },

    # ── Marrickville landscaping_min → not_applicable ──
    {
        "id": 1089,
        "lga": "marrickville",
        "control_type": "landscaping_min",
        "value_min": None,
        "value_max": None,
        "needs_review": False,
        "condition": (
            "No whole-of-site numeric landscaping minimum for dwelling houses. "
            "s2.18.11.1 C11 requires front setback to be pervious landscape; "
            "s4.1.6.3 controls site coverage by allotment area (implicitly preserving open space)."
        ),
        "source_text": (
            "Marrickville DCP 2011 s2.18.11.1 C11: 'The entire front setback must be of a pervious landscape "
            "with the exception of driveways, paths and the like.' "
            "No whole-of-site minimum landscaping percentage is specified for low density residential. "
            "Landscaping and open space are addressed qualitatively in objectives (O12, O16) "
            "and through site coverage limits at s4.1.6.3."
        ),
        "section_ref": "s2.18.11.1",
        "review_reason": "Resolved: qualitative front setback pervious requirement only — no whole-of-site numeric minimum",
    },

    # ── Burwood rear_setback → numeric (Table 3) ──
    {
        "id": 1080,
        "lga": "burwood",
        "control_type": "rear_setback",
        "value_min": 3,
        "value_max": 6,
        "needs_review": False,
        "condition": "Table 3: Single storey 3m, two storey (second storey component) 6m",
        "source_text": (
            "Burwood DCP 2013 Chapter 4, s4.5, Table 3 (Setback Requirements for Single Dwelling Houses): "
            "'Rear Setback — (i) Two storey (second storey component of the dwelling only): 6m. "
            "(ii) Single storey: 3m.'"
        ),
        "section_ref": "s4.5-table-3",
        "review_reason": "Resolved: Table 3 extracted — rear setback 3m (single storey) / 6m (two storey)",
    },

    # ── Burwood landscaping_min → numeric (area-specific) ──
    {
        "id": 1081,
        "lga": "burwood",
        "control_type": "landscaping_min",
        "value_min": 30,
        "value_max": 70,
        "needs_review": False,
        "condition": (
            "Area-specific: P1 minimum 30% of front setback = soft landscaping; "
            "P2 minimum 70% of rear yard = soft landscaping. "
            "No single whole-of-site percentage."
        ),
        "source_text": (
            "Burwood DCP 2013 Chapter 4, s4.5 (Landscaped Areas): "
            "'P1: A minimum 30% of the front setback (i.e. front yard) is to consist of soft landscaping.' "
            "'P2: Rear yards will not be permitted to be dominated by hard landscaping. "
            "A minimum of 70% of the rear yard shall be soft landscaping.'"
        ),
        "section_ref": "s4.5-landscaped-areas",
        "review_reason": "Resolved: front 30% + rear 70% soft landscaping extracted — area-specific, not whole-of-site",
    },
]


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print(f"Updating {len(UPDATES)} needs_review rows...\n")

    for u in UPDATES:
        # Verify row exists and matches expected lga/control_type
        cur.execute(
            "SELECT lga, control_type FROM dcp_setback_controls WHERE id = %s AND is_current = true",
            (u["id"],),
        )
        row = cur.fetchone()
        if not row:
            print(f"  SKIP id={u['id']}: not found or not current")
            continue
        if row[0] != u["lga"] or row[1] != u["control_type"]:
            print(f"  SKIP id={u['id']}: mismatch — DB has {row[0]}/{row[1]}, expected {u['lga']}/{u['control_type']}")
            continue

        cur.execute(
            """
            UPDATE dcp_setback_controls SET
                value_min = %s,
                value_max = %s,
                needs_review = %s,
                condition = %s,
                source_text = %s,
                section_ref = %s,
                review_reason = %s,
                reviewed_at = NOW(),
                last_verified_at = %s,
                extraction_method = 'text_extraction'
            WHERE id = %s
            """,
            (
                u["value_min"],
                u["value_max"],
                u["needs_review"],
                u["condition"],
                u["source_text"],
                u["section_ref"],
                u["review_reason"],
                TODAY,
                u["id"],
            ),
        )
        status = "numeric" if u["value_min"] is not None else "not_applicable"
        print(f"  OK id={u['id']}: {u['lga']}/{u['control_type']} -> {status}")

    conn.commit()
    print(f"\nCommitted {len(UPDATES)} updates.")

    # Verify
    cur.execute(
        "SELECT COUNT(*) FROM dcp_setback_controls WHERE needs_review = true AND is_current = true"
    )
    remaining = cur.fetchone()[0]
    print(f"Remaining needs_review rows: {remaining}")

    conn.close()


if __name__ == "__main__":
    main()
