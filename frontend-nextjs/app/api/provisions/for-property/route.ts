/**
 * Provisions for Property API - 4-Layer Filtering
 *
 * Returns DCP provisions filtered by the 4-layer model:
 * - Layer 1 (Generic): Always include (Part 2, Section 1)
 * - Layer 2 (Use-specific): Zone-filtered (Part 4, Section 3)
 * - Layer 3 (Condition): Heritage/flood filtered (Part 8, heritage chapters)
 * - Layer 4 (Precinct): Location-filtered by precinct ID
 *
 * Query Parameters:
 * - lga: LGA name (e.g., "Inner West")
 * - zone: Zone code (e.g., "R2", "R3")
 * - heritage: "true" if property is heritage or in HCA
 * - flood: "true" if property is flood-prone
 * - precinct_id: Precinct identifier (e.g., "12_", "G6", "Part 1")
 * - dev_type: Development type (optional)
 * - topic: Filter by topic (optional)
 * - groupBy: "topic" (default) or "toc" - how to group results
 * - version_date: ISO date string (e.g., "2024-05-15") - returns provisions as of this date
 * - include_version_metadata: "true" to include version metadata in results
 *
 * Response includes:
 * - by_layer: provisions grouped by 4-layer model
 * - by_topic: provisions grouped by topic (always included)
 * - by_toc: provisions grouped by DCP structure (only if groupBy=toc)
 */

import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';
import { expandDevTypeHierarchy, expandDevTypeHierarchyMulti } from '@/lib/see/devTypeHierarchy';
import { inferSectionNumberFromHeader } from '@/lib/see/sectionKey';
import { parseRefNumber } from '@/lib/see/refNumber';
import { dataRateLimiter, getClientIdentifier, checkRateLimit, createRateLimitHeaders } from '@/lib/rate-limit';
import { captureServerException } from '@/lib/posthog-server';


export const dynamic = 'force-dynamic';

/**
 * Map former_council slug → document_id ILIKE pattern.
 *
 * Document IDs in regulatory_provisions use the DCP's published name
 * (e.g. "Sydney_DCP_2012__section_3_general_provisions") which doesn't
 * always match the formerCouncil slug (e.g. "city_of_sydney").
 */
const COUNCIL_DOC_PATTERNS: Record<string, string> = {
  city_of_sydney: 'Sydney_DCP',
  northern_beaches: 'Warringah_DCP',
  ku_ring_gai: 'Ku-ring-gai_DCP',
  the_hills: 'The_Hills',
  the_hills_shire: 'The_Hills',
  canada_bay: 'Canada_Bay',
};

function councilToDocPattern(formerCouncil: string): string {
  const slug = formerCouncil.toLowerCase().replace(/[-\s]+/g, '_');
  if (COUNCIL_DOC_PATTERNS[slug]) return COUNCIL_DOC_PATTERNS[slug];
  // Default: capitalize first letter of each word segment
  // e.g. "canterbury_bankstown" → "Canterbury_Bankstown"
  return slug.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join('_');
}

interface PropertyFilters {
  lga?: string;
  zone?: string;
  heritage?: boolean;
  flood?: boolean;
  bushfire?: boolean;
  precinct_id?: string;
  dev_type?: string;
  topic?: string;
  assessment_type?: 'CDC' | 'DA';  // CDC = quantitative only, DA = all
  former_council?: string;  // Former council name (Ashfield, Marrickville, Leichhardt)
  hca?: string;  // Heritage Conservation Area slug (e.g., "summer_hill", "hca_1")
  heritage_type?: 'control' | 'character' | 'descriptive';  // Filter heritage provisions by type
  groupBy?: 'topic' | 'toc';  // How to group results (default: topic)

  // Version tracking parameters
  version_date?: string;  // ISO date string (e.g., "2024-05-15") - get provisions as of this date
  include_version_metadata?: boolean;  // Include version metadata in results
}

interface LayerResult {
  layer: string;
  layer_name: string;
  provisions: any[];
  count: number;
}

/**
 * Normalize precinct ID format for database lookup
 *
 * Precinct service returns formats like: 9_29, 9_13, 9_30 (chapter_section for Marrickville)
 * Database uses formats like: 29_, 13_, 30_ (just section_)
 *
 * For Marrickville (chapter 9), convert 9_XX to XX_
 * For other councils (Ashfield, Leichhardt), pass through as-is
 */
function normalizePrecinctId(precinctId: string): string {
  if (!precinctId) return precinctId;

  // Marrickville chapter 9 format: 9_XX -> XX_
  const marrickvilleMatch = precinctId.match(/^9_(\d+)$/);
  if (marrickvilleMatch) {
    const normalized = `${marrickvilleMatch[1]}_`;
    console.log(`[Precinct Normalization] Marrickville: ${precinctId} -> ${normalized}`);
    return normalized;
  }

  // Ashfield format: Part 1, Part 2, etc. - pass through
  // Leichhardt format: C2.X.X.X, G1, etc. - pass through
  return precinctId;
}

/**
 * Strip OCR page-header prefix from Marrickville provision text.
 *
 * Marrickville DCP PDFs were OCR'd with running page headers captured alongside
 * provision content. The header format is:
 *   "PART N:  PART NAME \nPAGE_NUM \nMarrickville Development Control Plan 2011 \n"
 * This prefix is not provision content and must be removed before display.
 */
const MARRICKVILLE_OCR_HEADER = /^PART \d+:\s+[^\n]+\n\d+\s*\n(?:\s*Marrickville[^\n]*\n)?(?:\s*\n)*/;

/**
 * Strip OCR "doubled-glyph" running-header lines (e.g. City of Sydney DCP 2012).
 *
 * Some council DCP PDFs were OCR'd with running page headers where every glyph
 * is duplicated, e.g. "SSeeccttiioonn 11", "IINNTTRROODDUUCCTTIIOONN". These
 * land as standalone header lines; the provision body is unaffected (verified:
 * garbled lines are ~1.6% of characters and 0 rows retain doubling once removed).
 * Drop any line genuinely dominated by the doubled-character pattern. Applied
 * unconditionally — a no-op for councils without the artifact.
 */
const DOUBLED_GLYPH_RUN = /([A-Za-z])\1([A-Za-z])\2([A-Za-z])\3/;

function stripDoubledOcrLines(text: string): string {
  return text
    .split('\n')
    .filter((line) => {
      if (!DOUBLED_GLYPH_RUN.test(line)) return true; // normal line — keep
      // Only drop lines truly dominated by doubling, so a real line that merely
      // contains a garbled fragment survives. Collapsing consecutive duplicate
      // letters must shrink the line's letters by > 30%.
      const letters = (line.match(/[A-Za-z]/g) || []).length;
      const collapsed = (line.replace(/([A-Za-z])\1/g, '$1').match(/[A-Za-z]/g) || []).length;
      return letters === 0 || (letters - collapsed) / letters < 0.3;
    })
    .join('\n');
}

function stripOcrHeaderPrefix(text: string | null): string | null {
  if (!text) return text;
  let cleaned = text.replace(MARRICKVILLE_OCR_HEADER, '');
  cleaned = stripDoubledOcrLines(cleaned).trim();
  return cleaned || text; // never blank out a provision
}


/**
 * Lookup db_slug from heritage_conservation_areas by h_id (Planning Portal C-code)
 * Returns the db_slug that matches v2_heritage_hca in regulatory_provisions
 */
