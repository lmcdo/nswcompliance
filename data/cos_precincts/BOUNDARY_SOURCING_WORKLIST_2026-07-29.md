# City of Sydney precinct boundary sourcing — worklist (2026-07-29)

Status: **backfill DONE** (462 rows, backup `data/db_rollback_backups/cos_precinct_backfill_2026-07-29.csv`);
**boundaries LOADED STAGED 2026-07-29 (later session)** — 145 rows in `dcp_precinct_boundaries`
with `lga='Sydney-staged'` so the live service (which matches `LOWER(lga)='sydney'`) cannot
see them yet. **GO-LIVE FLIP (run ONLY after PR #842 — fix/precinct-attribution-warning —
merges AND deploys, else boundary-matched CoS addresses get formerCouncil='Marrickville'):**

```sql
UPDATE dcp_precinct_boundaries SET lga='Sydney' WHERE lga='Sydney-staged';
```

Load details: 91 locality sub-areas + 2.2/2.8 locality-level (L11), 12 specific areas (L15),
40 sites (L16). Rollback file `data/db_rollback_backups/cos_boundaries_inserted_2026-07-29.csv`.
Verified: 0 invalid geometries; verify_precinct_boundaries.py PASS; independent SIX-geocoded
spot checks 904 Bourke St Zetland → {6.3.3, 2.5.8, 5.2}, 2 Chifley Sq → {6.3.24, 2.1.12, 5.1},
18 Huntley St Alexandria → {6.2.4, 2.7.11} all PASS. Martin Place GIS names are SWAPPED
(Sections were right): 6.3.4 uses the 'Section 6.3.4' feature at Martin Pl/Macquarie St;
the feature *named* '60 Martin Place' is actually 65-79 Sussex St = 6.3.5. Skipped (logged in
loader output): 11 junk L11 features ('Central Sydney N', 'Railway Land', 'Neighbourhoods'),
X.Y.1 sub-areas whose content lives in locality-level rows, sites with no current provisions
(6.1.6, 6.2.6, 6.2.7). Locality-level rows 2.1, 2.3–2.7, 2.9–2.13 still have no polygons
(no locality-level source) — excluded + warning, as designed.

**KNOWN_POINTS to add to `scripts/verify_precinct_boundaries.py`** (file is currently
UNTRACKED in git — commit it, then add; coords geocoded independently via SIX
Address_Location 2026-07-29, all three verified passing against the staged polygons):

```python
# City of Sydney (staged as 'Sydney-staged' until PR #842 deploys + lga flip)
(151.2067248368, -33.9048022299, "6.3.3", "904 Bourke St Zetland (CoS site; also 2.5.8, 5.2)"),
(151.2117495867, -33.8659150961, "6.3.24", "2 Chifley Sq Sydney (CoS site; also 2.1.12, 5.1)"),
(151.1890328271, -33.9074964885, "6.2.4", "18 Huntley St Alexandria (CoS site; also 2.7.11)"),
```
('60 Martin Place' deliberately omitted — SIX geocodes it to the 53-63 odd-side range.)

## Authoritative source (verified live 2026-07-29)

City of Sydney official ArcGIS FeatureServer (no auth), one service, three layers:

`https://services1.arcgis.com/cNVyNtjGVZybOQWZ/arcgis/rest/services/Sydney_Development_Control_Plan_2012/FeatureServer`

| Layer | Name | Keying | Covers |
|---|---|---|---|
| 11 | SDCP 2012 – Locality areas | `Section` ('2.4.5') + `LocalityName` | 111 features, section-2 sub-areas |
| 15 | SDCP 2012 – Specific areas | `AreaName` only (no Section) | 12 features = all 5.1–5.12 |
| 16 | SDCP 2012 – Specific sites | `Section` ('6.3.1') + `SiteName` | 50 features |

## Traps found (verify before loading)

1. **Layer 16 uses STALE pre-amendment 6.1 numbering.** The amended DCP body renumbered
   group 6.1 (APDG subsections dissolved): body 6.1.5=261-263 Oxford St, 6.1.6=Eye Hospital,
   6.1.7=Victoria Park, 6.1.8=Email Site, 6.1.9=AMP. GIS still has 6.1.8=St John's (Oxford St),
   6.1.9=Eye Hospital, 6.1.10=Victoria Park, 6.1.11=Email, 6.1.12=AMP. The DB backfill used
   **body numbering** (authoritative, verified from the current PDF). Join 6.1 by SiteName, not Section.
2. Layer 16 quirks: OBJECTID 52 has Section='6.3' (SiteName says 6.3.19 Burrows Rd);
   6.2.12 Darlinghurst Rd = 4 multipart rows (union them); check for missing sites
   (6.3.16, 6.3.18, 6.3.25–6.3.31 not all seen in first 40 — enumerate all 50).
3. Layer 11 oddities: rows with Section '2', '5', '7', '8' + LocalityName 'Central Sydney N'
   — likely 2.1.x special character areas with truncated Section. Verify by name against
   the 2.1.x list before use.
4. Layer 15 has no Section field — join by AreaName to the name table below.
5. Layer 11 covers sub-areas (2.x.y). Locality-level rows (2.x) may need union of their
   sub-areas OR may not be covered — the DCP defines localities by the Section-2 index map
   (p7) and street descriptions, NOT suburb names. Do NOT use suburb polygons.

## v2_precinct_id → name table (source-verified from the adopted PDFs)

