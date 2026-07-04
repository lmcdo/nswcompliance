-- 056: store, for a FLAGGED review row, the sentence from the source PDF that the flagged
-- number/word should have matched — so the reviewer sees "the source says X" without opening
-- the PDF and hunting. Populated by dcp_fidelity_gate; nullable and additive.
ALTER TABLE dcp_review_queue
    ADD COLUMN IF NOT EXISTS fidelity_source_quote TEXT;

COMMENT ON COLUMN dcp_review_queue.fidelity_source_quote IS
    'For a flagged row, the best-matching sentence from the source PDF (what the source '
    'actually says), so a reviewer can resolve the flag at a glance instead of opening the PDF.';
