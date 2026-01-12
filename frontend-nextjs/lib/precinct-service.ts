/**
 * Precinct Mapping Service
 * Maps addresses to DCP precincts for location-specific controls using PostGIS geometric matching
 */

import { getPropertyCoordinates } from './nsw-planning-portal';
import { getPool } from './db';

// Use shared database pool from db.ts for consistent connection handling
const getDbPool = () => getPool();

export interface PrecinctMapping {
  precinctId: string;        // Changed from precinctNumber for consistency with frontend
  precinctNumber: string;    // Keep for backward compatibility
  precinctName: string;
  documentId: string;
  lga: string;
  formerCouncil?: string;    // Former council area (Ashfield, Marrickville, Leichhardt)
  confidenceScore?: number;
  matchMethod?: 'geometric' | 'heritage_mapping';
}

// REMOVED: Hardcoded street mappings - Use PostGIS spatial matching instead
// PostGIS provides accurate geometric matching from dcp_precinct_boundaries table

/**
 * Get DCP precinct for an address using PostGIS geometric matching
 *
 * Strategy:
 * 1. Try PostGIS geometric matching (most accurate)
 * 2. Try heritage→precinct mapping (for HCAs without boundaries)
 * 3. Fall back to hardcoded street name matching (less accurate, legacy)
 * 4. Return null if no match found
 */
export async function getPrecinctForAddress(
  address: string,
  lga: string,
  coordinates?: { lat: number; lon: number },
  heritageItemName?: string
): Promise<PrecinctMapping | null> {
  try {
    console.log('[Precinct Service] Looking up precinct for:', { address, lga, hasCoordinates: !!coordinates, heritageItemName });

    // Strategy 1: Heritage→Precinct Mapping (PRIORITY for HCAs without spatial boundaries)
    // Check this FIRST when heritage data is available, as HCAs are more specific than geometric matching
    if (heritageItemName) {
      console.log('[Precinct Service] HCA detected, trying heritage mapping first:', heritageItemName);
      const heritageMatch = await getPrecinctFromHeritageMapping(heritageItemName, lga);
      if (heritageMatch) {
        console.log('[Precinct Service] ✅ Matched via heritage mapping:', heritageMatch.precinctNumber);
        return heritageMatch;
      }
      console.log('[Precinct Service] Heritage mapping found no match, falling back to PostGIS');
    }

    // Strategy 2: PostGIS Geometric Matching (PRIMARY METHOD - uses dcp_precinct_boundaries)
    const geometricMatch = await getPrecinctUsingPostGIS(address, lga, coordinates);
    if (geometricMatch) {
      console.log('[Precinct Service] Matched using PostGIS:', geometricMatch.precinctNumber);
      return geometricMatch;
    }

    // No match found - PostGIS is the only source of truth for precinct matching
    console.log('[Precinct Service] No precinct match found in PostGIS boundaries');
    return null;

  } catch (error) {
    console.error('[Precinct Service] Error:', error);
    return null;
  }
}

/**
 * Get precinct from heritage item name mapping
 * For HCAs that have requirements but no spatial boundaries (e.g., E2 Haberfield HCA)
 */
async function getPrecinctFromHeritageMapping(
  heritageItemName: string,
  lga: string
): Promise<PrecinctMapping | null> {
  try {
    // Try exact match first (most accurate)
    let query = `
      SELECT
        precinct_id,
        lga,
        notes
      FROM heritage_precinct_mapping
      WHERE heritage_item_name = $1
        AND LOWER(lga) = LOWER($2)
      LIMIT 1
    `;

    let result = await getDbPool().query(query, [heritageItemName, lga]);

    // If no exact match, try fuzzy matching (handles Planning Portal name variations)
    // e.g., "Haberfield HCA (nominated area of State significance)" matches "Haberfield HCA"
    if (result.rows.length === 0) {
      console.log('[Precinct Service] No exact match, trying fuzzy match...');

      query = `
        SELECT
          precinct_id,
          lga,
          notes
        FROM heritage_precinct_mapping
        WHERE $1 ILIKE (heritage_item_name || '%')
          AND LOWER(lga) = LOWER($2)
        ORDER BY LENGTH(heritage_item_name) DESC
        LIMIT 1
      `;

      result = await getDbPool().query(query, [heritageItemName, lga]);
      console.log(`[Precinct Service] Fuzzy match query returned ${result.rows.length} rows`);
    }

    if (result.rows.length === 0) {
      console.log('[Precinct Service] Heritage mapping: No rows returned from query');
      return null;
    }

    const mapping = result.rows[0];

    // Get precinct name from requirements table
    const nameQuery = `
      SELECT DISTINCT precinct_name
      FROM dcp_precinct_requirements
      WHERE precinct_id = $1
      LIMIT 1
    `;
    const nameResult = await getDbPool().query(nameQuery, [mapping.precinct_id]);
    const precinctName = nameResult.rows[0]?.precinct_name || heritageItemName;

    return {
      precinctId: mapping.precinct_id,
      precinctNumber: mapping.precinct_id,
      precinctName: precinctName,
      documentId: buildPrecinctDocumentId(mapping.precinct_id, precinctName, mapping.lga),
      lga: mapping.lga,
      formerCouncil: getFormerCouncilFromPrecinctId(mapping.precinct_id),
      confidenceScore: 0.9, // High confidence for direct heritage mapping
      matchMethod: 'heritage_mapping' as const
    };
  } catch (error) {
    console.error('[Precinct Service] Heritage mapping ERROR:', error);
    console.error('[Precinct Service] Error details:', {
      message: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
      heritageItemName,
      lga
    });
    return null;
  }
}

