-- 074: dcp_clause_sibling_citations -- a rule published in more than one plan cites every plan it is in.
--
-- prior-art-checked: no citation or sibling-plan table exists (information_schema, 2026-09-15); the served
-- citation is built in scripts/conveyancing_db.cite_clause from dcp_setback_controls.section_ref alone.
--
-- Wingecarribee publishes its DCP as three town plans: Bowral, Mittagong and Moss Vale. Each applies to the land
-- edged on its own Figure A1.1 map, not to a suburb, so a property cannot be matched to its town plan without
-- guessing a boundary. The 30 served controls were read from the Bowral plan. On 2026-09-15 every one was found
-- under the same clause code, with the same numbers, in the Mittagong and Moss Vale plans -- at different pages,
-- and with the landscaping / site coverage table numbered C2.2 in Bowral but C2.1 in the other two.
--
-- One row per (council, chapter, clause, sibling plan): where the same clause sits in the sibling plan, and the
-- text of that page that was checked. The served citation then names every plan with its own clause and page.

CREATE TABLE IF NOT EXISTS dcp_clause_sibling_citations (
    id                  bigserial   PRIMARY KEY,
    council             text        NOT NULL,
    chapter_key         text        NOT NULL,
    section_ref         text        NOT NULL,
    sibling_chapter_key text        NOT NULL,
    sibling_section_ref text        NOT NULL,
    sibling_pdf_page    integer     NOT NULL CHECK (sibling_pdf_page > 0),
    sibling_excerpt     text        NOT NULL CHECK (btrim(sibling_excerpt) <> ''),
    verified_note       text        NOT NULL CHECK (btrim(verified_note) <> ''),
    created_at          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT dcp_clause_sibling_citations_one_per_sibling
        UNIQUE (council, chapter_key, section_ref, sibling_chapter_key),
    CONSTRAINT dcp_clause_sibling_citations_not_itself
        CHECK (sibling_chapter_key <> chapter_key)
);

COMMENT ON TABLE dcp_clause_sibling_citations IS
    'Where a cited DCP clause also appears, word for word with the same numbers, in a sibling plan of the same '
    'council (Wingecarribee town plans). Read by scripts/conveyancing_db.fetch_dcp_setbacks so a served number cites '
    'every plan it is published in, each at its own clause and page; counted by DQ-66.';
COMMENT ON COLUMN dcp_clause_sibling_citations.sibling_pdf_page IS
    'Page index in the sibling plan''s PDF (1-based), the same convention as dcp_setback_controls.pdf_page.';
COMMENT ON COLUMN dcp_clause_sibling_citations.sibling_excerpt IS
    'The sibling page''s own text from the clause code onward, as checked; every number of every served control '
    'citing this clause occurs in it.';
