#!/usr/bin/env python3
"""Insert Strathfield numeric DCP controls from the General Residential DCP (effective 1 September 2026).

prior-art-checked: follows the per-council insert-script pattern (insert_wingecarribee_setbacks.py et al.)
— hand-curated rows with verbatim source_text, section_ref and pdf_page, dup check, dry run. New data only.

Why: Strathfield Council repealed Strathfield Consolidated DCP 2005 Parts A (Dwelling Houses), B (Dual
Occupancy) and C (Multiple Unit Housing) from 1 September 2026 and replaced them with the General
Residential DCP (council Planning Policies page: "From 1 September 2026, the following sections of SCDCP
have been repealed and replaced with the General Residential DCP"). Every Strathfield row cited those
Parts; they were hidden on 2026-09-13 and are superseded here (is_current = FALSE), not deleted.

Source: "Strathfield Development Control Plan – General Residential Development", 38 pages, List of
amendments (p4): Amendment 1, adopted 28 July 2026, effective 1 September 2026. The file is pinned by
SHA-256 (the same hash as registry chapter general-residential-dcp-2026). pdf_page is the PDF page (the
printed page number matches). The plan covers dwelling houses, secondary dwellings, dual occupancies,
multi-dwelling housing, terraces and manor homes; it does not cover residential flat buildings. Where one
table row covers "Multi-Dwelling Housing, Terraces & Manor Homes", the row is stored under
multi_dwelling_housing and the condition says so (no terrace or manor-house type is served).

Not stored: building height in storeys (C3.8.1; the 2026-07-27 DQ rule holds storeys rows), minimum
frontages, internal separation, garage and crossover widths, dwelling sizes, private open space given only
as dimensions (C5.4.1), and manor-home-only controls.

Usage:
    python scripts/insert_strathfield_general_residential.py --pdf <plan.pdf>            # dry run
    python scripts/insert_strathfield_general_residential.py --pdf <plan.pdf> --apply    # write
The dry run performs every write inside a transaction and rolls it back. --apply refuses to run unless
--pdf is given, the file is the pinned plan, and every quote is found, in order, on its stated page.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path

LGA = "strathfield"
SOURCE_CHAPTER_KEY = "general-residential-dcp-2026"
SOURCE_SHA256 = "f879c120e25868617a86bcaf5e23cd517b796dbbac1cd2b1acc6e763cef357da"
TITLE_PAGE_1 = "Strathfield Development Control Plan – General Residential Development"
AMENDMENT_PAGE_4 = "1 Council Endorsement of General Residential 28 July 2026 1 September 2026"
DCP_VERSION = ("Strathfield DCP – General Residential Development, Amendment 1 "
               "(adopted 28 July 2026, effective 1 September 2026)")
EFFECTIVE_DATE = "2026-09-01"
EFFECTIVE_DATE_BASIS = "stated_in_document"
EXTRACTION_METHOD = "manual_curation"
PDF_PAGES = 38
SEGMENT = " ... "  # separates non-adjacent quoted passages; each must appear, in order, on the page

# The 23 current Strathfield rows, all cited to the repealed Parts and hidden on 2026-09-13.
SUPERSEDE_IDS = [683, 751, 752, 753, 754, 755, 756, 757, 758, 759, 760, 761, 762,
                 763, 764, 765, 766, 767, 1053, 1076, 1077, 1078, 1079]
SUPERSEDE_NOTE = (" | Superseded 2026-09-13 by rows from the Strathfield General Residential DCP "
                  "(effective 1 September 2026), which replaced SCDCP 2005 Parts A, B and C.")
REVIEW_NOTE = ("Inserted 2026-09-13 from the Strathfield General Residential DCP (effective 1 September 2026); "
               "quote found on its page by insert_strathfield_general_residential.py --pdf.")


def row(dev_type, control_type, vmin, vmax, unit, condition, source_text, ref, page,
        applicability="universal_residential"):
    return {"lga": LGA, "dev_type": dev_type, "control_type": control_type, "value_min": vmin,
            "value_max": vmax, "unit": unit, "condition": condition, "applicability": applicability,
            "source_text": source_text, "section_ref": f"{SOURCE_CHAPTER_KEY}#{ref}", "pdf_page": page,
            "needs_review": False, "dcp_version": DCP_VERSION, "source_chapter_key": SOURCE_CHAPTER_KEY}


# ── Passages shared by several dwelling types ─────────────────────────────────────────────────
Q_FRONT = ("C3.1.1 The minimum front building setback is the average of the existing front setback at the site "
           "and the two existing dwellings either side of the site (total of 5 dwellings). Where a site does not "
           "have two dwellings either side of the site, the proposal must demonstrate that the proposed setback is "
           "consistent with the prevailing street setback in the block.")
C_FRONT = ("no fixed figure: the average of the existing front setbacks of the site and the two dwellings either "
           "side (5 dwellings); otherwise consistent with the prevailing street setback in the block")
# The R2 rear setback is a formula with a 6m floor and a 10m cap, so it is stored as the 6-10m range it can
# produce; a single 6m would read as the whole R2 requirement. Other zones are a flat 6m.
Q_REAR_R2 = ("C3.6.1 For development in the R2 Low Density Residential zone, the minimum rear building setback for "  # noqa: zone-codes (verbatim plan text, clause C3.6.1 and the zone it names)
             "all developments is: a) 10m or 20% of the average length of the site, whichever is lesser, b) Not less "
             "than 6m.")
C_REAR_R2 = ("R2 Low Density Residential zone: 10m or 20% of the average length of the site, whichever is lesser, "
             "and not less than 6m, so between 6m and 10m depending on the site's length")
Q_REAR_OTHER = "C3.6.2 For development in all other zones, the minimum rear building setback is 6m."
# "Other zones" rows use the exclusion form "other than R2" that conveyancing_db.zone_row_applies reads: an R2
# site is served only the R2 rows, and every other zone only these.
C_REAR_OTHER = "zones other than R2 Low Density Residential"
Q_SECONDARY = ("C12.1.1 For two storey developments orientated towards the primary road, the secondary street side "
               "setback is 3m. Any third storey must be setback an additional 1.5m.")
C_SECONDARY = "corner sites; two storey developments orientated towards the primary road; any third storey an additional 1.5m"
Q_SIDE_DH_DO = ("C3.3 Side setbacks – Dwellings and Dual Occupancies C3.3.1 The minimum side setback for two (2) "
                "storey developments is 1.2m.")
C_SIDE_DH_DO = "two storey developments; where a third storey is permitted and proposed, the plan requires additional setbacks"
Q_PARK = "Dwelling Type Minimum Parking Spaces Required"
Q_LAND = "C5.1.1 Residential developments are to achieve the following landscaped areas:"
Q_DEEP = "C5.2.1 Residential developments are to achieve the following deep soil areas:"
Q_FENCE_FRONT = ("C6.1.1 Where a front fence is proposed, the fence is to be no higher than 1200mm. Front fences "
                 "proposed at greater than 1200mm are to be supported by sufficient justification, including "
                 "consistency with the streetscape and potential impacts on sight lines.")
C_FENCE_FRONT = "front fence; above 1200mm the plan requires justification addressing streetscape consistency and sight-line impacts"
Q_FENCE_SIDE = "C6.2.1 Side and Rear boundary fencing is to be a maximum of 1.8m in height measured from existing ground level"
C_FENCE_SIDE = "side and rear boundary fencing, measured from existing ground level"
Q_SOLAR_OWN = ("C7.2.1 For developments proposing ≤4 dwellings, 50% of the private open space and the principal living "
               "space of all dwellings must receive a minimum of 3 hours of direct sunlight between 8am and 4pm on 21 "
               "June (winter solstice).")
C_SOLAR_OWN = ("proposed dwellings, developments of 4 or fewer dwellings: 50% of the private open space and the "
               "principal living space of all dwellings, 8am to 4pm on 21 June")
Q_SOLAR_NEXT = ("C7.3.1 Direct sunlight to all north facing windows of habitable rooms of adjacent dwellings should not "
                "be reduced to less than 3 hours between 8am and 4pm on 21 June (winter solstice)." + SEGMENT +
                "C7.3.2 A minimum of 50% of the private open space of neighbouring dwellings must receive a minimum of "
                "3 hours of direct sunlight between 8am and 4pm on 21 June.")
C_SOLAR_NEXT = ("neighbouring dwellings: north facing habitable room windows not reduced below 3 hours, and at least "
                "50% of their private open space, 8am to 4pm on 21 June")
MDH_GROUP = "the plan's row covers multi-dwelling housing, terraces and manor homes"


def _shared(dev_type: str) -> list[dict]:
    """Rows whose passage names every dwelling type the plan's sections 1-12 apply to."""
    return [
        row(dev_type, "front_setback", None, None, "m", C_FRONT, Q_FRONT, "C3.1.1", 11),
        row(dev_type, "rear_setback", 6, 10, "m", C_REAR_R2, Q_REAR_R2, "C3.6.1", 15, "zone_specific"),
        row(dev_type, "rear_setback", 6, None, "m", C_REAR_OTHER, Q_REAR_OTHER, "C3.6.2", 15, "zone_specific"),
        row(dev_type, "secondary_street_setback", 3, None, "m", C_SECONDARY, Q_SECONDARY, "C12.1.1", 36),
        row(dev_type, "fencing_height_max", None, 1.2, "m", C_FENCE_FRONT, Q_FENCE_FRONT, "C6.1.1", 28),
        row(dev_type, "fencing_height_max", None, 1.8, "m", C_FENCE_SIDE, Q_FENCE_SIDE, "C6.2.1", 28),
        row(dev_type, "solar_access_hours", 3, None, "hours", C_SOLAR_NEXT, Q_SOLAR_NEXT, "C7.3.1-C7.3.2", 29),
    ]