async function resolveHcaCode(client: any, hcaCode: string): Promise<string | null> {
  // Try to resolve HCA code/name to db_slug
  // Input can be: "C35", "HCA 10", "Parramatta Road Heritage Conservation Area", or "parramatta_road_heritage_conservation_area"

  // Handle Marrickville HCA pattern: "HCA 10" -> "hca_10"
  if (hcaCode.match(/^HCA\s*\d+$/i)) {
    const hcaSlug = hcaCode.toLowerCase().replace(/\s+/g, '_');
    console.log(`[HCA Lookup] ${hcaCode} -> ${hcaSlug} (Marrickville format)`);
    return hcaSlug;
  }

  // If it matches code pattern (C35, A12), look up by h_id
  if (hcaCode.match(/^[CA]\d+$/i)) {
    const result = await client.query(
      `SELECT db_slug FROM heritage_conservation_areas WHERE h_id = $1 LIMIT 1`,
      [hcaCode.toUpperCase()]
    );

    if (result.rows.length > 0 && result.rows[0].db_slug) {
      console.log(`[HCA Lookup] ${hcaCode} -> ${result.rows[0].db_slug}`);
      return result.rows[0].db_slug;
    }
  }

  // Otherwise try to look up by h_name (full name) or return if already a slug
  // First check if it already looks like a slug (contains underscore, no spaces)
  if (hcaCode.includes('_') && !hcaCode.includes(' ')) {
    console.log(`[HCA Lookup] ${hcaCode} -> assuming already a slug`);
    return hcaCode;
  }

  // Try to look up by h_name
  const result = await client.query(
    `SELECT db_slug FROM heritage_conservation_areas WHERE h_name ILIKE $1 LIMIT 1`,
    [hcaCode]
  );

  if (result.rows.length > 0 && result.rows[0].db_slug) {
    console.log(`[HCA Lookup] ${hcaCode} (by name) -> ${result.rows[0].db_slug}`);
    return result.rows[0].db_slug;
  }

  console.log(`[HCA Lookup] ${hcaCode} -> no mapping found`);
  return null;
}

// Module-level cache: former_council values known to have precinct provisions.
// Populated on first request per LGA; avoids repeated EXISTS queries.
const formerCouncilsWithPrecinctProvisions = new Set<string>();

// Module-level cache: LGA -> whether dcp_precinct_boundaries has any rows for it.
// Used by the precinct warning when a council has boundaries but no keyed
// provisions (content not yet extracted) — negative results are cached too.
const lgasWithPrecinctBoundaries = new Map<string, boolean>();

// former_council slug -> LGA name as stored in dcp_precinct_boundaries.lga.
// Callers don't always pass ?lga=, so the warning derives it here.
const COUNCIL_TO_LGA: Record<string, string> = {
  ashfield: 'Inner West',
  marrickville: 'Inner West',
  leichhardt: 'Inner West',
  waverley: 'Waverley',
  ku_ring_gai: 'Ku-ring-gai',
  city_of_sydney: 'Sydney',
};

/**
 * Deduplicate provisions across all layers
 * Removes duplicate provisions based on:
 * 1. Same provision ID
 * 2. Same text content (first 100 chars) + page number
 */
function deduplicateLayers(layers: LayerResult[]): LayerResult[] {
  // Collect all provisions with their layer info
  const allProvisions: Array<{ provision: any; layerIndex: number }> = [];
  layers.forEach((layer, layerIndex) => {
    layer.provisions.forEach(provision => {
      allProvisions.push({ provision, layerIndex });
    });
  });

  // First pass: deduplicate by provision ID
  const idDeduped = new Map<number, { provision: any; layerIndex: number }>();
  for (const item of allProvisions) {
    if (!idDeduped.has(item.provision.id)) {
      idDeduped.set(item.provision.id, item);
    }
  }

  // Second pass: deduplicate by text content (first 100 chars) + page
  // Use provision ID in key to prevent NULL pdf_page from causing over-deduplication
  // (when pdf_page is NULL, all provisions with similar text would get key "text|0")
  const textDeduped = new Map<string, { provision: any; layerIndex: number }>();
  for (const item of idDeduped.values()) {
    const textKey = `${item.provision.id}|${(item.provision.provision_text || '').substring(0, 100)}`;
    if (!textDeduped.has(textKey)) {
      textDeduped.set(textKey, item);
    }
  }

  // Rebuild layers with deduplicated provisions
  const newLayers: LayerResult[] = layers.map(layer => ({
    ...layer,
    provisions: [],
    count: 0
  }));

  for (const item of textDeduped.values()) {
    newLayers[item.layerIndex].provisions.push(item.provision);
    newLayers[item.layerIndex].count++;
  }

  return newLayers;
}

