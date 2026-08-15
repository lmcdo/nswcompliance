-- Populate Common Planning Definitions
-- Add frequently-queried terms missing from regulatory_definitions table
--
-- Source: NSW Planning Portal, SEPP glossaries, common planning terminology
-- Date: 2026-02-01

-- Check if terms already exist before inserting
DO $$
BEGIN
    -- BASIX (Building Sustainability Index)
    IF NOT EXISTS (SELECT 1 FROM regulatory_definitions WHERE term_normalized = 'basix') THEN
        INSERT INTO regulatory_definitions (
            term, term_normalized, definition_text, definition_summary,
            source_document, legislation_type
        ) VALUES (
            'BASIX',
            'basix',
            'Building Sustainability Index (BASIX) is an online assessment tool that measures the potential environmental performance of residential buildings. BASIX requires applicants to meet water, thermal comfort and energy targets by incorporating sustainable design features.',
            'Online assessment tool for sustainable residential building design',
            'SEPP (Building Sustainability Index: BASIX) 2004',
            'SEPP'
        );
    END IF;

    -- FSR (Floor Space Ratio)
    IF NOT EXISTS (SELECT 1 FROM regulatory_definitions WHERE term_normalized = 'fsr' OR term_normalized = 'floor space ratio') THEN
        INSERT INTO regulatory_definitions (
            term, term_normalized, definition_text, definition_summary,
            source_document, legislation_type
        ) VALUES (
            'Floor Space Ratio',
            'floor space ratio',
            'Floor Space Ratio (FSR) is the ratio of the gross floor area of all buildings on a site to the area of that site. For example, an FSR of 1:1 means the total floor area of buildings equals the site area. FSR controls building bulk and density.',
            'Ratio of total floor area to site area (controls density)',
            'Standard Instrument LEP',
            'LEP'
        );
    END IF;

    -- FSR abbreviation
    IF NOT EXISTS (SELECT 1 FROM regulatory_definitions WHERE term_normalized = 'fsr') THEN
        INSERT INTO regulatory_definitions (
            term, term_normalized, definition_text, definition_summary,
            source_document, legislation_type
        ) VALUES (
            'FSR',
            'fsr',
            'Abbreviation for Floor Space Ratio. See "Floor Space Ratio" for full definition.',
            'Abbreviation for Floor Space Ratio',
            'Standard Instrument LEP',
            'LEP'
        );
    END IF;

    -- CDC (Complying Development Certificate)
    IF NOT EXISTS (SELECT 1 FROM regulatory_definitions WHERE term_normalized = 'cdc' OR term_normalized = 'complying development certificate') THEN
        INSERT INTO regulatory_definitions (
            term, term_normalized, definition_text, definition_summary,
            source_document, legislation_type
        ) VALUES (
            'Complying Development Certificate',
            'complying development certificate',
            'A Complying Development Certificate (CDC) is a combined planning and construction approval for development that meets specific pre-determined criteria. CDCs are faster and cheaper than Development Applications (DA) but are only available for eligible development types that comply with all applicable development standards.',
            'Fast-track approval for development meeting specific criteria',
            'SEPP (Exempt and Complying Development Codes) 2008',
            'SEPP'
        );
    END IF;

    -- CDC abbreviation
    IF NOT EXISTS (SELECT 1 FROM regulatory_definitions WHERE term_normalized = 'cdc') THEN
        INSERT INTO regulatory_definitions (
            term, term_normalized, definition_text, definition_summary,
            source_document, legislation_type
        ) VALUES (
            'CDC',
            'cdc',
            'Abbreviation for Complying Development Certificate. See "Complying Development Certificate" for full definition.',
            'Abbreviation for Complying Development Certificate',
            'SEPP (Exempt and Complying Development Codes) 2008',
            'SEPP'
        );
    END IF;

    -- DA (Development Application)
    IF NOT EXISTS (SELECT 1 FROM regulatory_definitions WHERE term_normalized = 'da' OR term_normalized = 'development application') THEN
        INSERT INTO regulatory_definitions (
            term, term_normalized, definition_text, definition_summary,
            source_document, legislation_type
        ) VALUES (
            'Development Application',
            'development application',
            'A Development Application (DA) is a formal request to a consent authority (usually council) for permission to carry out development. The DA must demonstrate compliance with applicable planning controls and may require community consultation, assessment against design guidelines, and consideration of environmental impacts.',
            'Formal application for development consent from council',
            'Environmental Planning and Assessment Act 1979',
            'LEP'
        );
    END IF;

    -- DA abbreviation
    IF NOT EXISTS (SELECT 1 FROM regulatory_definitions WHERE term_normalized = 'da') THEN
        INSERT INTO regulatory_definitions (
            term, term_normalized, definition_text, definition_summary,
            source_document, legislation_type
        ) VALUES (
            'DA',
            'da',
            'Abbreviation for Development Application. See "Development Application" for full definition.',
            'Abbreviation for Development Application',
            'Environmental Planning and Assessment Act 1979',
            'LEP'
        );
    END IF;

    -- GFA (Gross Floor Area)
    IF NOT EXISTS (SELECT 1 FROM regulatory_definitions WHERE term_normalized = 'gfa' OR term_normalized = 'gross floor area') THEN
        INSERT INTO regulatory_definitions (
            term, term_normalized, definition_text, definition_summary,
            source_document, legislation_type
        ) VALUES (
            'Gross Floor Area',
            'gross floor area',
            'Gross Floor Area (GFA) is the total floor area of a building, measured from the external walls. GFA includes all floor levels and is used to calculate Floor Space Ratio (FSR). Certain areas may be excluded from GFA calculations depending on the specific LEP (e.g., car parking, plant rooms, basement storage).',
            'Total floor area measured from external walls',
            'Standard Instrument LEP',
            'LEP'
        );
    END IF;

    -- Site Area
    IF NOT EXISTS (SELECT 1 FROM regulatory_definitions WHERE term_normalized = 'site area') THEN
        INSERT INTO regulatory_definitions (
            term, term_normalized, definition_text, definition_summary,
            source_document, legislation_type
        ) VALUES (
            'Site Area',
            'site area',
            'Site area is the total area of land on which development is proposed, measured in square metres. For FSR calculations, site area is the denominator. Site area typically excludes public roads but includes private access ways and driveways within the lot boundary.',
            'Total area of the development site in square metres',
            'Standard Instrument LEP',
            'LEP'
        );
    END IF;

    -- Habitable Room
    IF NOT EXISTS (SELECT 1 FROM regulatory_definitions WHERE term_normalized = 'habitable room') THEN
        INSERT INTO regulatory_definitions (
            term, term_normalized, definition_text, definition_summary,
            source_document, legislation_type
        ) VALUES (
            'Habitable Room',
            'habitable room',
            'A habitable room is a room used for living purposes including bedrooms, living rooms, dining rooms, studies, and kitchens (but not bathrooms, toilets, laundries, pantries, or corridors). Habitable rooms have specific requirements for natural light, ventilation, ceiling height, and minimum dimensions in DCPs and building codes.',
            'Room used for living (bedroom, living room, kitchen)',
            'Building Code of Australia',
            'DCP'
        );
    END IF;

    -- Setback
    IF NOT EXISTS (SELECT 1 FROM regulatory_definitions WHERE term_normalized = 'setback') THEN
        INSERT INTO regulatory_definitions (
            term, term_normalized, definition_text, definition_summary,
            source_document, legislation_type
        ) VALUES (
            'Setback',
            'setback',
            'A setback is the minimum distance required between a building and a property boundary (front, side, or rear). Setbacks ensure adequate separation between buildings, provide space for landscaping, protect privacy, maintain streetscape character, and allow for building maintenance access. Setback requirements vary by zone, building height, and lot characteristics (e.g., corner lots).',
            'Minimum distance between building and property boundary',
            'Development Control Plan',
            'DCP'
        );
    END IF;

    -- Building Height
    IF NOT EXISTS (SELECT 1 FROM regulatory_definitions WHERE term_normalized = 'building height') THEN
        INSERT INTO regulatory_definitions (
            term, term_normalized, definition_text, definition_summary,
            source_document, legislation_type
        ) VALUES (
            'Building Height',
            'building height',
            'Building height is the vertical distance from natural ground level to the highest point of the building (excluding minor structures like chimneys, vents, or aerials). Height limits are specified in metres or storeys in the LEP Height of Buildings Map and aim to control building scale, overshadowing, and visual impact.',
            'Vertical distance from ground to highest building point',
            'Standard Instrument LEP - Clause 4.3',
            'LEP'
        );
    END IF;

    -- TOD (Transport Oriented Development)
    IF NOT EXISTS (SELECT 1 FROM regulatory_definitions WHERE term_normalized = 'tod' OR term_normalized = 'transport oriented development') THEN
        INSERT INTO regulatory_definitions (
            term, term_normalized, definition_text, definition_summary,
            source_document, legislation_type
        ) VALUES (
            'Transport Oriented Development',
            'transport oriented development',
            'Transport Oriented Development (TOD) refers to higher-density mixed-use development within walking distance (typically 400-800m) of high-frequency public transport. SEPP (Housing) 2021 provides planning incentives (increased height and FSR) for residential development in mapped TOD areas near train stations, light rail, and major bus interchanges.',
            'Higher-density development near high-frequency transport',
            'SEPP (Housing) 2021 - Part 4',
            'SEPP'
        );
    END IF;

    -- Heritage Item
    IF NOT EXISTS (SELECT 1 FROM regulatory_definitions WHERE term_normalized = 'heritage item') THEN
        INSERT INTO regulatory_definitions (
            term, term_normalized, definition_text, definition_summary,
            source_document, legislation_type
        ) VALUES (
            'Heritage Item',
            'heritage item',
            'A heritage item is a building, work, place, relic, tree, or object identified as having heritage significance and listed in Schedule 5 of the LEP. Development affecting heritage items requires heritage consent and must demonstrate that the proposal conserves the heritage significance of the item. Heritage items have additional controls for alterations, demolition, and new development.',
            'Place or object of heritage significance listed in LEP Schedule 5',
            'Standard Instrument LEP - Clause 5.10',
            'LEP'
        );
    END IF;

END $$;

-- Verify insertions
SELECT
    COUNT(*) FILTER (WHERE term_normalized IN ('basix', 'fsr', 'floor space ratio')) as planning_tools,
    COUNT(*) FILTER (WHERE term_normalized IN ('cdc', 'complying development certificate', 'da', 'development application')) as approvals,
    COUNT(*) FILTER (WHERE term_normalized IN ('gfa', 'gross floor area', 'site area', 'habitable room')) as measurements,
    COUNT(*) FILTER (WHERE term_normalized IN ('setback', 'building height')) as controls,
    COUNT(*) FILTER (WHERE term_normalized IN ('tod', 'transport oriented development', 'heritage item')) as special_areas,
    COUNT(*) as total_new_definitions
FROM regulatory_definitions
WHERE term_normalized IN (
    'basix', 'fsr', 'floor space ratio', 'cdc', 'complying development certificate',
    'da', 'development application', 'gfa', 'gross floor area', 'site area',
    'habitable room', 'setback', 'building height', 'tod', 'transport oriented development',
    'heritage item'
);
