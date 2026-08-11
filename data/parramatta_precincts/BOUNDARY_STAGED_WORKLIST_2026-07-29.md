# Parramatta precinct boundaries — STAGED load worklist (2026-07-29)

Status: **13 rows LOADED STAGED** as `lga='Parramatta-staged'` (ids 450–462,
rollback CSV `data/db_rollback_backups/parramatta_boundaries_inserted_2026-07-29.csv`).
The live matcher (`LOWER(lga)=LOWER($lga)`) cannot see them until the flip.

## GO-LIVE FLIP — string matters

The frontend's `constraints.lga` comes from the Planning Portal layerintersect
`LGA Name` field, which for Parramatta addresses returns **`CITY OF PARRAMATTA`**
(verified live 2026-07-29 against propId 815225, 126 Church St). The flip must
therefore be:

```sql
UPDATE dcp_precinct_boundaries SET lga='City of Parramatta' WHERE lga='Parramatta-staged';
```

(NOT `'Parramatta'` — that string never matches the portal value.)
Run ONLY after the former_council-first attribution PR deploys, else
boundary-matched Parramatta addresses fall through PRECINCT_ID_PATTERNS
(dotted 7.10.x/9 ids have no Parramatta pattern entry → attribution falls back
wrongly). `former_council='Parramatta'` is set on all 13 rows.

## What was loaded

| precinct_id | name | source | parts | area m² |
|---|---|---|---|---|
| 7.10.1 | North Parramatta and Sorrell Street Conservation Areas | ePlanning EPI heritage (H_NAME join, union of 2) | 2 | 149,615 |
| 7.10.2–7.10.10, 7.10.12 | single-HCA sections | ePlanning EPI heritage | 1 each | 4,316–297,464 |
| 7.10.11 | Epping/Eastwood + Boronia Ave + Wyralla Ave (union of 3) | ePlanning EPI heritage | 3 | 1,001,482 |
| 9 | Parramatta City Centre | council AGOL LEP 2023 layer 12; ePlanning Development_Control/3 corroborates (bbox delta 1.3e-5°) | 1 | 2,680,388 |

Join evidence: 15/15 `H_NAME` exact-set match vs the section→name map;
corpus section headings confirm the multi-HCA unions verbatim
("7.10.1 NORTH PARRAMATTA AND SORRELL STREET CONSERVATION AREAS",
"7.10.11 EPPING/EASTWOOD, BORONIA AVENUE AND WYRALLA AVENUE CONSERVATION AREAS").
Part 9 = LEP city-centre area confirmed from corpus 9.1.1: "The controls in
this Part apply to the Parramatta City Centre… support the controls contained
in Part 7 of Parramatta LEP 2023."

## Spot checks (SIX Address_Location, independent of both geometry sources)

All PASS against staged polygons; DCP text corroborates Boronia (northern-side
row = odd numbers inside, even outside):

```python
# KNOWN_POINTS for scripts/verify_precinct_boundaries.py
# (staged as 'Parramatta-staged'; flip to 'City of Parramatta')
(151.008622, -33.801548, "7.10.1",  "74 Sorrell St North Parramatta (HCA)"),
(151.075045, -33.774674, "7.10.11", "15 Boronia Ave Epping (northern-side row per DCP text)"),
(151.086887, -33.774601, "7.10.9",  "46 Essex St Epping (HCA)"),
(151.004125, -33.818227, "9",       "126 Church St Parramatta (city centre)"),
```

Near-miss evidence the polygons are tight, not wrong: 10 Sorrell St = 29 m
outside; 8 Boronia (southern side) = 43 m outside; 30 Essex = 95 m outside.

## Deliberately NOT loaded

- **Part 10 LNTAs (10.2.1–3)**: no provision rows carry 10.2.x precinct ids
  (Part 10 was never precinct-keyed) → loading polygons would create orphan
  boundaries; ALSO the council `city_centre_LNTA` layer is stamped Amendment
  No 2 while the corpus is Amendment 4 — currency unverified. Load only after
  Part 10 keying + amendment check.
- **Part 8 precincts (8.1.x/8.2.x/8.3.x/8.4.x) and 9.10.x / 8.5.x sites**: no
  public polygon source exists (4-sweep negative in
  parramatta_boundary_sources.md). Awaiting council GIS reply
  (`gis_boundary_request_email_draft.md` in this directory). Do NOT derive
  from DPIE rezoning precincts or suburbs.
- Deferred-area caveat: Part 9's Land Application Map includes deferred areas
  (9B Auto Alley West; Area A Park Edge). 9B provisions are pending re-chunk
  (row 105629); until then '9' rows serve there — same over-inclusion class,
  bounded to the deferred strips.