/**
 * Get precinct using PostGIS geometric point-in-polygon matching
 * This is the proper, scalable solution that works for ANY address
 */
async function getPrecinctUsingPostGIS(
  address: string,
  lga: string,
  providedCoordinates?: { lat: number; lon: number }
): Promise<PrecinctMapping | null> {
  try {
    // Step 1: Get property coordinates (use provided if available, otherwise geocode)
    let coords;
    if (providedCoordinates) {
      coords = { latitude: providedCoordinates.lat, longitude: providedCoordinates.lon };
      console.log('[Precinct Service] Using provided coordinates:', coords);
    } else {
      coords = await getPropertyCoordinates(address);
      if (!coords) {
        console.log('[Precinct Service] Could not get coordinates for address');
        return null;
      }
      console.log('[Precinct Service] Geocoded coordinates:', coords);
    }

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

    const result = await getDbPool().query(query, [coords.longitude, coords.latitude, lga]);

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
      precinctId: precinct.precinct_id,
      precinctNumber: precinct.precinct_id,  // Same as precinctId for compatibility
      precinctName: precinct.precinct_name,
      documentId: documentId,
      lga: precinct.lga,
      formerCouncil: getFormerCouncilFromPrecinctId(precinct.precinct_id),
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

    const result = await getDbPool().query(query, [longitude, latitude, lga]);

    if (result.rows.length === 0) {
      return null;
    }

    const precinct = result.rows[0];
    console.log(`[Precinct Service] Found nearest precinct ${precinct.precinct_id} at ${Math.round(precinct.distance_m)}m`);

    return {
      precinctId: precinct.precinct_id,
      precinctNumber: precinct.precinct_id,  // Same as precinctId for compatibility
      precinctName: precinct.precinct_name,
      documentId: buildPrecinctDocumentId(precinct.precinct_id, precinct.precinct_name, precinct.lga),
      lga: precinct.lga,
      formerCouncil: getFormerCouncilFromPrecinctId(precinct.precinct_id),
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
  // Marrickville precincts: 9_XX, XX_ (numeric underscore like 13_)
  // Ashfield precincts: "Part X" format (Part 1 through Part 13 from Chapter D)
  // Leichhardt precincts: C2.X.X.X format

  const id = precinctId.toLowerCase();

  // Ashfield patterns - "Part X" format from precinct_boundaries table
  // Part 1-13 are Ashfield Chapter D precincts (Ashfield Town Centre, Summer Hill, etc.)
  if (/^part\s*\d+$/i.test(precinctId)) {
    return 'Ashfield';
  }

  // Other Ashfield patterns
  if (id.startsWith('ashfield') || id.startsWith('a_') ||
      id.includes('chapter_d') || id.includes('chapter_e') || id.includes('chapter_f')) {
    return 'Ashfield';
  }

  // Leichhardt patterns (C2.X.X.X format)
  if (id.startsWith('c2') || id.startsWith('l_') ||
      id.includes('part_g') || id.includes('part_c')) {
    return 'Leichhardt';
  }

  // Marrickville patterns - numeric underscore like 9_, 10_, 13_
  if (precinctId.startsWith('9_') || /^\d+_$/.test(precinctId) || id.includes('part_9')) {
    return 'Marrickville';
  }

  // Default to Marrickville as it's most common in Inner West
  return 'Marrickville';
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

    const result = await getDbPool().query(query, [precinctId, lga]);
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
