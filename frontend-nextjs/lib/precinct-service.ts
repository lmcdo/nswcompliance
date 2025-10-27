/**
 * Precinct Mapping Service
 * Maps addresses to DCP precincts for location-specific controls using PostGIS geometric matching
 */

import { Pool } from 'pg';
import { getPropertyCoordinates } from '../../lib/services/planning-portal-api';

const pool = new Pool({
  host: 'localhost',
  port: 5432,
  database: 'nsw_planning',
  user: 'postgres',
  password: process.env.DB_PASSWORD || 'postgres'
});

export interface PrecinctMapping {
  precinctNumber: string;
  precinctName: string;
  documentId: string;
  lga: string;
  confidenceScore?: number;
  matchMethod?: 'geometric' | 'fallback' | 'hardcoded';
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
 * Get DCP precinct for an address using PostGIS geometric matching
 *
 * Strategy:
 * 1. Try PostGIS geometric matching (most accurate)
 * 2. Fall back to hardcoded street name matching (less accurate, legacy)
 * 3. Return null if no match found
 */
export async function getPrecinctForAddress(
  address: string,
  lga: string
): Promise<PrecinctMapping | null> {
  try {
    console.log('[Precinct Service] Looking up precinct for:', { address, lga });

    // Strategy 1: PostGIS Geometric Matching (PRIMARY METHOD)
    const geometricMatch = await getPrecinctUsingPostGIS(address, lga);
    if (geometricMatch) {
      console.log('[Precinct Service] Matched using PostGIS:', geometricMatch.precinctNumber);
      return geometricMatch;
    }

    // Strategy 2: Hardcoded Street Name Matching (FALLBACK for areas without PostGIS boundaries)
    console.log('[Precinct Service] PostGIS match failed, trying hardcoded fallback...');
    const lgaLower = lga.toLowerCase();

    // Inner West LGA includes Marrickville, Ashfield, and Leichhardt
    // Check if address is in Marrickville area (postcode 2204 or contains "marrickville")
    if (lgaLower.includes('marrickville') ||
        (lgaLower.includes('inner west') &&
         (address.toLowerCase().includes('marrickville') || address.includes('2204')))) {
      const fallbackMatch = getMarrickvillePrecinct(address);
      if (fallbackMatch) {
        console.log('[Precinct Service] Matched using hardcoded fallback:', fallbackMatch.precinctNumber);
        return {
          ...fallbackMatch,
          confidenceScore: 0.6,
          matchMethod: 'hardcoded'
        };
      }
    }

    // No match found
    console.log('[Precinct Service] No precinct match found');
    return null;

  } catch (error) {
    console.error('[Precinct Service] Error:', error);
    return null;
  }
}

/**
 * Get precinct using PostGIS geometric point-in-polygon matching
 * This is the proper, scalable solution that works for ANY address
 */
async function getPrecinctUsingPostGIS(
  address: string,
  lga: string
): Promise<PrecinctMapping | null> {
  try {
    // Step 1: Get property coordinates from NSW Planning Portal
    const coords = await getPropertyCoordinates(address);
    if (!coords) {
      console.log('[Precinct Service] Could not get coordinates for address');
      return null;
    }

    console.log('[Precinct Service] Property coordinates:', coords);

    // Step 2: Query PostGIS for precinct containing these coordinates
    const query = `
      SELECT
        precinct_id,
        precinct_name,
        lga,
        confidence_score,
        extraction_method
      FROM dcp_precinct_boundaries
      WHERE ST_Contains(
        boundary,
        ST_SetSRID(ST_MakePoint($1, $2), 4326)
      )
      AND LOWER(lga) = LOWER($3)
      ORDER BY confidence_score DESC
      LIMIT 1
    `;

    const result = await pool.query(query, [coords.longitude, coords.latitude, lga]);

    if (result.rows.length === 0) {
      // Try finding nearest precinct within 500m (fallback for boundary edge cases)
      return await findNearestPrecinct(coords.longitude, coords.latitude, lga);
    }

    const precinct = result.rows[0];

    // Build document ID for provision lookup
    const documentId = buildPrecinctDocumentId(
      precinct.precinct_id,
      precinct.precinct_name,
      precinct.lga
    );

    return {
      precinctNumber: precinct.precinct_id,
      precinctName: precinct.precinct_name,
      documentId: documentId,
      lga: precinct.lga,
      confidenceScore: precinct.confidence_score,
      matchMethod: 'geometric'
    };

  } catch (error) {
    // If PostGIS not installed or table doesn't exist, silently return null
    // This allows fallback to hardcoded method
    if (error instanceof Error) {
      const errMsg = error.message.toLowerCase();
      if (errMsg.includes('postgis') || errMsg.includes('dcp_precinct_boundaries')) {
        console.log('[Precinct Service] PostGIS not available, will use fallback');
        return null;
      }
    }
    console.error('[Precinct Service] PostGIS query error:', error);
    return null;
  }
}

/**
 * Find nearest precinct within 500m if point is not inside any boundary
 * This handles edge cases where address is just outside precinct boundary
 */
async function findNearestPrecinct(
  longitude: number,
  latitude: number,
  lga: string
): Promise<PrecinctMapping | null> {
  try {
    const query = `
      SELECT
        precinct_id,
        precinct_name,
        lga,
        confidence_score * 0.5 as confidence_score,
        ST_Distance(
          ST_Transform(boundary, 3857),
          ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 3857)
        ) as distance_m
      FROM dcp_precinct_boundaries
      WHERE LOWER(lga) = LOWER($3)
      AND ST_DWithin(
        ST_Transform(boundary, 3857),
        ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 3857),
        500  -- Within 500 metres
      )
      ORDER BY distance_m ASC, confidence_score DESC
      LIMIT 1
    `;

    const result = await pool.query(query, [longitude, latitude, lga]);

    if (result.rows.length === 0) {
      return null;
    }

    const precinct = result.rows[0];
    console.log(`[Precinct Service] Found nearest precinct ${precinct.precinct_id} at ${Math.round(precinct.distance_m)}m`);

    return {
      precinctNumber: precinct.precinct_id,
      precinctName: precinct.precinct_name,
      documentId: buildPrecinctDocumentId(precinct.precinct_id, precinct.precinct_name, precinct.lga),
      lga: precinct.lga,
      confidenceScore: precinct.confidence_score,
      matchMethod: 'geometric'
    };
  } catch (error) {
    console.error('[Precinct Service] Nearest precinct query error:', error);
    return null;
  }
}

/**
 * Build document ID for precinct provisions lookup
 */
function buildPrecinctDocumentId(precinctId: string, precinctName: string, lga: string): string {
  // Map LGA to former council for document naming
  const formerCouncil = lga.toLowerCase().includes('inner west')
    ? getFormerCouncilFromPrecinctId(precinctId)
    : lga;

  const nameSlug = precinctName.replace(/ /g, '_');

  // Example: "Marrickville_DCP_2011_9_10_Dulwich_Hill_North"
  return `${formerCouncil}_DCP_2011_${precinctId}_${nameSlug}`;
}

function getFormerCouncilFromPrecinctId(precinctId: string): string {
  // Marrickville precincts: 9_XX or just XX_
  // Ashfield precincts: A_XX or specific naming
  // Leichhardt precincts: L_XX or Part_G format

  if (precinctId.startsWith('9_') || /^\d+_$/.test(precinctId)) {
    return 'Marrickville';
  } else if (precinctId.startsWith('A_')) {
    return 'Ashfield';
  } else if (precinctId.startsWith('L_') || precinctId.includes('Part_G')) {
    return 'Leichhardt';
  }

  return 'Inner West';
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
