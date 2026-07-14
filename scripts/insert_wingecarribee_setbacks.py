#!/usr/bin/env python3
"""Insert Wingecarribee numeric DCP controls (Bowral/Mittagong/Moss Vale town plans).

prior-art-checked: follows the established per-council insert-script pattern
(insert_ashfield_sd_setbacks.py et al.) — hand-curated rows with verbatim
source_text + section_ref, dup-check, dry-run mode. New data only, no new logic.

Source documents (fetched from Planning Portal /dcp planURLs, 2026-07-14):
  - Wingecarribee DCP 2010 - Bowral Town Plan - as amended 23 Sep 2015 (296 pp)
  - Wingecarribee DCP 2010 - Mittagong Town Plan - as amended 17 Jun 2015
  - Wingecarribee DCP 2010 - Moss Vale Town Plan - as amended 17 Jun 2015
Phase-0 smoke test (ce-wingecarribee-numeric-onboarding-2026-07.md) verified the
three town plans share one Part C template with IDENTICAL residential values
(front/side setbacks checked verbatim in all three), so rows are loaded once
under lga='wingecarribee' scoped to the town plans via `applicability`.
pdf_page refers to the Bowral Town Plan PDF (the reference copy).

KNOWN SOURCE DEFECT: C3.9.2(c)(ii) omits the height threshold in ALL THREE
documents ("3.5 metres where development is more than ___ metres in height") —
that row is inserted with needs_review=TRUE so consumers fail closed (#707)
until the user rules on it.
"""
import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")

DRY_RUN = "--dry-run" in sys.argv

LGA = "wingecarribee"
APPLICABILITY = "development_specific"  # constrained enum; town-plan scope carried by dcp_version
DCP_VERSION = "Wingecarribee DCP 2010 town plans, as amended 2015"
EXTRACTION_METHOD = "manual_curation"  # constrained enum


def row(dev_type, control_type, vmin, vmax, unit, condition, source_text,
        section_ref, pdf_page, needs_review=False, review_reason=None):
    return {
        "lga": LGA, "dev_type": dev_type, "control_type": control_type,
        "value_min": vmin, "value_max": vmax, "unit": unit,
        "condition": condition, "applicability": APPLICABILITY,
        "source_text": source_text, "section_ref": section_ref,
        "pdf_page": pdf_page, "needs_review": needs_review,
        "review_reason": review_reason,
    }


