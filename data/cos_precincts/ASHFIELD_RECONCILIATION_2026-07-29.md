# Ashfield precinct reconciliation — findings + state (2026-07-29)

## D-number → Part-N → name mapping (SOURCE-PROVEN)

Source: `chapter-d-precinct-guidelines.pdf` R2 v1.1-2026-03-02 (same file as council's
`..._with_IWLEP_2022_amendments_Nov_22.pdf`). Every page carries a "Part N – Name"
running header; full page ranges:

| Part | Pages | Name (source) | Boundary row name | Boundary? |
|---|---|---|---|---|
| 1 | 3–40 | Ashfield Town Centre | same | ✓ |
| 2 | 41–57 | Ashfield East | same | ✓ |
| 3 | 58–83 | Ashfield West | same | ✓ |
| 4 | 84–95 | **Croydon Town Centre** | 'Croydon Urban Village' (name drift) | ✓ |
| 5 | 96–106 | Neighbourhood Centre (B1) Zone | — | ✗ none |
| 6 | 107–155 | Enterprise Zone (B6) Parramatta Road | same | ✓ |
| 7 | 156–168 | Enterprise Zone (B6) Hurlstone Park | same | ✓ |
| 8 | 169–180 | SummerHill Town Centre | 'SummerHill Urban Village' (drift) | ✓ |
| 9 | 181–182 | Summer Hill Flour Mills Site | same | ✓ |
| 10 | 183–187 | Edwards Street – B4 Zone | same | ✓ (was orphan) |
| 11 | 188–192 | Industrial Zones | — | ✗ none |
| 12 | 193–196 | 55-63 Smith Street Summer Hill | same | ✓ |
| 13 | 197–204 | 120C Old Canterbury Road | same | ✓ |

⚠ The extractor's D-numbers in refs are UNRELIABLE: 11 rows ref-labelled `D12` are
Part 10 (Edwards St) content by text location. Only text location was trusted.

## What was changed (backups in data/db_rollback_backups/)

1. **506 chapter-D rows backfilled** `v2_precinct_id='Part N'` — each row's body text
   located uniquely inside one Part's page range (start/mid/end probes, all must agree).
   `ashfield_precinct_backfill_2026-07-29.csv`. Boundaries now serve them geometrically.
2. **120 chapter-E2 rows backfilled** `v2_precinct_id='Haberfield'` — whole-document
   scope = Haberfield Neighbourhood; served via existing `dcp_precinct_localities`
   row (HABERFIELD → 'Haberfield') for addresses containing the suburb token; excluded
   elsewhere (was: served to every former-Ashfield address).
3. **198 legacy rows superseded** (`is_current=false`, NOT deleted) — parallel old
   extraction of the same chapter-D PDF (`...IWLEP_2022_amendments_Nov_22` document_id)
   with NULL ref_number/section_header; 133 of them carried 'Part N' ids and
   double-served alongside the new rows wherever a Part boundary matched. FK-checked
   (0 references). `ashfield_old_chapter_d_superseded_2026-07-29.csv`.

## SECOND WAVE (2026-07-29 pm) — cross-part rows RESOLVED

- **146 rows assigned directly** (`Part N`): full/heading/shingle text located only in one
  Part (`ashfield_crosspart_updates_2026-07-29.csv`).
- **113 boilerplate rows superseded and re-issued as 368 part-scoped copies** with refs
  `...__D<n> <clause>` (source repeats identical clause text per Part; each Part restarts
  its numbering, so per-part rows with Part-qualified refs mirror the adopted structure).
  Backups: `ashfield_crosspart_superseded_...csv` + `ashfield_crosspart_inserted_...csv`.
- **7 rows unresolvable** (ids 109994, 110264, 110270, 110280, 110281, 110295, 110487 —
  C1.1 table-synthesized text absent from the current PDF; likely pre-amendment). Still
  NULL → served council-wide; fix = chapter-D re-extraction.
- **⚠ UNDER-EXTRACTION DISCOVERED**: the current chapter-D extraction is missing ~60
  content chunks — ALL of Part 9 (Summer Hill Flour Mills, pp181-182) plus map-caption/
  table content across Parts 1-8. The 62 legacy rows carrying that content were RESTORED
  to is_current=true (`ashfield_legacy_part9_restored_2026-07-29.csv`) so it keeps serving
  (Part-tagged where known; 15 NULL). Proper fix = re-extraction of chapter D via the
  pipeline (fidelity gates), then supersede these again.
