"""
Phase 1E: Non-numeric explanation rows
Insert NULL-value rows for all confirmed non-numeric gaps so users see
WHY there's no number, not just silence.

condition prefix = programmatic filter key
source_text = user-visible explanation
"""
import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

rows = []

# ---------------------------------------------------------------------------
# 1. CHARACTER-BASED front setbacks (no numeric value — match prevailing)
# ---------------------------------------------------------------------------
char_setback_lgas = [
    ("waverley", "Waverley DCP 2022", "C1.2(a)", 7, "waverley-dcp-2022-part-c1",
     "The front setback is to be consistent with the predominant front setback of adjacent development on the same side of the street."),
    ("woollahra", "Woollahra DCP 2015", "B3.2.2", 7, "woollahra-dcp-2015-ch-b3",
     "The front setback is to be not less than the average of the setbacks of the two nearest residential buildings on the same side of the street."),
    ("inner_west", "Inner West DCP (former councils)", "various", None, None,
     "Front setback must be consistent with the established building line in the street. Former Ashfield/Leichhardt/Marrickville DCPs — character-based, no numeric minimum."),
]
for lga, dcp, ref, page, chap_key, txt in char_setback_lgas:
    for dev_type in ["dwelling_house", "dual_occupancy"]:
        rows.append({
            "lga": lga, "control_type": "front_setback", "dev_type": dev_type,
            "value_min": None, "value_max": None, "unit": None,
            "condition": "CHARACTER-BASED: front setback determined by prevailing streetscape; no numeric minimum in DCP",
            "applicability": "universal_residential",
            "source_text": txt,
            "section_ref": ref, "pdf_page": page,
            "dcp_version": dcp, "source_chapter_key": chap_key,
        })

# ---------------------------------------------------------------------------
# 2. QUALITATIVE landscaping (no numeric % — words only)
# ---------------------------------------------------------------------------
qual_landscape = [
    ("blacktown", "Blacktown DCP 2015", "6.9.1", 57, "blacktown-dcp-2015-part-c",
     "All parts of the site not built-upon or paved shall be landscaped with grass, trees, shrubs and/or other vegetation. No numeric minimum percentage specified."),
    ("campbelltown", "Campbelltown SCDCP 2015 (updated 02/09/2024)", "3.4", None, "campbelltown-scdcp-2015-part3",
     "Landscaping plan required; no minimum percentage of total site area specified for landscaping. Deep soil minimum of 20% applies separately."),
]
for lga, dcp, ref, page, chap_key, txt in qual_landscape:
    for dev_type in ["dwelling_house", "dual_occupancy"]:
        rows.append({
            "lga": lga, "control_type": "landscaping_min", "dev_type": dev_type,
            "value_min": None, "value_max": None, "unit": None,
            "condition": "QUALITATIVE: DCP requires landscaping but specifies no numeric minimum percentage of site area",
            "applicability": "universal_residential",
            "source_text": txt,
            "section_ref": ref, "pdf_page": page,
            "dcp_version": dcp, "source_chapter_key": chap_key,
        })

# ---------------------------------------------------------------------------
# 3. ALTERNATIVE-METRIC landscaping (woollahra uses deep soil + tree canopy)
# ---------------------------------------------------------------------------
for dev_type in ["dwelling_house", "dual_occupancy"]:
    rows.append({
        "lga": "woollahra", "control_type": "landscaping_min", "dev_type": dev_type,
        "value_min": None, "value_max": None, "unit": None,
        "condition": "ALTERNATIVE-METRIC: landscaping controlled via deep soil zone (35% of site) and tree canopy (35% of site) — no separate landscaped area minimum",
        "applicability": "universal_residential",
        "source_text": "Woollahra DCP 2015 uses deep soil landscaped area (35%) and tree canopy area (35%) controls instead of a separate minimum landscaped area percentage.",
        "section_ref": "B3.7.1", "pdf_page": 48,
        "dcp_version": "Woollahra DCP 2015", "source_chapter_key": "woollahra-dcp-2015-ch-b3",
    })

