import { NextRequest, NextResponse } from 'next/server';
import { Pool } from 'pg';

// Database connection
const pool = new Pool({
  host: process.env.DB_HOST || process.env.DATABASE_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || process.env.DATABASE_PORT || '5432'),
  database: process.env.DB_NAME || process.env.DATABASE_NAME || 'nsw_planning',
  user: process.env.DB_USER || process.env.DATABASE_USER || 'postgres',
  password: process.env.DB_PASSWORD || process.env.DATABASE_PASSWORD || '',
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : undefined,
  statement_timeout: 30000
});

// Default parking rates by development type (from common DCP standards)
// These are fallbacks - actual rates should come from council DCPs
const DEFAULT_PARKING_RATES: Record<string, { rate: number; source: string }> = {
  'residential_flat': { rate: 1.0, source: 'Standard rate: 1 space per dwelling (varies by council DCP)' },
  'residential_flat_building': { rate: 1.0, source: 'Standard rate: 1 space per dwelling (varies by council DCP)' },
  'multi_dwelling': { rate: 1.0, source: 'Standard rate: 1 space per dwelling (varies by council DCP)' },
  'multi_dwelling_housing': { rate: 1.0, source: 'Standard rate: 1 space per dwelling (varies by council DCP)' },
  'shop_top_housing': { rate: 1.0, source: 'Standard rate: 1 space per dwelling (varies by council DCP)' },
  'boarding_house': { rate: 0.5, source: 'Standard rate: 0.5 spaces per room (SEPP Housing 2021)' },
  'dwelling_house': { rate: 1.0, source: 'Standard rate: 1 space per dwelling' },
  'dual_occupancy': { rate: 1.0, source: 'Standard rate: 1 space per dwelling' },
  'commercial': { rate: 0.033, source: 'Standard rate: 1 space per 30m² GFA (varies by council)' },
  'retail': { rate: 0.025, source: 'Standard rate: 1 space per 40m² GFA (varies by council)' },
};

/**
 * GET /api/tod/parking-rates
 *
 * Fetches parking rates from database or returns default rates
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

    // Try to find rate in database first
    let dbRate = null;
    try {
      const result = await pool.query(`
        SELECT parking_rate, source_document, notes
        FROM parking_rates
        WHERE development_type = $1
        AND (zone_code = $2 OR zone_code IS NULL)
        AND (lga = $3 OR lga IS NULL)
        ORDER BY
          CASE WHEN zone_code IS NOT NULL AND lga IS NOT NULL THEN 1
               WHEN zone_code IS NOT NULL THEN 2
               WHEN lga IS NOT NULL THEN 3
               ELSE 4 END
        LIMIT 1
      `, [developmentType, zone, lga]);

      if (result.rows.length > 0) {
        dbRate = result.rows[0];
      }
    } catch (dbError) {
      // Table might not exist - fall through to defaults
      console.log('[Parking Rates API] Database query failed, using defaults:', dbError);
    }

    if (dbRate) {
      return NextResponse.json({
        found: true,
        rate: parseFloat(dbRate.parking_rate),
        source: dbRate.source_document || `${lga || 'Council'} DCP`,
        notes: dbRate.notes
      });
    }

    // Fall back to default rates
    const defaultRate = DEFAULT_PARKING_RATES[developmentType];
    if (defaultRate) {
      return NextResponse.json({
        found: true,
        rate: defaultRate.rate,
        source: defaultRate.source,
        isDefault: true
      });
    }

    // No rate found
    return NextResponse.json({
      found: false,
      message: `No parking rate found for ${developmentType}. Check council DCP for specific requirements.`
    });

  } catch (error) {
    console.error('[Parking Rates API] Error:', error);
    return NextResponse.json({
      found: false,
      error: error instanceof Error ? error.message : 'Internal server error'
    }, { status: 500 });
  }
}
