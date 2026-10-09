"""DQ-142 findings, 2026-10-10: building-area controls quoted from stored DCP text.

prior-art-checked: reuse not viable because this is the reviewed input for
scripts/dq142_build_controls_migration.py, not a new capability; no existing
file holds these findings.

Each finding came from a read-only search of regulatory_provisions and is
re-verified by scripts/dq142_build_controls_migration.py (quote must be in the
named current row, figure must be in the quote) before any SQL is written.
Writes data/dq142_controls_2026-10-10.json.
"""
import json

S = []


def a(lga, dt, ct, v, unit, cond, quotes, page, sec):
    S.append(dict(lga=lga, dev_type=dt, control_type=ct, value_min=v, unit=unit,
                  condition=cond, quotes=quotes, pdf_page=page, section_ref=sec))


def nf(s):
    return "NO FIGURE: " + s


# Parramatta / Penrith / Waverley / Woollahra
a("parramatta", "dual_occupancy", "front_setback", 6, "m", "and consistent with the prevailing setback along the street",
  [[105058, "Buildings must be set back a minimum of 6 metres from the street boundary and be consistent with the prevailing setback along the street"]], 67, "3.3.2.2 C.05")
a("parramatta", "dual_occupancy", "rear_setback", 10, "m", "or 30% of the site length, whichever is greater; corner sites minimum 6 m",
  [[105058, "A rear setback equal to 30% of the site length or 10 metres, whichever is greater"]], 67, "3.3.2.2 C.14")
a("parramatta", "dual_occupancy", "side_setback", 1.5, "m", "buildings to occupy a maximum of 80% of the lot width",
  [[105058, "Buildings must be set back a minimum of 1.5 metres from side boundaries"]], 67, "3.3.2.2 C.09")
a("parramatta", "dwelling_house", "rear_setback", None, None, nf("formula - rear setback equal to 30% of the site length"),
  [[105051, "A rear setback equal to 30% of the site length"]], 60, "3.3.1.2 C.10")
a("parramatta", "secondary_dwelling", "landscaping_min", 40, "%", "as for dwelling houses (3.3.3.4 C.02 a)",
  [[105066, "Secondary dwellings do not reduce the deep soil or landscaped area of the lot to less than the minimum required for dwelling houses"],
   [105053, "A minimum 40% of the total site area, including deep soil zone, is to be provided as landscaping"]], 77, "3.3.3.4 C.02(a); 3.3.1.4 C.02")
a("parramatta", "secondary_dwelling", "front_setback", None, None, nf("must not be forward of the main building frontage"),
  [[105065, "Secondary dwellings must not be forward of the main building frontage"]], 76, "3.3.3.2 C.08")
a("parramatta", "secondary_dwelling", "rear_setback", 3, "m", "6 m for buildings up to 2 storeys",
  [[105065, "Secondary dwellings must provide a minimum 3 metre rear setback for buildings up to 1 storey in height"]], 76, "3.3.3.2 C.12")
a("parramatta", "secondary_dwelling", "side_setback", 0.9, "m", "2 m for buildings up to 2 storeys",
  [[105065, "Secondary dwellings must be setback a minimum of 900mm from side boundaries"]], 76, "3.3.3.2 C.11")
a("penrith", "dual_occupancy", "front_setback", 5.5, "m", "or the average of the immediate neighbours' setbacks, whichever is greater",
  [[104913, "adopt a 5.5m minimum whichever is the greater dimension"]], 19, "D2 2.2.5 B.3")
a("penrith", "dual_occupancy", "rear_setback", 4, "m", "6 m for a two storey building",
  [[104913, "The minimum rear setback for a single storey building (or any single storey component of a building) is 4m"]], 19, "D2 2.2.5 B.1")
a("penrith", "dual_occupancy", "side_setback", 0.9, "m", "greater for second storey walls, consistent with the building envelope",
  [[104915, "a minimum 900 mm setback at ground level"]], 21, "D2 2.2.6 B.6")
a("penrith", "secondary_dwelling", "front_setback", None, None, nf("behind the front building line of the primary dwelling"),
  [[104931, "Secondary dwellings must be located behind the front building line of the primary dwelling"]], 39, "D2 2.3.3 B.3a")
W = "New buildings and extensions to existing buildings are to extend no further than the front and rear predominant building lines"
for dt in ("dual_occupancy", "dwelling_house"):
    a("waverley", dt, "front_setback", None, None, nf("predominant front building line (three adjacent neighbours either side)"),
      [[126239, W]], 171, "C1.2.1(a)")
    a("waverley", dt, "rear_setback", None, None, nf("predominant rear building line, determined for each floor level"),
      [[126239, W], [126239, "The predominant rear building line is determined separately for each floor level"]], 171, "C1.2.1(a),(b)")
