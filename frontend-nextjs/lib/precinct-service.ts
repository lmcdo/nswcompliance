/**
 * Precinct Mapping Service
 * Maps addresses to DCP precincts for location-specific controls
 */

import { Pool } from 'pg';

const pool = new Pool({
  host: 'localhost',
  port: 5432,
  database: 'nsw_planning',
  user: 'postgres',
  password: 'postgres'
});

export interface PrecinctMapping {
  precinctNumber: string;
  precinctName: string;
  documentId: string;
  lga: string;
}

/**
 * Marrickville precinct street mappings
 * Extracted from DCP boundary descriptions
 */
const MARRICKVILLE_PRECINCT_STREETS: Record<string, string[]> = {
  '9_1': ['West Street', 'Thomas Street'],
  '9_3': ['Crystal Street', 'Parramatta Road', 'Kingston Road'],
  '9_4': ['Parramatta Road', 'Church Street'],
  '9_8': ['Liberty Street', 'Station Street', 'Enmore Road'],
  '9_9': ['Stanmore Road', 'Enmore Road', 'Albert Street'],
  '9_10': ['Old Canterbury Road', 'Constitution Road'],
  '9_11': ['New Canterbury Road'],
  '9_18': ['Wardell Road', 'Marrickville Road', 'New Canterbury Road'],
  '9_20': ['Livingstone Road', 'Sydenham Road', 'Victoria Road'],
  '9_21': ['Livingstone Road', 'Marrickville Road', 'Wardell Road'],
  '9_23': ['Livingstone Road', 'Arthur Street', 'Petersham Road'],
  '9_24': ['Meeks Road'],
  '9_26': ['Barwon Park Road', 'Campbell Street'],
  '9_27': ['Campbell Street', 'Albert Street'],
  '9_28': ['Illawarra Road', 'Hill Street', 'Wallace Street'],  // South section
  '9_29': ['Harnett Avenue', 'Illawarra Road', 'Hill Street', 'Livingstone Road'],
  '9_30': ['Illawarra Road', 'Carrington Road', 'Renwick Street', 'Warren Road', 'Excelsior Parade'],  // The Warren
  '9_32': ['Collins Street', 'Union Street'],
  '9_33': ['Campbell Street', 'Holbeach Avenue'],
  '9_34': ['Smith Street', 'Holbeach Avenue'],
  '9_37': ['King Street', 'Enmore Road'],  // Commercial precinct
  '9_38': ['Dulwich Hill'],  // Commercial precinct
  '9_39': ['Victoria Road', 'Murray Street', 'Edgeware Road'],
  '9_42': ['Parramatta Road', 'Derby Street', 'Australia Street'],
  '9_43': ['Edinburgh Road', 'Meeks Road', 'Fitzroy Street'],
  '9_44': ['Way Street'],
  '9_45': ['Gill Street', 'Old Canterbury Road', 'Longport Street'],
  '9_47': ['Addison Road', 'Fitzroy Street', 'Sydenham Road']
};

/**
 * Map address to Marrickville precinct
 */
function getMarrickvillePrecinct(address: string): PrecinctMapping | null {
  const addressLower = address.toLowerCase();

  // Check each precinct's streets
  for (const [precinctNum, streets] of Object.entries(MARRICKVILLE_PRECINCT_STREETS)) {
    for (const street of streets) {
      if (addressLower.includes(street.toLowerCase())) {
        // Special handling for Illawarra Road - appears in multiple precincts
        if (street === 'Illawarra Road') {
          // Check street number to determine which precinct
          const numberMatch = address.match(/(\d+)\s+Illawarra/i);
          if (numberMatch) {
            const streetNum = parseInt(numberMatch[1]);
            // Precinct 30 (The Warren) is roughly 200-400 Illawarra Road
            // Precinct 28 is southern section
            // Precinct 29 is middle section
            if (streetNum >= 200 && streetNum <= 400) {
              return {
                precinctNumber: '9_30',
                precinctName: 'The Warren',
                documentId: 'Marrickville_DCP_2011___9_30_The_Warren',
                lga: 'Marrickville'
              };
            } else if (streetNum < 200) {
              return {
                precinctNumber: '9_29',
                precinctName: 'South Western Marrickville',
                documentId: 'Marrickville_DCP_2011___9_29_South_Western_Marrickville',
                lga: 'Marrickville'
              };
            } else {
              return {
                precinctNumber: '9_28',
                precinctName: 'Cooks River West',
                documentId: 'Marrickville_DCP_2011___9_28_Cooks_River_West',
                lga: 'Marrickville'
              };
            }
          }
        }

        // Return the first matching precinct
        const precinctNames: Record<string, string> = {
          '9_30': 'The Warren',
          '9_37': 'King Street and Enmore Road Commercial',
          '9_38': 'Dulwich Hill Commercial',
          '9_28': 'Cooks River West',
          '9_29': 'South Western Marrickville'
          // Add more as needed
        };

        return {
          precinctNumber: precinctNum,
          precinctName: precinctNames[precinctNum] || `Precinct ${precinctNum}`,
          documentId: `Marrickville_DCP_2011___${precinctNum}_${precinctNames[precinctNum]?.replace(/ /g, '_') || ''}`,
          lga: 'Marrickville'
        };
      }
    }
  }

  return null;
}

/**
 * Get DCP precinct for an address
 */
export async function getPrecinctForAddress(
  address: string,
  lga: string
): Promise<PrecinctMapping | null> {
  try {
    const lgaLower = lga.toLowerCase();

    // Inner West LGA includes Marrickville, Ashfield, and Leichhardt
    // Check if address is in Marrickville area (postcode 2204 or contains "marrickville")
    if (lgaLower.includes('marrickville') ||
        (lgaLower.includes('inner west') &&
         (address.toLowerCase().includes('marrickville') || address.includes('2204')))) {
      return getMarrickvillePrecinct(address);
    }

    // TODO: Add Ashfield and Leichhardt precinct mappings for other Inner West areas

    return null;
  } catch (error) {
    console.error('[Precinct Service] Error:', error);
    return null;
  }
}

/**
 * Get DCP provisions for a precinct
 * Queries the new dcp_precinct_provisions table
 */
export async function getPrecinctProvisions(
  precinctId: string,
  lga: string
): Promise<any[]> {
  try {
    console.log('[Precinct Service] Fetching provisions for:', { precinctId, lga });

    const query = `
      SELECT
        pp.id,
        pp.precinct_id,
        pp.precinct_name,
        pp.provision_text,
        pp.provision_type,
        pp.ref_number,
        pp.section_header,
        pp.pdf_page,
        pp.document_id,
        pp.pdf_path,
        pp.pdf_page_image_url
      FROM dcp_precinct_provisions pp
      WHERE pp.precinct_id = $1
        AND pp.lga = $2
      ORDER BY pp.display_order ASC, pp.ref_number ASC
      LIMIT 50
    `;

    const result = await pool.query(query, [precinctId, lga]);
    console.log(`[Precinct Service] Query returned ${result.rows.length} rows`);

    return result.rows;
  } catch (error) {
    console.error('[Precinct Service] Error getting provisions:', error);
    throw error;
  }
}

/**
 * DEPRECATED: Use getPrecinctProvisions instead
 * Old function that queried development_controls (which had no precinct data)
 */
export async function getPrecinctControls(
  precinctDocumentId: string,
  controlTypes?: string[]
): Promise<any[]> {
  console.warn('[Precinct Service] getPrecinctControls is deprecated, use getPrecinctProvisions instead');
  return [];
}
