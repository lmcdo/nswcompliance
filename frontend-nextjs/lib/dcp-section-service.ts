/**
 * DCP Section Service - LGA-Independent
 *
 * Dynamically detects DCP section structure from database
 * Works for ANY LGA without code changes
 */

import { Pool } from 'pg';

const pool = new Pool({
  host: process.env.PGHOST || process.env.DATABASE_HOST || 'localhost',
  port: parseInt(process.env.PGPORT || process.env.DATABASE_PORT || '5432'),
  database: process.env.PGDATABASE || process.env.DATABASE_NAME || 'nsw_planning',
  user: process.env.PGUSER || process.env.DATABASE_USER || 'postgres',
  password: process.env.PGPASSWORD || process.env.DATABASE_PASSWORD || '',
});

export interface DCPSection {
  sectionIdentifier: string;   // e.g., "F.1", "3.2", "Part A"
  sectionTitle: string;         // e.g., "Dwelling Houses"
  documentId: string;           // Full document ID
  lga: string;                  // Extracted LGA name
}

/**
 * Get DCP section for development type (LGA-independent)
 *
 * This queries the database to find the DCP section structure
 * Works automatically for Inner West, Canterbury-Bankstown, or any future LGA
 */
export async function getDCPSection(
  lga: string,
  developmentType: string
): Promise<DCPSection | null> {
  try {
    // Query database to find DCP section for this LGA + dev type
    // This works because provisions are tagged with development_type
    const query = `
      SELECT DISTINCT
        document_id,
        section_header,
        -- Extract section identifier (e.g., "F.1" from "F.1 Dwelling Houses")
        COALESCE(
          SUBSTRING(section_header FROM '^[A-Z]\\.\\d+'),           -- Matches "F.1"
          SUBSTRING(section_header FROM '^\\d+\\.\\d+'),            -- Matches "3.2"
          SUBSTRING(section_header FROM '^Part [A-Z]'),            -- Matches "Part A"
          ref_number                                                -- Fallback to ref_number
        ) as section_identifier
      FROM provisions_with_category
      WHERE document_category = 'DCP'
        AND development_type = $1
        AND (
          document_id ILIKE '%' || $2 || '%'                       -- Match LGA in document_id
          OR document_id ILIKE '%DCP%'                              -- Or any DCP if LGA not in name
        )
        AND section_header IS NOT NULL
        AND section_header != ''
      ORDER BY document_id DESC
      LIMIT 1
    `;

    const result = await pool.query(query, [developmentType, lga]);

    if (result.rows.length === 0) {
      // No specific section found - return generic
      return {
        sectionIdentifier: 'General',
        sectionTitle: 'General Development Controls',
        documentId: `${lga}_DCP`,
        lga
      };
    }

    const row = result.rows[0];

    return {
      sectionIdentifier: row.section_identifier || 'General',
      sectionTitle: row.section_header || 'General Development Controls',
      documentId: row.document_id,
      lga
    };

  } catch (error) {
    console.error('[DCP Section Service] Error:', error);

    // Fallback to generic section
    return {
      sectionIdentifier: 'General',
      sectionTitle: 'General Development Controls',
      documentId: `${lga}_DCP`,
      lga
    };
  }
}

/**
 * Get all available DCP sections for an LGA
 * Useful for building UI dropdowns or documentation
 */
export async function getAvailableDCPSections(lga: string): Promise<DCPSection[]> {
  try {
    const query = `
      SELECT DISTINCT
        development_type,
        document_id,
        section_header,
        COALESCE(
          SUBSTRING(section_header FROM '^[A-Z]\\.\\d+'),
          SUBSTRING(section_header FROM '^\\d+\\.\\d+'),
          SUBSTRING(section_header FROM '^Part [A-Z]'),
          ref_number
        ) as section_identifier
      FROM provisions_with_category
      WHERE document_category = 'DCP'
        AND development_type IS NOT NULL
        AND (
          document_id ILIKE '%' || $1 || '%'
          OR document_id ILIKE '%DCP%'
        )
        AND section_header IS NOT NULL
      ORDER BY development_type, section_identifier
    `;

    const result = await pool.query(query, [lga]);

    return result.rows.map(row => ({
      sectionIdentifier: row.section_identifier || 'General',
      sectionTitle: row.section_header || '',
      documentId: row.document_id,
      lga
    }));

  } catch (error) {
    console.error('[DCP Section Service] Error getting available sections:', error);
    return [];
  }
}

/**
 * Extract LGA name from property data or document ID
 * Handles various formats
 */
export function extractLGA(source: string): string {
  const lgaPatterns = [
    { pattern: /inner[_\s]west/i, name: 'Inner West' },
    { pattern: /canterbury[_\s-]?bankstown/i, name: 'Canterbury-Bankstown' },
    { pattern: /sydney/i, name: 'Sydney' },
    { pattern: /parramatta/i, name: 'Parramatta' },
    { pattern: /marrickville/i, name: 'Marrickville' },
    { pattern: /ashfield/i, name: 'Ashfield' },
    { pattern: /leichhardt/i, name: 'Leichhardt' },
    // Add more LGAs as needed
  ];

  for (const { pattern, name } of lgaPatterns) {
    if (pattern.test(source)) {
      return name;
    }
  }

  // Fallback: try to extract from string
  const match = source.match(/^([A-Za-z\s-]+)/);
  return match ? match[1].trim() : 'Unknown';
}