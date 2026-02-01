/**
 * Populate Common Definitions
 * POST /api/populate-definitions
 *
 * ADMIN ONLY - Adds missing common planning terms to regulatory_definitions table
 */

import { NextResponse } from 'next/server';
import { getPool } from '@/lib/database/pool-manager';

const COMMON_DEFINITIONS = [
  {
    term: 'BASIX',
    normalized: 'basix',
    text: 'Building Sustainability Index (BASIX) is an online assessment tool that measures the potential environmental performance of residential buildings. BASIX requires applicants to meet water, thermal comfort and energy targets by incorporating sustainable design features.',
    summary: 'Online assessment tool for sustainable residential building design',
    source: 'SEPP (Building Sustainability Index: BASIX) 2004',
    type: 'SEPP'
  },
  {
    term: 'FSR',
    normalized: 'fsr',
    text: 'Abbreviation for Floor Space Ratio. See "Floor Space Ratio" for full definition.',
    summary: 'Abbreviation for Floor Space Ratio',
    source: 'Standard Instrument LEP',
    type: 'LEP'
  },
  {
    term: 'Floor Space Ratio',
    normalized: 'floor space ratio',
    text: 'Floor Space Ratio (FSR) is the ratio of the gross floor area of all buildings on a site to the area of that site. For example, an FSR of 1:1 means the total floor area of buildings equals the site area. FSR controls building bulk and density.',
    summary: 'Ratio of total floor area to site area (controls density)',
    source: 'Standard Instrument LEP',
    type: 'LEP'
  },
  {
    term: 'CDC',
    normalized: 'cdc',
    text: 'Abbreviation for Complying Development Certificate. See "Complying Development Certificate" for full definition.',
    summary: 'Abbreviation for Complying Development Certificate',
    source: 'SEPP (Exempt and Complying Development Codes) 2008',
    type: 'SEPP'
  },
  {
    term: 'Complying Development Certificate',
    normalized: 'complying development certificate',
    text: 'A Complying Development Certificate (CDC) is a combined planning and construction approval for development that meets specific pre-determined criteria. CDCs are faster and cheaper than Development Applications (DA) but are only available for eligible development types that comply with all applicable development standards.',
    summary: 'Fast-track approval for development meeting specific criteria',
    source: 'SEPP (Exempt and Complying Development Codes) 2008',
    type: 'SEPP'
  },
  {
    term: 'Gross Floor Area',
    normalized: 'gross floor area',
    text: 'Gross Floor Area (GFA) is the total floor area of a building, measured from the external walls. GFA includes all floor levels and is used to calculate Floor Space Ratio (FSR). Certain areas may be excluded from GFA calculations depending on the specific LEP (e.g., car parking, plant rooms, basement storage).',
    summary: 'Total floor area measured from external walls',
    source: 'Standard Instrument LEP',
    type: 'LEP'
  },
  {
    term: 'GFA',
    normalized: 'gfa',
    text: 'Abbreviation for Gross Floor Area. See "Gross Floor Area" for full definition.',
    summary: 'Abbreviation for Gross Floor Area',
    source: 'Standard Instrument LEP',
    type: 'LEP'
  },
  {
    term: 'Site Area',
    normalized: 'site area',
    text: 'Site area is the total area of land on which development is proposed, measured in square metres. For FSR calculations, site area is the denominator. Site area typically excludes public roads but includes private access ways and driveways within the lot boundary.',
    summary: 'Total area of the development site in square metres',
    source: 'Standard Instrument LEP',
    type: 'LEP'
  },
  {
    term: 'Habitable Room',
    normalized: 'habitable room',
    text: 'A habitable room is a room used for living purposes including bedrooms, living rooms, dining rooms, studies, and kitchens (but not bathrooms, toilets, laundries, pantries, or corridors). Habitable rooms have specific requirements for natural light, ventilation, ceiling height, and minimum dimensions in DCPs and building codes.',
    summary: 'Room used for living (bedroom, living room, kitchen)',
    source: 'Building Code of Australia',
    type: 'DCP'
  },
  {
    term: 'Setback',
    normalized: 'setback',
    text: 'A setback is the minimum distance required between a building and a property boundary (front, side, or rear). Setbacks ensure adequate separation between buildings, provide space for landscaping, protect privacy, maintain streetscape character, and allow for building maintenance access. Setback requirements vary by zone, building height, and lot characteristics (e.g., corner lots).',
    summary: 'Minimum distance between building and property boundary',
    source: 'Development Control Plan',
    type: 'DCP'
  },
  {
    term: 'Building Height',
    normalized: 'building height',
    text: 'Building height is the vertical distance from natural ground level to the highest point of the building (excluding minor structures like chimneys, vents, or aerials). Height limits are specified in metres or storeys in the LEP Height of Buildings Map and aim to control building scale, overshadowing, and visual impact.',
    summary: 'Vertical distance from ground to highest building point',
    source: 'Standard Instrument LEP - Clause 4.3',
    type: 'LEP'
  }
];

export async function POST() {
  const pool = getPool();

  try {
    const results = {
      added: [] as string[],
      skipped: [] as string[],
      errors: [] as string[]
    };

    for (const def of COMMON_DEFINITIONS) {
      try {
        // Check if already exists
        const existing = await pool.query(
          'SELECT id FROM regulatory_definitions WHERE term_normalized = $1',
          [def.normalized]
        );

        if (existing.rows.length > 0) {
          results.skipped.push(def.term);
          continue;
        }

        // Insert new definition
        await pool.query(`
          INSERT INTO regulatory_definitions (
            term, term_normalized, definition_text, definition_summary,
            source_document, legislation_type
          ) VALUES ($1, $2, $3, $4, $5, $6)
        `, [def.term, def.normalized, def.text, def.summary, def.source, def.type]);

        results.added.push(def.term);
      } catch (err: any) {
        results.errors.push(`${def.term}: ${err.message}`);
      }
    }

    return NextResponse.json({
      success: true,
      added: results.added.length,
      skipped: results.skipped.length,
      errors: results.errors.length,
      details: results,
      timestamp: new Date().toISOString()
    });

  } catch (error: any) {
    return NextResponse.json({
      success: false,
      error: error.message
    }, { status: 500 });
  }
}
