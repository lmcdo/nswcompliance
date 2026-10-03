-- 081_applicability_declined.sql
--
-- WHY
-- ---
-- 062 split `['ALL']` into "a config decided this" and "nothing matched, so we
-- defaulted". Working through 40 DCP chapters on 2026-10-03 surfaced a THIRD
-- state that neither word fits, and writing it as `config_all` makes the column
-- assert something the council never said.
--
--   config_all      the chapter's own words are universal. Wollongong E6:
--                   "outlines Council's requirements for the lodgement of
--                   landscaping plans ... in support of a Development
--                   Application". Ku-ring-gai Part 21: "applies to all types of
--                   development". Blacktown Part C section 1.2(a): "both
--                   residential and non-residential development". These EARN it.
--
--   config_declined the chapter states a NARROWER scope, and this field cannot
--                   hold it without hiding the chapter from development it
--                   governs. A person read the chapter, and the honest act was
--                   to decline to narrow rather than to narrow wrongly:
--                     * Campbelltown Part 4 names six zones, FOUR of them codes
--                       the 2022 employment-zone reform retired, and B1
--                       Neighbourhood Centre and B2 Local Centre both map onto
--                       E1 — so the successor mapping is not one-to-one and
--                       belongs in zone-migration data with its own citation.
--                     * Wollongong B1 names seven development types and its
--                       section 4 also covers "ancillary structures"; fence,
--                       carport, pool and deck are all selectable in the DA
--                       scope input, so a five-term list deletes section 4 from
--                       each of them.
--                     * Waverley Part E and the Ku-ring-gai local centres are
--                       scoped to a MAPPED AREA, which a zone list cannot
--                       express at all.
--
--   config_silent   nobody decided. The key was simply omitted and
--                   `.get(k, ['ALL'])` invented the value.
--
-- The distinction is the whole point of the column. `config_all` is documented
-- as "a real assertion of universality; trust it", and
-- tests/test_campbelltown_applicability.py already refused to claim it for a
-- chapter that does not say it. Without this value the only ways to clear
-- DQ-114 were to assert universality falsely or to leave a read chapter
-- recorded as unread, and both corrupt the signal the effort exists to build.
--
-- WHAT IT IS NOT
-- --------------
-- Not a pass for DQ-115. A declined key must still carry the council's sentence
-- in `scope_evidence` saying WHAT could not be expressed — otherwise "declined"
-- becomes the new silent default, which is the failure this replaces.
--
-- SAFETY
-- ------
-- The CHECK is dropped and re-added with one more permitted value. No column is
-- altered, no row is rewritten, nothing is dropped, and no existing value
-- becomes invalid, so every row that satisfied the old constraint satisfies the
-- new one. Re-runnable: the DO block only acts when the constraint's definition
-- does not already permit the new value.
--
-- The served VALUE for a declined key is `['ALL']`, exactly as for
-- `config_silent` today, so applying this migration alone changes no answer. It
-- only widens what the column is allowed to say about why.

DO $$
DECLARE
  current_def text;
BEGIN
  SELECT pg_get_constraintdef(oid) INTO current_def
    FROM pg_constraint
   WHERE conname = 'regulatory_provisions_applicability_source_check'
     -- Scoped to the relation, not just the name: conname is unique per
     -- (table, name) and not globally, so a same-named constraint elsewhere
     -- must not make this think the work is done. 062 learned this.
     AND conrelid = 'public.regulatory_provisions'::regclass;

  IF current_def IS NULL THEN
    RAISE EXCEPTION
      'regulatory_provisions_applicability_source_check is missing — run 062 first';
  END IF;

  IF position('config_declined' IN current_def) > 0 THEN
    RAISE NOTICE '081: constraint already permits config_declined; nothing to do';
    RETURN;
  END IF;

  ALTER TABLE regulatory_provisions
    DROP CONSTRAINT regulatory_provisions_applicability_source_check;

  ALTER TABLE regulatory_provisions
    ADD CONSTRAINT regulatory_provisions_applicability_source_check
    CHECK (
      (v2_zone_source IS NULL OR v2_zone_source IN (
        'config_specific','config_all','config_declined','config_silent',
        'no_config','text_regex','filtered_to_all','no_document_id'))
      AND
      (v2_dev_type_source IS NULL OR v2_dev_type_source IN (
        'config_specific','config_all','config_declined','config_silent',
        'no_config','text_regex','filtered_to_all','no_document_id'))
    );
END $$;

COMMENT ON COLUMN regulatory_provisions.v2_zone_source IS
  'Why v2_applicable_zones holds what it does. NULL = tagged before provenance '
  'existed (origin unknown, NOT a pass). Trustworthy assertions: config_specific, '
  'config_all (the chapter''s own words are universal), config_declined (a person '
  'read the chapter, its stated scope cannot be expressed in this field without '
  'hiding rules, and narrowing was declined — the reason is in the config''s '
  'scope_evidence), text_regex. Undetermined: config_silent (nobody decided), '
  'no_config, no_document_id, filtered_to_all.';

COMMENT ON COLUMN regulatory_provisions.v2_dev_type_source IS
  'Why v2_applicable_dev_types holds what it does. Same vocabulary as '
  'v2_zone_source.';
