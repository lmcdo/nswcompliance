/**
 * CDC Full Compliance Check API
 *
 * Compares the entered development details with the Housing Code standards
 * STORED in cdc_eligibility_standards (SEPP Exempt and Complying Development
 * Codes 2008, Part 3). No planning figure is typed in this file.
 *
 * Each check is one of: pass, fail, or not_checked. not_checked carries a reason
 * and the stored clause list; it never carries a number or a verdict.
 *
 * prior-art-checked: rewrite of the existing route onto lib/cdc.
 */

import { NextRequest, NextResponse } from 'next/server';
import { loadHousingCodeStandards } from '@/lib/cdc/housing-code-standards-db';
import {
  evaluateCdcChecks,
  summariseChecks,
  shortfallText,
  type CdcCheckInput,
} from '@/lib/cdc/housing-code-checks';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as CdcCheckInput & { address?: string };

    if (!body.setbacks || typeof body.setbacks !== 'object') {
      return NextResponse.json({ error: 'Setbacks object is required' }, { status: 400 });
    }

    const stored = await loadHousingCodeStandards();
    const results = evaluateCdcChecks(body, stored.parsed, stored.error);
    const summary = summariseChecks(results);

    const failed = results.filter((r) => r.status === 'fail');
    const recommendations = failed.map(
      (r) =>
        `${r.label}: ${r.proposed}${r.unit === '' ? '' : ' ' + r.unit}, ${shortfallText(r)} ` +
        `(${r.required}${r.unit === '' ? '' : ' ' + r.unit}, ${r.clause})`
    );

    let text: string;
    if (summary.fail > 0) {
      text = `${summary.fail} of ${summary.total} checks do not meet the stored standards.`;
    } else if (summary.allPass) {
      text = 'Every check met its stored standard.';
    } else {
      text =
        `${summary.pass} of ${summary.total} checks met a stored standard; ${summary.notChecked} not checked. ` +
        'A check marked Not checked has no stored standard that applies to the values entered.';
    }

    return NextResponse.json({
      success: true,
      // true only when every check passed; false when any failed; null when undecided.
      overallCompliant: summary.fail > 0 ? false : summary.allPass ? true : null,
      passCount: summary.pass,
      failCount: summary.fail,
      notCheckedCount: summary.notChecked,
      totalChecks: summary.total,
      results,
      summary: text,
      recommendations,
      disclaimer:
        'Checks use only the Housing Code standards stored from the Codes SEPP. ' +
        'A check marked Not checked was not assessed. Lot characteristics, zone and ' +
        'council controls can also apply. Confirm with a registered certifier.',
      meta: {
        timestamp: new Date().toISOString(),
        standardsApplied: 'SEPP (Exempt and Complying Development Codes) 2008, Part 3 Housing Code, as stored',
        standardsError: stored.error,
      },
    });
  } catch (error) {
    console.error('CDC compliance check error:', error);
    return NextResponse.json(
      {
        error: 'Failed to check compliance',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

export async function GET() {
  const stored = await loadHousingCodeStandards();
  return NextResponse.json({
    success: true,
    usage: {
      method: 'POST',
      body: {
        developmentType: 'new_dwelling | alteration | addition | secondary_dwelling',
        lotAreaM2: 'number (optional, selects the stored band)',
        lotWidthM: 'number (optional, lot width at the building line)',
        setbacks: {
          front: 'number (meters)',
          sideLeft: 'number (meters)',
          sideRight: 'number (meters)',
          rear: 'number (meters)',
        },
        hasUpperFloorHabitableRooms: 'boolean',
        siteCoveragePercent: 'number (0-100)',
        landscapedAreaPercent: 'number (0-100)',
        buildingHeightMeters: 'number',
        storeys: 'number',
        parkingSpaces: 'number',
      },
    },
    storedStandards: stored.parsed
      .filter((p) => p.usable)
      .map((p) => ({
        standardType: p.row.standard_type,
        value: p.numericValue,
        band: p.row.conditionality,
        clause: p.citation,
      })),
    standardsError: stored.error,
  });
}