def _houses_and_dual(dev_type: str, parking: dict, front_landscaping: dict) -> list[dict]:
    """Dwelling houses and dual occupancies share the C3.3 side setback and the 750m2 lot-size tables."""
    return _shared(dev_type) + [
        row(dev_type, "side_setback", 1.2, None, "m", C_SIDE_DH_DO, Q_SIDE_DH_DO, "C3.3.1", 12),
        parking,
        row(dev_type, "landscaping_min", 30, None, "%", "lots less than or equal to 750m²",
            Q_LAND + SEGMENT + "Dwelling Houses Dual Occupancies Lots less than or equal to 750m² 30%", "C5.1.1", 24),
        row(dev_type, "landscaping_min", 35, None, "%", "lots greater than 750m²",
            Q_LAND + SEGMENT + "Dwelling Houses Dual Occupancies Lots less than or equal to 750m² 30% Lots greater "
            "than 750m² 35%", "C5.1.1", 24),
        row(dev_type, "deep_soil_min", 25, None, "%",
            "lots less than or equal to 750m²; each deep soil area at least 2m x 2m (C5.2.2)",
            Q_DEEP + SEGMENT + "Dwelling Houses Dual Occupancies Lots less than or equal to 750m² 25%", "C5.2.1", 25),
        row(dev_type, "deep_soil_min", 30, None, "%", "lots greater than 750m²; each deep soil area at least 2m x 2m (C5.2.2)",
            Q_DEEP + SEGMENT + "Dwelling Houses Dual Occupancies Lots less than or equal to 750m² 25% Lots greater "
            "than 750m² 30%", "C5.2.1", 25),
        front_landscaping,
        row(dev_type, "solar_access_hours", 3, None, "hours", C_SOLAR_OWN, Q_SOLAR_OWN, "C7.2.1", 29),
    ]