ROWS = [
    # ----- dwelling_house — SECTION 2 DETACHED DWELLINGS -----
    row("dwelling_house", "front_setback", 4.5, None, "m",
        "lot less than 900m2; exclusive of garage setbacks; in general, subject to site assessment",
        "C2.6.2(e) In general, subject to site assessment, Council requires the following front setbacks, "
        "exclusive of garage setbacks: Lot size less than 900m2 — minimum front setback 4.5m",
        "part-c-s2/C2.6.2(e)", 193),
    row("dwelling_house", "front_setback", 6.5, None, "m",
        "lot between 900m2 and 1500m2; exclusive of garage setbacks; subject to site assessment",
        "C2.6.2(e) Lot size between 900m2 and 1500m2 — minimum front setback 6.5m",
        "part-c-s2/C2.6.2(e)", 193),
    row("dwelling_house", "front_setback", 15.0, None, "m",
        "lot over 1500m2; exclusive of garage setbacks; subject to site assessment",
        "C2.6.2(e) Lot size over 1500m2 — minimum front setback 15m",
        "part-c-s2/C2.6.2(e)", 193),
    row("dwelling_house", "side_setback", 0.9, None, "m",
        "lot less than 900m2; in general, subject to site assessment",
        "C2.7.2(c) In general, subject to site assessment, Council requires the following side setbacks: "
        "Lot size less than 900m2 — minimum required side setback 0.9m",
        "part-c-s2/C2.7.2(c)", 194),
    row("dwelling_house", "side_setback", 1.5, None, "m",
        "lot between 900m2 and 1500m2; subject to site assessment",
        "C2.7.2(c) Lot size between 900m2 and 1500m2 — minimum required side setback 1.5m",
        "part-c-s2/C2.7.2(c)", 194),
    row("dwelling_house", "side_setback", 2.5, None, "m",
        "lot over 1500m2; subject to site assessment",
        "C2.7.2(c) Lot size over 1500m2 — minimum required side setback 2.5m",
        "part-c-s2/C2.7.2(c)", 194),
    row("dwelling_house", "rear_setback", 3.0, 8.0, "m",
        "lot less than 900m2; depending on building height — sliding scale above 3.8m rear building height "
        "(minimum for lot size plus three times the height of the rear of the dwelling exceeding 3.8m)",
        "C2.8.2(c) Lot size less than 900m2 — minimum required rear setback 3.0m-8.0m depending on building "
        "height. (d) the minimum rear setback increases on a sliding scale once the building height at the "
        "rear of the dwelling exceeds 3.8m",
        "part-c-s2/C2.8.2(c)-(d)", 195),
    row("dwelling_house", "rear_setback", 5.0, 12.0, "m",
        "lot between 900m2 and 1500m2; depending on building height — sliding scale above 3.8m rear height",
        "C2.8.2(c) Lot size between 900m2 and 1500m2 — minimum required rear setback 5.0m-12.0m depending on "
        "building height",
        "part-c-s2/C2.8.2(c)-(d)", 195),
    row("dwelling_house", "rear_setback", 10.0, 15.0, "m",
        "lot over 1500m2; depending on building height — sliding scale above 3.8m rear height",
        "C2.8.2(c) Lot size over 1500m2 — minimum required rear setback 10m-15m depending on building height",
        "part-c-s2/C2.8.2(c)-(d)", 195),
    row("dwelling_house", "max_height", 2, None, "storeys",
        None,
        "C2.9.2(a) The maximum height of a dwelling house shall not exceed two (2) storeys, 'storey' being "
        "as defined in Section C1.5",
        "part-c-s2/C2.9.2(a)", 196),
    row("dwelling_house", "max_height", 1, None, "storeys",
        "within a Heritage Conservation Area; additional rooms permissible within roof spaces if roof form "
        "compatible with desired streetscape character",
        "C2.9.2(b) Notwithstanding subclause (a) above, within a Heritage Conservation Area, the maximum "
        "height of a dwelling house shall not exceed one (1) storey with additional rooms permissible "
        "within the roof spaces of buildings",
        "part-c-s2/C2.9.2(b)", 196),
    row("dwelling_house", "landscaped_area_min", 35, None, "%",
        "lot less than 2000m2; or 90m2, whichever is the greater",
        "C2.13.2(a) Table C2.2: Lot size less than 2,000m2 — minimum Private Landscaped Open Space 35% of "
        "the site area or 90m2, whichever is the greater",
        "part-c-s2/C2.13.2(a)-Table-C2.2", 200),
    row("dwelling_house", "landscaped_area_min", 50, None, "%",
        "lot less than 2000m2 on a site which is an Item of Heritage or located within a Heritage "
        "Conservation Area",
        "C2.13.2(a) Table C2.2: Less than 2,000m2 on a site which is an Item of Heritage or located within "
        "a Heritage Conservation Area — minimum Private Landscaped Open Space 50% of the site area",
        "part-c-s2/C2.13.2(a)-Table-C2.2", 200),
    row("dwelling_house", "landscaped_area_min", 50, None, "%",
        "lot between 2000m2 and 4000m2",
        "C2.13.2(a) Table C2.2: Lot size between 2,000m2 and 4,000m2 — minimum Private Landscaped Open "
        "Space 50% of the site area",
        "part-c-s2/C2.13.2(a)-Table-C2.2", 200),
    row("dwelling_house", "landscaped_area_min", 75, None, "%",
        "lot over 4000m2",
        "C2.13.2(a) Table C2.2: Lot size over 4,000m2 — minimum Private Landscaped Open Space 75% of the "
        "site area",
        "part-c-s2/C2.13.2(a)-Table-C2.2", 200),
    row("dwelling_house", "max_site_coverage", 65, None, "%",
        "lot less than 2000m2; 'Maximum Development Footprint' in Table C2.2",
        "C2.13.2(a) Table C2.2: Lot size less than 2,000m2 — Maximum Development Footprint 65% of the site area",
        "part-c-s2/C2.13.2(a)-Table-C2.2", 200),
    row("dwelling_house", "max_site_coverage", 50, None, "%",
        "lot less than 2000m2 heritage item or Heritage Conservation Area; 'Maximum Development Footprint'",
        "C2.13.2(a) Table C2.2: Less than 2,000m2 heritage — Maximum Development Footprint 50% of the site area",
        "part-c-s2/C2.13.2(a)-Table-C2.2", 200),
    row("dwelling_house", "max_site_coverage", 50, None, "%",
        "lot between 2000m2 and 4000m2; 'Maximum Development Footprint'",
        "C2.13.2(a) Table C2.2: Between 2,000m2 and 4,000m2 — Maximum Development Footprint 50% of the site area",
        "part-c-s2/C2.13.2(a)-Table-C2.2", 200),
    row("dwelling_house", "max_site_coverage", 25, None, "%",
        "lot over 4000m2; 'Maximum Development Footprint'",
        "C2.13.2(a) Table C2.2: Over 4,000m2 — Maximum Development Footprint 25% of the site area",
        "part-c-s2/C2.13.2(a)-Table-C2.2", 200),
    row("dwelling_house", "car_parking", 2, None, "spaces/dwelling",
        "minimum two car spaces behind the building line; may include an access way to the side of the "
        "dwelling of minimum width 2700mm",
        "C2.12.2(f) New development shall provide a minimum of two car spaces behind the building line "
        "which may include an access way to the side of the dwelling of a minimum width of 2700mm",
        "part-c-s2/C2.12.2(f)", 198),

    # ----- multi_dwelling — SECTION 3 MEDIUM DENSITY DEVELOPMENT -----
    row("multi_dwelling", "front_setback", 8.0, None, "m",
        "contextual approach — consistent with adjacent dwellings; where inconsistent or no adjacent "
        "dwellings, assessed on merit; 'to date, the accepted standard has been 8 metres'",
        "C3.8.2(c) In the case where there are inconsistent setbacks immediately adjacent to the site ... "
        "Council will assess the proposed front setback on merit. To date, the accepted standard has been "
        "8 metres",
        "part-c-s3/C3.8.2(c)", 212),
    row("multi_dwelling", "side_setback", 2.0, None, "m",
        "development up to 3 metres in height above natural ground level; standard minimum, subject to "
        "consistency with adjacent context",
        "C3.9.2(c)(i) Council's standard minimum side setbacks are: Two (2) metres where development is up "
        "to 3 metres in height above natural ground level",
        "part-c-s3/C3.9.2(c)(i)", 213),
    row("multi_dwelling", "side_setback", 3.5, None, "m",
        "development above the height threshold (threshold digit omitted in the source document)",
        "C3.9.2(c)(ii) 3.5 metres where development is more than [ ] metres in height above natural ground "
        "level [sic — the height figure is missing in the published document]",
        "part-c-s3/C3.9.2(c)(ii)", 213,
        needs_review=True,
        review_reason="Source defect: the height threshold digit is omitted in ALL THREE town plans "
                      "(Bowral p213, Mittagong p208, Moss Vale p214 — text reads 'more than metres in "
                      "height'). Structurally implied 3m as the complement of clause (i), but unverified — "
                      "needs user ruling or council confirmation."),
    row("multi_dwelling", "private_open_space", 50, None, "m2",
        "per dwelling; consolidated principal area; minimum length 5 metres",
        "C3.13.2(b) All dwellings must provide a minimum private open space area of 50 m2 with a minimum "
        "length of 5 metres",
        "part-c-s3/C3.13.2(b)", 216),
    row("multi_dwelling", "landscaping_min", 50, None, "%",
        "of site; paths, patios and soft landscaping included; building footprint, driveways, car parking "
        "and garbage storage excluded; detailed landscaping plan required at DA stage",
        "C3.14(a) 50 per cent (50%) of any site developed for multi dwelling housing shall be landscaped "
        "to the satisfaction of Council",
        "part-c-s3/C3.14(a)", 217),
    row("multi_dwelling", "car_parking", 1, None, "spaces/dwelling",
        "1 and 2 bedroom dwellings; dedicated resident parking; plus dedicated visitor parking at 1 space "
        "per 3 dwellings (rounded up)",
        "C3.17.2(a)(i) Dedicated resident parking at a rate of 1 space per 1 and 2 bedroom dwellings; "
        "(iii) Dedicated visitor parking at a rate of 1 space per 3 dwellings (rounded up to the nearest "
        "whole number)",
        "part-c-s3/C3.17.2(a)", 219),
    row("multi_dwelling", "car_parking", 2, None, "spaces/dwelling",
        "3 or more bedroom dwellings; dedicated resident parking; plus dedicated visitor parking at 1 "
        "space per 3 dwellings (rounded up)",
        "C3.17.2(a)(ii) Dedicated resident parking at a rate of 2 spaces per 3 or more bedroom dwellings",
        "part-c-s3/C3.17.2(a)", 219),

    # ----- residential_flat_building — SECTION 4 -----
    row("residential_flat_building", "private_open_space", 30, None, "m2",
        "ground floor flats; minimum length 4 metres",
        "C4.4.2(b) All ground floor flats must provide a minimum private open space area of 30 m2 with a "
        "minimum length of 4 metres",
        "part-c-s4/C4.4.2(b)", 226),
    row("residential_flat_building", "private_open_space", 15, None, "m2",
        "above ground floor flats; minimum length 3 metres",
        "C4.4.2(c) All above ground floor flats must provide a minimum private open space area of 15 m2 "
        "with a minimum length of 3 metres",
        "part-c-s4/C4.4.2(c)", 226),
    row("residential_flat_building", "landscaping_min", 50, None, "%",
        "of site; detailed landscaping plan required at DA stage, approved prior to Construction Certificate",
        "C4.5(a) Fifty per cent (50%) of any site developed for a residential flat building shall be "
        "landscaped to the satisfaction of Council",
        "part-c-s4/C4.5(a)", 226),
    row("residential_flat_building", "car_parking", 1, None, "spaces/dwelling",
        "1 and 2 bedroom dwellings; dedicated resident parking; plus visitor 1 space per 3 dwellings "
        "(rounded up); at least one parking space per dwelling shall be covered; no parking between "
        "building line and frontage",
        "C4.6(b) Dedicated resident parking at a rate of 1 space per 1 and 2 bedroom dwellings; (d) "
        "Dedicated visitor parking at a rate of 1 space per 3 dwellings (rounded up); (g) At least one "
        "parking space per dwelling shall be a covered parking space",
        "part-c-s4/C4.6", 227),
    row("residential_flat_building", "car_parking", 2, None, "spaces/dwelling",
        "3 or more bedroom dwellings; dedicated resident parking; plus visitor 1 space per 3 dwellings "
        "(rounded up)",
        "C4.6(c) Dedicated resident parking at a rate of 2 spaces per 3 or more bedroom dwellings",
        "part-c-s4/C4.6", 227),
]


