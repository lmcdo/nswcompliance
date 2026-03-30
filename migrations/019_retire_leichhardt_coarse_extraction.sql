-- Migration 019: Retire coarse Leichhardt extraction and tag old extraction with source_council
--
-- Background:
-- Two separate Leichhardt DCP 2013 extractions exist simultaneously with is_current = TRUE:
--
-- OLD extraction (keep): document_ids like "Leichhardt DCP 2013 - N - Part X ..."
--   - 1444 provisions, source_council = NULL
--   - Correct v2_dcp_part values ('Part C Section 1', 'Part G', etc.)
--   - Proper provision-level granularity: ~516 individual provisions for Part C Section 1
--   - Correct C-marker grouping (v2_marker = C1, C2...) for sidebar sub-sections
--
-- NEW extraction (retire): document_ids like "Leichhardt_DCP_2013__part_c_s1_general" (double underscore)
--   - 508 provisions, source_council = 'leichhardt'
--   - v2_dcp_part = 'unknown' for ALL provisions (tagger doesn't handle underscore doc_id format)
--   - Coarse section-level granularity: 62 provisions bundle entire C1.1/C1.2/... sections into one block
--   - Includes TOC page entries (page 2, "# C1.11 PARKING .........." text)
--   - Zero text overlap with old extraction — genuinely different extraction quality, not duplicate rows
--
-- Effect:
-- Retiring new extraction removes 508 provisions. Remaining 1444 (old) cover Parts A, C, D, E, F, G.
-- Lost: Part B (18 provisions, intro/connections) and appendix (25 provisions) — non-essential.
-- After source_council fix, validate_toc_join.py and TOC JOIN validation cover all 1444 provisions.

-- ── Step 1: Retire new (coarse) extraction ────────────────────────────────────────────────────────
-- Targets: document_id starting with "Leichhardt_DCP_2013__" (double underscore after year)
-- These were extracted with wrong granularity and have v2_dcp_part = 'unknown' throughout.

UPDATE regulatory_provisions
SET is_current = FALSE
WHERE document_id LIKE 'Leichhardt\_DCP\_2013\_\_%' ESCAPE '\'
  AND source_council = 'leichhardt';

-- ── Step 2: Tag old extraction with source_council ────────────────────────────────────────────────
-- Old extraction provisions have source_council = NULL.
-- Setting 'leichhardt' makes them visible to source_council-based queries and validate_toc_join.py.
-- Applies to all provisions (is_current TRUE and FALSE) for historical accuracy.

UPDATE regulatory_provisions
SET source_council = 'leichhardt'
WHERE document_id ILIKE '%Leichhardt%'
  AND source_council IS NULL;