### Section 2 localities (id = 2.x; sub-areas 2.x.y carry the sub-area name in their DB section_header)
2.1 Central Sydney · 2.2 Rosebery Estate · 2.3 Chippendale, Camperdown, Darlington, West
2.4 City East · 2.5 Green Square · 2.6 Glebe and Forest Lodge
2.7 Erskineville, Alexandria (west) and Newtown (south) · 2.8 Millers Point
2.9 Paddington/Centennial Park · 2.10 Southern Enterprise Area · 2.11 Surry Hills
2.12 Ultimo/Pyrmont · 2.13 Waterloo and Redfern
(2.0 = document apparatus rows — never load a boundary; stays excluded)

### Section 5 areas (id = 5.x)
5.1 Central Sydney · 5.2 Green Square · 5.3 Green Square - Epsom Park
5.4 Green Square – Lachlan · 5.5 Ashmore Neighbourhood · 5.6 Rosebery Estate, Rosebery
5.7 Green Square - North Rosebery · 5.8 Southern Enterprise Area · 5.9 Danks Street South
5.10 Botany Road Precinct · 5.11 Oxford Street Cultural and Creative Precinct
5.12 Waterloo Estate (South)
(5.0 = document apparatus)

### Section 6 sites (id = 6.x.y, BODY numbering)
6.1.3 Commonwealth Bank 'Money Box' 108-120 Pitt St · 6.1.4 APDG site (incl. Cahill figures)
6.1.5 261-263 Oxford St St John's Church Paddington · 6.1.6 Former Sydney Eye Hospital
6.1.7 Victoria Park–South Dowling Corridor · 6.1.8 Email Site 13 Joynton Ave Zetland
6.1.9 AMP Circular Quay Precinct
6.2.4 18 Huntley St Alexandria · 6.2.6 25-33 Erskineville Rd · 6.2.7 Telecommunications Bldg Oxford St
6.2.8 397-399 Cleveland St & 2-38 Baptist St · 6.2.9 Bayswater Car Rental William St
6.2.10 219-241 Cleveland St (Australia Post) · 6.2.11 97-101 Pyrmont Bridge Rd · 6.2.12 Darlinghurst Rd Potts Point
6.3.1–6.3.31 per section-6 TOC (TOC = body-consistent for 6.2/6.3): 6.3.1 87 Bay St Glebe,
6.3.2 287-289 Crown St, 6.3.3 904 Bourke St Zetland, 6.3.4 60 Martin Pl, 6.3.5 65-79 Sussex St,
6.3.6 230-238 Sussex St, 6.3.7 505-523 George St, 6.3.8 45 Murray St, 6.3.9 51-55 Missenden Rd,
6.3.10 296-298 Botany Rd & 284 Wyndham St, 6.3.11 7-15 Randle St, 6.3.12 2-32 Junction St,
6.3.13 102-106 Dunning Ave, 6.3.14 4-6 Bligh St, 6.3.15 225-279 Broadway, 6.3.16 12-22 & 24 Rothschild Ave,
6.3.17 72-84 Foveaux St, 6.3.18 1-11 Oxford St Paddington, 6.3.19 1-3 Burrows Rd St Peters,
6.3.20 4-44 Wentworth Ave, 6.3.21 187 Thomas St Haymarket, 6.3.22 17-31 Cowper St & 2A-2D Wentworth Park Rd,
6.3.23 30-62 Barcom Ave, 6.3.24 2 Chifley Sq, 6.3.25 757-763 George St, 6.3.26 15-23 Hunter St & 103-107 Pitt St,
6.3.27 923-935 Bourke St Waterloo, 6.3.28 232-236A & 238 Elizabeth St, 6.3.29 8-24 Kippax St,
6.3.30 47-51 Riley St Woolloomooloo, 6.3.31 383-395A Kent St
(6.0 = document apparatus; GIS Section '6.3.4/6.3.5' note: GIS has '58-60 Martin Place'=6.3.4
and '60 Martin Place'=6.3.5 — DCP TOC says 6.3.4 '60 Martin Place', 6.3.5 '65-79 Sussex St'.
Verify by SiteName + address, never by Section alone.)

## Loading procedure (next session — Waverley E1–E5 pattern)

1. Query each layer with `returnGeometry=true&outSR=4326`, union multipart per id.
2. Insert into `dcp_precinct_boundaries` (lga='City of Sydney', precinct_id=v2_precinct_id
   value, precinct_name from table above). Backup table first.
3. Spot checks via `scripts/verify_precinct_boundaries.py` — add CoS KNOWN_POINTS
   (e.g. 904 Bourke St Zetland → 6.3.3; 18 Huntley St Alexandria → 6.2.4; a Green Square
   address → 5.2 + 2.5).
4. Do NOT add 'city of sydney' to NEAREST_FALLBACK_LGAS until coverage is assessed.
5. Sub-area vs locality serving: rows carry ids at both levels (2.x and 2.x.y).
   A point inside sub-area 2.4.11 must also match locality 2.4 — either load locality
   polygons as union of sub-areas (only if the DCP index map confirms coverage) or make
   matching return all containing ids (multi-match already supported since #835).

## Extraction evidence

Full per-row evidence: `data/db_rollback_backups/cos_precinct_backfill_2026-07-29.csv`
(evidence column: footer anchor / ref+footer agreement / TOC-vs-body resolution / manual
front-matter classification). Method: page footers ('Sydney DCP 2012 - December 2012 X.Y-N')
anchored per page; contiguity-checked blocks; sandwich completion for footerless figure pages;
sec-6 site ranges from body headings (6.1) / body-verified TOC (6.2, 6.3).
