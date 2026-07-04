-- 055: fidelity-gated review — store per-row source-grounding so a reviewer sees only the
-- rules the source check FLAGGED, and clears the source-grounded rest with evidence rather
-- than eyeballing thousands blind.
--
-- Populated at extraction time by the grounding check (reuses verify_extraction_fidelity):
--   fidelity_status     'grounded' -> every number + the distinctive words appear in the
--                                     source chapter PDF (low risk; bulk-approvable);
--                       'flagged'  -> a number or a block of words is NOT in the source
--                                     (route to a human);
--                       NULL       -> not yet checked (legacy rows / no source PDF).
--   fidelity_detail     human-readable reason for a flag (e.g. "18.5 not in source").
--   source_page_verified  the real PDF page, found by matching the provision text to a
--                         page (the AI's own page number resets per chunk and is
--                         unreliable). Set ONLY on a CONFIDENT match; left NULL when the
--                         page match is ambiguous (~23% — repeated/short/straddling rules),
--                         so we never store a guessed page.
--
-- All three are nullable and additive. The commit gate and every existing query are
-- unaffected (they don't read these columns). Safe to re-run.

ALTER TABLE dcp_review_queue
    ADD COLUMN IF NOT EXISTS fidelity_status      TEXT,
    ADD COLUMN IF NOT EXISTS fidelity_detail      TEXT,
    ADD COLUMN IF NOT EXISTS source_page_verified INTEGER;

COMMENT ON COLUMN dcp_review_queue.fidelity_status IS
    'Source-grounding result: grounded = all numbers + key words found in the source PDF '
    '(bulk-approvable); flagged = something not in source (human review); NULL = unchecked.';
COMMENT ON COLUMN dcp_review_queue.source_page_verified IS
    'Real PDF page found by text-matching the provision (the AI page number resets per '
    'chunk). Set only on a confident match; NULL when the page match is ambiguous.';
