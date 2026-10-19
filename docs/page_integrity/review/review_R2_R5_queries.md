# R2/R5 queries (read-only, prod, 2026-10-19; worktree 55ccc875, origin/main 97110bc0, no diff in reviewed code)

Served dcp_setback_controls = `is_current AND NOT coalesce(needs_review,false)` -> 963 (of 1,273 rows).

```sql
-- structured columns populated
SELECT count(*) FILTER (WHERE cardinality(zones_include)>0) zinc,   -- 36
       count(*) FILTER (WHERE cardinality(zones_exclude)>0) zexc    -- 5
FROM dcp_setback_controls WHERE is_current AND NOT coalesce(needs_review,false);

-- condition text carrying a scope qualifier (any of the regex families below) -> 371
-- families: storey 136, corner/street 78, lot tier 137, housing type 76, site feature 24 (overlapping)
SELECT count(*) FROM dcp_setback_controls
WHERE is_current AND NOT coalesce(needs_review,false)
 AND condition ~* '(storey|story|upper (floor|level)|ground (floor|level)|first floor|second floor|wall height|attic|corner|secondary street|side street|primary street|laneway|rear lane|battle|classified|state road|regional road|arterial|lot (size|area|width|frontage)|site (area|width|frontage)|[0-9]+ ?(m2|m²|sqm)|terrace|dual occ|multi.?dwelling|semi|attached|detached|apartment|residential flat|boarding|secondary dwelling|granny|shop.?top|manor|townhouse|villa)';
-- of those 371: no zone columns 352; applicability='universal_residential' 245

-- applicability enum: universal_residential 705, zone_specific 105, development_specific 63, secondary_dwelling_specific 52, sepp_cdc_only 19, sepp_statewide 12, precinct_specific 7
```

```sql
-- (b) served set
SELECT count(*), count(*) FILTER (WHERE v2_applicable_dev_types IS NULL),
       count(*) FILTER (WHERE v2_applicable_dev_types=ARRAY['ALL'])
FROM regulatory_provisions WHERE is_current AND v2_is_actionable;   -- 61362, 0, 56959

SELECT v2_dev_type_source, count(*),
 count(*) FILTER (WHERE provision_text ~* '(dual occupanc|secondary dwelling|granny flat|terrace|semi.?detached|boarding house|manor house|shop.?top)')
FROM regulatory_provisions WHERE is_current AND v2_is_actionable AND v2_applicable_dev_types=ARRAY['ALL'] GROUP BY 1;
-- config_all 47746/1538; no_config 4622/82; config_declined 3969/268; NULL 622/179  (total narrow 2067)
-- broad housing-type regex (adds multi-dwelling, apartment, RFB, dwelling house, seniors, townhouse): 3965
```
Note: the task's "served = is_current AND v2_is_actionable" gives 61,362 now (CLAUDE.md quotes 19,957 as of 2026-08-08; stale).

R5 SQL identifier sweep: scripts parsed backticked SQL in app/api/**.ts, compared FROM/JOIN names and alias.column refs to information_schema (public). Missing tables: dcp_general_provisions, dcp_general_requirements, requirement_feedback (requirement_votes also unverified). Missing columns: regulatory_provisions.former_council; housing_sepp_standards.dwelling_type/notes/is_current. Other heuristic hits were CTE/aggregate aliases (false positives).
