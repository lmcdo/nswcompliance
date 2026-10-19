# PRODUCER MAP: assessment page facts (and the brief/report paths that recompute them)

Basis: worktree `.claude/worktrees/page-integrity` (origin/main). Read-only static trace; nothing executed against prod. Paths are relative to the repo root. Companion to `ASSESSMENT_PAGE_INVENTORY.md` (Tables A and B).

## Summary

- **27 facts mapped; 26 DUPLICATED; 1 SINGLE.** 241 producer sites in total (240 in the duplicated facts). A "producer" is code that derives the value from raw inputs; pure display/pass-through code is not counted. A row with several sites (e.g. 24 zone-token extractors) counts each site; a site that serves two facts (e.g. services/cdc_lot_inputs.py:116 in F5 and F6) is counted once per fact, so treat the total as approximate.
- Table rows: 189 (grouped rows hold several sites). Per-fact producer counts are in the verdict lines.
- Live scope used: `frontend-nextjs/{app,lib,components,hooks}` and the deployed Python (`Dockerfile.python` copies `services/`, `scripts/generate_conveyancing_report.py`, `scripts/conveyancing_db.py`). `src/` and the rest of `scripts/` are not deployed and were not searched; offline batch builders are listed once where they feed a served table.
- Hits in `__tests__`, `node_modules`, `archive/`, `.next`, `*spike*`, `*RELEVANCE_DRAFT*`, `*.backup` are excluded.
- Surfaces: ASSESS = /assessment (call numbers refer to the inventory, e.g. A3#18); BRIEF = /reports/intelligence-brief (services/intelligence_brief.py); CONVEY = /reports/conveyancing (services/conveyancing.py + scripts/generate_conveyancing_report.py); CIBI = /canibuildit (api/canibuildit/check); GRANNY = granny-flat tool/report (services/granny_flat.py); PROV = /api/provisions/for-property; TOOLS = app/(tools)/*.

### Duplicated facts (producer sites)

- F1 Council key / slug (formerCouncil, source_council, dcp_setback_controls.lga): 28
- F2 LGA display name: 10
- F3 Zone (code and description): 40
- F4 Lot area: 10
- F5 Frontage / depth (lot width): 5
- F6 Street frontage / width at front building line: 3
- F7 Corner lot: 6
- F8 Setbacks front / side / rear (which row applies): 10
- F9 Dev-type filter of DCP controls: 19
- F10 Condition / applicability filter (zone, precinct, heritage, land facts): 11
- F11 Permitted forms / permissibility: 11
- F13 FSR: 8
- F14 Max height: 8
- F15 Min lot size: 4
- F16 Heritage flag: 12
- F17 Flood flag: 9
- F18 LMR (Low and Mid-Rise) area: 6
- F19 Instrument / LEP name: 7
- F20 Development type (page developmentType): 6
- F21 TOD / station distance: 6
- F22 Strata: 4
- F23 Bushfire prone: 4
- F24 Acid sulfate soils: 4
- F25 Aircraft noise (ANEF): 2
- F26 Road classification / street type: 2
- F27 Coordinates (lat/lng): 5

### Findings worth acting on first (each cited below)

1. Two independent LMR derivations that disagree on a layer outage: `services/housing_sepp_gates_api.py:53 lmr_gates` returns None, `services/housing_sepp_eligibility.py:170 _gate_inputs` returns False (F18). The page uses the first; the brief uses the second.
2. Lot area precedence is opposite between surfaces: polygon-first on /assessment (lib/geometry/lot-dimensions.ts), valuation-first with a 25% tolerance in BRIEF (services/intelligence_brief.py:3386), valuation-only in CONVEY (scripts/generate_conveyancing_report.py:1168) (F4).
3. DCP tab setbacks (`app/api/dcp/structured-controls/route.ts:207`) call the guarded reader without a zone, so `zone_row_applies` never runs, and show every row for dev_type=dwelling_house; the LEP-tab card (`services/constraint_arithmetic.py:157`) passes the zone and reduces to the largest minimum (F8, F10).
4. Twenty-six council-key sites produce at least four different key spaces (`source_council`, `dcp_setback_controls.lga`, `lep_land_use_table.lga`) plus title-case variants; `councilKey` and `toLgaSlug` target different tables on purpose, and disagree on `the_hills_shire`; `page.tsx` and `property-data.ts` add two unaligned copies (F1).
5. `constraints.floodProne` is a constant false (lib/nsw-planning-portal.ts:745) while `dcpFloodMap` comes from PostGIS (app/api/property/route.ts:84): two flood flags on one object (F17).
6. `lib/see/propertyContext.ts:112` reads `propertyData.nearbyRoads`, which nothing produces, so DA-intake `is_corner` is always false; Python hard-codes `is_corner=False` in three places (F7).
7. `/constraint-arithmetic/full` (ASSESS) calls `_detect_sepp_lep_overrides` without the heritage argument (services/constraint_arithmetic.py:1367) while BRIEF passes it (services/intelligence_brief.py:3985-4039): SEPP overrides are not suppressed on heritage land on the page (F12).
8. `lib/property-data.ts:359` hard-codes `Local Environmental Plan 2022` for local-provision instrument names (F19). `services/shadow_detector.py:267` selects `regulatory_provisions.former_council`, a column CLAUDE.md says does not exist (not verified against the DB).

## Producer table

Columns: producer # (per fact) | file:line function | language | inputs | surfaces that consume it | how it differs from the other producers.

### F1. Council key / slug (formerCouncil, source_council, dcp_setback_controls.lga)

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/lib/council-key.ts:33 councilKey (+COUNCIL_KEY_ALIASES :20) | TS | LGA name or slug | PROV /api/provisions/for-property (route.ts:309,464,522,640,834,1073,1307); lib/not-covered.ts:28 | Key space = regulatory_provisions.source_council. Alias map only {city_of_parramatta, sydney}; strips _municipal_council/_city_council/_council/_municipal and a city_of_ prefix (except city_of_sydney); never strips shire (the_hills_shire stays). |
| 2 | frontend-nextjs/lib/lga-slug.ts:39 toLgaSlug (+LGA_NAME_TO_SLUG :23) | TS | LGA name or slug | ASSESS DCP tab (api/dcp/structured-controls/route.ts:37); api/tod/parking-rates/route.ts:109; api/canibuildit/check/route.ts:446; lib/dcp-land-application.ts:142 | Key space = dcp_setback_controls.lga. 6-entry rename table (the_hills_shire->the_hills, city_of_ryde->ryde...); NO generic suffix/prefix stripping. Same input can give a different key than #1 (the_hills_shire: #1 keeps, #2 -> the_hills). |
| 3 | frontend-nextjs/app/assessment/page.tsx:56 normalizeLgaSlug (+LGA_NAME_TO_SLUG :46) | TS | SP.constraints.lga | ASSESS formerCouncil prop fallback page.tsx:625 (-> calls A2#4,#5); DCP enable gate page.tsx:70 | Page-local copy of #2's table (lowercase, space-keyed) with different entries (includes 'city of sydney'); drifts independently. |
| 4 | frontend-nextjs/lib/property-data.ts:325 inline slug (final fallback) | TS | constraints.lga | ASSESS constraints.formerCouncil -> A2#4,#5,#6, DCP titles, InstrumentCurrency | No alias map: 'City of Parramatta' -> city_of_parramatta (#1/#2 -> parramatta); only runs if the 4 earlier steps left formerCouncil unset. |
| 5 | frontend-nextjs/lib/precinct-service.ts:65 getPrecinctForAddress (.formerCouncil) | TS | address, lga, lat/lon (dcp_precinct_boundaries spatial match) | ASSESS via property-data.ts:243-253 | First writer of constraints.formerCouncil; casing/spelling is whatever the boundary table stores. |
| 6 | frontend-nextjs/lib/inner-west-mapping-v2.ts:51 determineFormerCouncilArea (v1 twin lib/inner-west-mapping.ts:79) | TS | address text, lga | ASSESS property-data.ts:264 (OVERRIDES precinct value); api/dcp/provisions:78; api/compliance/dcp-complete:166; api/compliance/constraints:94; api/permissibility/check:67. v1 used by property-data.ts:453 | Inner West only; suburb parsed out of the address string; returns capitalised name ('Marrickville'). v1 and v2 are two implementations. |
| 7 | frontend-nextjs/lib/precinct-service.ts:512 getFormerCouncilForPoint | TS | lat/lon vs lot_search_index.former_council | ASSESS property-data.ts:276 (OVERRIDES both above for 'inner west' LGA) | Third writer for Inner West; capitalises first letter; depends on an index populated offline (#26). |
| 8 | frontend-nextjs/lib/lga-configs/index.ts:143 detectLGAFromName (+LGA_ALIASES :34) | TS | LGA name | ASSESS property-data.ts single-LGA fallback (sets formerCouncil = config id) | Substring match both directions over an alias table that maps ashfield/leichhardt/marrickville -> 'inner_west' and suburbs (bondi...) -> waverley. |
| 9 | frontend-nextjs/lib/precinct-service.ts:576 councilSlugCandidates | TS | lga, formerCouncil | getPrecinctProvisions precinct lookup (api/precinct/provisions) | [\s-]->_ only, no alias; returns BOTH formerCouncil and LGA slugs. |
| 10 | frontend-nextjs/lib/council-config.ts:217 detectCouncil (+COUNCIL_ALIASES :199) | TS | lga, formerCouncil | council-config.ts:271 only (no other caller found by grep of app/lib/components/hooks) | Substring `includes` over 8 aliases; possibly dead, not verified. |
| 11 | frontend-nextjs/app/api/provisions/for-property/route.ts:209 COUNCIL_TO_LGA (+:491) | TS | former_council slug | PROV precinct warning (DCP tab banner) | Reverse map slug -> LGA display name, 6 entries; comment says it exists because callers omit ?lga=. |
| 12 | frontend-nextjs/components/compliance/StateLevelControls.tsx:145 | TS | lga | ASSESS SEPP tab lgaConfig | lga.toLowerCase().replace(/\s+/g,'_') then tryGetLGAConfig; hyphens not converted. |
| 13 | frontend-nextjs/app/(tools)/planning-controls/[lga-slug]/page.tsx:54 slugToDocPattern (+SLUG_TO_DOC_PATTERN :37) | TS | slug, name | TOOLS /planning-controls/[lga-slug] | Builds Title_Case document-name pattern from slug/name; a different key space again. |
| 14 | frontend-nextjs/app/api/lep/permissibility/route.ts:6 normalizeLga | TS | lga query param | ASSESS A4#23 LandUseZoningCard, A4#33 DCP SWR | Title-cases each space word AND each hyphen part ('Ku-ring-gai' -> 'Ku-Ring-Gai') for lep_zone_coverage/lep_land_use_table. |
| 15 | frontend-nextjs/app/api/capacity/calculate/route.ts:50 normalizedLGA (+:402-435 includes('marrickville'...)) | TS | body.lga, body.formerCouncil | ASSESS A2#3 (result not displayed) | Title-cases space words only ('Canterbury-Bankstown' -> 'Canterbury-bankstown'; differs from #14); setback fallback matches formerCouncil by substring. |
| 16 | frontend-nextjs/app/api/permissibility/check/route.ts:65 | TS | constraints.lga | api/permissibility/check (caller lib/ai/router.ts:641) | Third title-case variant (copy of #15's idiom). |
| 17 | scripts/generate_conveyancing_report.py:606 detect_former_council (+ZONE_EPI_TO_LGA_SLUG :257, DCP_ONBOARDED_SLUGS :284, SUBURB_TO_FORMER_COUNCIL :298, _slug_from_epi :582) | PY | address, zone_epi (LEP name) | BRIEF intelligence_brief.py:3826; CONVEY conveyancing.py:437,628 | Derived from the LEP (EPI) name, not the LGA name; returns None unless slug is in a hand-maintained onboarded set; Inner West by substring of address. |
| 18 | services/lga_lookup.py:67 lookup_lga (+_LGA_NAME_TO_SLUG :23, _IW_SUBURB_TO_FORMER :42, _normalise_slug :62) | PY | lat/lng (spatial_overlays.lga_name), address | BRIEF/CONVEY validators; granny_flat.py:2107; shadow_detector.py:645; solar_yield.py:700 | Spatial; 11-entry table; fallback [\s-]->_ with no city_of_/council stripping. |
| 19 | services/intelligence_brief.py:1682 _validate_former_council_postgis | PY | text slug, lat/lng, address | BRIEF | Returns (slug, advisory); overrides an Inner West text match when PostGIS says otherwise. |
| 20 | services/conveyancing.py:101 _validate_former_council_postgis | PY | text slug, lat/lng, address, zone_epi | CONVEY | Copy of #19 with a different signature/return (slug only, no advisory). |
| 21 | services/intelligence_brief.py:1412 _norm_lga | PY | council or LGA name | BRIEF _permitted_engine_forms :1436, :2054-2074; granny_flat.py:190-210 | Drops council/city/shire/municipal/of/the tokens -> 'sydney', 'strathfield'; a third key space (lep_land_use_table.lga). |
| 22 | scripts/generate_conveyancing_report.py:1676 _normalise_council / :1860 _council_from_zone_epi | PY | LGA name or EPI name | CONVEY/BRIEF nearby-DA lookups (conveyancing.py:433,627) | Produces 'Waverley Council'-style names from a hand map. |
| 23 | services/dcp_controls_api.py:51 | PY | ?lga= | every /pipeline/dcp-controls caller (structured-controls, capacity, canibuildit, parking-rates, constraint-arithmetic) | strip().lower() only: relies on every TS caller having produced the right slug (#2 vs #1 vs page.tsx). |
| 24 | services/intelligence_brief.py:1392 _bare_lga_from_epi; services/upzoning_check.py:186 | PY | zone_epi | BRIEF; upzoning-check tool | Two copies of EPI -> bare LGA name regex. |
| 25 (x3) | services/threat_radar.py:174 _normalise_council; services/pre_da_history.py:235; services/shadow_detector.py:199 | PY | council/LGA name | threat-radar, pre-DA history, shadow tools | Each tool has its own council vocabulary/normaliser. |
| 26 | scripts/build_lot_search_index.py:84 lga_name_to_dcp_slugs (+LGA_TO_DCP_SLUGS :69) | PY (offline batch, NOT in Docker image) | LGA name | writes lot_search_index read by #7 and /api/lot-search | Batch producer; same concept, fourth mapping table. |

**Verdict: DUPLICATED (28 producer sites in 26 code locations).**

### F2. LGA display name

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 (x4) | frontend-nextjs/lib/nsw-planning-portal.ts:761,783,818,824 constraints.lga = result['LGA Name'] | TS | 4 different layer results | ASSESS header pill, left panel, PropertyDetails, LepControls, StateLevelControls guard (Table B) | Four writers in one function: last layer processed wins (no precedence rule). |
| 2 | frontend-nextjs/app/api/property/profile/route.ts:55 | TS | zoning layer only | ASSESS A1#2 (lga not displayed) | Zoning layer only, can differ from #1. |
| 3 | frontend-nextjs/app/api/canibuildit/check/route.ts:247 | TS | zoneResult.LGA_NAME ?? Council | CIBI | Reads different attribute names (LGA_NAME/Council) from #1 ('LGA Name'). |
| 4 | services/lga_lookup.py:110 | PY | spatial_overlays height layer lga_name | BRIEF/CONVEY/granny/shadow/solar | PostGIS name vocabulary ('Canterbury-Bankstown'), not portal attribute. |
| 5 (x2) | scripts/generate_conveyancing_report.py:1575,1583 | PY | spatial_overlays lga_name | CONVEY overlay coverage | Two more SELECTs of the same column. |
| 6 | services/intelligence_brief.py:1392 _bare_lga_from_epi (also F1 #24) | PY | zone_epi | BRIEF lga_name for land-use panel | Derived from LEP title string, not from an LGA field. |

**Verdict: DUPLICATED (10 producer sites in 6 code locations).**

### F3. Zone (code and description)

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/lib/nsw-planning-portal.ts:775,779 zone=result['Zone'], zoneDescription=result['title'] | TS | Land Zoning layer | ASSESS badge, LandUseZoningCard, all zone-keyed calls | Primary source. |
| 2 | frontend-nextjs/lib/nsw-planning-portal.ts:609 zoneDescription = attrs.zone_desc | TS | SIX Valuation | data.zoneDescription (unused on page) | Different source/vocabulary from #1. |
| 3 | frontend-nextjs/app/api/property/profile/route.ts:53-54 | TS | zoning layer 'title' else valuation | ASSESS A1#2 (zoneDescription not displayed) | Fallback chain to the valuation string. |
| 4 | scripts/generate_conveyancing_report.py:1281 parse_controls out['zone'] | PY | layerintersect | BRIEF/CONVEY (controls['zone']) | find('Zone') else find('title','Value'): fallback to title text. |
| 5 | services/bushfire_prescreen.py:325 _query_zone_overlay | PY | spatial_overlays layer_type='zone' | bushfire prescreen | PostGIS, not portal. |
| 6 | frontend-nextjs/app/api/canibuildit/check/route.ts:244-245 | TS | zoneResult.Zone | CIBI | Own parse + split(' ')[0].toUpperCase(). |
| 7 (x24) | TS zone-code token extractors: components/compliance/StateLevelControls.tsx:250,434,505; ProvisionsByTocStructure.tsx:434; app/api/housing-sepp/eligibility/route.ts:150; lib/regulatory-constants.ts:305,327,340,348,374,402; lib/lep-land-condition.ts:71; app/api/cdc/preliminary-check/route.ts:42; components/compliance/ADGSummaryCard.tsx:126; lib/nsw-planning-portal.ts:979; lib/see/section-aggregation.ts:121; lib/see/seeBuilders.ts:81,258; lib/pdf/see-helpers.ts:73; components/pdf/ContextSection.tsx:50,91; app/api/og/granny-flat/route.tsx:46; app/tools/zoning-check/page.tsx:60; app/tools/subdivision-check/page.tsx:124 | TS | zone string | ASSESS: A3#15/#16/#22 (exempt-complying zone), A4#33/A2#4 (DCP zone), Housing card; tools | At least 4 tokenisers: strip non-alnum+uppercase (StateLevelControls, regulatory-constants), raw split (ProvisionsByTocStructure :434, no uppercase), regex ^[A-Z]+[0-9]* on the description (cdc/preliminary-check), split on [\s:] (lep-land-condition). HousingSEPPEligibilityCard displays the raw SP zone (Table B). |
| 8 (x10) | PY zone-prefix extractors: scripts/conveyancing_db.py:854,1199; scripts/generate_conveyancing_report.py:669,4675,4765,5228; services/cdc_screen.py:479; services/housing_sepp_eligibility.py:85 normalize_zone; services/intelligence_brief.py:1172 _zone_prefix; services/compound_constraints.py:408 _zone_prefix | PY | zone string | BRIEF/CONVEY/CDC screen/housing eligibility | Copies of split()[0].upper(); two named _zone_prefix are identical functions. |

**Verdict: DUPLICATED (40 producer sites in 8 code locations).**

### F4. Lot area

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/lib/geometry/lot-dimensions.ts:86,217 calculatePolygonArea (callers property-data.ts:139, api/property/[address]/route.ts:208, api/satellite/granny-flat/route.ts:326) | TS | PP lot polygon (EPSG:3857, scale-corrected) | ASSESS lotDimensions.area (page.tsx:274, LepControls, Housing card, ...) | Polygon-first, rounded 2dp. |
| 2 | frontend-nextjs/app/api/property/profile/route.ts:70 | TS | same fn, own call site | ASSESS A1#2 lotArea (unused) | Rounded integer in the response. |
| 3 | frontend-nextjs/lib/nsw-planning-portal.ts:609 propertyArea = attrs.prop_area | TS | SIX Valuation string | ASSESS page.tsx:276 fallback | Valuation string ('Unknown' when absent); a different parcel concept. |
| 4 | frontend-nextjs/hooks/usePropertyAssessment.ts:113-115 | TS | area ?? parseFloat(propertyArea) | ASSESS A2#3 lotSize, A1 capacity | Fallback chain #1 then #3. |
| 5 | frontend-nextjs/components/compliance/StateLevelControls.tsx:483-486 | TS | area ?? parse(propertyArea) ?? geometry.area | ASSESS A3#18 lotSize, Housing card, ExemptComplying | Third fallback chain adds geometry.area. |
| 6 | frontend-nextjs/app/api/canibuildit/check/route.ts:191-204 | TS | PP lot rings | CIBI lot_area | Own inline shoelace x cos^2(lat); not lot-dimensions.ts. |
| 7 | services/lot_dimensions.py:173,232 _shoelace_area (calculate_lot_dimensions :134) | PY | PP lot rings | BRIEF (intelligence_brief.py:2714,3439), cdc_lot_inputs | Python twin of #1. |
| 8 | services/granny_flat.py:903 _compute_lot_area_m2 | PY | PP lot rings | GRANNY (granny_flat.py:1511,1797) | Third shoelace implementation. |
| 9 | services/intelligence_brief.py:3386 _reconcile_lot_area, applied :3425,:3743 | PY | VG valuation area vs polygon area | BRIEF lot_area_m2 for the whole brief | VALUATION-first; uses polygon only if the two differ by >25%. Opposite precedence to #1/#4. |
| 10 | scripts/generate_conveyancing_report.py:1168-1215 get_valuation (used conveyancing.py:385,417,502) | PY | VG valuation only | CONVEY lot_area_m2 | Valuation only, no polygon cross-check at all. |

**Verdict: DUPLICATED (10 producer sites in 10 code locations).**

### F5. Frontage / depth (lot width)

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/lib/geometry/lot-dimensions.ts:142 frontageDepthFromRect | TS | lot ring | ASSESS PropertyDetails 'Lot width (shorter side)', A4#24 frontage/depth | Shorter side of min-area bounding rectangle (null if fill < 0.6). |
| 2 | frontend-nextjs/hooks/usePropertyAssessment.ts:120 | TS | sqrt(lotArea) | ASSESS A2#3 body.frontage | Pure estimate sent as if measured. |
| 3 | services/lot_dimensions.py:181,243 _frontage_depth_obb | PY | lot ring | BRIEF | Python twin of #1. |
| 4 | services/constraint_arithmetic.py:376-403 _estimate_lot_dimensions | PY | area only: sqrt(area/2.5) | BRIEF/ASSESS A4#24 when frontage absent | Third estimate with a different ratio (2.5). |
| 5 | services/cdc_lot_inputs.py:116 rectangle_width_range | PY | lot geometry | CDC screen | Width range via a rectangle method. |

**Verdict: DUPLICATED (5 producer sites in 5 code locations).**

### F6. Street frontage / width at front building line

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/lib/geometry/street-frontage.ts:163 measureStreetFrontage (+widthRange :226) | TS | lot ring + road corridors | ASSESS cornerLot.streetFrontage -> PropertyDetails, Housing card (A3#18 lotWidthMin/Max), Pattern Book | Measured from road edge. |
| 2 | services/street_frontage.py:144 measure_street_frontage (+width_range :222, street_frontage_for_geometry :261) | PY | lot ring + road shapes | BRIEF intelligence_brief.py:3997 | Python twin of #1 (two implementations of the same algorithm). |
| 3 | services/cdc_lot_inputs.py:116 rectangle_width_range | PY | lot geometry | CDC screen | Rectangle-based, not road-based. |

**Verdict: DUPLICATED (3 producer sites in 3 code locations).**

### F7. Corner lot

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/lib/geometry/corner-lot-detection.ts:150-153 isCornerLot: roadCount >= 2 | TS | adjacent named roads | ASSESS PropertyDetails corner/not-corner (property-data.ts:140; api/property/[address]:217) | The only real detector. |
| 2 | frontend-nextjs/lib/see/propertyContext.ts:112-113 nearbyRoads.length >= 2 | TS | propertyData.nearbyRoads | ASSESS DA-mode intake is_corner (ProvisionsByTocStructure) | nearbyRoads has NO producer anywhere in app/lib/components/hooks (grep), so this is always false. |
| 3 | frontend-nextjs/components/property-details-comprehensive.tsx:249 | TS | literal text | ASSESS left panel when #1 says corner | Hard-coded 'Secondary street setback: 3m (vs 6m rear for non-corner)'; a setback value, not derived (see F8). |
| 4 (x3) | services/lot_dimensions.py:199; services/constraint_arithmetic.py:1285,1463 (is_corner=False) | PY | none | BRIEF/ASSESS constraint arithmetic | Python never detects corner lots: is_corner hard-coded False. |

**Verdict: DUPLICATED (6 producer sites in 4 code locations).**

### F8. Setbacks front / side / rear (which row applies)

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | scripts/conveyancing_db.py:641 fetch_dcp_setbacks (+zone_row_applies :505, precinct_specific skip :876) | PY | lga slug, zone, dcp_setback_controls rows | ALL setback surfaces via /pipeline/dcp-controls (services/dcp_controls_api.py:70), conveyancing.py:293, intelligence_brief.py:1938, constraint_arithmetic.py:1354 | The guarded row set: is_current, not needs_review, no precinct_specific rows, zone filter ONLY if a zone is passed; ORDER dwelling_house first, front/side/rear, value_min NULLS LAST. |
| 2 | services/constraint_arithmetic.py:157 _get_dcp_value (+_matching_controls :203, _resolve_lot_band :137) | PY | controls, dev_type, lot area | ASSESS A4#24 'DCP Setbacks Applied' (LEP tab), BRIEF | Reduces to ONE number: LARGEST value_min among matches (smallest value_max for caps) unless exactly one lot-size band matches; dev_type exact else dwelling_house. |
| 3 | frontend-nextjs/app/api/dcp/structured-controls/route.ts:229-309 | TS | fetchDcpControls(slug) (:207, no zone arg) | ASSESS DCP tab 'Setbacks' category (A2#5); components/tools/DcpSnapshotCard.tsx:77 | Shows EVERY row of one dev_type (default dwelling_house, never the page dev type), no zone filter, no max/min reduction, ranges shown as value_min-value_max. |
| 4 | frontend-nextjs/app/api/capacity/calculate/route.ts:121-127,220-451 getSetbacks | TS | zone passed; precinct SQL dcp_precinct_requirements :268; per-council literals :402-451 | ASSESS A2#3 (setbacks fetched, never displayed) | Third selection path (precinct-specific -> general -> hard-coded per-council text for marrickville/ashfield/leichhardt/sydney). |
| 5 | frontend-nextjs/components/property-details-comprehensive.tsx:249 | TS | literal | ASSESS left panel (corner lot) | Hard-coded '3m (vs 6m rear)'. |
| 6 | services/intelligence_brief.py:2749 _build_dcp_controls | PY | fetch_dcp_setbacks dict | BRIEF DCP card | Second copy of constraint_arithmetic._dcp_controls_from_setback_rows (:294). |
| 7 | services/granny_flat.py:310 _fetch_sd_setbacks (own SQL :325) | PY | lga slug | GRANNY | Own SELECT on dcp_setback_controls for secondary_dwelling; bypasses fetch_dcp_setbacks guards. |
| 8 | frontend-nextjs/app/api/canibuildit/check/route.ts:448-460 | TS | fetchDcpControls(normLga) | CIBI dcpSetbacks | Filters dev_type === 'secondary_dwelling'; no zone passed. |
| 9 | frontend-nextjs/app/(tools)/planning-controls/[lga-slug]/page.tsx:229 | TS | own SQL on dcp_setback_controls | TOOLS planning-controls page | Direct SQL, not the guarded path. |
| 10 | frontend-nextjs/app/api/compliance/dcp-complete/route.ts:364,512,1200 and app/api/compliance/precinct-requirements/route.ts:131 | TS | dcp_precinct_requirements SQL | live API routes; not called by /assessment (caller ComplianceDashboard is unmounted) | Precinct-requirement readers with their own selection. |

**Verdict: DUPLICATED (10 producer sites in 10 code locations).**

### F9. Dev-type filter of DCP controls

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/app/api/dcp/structured-controls/route.ts:229 | TS | dev_type query (default dwelling_house) | ASSESS DCP tab | Exact match, no fallback; DcpStructuredControls.tsx:167 never passes the page dev type. |
| 2 | services/constraint_arithmetic.py:203-217 _matching_controls | PY | controls, dev_type | ASSESS A4#24 (page dev type), BRIEF | Exact dev_type, falls back to dwelling_house ROWS when no exact match. |
| 3 | frontend-nextjs/app/api/capacity/calculate/route.ts:124 | TS | developmentType (not sent by hook) | ASSESS A2#3 | dev_type === X \|\| 'universal_residential'. |
| 4 | frontend-nextjs/app/api/tod/parking-rates/route.ts:177-191 | TS | developmentType | TOD parking | Same idiom as #3 plus exact-first sort. |
| 5 | frontend-nextjs/app/api/canibuildit/check/route.ts:450 | TS | - | CIBI | Hard-coded 'secondary_dwelling'. |
| 6 | scripts/conveyancing_db.py:934-936 | PY | applicability / dev_type | setbacks vs sd_setbacks split in every fetch_dcp_setbacks consumer | Splits secondary-dwelling rows from dwelling-house rows in the output. |
| 7 | services/granny_flat.py:332 | PY | SQL dev_type = 'secondary_dwelling' | GRANNY | Own filter. |
| 8 (x11) | frontend-nextjs/components/compliance/ProvisionsByTocStructure.tsx:595,674-676,725,820,1002,1101,1179,1273,1376,1453 (v2_applicable_dev_types) | TS | DA-mode devType (:214) vs provision tags | ASSESS DCP tab provisions list, TOC counts | Client-side filters; driven by DA-mode dev type, NOT the page developmentType; the server route excludes dev types on purpose (lib/dcp-provisions-query.ts:56). |
| 9 | frontend-nextjs/lib/dev-type-filter.ts:441 filterRequirementsByDevType | TS | requirements, dev type | api/compliance/dcp-complete only (ComplianceDashboard unmounted) | Another filter implementation, not on /assessment. |

**Verdict: DUPLICATED (19 producer sites in 9 code locations).**

### F10. Condition / applicability filter (zone, precinct, heritage, land facts)

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | scripts/conveyancing_db.py:505 zone_row_applies (+_ZONE_CODE :495, _EXCLUSION_WORDING :497) | PY | applicability, condition text, zones_include/exclude, zone | ASSESS A4#24, BRIEF, CONVEY | Parses zone codes from free-text condition; NOT run for the DCP tab (structured-controls passes no zone). |
| 2 | scripts/conveyancing_db.py:876 | PY | applicability == 'precinct_specific' | all fetch_dcp_setbacks consumers | Drops every precinct-specific row council-wide. |
| 3 | services/constraint_arithmetic.py:110-155 _lot_band_match/_resolve_lot_band | PY | condition text, lot area | ASSESS A4#24, BRIEF | Parses 'lot less than X m2' bands; other conditions ignored. |
| 4 | services/constraint_arithmetic.py:226 _dcp_height_metres | PY | dev_type rows | ASSESS A4#24, BRIEF | Prefers rows with empty condition, then smallest cap. |
| 5 | frontend-nextjs/lib/provision-sql-filters.ts:65 ZONE_APPLIES_SQL | TS | v2_applicable_zones vs zone | PROV (route.ts:1111) | Array membership on tags, different logic from #1. |
| 6 | frontend-nextjs/lib/provision-sql-filters.ts:30,46 NOT_HERITAGE_SQL / hcaTagSql | TS | heritage, hca | PROV (route.ts:825,828,1094,1099) | Heritage/HCA predicate in SQL. |
| 7 | frontend-nextjs/app/api/provisions/for-property/route.ts:1120-1123 | TS | flood/bushfire/acid/riparian flags from the page | PROV | Condition tags matched by caller-supplied booleans (lib/dcp-provisions-query.ts:32). |
| 8 | frontend-nextjs/lib/lep-land-condition.ts:98 decideLandCondition / :119 applyLandConditions | TS | land facts from layers (:54) | PROV (route.ts:419) | Third 'does this apply' evaluator. |
| 9 | frontend-nextjs/lib/dcp-land-application.ts:138 decideLandApplication | TS | land application instruments | PROV (route.ts:319) | Withholds a whole DCP when the lot is outside the instrument. |
| 10 | frontend-nextjs/lib/see/intake.ts:432-433 | TS | constraints.floodProne | ASSESS DCP tab greying (DcpProvisionList:94) | Uses floodProne (constant false), not dcpFloodMap. |
| 11 | frontend-nextjs/lib/environmental-relevance-filter.ts:40 assessControlRelevance | TS | control, context | ComplianceDashboard only (unmounted) | Not on /assessment. |

**Verdict: DUPLICATED (11 producer sites in 11 code locations).**

### F11. Permitted forms / permissibility

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/app/api/lep/permissibility/route.ts:36-50 | TS | zone, normalised LGA (F1 #14); lep_zone_coverage gate | ASSESS A4#23 LandUseZoningCard, A4#33 | Raw land-use table rows. |
| 2 | frontend-nextjs/app/api/permissibility/check/route.ts:77-161 | TS | own lep_land_use_table queries, title-cased LGA | live route (caller lib/ai/router.ts:641) | Second reader of the same table. |
| 3 | services/intelligence_brief.py:1428 _permitted_engine_forms (+_ceiling_within_tier :1458, _realistic_forms :1482, _ZONE_TIER_CEILING :1383) | PY | zone, _norm_lga name | BRIEF capacity floor/ceiling form | Zone-tier ceiling + land-use table; fail-safe to dwelling_house. |
| 4 | services/granny_flat.py:178 _dwelling_house_permissible | PY | zone, lga | GRANNY | Own lep_land_use_table query. |
| 5 | services/housing_sepp_eligibility.py:272 evaluate_eligibility | PY | zone, lot area/width, heritage, gates | BRIEF SEPP card/ceiling; services/upzoning_check.py:191 | Eligible Housing-SEPP forms. |
| 6 | frontend-nextjs/app/api/housing-sepp/eligibility/route.ts:117-520 | TS | zoneCode, lotSize, widths, isLMRArea, lepHeight/Fsr; housing_sepp_standards :192 | ASSESS A3#18 Housing card | TS re-implementation of #5 (own zone/LMR/lot/width tests). |
| 7 (x2) | frontend-nextjs/lib/regulatory-constants.ts:373 isLMREligibleZone, :401 permitsApartmentDevelopment | TS | zone, lmr | ASSESS show/hide of LMR and ADG sections (StateLevelControls:532,545) | Hard-coded zone lists. |
| 8 | frontend-nextjs/components/compliance/StateLevelControls.tsx:253 | TS | NSW_PLANNING_CONSTANTS.ZONES.RESIDENTIAL | ASSESS A3#9 housing_2021 SEPP filter | Zone list again. |
| 9 | frontend-nextjs/app/api/canibuildit/check/route.ts:402 | TS | inline housing_sepp_standards | CIBI | Own eligibility SQL. |
| 10 | services/secondary_dwelling_paths.py:198,250,330 | PY | zone, lot area, frontage | GRANNY/CIBI paths | Own standards SQL and CDC/DA path logic. |

**Verdict: DUPLICATED (11 producer sites in 10 code locations).**

### F12. Dwelling yield (floor/ceiling)

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | services/constraint_arithmetic.py:1011-1037 _dwellings_for (+_dwellings_for_form :417) | PY | envelope GFA, dev_type (floor), ceiling_dev_type | ASSESS A4#24 (/constraint-arithmetic/full :1447: no ceiling form, no heritage suppression - _detect_sepp_lep_overrides called at :1367 without is_heritage); BRIEF intelligence_brief.py:4043-4060 (ceiling, heritage, LMR uplift); batch lot_search_index ca_* | One formula; three call contexts feed it different inputs (see F11/F18/F20). |

**Verdict: SINGLE** (1 producer of the formula). Formula is SINGLE. Inputs diverge: ASSESS passes page dev type and omits ceiling/excluded forms/heritage; BRIEF passes floor+ceiling from _realistic_forms and heritage.

### F13. FSR

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/lib/nsw-planning-portal.ts:757-758 | TS | layer 'Floor Space Ratio' | ASSESS LepControls, A4#24 maxFsr | Primary. |
| 2 | frontend-nextjs/app/api/property/route.ts:149-151 | TS | PostGIS spatial_overlays fsr | ASSESS constraints.maxFsr fallback | Fallback source. |
| 3 | frontend-nextjs/app/api/property/profile/route.ts:57 | TS | layer value (string) | A1#2 (unused) | Not parsed to number. |
| 4 | frontend-nextjs/components/compliance/StateLevelControls.tsx:522-524 lepFsr | TS | planningLayers['Floor Space Ratio Map'] | ASSESS A3#18 Housing card | Re-reads the same layer (Table B). |
| 5 | frontend-nextjs/app/api/canibuildit/check/route.ts:262 | TS | FSR / MAX_FSR keys | CIBI | Different attribute names. |
| 6 | frontend-nextjs/app/api/capacity/calculate/route.ts:100-103 | TS | regex on lep_development_type_clauses text | ASSESS A2#3 (not displayed) | Parsed from clause prose. |
| 7 | frontend-nextjs/app/api/property/[address]/route.ts:175,271-275 fsr_limit | TS | planningControls | live route | Another parse. |
| 8 | scripts/generate_conveyancing_report.py:1291-1293 (+services/constraint_arithmetic.py:476 _parse_numeric) | PY | layerintersect | BRIEF/CONVEY; constraint arithmetic | Keeps string; keys 'Floor Space Ratio','FSR','title'. |

**Verdict: DUPLICATED (8 producer sites in 8 code locations).**

### F14. Max height

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/lib/nsw-planning-portal.ts:767-768 | TS | layer 'Maximum Building Height' | ASSESS LepControls, A4#24 | Primary. |
| 2 | frontend-nextjs/components/compliance/StateLevelControls.tsx:511-514 lepHeight | TS | planningLayers keys 'Maximum Building Height'\|'MAX_B_H'\|'B_H'\|'HEIGHT' | ASSESS Housing card | Different key fallbacks. |
| 3 | frontend-nextjs/app/api/property/profile/route.ts:56 | TS | layer | A1#2 (unused) |  |
| 4 | frontend-nextjs/app/api/canibuildit/check/route.ts:258 | TS | MAX_B_H\|B_H\|HEIGHT | CIBI | Different keys; appends 'm' string. |
| 5 | frontend-nextjs/app/api/capacity/calculate/route.ts:93-97 | TS | regex on clause text | A2#3 | Parsed from prose. |
| 6 | frontend-nextjs/app/api/property/[address]/route.ts:270 | TS | planningControls | live route |  |
| 7 | scripts/generate_conveyancing_report.py:1287-1289 | PY | layerintersect | BRIEF/CONVEY | Keys 'Maximum Building Height','Height','title'. |
| 8 | services/constraint_arithmetic.py:226 _dcp_height_metres | PY | DCP rows (storeys or m) | ASSESS A4#24, BRIEF | DCP height is a different control from LEP height but is combined with it in the envelope. |

**Verdict: DUPLICATED (8 producer sites in 8 code locations).**

### F15. Min lot size

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/lib/nsw-planning-portal.ts:788 | TS | layer 'Lot Size Map' -> 'Lot Size' | ASSESS LepControls tile | Primary. |
| 2 | frontend-nextjs/app/api/property/route.ts:160-162 | TS | PostGIS lot_size fallback | ASSESS | Fallback. |
| 3 | frontend-nextjs/components/compliance/StateLevelControls.tsx:560 | TS | planningLayers 'Minimum Lot Size' \|\| 'Lot Size' | not rendered | Computed, not shown. |
| 4 | scripts/generate_conveyancing_report.py:1296 (+fallbacks :5860; conveyancing.py:408,608; intelligence_brief.py:3943) | PY | layerintersect then spatial_overlays | BRIEF/CONVEY | Three more copies of the overlay fallback. |

**Verdict: DUPLICATED (4 producer sites in 4 code locations).**

### F16. Heritage flag

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/lib/nsw-planning-portal.ts:791-792 (+lib/property-data.ts:211-219) | TS | Heritage Map layer presence | ASSESS Heritage Yes/No, LepControls, CDC screener, Pattern Book, DCP hca param | Two flags (constraints.heritage and heritage.isHeritage) from one source. |
| 2 | frontend-nextjs/lib/see/heritageType.ts:14 classifyHeritageType | TS | heritageType string | ASSESS page.tsx:102 -> hca param (A2#4) | Decides HCA vs item from text. |
| 3 | frontend-nextjs/app/api/property/profile/route.ts:58 | TS | layer results length | A1#2 (unused) |  |
| 4 | frontend-nextjs/app/api/canibuildit/check/route.ts:254 | TS | any layer whose name contains 'heritage' | CIBI | Name substring match. |
| 5 | frontend-nextjs/app/api/satellite/granny-flat/route.ts:534 | TS | property.heritage_status / heritage_overlays | GRANNY | Reads a different shape. |
| 6 | scripts/conveyancing_db.py:1079 fetch_heritage_postgis (+scripts/generate_conveyancing_report.py:1308,1377; merged conveyancing.py:881-884) | PY | PostGIS + portal items | CONVEY/BRIEF | Portal items UNION PostGIS. |
| 7 | services/intelligence_brief.py:2952 _is_heritage_land | PY | controls.heritage_items or has_heritage | BRIEF LMR/override gating |  |
| 8 | services/upzoning_check.py:168 | PY | heritage_items or heritage_hca | upzoning tool |  |
| 9 | services/granny_flat.py:871 | PY | spatial_overlays | GRANNY |  |
| 10 | services/solar_yield.py:530 | PY | spatial_overlays | solar |  |
| 11 | services/pre_da_history.py:735 | PY | spatial_overlays | pre-DA history |  |
| 12 | services/bushfire_prescreen.py:298 | PY | spatial_overlays | bushfire prescreen |  |

**Verdict: DUPLICATED (12 producer sites in 12 code locations).**

### F17. Flood flag

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/app/api/property/route.ts:84,128 dcpFloodMap | TS | spatial_overlays layer_type='flood' | ASSESS LepControls 'Flood Mapping', DCP flood= param | The only flood signal the page uses for display. |
| 2 | frontend-nextjs/lib/nsw-planning-portal.ts:745 floodProne: false | TS | constant | ASSESS intake.ts:432 (flood topic greyed for every lot), Pattern Book exclusion | Never set true. |
| 3 | frontend-nextjs/app/api/property/profile/route.ts:86 | TS | 'Flood Planning Area' layer | A1#2 (unused) | Third definition. |
| 4 | frontend-nextjs/app/api/canibuildit/check/route.ts:298,349 | TS | spatial_overlays + LGA coverage | CIBI | Three-state with LGA coverage check. |
| 5 | frontend-nextjs/lib/see/propertyContext.ts:167 | TS | !!envC.floodProne | DA intake | Coerces undefined to false. |
| 6 | services/flood_truth.py:477 _query_epi_overlay (+SES :949) | PY | spatial_overlays | BRIEF flood_epi, flood product |  |
| 7 | services/cdc_screen.py:485-503 _overlay_state('flood') | PY | overlays + coverage | CDC screen | Three-state. |
| 8 | services/bushfire_prescreen.py:271 | PY | spatial_overlays | bushfire prescreen |  |
| 9 | scripts/generate_conveyancing_report.py:1437 get_unique_overlays (flood rows :4944-4995) | PY | spatial_overlays | CONVEY |  |

**Verdict: DUPLICATED (9 producer sites in 9 code locations).**

### F18. LMR (Low and Mid-Rise) area

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | services/housing_sepp_gates_api.py:53 lmr_gates | PY | lat/lng; layers 776, TOD, town centres | ASSESS A3#8 -> isLMRArea (hooks/useLmrGates.ts:37) | Tri-state: any failed query -> None. |
| 2 | services/housing_sepp_eligibility.py:170 _gate_inputs | PY | same layers | BRIEF (evaluate_eligibility), upzoning_check.py:161 | Same formula, two-state: any failed query -> False ('not in area'). Different answer to #1 on a layer outage. |
| 3 | frontend-nextjs/lib/nsw-planning-portal.ts:1298,1366 lowMidRiseExcluded | TS | layer 776 | unused by page (Table B) | Exclusion only. |
| 4 | frontend-nextjs/app/api/housing-sepp/eligibility/route.ts:259-260 | TS | isLMRArea from client | ASSESS Housing card eligibility | Re-interprets null as unknown. |
| 5 | services/intelligence_brief.py:1588 _lmr_uplift_form | PY | eligibility results | BRIEF ceiling_from_lmr | Derived 'LMR uplift' form. |
| 6 | frontend-nextjs/lib/regulatory-constants.ts:401 permitsApartmentDevelopment | TS | zone, lmr | ASSESS ADG section show/hide | R1-R3 apartments only if lmr === true. |

**Verdict: DUPLICATED (6 producer sites in 6 code locations).**

### F19. Instrument / LEP name

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/components/compliance/LepControls.tsx:54-55 | TS | zoneResult['EPI Name'] else '{lga} Local Environmental Plan' | ASSESS LEP tab badge and currency line | Synthesises a name without a year when EPI Name is absent. |
| 2 | frontend-nextjs/lib/property-data.ts:359 | TS | `${lga} Local Environmental Plan 2022` | ASSESS constraints.localProvisions[].epiName -> LocalProvisionsCard | Hard-codes the year 2022 (LepControls.tsx:52 says never fabricate a year). |
| 3 | frontend-nextjs/app/api/canibuildit/check/route.ts:248 | TS | EPI_NAME ?? LEP_NAME | CIBI | Different attribute names. |
| 4 | frontend-nextjs/app/api/instrument-currency/route.ts:42 instrument_label | TS | DB instrument_registry | ASSESS InstrumentCurrency list | DB label vocabulary. |
| 5 | scripts/generate_conveyancing_report.py:1283 zone_epi | PY | layerintersect 'EPI Name' | BRIEF/CONVEY |  |
| 6 | services/shadow_detector.py:199 | PY | lga_name.title()+' Local Environmental Plan' | shadow tool | Synthesised, no year. |
| 7 | services/intelligence_brief.py:1392 _bare_lga_from_epi | PY | zone_epi | BRIEF land-use panel | Reverse direction (name from title). |

**Verdict: DUPLICATED (7 producer sites in 7 code locations).**

### F20. Development type (page developmentType)

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/lib/requirement-prioritization.ts:103 detectDevTypeFromZone | TS | constraints.zone | ASSESS usePropertyAssessment.ts:98 -> A3#9,#13, A4#24 dev_type | R4->residential_flat_building, R3->multi_dwelling_housing, other R->dwelling_house, B/E/IN->commercial, MU->shop_top_housing. |
| 2 | services/intelligence_brief.py:1383 _ZONE_TIER_CEILING / :1482 _realistic_forms | PY | zone + permitted forms | BRIEF floor/ceiling | Different tiering and uses the land-use table. |
| 3 | frontend-nextjs/components/compliance/DcpStructuredControls.tsx:167 | TS | default 'dwelling_house' | ASSESS A2#5 | Never wired to #1. |
| 4 | frontend-nextjs/components/compliance/ProvisionsByTocStructure.tsx:214,305 | TS | DA-mode planner choice | ASSESS DCP tab filters | Independent of #1. |
| 5 | scripts/generate_conveyancing_report.py:2730 | PY | constant dwelling_house floor | CONVEY | Hard-coded. |
| 6 | services/constraint_arithmetic.py:1431 (request default) | PY | default 'dwelling_house' | ASSESS/BRIEF | Default when caller omits. |

**Verdict: DUPLICATED (6 producer sites in 6 code locations).**

### F21. TOD / station distance

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/lib/nsw-planning-portal.ts:862 todPrecinct.stationDistance (and :1280 Math.sqrt distance) | TS | TOD layer attribute / projected dx,dy | ASSESS left TOD card, Housing card | Layer attribute or euclidean metres. |
| 2 | frontend-nextjs/app/api/tod/transport-autocomplete/route.ts:8-80 | TS | hard-coded TRANSPORT_STATIONS + haversine | ASSESS TOD section, NearbyTransportCard | Hard-coded station list. |
| 3 | frontend-nextjs/components/compliance/StateLevelControls.tsx:501 | TS | todPrecinct.stationDistance \|\| first heavy-rail stop distance | ASSESS Housing card 'To station' | Chooses between two sources. |
| 4 | services/portal_constraints.py:451 fetch_tod_catchment | PY | layers 752/759 | gates | Boolean catchment, not distance. |
| 5 | scripts/generate_conveyancing_report.py:2675 get_tod_uplift_live | PY | TOD layers | BRIEF/CONVEY |  |
| 6 | services/transport_proximity_detector.py:81 detect_nearby_transport | PY | lat/lng | granny/other | Own haversine (an 8th+ copy: conveyancing_db.py:1410, generate_conveyancing_report.py:1673, da_outcome.py:364, vg_comparables.py:130, threat_radar.py:98, nsw_planning_api.py:404). |

**Verdict: DUPLICATED (6 producer sites in 6 code locations).**

### F22. Strata

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/lib/nsw-planning-portal.ts:1203 strataInfo | TS | unit match in address / valuation fallback | ASSESS left, SEPP, LEP, Housing, Pattern Book |  |
| 2 | services/strata_lookup.py:107 query_strata_at_point | PY | cadastre strata layer | BRIEF | Different source. |
| 3 | scripts/generate_conveyancing_report.py:452 detect_strata | PY | address + cadastre | CONVEY | Another implementation. |
| 4 | services/intelligence_brief.py:1097 classify_strata | PY | strata dict, lot area | BRIEF routing |  |

**Verdict: DUPLICATED (4 producer sites in 4 code locations).**

### F23. Bushfire prone

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/lib/nsw-planning-portal.ts:1328 bushfireProne/bushfireCategory | TS | BFPL layer | ASSESS LepControls, DCP bushfire= param |  |
| 2 | services/portal_constraints.py:348 fetch_bushfire_bfpl | PY | BFPL layer | BRIEF |  |
| 3 | scripts/generate_conveyancing_report.py:1993 get_bushfire_live | PY | BFPL | CONVEY |  |
| 4 | services/bushfire_prescreen.py:169 _query_rfs_bfpl | PY | RFS BFPL | bushfire product |  |

**Verdict: DUPLICATED (4 producer sites in 4 code locations).**

### F24. Acid sulfate soils

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/lib/nsw-planning-portal.ts:815 | TS | layer 'Class' | ASSESS LepControls, DCP acid_sulfate= param |  |
| 2 | frontend-nextjs/app/api/property/route.ts:156 | TS | PostGIS fallback | ASSESS | Fallback; 'Present' when value empty. |
| 3 | scripts/generate_conveyancing_report.py:1301 (+:5857) | PY | layer Class / overlay | BRIEF/CONVEY |  |
| 4 | services/cdc_screen.py:458,493 _ACID_CLASS_RE | PY | overlay value regex | CDC screen | Own class parser. |

**Verdict: DUPLICATED (4 producer sites in 4 code locations).**

### F25. Aircraft noise (ANEF)

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/lib/nsw-planning-portal.ts:1239-1241 | TS | ANEF layer | ASSESS LepControls | '>40' mapped to 40. |
| 2 | scripts/generate_conveyancing_report.py:2597 get_anef_live | PY | ANEF layer | BRIEF/CONVEY |  |

**Verdict: DUPLICATED (2 producer sites in 2 code locations).**

### F26. Road classification / street type

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/lib/road-classification-service.ts:46 getRoadClassifications | TS | SIX road service | ASSESS StateLevelControls alert |  |
| 2 | frontend-nextjs/app/api/spatial/brief/route.ts:115 /street-context (street_hierarchy) | TS proxy -> external spatial service | lat/lng | ASSESS SpatialContextCard | Different source; can disagree (Table B). |

**Verdict: DUPLICATED (2 producer sites in 2 code locations).**

### F27. Coordinates (lat/lng)

| # | file:line function | lang | inputs | consumed by | differs |
|---|---|---|---|---|---|
| 1 | frontend-nextjs/hooks/usePropertyAssessment.ts:87 selectedCoordinates (Google Places) | TS | autocomplete pick | ASSESS A2#3 body, mapLat/mapLng (page.tsx:129) | Only on autocomplete path. |
| 2 | frontend-nextjs/app/api/property/profile/route.ts:67-81 (lotPolygon; lat/lng returned in the same response per inventory A1#2) | TS | PP lot polygon | ASSESS page.tsx:129 profileMap | Fallback for #1. |
| 3 | frontend-nextjs/components/compliance/StateLevelControls.tsx:113-134 getCoordinates | TS | SP.geometry centroid/x,y with Mercator inverse | ASSESS SEPP tab calls A3#8,#10,#11 | Can differ by metres from #1/#2. |
| 4 (x2) | scripts/generate_conveyancing_report.py:1033 resolve_address, :1153 geocode_address | PY | address string | BRIEF/CONVEY | Server-side geocode. |

**Verdict: DUPLICATED (5 producer sites in 4 code locations).**

### Facts in Table B not mapped

Address, Lot DP, Precinct, BASIX, Applicable SEPPs, SEPP parking rates, Data currency, Other single-place overlays: either display-only (static literals in StateLevelControls.tsx:1376-1560) or one producer (lib/nsw-planning-portal.ts) with no second computation found. Not exhaustively searched.

Dead or unmounted producers found while tracing (not counted): lib/setback-calculator.ts (no importers), lib/geometry/calculator.ts + app/api/setbacks/calculate (only unmounted PreciseSetbackCalculator/AnalysisTabs), components/compliance/ComplianceDashboard.tsx and its API routes, hooks/useFullPropertyData.ts, hooks/useFullAssessment.ts, services/setback_calculator.py (no importers), services/authoritative_setback_calculator.py (imports only itself/universal_regulatory_engine).

## LINT PATTERNS

Run from the repo root. Engine: ripgrep (Rust regex; `\x5C` = backslash). TS scope: `frontend-nextjs/app frontend-nextjs/lib frontend-nextjs/components frontend-nextjs/hooks` with `--glob '*.ts' --glob '*.tsx'`. PY scope: `services scripts/conveyancing_db.py scripts/generate_conveyancing_report.py` with `--glob '*.py'`. Exclusions (placed AFTER the include globs, because later globs win): `!**/node_modules/** !**/__tests__/** !*.test.* !**/archive/** !**/.next/** !*spike* !*RELEVANCE_DRAFT* !*.backup !*.md`.

Reference command: `rg -n --no-heading --glob '*.ts' --glob '*.tsx' --glob '!**/node_modules/**' --glob '!**/__tests__/**' --glob '!*.test.*' --glob '!**/archive/**' --glob '!**/.next/**' -f <patternfile> frontend-nextjs/app frontend-nextjs/lib frontend-nextjs/components frontend-nextjs/hooks`. Each pattern file holds one regex per line (OR).

Baseline counts are those of **today's** tree. A check should fail when a hit appears at a file:line not in the baseline, or when the count rises; the intended end state is one hit per fact outside the canonical module. Patterns match producer DEFINITIONS and derivations (not callers); a few hits are callers/types and are noted as noise.

### F1 (Council key / slug (formerCouncil, source_council, dcp_setback_controls.lga))

**TS pattern file `council_ts`** (33 hits today):

```
(function|const)\s+(toLgaSlugs?|councilKey|normalizeLgaSlug|normalizeLga|detectCouncil|detectLGAFromName|councilSlugCandidates|determineFormerCouncilArea|getFormerCouncilForPoint|slugToDocPattern)\b
\b(LGA_NAME_TO_SLUG|COUNCIL_KEY_ALIASES|COUNCIL_ALIASES|LGA_ALIASES|COUNCIL_TO_LGA|SLUG_TO_DOC_PATTERN)\s*[:=]
(lga|Lga|LGA|council|Council|lgaId|fc|normalized|name|v)\b[^;\n]{0,40}\.replace\(/(\[[^\]]*\]\+|\x5Cs\+)/g,\s*'_'\)
lga\.split\(' '\)\.map\(
^\s*\.replace\(/\[[^\]]*\]\+/g,\s*'_'\)
```

Baseline hits (file:line): frontend-nextjs/app/assessment/page.tsx:46,56; frontend-nextjs/lib/council-key.ts:20,33,35; frontend-nextjs/lib/council-config.ts:199,217; frontend-nextjs/lib/lga-slug.ts:23,39,44,55; frontend-nextjs/lib/inner-west-mapping.ts:79; frontend-nextjs/lib/inner-west-mapping-v2.ts:51; frontend-nextjs/app/(tools)/planning-controls/[lga-slug]/page.tsx:37,54,57; frontend-nextjs/lib/lga-configs/index.ts:34,111,143,147,148,249; frontend-nextjs/lib/property-data.ts:326; frontend-nextjs/lib/precinct-service.ts:512,576,578; frontend-nextjs/components/compliance/StateLevelControls.tsx:145; frontend-nextjs/app/api/permissibility/check/route.ts:65; frontend-nextjs/app/api/capacity/calculate/route.ts:50; frontend-nextjs/app/api/dcp/structured-controls/route.ts:31; frontend-nextjs/app/api/lep/permissibility/route.ts:6; frontend-nextjs/app/api/provisions/for-property/route.ts:209,491

**PY pattern file `council_py`** (22 hits today):

```
def\s+(_norm_lga|_normalise_slug|_normalise_council|_slug_from_epi|_council_from_zone_epi|detect_former_council|_bare_lga_from_epi|lookup_lga|_validate_former_council_postgis)\b
^(_LGA_NAME_TO_SLUG|ZONE_EPI_TO_LGA_SLUG|SUBURB_TO_FORMER_COUNCIL|_IW_SUBURB_TO_FORMER|DCP_ONBOARDED_SLUGS|_LGA_SLUG_TO_DCP_NAME)\b
(lga|council)[A-Za-z_]*\s*=\s*\(?[A-Za-z_.]*\s*(or\s*"")?\)?\.strip\(\)\.lower\(\)
key\s*=\s*(lga_name|council_name)\.strip\(\)\.lower\(\)
re\.match\(r"\(\.\+\?\)\x5Cs\+Local Environmental Plan
return f"\{lga_name\.title\(\)\} Local Environmental Plan"
```

Baseline hits (file:line): scripts/conveyancing_db.py:246; scripts/generate_conveyancing_report.py:257,284,298,582,606,1676,1860; services/conveyancing.py:101; services/dcp_controls_api.py:51; services/intelligence_brief.py:1392,1412,1682; services/lga_lookup.py:23,42,62,67; services/shadow_detector.py:199; services/pre_da_history.py:235; services/upzoning_check.py:186; services/threat_radar.py:174,176

### F2 (LGA display name)

**TS pattern file `lgad_ts`** (6 hits today):

```
constraints\.lga = result\['LGA Name'\]|const lga = zoneLayer|zoneResult\?\.LGA_NAME|lga_info\[.lga_name.\]|lga_name = row\[0\]\.strip\(\)|lga_name = rows\[0\]\[3\]|lga_name = lga_row\[0\]
```

Baseline hits (file:line): frontend-nextjs/lib/nsw-planning-portal.ts:761,783,818,824; frontend-nextjs/app/api/canibuildit/check/route.ts:247; frontend-nextjs/app/api/property/profile/route.ts:55

**PY pattern file `lgad_py`** (4 hits today):

```
constraints\.lga = result\['LGA Name'\]|const lga = zoneLayer|zoneResult\?\.LGA_NAME|lga_info\[.lga_name.\]|lga_name = row\[0\]\.strip\(\)|lga_name = rows\[0\]\[3\]|lga_name = lga_row\[0\]
```

Baseline hits (file:line): scripts/generate_conveyancing_report.py:1575,1583; services/lga_lookup.py:110; services/granny_flat.py:2271

### F3 (Zone (code and description))

**TS pattern file `zone_ts`** (28 hits today):

```
[zZ]one[A-Za-z]*\??\.(trim\(\)\.)?split\((' '|/\[[^\]]*\]/)\)|function extractZoneCode|zoneDescription\.match\(/\^
```

Baseline hits (file:line): frontend-nextjs/app/tools/zoning-check/page.tsx:60; frontend-nextjs/lib/lep-land-condition.ts:71; frontend-nextjs/app/tools/subdivision-check/page.tsx:124; frontend-nextjs/lib/nsw-planning-portal.ts:979; frontend-nextjs/lib/pdf/see-helpers.ts:73; frontend-nextjs/components/pdf/ContextSection.tsx:50,91; frontend-nextjs/lib/regulatory-constants.ts:305,327,340,348,374,402; frontend-nextjs/components/compliance/ADGSummaryCard.tsx:126; frontend-nextjs/components/compliance/StateLevelControls.tsx:250,434,505; frontend-nextjs/lib/see/seeBuilders.ts:81,258; frontend-nextjs/components/compliance/ProvisionsByTocStructure.tsx:434,1640,1641; frontend-nextjs/lib/see/section-aggregation.ts:121; frontend-nextjs/app/api/housing-sepp/eligibility/route.ts:150; frontend-nextjs/app/api/canibuildit/check/route.ts:245; frontend-nextjs/app/api/cdc/preliminary-check/route.ts:42,44; frontend-nextjs/app/api/og/granny-flat/route.tsx:46

**PY pattern file `zone_py`** (12 hits today):

```
[zZ]one[A-Za-z_]*\)?\.strip\(\)\.split\(\)\[0\]|_zone_parts\s*=|_zc_parts\s*=|_pz_parts\s*=|_zs_parts\s*=|def _zone_prefix|def normalize_zone|_zone_parts\[0\]
```

Baseline hits (file:line): scripts/conveyancing_db.py:854,1199; scripts/generate_conveyancing_report.py:669,670,4675,4765,5228; services/compound_constraints.py:408; services/cdc_screen.py:479,480; services/housing_sepp_eligibility.py:85; services/intelligence_brief.py:1172

### F4 (Lot area)

**TS pattern file `area_ts`** (15 hits today):

```
(calculatePolygonArea|calculateLotDimensions)\(|Shoelace area|cosLat\s*\*\s*cosLat|parseFloat\([A-Za-z.?]*propertyArea|propertyAreaStr\s*\?
```

Baseline hits (file:line): frontend-nextjs/hooks/usePropertyAssessment.ts:115; frontend-nextjs/hooks/useFullPropertyData.ts:304; frontend-nextjs/lib/geometry/lot-dimensions.ts:55,86,217,327,339; frontend-nextjs/lib/property-data.ts:139; frontend-nextjs/app/api/assessment/full/route.ts:125; frontend-nextjs/app/api/canibuildit/check/route.ts:191,204; frontend-nextjs/components/compliance/StateLevelControls.tsx:485; frontend-nextjs/app/api/property/[address]/route.ts:208; frontend-nextjs/app/api/property/profile/route.ts:70; frontend-nextjs/app/api/satellite/granny-flat/route.ts:326

**PY pattern file `area_py`** (6 hits today):

```
def _shoelace_area|def _compute_lot_area_m2|def calculate_lot_dimensions|def _reconcile_lot_area|lot_area_m2 = valuation\.get|"lot_area_m2": _num\(area\)
```

Baseline hits (file:line): scripts/generate_conveyancing_report.py:1215; services/granny_flat.py:903; services/lot_dimensions.py:134,232; services/intelligence_brief.py:3386,3743

### F5, F6, F7 (Frontage / depth (lot width); Street frontage / width at front building line; Corner lot)

**TS pattern file `front_ts`** (9 hits today):

```
roadCount >= 2|nearbyRoads\.length >= 2|Math\.sqrt\(lotArea\)|function frontageDepthFromRect|export function measureStreetFrontage|export function widthRange|Secondary street setback
```

Baseline hits (file:line): frontend-nextjs/hooks/usePropertyAssessment.ts:120; frontend-nextjs/lib/geometry/street-frontage.ts:163,226; frontend-nextjs/lib/geometry/lot-dimensions.ts:142; frontend-nextjs/lib/geometry/corner-lot-detection.ts:153; frontend-nextjs/lib/see/propertyContext.ts:113; frontend-nextjs/app/blog/setback-requirements-nsw/page.tsx:53; frontend-nextjs/app/api/dcp/structured-controls/route.ts:114; frontend-nextjs/components/property-details-comprehensive.tsx:249

**PY pattern file `front_py`** (9 hits today):

```
math\.sqrt\(lot_area_m2|is_corner=False|def _frontage_depth_obb|def measure_street_frontage|def street_frontage_for_geometry|def rectangle_width_range|def width_range
```

Baseline hits (file:line): services/constraint_arithmetic.py:403,1285,1463; services/cdc_lot_inputs.py:116; services/lot_dimensions.py:199,243; services/street_frontage.py:144,222,261

### F8 (Setbacks front / side / rear (which row applies))

**TS pattern file `setback_ts`** (19 hits today):

```
fetchDcpControls\(|async function getSetbacks|FROM dcp_precinct_requirements|FROM dcp_setback_controls
```

Baseline hits (file:line): frontend-nextjs/lib/dcp-controls-client.ts:57; frontend-nextjs/lib/coverage.ts:28,55,73; frontend-nextjs/app/api/tod/parking-rates/route.ts:173; frontend-nextjs/lib/precinct-service.ts:157; frontend-nextjs/app/api/capacity/calculate/route.ts:121,220,268; frontend-nextjs/app/api/canibuildit/check/route.ts:448; frontend-nextjs/app/api/internal/setback-review/[id]/route.ts:121; frontend-nextjs/app/api/internal/setback-review/route.ts:21; frontend-nextjs/app/api/dcp/structured-controls/route.ts:207; frontend-nextjs/app/api/compliance/precinct-requirements/route.ts:131; frontend-nextjs/app/api/compliance/dcp-complete/route.ts:364,512,1200; frontend-nextjs/app/api/dcp/coverage/route.ts:68; frontend-nextjs/app/(tools)/planning-controls/[lga-slug]/page.tsx:229

**PY pattern file `setback_py`** (9 hits today):

```
def fetch_dcp_setbacks|def _get_dcp_value|def _matching_controls|def _fetch_sd_setbacks|def _dcp_controls_from_setback_rows|def _build_dcp_controls|def _dcp_height_metres|FROM dcp_setback_controls
```

Baseline hits (file:line): scripts/conveyancing_db.py:641,683; services/constraint_arithmetic.py:157,203,226,294; services/granny_flat.py:310,325; services/intelligence_brief.py:2749

### F9, F20 (Dev-type filter of DCP controls; Development type (page developmentType))

**TS pattern file `devtype_ts`** (22 hits today):

```
export function detectDevTypeFromZone|r\.dev_type === |dev_type=$\{|devType\s*=\s*'dwelling_house'|devType\??:\s*string\s*=\s*'dwelling_house'|\.v2_applicable_dev_types|export function filterRequirementsByDevType
```

Baseline hits (file:line): frontend-nextjs/lib/dev-type-filter.ts:441; frontend-nextjs/lib/requirement-prioritization.ts:103; frontend-nextjs/app/api/tod/parking-rates/route.ts:177; frontend-nextjs/components/compliance/ProvisionsByTocStructure.tsx:595,674,675,676,725,820,1002,1101,1179,1273,1376,1453; frontend-nextjs/app/api/capacity/calculate/route.ts:124,227; frontend-nextjs/components/compliance/DARequirementsSection.tsx:194; frontend-nextjs/components/compliance/DcpStructuredControls.tsx:167; frontend-nextjs/app/api/canibuildit/check/route.ts:450; frontend-nextjs/app/api/dcp/structured-controls/route.ts:229; frontend-nextjs/app/api/provisions/for-property/route.ts:760

**PY pattern file `devtype_py`** (7 hits today):

```
_ZONE_TIER_CEILING\s*[:=]|c\.dev_type == |ovr\.dev_type == dev_type|std\.dev_type == dev_type|dev_type\s*=\s*['"]dwelling_house['"]
```

Baseline hits (file:line): scripts/generate_conveyancing_report.py:2730; services/constraint_arithmetic.py:214,217,519,760,950; services/intelligence_brief.py:1383

### F10 (Condition / applicability filter (zone, precinct, heritage, land facts))

**TS pattern file `applic_all_ts`** (11 hits today):

```
export const ZONE_APPLIES_SQL|export function decideLandCondition|export function decideLandApplication|export function applyLandConditions|hcaTagSql\(|NOT_HERITAGE_SQL\s*=|export function assessControlRelevance
```

Baseline hits (file:line): frontend-nextjs/lib/environmental-relevance-filter.ts:40; frontend-nextjs/lib/dcp-land-application.ts:138; frontend-nextjs/lib/lep-land-condition.ts:98,119; frontend-nextjs/lib/provision-sql-filters.ts:30,46,65; frontend-nextjs/app/api/provisions/for-property/route.ts:825,828,1094,1099

**PY pattern file `applic_py`** (6 hits today):

```
def zone_row_applies|def _lot_band_match|def _resolve_lot_band|_ZONE_CODE\s*=|_EXCLUSION_WORDING\s*=|applicability == "precinct_specific"
```

Baseline hits (file:line): scripts/conveyancing_db.py:495,497,505,876; services/constraint_arithmetic.py:110,137

### F11 (Permitted forms / permissibility)

**TS pattern file `perm_ts`** (12 hits today):

```
FROM lep_land_use_table|export function permitsApartmentDevelopment|export function isLMREligibleZone|FROM housing_sepp_standards|eligibleTypes\.push|const eligibleTypes
```

Baseline hits (file:line): frontend-nextjs/app/api/tod/parking-rates/route.ts:120; frontend-nextjs/app/planning-standards/page.tsx:66; frontend-nextjs/app/api/canibuildit/check/route.ts:402; frontend-nextjs/app/api/compliance/parking/route.ts:100; frontend-nextjs/lib/regulatory-constants.ts:373,401; frontend-nextjs/app/api/lep/permissibility/route.ts:50; frontend-nextjs/app/api/housing-sepp/eligibility/route.ts:192; frontend-nextjs/app/api/permissibility/check/route.ts:77,108,135,161

**PY pattern file `perm_py`** (13 hits today):

```
FROM lep_land_use_table|def _permitted_engine_forms|def _realistic_forms|def _ceiling_within_tier|def evaluate_eligibility|def _dwelling_house_permissible|FROM housing_sepp_standards
```

Baseline hits (file:line): scripts/conveyancing_db.py:1215,1532; services/intelligence_brief.py:1428,1444,1458,1482,2061; services/housing_sepp_eligibility.py:119,272; services/secondary_dwelling_paths.py:198; services/granny_flat.py:158,178,208

### F13, F14, F15 (FSR; Max height; Min lot size)

**TS pattern file `fsr_ts`** (22 hits today):

```
constraints\.(maxFsr|maxHeight|minLotSize)\s*=|propertyData\.constraints\.(maxFsr|minLotSize)\s*=|const (maxHeight|maxFsr)\s*=\s*(heightLayer|fsrLayer)|const (lepHeight|lepFsr)\b|MAX_B_H|MAX_FSR|\bmaxHeight = parseFloat|\bmaxFSR = parseFloat|fsr_limit:|return result\['Maximum Building Height'\]
```

Baseline hits (file:line): frontend-nextjs/hooks/usePropertyData.ts:90; frontend-nextjs/app/api/capacity/calculate/route.ts:97,103; frontend-nextjs/app/api/canibuildit/check/route.ts:258,262; frontend-nextjs/app/api/housing-sepp/eligibility/route.ts:146,147; frontend-nextjs/components/compliance/StateLevelControls.tsx:511,513,522; frontend-nextjs/lib/nsw-planning-portal.ts:758,768,788; frontend-nextjs/app/api/property/[address]/route.ts:92,175,197,270; frontend-nextjs/app/api/property/route.ts:151,160,162; frontend-nextjs/app/api/property/profile/route.ts:56,57

**PY pattern file `fsr_py`** (11 hits today):

```
out\["(height|fsr|lot_size)"\] = |_parse_numeric\(lep_(height|fsr)_str\)|controls\["lot_size"\] = 
```

Baseline hits (file:line): scripts/generate_conveyancing_report.py:1287,1292,1296,5860; services/conveyancing.py:408,608; services/constraint_arithmetic.py:475,476,1367,1368; services/intelligence_brief.py:3943

### F16 (Heritage flag)

**TS pattern file `heritage_ts`** (7 hits today):

```
case 'Heritage Map'|const heritage = heritageLayer|const hasHeritage|const is_heritage|isHeritage: true|const heritage = constraints\.heritage
```

Baseline hits (file:line): frontend-nextjs/lib/property-data.ts:211,212; frontend-nextjs/app/api/canibuildit/check/route.ts:254; frontend-nextjs/lib/nsw-planning-portal.ts:791; frontend-nextjs/components/property-card.tsx:101; frontend-nextjs/app/api/property/profile/route.ts:58; frontend-nextjs/app/api/satellite/granny-flat/route.ts:534

**PY pattern file `heritage_py`** (9 hits today):

```
def fetch_heritage_postgis|def _is_heritage_land|def _check_heritage|def check_heritage_flag|def _query_heritage_overlay|def _check_heritage_overlay|heritage = bool\(heritage_items|out\["heritage_items"\]
```

Baseline hits (file:line): scripts/conveyancing_db.py:1079; scripts/generate_conveyancing_report.py:1308,1377; services/bushfire_prescreen.py:298; services/granny_flat.py:871; services/intelligence_brief.py:2952; services/pre_da_history.py:735; services/solar_yield.py:530; services/upzoning_check.py:168

### F17 (Flood flag)

**TS pattern file `flood_ts`** (13 hits today):

```
layer_type === 'flood'|floodProne:\s*false|const floodProne = floodLayer|overlayTypes\.has\('flood'\)|dcpFloodMap\s*=|constraints\.floodProne
```

Baseline hits (file:line): frontend-nextjs/lib/property-data.ts:226; frontend-nextjs/lib/nsw-planning-portal.ts:745; frontend-nextjs/components/property-card.tsx:60; frontend-nextjs/lib/see/intake.ts:73,432,433; frontend-nextjs/components/compliance/ComplianceDashboard.tsx:1012,1013; frontend-nextjs/app/api/canibuildit/check/route.ts:349; frontend-nextjs/app/api/compliance/dashboard/route.ts:45; frontend-nextjs/app/api/property/route.ts:84,128; frontend-nextjs/app/api/property/profile/route.ts:86

**PY pattern file `flood_py`** (7 hits today):

```
def _query_flood_overlay|def _query_epi_overlay|_overlay_state\("flood"\)|layer_type = 'flood'|def _query_ses_flood_study
```

Baseline hits (file:line): services/cdc_screen.py:503; services/bushfire_prescreen.py:271,280; services/flood_truth.py:477,949,976,985

### F18 (LMR (Low and Mid-Rise) area)

**TS pattern file `lmr_ts`** (8 hits today):

```
lowMidRiseExcluded\s*=|lowMidRiseExclusion:|const inLMRArea|const lmrAreaKnown|requiresLMR:|export function permitsApartmentDevelopment
```

Baseline hits (file:line): frontend-nextjs/lib/nsw-planning-portal.ts:361,1366; frontend-nextjs/lib/regulatory-constants.ts:401; frontend-nextjs/app/api/housing-sepp/eligibility/route.ts:203,221,242,259,260

**PY pattern file `lmr_py`** (9 hits today):

```
def lmr_gates|def _lmr_uplift_form|def fetch_sepp_exclusions|def fetch_tod_catchment|def fetch_town_centre_catchment|def fetch_dual_occ_prohibition|"lowMidRiseExclusion"
def _gate_inputs
```

Baseline hits (file:line): services/housing_sepp_gates_api.py:53; services/housing_sepp_eligibility.py:170; services/intelligence_brief.py:1588; services/portal_constraints.py:31,412,422,451,481,511

### F19 (Instrument / LEP name)

**TS pattern file `inst_ts`** (6 hits today):

```
lepName =|zone_epi"\] = results|const epiName: string|lga_name\.title\(\)\}" Local Environmental|\$\{constraints\.lga\} Local Environmental Plan|def _bare_lga_from_epi
```

Baseline hits (file:line): frontend-nextjs/lib/property-data.ts:359; frontend-nextjs/lib/see/seeBuilders.ts:262; frontend-nextjs/components/compliance/ComplianceDashboard.tsx:1262; frontend-nextjs/components/compliance/LepControls.tsx:54,55; frontend-nextjs/app/api/canibuildit/check/route.ts:248

**PY pattern file `inst_py`** (2 hits today):

```
lepName =|zone_epi"\] = results|const epiName: string|lga_name\.title\(\)\}" Local Environmental|\$\{constraints\.lga\} Local Environmental Plan|def _bare_lga_from_epi
```

Baseline hits (file:line): scripts/generate_conveyancing_report.py:1283; services/intelligence_brief.py:1392

### F21 (TOD / station distance)

**TS pattern file `tod_ts`** (4 hits today):

```
stationDistance: result\[|const TRANSPORT_STATIONS|const distance = Math\.sqrt\(dx \* dx \+ dy \* dy\)|const stationDistance =
```

Baseline hits (file:line): frontend-nextjs/app/api/tod/transport-autocomplete/route.ts:8; frontend-nextjs/lib/nsw-planning-portal.ts:862,1280; frontend-nextjs/components/compliance/StateLevelControls.tsx:501

**PY pattern file `tod_py`** (3 hits today):

```
def fetch_tod_catchment|def get_tod_uplift_live|def detect_nearby_transport
```

Baseline hits (file:line): scripts/generate_conveyancing_report.py:2675; services/transport_proximity_detector.py:81; services/portal_constraints.py:451

### F22 (Strata)

**TS pattern file `strata_ts`** (2 hits today):

```
const strataInfo: StrataInfo|isStrata: valuationFallback
```

Baseline hits (file:line): frontend-nextjs/lib/nsw-planning-portal.ts:1203,1204

**PY pattern file `strata_py`** (4 hits today):

```
def query_strata_at_point|def detect_strata|def classify_strata|def classify_dwelling_type
```

Baseline hits (file:line): scripts/generate_conveyancing_report.py:452; services/intelligence_brief.py:1097; services/strata_lookup.py:61,107

### F23 (Bushfire prone)

**TS pattern file `bush_ts`** (2 hits today):

```
constraints\.bushfireProne = true|bushfireCategory = 
```

Baseline hits (file:line): frontend-nextjs/lib/nsw-planning-portal.ts:1328,1329

**PY pattern file `bush_py`** (3 hits today):

```
def fetch_bushfire_bfpl|def get_bushfire_live|def _query_rfs_bfpl
```

Baseline hits (file:line): scripts/generate_conveyancing_report.py:1993; services/bushfire_prescreen.py:169; services/portal_constraints.py:348

### F24 (Acid sulfate soils)

**TS pattern file `ass_ts`** (2 hits today):

```
constraints\.acidSulfateSoils = |propertyData\.constraints\.acidSulfateSoils = 
```

Baseline hits (file:line): frontend-nextjs/lib/nsw-planning-portal.ts:815; frontend-nextjs/app/api/property/route.ts:156

**PY pattern file `ass_py`** (2 hits today):

```
out\["ass_class"\] = |_ACID_CLASS_RE = 
```

Baseline hits (file:line): scripts/generate_conveyancing_report.py:1301; services/cdc_screen.py:458

### F25 (Aircraft noise (ANEF))

**TS pattern file `anef_ts`** (1 hits today):

```
let anefLevel
```

Baseline hits (file:line): frontend-nextjs/lib/nsw-planning-portal.ts:1239

**PY pattern file `anef_py`** (1 hits today):

```
def get_anef_live
```

Baseline hits (file:line): scripts/generate_conveyancing_report.py:2597

### F26 (Road classification / street type)

**TS pattern file `road_ts`** (5 hits today):

```
export async function getRoadClassifications|street_hierarchy
```

Baseline hits (file:line): frontend-nextjs/hooks/useSpatialContext.ts:23; frontend-nextjs/lib/road-classification-service.ts:46; frontend-nextjs/lib/see/seeBuilders.ts:375; frontend-nextjs/components/property/SpatialContextCard.tsx:64,71

### F27 (Coordinates (lat/lng))

**TS pattern file `coord_ts`** (2 hits today):

```
getCoordinates = \(\)|selectedCoordinates\?\.lat|const lotPolygonWgs84
```

Baseline hits (file:line): frontend-nextjs/app/assessment/page.tsx:129; frontend-nextjs/components/compliance/StateLevelControls.tsx:113

**PY pattern file `coord_py`** (4 hits today):

```
def geocode_address|def resolve_address|def resolve_propid_by_point
```

Baseline hits (file:line): scripts/generate_conveyancing_report.py:1033,1091,1153; services/pre_da_history.py:279

### F12 Dwelling yield

No lint needed (single formula). Guard the call contexts instead: `rg -n "compute_constraint_arithmetic\(|_dwellings_for" services` should show only services/constraint_arithmetic.py and the two callers (constraint_arithmetic_full :1447 and intelligence_brief.py:4043 region).

### Distance primitive (supports F21)

Pattern: `def _?haversine|haversine\w*\(|Math\.atan2\(Math\.sqrt\(a\)` finds the copies listed in F21 row 6 (conveyancing_db.py:1410, generate_conveyancing_report.py:1673, da_outcome.py:364, vg_comparables.py:130, threat_radar.py:98, nsw_planning_api.py:404, transport_proximity_detector.py:77; TS: api/tod/transport-autocomplete/route.ts:75, api/canibuildit/check/route.ts:523, api/satellite/threat-radar/search/route.ts:36). Counts above come from a manual grep, not the lint scripts.