Q_FSL_OTHERS = ("C5.3.2 Dual Occupancies, Multi Dwelling Housing, Terraces and Manor Homes - minimum of 40% of the "
                "front building setback is to be deep soil area.")
C_FSL = "of the front building setback to be deep soil area"
Q_MDH_SIDE_A = ("C3.4.2 For a development or a dwelling that is orientated so that the front or rear of the dwelling faces "
                "the side boundary, minimum side setback (being the setback between the façade line and the allotment "
                "side boundary) are:")
C_MDH_ORIENT = "dwelling front or rear faces the side boundary"

ROWS = (
    _houses_and_dual(
        "dwelling_house",
        row("dwelling_house", "car_parking", 2, None, "spaces/dwelling",
            "minimum; where a basement is proposed on an allotment greater than 750m², no maximum number of spaces "
            "(Note 2)", Q_PARK + SEGMENT + "Dwelling House 2 spaces per dwelling", "C4.1.1", 19),
        row("dwelling_house", "front_setback_landscaping", 50, None, "%", C_FSL,
            "C5.3.1 Dwelling Houses - minimum of 50% of the front building setback is to be deep soil area.",
            "C5.3.1", 26),
    )
    + _houses_and_dual(
        "dual_occupancy",
        row("dual_occupancy", "car_parking", 1, None, "spaces/dwelling", "minimum",
            Q_PARK + SEGMENT + "Dual Occupancy 1 space per dwelling", "C4.1.1", 19),
        row("dual_occupancy", "front_setback_landscaping", 40, None, "%", C_FSL, Q_FSL_OTHERS, "C5.3.2", 26),
    )
    + _shared("multi_dwelling_housing")
    + [
        row("multi_dwelling_housing", "side_setback", 1.2, None, "m",
            "fronting the street and two storeys or less; multi-dwelling housing and terraces",
            "C3.4 Side setbacks – Multi-Dwelling Housing and Terraces C3.4.1 For developments that are fronting the "
            "street and are two storeys or less in height, the minimum side setback is 1.2m.", "C3.4.1", 12),
        row("multi_dwelling_housing", "side_setback", 5, None, "m",
            f"R2 Low Density zone; {C_MDH_ORIENT}; to one side boundary, including a minimum 3m wide deep soil area",
            Q_MDH_SIDE_A + SEGMENT + "In the R2 Low Density zone: a) 5m to one side boundary including a minimum 3m "
            "wide deep soil area with landscaping capable of providing a visual buffer", "C3.4.2", 12, "zone_specific"),
        row("multi_dwelling_housing", "side_setback", 3, None, "m",
            f"R2 Low Density zone; {C_MDH_ORIENT}; to the other side boundary, including a 1.5m landscape strip",
            Q_MDH_SIDE_A + SEGMENT + "In the R2 Low Density zone:" + SEGMENT + "b) 3m to the other side boundary "
            "including a 1.5m landscape strip", "C3.4.2", 12, "zone_specific"),
        row("multi_dwelling_housing", "side_setback", 4, None, "m",
            f"zones other than R2 Low Density (medium density or any other zone); {C_MDH_ORIENT}; to one side "
            "boundary, including a minimum 2m wide deep soil area",
            Q_MDH_SIDE_A + SEGMENT + "In the R3 Medium Density zone or any other zone: a) 4m to one side boundary "
            "including a minimum 2m wide deep soil area", "C3.4.2", 12, "zone_specific"),
        row("multi_dwelling_housing", "side_setback", 2, None, "m",
            f"zones other than R2 Low Density (medium density or any other zone); {C_MDH_ORIENT}; to the other "
            "side boundary, including a 1.5m landscape strip",
            Q_MDH_SIDE_A + SEGMENT + "In the R3 Medium Density zone or any other zone:" + SEGMENT + "b) 2m to the "
            "other side boundary including a 1.5m landscape strip", "C3.4.2", 12, "zone_specific"),
        row("multi_dwelling_housing", "side_setback", 2.7, None, "m",
            "three storey developments: at level 2 (1.2m at ground and level 1 plus an additional 1.5m)",
            "C3.4.4 Three storey developments must feature an additional 1.5m setback for the second level. With a "
            "1.2m setback for ground and level 1, this would require a 2.7m setback at level 2.", "C3.4.4", 15),
        row("multi_dwelling_housing", "car_parking", 1, None, "spaces/dwelling",
            f"minimum; {MDH_GROUP} (including the residential component of any mixed use or shop top housing)",
            "Multi-Dwelling Housing, Terraces & Manor Homes (including the residential component of any mixed use or "
            "shop top housing development) 1 space per dwelling", "C4.1.1", 19),
        row("multi_dwelling_housing", "landscaping_min", 25, None, "%", f"lots less than 1,500m²; {MDH_GROUP}",
            Q_LAND + SEGMENT + "Multi-dwelling Housing Lots less than 1,500m² 25%", "C5.1.1", 24),
        row("multi_dwelling_housing", "landscaping_min", 30, None, "%",
            f"lots greater than or equal to 1,500m²; {MDH_GROUP} (the table continues from page 24)",
            "Terraces Manor Homes Lots greater than or equal to 1,500m² 30%", "C5.1.1", 25),
        row("multi_dwelling_housing", "deep_soil_min", 20, None, "%",
            f"lots less than 1,500m²; {MDH_GROUP}; each deep soil area at least 2m x 2m (C5.2.2)",
            Q_DEEP + SEGMENT + "Multi-dwelling Housing Terraces Manor Homes Lots less than 1,500m² 20%", "C5.2.1", 25),
        row("multi_dwelling_housing", "deep_soil_min", 25, None, "%",
            f"lots greater than or equal to 1,500m²; {MDH_GROUP}; each deep soil area at least 2m x 2m (C5.2.2)",
            Q_DEEP + SEGMENT + "Multi-dwelling Housing Terraces Manor Homes Lots less than 1,500m² 20% Lots greater "
            "than or equal to 1,500m² 25%", "C5.2.1", 25),
        row("multi_dwelling_housing", "front_setback_landscaping", 40, None, "%", f"{C_FSL}; {MDH_GROUP}",
            Q_FSL_OTHERS, "C5.3.2", 26),
        row("multi_dwelling_housing", "solar_access_hours", 3, None, "hours",
            C_SOLAR_OWN + "; more than 4 dwellings: 70% of the proposed dwellings must achieve that (C7.2.2)",
            Q_SOLAR_OWN + SEGMENT + "C7.2.2 Where a development features >4 dwellings, 70% of the proposed dwellings "
            "must achieve the 50% solar access requirement in 7.2.1 above.", "C7.2.1-C7.2.2", 29),
    ]
    + [
        row("secondary_dwelling", "car_parking", 0, None, "spaces/dwelling",
            "no spaces required; a space must not add a driveway crossover from the primary road (Note 1)",
            Q_PARK + " Secondary Dwelling 0 Spaces required", "C4.1.1", 19, "secondary_dwelling_specific"),
        row("secondary_dwelling", "rear_setback", 3, None, "m",
            "detached secondary dwellings; nil setback where the site has access to a rear laneway",
            "Detached secondary dwellings should be setback as follows: a) 3m from the rear boundary unless the site "
            "has access to a rear laneway, in which case the secondary dwelling can have a nil setback,",
            "C13.2", 38, "secondary_dwelling_specific"),
        row("secondary_dwelling", "side_setback", 1.5, None, "m", "detached secondary dwellings; from any side boundary",
            "Detached secondary dwellings should be setback as follows:" + SEGMENT + "b) 1500mm from any side boundary,",
            "C13.2", 38, "secondary_dwelling_specific"),
        row("secondary_dwelling", "separation_from_dwelling", 6, None, "m",
            "detached secondary dwellings; from the wall of the primary dwelling",
            "c) Detached secondary dwellings must be a minimum of 6m from the wall of the primary dwelling.",
            "C13.2", 38, "secondary_dwelling_specific"),
        row("secondary_dwelling", "private_open_space", 6, None, "m2",
            "primary private open space directly accessible to the internal living areas; the plan prints the minimum "
            "dimension as '1m²'",
            "C13.5.2 Secondary dwellings must be provided with a primary private open space area directly accessible "
            "to the internal living areas of the dwelling. The private open space area should: a) have an area of "
            "6m² and minimum dimension of 1m².", "C13.5.2", 38, "secondary_dwelling_specific"),
    ]
)


