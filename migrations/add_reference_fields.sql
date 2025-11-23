-- Add reference fields to dcp_general_requirements table
-- These capture tables, figures, section cross-refs, LEP refs, and SEPP refs

-- Table references (15% frequency)
ALTER TABLE dcp_general_requirements
ADD COLUMN IF NOT EXISTS references_table BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS table_location TEXT,
ADD COLUMN IF NOT EXISTS table_page INTEGER;

-- Figure/Diagram references (30% frequency)
ALTER TABLE dcp_general_requirements
ADD COLUMN IF NOT EXISTS references_figure BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS figure_number TEXT,
ADD COLUMN IF NOT EXISTS figure_description TEXT,
ADD COLUMN IF NOT EXISTS figure_page INTEGER;

-- Section cross-references (50% frequency)
ALTER TABLE dcp_general_requirements
ADD COLUMN IF NOT EXISTS references_section BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS section_reference TEXT,
ADD COLUMN IF NOT EXISTS section_title TEXT;

-- LEP/Map references (13% frequency)
ALTER TABLE dcp_general_requirements
ADD COLUMN IF NOT EXISTS references_lep BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS lep_document TEXT,
ADD COLUMN IF NOT EXISTS lep_clause TEXT,
ADD COLUMN IF NOT EXISTS lep_map_type TEXT;

-- SEPP references (3% frequency)
ALTER TABLE dcp_general_requirements
ADD COLUMN IF NOT EXISTS references_sepp BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS sepp_name TEXT,
ADD COLUMN IF NOT EXISTS sepp_clause TEXT;

-- Create indexes for filtering
CREATE INDEX IF NOT EXISTS idx_dgr_references_table ON dcp_general_requirements(references_table) WHERE references_table = TRUE;
CREATE INDEX IF NOT EXISTS idx_dgr_references_figure ON dcp_general_requirements(references_figure) WHERE references_figure = TRUE;
CREATE INDEX IF NOT EXISTS idx_dgr_references_section ON dcp_general_requirements(references_section) WHERE references_section = TRUE;
CREATE INDEX IF NOT EXISTS idx_dgr_references_lep ON dcp_general_requirements(references_lep) WHERE references_lep = TRUE;
CREATE INDEX IF NOT EXISTS idx_dgr_references_sepp ON dcp_general_requirements(references_sepp) WHERE references_sepp = TRUE;

-- Comments
COMMENT ON COLUMN dcp_general_requirements.references_table IS 'Whether requirement references a table';
COMMENT ON COLUMN dcp_general_requirements.table_location IS 'Description of table location (e.g., "following table", "Table 1")';
COMMENT ON COLUMN dcp_general_requirements.table_page IS 'PDF page number where table appears';

COMMENT ON COLUMN dcp_general_requirements.references_figure IS 'Whether requirement references a figure/diagram';
COMMENT ON COLUMN dcp_general_requirements.figure_number IS 'Figure number (e.g., "5", "3.2")';
COMMENT ON COLUMN dcp_general_requirements.figure_description IS 'Description of figure if provided in text';
COMMENT ON COLUMN dcp_general_requirements.figure_page IS 'PDF page number where figure appears';

COMMENT ON COLUMN dcp_general_requirements.references_section IS 'Whether requirement references another DCP section';
COMMENT ON COLUMN dcp_general_requirements.section_reference IS 'Section reference (e.g., "Section 2.9", "Part 4")';
COMMENT ON COLUMN dcp_general_requirements.section_title IS 'Title of referenced section if provided';

COMMENT ON COLUMN dcp_general_requirements.references_lep IS 'Whether requirement references LEP';
COMMENT ON COLUMN dcp_general_requirements.lep_document IS 'LEP document name (e.g., "MLEP 2011", "Inner West LEP 2022")';
COMMENT ON COLUMN dcp_general_requirements.lep_clause IS 'Specific LEP clause if mentioned';
COMMENT ON COLUMN dcp_general_requirements.lep_map_type IS 'Type of LEP map (e.g., "Height of Buildings", "FSR Map")';

COMMENT ON COLUMN dcp_general_requirements.references_sepp IS 'Whether requirement references SEPP';
COMMENT ON COLUMN dcp_general_requirements.sepp_name IS 'SEPP name (e.g., "Affordable Rental Housing SEPP 2009")';
COMMENT ON COLUMN dcp_general_requirements.sepp_clause IS 'Specific SEPP clause if mentioned';
