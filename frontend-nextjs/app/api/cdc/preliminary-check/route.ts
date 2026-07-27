/**
 * CDC Preliminary Eligibility Check API
 *
 * Thin data-plumbing layer over the backend CDC screen engine (#820 PR-2):
 * this route fetches the property facts (zone, lot, heritage, overlays,
 * exclusion layers) and POSTs them to the Python engine, which owns ALL
 * regulatory values (verified cdc_eligibility_standards rows, quote-cited to
 * the Codes SEPP). No zone lists or thresholds live here — the previous
 * hardcoded set carried two grounding errors (acid-sulfate class ≤3 instead
 * of 1–2; B1/B2 zones with no Housing Code basis).
 *
 * NOTE: This is NOT a formal CDC assessment. The engine never answers "yes" —
 * only "no" with cited exclusions, or "maybe" (professional verification).
 */

import { NextRequest, NextResponse } from 'next/server';
import { PropertyDataService } from '@/lib/property-data';

export const dynamic = 'force-dynamic';

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000';

interface CdcExclusion {
  reason: string;
  constraint: string;
  severity: 'definite' | 'likely';
  source: string;
}

interface CdcCheckResult {
  eligible: 'yes' | 'no' | 'maybe';
  exclusions: CdcExclusion[];
  warnings: string[];
  checksPerformed: string[];
  disclaimer: string;
}

/**
 * Extract zone code from zone description
 * e.g., "R2 Low Density Residential" -> "R2"
 */
function extractZoneCode(zoneDescription: string | null | undefined): string | null {
  if (!zoneDescription) return null;
  const match = zoneDescription.match(/^([A-Z]+[0-9]*)/);
  return match ? match[1] : null;
}

/** Three-state boolean: undefined/null stays null (= not determined). */
function threeState(value: unknown): boolean | null {
  if (value === true) return true;
  if (value === false) return false;
  return null;
}

/**
 * Build the engine's input payload from property data. Parsing only —
 * no regulatory decisions are made here.
 */
async function buildScreenInputs(address: string) {
  const propertyData = await PropertyDataService.getPropertyComplianceData(address);
  const { constraints, heritage, environmental, propertyArea, lotDimensions } = propertyData;

  // Lot area: prefer cadastre-calculated, fall back to property area string.
  // The fallback must respect the unit — "0.1 ha" is 1,000 m², not 0.1 m²,
  // and an unknown unit reads as unknown, never as square metres.
  let lotArea: number | null = null;
  if (lotDimensions?.area) {
    lotArea = lotDimensions.area;
  } else if (propertyArea) {
    const areaMatch = propertyArea.match(/([\d,]+\.?\d*)\s*(ha|hectare|hectares|m2|m²|sqm|square met\w*)?/i);
    if (areaMatch && areaMatch[1]) {
      const value = parseFloat(areaMatch[1].replace(/,/g, ''));
      const unit = (areaMatch[2] || '').toLowerCase();
      if (unit.startsWith('ha')) {
        lotArea = value * 10_000;
      } else if (unit) {
        lotArea = value;                 // an explicit m² variant
      } else {
        lotArea = null;                  // no unit — cannot assume m²
      }
    }
  }

  // Heritage: item vs conservation area are INDEPENDENT facts for the engine —
  // "Heritage item within a conservation area" must set both, never one at
  // the other's expense.
  let heritageItem: boolean | null = null;
  let heritageHca: boolean | null = null;
  if (heritage?.isHeritage === false) {
    heritageItem = false;
    heritageHca = false;
  } else if (heritage?.isHeritage === true) {
    const type = (heritage.heritageType || '').toLowerCase();
    heritageHca = type.includes('conservation area');
    // An explicit item marker, or unclassifiable heritage (the stricter
    // reading, matching previous behaviour for bare "Heritage listed").
    heritageItem = type.includes('item') || !heritageHca;
  }

  // Acid sulfate: parse the class number; the engine validates range
  let acidClass: number | null = null;
  const classMatch = environmental?.acidSulfateSoils?.match(/Class\s*([0-9]+)/i);
  if (classMatch) acidClass = parseInt(classMatch[1], 10);

  return {
    zone_code: extractZoneCode(constraints?.zone),
    lot_area_m2: Number.isFinite(lotArea as number) ? lotArea : null,
    heritage_item: heritageItem,
    heritage_conservation_area: heritageHca,
    flood_prone: threeState(environmental?.floodProne),
    bushfire_prone: threeState(environmental?.bushfireProne),
    acid_sulfate_class: acidClass,
    complying_excluded: threeState(constraints?.complyingExcluded),
    dual_occ_prohibited: threeState(constraints?.dualOccProhibited?.prohibited),
    dual_occ_epi_name: constraints?.dualOccProhibited?.epiName ?? null,
  };
}

async function performCdcChecks(address: string): Promise<CdcCheckResult> {
  try {
    const inputs = await buildScreenInputs(address);

    const response = await fetch(`${PYTHON_API}/pipeline/cdc/screen`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(inputs),
      signal: AbortSignal.timeout(15_000),
    });

    if (!response.ok) {
      // 503 = standards unavailable (engine fails closed) — surface visibly
      throw new Error(`CDC screen backend returned ${response.status}`);
    }

    const result = await response.json();
    return {
      eligible: result.eligible,           // engine never returns 'yes'
      exclusions: result.exclusions,
      warnings: result.warnings,
      checksPerformed: result.checks_performed,
      disclaimer: result.disclaimer,
    };
  } catch (error) {
    // Fail visible, never fail wrong: no screen ran, so nothing is asserted.
    return {
      eligible: 'maybe',
      exclusions: [],
      warnings: [
        `CDC screen could not run: ${error instanceof Error ? error.message : 'Unknown error'}`,
        'Manual verification required',
      ],
      checksPerformed: [],
      disclaimer: 'Screening unavailable. Professional assessment required.',
    };
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { address } = body;

    if (!address) {
      return NextResponse.json(
        { error: 'Address is required' },
        { status: 400 }
      );
    }

    const result = await performCdcChecks(address);

    return NextResponse.json({
      success: true,
      data: result,
      meta: {
        timestamp: new Date().toISOString(),
        address,
        source: 'NSW Planning Portal + SEPP (Exempt and Complying Development Codes) 2008 standards',
      },
    });
  } catch (error) {
    console.error('CDC check error:', error);
    return NextResponse.json(
      {
        error: 'Failed to perform CDC eligibility check',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const address = searchParams.get('address');

  if (!address) {
    return NextResponse.json(
      {
        error: 'Address query parameter is required',
        example: '/api/cdc/preliminary-check?address=123 Main St, Sydney NSW 2000',
      },
      { status: 400 }
    );
  }

  const result = await performCdcChecks(address);

  return NextResponse.json({
    success: true,
    data: result,
    meta: {
      timestamp: new Date().toISOString(),
      address,
      source: 'NSW Planning Portal + SEPP (Exempt and Complying Development Codes) 2008 standards',
    },
  });
}
