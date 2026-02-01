/**
 * Parking Requirements API
 *
 * Returns parking requirements from SEPP Housing for a given development type.
 * SEPP Housing overrides DCP parking requirements in most cases.
 *
 * Query Parameters:
 * - dev_type: Development type (e.g., "dual_occupancy", "multi_dwelling", "residential_flat_building")
 * - zone: Zone code (optional, used for residential_flat which varies by zone)
 *
 * Response:
 * - value: Numeric parking requirement per dwelling
 * - unit: "spaces"
 * - source_clause: SEPP Housing clause reference
 * - source_url: Link to legislation
 * - display_text: Human-readable requirement
 * - sepp_override: Whether SEPP overrides DCP
 */

import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';
import { z } from 'zod';
import { validateRequest, formatValidationErrors } from '@/lib/schemas';


export const dynamic = 'force-dynamic';
// SEPP Housing legislation URL
const SEPP_HOUSING_URL = 'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714';

// Map frontend dev_type to database development_type
const DEV_TYPE_MAP: Record<string, string[]> = {
  'dual_occupancy': ['dual_occupancy'],
  'dual_occupancy_attached': ['dual_occupancy'],
  'dual_occupancy_detached': ['dual_occupancy'],
  'multi_dwelling_housing': ['multi_dwelling'],
  'multi_dwelling': ['multi_dwelling'],
  'terraces': ['terraces'],
  'residential_flat_building': ['residential_flat_r1r2', 'residential_flat_building'],
  'rfb': ['residential_flat_r1r2', 'residential_flat_building'],
  'boarding_house': ['boarding_house'],
  'secondary_dwelling': ['secondary_dwelling'],
};

interface ParkingRequirement {
  value: number;
  unit: string;
  source_clause: string;
  source_url: string;
  display_text: string;
  sepp_override: boolean;
  development_type: string;
}

// Schema for parking query params
const ParkingQuerySchema = z.object({
  dev_type: z.string().min(1, 'dev_type is required'),
  zone: z.string().optional(),
});

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;

    // Convert URLSearchParams to object
    const params = {
      dev_type: searchParams.get('dev_type'),
      zone: searchParams.get('zone'),
    };

    // Validate query parameters
    const validation = validateRequest(ParkingQuerySchema, params);

    if (!validation.success) {
      return NextResponse.json(
        {
          success: false,
          error: 'Invalid query parameters',
          details: formatValidationErrors(validation.details),
        },
        { status: 400 }
      );
    }

    const { dev_type: devType, zone } = validation.data;

    // Map to database dev types
    const dbDevTypes = DEV_TYPE_MAP[devType.toLowerCase()] || [devType];

    const pool = getPool();
    const client = await pool.connect();

    try {
      // Query SEPP Housing standards for parking
      const result = await client.query(`
        SELECT
          development_type,
          numeric_value,
          unit,
          source_clause
        FROM housing_sepp_standards
        WHERE standard_type = 'parking_per_dwelling'
          AND development_type = ANY($1::text[])
        LIMIT 1
      `, [dbDevTypes]);

      if (result.rows.length === 0) {
        // No SEPP standard found - return indication that DCP applies
        return NextResponse.json({
          success: true,
          data: {
            value: null,
            unit: null,
            source_clause: null,
            source_url: null,
            display_text: 'Refer to DCP parking requirements',
            sepp_override: false,
            development_type: devType,
            note: 'No SEPP Housing parking standard applies to this development type'
          }
        });
      }

      const row = result.rows[0];
      const value = parseFloat(row.numeric_value);

      // Format display text based on value
      let displayText: string;
      if (value === 1) {
        displayText = '1 space per dwelling';
      } else if (value < 1) {
        displayText = `${value} spaces per dwelling`;
      } else {
        displayText = `${value} spaces per dwelling`;
      }

      const requirement: ParkingRequirement = {
        value,
        unit: row.unit || 'spaces',
        source_clause: `SEPP Housing cl. ${row.source_clause}`,
        source_url: `${SEPP_HOUSING_URL}#sec.${row.source_clause.split('(')[0]}`,
        display_text: displayText,
        sepp_override: true,
        development_type: row.development_type,
      };

      return NextResponse.json({
        success: true,
        data: requirement,
        meta: {
          requested_dev_type: devType,
          matched_dev_type: row.development_type,
          zone: zone,
          note: 'SEPP Housing parking standards override DCP requirements'
        }
      });

    } finally {
      client.release();
    }

  } catch (error) {
    console.error('[Parking API] Error:', error);
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

// Documentation endpoint
export async function POST() {
  return NextResponse.json({
    endpoint: 'GET /api/compliance/parking',
    description: 'Returns SEPP Housing parking requirements for development type',
    parameters: {
      dev_type: {
        required: true,
        description: 'Development type',
        examples: ['dual_occupancy', 'multi_dwelling_housing', 'residential_flat_building', 'terraces']
      },
      zone: {
        required: false,
        description: 'Zone code (for zone-specific requirements)',
        examples: ['R1', 'R2', 'R3']
      }
    },
    response: {
      value: 'number - Parking spaces per dwelling',
      unit: 'string - Always "spaces"',
      source_clause: 'string - SEPP Housing clause reference',
      source_url: 'string - Link to legislation',
      display_text: 'string - Human-readable requirement',
      sepp_override: 'boolean - Whether SEPP overrides DCP'
    }
  });
}
