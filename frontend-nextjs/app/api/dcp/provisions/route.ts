import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';
import { getDCPSection, extractLGA } from '@/lib/dcp-section-service';
import { determineFormerCouncilArea } from '@/lib/inner-west-mapping-v2';
import { getZoneAliases } from '@/lib/zone-translation';

interface ProvisionsRequest {
  address?: string;
  lga: string;
  zone: string;
  developmentType: string;

  // Optional user filters
  search?: string;              // Full-text search
  categories?: string[];        // ["setback", "landscaping", "privacy", "solar", "parking"]
  provisionType?: string;       // "table" | "control" | "objective" | "all"

  // Pagination
  limit?: number;               // Default: 15
  offset?: number;              // Default: 0
}

interface ProvisionResult {
  id: number;
  ref_number: string;
  section_header: string;
  provision_text: string;
  document_id: string;
  provision_type: string;
  pdf_page: number;
  zone: string;
  development_type: string;
  rank_score?: number;          // For debugging ranking
}

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    const body: ProvisionsRequest = await request.json();
    const {
      address,
      lga,
      zone,
      developmentType,
      search,
      categories = [],
      provisionType = 'all',
      limit = 15,
      offset = 0
    } = body;

    // Validate required fields
    if (!lga || !zone || !developmentType) {
      return NextResponse.json({
        success: false,
        error: 'lga, zone, and developmentType are required'
      }, { status: 400 });
    }

    console.log('[DCP Provisions API] Request:', {
      lga,
      zone,
      developmentType,
      search,
      categories,
      provisionType,
      limit,
      offset
    });

    // Determine target LGA (handle Inner West former councils)
    let targetLGA = lga;
    let lgaSearchPattern = lga;

    if (lga.toLowerCase().includes('inner west')) {
      if (address) {
        const formerCouncil = determineFormerCouncilArea(address, lga);
        if (formerCouncil) {
          targetLGA = formerCouncil;
          lgaSearchPattern = formerCouncil;
          console.log(`[DCP Provisions API] Mapped to former council: ${formerCouncil}`);
        } else {
          lgaSearchPattern = '.*(Marrickville|Ashfield|Leichhardt).*';
        }
      } else {
        lgaSearchPattern = '.*(Marrickville|Ashfield|Leichhardt).*';
      }
    }

    // Build DCP document pattern based on dev type
    // Strategy: Include BOTH Part 2 (general controls) AND Part 4.X (dev-specific)
    let dcpDocumentPatterns: string[] = [];
    let dcpSectionName: string;

    // Map development types to DCP section patterns
    // Each dev type gets Part 2 (general) + Part 4.X (specific)
    const devTypeMapping: Record<string, { patterns: string[]; section: string }> = {
      'dwelling_house': {
        patterns: [
          `${lgaSearchPattern}.*_2_`,              // Part 2: General controls (parking, privacy, solar)
          `${lgaSearchPattern}.*4\\.1`             // Part 4.1: Low density specific
        ],
        section: 'Part 2 (General) + Part 4.1 (Low Density)'
      },
      'secondary_dwelling': {
        patterns: [
          `${lgaSearchPattern}.*_2_`,              // Part 2: General controls
          `${lgaSearchPattern}.*4\\.1`             // Part 4.1: Secondary dwellings covered here
        ],
        section: 'Part 2 (General) + Part 4.1 (Low Density)'
      },
      'multi_dwelling': {
        patterns: [
          `${lgaSearchPattern}.*_2_`,              // Part 2: General controls
          `${lgaSearchPattern}.*4\\.2`             // Part 4.2: Multi dwelling (when available)
        ],
        section: 'Part 2 (General) + Part 4.2 (Multi Dwelling)'
      },
      'residential_flat': {
        patterns: [
          `${lgaSearchPattern}.*_2_`,              // Part 2: General controls
          `${lgaSearchPattern}.*4\\.2`             // Part 4.2: RFBs covered here
        ],
        section: 'Part 2 (General) + Part 4.2 (Multi Dwelling)'
      },
      'shop_top_housing': {
        patterns: [
          `${lgaSearchPattern}.*_2_`,              // Part 2: General controls
          `${lgaSearchPattern}.*4\\.3`             // Part 4.3: Shop top housing
        ],
        section: 'Part 2 (General) + Part 4.3 (Shop Top)'
      },
      'boarding_house': {
        patterns: [
          `${lgaSearchPattern}.*_2_`,              // Part 2: General controls
          `${lgaSearchPattern}.*Boarding`          // Part 4.3: Boarding houses
        ],
        section: 'Part 2 (General) + Part 4.3 (Boarding House)'
      },
      'commercial': {
        patterns: [
          `${lgaSearchPattern}.*_2_`,              // Part 2: General controls
          `${lgaSearchPattern}.*_5`                // Part 5: Commercial/Industrial
        ],
        section: 'Part 2 (General) + Part 5 (Commercial)'
      },
      'child_care': {
        patterns: [
          `${lgaSearchPattern}.*_2_`,              // Part 2: General controls
          `${lgaSearchPattern}.*_5`                // Part 5: Community facilities
        ],
        section: 'Part 2 (General) + Part 5 (Community)'
      }
    };

    // When user is filtering by provision type (tables/controls/objectives),
    // search across ALL DCP sections, not just the development type section
    // NOTE: Category filters (setbacks, privacy, etc.) should REFINE the existing
    // dev-type filtering, NOT trigger browse-all mode
    const isFilteringByType = provisionType && provisionType !== 'all';
    const isBrowsingMode = isFilteringByType;  // Only provision type triggers browse mode

    const mapping = devTypeMapping[developmentType];
    if (mapping && !isBrowsingMode) {
      // Normal mode: filter to Part 2 + dev-specific section
      dcpDocumentPatterns = mapping.patterns;
      dcpSectionName = mapping.section;
    } else {
      // Browse mode: search all DCP documents for this LGA
      dcpDocumentPatterns = [`${lgaSearchPattern}.*DCP`];
      dcpSectionName = isBrowsingMode ? 'All DCP Sections (Browse Mode)' : 'All DCP Sections';
    }

    console.log('[DCP Provisions API] Document patterns:', dcpDocumentPatterns);
    console.log('[DCP Provisions API] Section:', dcpSectionName);
    console.log('[DCP Provisions API] Browse mode:', isBrowsingMode);

    // Build dynamic WHERE clauses
    const whereClauses: string[] = [];
    const queryParams: any[] = [];
    let paramIndex = 1;

    // Base filter: document_id patterns (OR combined)
    // OPTIMIZATION: Use LIKE for LGA prefix (fast) + regex for precision
    // Extract LGA prefix from first pattern
    const lgaPrefix = lgaSearchPattern.includes('|')
      ? lgaSearchPattern.split('|')[0].replace(/\.\*/g, '%').replace(/[()]/g, '').trim()
      : lgaSearchPattern.replace(/\.\*/g, '%');

    if (dcpDocumentPatterns.length > 1) {
      // Multiple patterns - combine with LIKE prefix + OR regex
      const patternClauses = dcpDocumentPatterns.map(() => {
        const clause = `document_id ~ $${paramIndex}`;  // Use ~ instead of ~* for case-sensitive (faster)
        paramIndex++;
        return clause;
      });
      whereClauses.push(`(document_id LIKE $${paramIndex} AND (${patternClauses.join(' OR ')}))`);
      queryParams.push(...dcpDocumentPatterns, lgaPrefix + '%');
      paramIndex++;
    } else {
      // Single pattern - LIKE prefix + regex
      whereClauses.push(`(document_id LIKE $${paramIndex} AND document_id ~ $${paramIndex + 1})`);
      queryParams.push(lgaPrefix + '%', dcpDocumentPatterns[0]);
      paramIndex += 2;
    }

    // Search filter (full-text)
    if (search && search.trim()) {
      whereClauses.push(`
        (
          to_tsvector('english', provision_text || ' ' || COALESCE(section_header, ''))
          @@ plainto_tsquery('english', $${paramIndex})
        )
      `);
      queryParams.push(search.trim());
      paramIndex++;
    }

    // Category filters (keyword matching)
    if (categories.length > 0) {
      const categoryPattern = categories.join('|');
      whereClauses.push(`provision_text ~* $${paramIndex}`);
      queryParams.push(categoryPattern);
      paramIndex++;
    }

    // Provision type filter
    if (provisionType && provisionType !== 'all') {
      switch (provisionType) {
        case 'table':
          whereClauses.push(`provision_text LIKE '%<table%'`);
          break;
        case 'control':
          whereClauses.push(`provision_text ~* '^(Control|Controls)'`);
          break;
        case 'objective':
          whereClauses.push(`provision_text ~* '^(Objective|Objectives)'`);
          break;
      }
    }

    // Build ranking logic
    const rankingClause = search && search.trim()
      ? `ts_rank(provision_tsv, plainto_tsquery('english', $${queryParams.findIndex(p => p === search.trim()) + 1})) DESC,`
      : '';

    // Main query with smart ranking
    // OPTIMIZATION: Filter by document_id FIRST (uses index), then apply text filters on smaller set
    const provisionsQuery = `
      WITH document_filtered AS MATERIALIZED (
        -- Step 1: Filter by document_id first (can use index, reduces to ~241 rows)
        -- MATERIALIZED forces PostgreSQL to execute this first and cache results
        SELECT *
        FROM regulatory_provisions
        WHERE ${whereClauses[0]}  -- Document ID filter only
      ),
      ranked_provisions AS (
        -- Step 2: Apply text filters and ranking on the smaller filtered set
        SELECT
          id,
          ref_number,
          section_header,
          provision_text,
          document_id,
          provision_type,
          pdf_page,
          pdf_page_image_url,
          zone,
          development_type,
          -- Provision type ranking (1=highest priority)
          CASE
            WHEN provision_text LIKE '%<table%' THEN 1
            WHEN provision_text ~ '[0-9]+\\.?[0-9]*\\s*(m|metre|%|sqm|m²)' THEN 2
            WHEN provision_text ~* '^(Control|Controls)' THEN 3
            WHEN provision_text ~* '^(Objective|Objectives)' THEN 5
            ELSE 4
          END as type_rank,
          -- Search relevance (if search provided)
          ${search && search.trim() ? `
            ts_rank(provision_tsv, plainto_tsquery('english', $${queryParams.findIndex(p => p === search.trim()) + 1})) as search_rank
          ` : '0 as search_rank'}
        FROM document_filtered
        WHERE ${whereClauses.length > 1 ? whereClauses.slice(1).join(' AND ') : 'TRUE'}
      )
      SELECT *
      FROM ranked_provisions
      ORDER BY
        type_rank ASC,          -- Tables first, objectives last
        search_rank DESC,        -- Search relevance (if search provided)
        pdf_page ASC,           -- Document order
        id ASC
      LIMIT $${paramIndex}
      OFFSET $${paramIndex + 1}
    `;

    queryParams.push(limit, offset);

    console.log('[DCP Provisions API] Query params:', queryParams);

    // Execute query
    const provisionsResult = await query(provisionsQuery, queryParams);

    // Get total count for pagination (optimized with same filter order)
    const countQuery = `
      WITH document_filtered AS MATERIALIZED (
        SELECT id, provision_text, provision_tsv, section_header
        FROM regulatory_provisions
        WHERE ${whereClauses[0]}
      )
      SELECT COUNT(*) as total
      FROM document_filtered
      WHERE ${whereClauses.length > 1 ? whereClauses.slice(1).join(' AND ') : 'TRUE'}
    `;

    const countResult = await query(countQuery, queryParams.slice(0, -2)); // Exclude limit/offset
    const totalCount = parseInt(countResult.rows[0]?.total || '0');

    const processingTime = Date.now() - startTime;

    console.log(`[DCP Provisions API] Found ${provisionsResult.rows.length} provisions (total: ${totalCount})`);

    return NextResponse.json({
      success: true,
      data: {
        provisions: provisionsResult.rows,
        totalCount,
        hasMore: (offset + limit) < totalCount,
        pagination: {
          limit,
          offset,
          currentPage: Math.floor(offset / limit) + 1,
          totalPages: Math.ceil(totalCount / limit)
        }
      },
      metadata: {
        lga: targetLGA,
        zone,
        developmentType,
        dcpSection: dcpSectionName,
        documentPatterns: dcpDocumentPatterns,
        filters: {
          search: search || null,
          categories: categories.length > 0 ? categories : null,
          provisionType: provisionType !== 'all' ? provisionType : null
        },
        processingTimeMs: processingTime,
        timestamp: new Date().toISOString()
      }
    });

  } catch (error) {
    console.error('[DCP Provisions API] Error:', error);

    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
      processingTimeMs: Date.now() - startTime
    }, { status: 500 });
  }
}