a("waverley", "dual_occupancy", "side_setback", 0.9, "m", "first floor 0.9 m; second floor 1.5 m; third floor on merit",
  [[126240, "Ground Floor 0.9m"]], 172, "C1.2.2(a) Table 1")
for dt in ("dual_occupancy", "dwelling_house"):
    a("woollahra", dt, "deep_soil_min", 35, "%", "30% in the Wolseley Road area",
      [[127010, "35% of the site area is deep soil landscaped area"]], 46, "B3.7.1 C2")  # noqa: zone-codes -- DCP section number
    a("woollahra", dt, "front_setback", None, None,
      nf("formula - average of the three most typical setbacks of the four closest residential buildings on the same side of the street"),
      [[127006, "The front setback of the building envelope is determined by averaging the three most typical setbacks of the four closest residential buildings"]], 12, "B3.2.2 C1")  # noqa: zone-codes -- DCP section number
    a("woollahra", dt, "rear_setback", None, None, nf("formula - 25% of the average of the two side boundary dimensions"),
      [[127006, "The minimum rear setback control is 25% of the average of the two side boundary dimensions"]], 12, "B3.2.4 C1")  # noqa: zone-codes -- DCP section number
    a("woollahra", dt, "side_setback", None, None, nf("by site width, Figure 5A table (0.9 m below 9 m wide up to 4.5 m at 30 m+)"),
      [[127006, "The minimum side setback for dwelling houses, semi-detached dwellings and dual occupancies is determined by the table in Figure 5A"]], 12, "B3.2.3 C1")  # noqa: zone-codes -- DCP section number

# Sydney / Cumberland / Georges River / Hornsby
a("city_of_sydney", "dwelling_house", "deep_soil_min", 15, "%", "lots greater than 150 sqm",
  [[95522, "For lots greater than 150sqm, the minimum amount of deep soil is to be 15% of the site area"]], 9, "4.1.3.4(1)")
a("city_of_sydney", "dwelling_house", "front_setback", None, None, nf("Building setbacks map, else the predominant setting in the street"),
  [[95520, "Front setbacks are to be consistent with the Building setbacks map"]], 6, "4.1.2(1)")
a("city_of_sydney", "dwelling_house", "rear_setback", None, None, nf("respect the predominant rear building line"),
  [[95521, "must respect and be sympathetic to the predominant rear building line"]], 7, "4.1.2(4)")
a("city_of_sydney", "dwelling_house", "side_setback", None, None,
  nf("heritage conservation areas relate to the established development pattern; no figure otherwise"),
  [[95520, "Within heritage conservation areas, new development is to relate to the established development pattern"]], 6, "4.1.2(2)")
a("city_of_sydney", "secondary_dwelling", "deep_soil_min", 15, "%", "general dwelling provision, lots greater than 150 sqm",
  [[95522, "For lots greater than 150sqm, the minimum amount of deep soil is to be 15% of the site area"]], 9, "4.1.3.4(1)")
a("cumberland", "dual_occupancy", "landscaping_min", 20, "%", "or a minimum of 30 m2 per dwelling",
  [[104724, "The total landscaped area for a low rise medium density development shall be a minimum of 20% of total site area"]], 35, "B2 3.4 C1")  # noqa: zone-codes -- DCP section number
a("cumberland", "secondary_dwelling", "max_site_coverage", None, None, nf("as for a single dwelling house (combined coverage)"),
  [[104721, "shall remain compliant with the site coverage controls for a single dwelling house"]], 27, "2.21 Site coverage")
a("cumberland", "secondary_dwelling", "front_setback", None, None, nf("not within the front setback area of the principal dwelling house"),
  [[104721, "Secondary dwellings are not permitted within the front setback area of the principal dwelling house"]], 26, "2.21 Setbacks")
a("georges_river", "dual_occupancy", "landscaping_min", None, None, nf("per Georges River LEP 2021 cl 6.12 table"),
  [[127299, "is to be provided in accordance with the table contained within Clause 6.12"]], 29, "6.1.3.11 Control 1")
a("georges_river", "secondary_dwelling", "landscaping_min", None, None, nf("the Georges River LEP 2021 minimum for single dwelling development"),
  [[127298, "The minimum landscaped area specified in the Georges River LEP 2021 for single dwelling development is to be provided on the site"]], 14, "6.1.2.12 Control 9")
a("georges_river", "secondary_dwelling", "front_setback", None, None, nf("behind the main building setbacks required for a single dwelling"),
  [[127298, "The secondary dwelling is to be located behind the main building setbacks required for a single dwelling"]], 14, "6.1.2.12 Control 7")
