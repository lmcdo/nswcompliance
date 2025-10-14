/**
 * DCP Parking Requirements API
 * Returns parking requirements for a given development type from Marrickville DCP 2011
 * Handles all development types from the assessment page dropdown
 */

import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';

// Development type mapping: Frontend dropdown value → DCP terminology
const DEV_TYPE_MAPPING: Record<string, { searchTerm: string; tableId: number; description: string }> = {
  dwelling_house: {
    searchTerm: 'Dwelling houses',
    tableId: 66126,
    description: 'Includes attached, semi-detached and secondary dwellings'
  },
  secondary_dwelling: {
    searchTerm: 'secondary dwelling',
    tableId: 66126,
    description: 'Combined with principal dwelling'
  },
  shop_top_housing: {
    searchTerm: 'Shop ?top housing',
    tableId: 66126,
    description: 'Rates vary by number of units (6 or less vs 7+)'
  },
  multi_dwelling: {
    searchTerm: 'residential ?flat ?buildings?', // Multi-dwelling uses RFB rates
    tableId: 66126,
    description: 'Uses residential flat building rates'
  },
  residential_flat: {
    searchTerm: 'residential ?flat ?buildings?',
    tableId: 66126,
    description: 'Rates vary by bedroom count (studio, 1br, 2br, 3+br)'
  },
  boarding_house: {
    searchTerm: 'Boarding houses',
    tableId: 66126,
    description: '1 per resident employee + 0.5 per boarding room'
  },
  child_care: {
    searchTerm: 'Child care centres',
    tableId: 66128,
    description: 'Rates per GFA (Gross Floor Area)'
  },
  commercial: {
    searchTerm: 'Business premises|retail premises|shops',
    tableId: 66127,
    description: 'Rates vary by size and parking area'
  }
};

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { developmentType, zone, lga } = body;

    if (!developmentType) {
      return NextResponse.json({
        success: false,
        error: 'Development type is required'
      }, { status: 400 });
    }

    // Get mapping for this development type
    const mapping = DEV_TYPE_MAPPING[developmentType];
    if (!mapping) {
      return NextResponse.json({
        success: false,
        error: `Unknown development type: ${developmentType}`
      }, { status: 400 });
    }

    // Query the parking table using shared db connection
    const parkingQuery = `
      SELECT
        id,
        ref_number,
        provision_text,
        document_id
      FROM regulatory_provisions
      WHERE id = $1
      LIMIT 1;
    `;

    const result = await query(parkingQuery, [mapping.tableId]);

    if (result.rows.length === 0) {
      return NextResponse.json({
        success: false,
        error: 'Parking requirements not found'
      }, { status: 404 });
    }

    const parkingTable = result.rows[0];

    // Extract the relevant row from the HTML table for this development type
    const htmlTable = parkingTable.provision_text;
    const relevantRow = extractParkingRow(htmlTable, mapping.searchTerm);

    return NextResponse.json({
      success: true,
      data: {
        developmentType,
        documentId: parkingTable.document_id,
        provisionId: parkingTable.id,
        refNumber: parkingTable.ref_number,
        fullTable: htmlTable,
        relevantRow,
        description: mapping.description,
        source: {
          document: 'Marrickville DCP 2011',
          section: '2.10 Parking',
          clause: 'Table 1 (Residential) or equivalent'
        }
      }
    });

  } catch (error) {
    console.error('[DCP Parking API] Error:', error);
    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error'
    }, { status: 500 });
  }
}

/**
 * Extract the relevant parking row from the HTML table
 * Uses regex to find rows matching the development type
 */
function extractParkingRow(htmlTable: string, searchTerm: string): string | null {
  try {
    // Extract all <tr> rows
    const rowRegex = /<tr>(.*?)<\/tr>/gs;
    const rows = [...htmlTable.matchAll(rowRegex)];

    // Find row matching the search term (case-insensitive)
    const searchRegex = new RegExp(searchTerm, 'i');

    for (const row of rows) {
      const rowContent = row[1];
      if (searchRegex.test(rowContent)) {
        return `<table><tr>${rowContent}</tr></table>`;
      }
    }

    return null;
  } catch (error) {
    console.error('[extractParkingRow] Parse error:', error);
    return null;
  }
}
