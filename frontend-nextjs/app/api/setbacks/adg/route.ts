import { NextRequest, NextResponse } from 'next/server';
import { Pool } from 'pg';

const pool = new Pool({
  user: process.env.PGUSER || 'postgres',
  host: process.env.PGHOST || 'localhost',
  database: process.env.PGDATABASE || 'nsw_planning',
  password: process.env.PGPASSWORD || 'postgres',
  port: parseInt(process.env.PGPORT || '5432'),
});

/**
 * GET /api/setbacks/adg
 *
 * Returns NSW Apartment Design Guide building separation standards (Section 3F-1)
 * These are STATUTORY requirements under SEPP (Housing) 2021
 *
 * Query Parameters:
 * - building_height: Building height in meters (required)
 * - development_type: Type of development (required)
 *
 * Example:
 * /api/setbacks/adg?building_height=10&development_type=multi_dwelling_housing
 */
export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const buildingHeightStr = searchParams.get('building_height');
  const developmentType = searchParams.get('development_type');

  // Validate parameters
  if (!buildingHeightStr || !developmentType) {
    return NextResponse.json(
      { error: 'Missing required parameters: building_height and development_type' },
      { status: 400 }
    );
  }

  const buildingHeight = parseFloat(buildingHeightStr);

  if (isNaN(buildingHeight) || buildingHeight <= 0) {
    return NextResponse.json(
      { error: 'building_height must be a positive number' },
      { status: 400 }
    );
  }

  // Check if ADG applies to this development type
  const adgApplicableTypes = [
    'multi_dwelling_housing',
    'residential_flat_building',
    'shop_top_housing'
  ];

  if (!adgApplicableTypes.includes(developmentType)) {
    return NextResponse.json({
      applies: false,
      reason: 'ADG building separation standards only apply to multi-dwelling housing, residential flat buildings, and shop-top housing developments',
      development_type: developmentType
    });
  }

  // Determine building height category based on ADG Table 3F-1
  let heightCondition: string;
  let heightLabel: string;
  let storeyRange: string;

  if (buildingHeight <= 12) {
    heightCondition = 'building_height_up_to_12m';
    heightLabel = 'Up to 12m';
    storeyRange = '4 storeys';
  } else if (buildingHeight <= 25) {
    heightCondition = 'building_height_12m_to_25m';
    heightLabel = 'Up to 25m';
    storeyRange = '5-8 storeys';
  } else {
    heightCondition = 'building_height_over_25m';
    heightLabel = 'Over 25m';
    storeyRange = '9+ storeys';
  }

  let client;

  try {
    client = await pool.connect();

    // Query ADG standards from setback_rules table
    const result = await client.query(`
      SELECT
        ref_number,
        boundary_type,
        setback_meters,
        exceptions,
        source_text,
        document_name,
        notes
      FROM setback_rules
      WHERE ref_number LIKE 'ADG 3F-1%'
        AND $1 = ANY(site_condition)
        AND $2 = ANY(development_type)
      ORDER BY
        boundary_type,
        CASE WHEN ref_number LIKE '%Non-habitable%' THEN 2 ELSE 1 END
    `, [heightCondition, developmentType]);

    if (result.rows.length === 0) {
      return NextResponse.json({
        applies: true,
        error: 'ADG standards not found in database. This may indicate a database setup issue.',
        height_category: heightLabel,
        development_type: developmentType
      }, { status: 500 });
    }

    // Organize results by boundary and room type
    const standards = {
      applies: true,
      building_height_meters: buildingHeight,
      height_category: heightLabel,
      storey_range: storeyRange,
      development_type: developmentType,
      setbacks: {
        side: {
          habitable_rooms_and_balconies: null as number | null,
          non_habitable_rooms: null as number | null,
        },
        rear: {
          habitable_rooms_and_balconies: null as number | null,
          non_habitable_rooms: null as number | null,
        }
      },
      additional_requirements: [] as string[],
      source: {
        document: 'NSW Apartment Design Guide - Part 3: Siting the Development',
        section: '3F-1 Visual Privacy',
        design_criteria: 'Design Criteria 1',
        authority: 'SEPP (Housing) 2021',
        legal_status: 'STATUTORY',
        url: 'https://www.planning.nsw.gov.au/sites/default/files/2023-03/apartment-design-guide-part-3-siting-the-development.pdf',
        page: 63,
        pdf_page_image_url: '/pdf-pages/adg/adg-part-3_page_63.png'
      },
      notes: [] as string[]
    };

    // Parse results
    const seenNotes = new Set<string>();

    result.rows.forEach(row => {
      const isNonHabitable = row.ref_number.includes('Non-habitable');
      const roomTypeKey = isNonHabitable ? 'non_habitable_rooms' : 'habitable_rooms_and_balconies';
      const boundary = row.boundary_type as 'side' | 'rear';

      if (standards.setbacks[boundary]) {
        standards.setbacks[boundary][roomTypeKey] = parseFloat(row.setback_meters);
      }

      // Add exceptions/requirements (avoid duplicates)
      if (row.exceptions && !seenNotes.has(row.exceptions)) {
        standards.additional_requirements.push(row.exceptions);
        seenNotes.add(row.exceptions);
      }

      // Add database notes
      if (row.notes && !seenNotes.has(row.notes)) {
        standards.notes.push(row.notes);
        seenNotes.add(row.notes);
      }
    });

    return NextResponse.json(standards);

  } catch (error) {
    console.error('Error fetching ADG standards:', error);
    return NextResponse.json(
      { error: 'Failed to fetch ADG standards from database' },
      { status: 500 }
    );
  } finally {
    if (client) client.release();
  }
}
