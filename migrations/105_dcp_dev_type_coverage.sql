-- 105: dcp_dev_type_coverage -- where a council's DCP does not (or only partly) set controls for a
-- housing type, recorded as a fact with its evidence, so the site can say so instead of a generic
-- "no value recorded -- verify against the DCP" (user request 2026-10-10: "the UI should reflect the
-- reality of the DCP, e.g. Liverpool has no dual occupancy").
--
-- A row is a READING FINDING, not a quote of the law: `statement` says what was found and in which
-- Parts, `evidence_quote` holds the DCP's own words where they exist (e.g. a Part's title limiting
-- its scope), `reviewed_at` dates the reading. Absence cannot be quoted, so a 'none' row may have no
-- quote; its statement names the Parts reviewed.
-- Read by services/constraint_arithmetic.py (_fetch_dcp_coverage) for the buildable-area gap text,
-- and by DQ-142, which counts a recorded 'none'/'partial' as decided rather than missing.

BEGIN;

CREATE TABLE IF NOT EXISTS dcp_dev_type_coverage (
    id             serial PRIMARY KEY,
    council        text NOT NULL,
    dev_type       text NOT NULL,
    coverage       text NOT NULL CHECK (coverage IN ('none', 'partial')),
    statement      text NOT NULL,
    evidence_quote text,
    evidence_url   text NOT NULL,
    evidence_page  integer,
    reviewed_at    date NOT NULL,
    is_current     boolean NOT NULL DEFAULT TRUE,
    UNIQUE (council, dev_type)
);

-- Rule data: never writable (or readable) by the public browser key (DQ-138).
REVOKE ALL ON dcp_dev_type_coverage FROM anon, authenticated;
ALTER TABLE dcp_dev_type_coverage ENABLE ROW LEVEL SECURITY;

INSERT INTO dcp_dev_type_coverage
  (council, dev_type, coverage, statement, evidence_quote, evidence_url, evidence_page, reviewed_at)
VALUES
  ('liverpool', 'dual_occupancy', 'none',
   'No Part of Liverpool DCP 2008 reviewed on 10 October 2026 sets dual occupancy controls. Its residential Parts cover dwelling houses (Parts 3.2, 3.5 and 8) and semi-detached and attached dwellings (Part 3.4).',
   NULL,
   'https://www.liverpool.nsw.gov.au/development/liverpools-planning-controls/liverpool-development-control-plan',
   NULL, DATE '2026-10-10'),
  ('ryde', 'dual_occupancy', 'partial',
   'Ryde DCP 2014 Part 3.3 sets these controls for attached dual occupancy only; no Part reviewed on 10 October 2026 sets them for detached dual occupancy.',
   'Dwelling Houses and Dual Occupancy (attached)',
   'https://www.ryde.nsw.gov.au/files/assets/public/development/dcp/dcp-2014-3.3-dwelling-houses-and-dual-occupancy.pdf',
   1, DATE '2026-10-10'),
  ('hornsby', 'secondary_dwelling', 'none',
   'Hornsby DCP 2024 Part 3 (Residential), reviewed on 10 October 2026, has no secondary dwelling section. The State Environmental Planning Policy (Housing) 2021 secondary dwelling standards are shown separately.',
   NULL,
   'https://www.hornsby.nsw.gov.au/Property/Building-and-development/Policies-and-guidelines/Hornsby-Development-Control-Plan',
   NULL, DATE '2026-10-10')
ON CONFLICT (council, dev_type) DO NOTHING;

DO $$
BEGIN
    IF (SELECT count(*) FROM dcp_dev_type_coverage WHERE is_current) < 3 THEN
        RAISE EXCEPTION '105: coverage rows missing';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.role_table_grants
                WHERE table_name = 'dcp_dev_type_coverage' AND grantee IN ('anon', 'authenticated')) THEN
        RAISE EXCEPTION '105: public roles still hold grants on dcp_dev_type_coverage';
    END IF;
END $$;

COMMIT;