# Hornsby p6/p9 are two-column pages; each quote is a run the extractor kept intact.
a("hornsby", "dual_occupancy", "max_site_coverage", None, None, nf("by lot size, Table 3.1.1-b (65% at 200 m2 down to 30% at 1500 m2+)"),
  [[120154, "Table 3.1.1-b: Maximum Site Coverage Lot Size Maximum site coverage (% of total lot size) 200m2 to 249m2 65%"]], 6, "3.1.1(j) Table 3.1.1-b")
a("hornsby", "dual_occupancy", "front_setback", 6, "m", "9 m to designated roads; attached dual occupancy 7.6 m",
  [[120155, "Front boundary 6m to local roads and 9m to"]], 9, "3.1.2 Table 3.1.2-a")
a("hornsby", "dual_occupancy", "rear_setback", 3, "m", "8 m for a 2 storey element", [[120155, "Rear boundary Up to 1 storey = 3m"]], 9, "3.1.2 Table 3.1.2-a")
a("hornsby", "dual_occupancy", "side_setback", 0.9, "m", "1.5 m for a 2 storey element", [[120155, "Side boundary Up to 1 storey = 0.9m"]], 9, "3.1.2 Table 3.1.2-a")

# Ashfield / Blacktown / Campbelltown
a("ashfield", "dwelling_house", "rear_setback", None, None, nf("Chapter F states no rear setback for dwelling houses; DS3.8 only cross-refers"),
  [[110840, "also refer to minimum rear boundary setbacks in this DCP"]], 6, "Ch F DS3.8")
a("ashfield", "secondary_dwelling", "landscaping_min", None, None, nf("as for a dwelling house (DS8.3: 25% to 35% by lot size)"),
  [[110935, "Development does not reduce landscaped areas for the property to less than the minimum required for a dwelling house"]], 17, "Ch F DS7.1")
a("ashfield", "secondary_dwelling", "front_setback", None, None, nf("not forward of the front building line of the principal dwelling"),
  [[110930, "A secondary dwelling is not located forward of the front building line of the principal dwelling"]], 17, "Ch F DS5.1")
for dt in ("dual_occupancy", "secondary_dwelling"):
    a("blacktown", dt, "landscaping_min", None, None, nf("landscape concept plan only; no percentage"),
      [[126613, "A landscaping concept plan must be submitted with any DA"]], 42, "Part C 4.3.15")
a("blacktown", "dual_occupancy", "front_setback", 6, "m", "5.5 m to a covered car space; Stanhope Gardens 4.5 m",
  [[126612, "The building setback from the street for dual occupancy housing and secondary dwellings should be 6m and 5.5m to a covered car space"]], 39, "Part C 4.3.5")
for ct in ("rear_setback", "side_setback"):
    a("blacktown", "dual_occupancy", ct, 0.9, "m", "1.2 m for 2 storey walls / Stanhope Gardens",
      [[126642, "The walls of dual occupancy and secondary dwelling buildings are generally required to stand a minimum of 900mm from the side and rear boundaries"]], 40, "Part C 4.3.6")
a("campbelltown", "dual_occupancy", "front_setback", 5.5, "m", "garage 6.0 m; secondary street 3 m",
  [[131099, "5.5 metres from the primary street boundary for the dual occupancy"]], 24, "Part 3 3.6.3.2 i)")
a("campbelltown", "dual_occupancy", "rear_setback", 3, "m", "8 m for any part higher than 4.5 m",
  [[131104, "3 metres from the rear boundary for any part of the building that is up to 4.5 metres in height"]], 25, "Part 3 3.6.3.2 vi)")
a("campbelltown", "dual_occupancy", "side_setback", 0.9, "m", None, [[131103, "0.9 metres from any side boundary"]], 25, "Part 3 3.6.3.2 v)")
a("campbelltown", "dwelling_house", "deep_soil_min", 20, "%", None,
  [[131054, "a minimum of 20% of the total site area shall be available for deep soil planting"]], 20, "Part 3 3.6.1.2 ii)")

# Ku-ring-gai / Leichhardt / Marrickville / Northern Beaches
a("ku_ring_gai", "dual_occupancy", "landscaping_min", None, None,
  nf("formula - 50% of the Parent Lot area minus 100 sqm; built-upon area 50-55% by lot size"),
  [[126589, "The Parent Lot is to provide a minimum landscaped area equal to 50% of the Parent Lot area minus 100sqm"]], 20, "KDCP 5A.5 C1")
