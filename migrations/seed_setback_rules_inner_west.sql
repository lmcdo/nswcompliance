-- Seed: Inner West DCP setback reference values for inline chips
-- Sources: Marrickville DCP 2011, Leichhardt DCP 2013, Ashfield Comprehensive DCP 2016
-- Purpose: Read-only reference chips in DA assessment UI (not compliance determination)
-- Confidence: manual_verified = false until checked against current DCP PDFs
-- Last reviewed: 2026-03

-- R2 Low Density Residential — Side setbacks
-- Marrickville DCP 2011 C11 (already seeded as example, added here for completeness with more context)
INSERT INTO setback_rules (
    ref_number, boundary_type, storey_level, building_element, zone, lga,
    setback_meters, qualifier, document_type, document_name, priority,
    source_text, extraction_method, extraction_confidence, notes
) VALUES
-- Marrickville R2 side setbacks
('C11', 'side', 'ground', 'main_dwelling', ARRAY['R2'], 'Inner West',
 0.9, 'minimum', 'DCP', 'Marrickville DCP 2011', 3,
 'Minimum side boundary setback for ground floor level in R2 Low Density Residential zone.',
 'manual', 0.95, 'Marrickville DCP 2011 Part C Section 2'),

('C11', 'side', 'first', 'main_dwelling', ARRAY['R2'], 'Inner West',
 1.5, 'minimum', 'DCP', 'Marrickville DCP 2011', 3,
 'Minimum side boundary setback for first floor level in R2 Low Density Residential zone.',
 'manual', 0.95, 'Marrickville DCP 2011 Part C Section 2'),

-- Leichhardt R2 side setbacks (Leichhardt DCP 2013 Part C)
('C-SD', 'side', 'ground', 'main_dwelling', ARRAY['R2'], 'Inner West',
 0.9, 'minimum', 'DCP', 'Leichhardt DCP 2013', 3,
 'Minimum side setback for single dwellings — ground floor, R2 zone.',
 'manual', 0.85, 'Leichhardt DCP 2013 Part C — needs verification against current PDF'),

('C-SD', 'side', 'first', 'main_dwelling', ARRAY['R2'], 'Inner West',
 1.5, 'minimum', 'DCP', 'Leichhardt DCP 2013', 3,
 'Minimum side setback for single dwellings — first floor, R2 zone.',
 'manual', 0.85, 'Leichhardt DCP 2013 Part C — needs verification against current PDF'),

-- Ashfield R2 side setbacks (Ashfield Comprehensive DCP 2016)
('B2', 'side', 'ground', 'main_dwelling', ARRAY['R2'], 'Inner West',
 0.9, 'minimum', 'DCP', 'Ashfield Comprehensive DCP 2016', 3,
 'Minimum side setback ground floor residential dwellings R2 zone.',
 'manual', 0.85, 'Ashfield DCP 2016 Part B — needs verification against current PDF'),

('B2', 'side', 'first', 'main_dwelling', ARRAY['R2'], 'Inner West',
 1.5, 'minimum', 'DCP', 'Ashfield Comprehensive DCP 2016', 3,
 'Minimum side setback first floor residential dwellings R2 zone.',
 'manual', 0.85, 'Ashfield DCP 2016 Part B — needs verification against current PDF'),

-- R2 Rear setbacks (common across Inner West DCPs)
('C11', 'rear', 'all', 'main_dwelling', ARRAY['R2'], 'Inner West',
 6.0, 'minimum', 'DCP', 'Marrickville DCP 2011', 3,
 'Minimum rear boundary setback for residential buildings in R2 zone. 6m is the standard Inner West minimum; may vary for secondary structures.',
 'manual', 0.80, 'Standard Inner West residential rear setback — verify per specific DCP and precinct'),

-- R2 Rear setbacks — secondary structures (garages, sheds)
('C11', 'rear', 'all', 'garage', ARRAY['R2'], 'Inner West',
 0.9, 'minimum', 'DCP', 'Marrickville DCP 2011', 3,
 'Minimum rear setback for garages and outbuildings. Minimum 900mm from rear boundary where no rear lane access.',
 'manual', 0.75, 'Verify — secondary structure rear setbacks vary; some precincts allow zero setback'),

-- R3 Medium Density — Side setbacks
('', 'side', 'ground', 'main_dwelling', ARRAY['R3'], 'Inner West',
 0.9, 'minimum', 'DCP', 'Marrickville DCP 2011', 3,
 'Minimum side setback for medium density residential development ground floor in R3 zone.',
 'manual', 0.75, 'R3 setbacks vary significantly by development type and DCP part — use with caution'),

('', 'side', 'first', 'main_dwelling', ARRAY['R3'], 'Inner West',
 1.5, 'minimum', 'DCP', 'Marrickville DCP 2011', 3,
 'Minimum side setback for medium density residential development first floor in R3 zone.',
 'manual', 0.75, 'R3 setbacks vary significantly by development type and DCP part — use with caution'),

-- R3 Rear setbacks
('', 'rear', 'all', 'main_dwelling', ARRAY['R3'], 'Inner West',
 6.0, 'minimum', 'DCP', 'Marrickville DCP 2011', 3,
 'Minimum rear setback for medium density residential development in R3 zone.',
 'manual', 0.75, 'Varies by DCP and development type — verify for specific project')

ON CONFLICT DO NOTHING;

-- Front setbacks intentionally omitted: Inner West DCPs use qualitative controls
-- ("maintain setback consistent with established streetscape pattern") rather than
-- hard numeric minimums. Front setbacks are not suitable for reference chip display.
-- Exception: specific precinct provisions may override — these should be added per precinct
-- when Track A (numeric extraction pipeline) completes.