- **Incident + revert (self-inflicted, fixed within minutes)**: a coverage-restore query
  scoped by `document_id LIKE '%IWLEP_2022_amendments%'` matched legacy docs of ALL
  chapters and wrongly restored 1,125 historical rows; fully reverted from the backup CSV
  (`ashfield_legacy_restored_2026-07-29_REVERTED.csv`). Lesson: exact document_id lists,
  never LIKE, for is_current mutations.
- **Boundary names fixed**: 'Part 4' → 'Croydon Town Centre', 'Part 8' → 'SummerHill Town
  Centre' (source-verified; backup `ashfield_boundary_names_before_2026-07-29.csv`).
- **Part 5 / Part 11 boundaries — decision needed, NOT derived**: source application text
  says "areas zoned B1 - Neighbourhood Centre" (Part 5) and "land zoned IN2 Light
  Industrial" (Part 11) — pre-IWLEP-2022 zone codes even in the amended text. Deriving
  polygons needs the former-Ashfield extent + a B1→E1 / IN2→E4 translation; alternatively
  serve these rows via the existing v2_applicable_zones filter instead of geometry.
  Product decision before any of that.

## Remaining (NOT done — decisions/care needed)

- **266 chapter-D rows still NULL precinct** (still served council-wide):
  - ~250 "cross-part" rows: body text appears VERBATIM in multiple Parts (standard
    clauses repeated per part, e.g. 'Application of the Guideline' boilerplate,
    D1 C2–C7 matched all 12 part ranges). A single v2_precinct_id cannot represent
    them; options = (a) duplicate row per part, (b) multi-value column / join-table change,
    (c) leave NULL (council-wide; least wrong today since text genuinely recurs
    across parts). Decide model before acting.
  - 16 "no-match" rows (D1 DS1.2–DS2.11): text not found in the current PDF text
    layer (probably table content / reworded) — needs manual page-by-page check.
- **Part 5 + Part 11 have no boundaries** (B1 zones / industrial zones — these are
  ZONE-defined precincts; boundary = union of B1/industrial zone polygons from
  spatial_overlays could be derived, or serve via zone filter instead of geometry).
- **dcp_precinct_localities** rows for chapter-D names (ASHFIELD TOWN CENTRE etc.)
  still point at name-ids that match nothing → locality fallback for those tokens is
  inert (geometric matching covers Parts with boundaries). Suburb-shaped tokens that
  do fire: HABERFIELD (now correct), SUMMER HILL/HURLSTONE PARK/CAMPSIE/CANTERBURY
  (inert vs chapter D). Leave or re-point = product decision (re-pointing re-enables
  coarse suburb-level serving for parts whose polygons would have said "outside").
- **Boundary name drift**: 'Part 4' and 'Part 8' boundary precinct_name don't match
  the adopted Part names (see table). Display-only; fix when convenient.
- **Route defect (pre-existing)**: when locality matching passes precinct ids, the
  `precinct_warning` is suppressed even if the ids match nothing (filters.precinct_id
  set → warning skipped, layer filter `IS NULL OR = ANY(ids)`), and the
  no-precinct branch `v2_precinct_id IS NULL` is what serves NULL rows city-wide.

## Orphan boundaries — FULL enumeration (2026-07-29, post-backfill)

86 of 102 boundaries had zero current provisions; after the Part-N backfill, 75 remain:

- **Inner West Marrickville numeric (46)**: '1_'…'47_' (no '43_'). Marrickville
  provisions do NOT carry these ids (id-format drift hypothesis from 07-29 confirmed
  worth investigating: patterns file expects '9_XX' for provisions).
- **Inner West Leichhardt C2.2.x.y (29)**: all Distinctive Neighbourhood polygons.
- **Ku-ring-gai (10)**: 14B_T1–T4, 14I, 14J, 14K, 14L, 14N, 14O — NO ku_ring_gai
  provisions carry any v2_precinct_id → matched addresses silently get no precinct
  rules; the Ku-ring-gai precinct provisions presumably sit NULL-precinct and are
  served LGA-wide (same over-inclusion class — next candidate after CoS pattern).
- (Part 10 was un-orphaned by today's backfill.)
