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
    // Since zone/development_type metadata is often NULL, we build pattern from known DCP structure
    let dcpDocumentPattern: string;
    let dcpSectionName: string;

    // Map development types to DCP section patterns
    const devTypeMapping: Record<string, { pattern: string; section: string }> = {
      'dwelling_house': {
        pattern: `${lgaSearchPattern}.*4\\.1.*Low.*Density`,
        section: '4.1 Low Density Residential'
      },
      'multi_dwelling_housing': {
        pattern: `${lgaSearchPattern}.*4\\.2.*Multi.*Dwelling`,
        section: '4.2 Multi Dwelling Housing'
      },
      'residential_flat_building': {
        pattern: `${lgaSearchPattern}.*4\\.2.*Multi.*Dwelling`,
        section: '4.2 Multi Dwelling Housing'
      },
      // Add more mappings as needed
    };

    const mapping = devTypeMapping[developmentType];
    if (mapping) {
      dcpDocumentPattern = mapping.pattern;
      dcpSectionName = mapping.section;
    } else {
      // Fallback: search all DCP documents for this LGA
      dcpDocumentPattern = `${lgaSearchPattern}.*DCP`;
      dcpSectionName = 'All DCP Sections';
    }

    console.log('[DCP Provisions API] Document pattern:', dcpDocumentPattern);
    console.log('[DCP Provisions API] Section:', dcpSectionName);

    // Build dynamic WHERE clauses
    const whereClauses: string[] = [];
    const queryParams: any[] = [];
    let paramIndex = 1;

    // Base filter: document_id pattern
    whereClauses.push(`document_id ~* $${paramIndex}`);
    queryParams.push(dcpDocumentPattern);
    paramIndex++;

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
    const provisionsQuery = `
      WITH ranked_provisions AS (
        SELECT
          id,
          ref_number,
          section_header,
          provision_text,
          document_id,
          provision_type,
          pdf_page,
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
        FROM regulatory_provisions
        WHERE ${whereClauses.join(' AND ')}
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

    // Get total count for pagination
    const countQuery = `
      SELECT COUNT(*) as total
      FROM regulatory_provisions
      WHERE ${whereClauses.join(' AND ')}
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
        documentPattern: dcpDocumentPattern,
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