def main():
    db_url = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        print("No SUPABASE_DB_URL/DATABASE_URL set")
        sys.exit(1)
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # dcp_setback_controls.lga has an FK to lga_registry — register the LGA
    # first (idempotent; same pattern as existing registry rows, no parent_lga
    # since Wingecarribee is not an amalgamation).
    if not DRY_RUN:
        cur.execute(
            """
            INSERT INTO lga_registry (slug, display_name, parent_lga, is_active)
            VALUES ('wingecarribee', 'Wingecarribee', NULL, TRUE)
            ON CONFLICT (slug) DO NOTHING
            """
        )

    inserted = skipped = 0
    for r in ROWS:
        cur.execute(
            """
            SELECT id FROM dcp_setback_controls
            WHERE lga = %s AND dev_type = %s AND control_type = %s
              AND COALESCE(condition, '') = COALESCE(%s, '')
            """,
            (r["lga"], r["dev_type"], r["control_type"], r["condition"]),
        )
        if cur.fetchone():
            print(f"SKIP (dup): {r['dev_type']}/{r['control_type']} cond={str(r['condition'])[:50]}")
            skipped += 1
            continue

        flag = " [NEEDS_REVIEW]" if r["needs_review"] else ""
        if DRY_RUN:
            vm = f"{r['value_min']}" + (f"-{r['value_max']}" if r["value_max"] else "")
            print(f"DRY-RUN: {r['dev_type']:26s} {r['control_type']:20s} {vm:>8s} {r['unit'] or '':16s}"
                  f" p{r['pdf_page']}{flag}")
        else:
            cur.execute(
                """
                INSERT INTO dcp_setback_controls
                  (lga, dev_type, control_type, value_min, value_max, unit,
                   condition, applicability, source_text, section_ref,
                   pdf_page, dcp_version, extraction_method, is_current,
                   needs_review, review_reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s, %s)
                """,
                (r["lga"], r["dev_type"], r["control_type"], r["value_min"],
                 r["value_max"], r["unit"], r["condition"], r["applicability"],
                 r["source_text"], r["section_ref"], r["pdf_page"],
                 DCP_VERSION, EXTRACTION_METHOD, r["needs_review"], r["review_reason"]),
            )
            print(f"INSERTED: {r['dev_type']}/{r['control_type']} = {r['value_min']}{flag}")
            inserted += 1

    if not DRY_RUN:
        conn.commit()
    conn.close()
    print(f"\nDone. inserted={inserted} skipped={skipped} total_rows={len(ROWS)} dry_run={DRY_RUN}")


if __name__ == "__main__":
    main()