# ---------------------------------------------------------------------------
# 4. FSR-CONTROLLED site coverage (LEP FSR governs, DCP has no %)
# ---------------------------------------------------------------------------
fsr_site_coverage_lgas = [
    ("woollahra", "Woollahra DCP 2015"),
    ("parramatta", "Parramatta DCP 2023"),
    ("cumberland", "Cumberland DCP 2021"),
    ("liverpool", "Liverpool DCP 2008 (as amended)"),
    ("penrith", "Penrith DCP 2014"),
    ("randwick", "Randwick Comprehensive DCP 2013"),
    ("sutherland_shire", "Sutherland Shire DCP 2015"),
    ("hornsby", "Hornsby DCP 2013"),
    ("georges_river", "Georges River DCP 2021"),
]
for lga, dcp in fsr_site_coverage_lgas:
    for dev_type in ["dwelling_house", "dual_occupancy"]:
        rows.append({
            "lga": lga, "control_type": "max_site_coverage", "dev_type": dev_type,
            "value_min": None, "value_max": None, "unit": None,
            "condition": "FSR-CONTROLLED: site coverage governed by Floor Space Ratio in the LEP, not a DCP percentage",
            "applicability": "universal_residential",
            "source_text": "No maximum site coverage percentage specified in the DCP. Development bulk is controlled by Floor Space Ratio (FSR) and building height limits in the LEP.",
            "section_ref": "LEP", "pdf_page": None,
            "dcp_version": dcp, "source_chapter_key": None,
        })

# ---------------------------------------------------------------------------
# 5. DEFERS-TO-ADG deep soil (no council-specific value)
# ---------------------------------------------------------------------------
adg_deep_soil_lgas = [
    ("cumberland", "Cumberland DCP 2021"),
    ("georges_river", "Georges River DCP 2021"),
    ("liverpool", "Liverpool DCP 2008 (as amended)"),
    ("penrith", "Penrith DCP 2014"),
    ("randwick", "Randwick Comprehensive DCP 2013"),
    ("sutherland_shire", "Sutherland Shire DCP 2015"),
]
for lga, dcp in adg_deep_soil_lgas:
    for dev_type in ["dwelling_house", "dual_occupancy"]:
        rows.append({
            "lga": lga, "control_type": "deep_soil_min", "dev_type": dev_type,
            "value_min": None, "value_max": None, "unit": None,
            "condition": "DEFERS-TO-ADG: no council-specific deep soil minimum in DCP; NSW Apartment Design Guide standards apply to RFBs (7% min for sites <650sqm)",
            "applicability": "universal_residential",
            "source_text": "No council-specific deep soil zone minimum percentage specified in the DCP for low-density residential. The NSW Apartment Design Guide applies to residential flat buildings.",
            "section_ref": "ADG", "pdf_page": None,
            "dcp_version": dcp, "source_chapter_key": None,
        })

# ---------------------------------------------------------------------------
# Check for duplicates before inserting
# ---------------------------------------------------------------------------
cols = list(rows[0].keys())
placeholders = ", ".join(["%s"] * len(cols))
col_str = ", ".join(cols)

inserted = 0
skipped = 0
for row in rows:
    # Check if a row already exists for this (lga, control_type, dev_type) with NULL values
    cur.execute("""
    SELECT id FROM dcp_setback_controls
    WHERE lga = %s AND control_type = %s AND dev_type = %s
      AND value_min IS NULL AND value_max IS NULL AND is_current = true
    LIMIT 1
    """, (row["lga"], row["control_type"], row["dev_type"]))
    if cur.fetchone():
        skipped += 1
        continue

    vals = [row[c] for c in cols]
    cur.execute(f"""
    INSERT INTO dcp_setback_controls ({col_str}, is_current, needs_review, extraction_method)
    VALUES ({placeholders}, true, false, 'text_extraction')
    """, vals)
    inserted += 1

print(f"Inserted {inserted} explanation rows, skipped {skipped} duplicates")
print(f"Breakdown:")
print(f"  Character-based front setbacks: {len(char_setback_lgas) * 2} target")
print(f"  Qualitative landscaping: {len(qual_landscape) * 2} target")
print(f"  Alternative-metric landscaping (woollahra): 2 target")
print(f"  FSR-controlled site coverage: {len(fsr_site_coverage_lgas) * 2} target")
print(f"  ADG-deferred deep soil: {len(adg_deep_soil_lgas) * 2} target")

cur.execute('SELECT COUNT(*) FROM dcp_setback_controls WHERE is_current = true')
print(f"\nTotal active rows: {cur.fetchone()[0]}")

cur.execute('SELECT COUNT(*) FROM dcp_setback_controls WHERE is_current = true AND value_min IS NULL AND value_max IS NULL')
print(f"Of which explanation rows (NULL values): {cur.fetchone()[0]}")

conn.close()
