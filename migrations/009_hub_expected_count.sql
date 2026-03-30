BEGIN;

-- Migration 009: Add hub_expected_count to dcp_chapter_registry
-- council_page_url already exists and is populated with hub page URLs.
-- hub_expected_count is the baseline chapter count per council — used by the
-- anomaly gate in r2_monitor.py (abort if scrape returns <80% of expected).

ALTER TABLE dcp_chapter_registry
    ADD COLUMN IF NOT EXISTS hub_expected_count INTEGER;

-- Set expected counts for Inner West councils (confirmed chapter counts)
UPDATE dcp_chapter_registry SET hub_expected_count = 84 WHERE council = 'marrickville';
UPDATE dcp_chapter_registry SET hub_expected_count = 16 WHERE council = 'leichhardt';
UPDATE dcp_chapter_registry SET hub_expected_count = 10 WHERE council = 'ashfield';
UPDATE dcp_chapter_registry SET hub_expected_count = 15 WHERE council = 'woollahra';
UPDATE dcp_chapter_registry SET hub_expected_count = 1  WHERE council = 'waverley';
UPDATE dcp_chapter_registry SET hub_expected_count = 23 WHERE council = 'ku_ring_gai';
UPDATE dcp_chapter_registry SET hub_expected_count = 7  WHERE council = 'city_of_sydney';

COMMIT;
