/**
 * CDC Setback Check API
 *
 * Compares proposed setbacks with the Housing Code standards STORED in
 * cdc_eligibility_standards. No figure is typed here. A setback with no
 * applicable stored standard returns status 'not_checked' with a reason.
 *
 * prior-art-checked: rewrite of the existing route onto lib/cdc.
 */

import { NextRequest, NextResponse } from 'next/server';
import { loadHousingCodeStandards } from '@/lib/cdc/housing-code-standards-db';
import { evaluateCdcChecks, type CdcCheckInput } from '@/lib/cdc/housing-code-checks';

export const dynamic = 'force-dynamic';

interface SetbackInput {
  front?: number;
  side?: number;
  side_left?: number;
  side_right?: number;
  rear?: number;
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { setbacks, hasUpperFloorWindows, lotAreaM2, lotWidthM, buildingHeightM } = body as {
      setbacks: SetbackInput;
      hasUpperFloorWindows?: boolean;
      lotAreaM2?: number | null;
      lotWidthM?: number | null;
      buildingHeightM?: number | null;
    };

    if (!setbacks || typeof setbacks !== 'object') {
      return NextResponse.json({ error: 'Setbacks object is required' }, { status: 400 });
    }
    const provided = (['front', 'side', 'side_left', 'side_right', 'rear'] as const).filter(
      (k) => typeof setbacks[k] === 'number'
    );
    if (provided.length === 0) {
      return NextResponse.json({ error: 'At least one setback value must be provided' }, { status: 400 });
    }

    const input: CdcCheckInput = {
      lotAreaM2,
      lotWidthM,
      buildingHeightMeters: buildingHeightM,
      hasUpperFloorHabitableRooms: hasUpperFloorWindows === true,
      setbacks: {
        front: setbacks.front,
        sideLeft: setbacks.side_left ?? setbacks.side,
        sideRight: setbacks.side_right ?? setbacks.side,
        rear: setbacks.rear,
      },
    };

    const stored = await loadHousingCodeStandards();
    const all = evaluateCdcChecks(input, stored.parsed, stored.error);
    const wanted = new Set<string>();
    if (typeof setbacks.front === 'number') wanted.add('front');
    if (typeof setbacks.side === 'number' || typeof setbacks.side_left === 'number') wanted.add('sideLeft');
    if (typeof setbacks.side === 'number' || typeof setbacks.side_right === 'number') wanted.add('sideRight');
    if (typeof setbacks.rear === 'number') wanted.add('rear');
    const results = all.filter((r) => wanted.has(r.key));

    const failed = results.filter((r) => r.status === 'fail');
    const undecided = results.filter((r) => r.status === 'not_checked');

    return NextResponse.json({
      success: true,
      overallCompliant: failed.length > 0 ? false : undecided.length === 0 ? true : null,
      results,
      summary:
        failed.length > 0
          ? `${failed.length} setback(s) do not meet the stored standards: ${failed.map((r) => r.label).join(', ')}.`
          : undecided.length > 0
            ? `${undecided.length} setback(s) not checked: no stored standard applies to the values entered.`
            : 'Every setback met its stored standard.',
      disclaimer:
        'Checks use only the Housing Code standards stored from the Codes SEPP. ' +
        'A setback marked Not checked was not assessed. Confirm with a registered certifier.',
      meta: {
        timestamp: new Date().toISOString(),
        standardsApplied: 'SEPP (Exempt and Complying Development Codes) 2008, Part 3 Housing Code, as stored',
        standardsError: stored.error,
      },
    });
  } catch (error) {
    console.error('CDC setback check error:', error);
    return NextResponse.json(
      {
        error: 'Failed to check setback compliance',
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
    storedStandards: stored.parsed
      .filter((p) => p.usable && /setback/.test(p.row.standard_type))
      .map((p) => ({
        standardType: p.row.standard_type,
        value: p.numericValue,
        band: p.row.conditionality,
        clause: p.citation,
      })),
    standardsError: stored.error,
    usage: {
      method: 'POST',
      body: {
        setbacks: {
          front: 'number (meters)',
          side: 'number (meters) - generic side setback',
          side_left: 'number (meters)',
          side_right: 'number (meters)',
          rear: 'number (meters)',
        },
        hasUpperFloorWindows: 'boolean',
        lotAreaM2: 'number (optional)',
        lotWidthM: 'number (optional, at the building line)',
        buildingHeightM: 'number (optional)',
      },
    },
  });
}