def _norm(text: str) -> str:
    for a, b in (("–", "-"), ("—", "-"), ("²", "2"), ("’", "'"), ("‘", "'")):
        text = text.replace(a, b)
    return " ".join(text.lower().split())


def quote_on_page(quote: str, page_text: str) -> bool:
    """True when every SEGMENT-separated passage of ``quote`` appears on the page, in order."""
    text, pos = _norm(page_text), 0
    for segment in quote.split(SEGMENT):
        seg = _norm(segment)
        if not seg:
            return False
        found = text.find(seg, pos)
        if found < 0:
            return False
        pos = found + len(seg)
    return True


def check_against_pdf(pdf_path: Path) -> list[str]:
    """Problems found reading the plan; empty when the file is the pinned plan and every quote is on its page.

    The hash is checked first, so a draft or a later amendment that keeps the quoted wording cannot pass as
    the adopted Amendment 1; the title and the p4 amendment line are then read from the file itself.
    """
    digest = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        return [f"{pdf_path} sha256 {digest[:12]} is not the pinned General Residential DCP ({SOURCE_SHA256[:12]})"]
    import fitz  # PyMuPDF, imported here so the row data loads without it

    with fitz.open(pdf_path) as doc:
        pages = {i: page.get_text() for i, page in enumerate(doc, start=1)}
    problems = []
    if len(pages) != PDF_PAGES:
        problems.append(f"expected {PDF_PAGES} pages, found {len(pages)}")
    if not quote_on_page(TITLE_PAGE_1, pages.get(1, "")):
        problems.append("page 1 does not carry the plan title")
    if not quote_on_page(AMENDMENT_PAGE_4, pages.get(4, "")):
        problems.append("page 4 does not carry the Amendment 1 adoption and effective dates")
    return problems + [f"{r['dev_type']}/{r['control_type']} ({r['section_ref']}): quote not on page {r['pdf_page']}"
                       for r in ROWS if not quote_on_page(r["source_text"], pages.get(r["pdf_page"], ""))]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Insert Strathfield numeric DCP controls from the General Residential DCP.")
    ap.add_argument("--pdf", type=Path, help="local copy of the plan; every quote is checked on its page")
    ap.add_argument("--apply", action="store_true", help="commit (default: roll back)")
    args = ap.parse_args(argv)
    if args.apply and not args.pdf:
        print("--apply needs --pdf: rows are written only after every quote is found on its page")
        return 2
    if args.pdf:
        problems = check_against_pdf(args.pdf)
        for p in problems:
            print("PDF CHECK:", p)
        if problems:
            return 1
        print(f"PDF check: pinned file, all {len(ROWS)} quotes found on their pages")

    import psycopg2
    from dotenv import load_dotenv

    load_dotenv()
    conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"], connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30s'")
        cur.execute("""SELECT content_hash FROM dcp_chapter_registry WHERE council = %s AND chapter_key = %s
                         AND is_active AND r2_public_pdf_url IS NOT NULL""", (LGA, SOURCE_CHAPTER_KEY))
        registered = cur.fetchone()
        if registered is None:
            print(f"registry chapter {LGA}/{SOURCE_CHAPTER_KEY} with a public PDF copy is missing; register it first")
            return 1
        if registered[0] != SOURCE_SHA256:
            print(f"registry chapter {LGA}/{SOURCE_CHAPTER_KEY} links a different file ({str(registered[0])[:12]}); "
                  "the rows would cite a PDF other than the one checked")
            return 1
        cur.execute("SELECT * FROM dcp_setback_controls WHERE lga = %s ORDER BY is_current DESC, id", (LGA,))  # prior-art-checked: this script's own rollback backup, not a new data source
        backups = Path(__file__).resolve().parents[1] / "data" / "db_rollback_backups"
        backups.mkdir(parents=True, exist_ok=True)
        backup = backups / f"dcp_setback_controls_pre_strathfield_grdcp_{datetime.now():%Y-%m-%d_%H%M}.csv"
        with open(backup, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([d[0] for d in cur.description])
            writer.writerows(cur.fetchall())
        print(f"backup: {backup}")

        cur.execute("""UPDATE dcp_setback_controls SET is_current = FALSE,
                              review_reason = COALESCE(review_reason, '') || %s
                        WHERE id = ANY(%s) AND lga = %s AND is_current AND needs_review""",
                    (SUPERSEDE_NOTE, SUPERSEDE_IDS, LGA))
        if cur.rowcount != len(SUPERSEDE_IDS):
            conn.rollback()
            print(f"supersede matched {cur.rowcount} of {len(SUPERSEDE_IDS)} rows; nothing written")
            return 1
        verified = datetime.now().astimezone() if args.pdf else None
        for r in ROWS:
            cur.execute("""SELECT id FROM dcp_setback_controls WHERE lga = %s AND dev_type = %s AND control_type = %s
                             AND COALESCE(condition, '') = COALESCE(%s, '') AND is_current""",
                        (LGA, r["dev_type"], r["control_type"], r["condition"]))
            if cur.fetchone():
                conn.rollback()
                print(f"duplicate live row for {r['dev_type']}/{r['control_type']} [{r['condition']}]; nothing written")
                return 1
            cur.execute("""INSERT INTO dcp_setback_controls
                             (lga, dev_type, control_type, value_min, value_max, unit, condition, applicability,
                              source_text, section_ref, pdf_page, dcp_version, is_current, extraction_method,
                              source_chapter_key, needs_review, review_reason, last_verified_at,
                              effective_date, effective_date_basis)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,%s,%s,FALSE,%s,%s,%s,%s)""",
                        (LGA, r["dev_type"], r["control_type"], r["value_min"], r["value_max"], r["unit"],
                         r["condition"], r["applicability"], r["source_text"], r["section_ref"], r["pdf_page"],
                         DCP_VERSION, EXTRACTION_METHOD, SOURCE_CHAPTER_KEY, REVIEW_NOTE, verified,
                         EFFECTIVE_DATE, EFFECTIVE_DATE_BASIS))
        cur.execute("""SELECT count(*) FROM dcp_setback_controls
                        WHERE lga = %s AND is_current AND NOT needs_review""", (LGA,))
        live = cur.fetchone()[0]
        if live != len(ROWS):
            conn.rollback()
            print(f"expected {len(ROWS)} live Strathfield rows after insert, found {live}; nothing written")
            return 1
        if not args.apply:
            conn.rollback()
            print(f"DRY RUN: superseded {len(SUPERSEDE_IDS)}, inserted {len(ROWS)}; rolled back")
            return 0
        conn.commit()
        print(f"COMMITTED: superseded {len(SUPERSEDE_IDS)}, inserted {len(ROWS)} live Strathfield rows")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