for ct, q in (("front_setback", "The front setback at the building line for each dual occupancy dwelling is to be a minimum of 12m"),
              ("rear_setback", "The rear setback for each dual occupancy dwelling is to be a minimum of 12m"),
              ("side_setback", "The side setbacks of the Parent Lot are to be provided in accordance with the following table")):
    a("ku_ring_gai", "dual_occupancy", ct, None, None,
      nf("depends on the layout (side-by-side, front-back, corner, battle-axe) and Parent Lot size; KDCP 5A.3"),
      [[98162, q]], 8, "KDCP 5A.3")
a("ku_ring_gai", "dwelling_house", "max_site_coverage", None, None, nf("maximum built-upon area by site area and storeys (60% to 50%); KDCP 4A.3"),
  [[98132, "are to have a maximum built-upon area (BUA) as follows"]], 12, "KDCP 4A.3 C1")
a("ku_ring_gai", "dwelling_house", "front_setback", None, None, nf("9 m low side / 12 m high side minimum, with averages for two storey; KDCP 4A.2"),
  [[98130, "Minimum and average front setbacks are to be provided"]], 7, "KDCP 4A.2 C3")
a("leichhardt", "dwelling_house", "landscaping_min", None, None, nf("soft landscape area front and rear, consistent with the Building Location Zone; no percentage"),
  [[108516, "include soft landscape area in both the front and rear of the site where consistent with the BLZ controls"]], 9, "C3.2 C9")
a("leichhardt", "dwelling_house", "rear_setback", None, None, nf("set by the Building Location Zone (adjacent main buildings)"),
  [[108510, "The BLZ is determined by having regard to only the main building on the adjacent properties"]], 6, "C3.2 C3")
a("leichhardt", "dwelling_house", "side_setback", None, None, nf("side boundary setback graph, Figure C129 (rises with wall height)"),
  [[108514, "Building setbacks shall comply with the numerical requirements set out in the side boundary setback graph"]], 8, "C3.2 C7")
a("marrickville", "dwelling_house", "front_setback", None, None, nf("consistent with adjoining development or the dominant setback in the street"),
  [[112454, "Consistent with the setback of adjoining development or the dominant setback found along the street"]], 13, "4.1.6.2 C10 i")
a("marrickville", "dwelling_house", "rear_setback", None, None, nf("maintain the predominant first storey rear building line, otherwise on merit"),
  [[112454, "Where a predominant first storey rear building line exists"]], 13, "4.1.6.2 C10 iii")
a("marrickville", "secondary_dwelling", "landscaping_min", None, None,
  nf("entire front setback, and the lesser of 4 m or the prevailing rear setback, kept pervious"),
  [[124111, "The lesser of 4 metres wide or prevailing rear setback must be kept as pervious landscaped area"]], 10, "2.18.11.2 C13")
a("marrickville", "secondary_dwelling", "front_setback", None, None, nf("behind the front building line of the principal dwelling"),
  [[112455, "Secondary dwellings must be located behind the front building line of the principal dwelling"]], 13, "4.1.6.2 C11 ii")
a("marrickville", "secondary_dwelling", "rear_setback", None, None, nf("as for dwelling houses at C10iii where there is no rear lane"),
  [[112455, "Where there is no rear lane, the rear setback controls are the same as prescribed for attached dwellings, dwelling houses and semi-attached dwellings at C10iii"]], 13, "4.1.6.2 C11 iv")
a("marrickville", "secondary_dwelling", "side_setback", 1.5, "m", "detached at the rear; attached as for dwelling houses (C10 ii)",
  [[112455, "a minimum of 1.5 metres side setback from allotment"]], 13, "4.1.6.2 C11 iii")
a("northern_beaches", "dual_occupancy", "max_site_coverage", None, None, nf("set by the DCP Site Coverage map"),
  [[129379, "shall not exceed the maximum site coverage shown on the map"]], 18, "Warringah DCP B4 C1")  # noqa: zone-codes -- DCP section number
a("northern_beaches", "dual_occupancy", "side_setback", 1, "m", "2.5 m on the other side; combined width at least 3.5 m",
  [[129983, "The minimum setback for all buildings and structures to side boundaries is 1m on one side and 2.5m on the other"]], 252, "Warringah DCP G10.1 R4")
a("northern_beaches", "dwelling_house", "side_setback", None, None, nf("set by the DCP Side Boundary Setbacks map"),
  [[129384, "is to maintain a minimum setback from side boundaries as shown on the map"]], 18, "Warringah DCP B5 C1")  # noqa: zone-codes -- DCP section number

json.dump(S, open("data/dq142_controls_2026-10-10.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(S), "findings")
