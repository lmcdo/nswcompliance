import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';

/**
 * TOD Parking Rates API
 *
 * Returns parking rates with source provenance:
 * 1. First checks SEPP Housing standards (overrides local DCP)
 * 2. Then checks council DCP provisions
 * 3. Returns "not found" if no authoritative source - no hardcoded fallbacks
 */

// Map development types to SEPP Housing dwelling types
const SEPP_DWELLING_TYPE_MAP: Record<string, string[]> = {
  'residential_flat': ['residential_flat_building', 'rfb'],
  'residential_flat_building': ['residential_flat_building', 'rfb'],
  'multi_dwelling': ['multi_dwelling_housing', 'mdh'],
  'multi_dwelling_housing': ['multi_dwelling_housing', 'mdh'],
  'shop_top_housing': ['shop_top_housing'],
  'boarding_house': ['boarding_house'],
  'dual_occupancy': ['dual_occupancy'],
  'dwelling_house': ['dwelling_house'],
  'manor_house': ['manor_house'],
  'townhouse': ['multi_dwelling_housing'],
  'terrace': ['multi_dwelling_housing'],
};

/**
 * GET /api/tod/parking-rates
 *
 * Fetches parking rates from authoritative sources with provenance:
 * 1. SEPP Housing standards (state-level, overrides DCP)
 * 2. Council DCP provisions
 *
 * Query params: zone, development_type, lga
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const zone = searchParams.get('zone');
    const developmentType = searchParams.get('development_type');
    const lga = searchParams.get('lga');

    if (!developmentType) {
      return NextResponse.json({
        found: false,
        message: 'development_type parameter required'
      }, { status: 400 });
    }

    const pool = getPool();

    // 1. First check SEPP Housing standards (authoritative, overrides local DCP)
    const seppDwellingTypes = SEPP_DWELLING_TYPE_MAP[developmentType] || [developmentType];

    try {
      const seppResult = await pool.query(`
        SELECT
          standard_type,
          numeric_value,
          unit,
          source_clause,
          dwelling_type,
          effective_date,
          notes
        FROM housing_sepp_standards
        WHERE dwelling_type = ANY($1)
          AND standard_type IN ('parking_per_dwelling', 'parking_rate', 'car_parking')
          AND (is_current = true OR is_current IS NULL)
        ORDER BY
          CASE WHEN dwelling_type = $2 THEN 0 ELSE 1 END,
          effective_date DESC NULLS LAST
        LIMIT 1
      `, [seppDwellingTypes, developmentType]);

      if (seppResult.rows.length > 0) {
        const row = seppResult.rows[0];
        return NextResponse.json({
          found: true,
          rate: parseFloat(row.numeric_value),
          unit: row.unit || 'spaces',
          source: `SEPP (Housing) 2021 ${row.source_clause}`,
          source_clause: row.source_clause,
          source_url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714',
          dwelling_type: row.dwelling_type,
          effective_date: row.effective_date,
          notes: row.notes,
          authority: 'SEPP',
          sepp_override: true
        });
      }
    } catch (seppError) {
      console.log('[Parking Rates API] SEPP query failed:', seppError);
    }

    // 2. Check council DCP provisions for parking
    if (lga) {
      try {
        const dcpResult = await pool.query(`
          SELECT
            rp.id,
            rp.provision_title,
            rp.requirement_text,
            rp.numeric_value,
            rp.unit,
            rp.pdf_page,
            rp.pdf_page_image_url,
            d.dcp_name
          FROM regulatory_provisions rp
          JOIN dcps d ON rp.dcp_id = d.id
          WHERE d.council_name ILIKE $1
            AND (
              rp.provision_title ILIKE '%parking%'
              OR rp.subcategory ILIKE '%parking%'
              OR rp.topic ILIKE '%parking%'
            )
            AND (
              rp.development_type ILIKE $2
              OR rp.development_type IS NULL
            )
            AND rp.numeric_value IS NOT NULL
          ORDER BY
            CASE WHEN rp.development_type IS NOT NULL THEN 0 ELSE 1 END,
            rp.id
          LIMIT 1
        `, [`%${lga}%`, `%${developmentType.replace(/_/g, ' ')}%`]);

        if (dcpResult.rows.length > 0) {
          const row = dcpResult.rows[0];
          return NextResponse.json({
            found: true,
            rate: parseFloat(row.numeric_value),
            unit: row.unit || 'spaces',
            source: `${row.dcp_name} - ${row.provision_title}`,
            requirement_text: row.requirement_text,
            pdf_page: row.pdf_page,
            pdf_page_image_url: row.pdf_page_image_url,
            authority: 'DCP',
            sepp_override: false
          });
        }
      } catch (dcpError) {
        console.log('[Parking Rates API] DCP query failed:', dcpError);
      }
    }

    // 3. Return DCP provision text even without numeric extraction
    // Professionals read the actual provision - we provide the text + PDF source
    if (lga) {
      try {
        // Query regulatory_provisions table (same as working DCP provisions API)
        const provisionResult = await pool.query(`
          SELECT
            id,
            section_header,
            provision_text,
            document_id,
            provision_type,
            pdf_page,
            pdf_page_image_url
          FROM regulatory_provisions
          WHERE document_id ILIKE $1
            AND (
              provision_text ~* 'parking|car space|vehicle space'
              OR section_header ~* 'parking'
            )
          ORDER BY
            CASE
              WHEN section_header ~* 'parking' THEN 0
              WHEN provision_text ~* 'parking rate|spaces per' THEN 1
              ELSE 2
            END,
            pdf_page
          LIMIT 5
        `, [`%${lga}%`]);

        if (provisionResult.rows.length > 0) {
          return NextResponse.json({
            found: true,
            has_numeric_rate: false,
            provisions: provisionResult.rows.map(row => ({
              id: row.id,
              title: row.section_header,
              text: row.provision_text,
              pdf_page: row.pdf_page,
              pdf_page_image_url: row.pdf_page_image_url,
              document_id: row.document_id
            })),
            source: provisionResult.rows[0].document_id.replace(/_/g, ' '),
            council: lga,
            authority: 'DCP',
            note: 'Parking requirements vary by development type and context. Review the provision text to determine applicable rate.'
          });
        }
      } catch (provisionError) {
        console.log('[Parking Rates API] Provision text query failed:', provisionError);
      }
    }

    // No provisions found at all
    return NextResponse.json({
      found: false,
      message: `No parking provisions found${lga ? ` for ${lga}` : ''}. The DCP may not be loaded or parking may be in a different section.`
    });

  } catch (error) {
    console.error('[Parking Rates API] Error:', error);
    return NextResponse.json({
      found: false,
      error: error instanceof Error ? error.message : 'Internal server error'
    }, { status: 500 });
  }
}