export async function GET(request: NextRequest) {
  const startTime = Date.now();

  try {
    const clientIP = getClientIdentifier(request);
    const rateLimitResult = await checkRateLimit(clientIP, dataRateLimiter, 30, 60000);
    if (!rateLimitResult.success) {
      return NextResponse.json(
        { error: 'Rate limit exceeded. Please try again in a minute.' },
        { status: 429, headers: createRateLimitHeaders(rateLimitResult) }
      );
    }

    const searchParams = request.nextUrl.searchParams;

    // Parse filters
    const filters: PropertyFilters = {
      lga: searchParams.get('lga') || undefined,
      zone: searchParams.get('zone') || undefined,
      heritage: searchParams.get('heritage') === 'true',
      flood: searchParams.get('flood') === 'true',
      bushfire: searchParams.get('bushfire') === 'true',
      precinct_id: searchParams.get('precinct_id') ? normalizePrecinctId(searchParams.get('precinct_id')!) : undefined,
      dev_type: searchParams.get('dev_types') || searchParams.get('dev_type') || undefined,
      topic: searchParams.get('topic') || undefined,
      assessment_type: (searchParams.get('assessment_type') as 'CDC' | 'DA') || undefined,
      former_council: searchParams.get('former_council') || undefined,
      hca: searchParams.get('hca') || undefined,
      heritage_type: (searchParams.get('heritage_type') as 'control' | 'character' | 'descriptive') || undefined,
      groupBy: (searchParams.get('groupBy') as 'topic' | 'toc') || 'topic',

      // Version tracking parameters
      version_date: searchParams.get('version_date') || undefined,
      include_version_metadata: searchParams.get('include_version_metadata') === 'true',
    };

    console.log(`[4-Layer API] Filters: ${JSON.stringify(filters)}`);

    const pool = getPool();
    const client = await pool.connect();

    try {
      // Resolve HCA code (e.g., "C98") to db_slug (e.g., "summer_hill")
      if (filters.hca) {
        const resolvedHca = await resolveHcaCode(client, filters.hca);
        if (resolvedHca) {
          filters.hca = resolvedHca;
        } else {
          // No mapping found - clear the filter to avoid false matches
          filters.hca = undefined;
        }
      }

      const results: LayerResult[] = [];

      // Layer 1: Generic provisions (always include)
      const layer1Raw = await queryLayer(client, 'generic', filters);
      const layer1 = await enrichWithTocSections(client, layer1Raw);
      results.push({
        layer: 'generic',
        layer_name: 'General Requirements',
        provisions: layer1,
        count: layer1.length
      });

      // Layer 2: Use-specific provisions (zone-filtered)
      const layer2Raw = await queryLayer(client, 'use_specific', filters);
      const layer2 = await enrichWithTocSections(client, layer2Raw);
      results.push({
        layer: 'use_specific',
        layer_name: 'Zone-Specific Requirements',
        provisions: layer2,
        count: layer2.length
      });

      // Layer 3: Condition provisions (heritage/flood filtered)
      const layer3Raw = await queryLayer(client, 'condition', filters);
      const layer3 = await enrichWithTocSections(client, layer3Raw);
      results.push({
        layer: 'condition',
        layer_name: 'Site Condition Requirements',
        provisions: layer3,
        count: layer3.length
      });

      // Layer 4: Precinct provisions (location-filtered)
      const layer4Raw = await queryLayer(client, 'precinct', filters);
      const layer4 = await enrichWithTocSections(client, layer4Raw);
      results.push({
        layer: 'precinct',
        layer_name: 'Precinct-Specific Requirements',
        provisions: layer4,
        count: layer4.length
      });

      // No URL adjustment needed - PDF files are correctly named
      // page_N.png contains DCP page N+1 content (verified 2024-12-10)

      // Log layer counts before deduplication
      console.log('[Layer Counts Before Dedup]', {
        generic: results[0].count,
        use_specific: results[1].count,
        condition: results[2].count,
        precinct: results[3].count,
        total: results.reduce((sum, r) => sum + r.count, 0)
      });

      // Deduplicate provisions across all layers
      const adjustedResults = deduplicateLayers(results);

      // Log layer counts after deduplication
      console.log('[Layer Counts After Dedup]', {
        generic: adjustedResults[0].count,
        use_specific: adjustedResults[1].count,
        condition: adjustedResults[2].count,
        precinct: adjustedResults[3].count,
        total: adjustedResults.reduce((sum, r) => sum + r.count, 0)
      });

      const totalCount = adjustedResults.reduce((sum, r) => sum + r.count, 0);
      const responseTime = Date.now() - startTime;

      // Precinct warning: fires when site-specific (precinct) controls may exist for
      // this council that this response does not attribute to the address. Three cases:
      //   1. No precinct_id given and precinct-layer provisions exist for the council.
      //   2. precinct_id(s) given but they match ZERO precinct provisions (e.g. locality
      //      fallback passed name-shaped ids) — same exposure as case 1, previously
      //      silently suppressed.
      //   3. Precinct BOUNDARIES exist for the LGA but no provisions are keyed to them
      //      (content not yet extracted, e.g. Ku-ring-gai Part 14) — matched or not,
      //      the site-specific rules cannot be shown.
      let precinctWarning = false;
      if (filters.former_council) {
        const fc = filters.former_council;

        let idsMatchProvisions = false;
        if (filters.precinct_id) {
          const ids = filters.precinct_id.split(',').map(s => s.trim()).filter(Boolean);
          const { rows } = await client.query(
            `SELECT 1 FROM regulatory_provisions
             WHERE source_council = $1 AND v2_precinct_id = ANY($2::text[])
               AND is_current = true LIMIT 1`,
            [fc, ids]
          );
          idsMatchProvisions = rows.length > 0;
        }

        if (!idsMatchProvisions) {
          if (!formerCouncilsWithPrecinctProvisions.has(fc)) {
            const { rows } = await client.query(
              `SELECT 1 FROM regulatory_provisions
               WHERE source_council = $1 AND v2_dcp_layer = 'precinct'
                 AND v2_is_actionable = true AND is_current = true LIMIT 1`,
              [fc]
            );
            if (rows.length > 0) formerCouncilsWithPrecinctProvisions.add(fc);
          }
          precinctWarning = formerCouncilsWithPrecinctProvisions.has(fc);

          if (!precinctWarning) {
            const lgaName = filters.lga || COUNCIL_TO_LGA[fc.toLowerCase().replace(/[-\s]+/g, '_')];
            if (lgaName) {
              if (!lgasWithPrecinctBoundaries.has(lgaName)) {
                const { rows } = await client.query(
                  `SELECT 1 FROM dcp_precinct_boundaries WHERE LOWER(lga) = LOWER($1) LIMIT 1`,
                  [lgaName]
                );
                if (rows.length > 0) lgasWithPrecinctBoundaries.set(lgaName, true);
                else lgasWithPrecinctBoundaries.set(lgaName, false);
              }
              precinctWarning = lgasWithPrecinctBoundaries.get(lgaName) === true;
            }
          }
        }
      }

      // Fetch chapter registry: PDF URLs + chapter labels for part-name derivation.
      // Done before TOC grouping so buildPartNameMap can drive part titles automatically.
      const chapterPdfUrls: Record<string, string> = {};
      const chapterLabels: Record<string, string> = {};
      let dcpCurrency: { verified_at: string | null; amendment_pending: boolean } | null = null;

      if (filters.former_council) {
        const councilSlug = filters.former_council.toLowerCase();
        const registryResult = await client.query(
          `SELECT chapter_key, r2_public_pdf_url, council_url, council_page_url,
                  chapter_label, needs_extraction
           FROM dcp_chapter_registry
           WHERE council = $1 AND is_active = TRUE`,
          [councilSlug]
        );
        let amendmentPending = false;
        for (const row of registryResult.rows) {
          // Prefer our own R2 copy: it is stable, and the page anchor built by the
          // caller is only meaningful against the PDF we paginated. Fall back to
          // the council's own URL rather than leaving the citation unlinked.
          //
          // Measured 2026-08-26, across served controls: chapter_key matches the
          // registry for 88.6%, but only 39.9% have an r2_public_pdf_url while
          // 49.2% have a council_url. Ignoring the fallback is why Canterbury-
          // Bankstown showed exactly ONE linked citation out of twenty - parking
          // has an R2 copy and the two setback chapters do not, though both carry
          // a council URL.
          // Ordered by how precisely each identifies the source, best first.
          // Measured 2026-08-26 across served controls, cumulative:
          //   r2_public_pdf_url alone            39.9%
          //   + council_url                      49.2%
          //   + council_page_url                 78.7%   <- largest single gain
          // council_page_url is already COALESCEd elsewhere in this codebase, so
          // the data and the idiom both existed; only this lookup ignored them.
          const chapterUrl =
            row.r2_public_pdf_url || row.council_url || row.council_page_url;
          if (chapterUrl) chapterPdfUrls[row.chapter_key] = chapterUrl;
          if (row.chapter_label) chapterLabels[row.chapter_key] = row.chapter_label;
          if (row.needs_extraction) amendmentPending = true;
        }

        // Last verified date from instrument_currency (set by weekly monitor after clean run)
        const currencyResult = await client.query(
          `SELECT verified_at FROM instrument_currency
           WHERE council = $1 AND instrument_key = 'dcp'
           LIMIT 1`,
          [councilSlug]
        );
        const verifiedAt = currencyResult.rows[0]?.verified_at ?? null;
        dcpCurrency = {
          verified_at: verifiedAt ? verifiedAt.toISOString() : null,
          amendment_pending: amendmentPending,
        };
      }
      const partNameMap = buildPartNameMap(chapterLabels);

      // Group provisions based on groupBy parameter
      const byTopic = groupByTopic(adjustedResults);
      const byToc = filters.groupBy === 'toc'
        ? groupByTocStructure(adjustedResults, filters.former_council, partNameMap)
        : undefined;

      // Get complete DCP TOC structure (unfiltered) for sidebar navigation
      // When dev_type provided, includes dev_type_match_count per chapter
      const completeToc = filters.groupBy === 'toc' && filters.former_council
        ? await getCompleteTocStructure(client, filters.former_council, filters.dev_type, partNameMap)
        : undefined;

      // Reconcile complete_toc sections with by_toc sections.
      // complete_toc is council-wide (unfiltered) and may have sections keyed differently from by_toc.
      // Example: Marrickville Part 2 — complete_toc has chapter-key sections ('part2-s01-urban-design')
      // from provisions with no v2_dcp_layer, while by_toc has toc_section_number sections ('2.1')
      // from the layered provisions. These never match, causing sidebar to show dead section links.
      // Fix: when a part's complete_toc sections have zero overlap with by_toc sections, clear them.
      if (byToc && completeToc) {
        for (const [partId, completePart] of Object.entries(completeToc as Record<string, any>)) {
          const completeSectionKeys = Object.keys(completePart.sections || {});
          if (completeSectionKeys.length === 0) continue;

          const byTocPart = (byToc as Record<string, any>)[partId];
          if (!byTocPart || byTocPart.provision_count === 0) continue;

          const byTocSectionKeys = Object.keys(byTocPart.sections || {});
          if (byTocSectionKeys.length === 0) continue;

          const byTocKeySet = new Set(byTocSectionKeys);
          const hasOverlap = completeSectionKeys.some((k: string) => byTocKeySet.has(k));
          if (!hasOverlap) {
            completePart.sections = {};
          }
        }
      }

      // Calculate relevance summary if dev_type provided
      const relevanceSummary = filters.dev_type ? calculateRelevanceSummary(adjustedResults) : undefined;

      // Include dev_type hierarchy info if filtering by dev_type
      const devTypeInfo = filters.dev_type ? {
        selected: filters.dev_type,
        expanded_hierarchy: expandDevTypeHierarchyMulti(filters.dev_type),
      } : undefined;

      // Cache for 5 minutes on edge, 1 minute stale-while-revalidate
      const response = NextResponse.json({
        success: true,
        data: {
          by_layer: adjustedResults,
          by_topic: byTopic,
          by_toc: byToc,
          complete_toc: completeToc,  // Unfiltered TOC structure for sidebar navigation
          summary: {
            total_provisions: totalCount,
            layer_1_generic: adjustedResults[0].count,
            layer_2_use_specific: adjustedResults[1].count,
            layer_3_condition: adjustedResults[2].count,
            layer_4_precinct: adjustedResults[3].count,
            relevance_breakdown: relevanceSummary,  // NEW: Relevance stats
          }
        },
        meta: {
          filters_applied: filters,
          dev_type_hierarchy: devTypeInfo,
          dev_type_approach: filters.dev_type
            ? 'inclusive_with_relevance_scoring'
            : 'show_all_provisions',
          legal_note: filters.dev_type
            ? 'All provisions shown per EP&A Act s 4.15 (consider all relevant provisions). Dev type used for relevance ranking only.'
            : undefined,
          response_time_ms: responseTime,
          api_version: 'v3_relevance_scoring',
          chapter_pdf_urls: chapterPdfUrls,
          precinct_warning: precinctWarning,
          dcp_currency: dcpCurrency,
        }
      });
      // Temporarily disabled cache for debugging duplicates issue
      response.headers.set('Cache-Control', 'no-store, must-revalidate');
      return response;

    } finally {
      client.release();
    }

  } catch (error) {
    console.error('[4-Layer API] Error:', error);
    captureServerException(error, { endpoint: '/api/provisions/for-property' });
    return NextResponse.json(
      {
        success: false,
        error: 'Internal server error',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}

/**
 * Calculate relevance summary for provisions when dev_type is provided
 */
function calculateRelevanceSummary(layers: LayerResult[]): any {
  const summary = {
    primary: 0,
    general: 0,
    secondary: 0,
  };

  for (const layer of layers) {
    for (const provision of layer.provisions) {
      if (provision.relevance_level) {
        summary[provision.relevance_level as 'primary' | 'general' | 'secondary']++;
      }
    }
  }

  const total = summary.primary + summary.general + summary.secondary;
  return {
    ...summary,
    total,
    primary_pct: total > 0 ? ((summary.primary / total) * 100).toFixed(1) : '0.0',
    general_pct: total > 0 ? ((summary.general / total) * 100).toFixed(1) : '0.0',
    secondary_pct: total > 0 ? ((summary.secondary / total) * 100).toFixed(1) : '0.0',
  };
}

/**
 * Shared SELECT fields for all provision queries.
 * Each query function extends this base with layer-specific fields.
 * Uses `rp` table alias — ensure FROM clause aliases regulatory_provisions as rp.
 */
const PROVISION_BASE_SELECT = `
  rp.id,
  rp.document_id,
  rp.provision_text,
  rp.v2_dcp_layer,
  rp.v2_dcp_part,
  rp.v2_topic,
  rp.v2_structural_category,
  rp.v2_provision_type,
  rp.v2_precinct_id,
  rp.v2_marker,
  rp.v2_display_behavior,
  rp.v2_display_priority,
  rp.v2_has_numeric_value,
  rp.pdf_page,
  rp.pdf_printed_page,
  rp.pdf_source_file,
  rp.pdf_page_image_url,
  rp.v2_heritage_type,
  rp.v2_heritage_element,
  rp.v2_heritage_hca,
  rp.v2_applicable_dev_types,
  rp.source_chapter_key,
  rp.section_header,
  rp.ref_number,
  rp.source_council
`;

/**
 * Query heritage provisions from regulatory_provisions.
 * When filters.hca is set: returns general heritage controls + HCA-specific controls.
 * When filters.hca is not set (e.g. individual heritage items): returns general controls only.
 */
async function queryHeritageByHca(
  client: any,
  filters: PropertyFilters
): Promise<any[]> {
  const params: any[] = [];
  let paramIndex = 1;

  // Build relevance scoring for dev_type
  let relevanceSelect = '';
  if (filters.dev_type) {
    const expandedTypes = expandDevTypeHierarchyMulti(filters.dev_type);
    const devTypeParamIndex = paramIndex++;
    relevanceSelect = `,
      CASE
        WHEN v2_applicable_dev_types && $${devTypeParamIndex}::text[] THEN 'primary'
        WHEN v2_applicable_dev_types IS NULL OR 'ALL' = ANY(v2_applicable_dev_types) THEN 'general'
        ELSE 'secondary'
      END as relevance_level,
      CASE
        WHEN v2_applicable_dev_types && $${devTypeParamIndex}::text[] THEN 'Specifically written for selected development type'
        WHEN v2_applicable_dev_types IS NULL OR 'ALL' = ANY(v2_applicable_dev_types) THEN 'Applies to all development types'
        ELSE 'May apply if objectives relevant (EP&A Act s 4.15)'
      END as relevance_reason
    `;
    params.push(expandedTypes);
  } else {
    relevanceSelect = `, NULL as relevance_level, NULL as relevance_reason`;
  }

  // Query regulatory_provisions for HCA-specific provisions
  // LEFT JOIN heritage_conservation_areas to get human-readable HCA name for keyword search
  let sql = `
    SELECT ${PROVISION_BASE_SELECT},
      hca.h_name AS hca_display_name
      ${relevanceSelect}
    FROM regulatory_provisions rp
    LEFT JOIN heritage_conservation_areas hca ON hca.db_slug = rp.v2_heritage_hca
    WHERE rp.v2_is_actionable = true
      AND rp.v2_marker = 'heritage'
  `;

  // Include HCA-specific controls only when a specific HCA is provided.
  // Without HCA (e.g. individual heritage items): general controls only.
  if (filters.hca) {
    sql += `
      AND (
        rp.v2_heritage_hca IS NULL  -- General heritage controls
        OR rp.v2_heritage_hca = $${paramIndex++}  -- Property's specific HCA
      )
    `;
    params.push(filters.hca);
  } else {
    sql += ` AND rp.v2_heritage_hca IS NULL`;
  }

  // Filter by former council — map slug to document_id prefix
  if (filters.former_council) {
    const docPattern = councilToDocPattern(filters.former_council);
    sql += ` AND rp.document_id ILIKE $${paramIndex++}`;
    params.push(`%${docPattern}%`);
  }

  // Filter by precinct - only include general provisions or property's precinct
  // Supports comma-separated precinct IDs for suburbs spanning multiple Chapter D precincts.
  if (filters.precinct_id) {
    const precinctIds = filters.precinct_id.split(',').map((s: string) => s.trim()).filter(Boolean);
    sql += ` AND (rp.v2_precinct_id IS NULL OR rp.v2_precinct_id = ANY($${paramIndex++}::text[]))`;
    params.push(precinctIds);
  } else {
    // No precinct specified - exclude all precinct-specific provisions
    sql += ` AND rp.v2_precinct_id IS NULL`;
  }

  // Filter by heritage_type (control, character, descriptive)
  if (filters.heritage_type) {
    sql += ` AND rp.v2_heritage_type = $${paramIndex++}`;
    params.push(filters.heritage_type);
  }

  // Filter by topic (e.g., "Roof", "Materials", "Additions")
  if (filters.topic) {
    sql += ` AND LOWER(REPLACE(rp.v2_topic, ' ', '_')) = LOWER($${paramIndex++})`;
    params.push(filters.topic.replace(/ /g, '_'));
  }

  sql += ` ORDER BY rp.v2_dcp_part, rp.id LIMIT 2000`;

  const result = await client.query(sql, params);

  // Strip OCR page-header prefix from all provisions (unconditional).
  // The regex only matches the specific "PART N: ALL CAPS\nPAGE_NUM\n[council name]" pattern —
  // a no-op for any council that doesn't have this OCR artifact.
  return result.rows.map((row: any) => ({
    ...row,
    provision_text: stripOcrHeaderPrefix(row.provision_text),
  }));
}

/**
 * Enrich provisions with TOC section info (section_number, section_title)
 * Uses document_id + pdf_page to find matching TOC entry
 */
async function enrichWithTocSections(
  client: any,
  provisions: any[]
): Promise<any[]> {
  if (provisions.length === 0) return provisions;

  // Get unique document_id + pdf_page combinations
  const docPages = provisions
    .filter(p => p.pdf_page != null)
    .map(p => ({ doc_id: p.document_id, page: p.pdf_page, id: p.id }));

  if (docPages.length === 0) {
    // No pdf_page data — still apply section_header inference so buildSectionKey works on the frontend
    return provisions.map(p => ({
      ...p,
      toc_section_number: inferSectionNumberFromHeader(p.section_header) || null,
      toc_section_title: null,
      clause_label: parseRefNumber(p.ref_number, p.source_council),
    }));
  }

  // Batch query TOC sections for all provisions
  // Match strategy (in order of specificity):
  //   1. Exact document_id match
  //   2. Legacy dash-normalization match (Marrickville__DCP__2011__-__X or Marrickville_DCP_2011_-_X)
  //   3. IWLEP suffix LIKE match
  //   4. Slug match: lowercase + collapse all non-alnum runs to single underscore
  //      Handles: Ashfield underscore vs space-dash, Leichhardt space-dash vs TOC underscore,
  //               page-split TOC entries (e.g. ..._1_50, ..._51_100 share same provision doc_id)
  const sql = `
    WITH provision_pages AS (
      SELECT DISTINCT document_id, pdf_page,
        REPLACE(REPLACE(REPLACE(REPLACE(document_id, '__-__', '__'), '_-_', '_'), '__', '_'), '-', '_') as doc_normalized,
        TRIM('_' FROM REGEXP_REPLACE(REGEXP_REPLACE(LOWER(document_id), '[^a-z0-9]+', '_', 'g'), '_+', '_', 'g')) as doc_slug
      FROM regulatory_provisions
      WHERE id = ANY($1::int[])
    )
    SELECT DISTINCT ON (pp.document_id, pp.pdf_page)
      pp.document_id,
      pp.pdf_page,
      t.section_number as toc_section_number,
      t.section_title as toc_section_title
    FROM provision_pages pp
    LEFT JOIN dcp_table_of_contents t ON (
      t.document_id = pp.document_id
      OR REPLACE(REPLACE(t.document_id, '__', '_'), '-', '_') = pp.doc_normalized
      OR REPLACE(REPLACE(t.document_id, '__', '_'), '-', '_') LIKE pp.doc_normalized || '%'
      OR t.document_id LIKE REGEXP_REPLACE(pp.document_id, '_with_IWLEP.*$', '') || '%'
      OR TRIM('_' FROM REGEXP_REPLACE(REGEXP_REPLACE(LOWER(t.document_id), '[^a-z0-9]+', '_', 'g'), '_+', '_', 'g')) = pp.doc_slug
      OR LEFT(TRIM('_' FROM REGEXP_REPLACE(REGEXP_REPLACE(LOWER(t.document_id), '[^a-z0-9]+', '_', 'g'), '_+', '_', 'g')), LENGTH(pp.doc_slug)) = pp.doc_slug
    )
    AND pp.pdf_page >= t.page_start
    AND (t.page_end IS NULL OR pp.pdf_page <= t.page_end)
    ORDER BY pp.document_id, pp.pdf_page, t.page_start DESC, t.depth DESC, t.section_number DESC
  `;

  const provisionIds = provisions.map(p => p.id);
  const result = await client.query(sql, [provisionIds]);

  // Create lookup map: "doc_id|page" -> TOC info
  const tocMap = new Map<string, { section_number: string; section_title: string }>();
  for (const row of result.rows) {
    if (row.toc_section_number) {
      const key = `${row.document_id}|${row.pdf_page}`;
      tocMap.set(key, {
        section_number: row.toc_section_number,
        section_title: row.toc_section_title
      });
    }
  }

  // Enrich provisions with TOC info.
  // Resolution order for toc_section_number:
  //   1. TOC JOIN hit — authoritative dcp_table_of_contents section_number
  //   2. section_header inference — for provisions with null pdf_page or no TOC match
  //      but whose provision text starts with an embedded section number (e.g. "3.1 Setbacks")
  //   3. null — genuine un-numbered provisions (introductory / background text)
  return provisions.map(p => {
    const key = `${p.document_id}|${p.pdf_page}`;
    const tocInfo = tocMap.get(key);
    return {
      ...p,
      toc_section_number: tocInfo?.section_number || inferSectionNumberFromHeader(p.section_header) || null,
      toc_section_title: tocInfo?.section_title || null,
      clause_label: parseRefNumber(p.ref_number, p.source_council)
    };
  });
}

async function queryLayer(
  client: any,
  layer: string,
  filters: PropertyFilters
): Promise<any[]> {
  // For condition layer with heritage, always use regulatory_provisions.
  // queryHeritageByHca handles both: HCA-specific + general (when hca set)
  // or general-only (when hca not set, e.g. individual heritage items).
  if (layer === 'condition' && filters.heritage) {
    return queryHeritageByHca(client, filters);
  }

  const params: any[] = [];
  let paramIndex = 1;

  // Build relevance scoring for dev_type (used for ranking, NOT filtering)
  let relevanceSelect = '';
  if (filters.dev_type) {
    const expandedTypes = expandDevTypeHierarchyMulti(filters.dev_type);
    const devTypeParamIndex = paramIndex++;
    relevanceSelect = `,
      CASE
        WHEN v2_applicable_dev_types && $${devTypeParamIndex}::text[] THEN 'primary'
        WHEN v2_applicable_dev_types IS NULL OR 'ALL' = ANY(v2_applicable_dev_types) THEN 'general'
        ELSE 'secondary'
      END as relevance_level,
      CASE
        WHEN v2_applicable_dev_types && $${devTypeParamIndex}::text[] THEN 'Specifically written for selected development type'
        WHEN v2_applicable_dev_types IS NULL OR 'ALL' = ANY(v2_applicable_dev_types) THEN 'Applies to all development types'
        ELSE 'May apply if objectives relevant (EP&A Act s 4.15)'
      END as relevance_reason
    `;
    params.push(expandedTypes);
  } else {
    relevanceSelect = `, NULL as relevance_level, NULL as relevance_reason`;
  }

  // Build version metadata selection (if requested)
  let versionSelect = '';
  if (filters.include_version_metadata) {
    versionSelect = `,
      rp.version_count,
      rp.first_seen_date,
      rp.last_modified_date,
      pv.version_number,
      pv.effective_from,
      pv.effective_to
    `;
  }

  // Build FROM clause with optional version JOIN
  let fromClause = '';
  let whereClause = 'WHERE v2_is_actionable = true';

  if (filters.version_date) {
    // Historical query - JOIN to get provisions effective at specific date
    const versionDateParamIndex = paramIndex++;
    fromClause = `
    FROM regulatory_provisions rp
    INNER JOIN provision_versions pv ON (
      pv.provision_id = rp.id
      AND pv.effective_from <= $${versionDateParamIndex}::timestamp
      AND (pv.effective_to IS NULL OR pv.effective_to > $${versionDateParamIndex}::timestamp)
    )`;
    params.push(filters.version_date);
  } else {
    // Default: current provisions only (fast path)
    if (filters.include_version_metadata) {
      fromClause = `
    FROM regulatory_provisions rp
    LEFT JOIN provision_versions pv ON (
      pv.id = rp.current_version_id
    )`;
    } else {
      fromClause = `
    FROM regulatory_provisions rp`;
    }
    whereClause += ' AND rp.is_current = TRUE';
  }

  let sql = `
    SELECT ${PROVISION_BASE_SELECT}
      ${relevanceSelect}
      ${versionSelect}
    ${fromClause}
    ${whereClause}
      AND v2_dcp_layer = $${paramIndex++}
      AND NOT (
        LOWER(COALESCE(section_header, '')) LIKE '%table of contents%'
        OR LOWER(COALESCE(section_header, '')) LIKE '%list of tables%'
        OR LOWER(COALESCE(section_header, '')) = 'contents'
        OR (
          COALESCE(section_header, '') = ''
          AND (
            (provision_text LIKE '%Table %:%Table %:%Table %:%' AND provision_text LIKE '%. . .%')
            OR (provision_text ~ '[A-Z][0-9]+\.[0-9]+\.[0-9]+ .+\. \. +[0-9]+' AND provision_text ~ '(\n|^)[A-Z][0-9]+\.[0-9]+\.[0-9]+ .+\. \. +[0-9]+')
            OR (provision_text LIKE '%SECTION 1%SECTION 2%' AND provision_text LIKE '%.....%')
          )
        )
      )
  `;
  params.push(layer);

  // Filter by former council name embedded in document_id
  if (filters.former_council) {
    const docPattern = councilToDocPattern(filters.former_council);
    sql += ` AND document_id ILIKE $${paramIndex++}`;
    params.push(`%${docPattern}%`);
  }

  // Heritage filtering logic:
  // 1. Generic/use-specific layers: Only include heritage provisions if LEP heritage = true
  // 2. Precinct layer: ALWAYS include provisions if in that precinct (precinct defines scope)
  // 3. Condition layer: Handled separately below
  // IMPORTANT: Check both v2_topic and v2_marker for heritage (provisions tagged with either)
  //
  // Authority: EP&A Act s 3.42 - DCP precinct provisions apply to all properties within
  // precinct boundaries, independently of LEP heritage schedules (precinct maps define scope)
  if (!filters.heritage && layer !== 'condition' && layer !== 'precinct') {
    // Property is not heritage - exclude all heritage provisions from generic/use-specific layers
    sql += ` AND (LOWER(v2_topic) != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage'))`;
  } else if (filters.hca && layer !== 'condition' && layer !== 'precinct') {
    // Heritage with HCA - exclude from non-condition layers (handled by queryHeritageByHca)
    sql += ` AND (LOWER(v2_topic) != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage'))`;
  } else if (filters.heritage && !filters.hca && layer !== 'condition' && layer !== 'precinct') {
    // Heritage without HCA - include but filter by precinct to avoid showing ALL precincts
    if (filters.precinct_id) {
      const precinctIds = filters.precinct_id.split(',').map((s: string) => s.trim()).filter(Boolean);
      sql += ` AND ((LOWER(v2_topic) != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage')) OR v2_precinct_id IS NULL OR v2_precinct_id = ANY($${paramIndex++}::text[]))`;
      params.push(precinctIds);
    } else {
      // No precinct specified - only show non-precinct heritage provisions
      sql += ` AND ((LOWER(v2_topic) != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage')) OR v2_precinct_id IS NULL)`;
    }
  }
  // Note: Precinct layer (layer === 'precinct') is NOT filtered by heritage status
  // Precinct provisions (including heritage-tagged ones) apply to ALL properties in precinct

  // Layer-specific filtering
  if (layer === 'use_specific' && filters.zone) {
    // For use-specific layer, filter by zone applicability
    // Include provisions where: zone is NULL (universal), zone matches, OR 'ALL' is in zones
    sql += ` AND (v2_applicable_zones IS NULL OR $${paramIndex++} = ANY(v2_applicable_zones) OR 'ALL' = ANY(v2_applicable_zones))`;
    params.push(filters.zone);
  }

  if (layer === 'condition') {
    // For condition layer (non-heritage), only include if property has that condition
    const conditions: string[] = [];
    if (filters.flood) conditions.push('flood');
    if (filters.bushfire) conditions.push('bushfire');

    if (conditions.length === 0) {
      // No conditions apply, skip condition layer
      return [];
    }

    sql += ` AND v2_site_condition_required = ANY($${paramIndex++}::text[])`;
    params.push(conditions);
  }

  if (layer === 'precinct') {
    if (filters.precinct_id) {
      // Support comma-separated precinct IDs (e.g. "Ashfield Town Centre,Ashfield East,Ashfield South")
      // for ambiguous suburbs that span multiple DCP Chapter D precincts.
      const precinctIds = filters.precinct_id.split(',').map(s => s.trim()).filter(Boolean);
      console.log(`[4-Layer API] Precinct filter: v2_precinct_id IN [${precinctIds.join(', ')}] OR 'PART_G_OVERVIEW'`);
      sql += ` AND (v2_precinct_id = ANY($${paramIndex++}::text[]) OR v2_precinct_id = 'PART_G_OVERVIEW')`;
      params.push(precinctIds);
    } else {
      // No precinct ID - exclude all precinct-specific provisions
      console.log(`[4-Layer API] No precinct_id provided - excluding all precinct provisions`);
      sql += ` AND v2_precinct_id IS NULL`;

      // Also filter heritage for non-heritage properties
      // (Provisions with v2_precinct_id IS NULL don't get precinct boundary protection)
      if (!filters.heritage) {
        sql += ` AND (LOWER(v2_topic) != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage'))`;
      }
    }
  }

  // Optional topic filter (case-insensitive, handle underscore vs space)
  // DB has "Building Form", UI sends "building_form"
  if (filters.topic) {
    sql += ` AND LOWER(REPLACE(v2_topic, ' ', '_')) = LOWER($${paramIndex++})`;
    params.push(filters.topic.replace(/ /g, '_'));
  }

  // ⚠️ CRITICAL: dev_type is NOT used for filtering (legal compliance per EP&A Act s 4.15)
  // Dev type is only used for RELEVANCE SCORING (added to SELECT clause above)
  // All provisions are returned; they're just ranked by relevance to user's dev_type
  //
  // Previous exclusive filtering REMOVED for legal compliance:
  // - EP&A Act s 4.15 requires considering ALL relevant provisions
  // - Dev type listings are ADVISORY, not exclusive (*Wehbe v Pittwater Council*)
  // - Excluding provisions = high liability risk for missed merits-based application

  // Exclude TOC provisions from display (table of contents items are navigation only)
  sql += ` AND (v2_provision_type IS NULL OR v2_provision_type != 'TOC')`;

  // Exclude provisions that are TOC pages - multiple patterns:
  // 1. Contains "i Contents" or starts with "Contents"
  // 2. Contains multiple dotted line patterns (e.g., "2.11.1 Objectives.... 1")
  // 3. Contains section lists with page numbers and dots
  sql += ` AND provision_text NOT LIKE '%i%Contents%'
           AND provision_text NOT LIKE 'Contents%'
           AND NOT (provision_text LIKE '%.....%' AND provision_text ~ '\\d+\\.\\d+\\.\\d+.*\\.+.*\\d+')`;


  // Assessment type filter (CDC = quantitative only, DA = all)
  if (filters.assessment_type === 'CDC') {
    // CDC requires quantitative, checkable controls with numeric values
    sql += ` AND v2_provision_type = 'control' AND v2_has_numeric_value = true`;
  }
  // DA shows all provisions (no additional filter)

  // Order by relevance (if dev_type provided), then by topic and part
  // Increased limit to 3000 to accommodate all Leichhardt provisions (2309 generic + 660 precinct)
  if (filters.dev_type) {
    const devTypeParamIndex = 1; // First parameter in params array
    sql += ` ORDER BY
    CASE
      WHEN v2_applicable_dev_types && $${devTypeParamIndex}::text[] THEN 1
      WHEN v2_applicable_dev_types IS NULL OR 'ALL' = ANY(v2_applicable_dev_types) THEN 2
      ELSE 3
    END, v2_topic, v2_dcp_part, id LIMIT 3000`;
  } else {
    sql += ` ORDER BY v2_topic, v2_dcp_part, id LIMIT 3000`;
  }

  const result = await client.query(sql, params);

  // Strip OCR page-header prefix from all provisions (unconditional).
  // The regex only matches the specific "PART N: ALL CAPS\nPAGE_NUM\n[council name]" pattern —
  // a no-op for any council that doesn't have this OCR artifact.
  return result.rows.map((row: any) => ({
    ...row,
    provision_text: stripOcrHeaderPrefix(row.provision_text),
  }));
}

function groupByTopic(layers: LayerResult[]): Record<string, any[]> {
  const byTopic: Record<string, any[]> = {};

  for (const layer of layers) {
    for (const provision of layer.provisions) {
      // Normalize topic: "Building Form" → "building_form" for consistent UI keys
      const rawTopic = provision.v2_topic || 'other';
      const topic = rawTopic.toLowerCase().replace(/ /g, '_');
      if (!byTopic[topic]) {
        byTopic[topic] = [];
      }
      byTopic[topic].push({
        ...provision,
        layer: layer.layer
      });
    }
  }

  return byTopic;
}

/**
 * Group provisions by DCP TOC structure (Part → Section → Provisions)
 * Handles Leichhardt Part C Section 1 specially by grouping via C markers
 */
interface TocSection {
  section_id: string;
  section_title: string;
  provision_count: number;
  provisions: any[];
  sub_groups?: Record<string, TocSection>;  // For Leichhardt C markers
}

interface TocPart {
  part_id: string;
  part_name: string;
  provision_count: number;
  dev_type_match_count?: number;  // Only present when dev_type provided
  sections: Record<string, TocSection>;
}

/**
 * Parse a source_chapter_key into its parent TOC part ID.
 * Used when v2_dcp_part is null/unknown (Marrickville, Leichhardt).
 *
 * Marrickville: part{N}-s{M}-{desc} | part{N}-p{M}-{desc} | part{N}-{desc}
 * Leichhardt:   part-{L}-s{N}-{desc} | part-{L}-{desc} | appendix-{code}-{desc}
 */
function extractTocParent(chapterKey: string): string {
  if (!chapterKey) return 'Other';
  // Marrickville: part{N}-s{M}-* or part{N}-p{M}-* or part{N}-intro
  const mvilleSubsection = chapterKey.match(/^part(\d+)-([sp]\d+|intro)/);
  if (mvilleSubsection) return `Part ${mvilleSubsection[1]}`;
  // Marrickville: part{N}-{desc} (e.g. part8-heritage, part3-subdivision)
  const mvilleSimple = chapterKey.match(/^part(\d+)-/);
  if (mvilleSimple) return `Part ${mvilleSimple[1]}`;
  // Leichhardt: part-{L}-*
  const leichPart = chapterKey.match(/^part-([a-z])-/);
  if (leichPart) return `Part ${leichPart[1].toUpperCase()}`;
  // Appendix
  const appendix = chapterKey.match(/^appendix-([a-z\d]+)/);
  if (appendix) return `Appendix ${appendix[1].toUpperCase()}`;
  // da-guidelines → Part 1
  if (chapterKey === 'da-guidelines') return 'Part 1';
  return chapterKey;
}

/**
 * Derive a human-readable section title from a source_chapter_key.
 * e.g. part2-s10-parking → "Parking", part9-p06-petersham-south → "Petersham South"
 */
function sectionTitleFromChapterKey(chapterKey: string): string {
  if (!chapterKey) return 'General';
  let desc: string | undefined;
  let m: RegExpMatchArray | null;
  // part{N}-s{M}-{desc} or part{N}-p{M}-{desc}
  if ((m = chapterKey.match(/^part\d+-[sp]\d+-(.+)$/))) desc = m[1];
  // part{N}-intro
  else if (chapterKey.endsWith('-intro')) desc = 'introduction';
  // part{N}-{desc} (not a subsection)
  else if ((m = chapterKey.match(/^part\d+-(.+)$/))) desc = m[1];
  // part-{L}-s{N}-{desc}
  else if ((m = chapterKey.match(/^part-[a-z]-s\d+-(.+)$/))) desc = m[1];
  // part-{L}-{desc}
  else if ((m = chapterKey.match(/^part-[a-z]-(.+)$/))) desc = m[1];
  // appendix-{code}-{desc}
  else if ((m = chapterKey.match(/^appendix-[a-z\d]+-(.+)$/))) desc = m[1];
  else if (chapterKey === 'da-guidelines') desc = 'DA Guidelines';
  else desc = chapterKey;
  return desc.split('-').map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(' ');
}

/**
 * Get complete DCP TOC structure for a council (unfiltered by property)
 * Used for sidebar navigation to show all parts even if current property has no provisions from some parts
 */
async function getCompleteTocStructure(client: any, formerCouncil: string, devType?: string, partNameMap?: Record<string, string>): Promise<Record<string, TocPart>> {
  const councilName = councilToDocPattern(formerCouncil);

  // When devType is provided, also compute how many provisions in each chapter match
  const expandedTypes = devType ? expandDevTypeHierarchyMulti(devType) : null;

  // Include source_chapter_key for councils where v2_dcp_part is 'unknown'/'null' (Marrickville, Leichhardt)
  const query = expandedTypes
    ? `
    SELECT
      v2_dcp_part,
      source_chapter_key,
      COUNT(*) as provision_count,
      COUNT(*) FILTER (WHERE
        v2_applicable_dev_types && $2::text[]
        OR v2_applicable_dev_types IS NULL
        OR 'ALL' = ANY(v2_applicable_dev_types)
      ) as dev_type_match_count
    FROM regulatory_provisions
    WHERE document_id ILIKE $1
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND (v2_dcp_part IS NOT NULL OR source_chapter_key IS NOT NULL)
      AND (v2_provision_type IS NULL OR v2_provision_type != 'TOC')
      AND provision_text NOT LIKE '%i%Contents%'
      AND provision_text NOT LIKE 'Contents%'
      AND NOT (provision_text LIKE '%.....%' AND provision_text ~ '\\d+\\.\\d+\\.\\d+.*\\.+.*\\d+')
    GROUP BY v2_dcp_part, source_chapter_key
    ORDER BY v2_dcp_part, source_chapter_key
  `
    : `
    SELECT
      v2_dcp_part,
      source_chapter_key,
      COUNT(*) as provision_count
    FROM regulatory_provisions
    WHERE document_id ILIKE $1
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND (v2_dcp_part IS NOT NULL OR source_chapter_key IS NOT NULL)
      AND (v2_provision_type IS NULL OR v2_provision_type != 'TOC')
      AND provision_text NOT LIKE '%i%Contents%'
      AND provision_text NOT LIKE 'Contents%'
      AND NOT (provision_text LIKE '%.....%' AND provision_text ~ '\\d+\\.\\d+\\.\\d+.*\\.+.*\\d+')
    GROUP BY v2_dcp_part, source_chapter_key
    ORDER BY v2_dcp_part, source_chapter_key
  `;

  const params = expandedTypes
    ? [`%${councilName}%`, expandedTypes]
    : [`%${councilName}%`];

  const result = await client.query(query, params);

  const completeToc: Record<string, TocPart> = {};

  const CHAPTER_KEY_RE = /^(part\d+-|part-[a-z]-|appendix-|da-guidelines)/;
  for (const row of result.rows) {
    const isChapterKeyBased = row.source_chapter_key && CHAPTER_KEY_RE.test(row.source_chapter_key);
    const hasRealPart = !isChapterKeyBased && row.v2_dcp_part && row.v2_dcp_part !== 'unknown';
    const partId = hasRealPart
      ? row.v2_dcp_part
      : extractTocParent(row.source_chapter_key || '');
    const partName = partNameMap?.[partId] ?? formatPartName(partId);
    const count = parseInt(row.provision_count);
    const devCount = expandedTypes ? parseInt(row.dev_type_match_count) : undefined;

    if (!completeToc[partId]) {
      completeToc[partId] = {
        part_id: partId,
        part_name: partName,
        provision_count: 0,
        ...(expandedTypes ? { dev_type_match_count: 0 } : {}),
        sections: {}
      };
    }
    completeToc[partId].provision_count += count;
    if (expandedTypes && devCount !== undefined) {
      completeToc[partId].dev_type_match_count = (completeToc[partId].dev_type_match_count || 0) + devCount;
    }
    // Add section entry for chapter-key-based councils
    if (!hasRealPart && row.source_chapter_key) {
      const sectionId = row.source_chapter_key;
      if (!completeToc[partId].sections[sectionId]) {
        completeToc[partId].sections[sectionId] = {
          section_id: sectionId,
          section_title: sectionTitleFromChapterKey(sectionId),
          provision_count: 0,
          provisions: []
        };
      }
      completeToc[partId].sections[sectionId].provision_count += count;
    }
  }

  return completeToc;
}

function groupByTocStructure(
  layers: LayerResult[],
  formerCouncil?: string,
  partNameMap?: Record<string, string>
): Record<string, TocPart> {
  const byToc: Record<string, TocPart> = {};

  // Flatten all provisions from all layers
  // Deduplicate by provision ID to prevent same provision appearing multiple times
  const provisionMap = new Map<number, any>();
  for (const layer of layers) {
    for (const provision of layer.provisions) {
      // Keep first occurrence (preserves layer priority order)
      if (!provisionMap.has(provision.id)) {
        provisionMap.set(provision.id, { ...provision, layer: layer.layer });
      }
    }
  }

  // Second pass: deduplicate by text content (database may have multiple IDs with same text)
  // Use provision ID + first 100 chars as dedup key to prevent NULL pdf_page from causing over-deduplication
  const textDeduped = new Map<string, any>();
  const idDedupedProvisions = [...provisionMap.values()];
  for (const provision of idDedupedProvisions) {
    // Use provision ID in key to prevent NULL pdf_page from grouping unrelated provisions
    const textKey = `${provision.id}|${(provision.provision_text || '').substring(0, 100)}`;
    if (!textDeduped.has(textKey)) {
      textDeduped.set(textKey, provision);
    }
  }
  const allProvisions = [...textDeduped.values()];

  // Group by v2_dcp_part when populated; for councils where v2_dcp_part is 'unknown'/null
  // (Marrickville, Leichhardt), parse source_chapter_key into parent part + section.
  // ALSO: if source_chapter_key matches a chapter-key pattern (part\d+-, part-[a-z]-, etc.),
  // always use chapter-key grouping regardless of v2_dcp_part — some Marrickville provisions
  // have real v2_dcp_part values in the DB but source_chapter_key is authoritative for these councils.
  const CHAPTER_KEY_RE = /^(part\d+-|part-[a-z]-|appendix-|da-guidelines)/;
  for (const provision of allProvisions) {
    const isChapterKeyBased = provision.source_chapter_key && CHAPTER_KEY_RE.test(provision.source_chapter_key);
    const hasRealPart = !isChapterKeyBased && provision.v2_dcp_part && provision.v2_dcp_part !== 'unknown';
    let partId: string;
    let sectionId: string;
    let sectionTitle: string;

    if (hasRealPart) {
      partId = provision.v2_dcp_part;
      sectionId = provision.toc_section_number || 'unsectioned';
      sectionTitle = provision.toc_section_title || 'General';
      // Special handling for Leichhardt Part C Section 1 - use C markers as sub-groups
      const isLeichhardtPartC = formerCouncil?.toLowerCase() === 'leichhardt' &&
        partId?.includes('Part C') && partId?.includes('Section 1');
      if (isLeichhardtPartC && provision.v2_marker) {
        sectionId = provision.v2_marker;
        sectionTitle = `Control ${provision.v2_marker}`;
      }
    } else {
      const chapterKey = provision.source_chapter_key;
      // Skip provisions with no chapter classification rather than creating a phantom "Other" group.
      // These are data-quality gaps; they should be classified in the DB, not surfaced as a chapter.
      if (!chapterKey) continue;
      partId = extractTocParent(chapterKey);
      sectionId = chapterKey;
      sectionTitle = sectionTitleFromChapterKey(chapterKey);
    }

    const partName = partNameMap?.[partId] ?? formatPartName(partId);

    if (!byToc[partId]) {
      byToc[partId] = {
        part_id: partId,
        part_name: partName,
        provision_count: 0,
        sections: {}
      };
    }

    if (!byToc[partId].sections[sectionId]) {
      byToc[partId].sections[sectionId] = {
        section_id: sectionId,
        section_title: sectionTitle,
        provision_count: 0,
        provisions: []
      };
    }

    byToc[partId].sections[sectionId].provisions.push(provision);
    byToc[partId].sections[sectionId].provision_count++;
    byToc[partId].provision_count++;
  }

  // Sort sections within each part by section_id
  for (const partId of Object.keys(byToc)) {
    const sortedSections: Record<string, TocSection> = {};
    const sectionKeys = Object.keys(byToc[partId].sections).sort((a, b) => {
      // Sort C markers numerically (C1, C2, C10, C11...)
      if (a.startsWith('C') && b.startsWith('C')) {
        const numA = parseInt(a.slice(1)) || 0;
        const numB = parseInt(b.slice(1)) || 0;
        return numA - numB;
      }
      // Sort numeric sections (2.10, 2.11...)
      return a.localeCompare(b, undefined, { numeric: true });
    });
    for (const key of sectionKeys) {
      sortedSections[key] = byToc[partId].sections[key];
    }
    byToc[partId].sections = sortedSections;
  }

  return byToc;
}

/**
 * Format DCP part ID to readable name
 */
function formatPartName(partId: string): string {
  if (!partId || partId === 'Other') return 'Other Provisions';

  // Already formatted
  if (partId.includes(':')) return partId;

  // Common patterns
  const patterns: Record<string, string> = {
    'Part 2': 'Part 2: General Provisions',
    'Part 3': 'Part 3: Subdivision, Amalgamation and Movement Networks',
    'Part 4': 'Part 4: Residential Development',
    'Part 4.1': 'Part 4.1: Low Density Residential',
    'Part 4.2': 'Part 4.2: Multi-Dwelling Housing',
    'Part 5': 'Part 5: Commercial Development',
    'Part 6': 'Part 6: Industrial Development',
    'Part 7': 'Part 7: Miscellaneous',
    'Part 8': 'Part 8: Heritage',
    'Part 9': 'Part 9: Precincts',
    'Part C Section 1': 'Part C Section 1: General Controls',
    'Part C Section 2': 'Part C Section 2: Distinctive Neighbourhoods',
    'Part C Section 3': 'Part C Section 3: Residential',
    'Part D': 'Part D: Energy',
    'Part E': 'Part E: Water',
    'Part F': 'Part F: Food',
    'Part G': 'Part G: Neighbourhoods',
    'Chapter A': 'Chapter A: Miscellaneous',
    'Chapter B': 'Chapter B: Public Domain',
    'Chapter C': 'Chapter C: Sustainability',
    'Chapter D': 'Chapter D: Precincts',
    'Chapter E1': 'Chapter E1: Heritage',
    'Chapter F': 'Chapter F: Development Category',
  };

  if (patterns[partId]) return patterns[partId];

  // KRG underscore slugs: part_4_1_secondary_dwellings → Part 4.1: Secondary Dwellings
  const krgDecimal = partId.match(/^part_(\d+)_(\d+)_(.+)$/);
  if (krgDecimal) {
    const desc = krgDecimal[3].replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    return `Part ${krgDecimal[1]}.${krgDecimal[2]}: ${desc}`;
  }
  const krg = partId.match(/^part_(\d+)_(.+)$/);
  if (krg) {
    const desc = krg[2].replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    return `Part ${krg[1]}: ${desc}`;
  }

  return partId;
}

/**
 * Build a part-name map from dcp_chapter_registry chapter_label values.
 * For parts with a single chapter, the label encodes the part name directly:
 *   "Part 3 · Subdivision, Amalgamation and Movement Networks"
 * For multi-chapter parts (e.g. Part 7 with sub-sections 7.1, 7.2...) the
 * label suffix begins with a section number ("7.1 Child Care Centres") — those
 * fall back to the hardcoded formatPartName lookup.
 */
function buildPartNameMap(chapterLabels: Record<string, string>): Record<string, string> {
  const partChapters: Record<string, string[]> = {};
  for (const key of Object.keys(chapterLabels)) {
    const partId = extractTocParent(key);
    if (!partChapters[partId]) partChapters[partId] = [];
    partChapters[partId].push(key);
  }
  const partNames: Record<string, string> = {};
  for (const [partId, keys] of Object.entries(partChapters)) {
    if (keys.length === 1) {
      const label = chapterLabels[keys[0]];
      const prefix = partId + ' \u00b7 ';
      if (label && label.startsWith(prefix)) {
        const desc = label.slice(prefix.length).trim();
        // Don't auto-derive if desc looks like a section number (e.g. "7.1 Child Care...")
        if (desc && !/^\d+\.\d+/.test(desc) && !/^Section\s/i.test(desc)) {
          partNames[partId] = `${partId}: ${desc}`;
          continue;
        }
      }
    }
    // Fall back to hardcoded name (multi-section parts, or label format mismatch)
    partNames[partId] = formatPartName(partId);
  }
  return partNames;
}
