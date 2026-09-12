-- 070_chapter_measurement_attribution.sql
--
-- Signal 5: section attribution collapse.
--
-- WHY THIS EXISTS
-- ---------------
-- Marrickville's dominant cause, proven 2026-09-12, and invisible to the four
-- signals 069 already records.
--
-- marrickville/part2-s25-stormwater serves 40 rows and its document lists 19
-- sections. Every one of those 40 rows is stamped "2.25 Stormwater Management"
-- with a control marker (C5, C9, C10, C17, C24, C29 ...). The 19 real
-- sub-sections -- 2.25.1, 2.25.2, 2.25.3, 2.25.3.1 through 2.25.3.14 -- are
-- collapsed into their parent, so not one of them can be retrieved.
--
-- Signal 1 calls that chapter INCOMPLETE, which is true but reads as "the
-- content is missing". It is not missing: the capture ratio is 1.0, every
-- character is stored. It is UNREACHABLE, because the sub-section level was
-- never recorded. The repair for absent content is a re-extraction; the repair
-- for collapsed attribution is a prompt/parse change. Recording them under one
-- verdict would send both to the wrong fix.
--
-- Measured separation is clean rather than chosen: collapsed chapters store
-- 5-21% of their listed sections, healthy ones 85-91%. The threshold sits in
-- the empty gap between those clusters.
--
-- Corpus-wide at the time of writing: 59 chapters. marrickville 48,
-- ku_ring_gai 5, canterbury_bankstown 3, leichhardt 1, waverley 1, woollahra 1.
--
-- WHY NOT FOLDED INTO capture_verdict OR contents_verdict
-- ------------------------------------------------------
-- Both already answer a different question. capture_verdict asks whether the
-- TEXT arrived; for these chapters it did. contents_verdict asks whether the
-- SECTIONS arrived; it reports them absent. Only this column distinguishes
-- "absent" from "present but unaddressable", and that distinction is the whole
-- reason marrickville's 75 incomplete chapters were one mystery instead of two
-- separate, separately-fixable defects.
--
-- NO_STORED_CODES is deliberately its own value and NOT folded into COLLAPSED.
-- A chapter whose rows carry no parseable code at all (woollahra: 24 chapters,
-- 547 rows) is a different defect from one whose rows all carry the SAME code.
-- Folding them together reported 98 collapsed chapters where there are 59.

BEGIN;

ALTER TABLE dcp_chapter_measurement
  ADD COLUMN IF NOT EXISTS attribution_verdict TEXT,
  ADD COLUMN IF NOT EXISTS attribution_ratio   NUMERIC;

COMMENT ON COLUMN dcp_chapter_measurement.attribution_verdict IS
  'COLLAPSED = the rows are stored under far fewer section codes than the document lists, so the sections exist in the text but cannot be retrieved. ATTRIBUTED = fine. NO_STORED_CODES = no parseable code at all, a different defect. TOO_FEW_* = not judgeable.';
COMMENT ON COLUMN dcp_chapter_measurement.attribution_ratio IS
  'distinct stored section codes / sections listed on the contents page. Measured 2026-09-12: collapsed chapters sit at 0.05-0.21, healthy ones at 0.85-0.91.';

COMMIT;
