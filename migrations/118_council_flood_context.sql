-- 118: what flood information each council makes public, so the flood answer can
-- tell a user where to go when we cannot answer ("not known") — e.g. Newcastle:
-- a public flood viewer and a paid Flood Information Certificate; its flood
-- planning level wording; its online layers show hazard and PMF, not the
-- planning line.
--
-- Every fact carries its source URL and the date it was checked. Nothing here is
-- typed into code: rows are researched (2026-10-29, read-only web research) and
-- loaded by scripts/load_council_flood_context.py. A NULL field means "not found",
-- never "does not exist".
--
-- Owner approval: 2026-10-29 ("yes db"). Read only by the backend; no public
-- browser role can write it (migration 110 default) and row level security is on.

CREATE TABLE IF NOT EXISTS public.council_flood_context (
    lga_name          text PRIMARY KEY,          -- spatial_overlays.lga_name naming (e.g. 'NEWCASTLE')
    viewer_label      text,
    viewer_url        text,
    certificate_label text,
    certificate_url   text,
    certificate_fee   text,                      -- verbatim from the council page, if stated
    fpl_quote         text,                      -- flood planning level wording, verbatim
    fpl_url           text,
    layers_note       text,                      -- what its public online flood layers show
    data_sources      jsonb NOT NULL DEFAULT '[]'::jsonb,  -- [{label,url,licence}]
    notes             text,
    checked_on        date NOT NULL,
    updated_at        timestamptz NOT NULL DEFAULT now()
);

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.council_flood_context FROM anon, authenticated;
ALTER TABLE public.council_flood_context ENABLE ROW LEVEL SECURITY;
