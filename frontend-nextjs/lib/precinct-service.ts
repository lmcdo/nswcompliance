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

// LGAs whose DCP precincts tile the whole area — a containment miss there is a
// geocoding artefact, so snapping to the nearest boundary within 500m is safe.
// In councils with sparse site-specific precincts (e.g. Waverley Part E, and
// Ku-ring-gai where 10 boundaries cover 0.29 km² of an ~85 km² LGA), most
// addresses are legitimately in no precinct; snapping would serve controls for
// an area the property is not in.
const NEAREST_FALLBACK_LGAS = new Set(['inner west']);

/**
 * Row cap for a single precinct's provisions.
 *
 * Not a target — a backstop against a runaway query. The largest precinct in
 * the data today is 187 rows, so this is real headroom rather than a limit that
 * binds in normal use, and the query warns when it does bind. The topic filter
 * is applied in SQL BEFORE this cap, so narrowing to control types cannot lose
 * a row to truncation.
 */
const HARD_ROW_CAP = 1000;

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

    // Step 2: Query PostGIS for ALL precincts containing these coordinates.
    // DCP precincts can legitimately overlap (e.g. Waverley E5 "113 Macpherson
    // Street" sits inside the E3 "Macpherson Street" village centre), and the
    // provisions API accepts comma-separated precinct IDs.
    const query = `
      SELECT
        precinct_id,
        precinct_name,
        lga,
        former_council,
        confidence_score,
        extraction_method
      FROM dcp_precinct_boundaries
      WHERE ST_Contains(
        boundary,
        ST_SetSRID(ST_MakePoint($1, $2), 4326)
      )
      AND LOWER(lga) = LOWER($3)
      ORDER BY confidence_score DESC, precinct_id ASC
    `;

    const result = await getDbPool().query(query, [coords.longitude, coords.latitude, lga]);

    if (result.rows.length === 0) {
      // Nearest-boundary snapping is only valid where precincts tile the LGA;
      // elsewhere "no precinct" is the correct answer for most addresses.
      if (!NEAREST_FALLBACK_LGAS.has(lga.toLowerCase().trim())) {
        return null;
      }
      // Try finding nearest precinct within 500m (fallback for boundary edge cases)
      return await findNearestPrecinct(coords.longitude, coords.latitude, lga);
    }

    const primary = result.rows[0];
    const allIds = result.rows.map((r: { precinct_id: string }) => r.precinct_id).join(',');
    const allNames = result.rows
      .map((r: { precinct_name: string }) => r.precinct_name)
      .join(' + ');

    // Build document ID for provision lookup (primary precinct)
    const documentId = buildPrecinctDocumentId(
      primary.precinct_id,
      primary.precinct_name,
      primary.lga
    );

    return {
      precinctId: allIds,
      precinctNumber: primary.precinct_id,  // Primary precinct for compatibility
      precinctName: allNames,
      documentId: documentId,
      lga: primary.lga,
      formerCouncil: resolveFormerCouncil(primary.former_council, primary.precinct_id),
      confidenceScore: primary.confidence_score,
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
        former_council,
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
      formerCouncil: resolveFormerCouncil(precinct.former_council, precinct.precinct_id),
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

/**
 * Council precinct ID patterns - config-driven for multi-LGA support
 * Each entry defines regex patterns that identify precincts belonging to that council
 */
const PRECINCT_ID_PATTERNS: Record<string, RegExp[]> = {
  // Ashfield patterns - "Part X" format from dcp_precinct_boundaries table
  // Part 1-13 are Ashfield Chapter D precincts (Ashfield Town Centre, Summer Hill, etc.)
  'Ashfield': [
    /^part\s*\d+$/i,           // Part 1, Part 2, etc.
    /^ashfield/i,              // ashfield_*
    /^a_/i,                    // a_* prefix
    /chapter_[def]/i,          // Chapter D, E, F
  ],

  // Leichhardt patterns (C2.X.X.X format, Part G neighbourhoods)
  'Leichhardt': [
    /^c2/i,                    // C2.X.X.X format
    /^l_/i,                    // l_* prefix
    /part_[cg]/i,              // Part C, Part G
    /^g\d+$/i,                 // G1, G2, etc.
  ],

  // Marrickville patterns - Part 9 precincts with numeric format
  'Marrickville': [
    /^9_\d+$/,                 // 9_XX format
    /^\d+_$/,                  // XX_ format (precinct number)
    /part_9/i,                 // Part 9
    /^m_/i,                    // m_* prefix
  ],

  // Central Coast patterns (for future use)
  'Central Coast': [
    /^cc_/i,                   // cc_* prefix
    /^gosford/i,               // Gosford precincts
    /^wyong/i,                 // Wyong precincts
    /chapter_[45]/i,           // Chapters 4-5 specific sites
  ],

  // Parramatta patterns (for future use)
  'Parramatta': [
    /^parra/i,                 // parra_* prefix
    /^p_/i,                    // p_* prefix
  ],

  // Waverley DCP 2022 Part E precincts (E1 Bondi Junction … E7 Edina Estate).
  // Without this entry the default below returns 'Marrickville' and the
  // provisions API would be scoped to the wrong council.
  'Waverley': [
    /^e\d+$/i,                 // E1, E2, ... E7
  ],

  // Sydney DCP 2012 section-keyed precincts: 2.x[.y] locality statements,
  // 5.x specific areas, 6.x.y specific sites (e.g. '2.13.6', '5.8', '6.3.3').
  'City of Sydney': [
    /^[256]\.\d{1,2}(\.\d{1,2})?$/,
  ],

  // Ku-ring-gai DCP Part 14 local centre precincts (14B_T1..T4, 14I..14O).
  'Ku-ring-gai': [
    /^14[A-O](_T\d)?$/i,
  ],
};

/**
 * Display form for a stored former_council value. The column holds a mix of
 * display names ('Waverley', 'Marrickville', 'Parramatta', 'Woollahra') and
 * slugs ('city_of_sydney'); slugs are title-cased with joiner words kept
 * lowercase and the Ku-ring-gai hyphenation preserved.
 */
export function normalizeFormerCouncil(raw: string | null | undefined): string | null {
  const value = raw?.trim();
  if (!value) return null;
  if (!value.includes('_')) return value;
  if (value.toLowerCase() === 'ku_ring_gai') return 'Ku-ring-gai';
  const JOINERS = new Set(['of', 'and', 'the']);
  return value
    .toLowerCase()
    .split('_')
    .filter(Boolean)
    .map((w, i) => (i > 0 && JOINERS.has(w) ? w : w[0].toUpperCase() + w.slice(1)))
    .join(' ');
}

/**
 * Council attribution for a boundary row: the row's own former_council column
 * is authoritative when set (it names the council the boundary was loaded
 * for); PRECINCT_ID_PATTERNS is only a fallback for legacy rows where the
 * column is NULL (e.g. Ku-ring-gai). The pattern approach degrades as each new
 * council adds id formats — dotted Parramatta ids (7.10.1, 9) and name-keyed
 * Woollahra ids ('Paddington HCA') have no safe regex that does not collide
 * with another council's vocabulary.
 */
export function resolveFormerCouncil(
  storedFormerCouncil: string | null | undefined,
  precinctId: string
): string {
  return (
    normalizeFormerCouncil(storedFormerCouncil) ??
    getFormerCouncilFromPrecinctId(precinctId)
  );
}

/**
 * Get former council from precinct ID using config-driven patterns
 * Returns the council name that owns this precinct based on ID patterns
 */
export function getFormerCouncilFromPrecinctId(precinctId: string): string {
  if (!precinctId) return 'Unknown';

  const id = precinctId.toLowerCase();

  // Check each council's patterns
  for (const [council, patterns] of Object.entries(PRECINCT_ID_PATTERNS)) {
    for (const pattern of patterns) {
      if (pattern.test(precinctId) || pattern.test(id)) {
        return council;
      }
    }
  }

  // Default to Marrickville as it's most common in Inner West
  // This default can be overridden per-LGA in future versions
  return 'Marrickville';
}

/**
 * Register custom precinct patterns for a new LGA
 * Call this when adding support for a new council
 */
export function registerPrecinctPatterns(councilName: string, patterns: RegExp[]): void {
  PRECINCT_ID_PATTERNS[councilName] = patterns;
}

/**
 * Look up precinct IDs for an address by matching suburb tokens against dcp_precinct_localities.
 *
 * Returns an array of precinct_id values — usually one, but can be multiple when a suburb
 * spans several Chapter D precincts (e.g. "Ashfield" → three sub-precincts).
 * Returns null if no match is found.
 *
 * This is the data-driven replacement for hardcoded suburb→precinct dicts.
 * The mapping is owned by the dcp_precinct_localities table, populated from the
 * authoritative section_header values already in regulatory_provisions.
 */
export async function getPrecinctFromLocality(
  address: string,
  council: string,
): Promise<string[] | null> {
  try {
    // Match address (uppercased) against all known localities for this council.
    // Longer locality names rank higher to prefer specific matches ("SUMMER HILL" > "HILL").
    const result = await getDbPool().query<{ precinct_id: string }>(`
      SELECT precinct_id
      FROM dcp_precinct_localities
      WHERE LOWER(council) = LOWER($1)
        AND UPPER($2) LIKE ('%' || locality || '%')
      ORDER BY LENGTH(locality) DESC
    `, [council, address]);

    if (result.rows.length === 0) return null;

    // Deduplicate (a single suburb may have multiple rows if it maps to several precincts)
    const ids = [...new Set(result.rows.map(r => r.precinct_id))];
    console.log(`[Precinct Service] Locality match for '${council}' in "${address}": ${ids.join(', ')}`);
    return ids;
  } catch (error) {
    console.error('[Precinct Service] getPrecinctFromLocality error:', error);
    return null;
  }
}

/**
 * Get DCP provisions for a precinct
 * Queries the new dcp_precinct_provisions table
 */
/**
 * Council slug candidates for a precinct, as regulatory_provisions stores them.
 *
 * dcp_precinct_boundaries and regulatory_provisions name councils differently:
 * the boundary carries lga='City of Parramatta' with former_council='Parramatta',
 * while the provisions carry source_council='parramatta'. Inner West is the case
 * that forces the former_council preference — one LGA, but its provisions are
 * keyed by the three former councils (ashfield, leichhardt, marrickville), so
 * slugging the LGA alone would match nothing.
 *
 * Both candidates are returned rather than one: Ku-ring-gai boundaries carry no
 * former_council at all, and there the LGA slug ('ku_ring_gai') is the match.
 */
export function councilSlugCandidates(lga?: string | null, formerCouncil?: string | null): string[] {
  const slug = (v?: string | null) =>
    (v ?? '').trim().toLowerCase().replace(/[\s-]+/g, '_');
  return [slug(formerCouncil), slug(lga)].filter((v, i, a) => v !== '' && a.indexOf(v) === i);
}

/**
 * Provisions for a precinct, read from the table that actually holds them.
 *
 * WAS: `FROM dcp_precinct_provisions` — a legacy table with 0 rows, so this
 * returned an empty list for every precinct in every council. The live
 * provisions are in regulatory_provisions, keyed by v2_precinct_id (418
 * precincts carry them). CLAUDE.md has said "use v2_precinct_id, NOT
 * dcp_precinct_provisions" for months; this reader had not been moved across.
 *
 * The served-set filter (is_current AND v2_is_actionable) matches every other
 * read path, so a precinct cannot serve superseded or non-actionable text here
 * while hiding it elsewhere.
 */
export async function getPrecinctProvisions(
  precinctId: string,
  lga: string,
  formerCouncil?: string | null,
  controlTypes?: string[] | null,
): Promise<any[]> {
  try {
    const councils = councilSlugCandidates(lga, formerCouncil);
    // A precinct id is only unique WITHIN a council — "Part 1" exists in more
    // than one — so an empty candidate list must return nothing rather than
    // dropping the filter and serving another council's controls.
    if (precinctId.trim() === '' || councils.length === 0) return [];

    // Callers pass a comma-joined list when a point falls in overlapping
    // precincts (getPrecinctUsingPostGIS builds precinctId that way).
    const precinctIds = precinctId.split(',').map(v => v.trim()).filter(Boolean);
    if (precinctIds.length === 0) return [];

    // Topic narrowing happens HERE, not in JavaScript after the fact. Raised by
    // scripts/cross_review.py at 0.99: filtering after a row cap means a cap
    // that binds can drop the very control the caller asked for, and the
    // response still looks complete. The largest precinct measured today is 187
    // rows (leichhardt G6), so the old LIMIT 50 was already truncating and 200
    // left almost no headroom.
    const topics = (controlTypes && controlTypes.length > 0)
      ? controlTypes.map(t => t.toLowerCase())
      : null;

    // A council can map its precincts more finely than it keys its text. City of
    // Parramatta maps Epping as fifteen polygons — 8.1.1.1, 8.1.1.2, 8.1.1.3.1 —
    // while every one of their controls is written once, against 8.1.1. Exact
    // matching therefore returns NOTHING for a property in Epping Central, which
    // renders exactly like a property outside any precinct. Measured live
    // 2026-08-20, after #990 imported the boundaries and #992 wired the precinct
    // through to the page:
    //
    //     precinct_id=8.2.6    layer_4_precinct = 50   correct
    //     precinct_id=8.1.1.1  layer_4_precinct =  0   wrong
    //     no precinct at all   layer_4_precinct =  0
    //
    // #992 could not have caught it: it measured with 8.2.6, an exact match.
    //
    // `avail` is the set of keys this council actually has text for. `resolved`
    // maps each requested id onto the key that carries its controls: itself when
    // it has its own, otherwise the NEAREST ancestor that does — longest key
    // wins. A precinct with its own controls never also takes its parent's,
    // because serving a property controls it is not subject to is worse than
    // serving none, and it is the direction that looks like success.
    //
    // left(id, length(k)+1) = k || '.' rather than LIKE k || '.%': Marrickville
    // ids such as '47_' contain an underscore, which LIKE reads as a wildcard.
    //
    // Contained by measurement, not by hope: 22 of 89 City of Parramatta
    // polygons resolve only through an ancestor, and Sydney (145), Inner West
    // (85), Ku-ring-gai (10), Waverley (5) and Woollahra (14) all match exactly,
    // so nothing outside Parramatta changes.
    const query = `
      WITH requested AS (
        SELECT unnest($1::text[]) AS id
      ),
      avail AS (
        SELECT DISTINCT v2_precinct_id AS k
        FROM regulatory_provisions
        WHERE source_council = $2
          AND is_current
          AND v2_is_actionable
          AND v2_precinct_id IS NOT NULL
      ),
      precinct_keys AS (
        SELECT DISTINCT COALESCE(
          (SELECT a.k FROM avail a WHERE a.k = r.id),
          (SELECT a.k FROM avail a
            WHERE left(r.id, length(a.k) + 1) = a.k || '.'
            ORDER BY length(a.k) DESC
            LIMIT 1)
        ) AS k
        FROM requested r
      )
      SELECT
        rp.id,
        rp.v2_precinct_id      AS precinct_id,
        rp.provision_text,
        rp.provision_type,
        rp.v2_topic            AS control_type,
        rp.ref_number,
        rp.section_header,
        rp.pdf_page,
        rp.document_id,
        rp.pdf_page_image_url,
        rp.source_council
      FROM regulatory_provisions rp
      WHERE rp.v2_precinct_id IN (SELECT k FROM precinct_keys WHERE k IS NOT NULL)
        AND rp.source_council = $2
        AND rp.is_current
        AND rp.v2_is_actionable
        AND ($3::text[] IS NULL OR LOWER(rp.v2_topic) = ANY($3::text[]))
      ORDER BY rp.ref_number ASC NULLS LAST, rp.id ASC
      LIMIT ${HARD_ROW_CAP}
    `;

    // ONE council scope per query, never a union of both candidates. Raised by
    // scripts/cross_review.py at 0.94 and correct in principle: `source_council
    // = ANY([former, lga])` would merge two councils' controls for one property
    // if both carried the same precinct id. Measured today: 0 precinct ids are
    // shared across councils, so the union was harmless — but 'inner_west' does
    // exist as a source_council (16 rows) alongside ashfield/leichhardt/
    // marrickville, so the collision is one data change away. The preferred
    // scope (former council) is tried first and the LGA slug only when it
    // returns nothing, so the two can never combine.
    for (const council of councils) {
      const result = await getDbPool().query(query, [precinctIds, council, topics]);
      if (result.rows.length > 0) {
        if (result.rows.length >= HARD_ROW_CAP) {
          console.warn(
            `[Precinct Service] ${precinctId} (${council}) hit the ${HARD_ROW_CAP}-row cap — ` +
            `the list is truncated and may be missing controls.`,
          );
        }
        return result.rows;
      }
    }
    return [];
  } catch (error) {
    console.error('[Precinct Service] Error getting provisions:', error);
    throw error;
  }
}

/**
 * Precinct controls for the constraints API, narrowed to the topics it asks for.
 *
 * WAS: a stub that logged a deprecation notice and returned [] unconditionally,
 * whatever it was passed. The constraints route resolved the precinct correctly
 * from the boundary polygons and then handed it to this, so precinct controls
 * were empty for every address in every council — silently, because an empty
 * list renders as "no precinct controls" rather than as an error.
 *
 * It also took a precinctDocumentId built by string concatenation
 * (`${council}_DCP_2011_${id}_${name}`), which matched no stored document. The
 * signature now takes the precinct and its council, which is what identifies
 * the provisions.
 */
export async function getPrecinctControls(
  precinctId: string,
  lga: string,
  formerCouncil?: string | null,
  controlTypes?: string[],
): Promise<any[]> {
  // The topic list is pushed into SQL rather than applied to the result, so a
  // row cap can never discard a control the caller asked for. v2_topic is the
  // control_type analogue and carries exactly these values (height, parking,
  // open_space, ...); matching is case-insensitive because the caller's list is
  // lower-case by convention, not by constraint.
  return getPrecinctProvisions(precinctId, lga, formerCouncil, controlTypes);
}
