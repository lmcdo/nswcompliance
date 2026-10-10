-- 109: the LAND a site-specific LEP rule applies to, as a condition the Planning Portal can check (DQ-140).
-- RUN BEFORE the for-property route that selects this column is deployed: the route reads it directly,
-- so a deploy without it fails every provisions request (loudly, never by serving unfiltered rows).
--
-- Shape (enrichment/config/inner_west_lep_land.py `condition`):
--   {"layer": "Key Sites Map" | null, "labels": ["Area 19"] | null, "zones": ["E3","E4"] | null,
--    "verified": true, "source": "<the clause's own words>"}
-- NULL = the rule is not limited by land (the column says nothing). Populated by
-- scripts/apply_iw_lep_land_conditions.py; the filter is frontend-nextjs/lib/lep-land-condition.ts.
-- Additive and nullable: no existing row changes.

ALTER TABLE regulatory_provisions ADD COLUMN IF NOT EXISTS v2_land_condition jsonb;

COMMENT ON COLUMN regulatory_provisions.v2_land_condition IS
  'DQ-140: map layer + labels (+ zones) the lot must carry for this rule to apply; NULL = not land-limited';
